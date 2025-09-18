"""Gettext usage checker using stdlib ``ast``.

Detects misuse of ``_()``, ``_lt()`` translation functions and missing
``gettext`` wrappers on error messages.

Rules:
- ``gettext-variable``: ``_()`` / ``_lt()`` called with non-literal first arg.
- ``gettext-placeholders``: ``_()`` / ``_lt()`` with 2+ unnamed ``%s`` placeholders.
- ``gettext-repr``: ``%r`` inside a translation string.
- ``missing-gettext``: Raw string literal as first arg to error constructors.

Replaces the former ``_odoo_checker_gettext.py`` (which required
``astroid`` + ``pylint``).
"""

import ast
import re
from collections.abc import Iterator
from dataclasses import dataclass

PLACEHOLDER_REGEXP = re.compile(
    r"""
    (?<!%)             # avoid matching escaped %
    %
    [#0\- +]*          # conversion flag
    (?:\d+|\*)?        # minimum field width
    (?:\.(?:\d+|\*))?  # precision
    [hlL]?             # length modifier
    [bcdeEfFgGnorsxX]  # conversion type
""",
    re.VERBOSE,
)
REPR_REGEXP = re.compile(r"%(?:\(\w+\))?r")

ERRORS_REQUIRING_GETTEXT = frozenset(
    {
        "UserError",
        "ValidationError",
        "AccessError",
        "AccessDenied",
        "MissingError",
    }
)


@dataclass
class Violation:
    """A single gettext warning."""

    lineno: int
    col_offset: int
    rule: str
    message: str = ""


def _get_call_name(node: ast.Call) -> str:
    """Extract the function/method name from a Call node."""
    match node.func:
        case ast.Name(id=name):
            return name
        case ast.Attribute(attr=name):
            return name
    return ""


def _is_whitelisted_argument(arg: ast.expr) -> bool:
    """Check if *arg* is unlikely to be a raw untranslated string.

    Whitelisted patterns: variables, attributes, subscripts, calls,
    conditional expressions with whitelisted branches, boolean ops, binops.
    """
    match arg:
        case ast.Name() | ast.Attribute() | ast.Subscript() | ast.Call():
            return True
        case ast.IfExp(body=body, orelse=orelse):
            return _is_whitelisted_argument(body) and _is_whitelisted_argument(orelse)
        case ast.BoolOp(values=values):
            return all(_is_whitelisted_argument(v) for v in values)
        case ast.BinOp(left=left, right=right):
            return _is_whitelisted_argument(left) or _is_whitelisted_argument(right)
    return False


def check(tree: ast.Module, filepath: str = "") -> Iterator[Violation]:
    """Walk *tree* and yield gettext violations.

    Files whose path contains ``/test_`` or ``/tests/`` are skipped
    (same as the original pylint checker).
    """
    if "/test_" in filepath or "/tests/" in filepath:
        return

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        name = _get_call_name(node)
        if not name:
            continue

        # Rule: missing-gettext — error constructors with raw string first arg
        if name in ERRORS_REQUIRING_GETTEXT and node.args:
            first_arg = node.args[0]
            if not _is_whitelisted_argument(first_arg):
                yield Violation(
                    node.lineno,
                    node.col_offset,
                    "missing-gettext",
                    f"Static string passed to {name} without gettext call.",
                )
                continue

        # Rules: gettext-variable, gettext-placeholders, gettext-repr
        if name not in ("_", "_lt"):
            continue

        first_arg = node.args[0] if node.args else None

        if not (
            isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str)
        ):
            yield Violation(
                node.lineno,
                node.col_offset,
                "gettext-variable",
                "Bad usage of _, _lt function.",
            )
            continue

        if len(PLACEHOLDER_REGEXP.findall(first_arg.value)) >= 2:
            yield Violation(
                first_arg.lineno,
                first_arg.col_offset,
                "gettext-placeholders",
                "Usage of _, _lt function with multiple unnamed placeholders.",
            )

        if re.search(REPR_REGEXP, first_arg.value):
            yield Violation(
                first_arg.lineno,
                first_arg.col_offset,
                "gettext-repr",
                "Usage of %r in _, _lt function.",
            )
