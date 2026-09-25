"""Skills run with their real commands on throwaway git repos: no network, no model.
scripted skope tests fake every command, so these are what test the commands."""
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]


def repo():
    d = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q", "-b", "main", d], check=True)
    return d


def commit(d, files, message):
    for name, text in files.items():
        path = os.path.join(d, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(text)
        if name.endswith(".sh"):
            os.chmod(path, 0o755)
    subprocess.run(GIT + ["-C", d, "add", "-A"], check=True)
    subprocess.run(GIT + ["-C", d, "commit", "-qm", message], check=True)


def code_blocks(skill):
    with open(os.path.join(SKILLS, skill, "SKILL.md"), encoding="utf8") as f:
        return re.findall(r"```sh\n(.*?)```", f.read(), re.S)


@unittest.skipUnless(shutil.which("skope"), "skope isn't installed")
class TestDiffVsMain(unittest.TestCase):
    def test_reports_only_the_failure_the_branch_added(self):
        d = repo()
        self.addCleanup(shutil.rmtree, d)
        script = '#!/bin/sh\ncat "$1/failing.txt"\n'  # "tests" that fail are listed in a file
        commit(d, {"failing.txt": "a\n", "scripts/failing-tests.sh": script}, "base")
        subprocess.run(GIT + ["-C", d, "switch", "-q", "-c", "feature"], check=True)
        commit(d, {"failing.txt": "a\nb\n"}, "adds a failure")
        run = subprocess.run(
            ["skope", os.path.join(SKILLS, "test-diff-vs-main", "SKILL.md"), "--dry-run", "--param", "base=main"],
            cwd=d, capture_output=True, text=True, env={**os.environ, "SKOPE_CALLER": "agent"},
        )
        events = [json.loads(line) for line in run.stdout.splitlines() if line.startswith("{")]
        runs = {e.get("line"): e.get("stdout_tail", "").strip() for e in events if e["event"] == "run"}
        self.assertEqual([e["to"] for e in events if e["event"] == "transfer"], ["New failures"], run.stderr)
        self.assertIn("b", runs.values())  # new_tests names the one new failure
        self.assertEqual(run.returncode, 20)  # a handoff

    def test_a_script_that_cant_run_hands_off_instead_of_stopping(self):
        # failing_script's contract: exit 0 once tests ran (even with failures),
        # non-zero only when the runner itself couldn't run (collection/config error).
        # A pipe that hides that non-zero exit would read as "zero failures" instead.
        d = repo()
        self.addCleanup(shutil.rmtree, d)
        script = '#!/bin/sh\necho "collection error: bad config" >&2\nexit 2\n'
        commit(d, {"scripts/failing-tests.sh": script}, "base")
        run = subprocess.run(
            ["skope", os.path.join(SKILLS, "test-diff-vs-main", "SKILL.md"), "--dry-run", "--param", "base=main"],
            cwd=d, capture_output=True, text=True, env={**os.environ, "SKOPE_CALLER": "agent"},
        )
        events = [json.loads(line) for line in run.stdout.splitlines() if line.startswith("{")]
        outcome = [e for e in events if e["event"] == "outcome"][-1]
        self.assertEqual(outcome["outcome"], "handoff", run.stderr)
        self.assertEqual(outcome["reason"], "command_failed", run.stderr)
        self.assertEqual(run.returncode, 20)


class CommitRecords(unittest.TestCase):
    """when-did-this-change's git log format: one record per commit, its header with its own diff."""

    def fmt(self):
        for block in code_blocks("when-did-this-change"):
            m = re.search(r"--format='([^']*)'", block)
            if m:
                return m.group(1)
        raise AssertionError("no git log --format in when-did-this-change")

    def test_each_record_is_one_commit_with_its_own_diff(self):
        d = repo()
        self.addCleanup(shutil.rmtree, d)
        commit(d, {"one.txt": "first change\n"}, "subject one")
        commit(d, {"two.txt": "second change\n"}, "subject two")
        out = subprocess.run(["git", "-C", d, "log", "-p", "--no-merges", "--date=short", f"--format={self.fmt()}"],
                             capture_output=True, text=True, check=True).stdout
        recs = [r for r in out.split("\0") if r.strip()]
        self.assertEqual(len(recs), 2)
        self.assertIn("subject two", recs[0])
        self.assertIn("+second change", recs[0])
        self.assertNotIn("first change", recs[0])
        self.assertIn("subject one", recs[1])
        self.assertIn("+first change", recs[1])

    def test_no_recipe_uses_git_log_z(self):
        # With -p, git log -z puts the NUL between a commit's header and its diff.
        for skill in ("when-did-this-change", "jev-semgrep"):
            for block in code_blocks(skill):
                commands = "\n".join(l for l in block.splitlines() if not l.lstrip().startswith("#"))
                self.assertNotRegex(commands, r"git log\b[^\n|]*\s-z\b", skill)


if __name__ == "__main__":
    unittest.main()
