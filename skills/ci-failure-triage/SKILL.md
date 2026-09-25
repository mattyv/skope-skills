---
name: ci-failure-triage
description: Work out why the current branch's latest GitHub Actions run failed, and hand over only the log lines that matter - lint, type, test or build errors - or rerun it once if it's flaky. Use when CI fails and before reading a full CI log.
---

# CI failure triage

*A [skope](https://github.com/mattyv/skope) skill. Run it with the run-skope-skill skill if you have
it; if not, the bold steps are the procedure, and `{names}` are params set in the skope block below.*

```skope
format: 1
limits:
  run_timeout: 2m
  do_timeout: 2m
```

A CI log is thousands of lines; the cause is usually a few. Classify the
failure, then hand over only the lines for that kind of failure. The full log
stays in `/tmp/skope-ci-log.txt` if the excerpt isn't enough. The only change
this skill makes is one rerun of the failed jobs, and only for a flaky failure.
Needs `git` and an authenticated `gh`.

## Latest run
Classify why the branch's latest run failed, from the names of the failed jobs and the end of their log.

- **check** `gh run list --branch "$(git branch --show-current)" --limit 1 --json conclusion -q '.[0].conclusion' | grep -qx failure` succeeds · else [Not failing]
- **run** `gh run list --branch "$(git branch --show-current)" --limit 1 --json databaseId -q '.[0].databaseId' | xargs -n1 gh run view --json jobs -q '.jobs[] | select(.conclusion == "failure") | .name'` as failed_jobs
- **run** `gh run list --branch "$(git branch --show-current)" --limit 1 --json databaseId -q '.[0].databaseId' | xargs -n1 gh run view --log-failed > /tmp/skope-ci-log.txt 2>&1 && tail -n 150 /tmp/skope-ci-log.txt` as failed_log
- **ask** Given {failed_jobs} and {failed_log}, what kind of failure is this? · sure 80%
  - [Lint or format]
  - [Type error]
  - [Test failure]
  - [Build or dependency]
  - [Flaky or infrastructure]
  - [Investigate]

## Not failing
The latest run on this branch didn't fail: it passed, is still running, or there's no run.

- **stop**

## Lint or format
A linter or formatter rejected the code: style rules, unused variables, formatting differences.

- **run** `grep -i -E "error|warning|✖|×|would reformat|formatted" /tmp/skope-ci-log.txt | head -n 40` as lint_errors
- **hand off**

`lint_errors` holds the lint lines. Fix them locally with the project's lint
or format command (often it can fix them itself), then push.

## Type error
The type checker or compiler rejected the code: a type mismatch, a missing property, a wrong signature.

- **run** `grep -E "error TS[0-9]+|error\[E[0-9]+\]|: error:|error: |Found [0-9]+ error" /tmp/skope-ci-log.txt | head -n 40` as type_errors
- **hand off**

`type_errors` holds the compiler errors. Fix the first one first: later ones
often follow from it.

## Test failure
The code built, but one or more tests failed: an assertion, an exception in a test, a snapshot mismatch.

- **run** `grep -n -E "FAIL|FAILED|✗|×|AssertionError|Error:|panicked|expected" /tmp/skope-ci-log.txt | head -n 60` as test_errors
- **hand off**

`test_errors` holds the failing tests and their assertions. Run just those
tests locally to reproduce, then fix the code or the test, whichever is wrong.

## Build or dependency
Install or build failed before any test ran: a dependency that won't resolve, a missing package, a lockfile out of date, a compile step that broke.

- **run** `grep -i -E "ERR!|error:|not found|could not resolve|no matching|failed to build|lockfile|ERESOLVE" /tmp/skope-ci-log.txt | head -n 40` as build_errors
- **hand off**

`build_errors` holds the install and build errors. Reproduce with a clean
install locally. Check the lockfile is committed and matches the manifest.

## Flaky or infrastructure
Nothing in the change caused it: a network or registry timeout, a cancelled or lost runner, a rate limit, a service container that didn't start.

- **do** `gh run list --branch "$(git branch --show-current)" --limit 1 --json databaseId -q '.[0].databaseId' | xargs -n1 gh run rerun --failed`
- **stop**

## Investigate
None of the kinds above fits: a deploy or release step, a permission, secret or approval problem, a workflow file error, or a log that shows more than one problem.

- **hand off**

Read `failed_log` in the handoff record, then the full log in
`/tmp/skope-ci-log.txt` if needed.
