import ast
from collections.abc import Iterator
from dataclasses import dataclass

OPEN_AUTH = frozenset({"public", "none"})

GATE_CALLS = frozenset(
    {
        "inspect_inbound_request",
        "_check_inbound_request",
        "check_inbound_auth",
        "_check_webhook_request",
        "_admit_mini_app_call",
        "admit",
        "_admit_checked_request",
        "admit_notification",
        "_admit_proxy_webhook",
    }
)


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


def _called_names(function: ast.FunctionDef) -> tuple[set[str], set[str]]:
    names, own_methods = set(), set()
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute):
            names.add(func.attr)
            if isinstance(func.value, ast.Name) and func.value.id in ("self", "cls"):
                own_methods.add(func.attr)
        elif isinstance(func, ast.Name):
            names.add(func.id)
    return names, own_methods


def _reaches_a_gate(name: str, methods: dict, seen: set[str]) -> bool:
    if name in seen or name not in methods:
        return False
    seen.add(name)
    names, own_methods = _called_names(methods[name])
    if names & GATE_CALLS:
        return True
    return any(_reaches_a_gate(method, methods, seen) for method in own_methods)


def check(tree: ast.Module) -> Iterator[Violation]:
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        methods = {
            statement.name: statement
            for statement in node.body
            if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef)
        }
        for name, function in methods.items():
            keywords = _route_keywords(function)
            if keywords is None:
                continue
            if (
                keywords.get("auth") not in OPEN_AUTH
                or keywords.get("csrf") is not False
            ):
                continue
            if _reaches_a_gate(name, methods, set()):
                continue
            yield Violation(
                function.lineno,
                function.col_offset,
                f"{name}: auth={keywords.get('auth')!r} and csrf=False, and no path "
                "through this controller reaches an inbound gate",
            )
