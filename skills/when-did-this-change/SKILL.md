---
name: when-did-this-change
description: Find the commit that introduced, changed or removed a behaviour by searching commit messages and patches by meaning with jev-semgrep - cheaper than git bisect when you know what changed but not when. Use for "when did we start doing X", "which commit broke/removed/added X", "why does the code do X now".
---

# When did this change?

Searches commits, message and patch together, by meaning, with jev-semgrep's
`semgrep -z`. See the jev-semgrep skill for setup. Every commit searched is
sent to the configured endpoint (TypeSafe, directly or through OpenRouter):
ask the user first for company or proprietary repos, and never for history
that may hold secrets.

## Skip it when

- **The words are guessable.** `git log -S'retry_limit'` (added or removed
  text) or `git log -G'retry.*timeout'` (a regex in the diff) is free and
  exact. Try these first when you know a name.
- **You can test for it.** If a command tells good from bad, `git bisect run`
  proves the culprit. Meaning search only suggests one.

## Steps

1. **Narrow the history.** Limit it by path when you can (`-- src/runner/`) and by
   count (start at `-200`). The cost is proportional to the patch text sent.
2. **Write the change as a statement about the commit**, in English, naming
   the behaviour, not the code: "stops treating a zombie process group as
   still running", not "groupAlive". To find where a behaviour started, say
   "starts" or "adds". To find where it ended, say "stops" or "removes".
3. **Search**, newest first, one record per commit:

   ```sh
   git log -p --no-merges -200 --date=short --format='%x00%h %ad %s%n%b' -- <paths> \
     | semgrep -z -e "<the change>" | tr '\0' '\n' | grep -E '^[0-9a-f]{7,} [0-9]{4}-[0-9]{2}-[0-9]{2} '
   ```

   Each hit line is `<hash> <date> <subject>`. Keep the `%x00` at the start of
   the format, and don't use `git log -z`: with `-p` it puts the NUL between a
   commit's header and its diff, so a matching patch gets reported under the
   wrong commit. `--no-merges` leaves out merge commits, whose message repeats the
   PR title. A regex term first makes
   it cheaper: `-e '/retry|timeout/i' -a "<the change>"` sends only commits that
   mention one of those words.
4. **Read the results.**
   - **Several hits:** the oldest one usually introduced the behaviour, and later
     ones changed it. Say which is which.
   - **Wrong hits:** retry with `-p` to see probabilities, then `--level strict`.
   - **Nothing:** widen the count (`-500`), drop the path limit, or retry with
     `--level loose`. Then say what was searched.
5. **Confirm before reporting.** Run `git show --stat <hash>`, then read only the
   relevant hunk (`git show <hash> -- <file>`). Report the commit, its date, and
   the lines that changed the behaviour.
