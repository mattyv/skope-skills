---
name: cut-release
description: Cut a tagged release from the tip of the base branch - check the version, the tag and CI, then tag, push, watch the release workflow and confirm the release has its files. Use when a version bump is merged and it's time to release.
---

# Cut a release

*A [skope](https://github.com/mattyv/skope) skill. Run it with the run-skope-skill skill if you have
it; if not, the bold steps are the procedure, and `{names}` are params set in the skope block below.*

```skope
format: 1
params:
  version: 0.0.0              # set it: --param version=1.2.0
  tag_prefix: v
  base: main
  version_file: package.json  # must mention the version
  ci_workflow: ci.yml         # must have passed on the commit being tagged
  release_workflow: release.yml
limits:
  run_timeout: 45m            # watching the release workflow
  do_timeout: 2m
```

Release exactly the tip of the base branch, once CI has passed on it. Tag
only after every check passes. Once a tag is pushed, never move or delete it
without a person deciding: that's the one step here that can't be taken back
safely. Needs `git` and an authenticated `gh`.

## Preflight
Check everything the release depends on before creating the tag.

- **check** `test {version} != 0.0.0` succeeds · else [No version]
- **check** `git fetch -q origin {base} --tags && test "$(git rev-parse HEAD)" = "$(git rev-parse origin/{base})"` succeeds · else [Not at base]
- **check** `grep -qF {version} {version_file}` succeeds · else [Version mismatch]
- **check** `git rev-parse -q --verify refs/tags/{tag_prefix}{version}` succeeds → [Tag exists]
- **check** `test "$(gh run list --commit "$(git rev-parse HEAD)" --workflow {ci_workflow} --limit 1 --json conclusion -q '.[0].conclusion')" = success` succeeds · else [CI not green]
- **do** `git tag -a {tag_prefix}{version} -m {tag_prefix}{version}`
- **do** `git push origin {tag_prefix}{version}`
- **then** [Release run]

## Release run
Wait for the release workflow the tag started.

- **check** `sleep 20 && gh run list --workflow {release_workflow} --branch {tag_prefix}{version} --limit 1 --json databaseId -q '.[0].databaseId' | xargs -n1 gh run watch --exit-status > /dev/null` succeeds → [Published] · else [Release failed]

## Published
The workflow passed. Confirm the release exists and has files attached.

- **check** `gh release view {tag_prefix}{version} --json assets -q '.assets | length' | grep -qv '^0$'` succeeds → stop · else [Release failed]

## Release failed
The release workflow failed, or finished without a release that has files.

- **run** `gh run list --workflow {release_workflow} --branch {tag_prefix}{version} --limit 1 --json databaseId -q '.[0].databaseId' | xargs -n1 gh run view --log-failed 2>&1 | tail -n 80` as failed_log
- **run** `gh release view {tag_prefix}{version} > /dev/null 2>&1 && echo published || echo not published` as published
- **hand off**

`failed_log` is the end of the failed jobs' log, and `published` says whether a
GitHub release exists for the tag. The tag is pushed, so a person decides the
next step:

- **Nothing published:** fix the cause on the base branch. Then either move
  the tag to the fixed commit (delete the remote tag, re-tag, push) or release
  the next version. Rerunning the workflow alone builds the tagged commit
  again, which still has the bug.
- **Something published:** a release, a package or an image. Never move the
  tag. Release the next version with the fix.

## No version
The `version` param wasn't set.

- **hand off**

Run again with `--param version=<the version>`, matching `version_file`.

## Not at base
The current commit isn't the tip of the base branch on origin, so the release wouldn't be what's merged.

- **hand off**

Switch to the base branch and pull (`git switch {base} && git pull`), then run
again. If the version bump isn't merged yet, merge it first.

## Version mismatch
The version file doesn't mention the version being released.

- **hand off**

Bump the version in `version_file` in a pull request, merge it, and run again.

## Tag exists
A tag for this version already exists.

- **hand off**

Check `gh release view {tag_prefix}{version}`. If the version is already
released, release the next one. If the tag exists without a release, a person
decides whether to rerun the release workflow for it.

## CI not green
CI hasn't passed on the commit to be tagged: it failed, is still running, or never ran.

- **hand off**

Wait for CI on the base branch to pass, or fix it, then run again. Don't tag a
commit CI hasn't passed.
