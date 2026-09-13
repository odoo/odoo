import ast
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass

# Hook attributes that name a method, with the family prefix §2.4.1 reserves.
HOOK_PREFIXES = {
    "compute": "_compute_",
    "inverse": "_inverse_",
    "search": "_search_",
    "selection": "_selection_",
}

# A call whose value is meant per record, so `default=` wants the callable,
# not what it returned once at import.
CALLED_ONCE_AT_IMPORT = frozenset(
    {
        "today",
        "now",
        "utcnow",
        "context_today",
        "context_now",
        "uuid4",
        "uuid1",
        "token_hex",
        "token_urlsafe",
        "token_bytes",
        "random",
        "randint",
        "choice",
        "time",
        "_",
    }
)

# Where the label sits among the positional arguments of each field class,
# after the ones that come before it in its __init__ signature.
_STRING_POSITION = {
    "Many2one": 1,
    "One2many": 2,
    "Many2many": 4,
    "Selection": 1,
    "Reference": 1,
    "Count": 1,
}


@dataclass
class Violation:
    lineno: int
    col_offset: int
    rule: str
    message: str


def is_field_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "fields"
        and node.func.attr[:1].isupper()
    )


def keywords(call: ast.Call) -> dict[str, ast.expr]:
    return {keyword.arg: keyword.value for keyword in call.keywords if keyword.arg}


def string_argument(call: ast.Call) -> ast.expr | None:
    if (value := keywords(call).get("string")) is not None:
        return value
    position = _STRING_POSITION.get(call.func.attr, 0)
    if len(call.args) > position and not isinstance(call.args[position], ast.Starred):
        return call.args[position]
    return None


def selection_argument(call: ast.Call) -> ast.expr | None:
    if (value := keywords(call).get("selection")) is not None:
        return value
    if call.func.attr == "Selection" and call.args:
        return call.args[0]
    return None


def _callee_tail(node: ast.expr) -> str:
    match node:
        case ast.Attribute(attr=attr):
            return attr
        case ast.Name(id=name):
            return name
    return ""


def _constant_str(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _check_default(name: str, call: ast.Call) -> Iterator[Violation]:
    default = keywords(call).get("default")
    if not isinstance(default, ast.Call):
        return
    tail = _callee_tail(default.func)
    if tail in CALLED_ONCE_AT_IMPORT:
        yield Violation(
            default.lineno,
            default.col_offset,
            "default-evaluated-at-import",
            f"{name}: default={ast.unparse(default)} ran once, when the module "
            f"was imported; pass the callable, default={ast.unparse(default.func)}",
        )


def _check_selection(name: str, call: ast.Call) -> Iterator[Violation]:
    selection = selection_argument(call)
    if not isinstance(selection, (ast.List, ast.Tuple)):
        return
    keys = [
        _constant_str(entry.elts[0])
        for entry in selection.elts
        if isinstance(entry, (ast.Tuple, ast.List)) and len(entry.elts) == 2
    ]
    for key, count in Counter(keys).items():
        if key is not None and count > 1:
            yield Violation(
                selection.lineno,
                selection.col_offset,
                "selection-duplicate-key",
                f"{name}: selection key {key!r} appears {count} times; dict() "
                "keeps the last label and the others are dead",
            )


def _check_hooks(name: str, call: ast.Call) -> Iterator[Violation]:
    for attribute, prefix in HOOK_PREFIXES.items():
        method = _constant_str(keywords(call).get(attribute))
        if method is not None and not method.startswith(prefix):
            yield Violation(
                call.lineno,
                call.col_offset,
                "field-hook-prefix",
                f"{name}: {attribute}={method!r} names a method outside the "
                f"{prefix}* family that {attribute}= is reserved for",
            )


def bound_names(statement: ast.stmt) -> list[str]:
    match statement:
        case ast.Assign(targets=targets):
            return [t.id for t in targets if isinstance(t, ast.Name)]
        case ast.AnnAssign(target=ast.Name(id=name), value=value) if value is not None:
            return [name]
    return []


def _check_class(node: ast.ClassDef) -> Iterator[Violation]:
    bound: dict[str, int] = {}
    for statement in node.body:
        targets = bound_names(statement)
        if not targets:
            continue
        is_field = is_field_call(statement.value)
        for target in targets:
            if target in bound and (is_field or bound[target] < 0):
                yield Violation(
                    statement.lineno,
                    statement.col_offset,
                    "field-redeclared",
                    f"{node.name}.{target} is declared again here, so the "
                    f"declaration at line {abs(bound[target])} is dead",
                )
            bound[target] = -statement.lineno if is_field else statement.lineno
        if not is_field or len(targets) != 1:
            continue
        name = targets[0]
        call = statement.value
        yield from _check_default(name, call)
        yield from _check_selection(name, call)
        yield from _check_hooks(name, call)


def check(tree: ast.Module, nodes=None) -> Iterator[Violation]:
    for node in nodes if nodes is not None else ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            yield from _check_class(node)
