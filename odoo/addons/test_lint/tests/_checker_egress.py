import ast
import re
from collections.abc import Iterator
from dataclasses import dataclass

_REQUESTS_CALLS = frozenset(
    {
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "head",
        "options",
        "request",
        "Session",
        "session",
    }
)
_SECRET_NAME = re.compile(r"KEY|TOKEN|SECRET|PASSW|CREDENTIAL", re.IGNORECASE)


@dataclass
class Violation:
    lineno: int
    col_offset: int
    message: str


def _imports(tree: ast.Module) -> tuple[dict[str, str], dict[str, str]]:
    modules: dict[str, str] = {}
    names: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules[alias.asname or alias.name.split(".")[0]] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                names[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    return modules, names


def _dotted(node: ast.expr) -> str:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return ""


def _egress_target(call: ast.Call, modules, names) -> str | None:
    dotted = _dotted(call.func)
    if not dotted:
        return None
    head, _, rest = dotted.partition(".")
    if head in modules:
        dotted = f"{modules[head]}.{rest}" if rest else modules[head]
    elif head in names:
        dotted = f"{names[head]}.{rest}" if rest else names[head]
    else:
        return None
    module, _, attr = dotted.rpartition(".")
    if module == "requests" and attr in _REQUESTS_CALLS:
        return dotted
    if module == "requests.sessions" and attr in ("Session", "session"):
        return dotted
    if module == "httpx" or module.startswith("httpx."):
        return dotted
    if dotted == "urllib.request.urlopen":
        return dotted
    if dotted in ("zeep.Transport", "zeep.transports.Transport"):
        return dotted
    if dotted in ("boto3.client", "boto3.resource", "boto3.session.Session"):
        return dotted
    return None


def check_raw_egress(tree: ast.Module, nodes=None) -> Iterator[Violation]:
    modules, names = _imports(tree)
    for node in nodes if nodes is not None else ast.walk(tree):
        if isinstance(node, ast.Call):
            target = _egress_target(node, modules, names)
            if target:
                yield Violation(
                    node.lineno,
                    node.col_offset,
                    f"{target}() leaves Odoo outside ir.egress",
                )


def _is_os_environ(node: ast.expr) -> bool:
    return _dotted(node) == "os.environ"


def _secret_key(node: ast.expr | None) -> bool:
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and bool(_SECRET_NAME.search(node.value))
    )


def check_secret_in_environ(tree: ast.Module, nodes=None) -> Iterator[Violation]:
    message = "a secret written into os.environ is inherited by the whole worker"
    for node in nodes if nodes is not None else ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Subscript)
                    and _is_os_environ(target.value)
                    and _secret_key(target.slice)
                ):
                    yield Violation(node.lineno, node.col_offset, message)
        elif isinstance(node, ast.Call):
            dotted = _dotted(node.func)
            if dotted in ("os.environ.setdefault", "os.putenv") and node.args:
                if _secret_key(node.args[0]):
                    yield Violation(node.lineno, node.col_offset, message)
            elif dotted == "os.environ.update":
                for arg in node.args:
                    if isinstance(arg, ast.Dict) and any(
                        _secret_key(key) for key in arg.keys
                    ):
                        yield Violation(node.lineno, node.col_offset, message)
                if any(
                    keyword.arg and _SECRET_NAME.search(keyword.arg)
                    for keyword in node.keywords
                ):
                    yield Violation(node.lineno, node.col_offset, message)
