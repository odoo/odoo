"""Spell every argument of a field declaration as its keyword, in
FIELD_ATTRIBUTE_ORDER, one per line once there are two.

    python _sort_field_attributes.py [--dry-run] [--ruff <ruff>] <root>...

Invariant, checked per file before anything is written: the module's AST with
every field call normalised (positionals mapped to their keywords, keywords
sorted by name) is identical before and after. Only the spelling and the order
of the arguments may change. A declaration the fixer will not touch -- a
comment inside the parentheses, a `*args` or `**kwargs` -- is reported.
"""

import argparse
import ast
import io
import subprocess
import sys
import tokenize
from pathlib import Path

if __package__:
    from ._checker_field_declaration import (
        bound_names,
        canonical_order,
        is_field_call,
        positional_names,
    )
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _checker_field_declaration import (  # type: ignore[no-redef]
        bound_names,
        canonical_order,
        is_field_call,
        positional_names,
    )

_SKIP_DIRS = ("/tests/", "/_vendor/", "/migrations/", "/upgrades/", "/static/")


class Declined(Exception):
    pass


def _offset(lines: list[bytes], lineno: int, col: int) -> int:
    return sum(len(line) for line in lines[: lineno - 1]) + col


def _span(lines: list[bytes], node: ast.AST) -> tuple[int, int]:
    return (
        _offset(lines, node.lineno, node.col_offset),
        _offset(lines, node.end_lineno, node.end_col_offset),
    )


def _comments(source: bytes, lines: list[bytes]) -> list[tuple[int, bytes]]:
    text = source.decode("utf-8")
    out = []
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type == tokenize.COMMENT:
            line, col = token.start
            col = len(lines[line - 1].decode("utf-8")[:col].encode("utf-8"))
            out.append((_offset(lines, line, col), token.string.encode()))
    return out


def _arguments(call: ast.Call) -> list[tuple[str, ast.expr]]:
    names = positional_names(call)
    out: list[tuple[str, ast.expr]] = []
    for index, arg in enumerate(call.args):
        if isinstance(arg, ast.Starred) or index >= len(names):
            raise Declined("a positional argument the signature does not name")
        out.append((names[index], arg))
    for keyword in call.keywords:
        if keyword.arg is None:
            raise Declined("a **mapping argument")
        out.append((keyword.arg, keyword.value))
    if len({name for name, _ in out}) != len(out):
        raise Declined("an argument given twice")
    return out


def _render(
    source: bytes,
    lines: list[bytes],
    call: ast.Call,
    indent: bytes,
    comments: list[tuple[int, bytes]],
) -> bytes:
    arguments = dict(_arguments(call))
    ordered = canonical_order(list(arguments))
    func_start, func_end = _span(lines, call.func)
    head = source[func_start:func_end]
    call_start, call_end = _span(lines, call)
    spans = {name: _span(lines, value) for name, value in arguments.items()}
    # A comment inside an argument's own span stays there with the source
    # slice; one trailing an argument's last line travels with the argument;
    # one on a line of its own explains the argument that follows it and
    # travels with that one; one after the last argument has nothing to follow.
    trailing: dict[str, bytes] = {}
    leading: dict[str, list[bytes]] = {}
    for offset, text in comments:
        if not call_start <= offset < call_end:
            continue
        if any(start <= offset < end for start, end in spans.values()):
            continue
        line_end = source.find(b"\n", offset)
        owner = next(
            (
                name
                for name, (_start, end) in spans.items()
                if end <= offset and source.find(b"\n", end) == line_end
            ),
            None,
        )
        if owner is not None:
            if owner in trailing:
                raise Declined("two comments trailing one argument")
            trailing[owner] = b"  " + text
            continue
        following = next(
            (name for name, (start, _end) in spans.items() if start > offset),
            None,
        )
        if following is None:
            raise Declined("a comment after the last argument")
        leading.setdefault(following, []).append(text)
    pieces = [name.encode() + b"=" + source[slice(*spans[name])] for name in ordered]
    if len(pieces) < 2 and not trailing and not leading:
        return head + b"(" + b", ".join(pieces) + b")"
    inner = indent + b"    "
    return (
        head
        + b"(\n"
        + b"".join(
            b"".join(inner + c + b"\n" for c in leading.get(n, ()))
            + inner
            + p
            + b","
            + trailing.get(n, b"")
            + b"\n"
            for n, p in zip(ordered, pieces, strict=True)
        )
        + indent
        + b")"
    )


def _declarations(tree: ast.Module):
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for statement in node.body:
            if len(bound_names(statement)) == 1 and is_field_call(statement.value):
                yield statement


class _Normalise(ast.NodeTransformer):
    def visit_Call(self, node: ast.Call) -> ast.AST:
        self.generic_visit(node)
        if not is_field_call(node):
            return node
        try:
            arguments = _arguments(node)
        except Declined:
            return node
        return ast.Call(
            func=node.func,
            args=[],
            keywords=[
                ast.keyword(arg=name, value=value)
                for name, value in sorted(arguments, key=lambda item: item[0])
            ],
        )


def _normalised(tree: ast.Module) -> str:
    return ast.dump(_Normalise().visit(tree), include_attributes=False)


def rewrite(path: Path) -> tuple[bytes, bytes, int, list[str]]:
    source = path.read_bytes()
    tree = ast.parse(source, str(path))
    lines = source.splitlines(keepends=True)
    comments = _comments(source, lines)
    edits: list[tuple[int, int, bytes]] = []
    declined: list[str] = []
    for statement in _declarations(tree):
        call = statement.value
        indent = lines[statement.lineno - 1][: statement.col_offset]
        try:
            rendered = _render(source, lines, call, indent, comments)
        except Declined as reason:
            declined.append(f"{path}:{call.lineno}: {reason}")
            continue
        start, end = _span(lines, call)
        if source[start:end] != rendered:
            edits.append((start, end, rendered))
    out = source
    for start, end, rendered in sorted(edits, reverse=True):
        out = out[:start] + rendered + out[end:]
    if edits and _normalised(ast.parse(out, str(path))) != _normalised(tree):
        raise AssertionError(f"{path}: the rewrite changed more than argument spelling")
    return source, out, len(edits), declined


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--ruff", help="path to ruff, to reformat touched files")
    parser.add_argument("roots", nargs="+")
    args = parser.parse_args()

    changed: list[str] = []
    declined: list[str] = []
    total = 0
    for root in args.roots:
        for path in sorted(Path(root).rglob("*.py")):
            text = str(path)
            if any(part in text for part in _SKIP_DIRS) or path.name.startswith(
                "test_"
            ):
                continue
            try:
                before, after, count, skipped = rewrite(path)
            except SyntaxError:
                continue
            declined.extend(skipped)
            total += count
            if after != before:
                changed.append(text)
                if not args.dry_run:
                    path.write_bytes(after)
    if args.ruff and changed and not args.dry_run:
        subprocess.run([args.ruff, "format", "--quiet", *changed], check=True)
    for line in declined:
        print(line, file=sys.stderr)
    print(
        f"{total} declaration(s) in {len(changed)} file(s), {len(declined)} declined"
        f"{' (dry run)' if args.dry_run else ''}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
