"""review-focus's hunk splitter, the awk program in its SKILL.md, run on a fixed diff.
scripted skope tests fake this command, so this is what tests the real one."""
import os
import re
import subprocess
import textwrap
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "skills", "review-focus", "SKILL.md")


def awk_program():
    with open(SKILL, encoding="utf8") as f:
        for line in f:
            m = re.search(r"- \*\*run\*\* `.*&& awk '(.*?)' \"\$HOME", line)
            if m:
                return m.group(1)
    raise AssertionError("no awk splitter in review-focus/SKILL.md")


def split(diff):
    out = subprocess.run(["awk", awk_program()], input=diff, capture_output=True, text=True, check=True).stdout
    return [r for r in out.split("\0") if r]


DIFF = textwrap.dedent("""\
    diff --git a/src/a.ts b/src/a.ts
    index 1..2 100644
    --- a/src/a.ts
    +++ b/src/a.ts
    @@ -1,2 +1,3 @@
     keep
    +++counter
    @@ -10,1 +11,1 @@
    -old
    +new
    diff --git a/README.md b/README.md
    --- a/README.md
    +++ b/README.md
    @@ -1,1 +1,1 @@
    -Old words.
    +New words about auth.
    diff --git a/gone.ts b/gone.ts
    deleted file mode 100644
    --- a/gone.ts
    +++ /dev/null
    @@ -1,1 +0,0 @@
    -bye
    """)

# git appends a trailing tab after a path that contains a space, on both the
# --- and +++ lines, so the path itself doesn't need it stripped some other way.
SPACE_DIFF = (
    "diff --git a/src/my file.ts b/src/my file.ts\n"
    "index 1..2 100644\n"
    "--- a/src/my file.ts\t\n"
    "+++ b/src/my file.ts\t\n"
    "@@ -1,1 +1,1 @@\n"
    "-old\n"
    "+new\n"
)


class Splitter(unittest.TestCase):
    def test_one_record_per_code_hunk_at_the_new_file_line(self):
        recs = split(DIFF)
        self.assertEqual([r.split("\n", 1)[0] for r in recs], ["src/a.ts:1", "src/a.ts:11", "gone.ts:0"])

    def test_an_added_line_starting_with_plus_plus_stays_in_its_hunk(self):
        self.assertIn("+++counter", split(DIFF)[0])

    def test_doc_hunks_are_left_out(self):
        self.assertNotIn("New words about auth", "".join(split(DIFF)))

    def test_no_file_headers_leak_into_hunks(self):
        text = "".join(split(DIFF))
        for noise in ("diff --git", "deleted file mode", "index 1..2", "/dev/null"):
            self.assertNotIn(noise, text)

    def test_a_path_with_a_space_has_its_trailing_tab_stripped(self):
        recs = split(SPACE_DIFF)
        self.assertEqual([r.split("\n", 1)[0] for r in recs], ["src/my file.ts:1"])


if __name__ == "__main__":
    unittest.main()
