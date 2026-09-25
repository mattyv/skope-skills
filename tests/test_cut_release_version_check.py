"""cut-release's version-file check: the anchored grep pattern in its SKILL.md, run
against sample manifests. scripted skope tests fake this command, so this is what
tests the real one."""
import os
import re
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "skills", "cut-release", "SKILL.md")


def grep_pattern():
    with open(SKILL, encoding="utf8") as f:
        for line in f:
            m = re.search(r"grep -qE '([^']*\{version\}[^']*)'", line)
            if m:
                return m.group(1)
    raise AssertionError("no version-file grep in cut-release/SKILL.md")


def matches(version, text, suffix=".toml"):
    pattern = grep_pattern().replace("{version}", version)
    with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False) as f:
        f.write(text)
        path = f.name
    try:
        return subprocess.run(["grep", "-qE", pattern, path]).returncode == 0
    finally:
        os.unlink(path)


class VersionCheck(unittest.TestCase):
    def test_matches_package_json(self):
        text = '{\n  "name": "x",\n  "version": "1.2.0"\n}\n'
        self.assertTrue(matches("1.2.0", text, ".json"))

    def test_matches_pyproject_toml(self):
        text = '[project]\nname = "x"\nversion = "1.2.0"\n'
        self.assertTrue(matches("1.2.0", text))

    def test_matches_cargo_toml(self):
        text = '[package]\nname = "x"\nversion = "1.2.0"\n'
        self.assertTrue(matches("1.2.0", text))

    def test_does_not_match_a_dependency_pinned_at_the_same_version(self):
        # A Cargo.toml dependency line ("serde = \"1.2.0\"") must not be read as the
        # package's own version just because it holds the same string.
        cargo = '[package]\nname = "x"\nversion = "1.0.0"\n\n[dependencies]\nserde = "1.2.0"\n'
        self.assertFalse(matches("1.2.0", cargo))
        self.assertTrue(matches("1.0.0", cargo))


if __name__ == "__main__":
    unittest.main()
