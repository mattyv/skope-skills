---
name: jev-semgrep
description: Search by meaning with jev-semgrep (the `semgrep` command from @uehaj/semgrep, not the Semgrep static analyser) - find code by behaviour, the diff hunks or commits that change something, doc sections about a topic, or log lines that mean something - when grep can't guess the words and reading everything would cost more. Use for "find where X is handled", "which commit started doing X", "which hunks in this diff weaken a check", "which docs describe X", "which log lines show Y".
---

# jev-semgrep: search by meaning

`semgrep` asks Jev, for every line or record, "does this mean X?" and keeps the
ones above a calibrated threshold. It's from https://github.com/uehaj/jev-semgrep
(MIT), with guidance adapted from its own Claude Code skill.

## Setup

Needs `semgrep` from `npm install -g @uehaj/semgrep` (Node 20.16+) and a Jev API
key in `SEMGREP_API_KEY`, or in `~/.config/semgrep/.env`, which is read when the
variable isn't set. The key comes from TypeSafe directly, or from OpenRouter with
these two settings in the same file:

```sh
SEMGREP_URL=https://openrouter.ai/api/v1/systemone
SEMGREP_MODEL=typesafe/jev-1.13-20260917
```

`semgrep --help` should start with "grep by meaning". If it doesn't, the
command on PATH is the Semgrep static analyser, which has the same name. If
there's no key, don't hunt for one: tell the user what to set.

## Everything searched leaves the machine

Every line or record goes to the configured endpoint (TypeSafe, or OpenRouter then TypeSafe). **Before searching company
or proprietary code, logs or docs (anything that isn't public or the user's own
open-source work), ask the user first**, and never search files that may hold
secrets (`.env`, keys, credentials, customer data). Public repos are fine.

## Use it only when it's cheaper

It's worth it when all three hold. Otherwise read the file or use grep, and
say in one line why.

- **The hits are the answer.** After seeing them, you won't need to read the
  whole target. Summarising or understanding a whole codebase isn't this; you'd
  read everything anyway and pay twice.
- **The words can't be guessed.** If `grep -iE 'retry|backoff'` would find it,
  grep is as good and free. Meaning search is for behaviour, negation ("not
  X"), paraphrase and mixed languages.
- **The target is bigger than about 50 lines.** Below that, reading is cheaper.

After a hit, read around it with `-C N` or `sed -n 'A,Bp'`, not the whole file.

## Lines or records

The unit is a line by default: right for logs and one-line-per-item text. For
code, diffs, commits and docs, one line has no meaning on its own, so send
**records** with `-z`. Make them with `scripts/records.py` beside this file:

```sh
R=<this skill's directory>/scripts/records.py

# Code by behaviour. Python splits by function; other files into overlapping 60-line windows
git ls-files -z '*.ts' '*.py' | xargs -0 python3 $R code | semgrep -z -p -e "retries a request after a timeout" | tr '\0' '\n'

# Diff hunks that deserve a careful review
git diff main...HEAD | python3 $R hunks | semgrep -z -e "removes or weakens a check or validation" | tr '\0' '\n'

# Commits that changed a behaviour, with their patches. Start each record with %x00, and not
# git log -z, which with -p splits a commit's header from its diff. See when-did-this-change.
git log -p --no-merges -200 --format='%x00%h %s%n%b' | semgrep -z -e "stops retrying on timeout" | tr '\0' '\n'

# Doc sections to update after a change
python3 $R sections README.md docs/*.md | semgrep -z -l -e "describes how fake keys are merged"
```

Each record starts with `path:line` (hunks: the new-file line), so a hit points
at where to read. `-c` counts matching records, and `-l` lists files only.

## Writing the query

- Write the meaning in English: it's the most accurate, whatever the user
  wrote in.
- One condition per term: `-e A -e B` (A or B), `-e A -a B` (A and B), and
  `-e A -v B` (A but not B).
- Put a cheap regex first to cut cost: `-e '/timeout|retry/i' -a "gives up after too many attempts"`.
  Only records matching the regex are sent.
- Describe behaviour, not names: "checks whether a process group still has a
  running process", not "groupAlive".

## Reading results

- Wrong hits mixed in: add `-p` to see probabilities, then retry with
  `--level strict`.
- Nothing found: retry with `--level loose`. If still nothing, say so, with
  the query and level used.
- Exit status 2 is an error: show stderr.
- Report hits as `path:line` with a one-line reason each, then read only
  those spots.
