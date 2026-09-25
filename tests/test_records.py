"""records.py, the splitter behind jev-semgrep's -z recipes. Run: python3 -m unittest discover tests"""
import os
import subprocess
import tempfile
import textwrap
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECORDS = os.path.join(ROOT, "skills", "jev-semgrep", "scripts", "records.py")


def records(*args, stdin=None):
    out = subprocess.run(["python3", RECORDS, *args], input=stdin, capture_output=True, text=True, check=True).stdout
    return [r for r in out.split("\0") if r]


def headers(recs):
    return [r.split("\n", 1)[0] for r in recs]


class Files(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)

    def write(self, name, text):
        path = os.path.join(self.dir.name, name)
        with open(path, "w", encoding="utf8") as f:
            f.write(text)
        return path


class Code(Files):
    def test_python_splits_by_function_and_method_without_duplicates(self):
        p = self.write("m.py", textwrap.dedent("""\
            import os

            def a():
                return 1

            class B:
                x = 1

                def c(self):
                    return 2

                def d(self):
                    return 3

            if __name__ == "__main__":
                a()
            """))
        recs = records("code", p)
        self.assertEqual(headers(recs), [f"{p}:1", f"{p}:3", f"{p}:6", f"{p}:9", f"{p}:12", f"{p}:15"])
        text = "".join(recs)
        # Every source line is sent exactly once: class header, methods and module code included.
        for line in ["import os", "return 1", "class B:", "x = 1", "return 2", "return 3", "    a()"]:
            self.assertEqual(text.count(line), 1, line)

    def test_a_long_python_function_is_windowed_so_every_line_is_seen(self):
        body = "".join(f"    x{i} = {i}\n" for i in range(300))
        p = self.write("long.py", "def f():\n" + body)
        text = "".join(records("code", p))
        self.assertIn("x0 = 0", text)
        self.assertIn("x299 = 299", text)
        self.assertGreater(len(records("code", p)), 1)

    def test_python_with_a_syntax_error_falls_back_to_windows(self):
        p = self.write("bad.py", "def f(:\n  pass\n")
        self.assertEqual(headers(records("code", p)), [f"{p}:1"])

    def test_other_files_are_windowed_with_overlap_and_nothing_is_missed(self):
        lines = [f"line {i}\n" for i in range(1, 131)]
        p = self.write("x.ts", "".join(lines))
        recs = records("code", p)
        self.assertEqual(headers(recs), [f"{p}:1", f"{p}:46", f"{p}:91"])
        # 60-line windows, 15 lines shared with the next one, and the last line is covered.
        self.assertIn("line 60\n", recs[0])
        self.assertIn("line 46\n", recs[0])
        self.assertIn("line 130\n", recs[-1])

    def test_an_empty_file_gives_no_record(self):
        self.assertEqual(records("code", self.write("e.ts", "")), [])

    def test_a_class_whose_body_starts_with_a_method_still_sends_the_class_line(self):
        # walk()'s seed run for a class body was an empty [start, start - 1] range,
        # silently dropped instead of emitted, whenever the first member was a
        # method or nested class with nothing else before it.
        p = self.write("m.py", textwrap.dedent("""\
            class Empty:
                def m(self):
                    return 1
            """))
        recs = records("code", p)
        self.assertEqual(headers(recs), [f"{p}:1", f"{p}:2"])
        self.assertIn("class Empty:", recs[0])


class Sections(Files):
    def test_splits_on_headings_but_not_inside_code_fences(self):
        p = self.write("r.md", textwrap.dedent("""\
            Intro.
            # One
            text
            ```sh
            # a shell comment, not a heading
            ```
            ## Two
            more
            """))
        self.assertEqual(headers(records("sections", p)), [f"{p}:1", f"{p}:2", f"{p}:7"])


DIFF = textwrap.dedent("""\
    diff --git a/src/a.ts b/src/a.ts
    index 1..2 100644
    --- a/src/a.ts
    +++ b/src/a.ts
    @@ -1,2 +1,3 @@
     keep
    +added
    @@ -10,1 +11,1 @@
    -old
    +new
    diff --git a/gone.ts b/gone.ts
    deleted file mode 100644
    --- a/gone.ts
    +++ /dev/null
    @@ -1,1 +0,0 @@
    -bye
    """)


class Hunks(unittest.TestCase):
    def test_one_record_per_hunk_at_the_new_file_line(self):
        recs = records("hunks", stdin=DIFF)
        self.assertEqual(headers(recs), ["src/a.ts:1", "src/a.ts:11", "gone.ts:0"])
        self.assertIn("+added", recs[0])
        self.assertNotIn("diff --git", "".join(recs))

    def test_a_deleted_file_keeps_its_own_path(self):
        self.assertNotIn("/dev/null", "".join(headers(records("hunks", stdin=DIFF))))


if __name__ == "__main__":
    unittest.main()
