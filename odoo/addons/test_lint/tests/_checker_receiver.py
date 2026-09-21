import ast
from collections.abc import Iterator
from dataclasses import dataclass

OPEN_AUTH = frozenset({"public", "none"})


@dataclass
class Violation:
    lineno: int
    col_offset: int
    message: str


def _route_keywords(function: ast.FunctionDef) -> dict[str, object] | None:
    for decorator in function.decorator_list:
        if not isinstance(decorator, ast.Call):
            continue
        func = decorator.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        if name != "route":
            continue
        return {
            keyword.arg: keyword.value.value
            for keyword in decorator.keywords
            if keyword.arg and isinstance(keyword.value, ast.Constant)
        }
    return None


def check(tree: ast.Module) -> Iterator[Violation]:
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        keywords = _route_keywords(node)
        if keywords is None:
            continue
        if keywords.get("auth") not in OPEN_AUTH or keywords.get("csrf") is not False:
            continue
        yield Violation(
            node.lineno,
            node.col_offset,
            f"{node.name}: auth={keywords.get('auth')!r} with csrf=False takes calls "
            "from machines without declaring who may make them",
        )
