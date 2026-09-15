#!/usr/bin/env python3
"""Inventory, validate and strip the `odoo.libs.debug_log` call sites.

The debug loggers are a medium-term instrument: they are meant to be removed
at the end of the quality campaign that added them. Removal is mechanical only
while every site keeps one of a fixed set of shapes, so this tool answers
three questions about a tree:

    --list    how many sites, per package and per channel
    --check   does every site have a strippable shape (exit 1 otherwise)
    --strip   remove every site and print the files it rewrote

The strippable shapes, and only these:

    from odoo.libs.debug_log import DebugLog       (or `from .debug_log import`)
    _debug = DebugLog(__name__)                    module level, that name only
    _debug.logic(...) / .pipeline(...) / .lifecycle(...) / .perf.count(...)
                                                   an expression statement
    with _debug.perf(...) as span:                 the only item of its `with`
        span.set(...)                              an expression statement
    @_debug.perf.timed                             a decorator on a def, timing
    def method(self): ...                          the whole call
    if _debug.<channel>.enabled [and <cond>]:      a guard with no `else`
    <any line>  # debuglog                         a line that exists only to
                                                   feed a log call

Test suites are not scanned: a `test_*.py`, a `conftest.py`, or anything under
a `tests/` directory that holds a `test_*.py`. A package merely named `tests`
(`odoo/tests`, the test framework) is scanned like any other.

Unpacking into a debug call is refused in two of its three forms, because a
channel is `__call__(self, event, /, **fields)` and the call machinery decides
the argument binding BEFORE the channel's level check -- so both of these fire
with the channels off, where nothing else in this tool's remit can. A `*`
expansion in the positional slot passes more than the single positional
`event` takes for any length but one, and passes silently for a length of one,
so the shape stays green until the sequence grows. A `**` expansion beside
explicit keywords raises `TypeError: got multiple values for keyword argument`
whenever an expanded key -- a runtime value -- matches a fixed one; prefix the
expanded keys and fold the fixed ones into the same expansion rather than
flattening the structure away. A `**` expansion on its own is legal and meant
to be: `event` is positional-only and nothing can shadow it.

A bare `_debug.perf(...)` statement is refused: the perf channel returns a
span, so outside a `with` it silently does nothing. A site that is the only
statement of its block is refused too, because stripping it would leave the
block empty; the guard form covers `if cond: <log>`, and an `else:` that would
hold only a log line has no guard form at all -- log before the `if` with the
condition as a field instead.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from collections import Counter
from collections.abc import Collection, Iterator
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _repo_root import find_odoo_root

REPO = find_odoo_root(Path(__file__).resolve(), tool="debuglog")
DEFAULT_ROOTS = ("odoo", "addons")
CHANNELS = ("logic", "perf", "pipeline", "lifecycle")
LINE_CHANNELS = ("logic", "pipeline", "lifecycle")
MARKER = "# debuglog"
NAME = "_debug"
CLASS = "DebugLog"
MODULE = "debug_log"
SKIPPED = ("/__pycache__/", "/_vendor/", "/node_modules/")
_MARKER_RE = re.compile(r"\s*# debuglog\s*$")
_SURVIVOR_RE = re.compile(rf"(?<![\w.])(?<!def ){NAME}\b|\b{CLASS}\b|{MARKER}")


@dataclass
class Site:
    path: Path
    line: int
    end: int
    kind: str
    channel: str | None = None


@dataclass
class Violation:
    path: Path
    line: int
    message: str


@dataclass
class FileReport:
    path: Path
    sites: list[Site] = field(default_factory=list)
    violations: list[Violation] = field(default_factory=list)
    body_lines: set[int] = field(default_factory=set)
    dedent_ranges: list[tuple[int, int]] = field(default_factory=list)


def _is_debug_attr(node: ast.AST, *chain: str) -> bool:
    for part in reversed(chain):
        if not (isinstance(node, ast.Attribute) and node.attr == part):
            return False
        node = node.value
    return isinstance(node, ast.Name) and node.id == NAME


def _is_debug_call(node: ast.AST, *chain: str) -> bool:
    return isinstance(node, ast.Call) and _is_debug_attr(node.func, *chain)


def _is_timed_decorator(node: ast.AST) -> bool:
    """`@_debug.perf.timed`, applied bare rather than called."""
    return _is_debug_attr(node, "perf", "timed")


def _mentions_debug(node: ast.AST) -> bool:
    return any(
        isinstance(child, ast.Name) and child.id == NAME for child in ast.walk(node)
    )


_BLOCK_FIELDS = frozenset({"body", "orelse", "finalbody", "handlers", "cases"})


def _iter_header_nodes(stmt: ast.stmt) -> list[ast.AST]:
    nodes: list[ast.AST] = []
    for name, value in ast.iter_fields(stmt):
        if name in _BLOCK_FIELDS:
            continue
        if isinstance(value, ast.AST):
            nodes.append(value)
        elif isinstance(value, list):
            nodes.extend(v for v in value if isinstance(v, ast.AST))
    return nodes


def _header_mentions_debug(stmt: ast.stmt, ignoring: Collection[ast.AST] = ()) -> bool:
    skip = {id(node) for node in ignoring}
    return any(
        _mentions_debug(node)
        for node in _iter_header_nodes(stmt)
        if id(node) not in skip
    )


def _guard_channel(test: ast.expr) -> str | None:
    head = test
    if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And):
        head = test.values[0]
    for channel in CHANNELS:
        if _is_debug_attr(head, channel, "enabled"):
            return channel
    return None


def _line_channel(node: ast.Call) -> str | None:
    for channel in LINE_CHANNELS:
        if _is_debug_attr(node.func, channel):
            return channel
    if _is_debug_attr(node.func, "perf", "count"):
        return "perf"
    return None


def _iter_function_scopes(tree: ast.Module) -> Iterator[ast.AST]:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            yield node


def _bare_targets(target: ast.expr) -> Iterator[ast.Name]:
    """The plain names an assignment target binds, unpacking included."""
    if isinstance(target, ast.Name):
        yield target
    elif isinstance(target, ast.Tuple | ast.List | ast.Starred):
        elements = [target.value] if isinstance(target, ast.Starred) else target.elts
        for element in elements:
            yield from _bare_targets(element)


def _scope_nodes(scope: ast.AST) -> Iterator[ast.AST]:
    """Every node lexically inside `scope` but not inside a nested scope."""
    stack = list(ast.iter_child_nodes(scope))
    while stack:
        node = stack.pop()
        yield node
        if isinstance(
            node, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda | ast.ClassDef
        ):
            continue
        stack.extend(ast.iter_child_nodes(node))


class _Scanner(ast.NodeVisitor):
    def __init__(self, path: Path, source: str) -> None:
        self.path = path
        self.lines = source.splitlines()
        self.report = FileReport(path)
        self.spans: list[str] = []
        self._in_span = False

    def _site(self, node: ast.AST, kind: str, channel: str | None = None) -> None:
        line = node.lineno  # type: ignore[attr-defined]  # every node here has a span
        end = node.end_lineno or line  # type: ignore[attr-defined]
        self.report.sites.append(Site(self.path, line, end, kind, channel))

    def _violation(self, node: ast.AST, message: str) -> None:
        line = getattr(node, "lineno", 0)
        self.report.violations.append(Violation(self.path, line, message))

    def _is_removable(self, stmt: ast.stmt) -> bool:
        """Would the strip pass delete this statement outright?"""
        if _MARKER_RE.search(self.lines[stmt.lineno - 1]):
            return True
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            call = stmt.value
            if _line_channel(call) is not None:
                return True
            return (
                isinstance(call.func, ast.Attribute)
                and call.func.attr == "set"
                and isinstance(call.func.value, ast.Name)
                and call.func.value.id in self.spans
            )
        if isinstance(stmt, ast.If):
            return _guard_channel(stmt.test) is not None
        if isinstance(stmt, ast.With):
            # a span leaves its own body behind, dedented, so it disappears
            # only when that body disappears too
            return (
                len(stmt.items) == 1
                and _is_debug_call(stmt.items[0].context_expr, "perf")
                and all(self._is_removable(inner) for inner in stmt.body)
            )
        if isinstance(stmt, ast.ImportFrom):
            return _is_debug_import(stmt)
        if isinstance(stmt, ast.Assign):
            return _is_debug_assignment(stmt)
        return False

    def _check_removable(
        self, node: ast.stmt, body: list[ast.stmt], *, inside_span: bool = False
    ) -> None:
        """Refuse a block the strip pass would empty.

        A block of ONE debug statement is the obvious case, and it was the
        only one this checked until 2026-09-14. A block of several, all of
        them debug, empties just as completely -- and passed, because the
        count was the test. Found by the round trip on a three-statement
        `if line_errors:` whose body was two `# debuglog` counters and one
        `_debug.logic(...)`: `--check` read three statements and said nothing,
        `--strip` left a bare `if line_errors:` and the file stopped parsing.
        """
        if inside_span:
            # a span's own body may empty: the `with` line is removed too, so
            # nothing is left needing a statement
            return
        if all(self._is_removable(stmt) for stmt in body):
            self._violation(
                node,
                "every statement of this block is a debug site; stripping "
                "them would leave the block empty",
            )

    def _visit_body(self, body: list[ast.stmt]) -> None:
        for stmt in body:
            self._visit_stmt(stmt, body)

    def _check_unpacking(self, call: ast.Call) -> None:
        """Unpacking into a debug call can raise before the level check.

        A channel is `__call__(self, event, /, **fields)`, so the call
        machinery -- not the channel -- decides both of these, and it decides
        them with the channels off:

        * `*` in the positional slot passes more than the one positional
          `event` takes for any sequence whose length is not exactly 1, and
          silently works for a length of 1, so the shape sits green until the
          sequence grows.
        * `**` beside explicit keywords collides whenever an expanded key
          matches one of them, and the keys come from runtime data.

        `**` alone is legal and stays legal: `event` is positional-only, so
        nothing an expansion carries can collide with it.
        """
        starred = [arg for arg in call.args if isinstance(arg, ast.Starred)]
        if starred:
            self._violation(
                call,
                "a debug call may not use a `*` expansion: `event` is the only "
                "positional parameter, so any length but one raises TypeError "
                "at call time, channels off included -- and a length of one "
                "passes, which hides the shape until the sequence grows",
            )
        if any(keyword.arg is None for keyword in call.keywords) and any(
            keyword.arg is not None for keyword in call.keywords
        ):
            self._violation(
                call,
                "a debug call may not mix explicit keywords with a `**` "
                "expansion: an expanded key colliding with one of them raises "
                "TypeError at call time, channels off included",
            )

    def _visit_stmt(self, stmt: ast.stmt, body: list[ast.stmt]) -> None:
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            call = stmt.value
            channel = _line_channel(call)
            if channel is not None:
                self._check_unpacking(call)
                self._site(stmt, "line", channel)
                self._check_removable(stmt, body, inside_span=self._in_span)
                return
            if _is_debug_call(call, "perf"):
                self._violation(
                    stmt,
                    "bare _debug.perf(...) statement: the span is never "
                    "entered, so it logs nothing; use `with _debug.perf(...)`",
                )
                return
            if (
                isinstance(call.func, ast.Attribute)
                and call.func.attr == "set"
                and isinstance(call.func.value, ast.Name)
                and call.func.value.id in self.spans
            ):
                self._site(stmt, "span_set", "perf")
                self._check_removable(stmt, body, inside_span=self._in_span)
                return
        if isinstance(stmt, ast.With) and any(
            _mentions_debug(item.context_expr) for item in stmt.items
        ):
            self._visit_with(stmt, body)
            return
        if isinstance(stmt, ast.If) and _mentions_debug(stmt.test):
            self._visit_guard(stmt, body)
            return
        if isinstance(stmt, ast.Assign) and _is_debug_assignment(stmt):
            self._site(stmt, "assignment")
            return
        if isinstance(stmt, ast.ImportFrom) and _is_debug_import(stmt):
            self._site(stmt, "import")
            return
        timed = [
            decorator
            for decorator in getattr(stmt, "decorator_list", ())
            if _is_timed_decorator(decorator)
        ]
        for decorator in timed:
            self._site(decorator, "decorator", "perf")
        if _header_mentions_debug(stmt, timed):
            self._violation(stmt, f"{NAME} used outside the strippable shapes")
        self.generic_visit_stmt(stmt)

    def _visit_with(self, stmt: ast.With, body: list[ast.stmt]) -> None:
        if len(stmt.items) != 1:
            self._violation(
                stmt,
                "a `with` that opens a debug span must have that span as "
                "its only item; nest the other context manager inside",
            )
            return
        item = stmt.items[0]
        if not _is_debug_call(item.context_expr, "perf"):
            self._violation(stmt, "only `with _debug.perf(...)` may open a span")
            return
        assert isinstance(item.context_expr, ast.Call)
        self._check_unpacking(item.context_expr)
        self._site(stmt, "span", "perf")
        alias = item.optional_vars
        name = alias.id if isinstance(alias, ast.Name) else None
        first = stmt.body[0].lineno
        for line in range(stmt.lineno, first):
            self.report.body_lines.add(line)
        self.report.dedent_ranges.append((first, stmt.end_lineno or first))
        if name is not None:
            self.spans.append(name)
        was_in_span, self._in_span = self._in_span, True
        self._visit_body(stmt.body)
        self._in_span = was_in_span
        if name is not None:
            self.spans.pop()

    def _visit_guard(self, stmt: ast.If, body: list[ast.stmt]) -> None:
        if _guard_channel(stmt.test) is None or stmt.orelse:
            self._violation(
                stmt,
                "a debug guard must be `if _debug.<channel>.enabled [and ...]:` "
                "with no else branch",
            )
            return
        self._site(stmt, "guard")
        self._check_removable(stmt, body)
        for inner in stmt.body:
            if not (
                isinstance(inner, ast.Expr)
                and isinstance(inner.value, ast.Call)
                and _line_channel(inner.value) is not None
            ) and not _MARKER_RE.search(self.lines[inner.lineno - 1]):
                self._violation(
                    inner,
                    f"a guard body may hold debug lines and `{MARKER}` lines only",
                )

    def generic_visit_stmt(self, stmt: ast.stmt) -> None:
        for name in ("body", "orelse", "finalbody"):
            child_body = getattr(stmt, name, None)
            if isinstance(child_body, list) and child_body:
                if all(isinstance(child, ast.stmt) for child in child_body):
                    self._visit_body(child_body)
        for handler in getattr(stmt, "handlers", ()):
            self._visit_body(handler.body)
        for case in getattr(stmt, "cases", ()):
            self._visit_body(case.body)

    def _check_marked_assignments(self, tree: ast.Module) -> None:
        """Refuse a `# debuglog` line whose name outlives it.

        A marked line is deleted outright, so a name it binds must be read by
        debug code and nothing else. Measured 2026-09-14: the old checker read

            with _debug.perf("scan", modules=len(graph)) as span:
                members = graph.cycles()  # debuglog
                span.set(on_cycle=len(members))
            for member in members:

        as five clean sites, and the strip produced a file whose `for` loop
        named an undefined `members` -- two `F821`, out of a tree `--check`
        had just called clean.

        Scoped per function, because the first cut compared names across the
        whole file and read a sibling method's *parameter* as the surviving
        use: 20 findings, every one of them a name collision. And the marker
        is looked for across the statement's whole SPAN: the first cut read
        only its opening line, and so missed a marker on the closing bracket
        of a multi-line assignment whose name the next line reads.
        """
        covered = {
            line
            for site in self.report.sites
            for line in range(site.line, (site.end or site.line) + 1)
        }
        for scope in [tree, *_iter_function_scopes(tree)]:
            nodes = list(_scope_nodes(scope))
            bound: dict[str, ast.stmt] = {}
            for node in nodes:
                if not isinstance(node, ast.Assign | ast.AugAssign | ast.AnnAssign):
                    continue
                if not any(
                    _MARKER_RE.search(self.lines[line - 1])
                    for line in range(node.lineno, (node.end_lineno or node.lineno) + 1)
                ):
                    continue
                targets = (
                    node.targets if isinstance(node, ast.Assign) else [node.target]
                )
                for target in targets:
                    # only a bare name is bound; `self.x = ...` binds nothing
                    # called `self`, and reading the name inside the attribute
                    # target as a binding is how the first cut called
                    # `db/cursor.py`'s `self._backend_pid` a finding
                    for inner in _bare_targets(target):
                        bound.setdefault(inner.id, node)
            if not bound:
                continue
            for node in nodes:
                if (
                    isinstance(node, ast.Name)
                    and isinstance(node.ctx, ast.Load)
                    and node.id in bound
                    and node.lineno not in covered
                ):
                    self._violation(
                        bound.pop(node.id),
                        f"a `{MARKER}` line binds `{node.id}`, which surviving "
                        f"code reads at line {node.lineno}; stripping it leaves "
                        "an undefined name",
                    )
                    if not bound:
                        break

    def _check_marker_lines(self, tree: ast.Module) -> None:
        """Refuse a marker on a line that is not a whole statement.

        The strip removes a marked line and nothing else, so a marker on a
        continuation line -- or on a compound statement's header -- leaves the
        rest of the construct behind and the file stops parsing. Measured
        2026-09-15 on a probe the previous checker called clean at 5 sites:

            first = (
                a or b
            ) and not a  # debuglog

        stripped to `first = (` plus an orphaned `a or b`, a `SyntaxError` out
        of a tree `--check` had just passed. Fourteen sites in `odoo` were in
        that shape, including `)  # debuglog` on a closing bracket and
        `except Exception as err:  # debuglog` on a handler.
        """
        statements = [node for node in ast.walk(tree) if isinstance(node, ast.stmt)]
        for number, text in enumerate(self.lines, 1):
            if not _MARKER_RE.search(text):
                continue
            innermost = None
            for statement in statements:
                start = statement.lineno
                end = statement.end_lineno or start
                if start <= number <= end and (
                    innermost is None
                    or (end - start)
                    < ((innermost.end_lineno or innermost.lineno) - innermost.lineno)
                ):
                    innermost = statement
            if innermost is None:
                continue
            if (innermost.end_lineno or innermost.lineno) > innermost.lineno:
                self.report.violations.append(
                    Violation(
                        self.path,
                        number,
                        f"a `{MARKER}` marker must sit on a line that is a whole "
                        f"statement; this one is inside a statement spanning "
                        f"lines {innermost.lineno}-{innermost.end_lineno}, and "
                        "the strip removes the line rather than the statement",
                    )
                )

    def scan(self, tree: ast.Module) -> FileReport:
        self._visit_body(tree.body)
        for number, text in enumerate(self.lines, 1):
            if _MARKER_RE.search(text):
                self.report.sites.append(Site(self.path, number, number, "marker"))
        self._check_marked_assignments(tree)
        self._check_marker_lines(tree)
        return self.report


def _is_debug_assignment(stmt: ast.Assign) -> bool:
    return (
        len(stmt.targets) == 1
        and isinstance(stmt.targets[0], ast.Name)
        and stmt.targets[0].id == NAME
        and isinstance(stmt.value, ast.Call)
        and isinstance(stmt.value.func, ast.Name)
        and stmt.value.func.id == CLASS
    )


def _is_debug_import(stmt: ast.ImportFrom) -> bool:
    module = stmt.module or ""
    return module.endswith(MODULE) and all(a.name == CLASS for a in stmt.names)


def scan_file(path: Path) -> FileReport | None:
    source = path.read_text(encoding="utf-8")
    if NAME not in source and CLASS not in source and MARKER not in source:
        return None
    tree = ast.parse(source, filename=str(path))
    report = _Scanner(path, source).scan(tree)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == CLASS
        ):
            parent_ok = any(
                site.kind == "assignment" and site.line == node.lineno
                for site in report.sites
            )
            if not parent_ok:
                report.violations.append(
                    Violation(
                        path,
                        node.lineno,
                        f"{CLASS}(...) must be bound to a module-level `{NAME}`",
                    )
                )
    return report


def _is_test_suite_dir(directory: Path, memo: dict[Path, bool]) -> bool:
    known = memo.get(directory)
    if known is None:
        known = memo[directory] = any(directory.glob("test_*.py"))
    return known


def _is_test_file(path: Path, memo: dict[Path, bool]) -> bool:
    if path.name.startswith("test_") or path.name == "conftest.py":
        return True
    return any(
        parent.name == "tests" and _is_test_suite_dir(parent, memo)
        for parent in path.parents
    )


def iter_files(roots: list[Path]) -> list[Path]:
    files: list[Path] = []
    memo: dict[Path, bool] = {}
    for root in roots:
        for path in sorted(root.rglob("*.py")):
            text = str(path)
            if any(part in text for part in SKIPPED):
                continue
            if path.name == f"{MODULE}.py" or _is_test_file(path, memo):
                continue
            files.append(path)
    return files


def scan(roots: list[Path]) -> list[FileReport]:
    reports = []
    for path in iter_files(roots):
        report = scan_file(path)
        if report is not None and (report.sites or report.violations):
            reports.append(report)
    return reports


def _rel(path: Path) -> Path:
    try:
        return path.relative_to(REPO)
    except ValueError:
        return path


def _package_of(path: Path) -> str:
    parts = _rel(path).parts
    if path.is_absolute() and parts == path.parts:
        return path.parent.name
    if parts[0] == "odoo" and len(parts) > 2:
        if parts[1] == "addons" and len(parts) > 3:
            return f"odoo/addons/{parts[2]}"
        return f"odoo/{parts[1]}"
    if parts[0] == "addons" and len(parts) > 2:
        return f"addons/{parts[1]}"
    return parts[0]


def render_list(reports: list[FileReport]) -> str:
    per_package: dict[str, Counter] = {}
    files: Counter = Counter()
    for report in reports:
        package = _package_of(report.path)
        counter = per_package.setdefault(package, Counter())
        files[package] += 1
        for site in report.sites:
            if site.channel is not None and site.kind != "span_set":
                counter[site.channel] += 1
    lines = [f"{'package':<32} {'files':>5} " + " ".join(f"{c:>9}" for c in CHANNELS)]
    total: Counter = Counter()
    for package in sorted(per_package):
        counter = per_package[package]
        total.update(counter)
        lines.append(
            f"{package:<32} {files[package]:>5} "
            + " ".join(f"{counter[c]:>9}" for c in CHANNELS)
        )
    lines.append(
        f"{'total':<32} {sum(files.values()):>5} "
        + " ".join(f"{total[c]:>9}" for c in CHANNELS)
    )
    return "\n".join(lines)


def strip_file(report: FileReport) -> str:
    source = report.path.read_text(encoding="utf-8")
    lines = source.splitlines(keepends=True)
    doomed: set[int] = set(report.body_lines)
    for site in report.sites:
        if site.kind == "span":
            continue
        doomed.update(range(site.line, site.end + 1))
    dedent: set[int] = set()
    for first, last in report.dedent_ranges:
        dedent.update(range(first, last + 1))
    output: list[str] = []
    for number, text in enumerate(lines, 1):
        if number in doomed:
            continue
        if number in dedent and text.startswith("    "):
            text = text[4:]
        output.append(text)
    return _collapse_blank_lines("".join(output))


def _collapse_blank_lines(text: str) -> str:
    return re.sub(r"\n{4,}", "\n\n\n", text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--list", action="store_true", help="count sites per package")
    mode.add_argument("--check", action="store_true", help="validate every site")
    mode.add_argument("--strip", action="store_true", help="remove every site")
    parser.add_argument(
        "--dry-run", action="store_true", help="with --strip: report, do not write"
    )
    parser.add_argument(
        "--roots",
        nargs="+",
        default=list(DEFAULT_ROOTS),
        help="directories to scan, relative to the odoo checkout or absolute",
    )
    args = parser.parse_args(argv)

    roots = [Path(r) if Path(r).is_absolute() else REPO / r for r in args.roots]
    missing = [str(r) for r in roots if not r.is_dir()]
    if missing:
        parser.error(f"not a directory: {', '.join(missing)}")
    reports = scan(roots)

    if args.list:
        print(render_list(reports))
        return 0

    violations = [v for report in reports for v in report.violations]
    if args.check:
        for violation in violations:
            rel = _rel(violation.path)
            print(f"{rel}:{violation.line}: {violation.message}")
        sites = sum(len(r.sites) for r in reports)
        print(
            f"{len(reports)} files, {sites} sites, {len(violations)} violations",
            file=sys.stderr,
        )
        return 1 if violations else 0

    if violations:
        for violation in violations:
            rel = _rel(violation.path)
            print(f"{rel}:{violation.line}: {violation.message}", file=sys.stderr)
        print("refusing to strip a tree that fails --check", file=sys.stderr)
        return 1
    for report in reports:
        stripped = strip_file(report)
        rel = _rel(report.path)
        if _SURVIVOR_RE.search(stripped):
            print(f"{rel}: a debug reference survived the strip; not written")
            return 2
        print(f"{rel}: {len(report.sites)} sites")
        if not args.dry_run:
            report.path.write_text(stripped, encoding="utf-8")
    if not args.dry_run:
        print(
            "stripped; now run `ruff check --fix` and `ruff format` over the "
            "files above",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
