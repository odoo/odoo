import ast
from collections.abc import Iterator
from dataclasses import dataclass

OVERLOAD = frozenset({"overload"})
PROPERTY = frozenset({"property", "cached_property"})
RE_DECORATED = frozenset({"setter", "deleter", "getter"})
DISPATCH = frozenset({"register", "singledispatchmethod"})


@dataclass
class Violation:
    lineno: int
    col_offset: int
    message: str


def _decorator_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    names = set()
    for decorator in node.decorator_list:
        expr = decorator.func if isinstance(decorator, ast.Call) else decorator
        while isinstance(expr, ast.Attribute):
            names.add(expr.attr)
            expr = expr.value
        if isinstance(expr, ast.Name):
            names.add(expr.id)
    return names


def _redecorates(node: ast.FunctionDef | ast.AsyncFunctionDef, name: str) -> bool:
    for decorator in node.decorator_list:
        match decorator:
            case ast.Attribute(value=ast.Name(id=owner), attr=attr) if (
                attr in RE_DECORATED and owner == name
            ):
                return True
    return False


def _is_legitimate(definitions: list[ast.FunctionDef | ast.AsyncFunctionDef]) -> bool:
    decorators = [_decorator_names(node) for node in definitions]
    if all(names & OVERLOAD for names in decorators[:-1]):
        return True
    # `@other.setter` above a second `f` re-decorates `other`, not `f`: the
    # first `f` dies exactly as it would under a bare redefinition.
    if decorators[0] & PROPERTY and all(
        _redecorates(node, definitions[0].name) for node in definitions[1:]
    ):
        return True
    return "singledispatchmethod" in decorators[0] and all(
        names & DISPATCH for names in decorators[1:]
    )


def check(tree: ast.Module, nodes=None) -> Iterator[Violation]:
    for node in nodes if nodes is not None else ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        definitions: dict[str, list] = {}
        for statement in node.body:
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                definitions.setdefault(statement.name, []).append(statement)
        for name, found in definitions.items():
            if len(found) < 2 or _is_legitimate(found):
                continue
            shadowed = ", ".join(str(one.lineno) for one in found[:-1])
            yield Violation(
                found[-1].lineno,
                found[-1].col_offset,
                f"{node.name}.{name} is defined again here, so the definition"
                f" at line {shadowed} never runs",
            )
