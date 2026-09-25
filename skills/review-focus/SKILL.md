---
name: review-focus
description: Point a code review at the diff hunks that matter - the ones that weaken a check, change error handling, add network, file or shell calls, or touch security - and say when a change is cosmetic only. Uses jev-semgrep to judge each hunk. Use before reviewing or merging a branch, or to decide whether a change can merge without a close look.
---

# Review focus

*A [skope](https://github.com/mattyv/skope) skill. Run it with the run-skope-skill skill if you have
it; if not, the bold steps are the procedure, and `{names}` are params set in the skope block below.*

```skope
format: 1
params:
  base: origin/main   # a branch or commit hash to compare with (skope params allow no ~ or ^)
limits:
  run_timeout: 5m
```

Split the branch's diff into hunks and have [jev-semgrep](https://github.com/uehaj/jev-semgrep)
judge each one against a few risks. Code decides from the counts: any risky hunk
means a careful review of those hunks first, behaviour changes alone mean a
normal review, and formatting, renames or docs alone need none. This finds
where to look. It doesn't prove a hunk is safe, and it never replaces reading
the risky ones.

Every hunk is sent to jev-semgrep's endpoint (Jev, via TypeSafe or OpenRouter),
and [Careful review] sends the risky hunks a second time, to get their list
rather than just their count. Don't run it on code that mustn't leave the
machine. It needs `git` and jev-semgrep's `semgrep` with an API key set
(`SEMGREP_API_KEY`).

## Scan
Split the diff into hunks, leaving out docs, then count the hunks that match each risk.

- **check** `command -v semgrep > /dev/null && semgrep --help 2>&1 | grep -q "grep by meaning"` succeeds · else [No semgrep]
- **check** `git rev-parse -q --verify {base} > /dev/null` succeeds · else [No base]
- **run** `mkdir -p -m 700 "$HOME/.cache/skope-skills" && umask 077 && git -c diff.noprefix=false -c diff.mnemonicPrefix=false diff {base}...HEAD > "$HOME/.cache/skope-skills/rf-diff.txt" && awk '/^diff --git/ { if (r != "") printf "%s%c", r, 0; r = ""; h = 1; next } h && /^--- / { m = substr($0, 7); sub(/\t$/, "", m); next } h && /^\+\+\+ / { f = ($0 == "+++ /dev/null") ? m : substr($0, 7); sub(/\t$/, "", f); d = (f ~ /\.(md|markdown|rst|txt)$/); next } /^@@/ { if (r != "") printf "%s%c", r, 0; r = ""; h = 0; if (d) next; match($0, /\+[0-9]+/); r = f ":" substr($0, RSTART + 1, RLENGTH - 1) "\n" $0 "\n"; next } h { next } r != "" { r = r $0 "\n" } END { if (r != "") printf "%s%c", r, 0 }' "$HOME/.cache/skope-skills/rf-diff.txt" > "$HOME/.cache/skope-skills/rf-hunks.bin" && tr -cd '\000' < "$HOME/.cache/skope-skills/rf-hunks.bin" | wc -c` as hunks
- **check** {hunks} == 0 → [No code changes]
- **run** `semgrep -z -c -e "removes, loosens or skips a check, validation, assertion or test" "$HOME/.cache/skope-skills/rf-hunks.bin" || true` as weakens
- **run** `semgrep -z -c -e "changes how errors, failures, timeouts or retries are handled" "$HOME/.cache/skope-skills/rf-hunks.bin" || true` as errors
- **run** `semgrep -z -c -e "adds or changes a network request, file-system access, or shell or subprocess call" "$HOME/.cache/skope-skills/rf-hunks.bin" || true` as io
- **run** `semgrep -z -c -e "touches authentication, authorisation, secrets, credentials or permissions" "$HOME/.cache/skope-skills/rf-hunks.bin" || true` as security
- **run** `semgrep -z -c -e "changes what the code does, rather than only renaming, formatting, comments or documentation" "$HOME/.cache/skope-skills/rf-hunks.bin" || true` as behaviour
- **check** {security} > 0 → [Careful review]
- **check** {weakens} > 0 → [Careful review]
- **check** {errors} > 0 → [Careful review]
- **check** {io} > 0 → [Careful review]
- **check** {behaviour} == 0 → [Cosmetic only]
- **then** [Normal review]

## Careful review
At least one hunk weakens a check, changes error handling, adds I/O, or touches security.

- **run** `semgrep -z -e "removes, loosens or skips a check, validation, assertion or test" -e "changes how errors, failures, timeouts or retries are handled" -e "adds or changes a network request, file-system access, or shell or subprocess call" -e "touches authentication, authorisation, secrets, credentials or permissions" "$HOME/.cache/skope-skills/rf-hunks.bin" | tr '\000' '\n' | grep -E '^[^-+@ ].*:[0-9]+$' | head -n 40` as risky_hunks
- **hand off**

`risky_hunks` lists the `path:line` of each risky hunk (the new file's line).
Read those hunks first and closely, with a few lines of context, before the
rest of the diff. `security`, `weakens`, `errors` and `io` count each kind. A
removed check or a new shell call needs a stated reason in the PR.

## Normal review
The branch changes behaviour, but no hunk matched a risk.

- **run** `semgrep -z -e "changes what the code does, rather than only renaming, formatting, comments or documentation" "$HOME/.cache/skope-skills/rf-hunks.bin" | tr '\000' '\n' | grep -E '^[^-+@ ].*:[0-9]+$' | head -n 40` as changed_hunks
- **hand off**

`changed_hunks` lists where behaviour changes. Review those. The rest of the
diff is renames, formatting or docs.

## Cosmetic only
No hunk changes behaviour: only renames, formatting, comments or docs.

- **stop**

## No code changes
The branch changes nothing, or only docs (Markdown, reStructuredText or text files), which aren't judged.

- **stop**

## No base
`base` doesn't exist locally, so there's nothing to diff against.

- **hand off**

Run `git fetch origin` to fetch it, or pass a base that's already local with
`--param base=<branch>`.

## No semgrep
jev-semgrep's `semgrep` isn't on the PATH. The Semgrep static analyser has the same command name and doesn't count.

- **hand off**

Install it (`npm install -g @uehaj/semgrep`) and set `SEMGREP_API_KEY`. For
OpenRouter, see the jev-semgrep skill's Setup section for the endpoint and
model settings. Then run again.
