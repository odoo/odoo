"""Declare the parameters of every route a program calls.

`type="json2"` and `auth in {bearer, receiver}` say the caller is a program,
so the route's parameters are a contract: this adds `typed=True` and
annotates each named parameter from the rule's own converter, leaving a
handler that reads the raw body with its `**kwargs` alone.

    python _type_machine_routes.py <path>...        # rewrite
    python _type_machine_routes.py --dry-run <path>...
"""

import argparse
import ast
import re
import sys
from pathlib import Path

from _checker_typed_route import MACHINE_AUTH, MACHINE_TYPE

CONVERTERS = {
    "int": "int",
    "float": "float",
    "string": "str",
    "path": "str",
    "any": "str",
}
_RULE_ARG_RE = re.compile(
    r"<(?:(?P<converter>[a-zA-Z_][\w]*)(?:\([^>]*\))?:)?(?P<name>\w+)>"
)


def _route_calls(function):
    for decorator in function.decorator_list:
        if not isinstance(decorator, ast.Call):
            continue
        func = decorator.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        if name == "route":
            yield decorator


def _constants(call):
    return {
        keyword.arg: keyword.value.value
        for keyword in call.keywords
        if keyword.arg and isinstance(keyword.value, ast.Constant)
    }


def _rules(call):
    rules = []
    for node in call.args:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            rules.append(node.value)
        elif isinstance(node, ast.List | ast.Tuple):
            rules.extend(
                item.value
                for item in node.elts
                if isinstance(item, ast.Constant) and isinstance(item.value, str)
            )
    for keyword in call.keywords:
        if keyword.arg == "route":
            if isinstance(keyword.value, ast.Constant):
                rules.append(keyword.value.value)
            elif isinstance(keyword.value, ast.List | ast.Tuple):
                rules.extend(
                    item.value
                    for item in keyword.value.elts
                    if isinstance(item, ast.Constant)
                )
    return rules


def _path_types(call):
    types = {}
    for rule in _rules(call):
        for match in _RULE_ARG_RE.finditer(rule):
            converter = match.group("converter") or "string"
            types[match.group("name")] = CONVERTERS.get(converter)
    return types


def _named_args(function):
    args = function.args
    return [*args.posonlyargs, *args.args, *args.kwonlyargs][1:]


LITERAL_TYPES = {bool: "bool", int: "int", float: "float", str: "str"}


def _defaults(function):
    args = function.args
    positional = [*args.posonlyargs, *args.args]
    defaults = dict(
        zip(
            positional[len(positional) - len(args.defaults) :],
            args.defaults,
            strict=True,
        )
    )
    defaults.update(dict(zip(args.kwonlyargs, args.kw_defaults, strict=True)))
    return defaults


def _annotate(lines, function, path_types):
    # Only a parameter the rule itself names is annotated here; a body
    # parameter is the author's to declare.
    edits = []
    defaults = _defaults(function)
    for arg in _named_args(function):
        if arg.annotation is not None:
            continue
        annotation = path_types.get(arg.arg)
        if annotation is None:
            # A parameter the rule does not name is read from its default,
            # which is the only statement of its type the code makes.
            default = defaults.get(arg)
            if (
                isinstance(default, ast.Constant)
                and type(default.value) in LITERAL_TYPES
            ):
                annotation = LITERAL_TYPES[type(default.value)]
        if annotation is None:
            return None
        default = defaults.get(arg)
        if isinstance(default, ast.Constant) and default.value is None:
            annotation = f"{annotation} | None"
        edits.append((arg.lineno - 1, arg.col_offset + len(arg.arg), f": {annotation}"))
    for lineno, col, text in sorted(edits, reverse=True):
        line = lines[lineno]
        lines[lineno] = line[:col] + text + line[col:]
    return True


def _add_typed(lines, call):
    # After the last keyword of the decorator, in its own style.
    anchor = call.keywords[-1] if call.keywords else None
    if anchor is None or anchor.arg is None:
        return False
    end_line = anchor.value.end_lineno - 1
    line = lines[end_line]
    if call.lineno == call.end_lineno:
        insert_at = line.rindex(")")
        lines[end_line] = line[:insert_at] + ", typed=True" + line[insert_at:]
        return True
    indent = len(line) - len(line.lstrip())
    suffix = "," if not line.rstrip().endswith(",") else ""
    lines[end_line] = line.rstrip() + suffix
    lines.insert(end_line + 1, " " * indent + "typed=True,")
    return True


def rewrite(source):
    tree = ast.parse(source)
    lines = source.splitlines()
    todo = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        for call in _route_calls(node):
            keywords = _constants(call)
            if (
                keywords.get("type") != MACHINE_TYPE
                and keywords.get("auth") not in MACHINE_AUTH
            ):
                continue
            if keywords.get("typed") is True and not [
                arg for arg in _named_args(node) if arg.annotation is None
            ]:
                continue
            todo.append((node, call, keywords))
    if not todo:
        return source, 0, []
    left = []
    done = 0
    for node, call, keywords in sorted(
        todo, key=lambda item: item[0].lineno, reverse=True
    ):
        path_types = _path_types(call)
        if _annotate(lines, node, path_types) is None:
            left.append(node.name)
            continue
        if keywords.get("typed") is not True and not _add_typed(lines, call):
            left.append(node.name)
            continue
        done += 1
    return "\n".join(lines) + "\n", done, left


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    touched = total = 0
    left = []
    for root in args.paths:
        for path in sorted(Path(root).rglob("*.py")):
            if "/tests/" in str(path) or "/migrations/" in str(path):
                continue
            source = path.read_text()
            try:
                new, done, remaining = rewrite(source)
            except SyntaxError:
                continue
            left.extend(f"{path}:{name}" for name in remaining)
            if not done:
                continue
            touched += 1
            total += done
            if not args.dry_run:
                path.write_text(new)
    print(f"{total} route(s) declared in {touched} file(s)")  # noqa: T201, RUF100 CLI entry point: stdout is the fixer's report
    if left:
        print(f"{len(left)} route(s) name a parameter the rule does not:")  # noqa: T201, RUF100 CLI entry point: stdout is the fixer's report
        for entry in left:
            print(f"  {entry}")  # noqa: T201, RUF100 CLI entry point: stdout is the fixer's report
    return 0


if __name__ == "__main__":
    sys.exit(main())
