#!/usr/bin/env python3
"""Split text into NUL-terminated records for `semgrep -z`, each starting "path:line".

  records.py code FILE...     Python: a record per function and method, plus class
                              headers and module-level code; other files: overlapping windows
  records.py sections FILE... Markdown: one record per heading section
  records.py hunks            a unified diff on stdin (git diff): one record per hunk
"""
import ast
import re
import sys

WINDOW = 60   # lines per window for files with no parser here
OVERLAP = 15  # lines shared between neighbouring windows, so code at a boundary is seen whole
MAX_RECORD = 200  # longer blocks are windowed too: Jev judges a record as one unit


def emit(where, text):
    sys.stdout.write(f"{where}\n{text}\0")


def windows(path, lines, start=1):
    if not lines:
        return
    step = WINDOW - OVERLAP
    for i in range(0, max(len(lines) - OVERLAP, 1), step):
        emit(f"{path}:{start + i}", "".join(lines[i:i + WINDOW]))


def block(path, lines, start, end):
    """Lines start..end (1-based, inclusive) as one record, or windows if it's long."""
    body = lines[start - 1:end]
    if len(body) > MAX_RECORD:
        windows(path, body, start)
    elif body:
        emit(f"{path}:{start}", "".join(body))


def python(path, lines, tree):
    """Each function and method once, and every other statement in runs between them."""
    def first_line(node):
        return min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])

    def walk(body, run_start):
        # A truthy run_start means body is a class's: seed it as that class's own
        # header line, so the line is still sent if the first member is a method
        # or nested class (which flushes the seed before adding anything to it).
        run = [run_start, run_start] if run_start else None
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if run:
                    block(path, lines, *run)
                    run = None
                block(path, lines, first_line(node), node.end_lineno)
            elif isinstance(node, ast.ClassDef):
                if run:
                    block(path, lines, *run)
                    run = None
                walk(node.body, first_line(node))  # the class line starts its own run
            else:
                run = [run[0] if run else first_line(node), node.end_lineno]
        if run:
            block(path, lines, *run)

    walk(tree.body, None)


def code(path):
    with open(path, encoding="utf8", errors="replace") as f:
        text = f.read()
    lines = text.splitlines(keepends=True)
    if path.endswith(".py"):
        try:
            return python(path, lines, ast.parse(text))
        except SyntaxError:
            pass
    windows(path, lines)


def sections(path):
    with open(path, encoding="utf8", errors="replace") as f:
        lines = f.readlines()
    start, fenced = 0, False
    for i, line in enumerate(lines + ["# end"]):
        if line.startswith(("```", "~~~")):
            fenced = not fenced
        elif not fenced and re.match(r"#{1,6} ", line) and i > start:
            emit(f"{path}:{start + 1}", "".join(lines[start:i]))
            start = i


def hunks():
    new_path = old_path = None
    start, body = 0, []

    def flush():
        if body:
            emit(f"{new_path}:{start}", "".join(body))

    for line in sys.stdin.read().splitlines(keepends=True):
        if line.startswith("diff --git"):
            flush()
            body, new_path, old_path = [], None, None
        elif line.startswith("--- ") and not body:
            old_path = line[4:].strip().removeprefix("a/")
        elif line.startswith("+++ ") and not body:
            p = line[4:].strip()
            new_path = old_path if p == "/dev/null" else p.removeprefix("b/")  # a deleted file keeps its name
        elif line.startswith("@@"):
            flush()
            m = re.search(r"\+(\d+)", line)
            start, body = (int(m.group(1)) if m else 0), [line]
        elif body:
            body.append(line)
    flush()


if __name__ == "__main__":
    mode, files = (sys.argv[1] if len(sys.argv) > 1 else ""), sys.argv[2:]
    if mode == "hunks":
        hunks()
    elif mode in ("code", "sections") and files:
        for p in files:
            (code if mode == "code" else sections)(p)
    else:
        sys.exit(__doc__)
