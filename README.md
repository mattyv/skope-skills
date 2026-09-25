# skope-skills

Agent skills for everyday coding chores that a coding agent otherwise spends
many turns and tokens on: waiting on CI, reading logs, comparing test runs,
cutting releases, and searching code, diffs and history.

Most are [skope](https://github.com/mattyv/skope) skills. A skope skill is a
Markdown runbook that an agent can read and follow, and that `skope` can run:
the fixed steps run as commands, the one judgement call goes to a fast
classifier, and anything unclear is handed back to the agent with just the
evidence that matters. That turns a dozen agent turns into one, and a
2,000-line CI log into the 40 lines that explain the failure.

## skope skills

| Skill | What it does | Asks the model |
|---|---|---|
| [ship-pr](skills/ship-pr/SKILL.md) | Pushes the branch, opens a PR if there isn't one, waits for CI, reruns a flaky failure once, merges when GitHub says it's clean | Is a CI failure flaky, or does the change need a fix? |
| [ci-failure-triage](skills/ci-failure-triage/SKILL.md) | Finds why the branch's latest run failed and hands over only the relevant log lines; reruns a flaky failure once | Lint, type, test, build, flaky, or something else? |
| [test-diff-vs-main](skills/test-diff-vs-main/SKILL.md) | Runs the suite on the branch and on the base branch and reports only the failures the branch added | Nothing |
| [cut-release](skills/cut-release/SKILL.md) | Checks version, tag and CI, then tags, pushes, watches the release workflow and confirms the release has files | Nothing |
| [review-focus](skills/review-focus/SKILL.md) | Splits the branch's code changes into hunks and hands over only those that weaken a check, change error handling, add I/O or touch security; stops if the change is cosmetic or docs only | Nothing directly: jev-semgrep judges each hunk, and code decides from the counts |

They act on the current branch and use `git`. All but review-focus use `gh`,
and review-focus uses jev-semgrep (below).

## Agent skills (search by meaning)

These are ordinary agent skills, not skope skills, because their input is a
free-text description. They use [jev-semgrep](https://github.com/uehaj/jev-semgrep),
a grep that judges each line or record by meaning with Jev.

| Skill | What it does |
|---|---|
| [jev-semgrep](skills/jev-semgrep/SKILL.md) | Finds code by behaviour, diff hunks or commits that change something, doc sections about a topic, or log lines that mean something, and says when grep or reading is cheaper. Its `scripts/records.py` splits code, diffs and Markdown into records. |
| [when-did-this-change](skills/when-did-this-change/SKILL.md) | Finds the commit that introduced, changed or removed a behaviour, from messages and patches. It's cheaper than `git bisect` when you know what changed but not when. |

## What leaves your machine

Anything a model judges is sent to it: review-focus sends each code hunk, the
jev-semgrep skills send each record they search, and the skope skills that ask
send the evidence the question names. Jev runs at TypeSafe, directly or through
OpenRouter. Don't use these on code or logs that mustn't leave the machine;
the jev-semgrep skill tells the agent to ask first for anything that isn't
public.

## Install

1. **skope** 0.1.0-beta.2 or later. This also installs the `run-skope-skill`
   agent skill, which tells an agent how to run a skope skill:

   ```console
   $ curl -fsSL https://github.com/mattyv/skope/releases/download/v0.1.0-beta.2/install.sh | SKOPE_VERSION=0.1.0-beta.2 sh
   ```

2. **jev-semgrep**, for review-focus and the search skills:
   `npm install -g @uehaj/semgrep`, plus a key. The
   [jev-semgrep skill](skills/jev-semgrep/SKILL.md#setup) has the OpenRouter
   settings.
3. **The skills:** clone this repo and link the ones you want into your agent's
   skills directory, so a `git pull` updates them:

   ```console
   $ ln -s "$PWD/skills/ship-pr" ~/.claude/skills/ship-pr     # Claude Code
   $ ln -s "$PWD/skills/ship-pr" ~/.codex/skills/ship-pr      # Codex
   ```

Then ask the agent to ship the PR, triage CI or find when something changed.
You can also run a skope skill yourself, with a dry run first, which runs
only the read-only steps:

```console
$ skope ~/.claude/skills/ship-pr/SKILL.md --dry-run
$ skope ~/.claude/skills/cut-release/SKILL.md --apply --param version=1.2.0
```

The skope skills that ask the model need a skope backend (Jev, directly or
through OpenRouter); see the skope README. Without one, an agent can still
follow them by hand.

## Tests

CI runs, with no API key:

- `skope --lint` and `skope --test` on every skope skill. Each has a `tests.yaml`
  with a scenario for every way it can end, with faked command results.
- `python3 -m unittest discover tests`, for the real commands:
  - `records.py`'s splitting, and review-focus's own hunk splitter, taken from
    its `SKILL.md`;
  - the git record format when-did-this-change relies on;
  - test-diff-vs-main run end to end on a throwaway repo.

By hand, because they call the model: `skope SKILL.md --test --live` checks a
skope skill's questions, and [`evals/known-answers.sh`](evals/known-answers.sh)
checks review-focus and when-did-this-change against real commits whose right
answer is known.

## Contributing

A new skill or a change to one needs:

- **Tests first.** A skope skill needs a scenario in its `tests.yaml` for every
  ending: each option of each question, the false alarm, a failing command, an
  unsure answer, and "none of these fit". Real command pipelines need a unit
  test in `tests/`.
- **Live results for any question.** Run `skope SKILL.md --test --live --runs 5`,
  or `evals/known-answers.sh` for the meaning-search skills, and put the report
  in the pull request. When the model gets one wrong, improve the evidence or
  wording, not the `sure` bar.
- **Nothing irreversible without a check in front of it**, and nothing that
  can't be taken back (moving a tag, deleting data) at all: hand that to a
  person.
- **Generic commands only.** No company hostnames, credentials or internal
  names.

`write-skope-skill`, installed with skope, walks an agent through writing a
skope skill test-first.

## License

Licensed under either of the [Apache License, Version 2.0](LICENSE-APACHE)
or the [MIT license](LICENSE-MIT), at your option. [`NOTICE`](NOTICE) credits
jev-semgrep, whose guidance skills/jev-semgrep/SKILL.md adapts.
