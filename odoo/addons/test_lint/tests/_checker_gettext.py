import ast
import re
from collections.abc import Iterator
from dataclasses import dataclass

PLACEHOLDER_REGEXP = re.compile(
    r"""
    # Step over any run of escaped `%%` first, so the `%` that follows one is
    # still seen. A bare `(?<!%)` could only reject the second half of a `%%`
    # pair, which also rejected a real placeholder immediately after one:
    # `"%%%s"` -- an escaped percent then a substitution -- read as zero
    # placeholders. The lookbehind stays, to anchor the run at its true start.
    (?<!%)(?:%%)*
    %
    [#0\- +]*            # conversion flag
    (?:\d+|\*)?          # minimum field width
    (?:\.(?:\d+|\*))?    # precision
    [hlL]?               # length modifier
    # The conversion types Python's `%` operator actually accepts, no more and
    # no fewer. The set here was `[bcdeEfFgGnorsxX]`, which is neither: it
    # carried `b` and `n`, which raise `ValueError: unsupported format
    # character`, and it omitted `i`, `u` and `a`, so `_("%i of %i")` counted
    # zero placeholders and the rule that exists to catch exactly that pair
    # said nothing.
    [diouxXeEfFgGcrsa]   # conversion type
""",
    re.VERBOSE,
)
REPR_REGEXP = re.compile(r"(?<!%)(?:%%)*%(?:\(\w+\))?r")

ERRORS_REQUIRING_GETTEXT = frozenset(
    {
        "UserError",
        "ValidationError",
        "AccessError",
        "AccessDenied",
        "MissingError",
        "RedirectWarning",
    }
)

ERRORS_REFUSING_GETTEXT = frozenset(
    {
        "ArithmeticError",
        "AssertionError",
        "AttributeError",
        "BufferError",
        "EOFError",
        "FloatingPointError",
        "IndexError",
        "KeyError",
        "MemoryError",
        "NameError",
        "NotImplementedError",
        "OverflowError",
        "RecursionError",
        "ReferenceError",
        "RuntimeError",
        "StopIteration",
        "SyntaxError",
        "SystemError",
        "TypeError",
        "UnboundLocalError",
        "ValueError",
        "ZeroDivisionError",
    }
)


@dataclass
class Violation:
    lineno: int
    col_offset: int
    rule: str
    message: str = ""


def _get_call_name(node: ast.Call) -> str:
    match node.func:
        case ast.Name(id=name):
            return name
        case ast.Attribute(attr=name):
            return name
    return ""


def _get_call_name_if_gettext(node: ast.expr) -> str:
    match node:
        case ast.Call(func=ast.Attribute(attr="format", value=receiver)):
            return _get_call_name_if_gettext(receiver)
        case ast.BinOp(op=ast.Mod(), left=left):
            return _get_call_name_if_gettext(left)
    if isinstance(node, ast.Call) and _get_call_name(node) in ("_", "_lt"):
        return _get_call_name(node)
    return ""


def _is_raw_text(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def _is_whitelisted_argument(arg: ast.expr) -> bool:
    match arg:
        case ast.Name() | ast.Attribute() | ast.Subscript() | ast.Call():
            return True
        case ast.IfExp(body=body, orelse=orelse):
            return _is_whitelisted_argument(body) and _is_whitelisted_argument(orelse)
        case ast.BoolOp(values=values):
            return all(_is_whitelisted_argument(v) for v in values)
        case ast.BinOp(op=ast.Add(), left=left, right=right) if _is_raw_text(
            left
        ) or _is_raw_text(right):
            return False
        case ast.BinOp(left=left, right=right) if _is_raw_text(left) or _is_raw_text(
            right
        ):
            return False
        case ast.BinOp(left=left, right=right):
            return _is_whitelisted_argument(left) or _is_whitelisted_argument(right)
    return False


def check(tree: ast.Module, nodes=None) -> Iterator[Violation]:
    for node in nodes if nodes is not None else ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        name = _get_call_name(node)
        if not name:
            continue

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

        if name in ERRORS_REFUSING_GETTEXT and node.args:
            if _get_call_name_if_gettext(node.args[0]):
                yield Violation(
                    node.lineno,
                    node.col_offset,
                    "gettext-developer-error",
                    f"{name} reaches a reader as a traceback, not as UI; drop the "
                    f"gettext call and use an f-string.",
                )
                continue

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
