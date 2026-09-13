"""Drop `string=` arguments that restate the label the ORM derives from the name.

    python _drop_field_labels.py -d <db> [-c conf] [--addons-path a,b] [--dry-run]

Exact, not syntactic: the redundant set is read off the built registry, so a
string that overrides a lower definition's different label is kept.
"""

import argparse
import ast
import inspect
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


def _bootstrap():
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "odoo" / "release.py").is_file():
            sys.path.insert(0, str(parent))
            return
    raise SystemExit("cannot locate the odoo package from " + str(here))


_bootstrap()

from odoo import tools  # noqa: E402  the path is fixed above
from odoo.modules.registry import Registry  # noqa: E402  the path is fixed above
from odoo.orm.models.metaclass import MetaModel  # noqa: E402  the path is fixed above

from odoo.addons.test_lint.tests._checker_field_declaration import (  # noqa: E402  the path is fixed above
    bound_names,
)


def auto_label(name: str) -> str:
    return (
        (name[:-4] if name.endswith("_ids") else name.removesuffix("_id"))
        .replace("_", " ")
        .title()
    )


def redundant_definitions(
    registry, roots: list[Path]
) -> dict[str, set[tuple[str, str]]]:
    by_file: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for model_cls in registry.values():
        definitions: dict[str, list] = defaultdict(list)
        for cls in model_cls._model_classes__:
            if isinstance(cls, MetaModel):
                for field in cls._field_definitions:
                    definitions[field.name].append((cls, field))
        for name, chain in definitions.items():
            auto = auto_label(name)
            for index, (cls, field) in enumerate(chain):
                args = field._args__
                if args.get("string") != auto or "related" in args:
                    continue
                if not all(
                    "related" not in lower._args__
                    and lower._args__.get("string") in (None, auto)
                    for _, lower in chain[index + 1 :]
                ):
                    continue
                path = inspect.getsourcefile(cls)
                if path and any(Path(path).is_relative_to(root) for root in roots):
                    by_file[path].add((cls.__name__, name))
    return by_file


_STRING_POSITION = {
    "Many2one": 1,
    "One2many": 2,
    "Many2many": 4,
    "Selection": 1,
    "Reference": 1,
    "Count": 1,
}


def _string_node(call: ast.Call):
    for keyword in call.keywords:
        if keyword.arg == "string":
            return keyword
    position = _STRING_POSITION.get(call.func.attr, 0)
    if len(call.args) > position and not isinstance(call.args[position], ast.Starred):
        return call.args[position]
    return None


def _offset(lines: list[bytes], lineno: int, col: int) -> int:
    return sum(len(line) for line in lines[: lineno - 1]) + col


def _spans(source: bytes, call: ast.Call):
    lines = source.splitlines(keepends=True)
    ordered = sorted(
        [*call.args, *call.keywords],
        key=lambda node: (node.lineno, node.col_offset),
    )
    return [
        (
            node,
            _offset(lines, node.lineno, node.col_offset),
            _offset(lines, node.end_lineno, node.end_col_offset),
        )
        for node in ordered
    ]


def _removal(source: bytes, call: ast.Call, target) -> tuple[int, int]:
    spans = _spans(source, call)
    index = next(i for i, (node, _s, _e) in enumerate(spans) if node is target)
    _node, start, end = spans[index]
    if index + 1 < len(spans):
        return start, spans[index + 1][1]
    if index > 0:
        return spans[index - 1][2], end
    lines = source.splitlines(keepends=True)
    open_paren = _offset(lines, call.func.end_lineno, call.func.end_col_offset)
    close_paren = _offset(lines, call.end_lineno, call.end_col_offset) - 1
    return open_paren + 1, close_paren


def rewrite(path: str, wanted: set[tuple[str, str]]) -> tuple[bytes, bytes, int]:
    source = Path(path).read_bytes()
    tree = ast.parse(source, path)
    removals: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for statement in node.body:
            [name] = bound_names(statement) or [None]
            if name is None or (node.name, name) not in wanted:
                continue
            if not (
                isinstance(statement.value, ast.Call)
                and isinstance(statement.value.func, ast.Attribute)
            ):
                continue
            target = _string_node(statement.value)
            if target is None:
                continue
            removals.append(_removal(source, statement.value, target))
    out = source
    for start, end in sorted(removals, reverse=True):
        out = out[:start] + out[end:]
    return source, out, len(removals)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--database", required=True)
    parser.add_argument("-c", "--config")
    parser.add_argument("--addons-path")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json")
    parser.add_argument("--ruff", help="path to ruff, to reformat touched files")
    parser.add_argument("roots", nargs="+")
    args = parser.parse_args()

    argv = ["-d", args.database]
    if args.config:
        argv += ["-c", args.config]
    if args.addons_path:
        argv += ["--addons-path", args.addons_path]
    tools.config.parse_config(argv)
    registry = Registry(args.database)
    roots = [Path(root).resolve() for root in args.roots]

    by_file = redundant_definitions(registry, roots)
    total = 0
    changed = []
    for path, wanted in sorted(by_file.items()):
        before, after, count = rewrite(path, wanted)
        if count != len(wanted):
            print(f"{path}: {len(wanted)} redundant, {count} located", file=sys.stderr)
        ast.parse(after, path)
        total += count
        if after != before:
            changed.append(path)
            if not args.dry_run:
                Path(path).write_bytes(after)
    if args.ruff and changed and not args.dry_run:
        subprocess.run([args.ruff, "format", "--quiet", *changed], check=True)
    if args.json:
        Path(args.json).write_text(
            json.dumps({p: sorted(map(list, w)) for p, w in by_file.items()}, indent=1),
            encoding="utf-8",
        )
    print(
        f"{total} label(s) in {len(by_file)} file(s){' (dry run)' if args.dry_run else ''}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
