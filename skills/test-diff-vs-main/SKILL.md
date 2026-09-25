---
name: test-diff-vs-main
description: Tell which failing tests a branch introduced by running the suite on the branch and on the base branch and comparing the failures by name. Use before shipping, or when a test suite already has failures and you need to know whether any are yours.
---

# Test diff against the base branch

*A [skope](https://github.com/mattyv/skope) skill. Run it with the run-skope-skill skill if you have
it; if not, the bold steps are the procedure, and `{names}` are params set in the skope block below.*

```skope
format: 1
params:
  base: origin/main                       # a branch or commit hash, fetched first (no ~ or ^)
  failing_script: scripts/failing-tests.sh  # prints failing test names for a directory
limits:
  run_timeout: 30m                        # two full test runs
```

Answer one question cheaply: does this branch fail any test the base branch
doesn't? The result is three numbers and, only if there are new failures, their
names. Nothing in the working tree changes: `origin` is fetched, then the base
is exported to a scratch directory, not checked out. With no `origin`, pass a
local branch: `--param base=main`. Two runs at once share that scratch directory, so run one at a
time.

## Compare
Run the suite on the working tree and on the base branch, and compare the failing test names.

- **check** `test -x {failing_script}` succeeds · else [No script]
- **run** `git fetch -q origin 2>/dev/null || true`
- **run** `mkdir -p -m 700 "$HOME/.cache/skope-skills" && umask 077 && {failing_script} . > "$HOME/.cache/skope-skills/tdm-head-raw.txt" && sort -u "$HOME/.cache/skope-skills/tdm-head-raw.txt" > "$HOME/.cache/skope-skills/tdm-head.txt" && wc -l < "$HOME/.cache/skope-skills/tdm-head.txt"` as head_failing
- **run** `mkdir -p -m 700 "$HOME/.cache/skope-skills" && umask 077 && rm -rf "$HOME/.cache/skope-skills/tdm-base" && mkdir -p "$HOME/.cache/skope-skills/tdm-base" && git archive -o "$HOME/.cache/skope-skills/tdm-base.tar" {base} && tar -x -C "$HOME/.cache/skope-skills/tdm-base" -f "$HOME/.cache/skope-skills/tdm-base.tar" && {failing_script} "$HOME/.cache/skope-skills/tdm-base" > "$HOME/.cache/skope-skills/tdm-base-raw.txt" && sort -u "$HOME/.cache/skope-skills/tdm-base-raw.txt" > "$HOME/.cache/skope-skills/tdm-base.txt" && wc -l < "$HOME/.cache/skope-skills/tdm-base.txt"` as base_failing
- **run** `comm -13 "$HOME/.cache/skope-skills/tdm-base.txt" "$HOME/.cache/skope-skills/tdm-head.txt" | wc -l` as new
- **run** `comm -23 "$HOME/.cache/skope-skills/tdm-base.txt" "$HOME/.cache/skope-skills/tdm-head.txt" | wc -l` as fixed
- **run** `comm -13 "$HOME/.cache/skope-skills/tdm-base.txt" "$HOME/.cache/skope-skills/tdm-head.txt" | head -n 50` as new_tests
- **check** {new} == 0 → [No new failures]
- **then** [New failures]

## No new failures
Every test that fails here fails on the base branch too, so nothing is new.

- **stop**

## New failures
Some tests fail on this branch but pass on the base branch.

- **hand off**

`new_tests` in the handoff record lists them (the first 50), and `new`, `fixed`,
`head_failing` and `base_failing` give the counts. Run just those tests, fix
them, and run this skill again. Failures that also happen on the base branch
aren't yours to fix here.

## No script
There's no executable script at `failing_script`, so the suite can't be compared.

- **hand off**

Add one. It takes a directory, runs the tests there, and prints each failing
test's name on its own line. Its contract: exit 0 whenever the tests ran, even
if some failed, and non-zero only when the runner itself couldn't run - a
collection error, a config error, or no tests collected. The base branch is
exported without dependencies, so link them in first. For vitest:

```sh
#!/bin/sh
cd "$1" || exit 1
[ -e node_modules ] || ln -s "$OLDPWD/node_modules" node_modules
mkdir -p -m 700 "$HOME/.cache/skope-skills" && umask 077
rm -f "$HOME/.cache/skope-skills/vitest.json"
npx vitest run --reporter=json --outputFile="$HOME/.cache/skope-skills/vitest.json" > /dev/null 2>&1
[ -s "$HOME/.cache/skope-skills/vitest.json" ] || exit 1   # no JSON means the runner didn't finish
jq -r '(.testResults[].assertionResults[] | select(.status == "failed") | .fullName),
       (.testResults[] | select(.status == "failed" and (.assertionResults | length) == 0) | .name)' \
  "$HOME/.cache/skope-skills/vitest.json"
```

For pytest:

```sh
#!/bin/sh
cd "$1" || exit 1
out=$(python -m pytest -q -rfE 2>&1)
code=$?
echo "$out" | sed -nE 's/^(FAILED|ERROR) ([^ ]*).*/\2/p'
case $code in
  0|1) exit 0 ;;   # 0: all passed, 1: some tests failed - the runner still ran
  *) exit 1 ;;     # any other pytest exit code means it couldn't run properly
esac
```
