import ast
from collections.abc import Iterator
from dataclasses import dataclass

# A route whose caller is a program rather than a browser: its parameters are
# a contract, so they are declared and coerced instead of arriving as strings.
MACHINE_AUTH = frozenset({"bearer", "receiver"})
MACHINE_TYPE = "json2"


@dataclass
class Violation:
    lineno: int
    col_offset: int
    message: str


def _route_calls(function: ast.FunctionDef) -> Iterator[ast.Call]:
    for decorator in function.decorator_list:
        if not isinstance(decorator, ast.Call):
            continue
        func = decorator.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        if name == "route":
            yield decorator


def _constants(call: ast.Call) -> dict[str, object]:
    return {
        keyword.arg: keyword.value.value
        for keyword in call.keywords
        if keyword.arg and isinstance(keyword.value, ast.Constant)
    }


def _undeclared(function: ast.FunctionDef) -> list[str]:
    args = function.args
    named = [*args.posonlyargs, *args.args, *args.kwonlyargs][1:]
    return [arg.arg for arg in named if arg.annotation is None]


def check(tree: ast.Module) -> Iterator[Violation]:
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        for call in _route_calls(node):
            keywords = _constants(call)
            reached_as = (
                f"type={MACHINE_TYPE!r}"
                if keywords.get("type") == MACHINE_TYPE
                else f"auth={keywords.get('auth')!r}"
            )
            if (
                keywords.get("type") != MACHINE_TYPE
                and keywords.get("auth") not in MACHINE_AUTH
            ):
                continue
            if keywords.get("typed") is not True:
                yield Violation(
                    node.lineno,
                    node.col_offset,
                    f"{node.name}: {reached_as} takes its parameters from a "
                    "program without declaring them (typed=True)",
                )
                continue
            undeclared = _undeclared(node)
            if undeclared:
                yield Violation(
                    node.lineno,
                    node.col_offset,
                    f"{node.name}: {reached_as} is typed but "
                    f"{', '.join(undeclared)} carries no annotation",
                )
