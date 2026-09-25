---
name: ship-pr
description: Ship the current branch as a GitHub pull request - push, open the PR if there isn't one, wait for CI, rerun a flaky failure once, and merge when it merges cleanly. Use when a change is committed and ready to go in.
---

# Ship a pull request

*A [skope](https://github.com/mattyv/skope) skill. Run it with the run-skope-skill skill if you have
it; if not, the bold steps are the procedure, and `{names}` are params set in the skope block below.*

```skope
format: 1
params:
  base: main            # the branch the pull request merges into
  merge_method: merge   # merge, squash or rebase
limits:
  run_timeout: 45m      # waiting on CI is the slow part
  do_timeout: 5m
```

Ship what's committed on the current branch, and nothing else. Never force-push,
never merge a pull request GitHub doesn't call clean, and never rerun CI more
than once: a second failure is a real one. Needs `git` and an authenticated `gh`.

## Preflight
Check the branch is one to ship: not detached, not the base branch, and nothing left uncommitted.

- **check** `test -n "$(git branch --show-current)"` succeeds · else [On base]
- **check** `test "$(git branch --show-current)" != {base}` succeeds · else [On base]
- **check** `git diff --quiet && git diff --cached --quiet` succeeds · else [Uncommitted]
- **do** `git push -u origin HEAD`
- **check** `gh pr view --json number > /dev/null 2>&1` succeeds → [Checks]
- **do** `gh pr create --fill --base {base}`
- **then** [Checks]

## Checks
Wait for every CI check on the pull request. Checks can take a few seconds to
register after the pull request is created or a push lands, so first wait for
them to appear: up to 6 tries, 10 seconds apart (about a minute), before
giving up.

- **check** `i=0; while [ "$i" -lt 6 ]; do gh pr checks 2>&1 | grep -q "no checks reported" || exit 0; i=$((i + 1)); sleep 10; done; exit 1` succeeds · else [No checks]
- **check** `gh pr checks --watch --fail-fast > /dev/null 2>&1` succeeds → [Merge] · else [CI failed]

## Merge
CI passed. Merge only when GitHub says the pull request merges cleanly.

- **check** `test "$(gh pr view --json mergeStateStatus -q .mergeStateStatus)" = CLEAN` succeeds · else [Not mergeable]
- **do** `gh pr merge --{merge_method}`
- **stop**

## CI failed
A check failed. Decide from the checks and the failed job's log whether the change caused it.

- **run** `gh pr checks 2>&1 | head -n 40` as checks
- **run** `gh run list --commit "$(git rev-parse HEAD)" --status failure --limit 1 --json databaseId -q '.[0].databaseId' | grep -x '[0-9][0-9]*' | xargs -n1 gh run view --log-failed 2>&1 | tail -n 120` as failed_log
- **ask** Given {checks} and {failed_log}, what should happen next? · sure 85%
  - [Rerun]
  - [Needs a fix]

## Rerun
The failure looks flaky or infrastructural, not caused by the change: a network or registry timeout, a cancelled or lost runner, a rate limit, a service that didn't start.

- **do** `gh run list --commit "$(git rev-parse HEAD)" --status failure --limit 1 --json databaseId -q '.[0].databaseId' | grep -x '[0-9][0-9]*' | xargs -n1 gh run rerun --failed`
- **check** `sleep 15 && gh pr checks --watch --fail-fast > /dev/null 2>&1` succeeds → [Merge] · else [Needs a fix]

## Needs a fix
The failure comes from the change, or a rerun failed again: a failing test, a type, lint or build error, or anything that isn't clearly flaky.

- **hand off**

Read `failed_log` in the handoff record: it's the tail of the failed job's
log. Fix the cause, commit, and run this skill again. Don't rerun CI hoping it
passes.

## No checks
No CI check has appeared on the pull request within about a minute of waiting.

- **hand off**

The repository may have no CI checks configured, or they never started (a
missing workflow trigger, a paused workflow). If that's expected, merge by
hand once you've confirmed it's safe. Otherwise fix the workflow trigger and
run this skill again.

## On base
The current branch is the base branch, or there's no current branch to push (a detached `HEAD`), so there's nothing to ship as a pull request.

- **hand off**

Create a branch for the change (`git switch -c <name>`), then run this skill
again. Don't push to the base branch.

## Uncommitted
There are uncommitted changes, which wouldn't be in the pull request.

- **hand off**

Commit what belongs in this change and stash or discard the rest, then run
this skill again.

## Not mergeable
CI passed, but GitHub doesn't call the pull request clean: it's behind the base branch, has conflicts, or needs a review or a required check.

- **hand off**

Check `gh pr view --json mergeStateStatus,reviewDecision`. If it's behind or
conflicting, rebase on the base branch, fix conflicts, push and run this skill
again. If it needs a review, ask for one. Never bypass branch protection.
