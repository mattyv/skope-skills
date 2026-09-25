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
  base: main                              # the branch to compare with
  failing_script: scripts/failing-tests.sh  # prints failing test names for a directory
limits:
  run_timeout: 30m                        # two full test runs
```

Answer one question cheaply: does this branch fail any test the base branch
doesn't? The result is three numbers and, only if there are new failures, their
names. Nothing is changed: the base branch is exported to a scratch directory,
not checked out. Two runs at once share that scratch directory, so run one at a
time.

## Compare
Run the suite on the working tree and on the base branch, and compare the failing test names.

- **check** `test -x {failing_script}` succeeds · else [No script]
- **run** `{failing_script} . | sort -u > /tmp/skope-tdm-head.txt && wc -l < /tmp/skope-tdm-head.txt` as head_failing
- **run** `rm -rf /tmp/skope-tdm-base && mkdir -p /tmp/skope-tdm-base && git archive {base} | tar -x -C /tmp/skope-tdm-base && {failing_script} /tmp/skope-tdm-base | sort -u > /tmp/skope-tdm-base.txt && wc -l < /tmp/skope-tdm-base.txt` as base_failing
- **run** `comm -13 /tmp/skope-tdm-base.txt /tmp/skope-tdm-head.txt | wc -l` as new
- **run** `comm -23 /tmp/skope-tdm-base.txt /tmp/skope-tdm-head.txt | wc -l` as fixed
- **run** `comm -13 /tmp/skope-tdm-base.txt /tmp/skope-tdm-head.txt | head -n 50` as new_tests
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

Add one. It takes a directory, runs the tests there, prints each failing test's
name on its own line, and exits 0 even when tests fail. The base branch is
exported without dependencies, so link them in first. For vitest:

```sh
#!/bin/sh
cd "$1" || exit 1
[ -e node_modules ] || ln -s "$OLDPWD/node_modules" node_modules
npx vitest run --reporter=json --outputFile=/tmp/skope-vitest.json > /dev/null 2>&1
jq -r '.testResults[].assertionResults[] | select(.status == "failed") | .fullName' /tmp/skope-vitest.json
```

For pytest:

```sh
#!/bin/sh
cd "$1" || exit 1
python -m pytest -q -rf 2>/dev/null | sed -n 's/^FAILED \([^ ]*\).*/\1/p'
```
