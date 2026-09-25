# skope-skills

[skope](https://github.com/mattyv/skope) skills for everyday coding chores
that a coding agent otherwise spends many turns on: waiting on CI, reading
logs, comparing test runs, cutting releases.

A skope skill is a Markdown runbook. An agent can read it and follow it, and
`skope` can run it: the fixed steps run as commands, the one judgement call
goes to a fast classifier, and anything unclear is handed back to the agent
with just the evidence that matters. That turns a dozen agent turns into one,
and a 2,000-line CI log into the 40 lines that explain the failure.

| Skill | What it does | Asks the model |
|---|---|---|
| [ship-pr](skills/ship-pr/SKILL.md) | Pushes the branch, opens a PR if there isn't one, waits for CI, reruns a flaky failure once, merges when GitHub says it's clean | Is a CI failure flaky, or does the change need a fix? |
| [ci-failure-triage](skills/ci-failure-triage/SKILL.md) | Finds why the branch's latest run failed and hands over only the relevant log lines; reruns a flaky failure once | Lint, type, test, build, flaky, or something else? |
| [test-diff-vs-main](skills/test-diff-vs-main/SKILL.md) | Runs the suite on the branch and on the base branch and reports only the failures the branch added | Nothing |
| [cut-release](skills/cut-release/SKILL.md) | Checks version, tag and CI, then tags, pushes, watches the release workflow and confirms the release has files | Nothing |

All four use `git` and `gh`, and act on the current branch.

## Use

Install skope (0.1.0-beta.2 or later), which also installs the
`run-skope-skill` agent skill that tells an agent how to run these:

```console
$ curl -fsSL https://github.com/mattyv/skope/releases/download/v0.1.0-beta.2/install.sh | SKOPE_VERSION=0.1.0-beta.2 sh
```

Copy the skills you want into your agent's skills directory, for example
`~/.claude/skills/`. Then ask the agent to ship the PR or triage CI, or run a
skill yourself. Dry-run first: a dry run runs only the read-only steps.

```console
$ skope ~/.claude/skills/ship-pr/SKILL.md --dry-run
$ skope ~/.claude/skills/ship-pr/SKILL.md --apply
$ skope ~/.claude/skills/cut-release/SKILL.md --apply --param version=1.2.0
```

The skills that ask the model need a skope backend (Jev, directly or through
OpenRouter); see the skope README. Without one, an agent can still follow
them by hand.

## Contributing

A new skill or a change to one needs:

- **Tests first.** A `tests.yaml` beside the skill with a scenario for every
  ending: each option of each question, the false alarm, a failing command,
  an unsure answer, and "none of these fit". CI runs `skope --lint` and
  `skope --test` on every skill.
- **Live results for any question.** Run `skope SKILL.md --test --live --runs 5`
  and put the report in the pull request. Improve the evidence or wording,
  not the `sure` bar, when the model gets one wrong.
- **Nothing irreversible without a check in front of it**, and nothing that
  can't be taken back (moving a tag, deleting data) at all: hand that to a
  person.
- **Generic commands only.** No company hostnames, credentials or internal
  names.

`write-skope-skill`, installed with skope, walks an agent through writing one
test-first.

## License

Licensed under either of the [Apache License, Version 2.0](LICENSE-APACHE)
or the [MIT license](LICENSE-MIT), at your option.
