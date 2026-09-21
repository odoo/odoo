import ast
from collections.abc import Iterator
from dataclasses import dataclass

# The schemes `ir.http` answers `auth=` with. base owns the session ones and
# the API key; integration owns the receiver. Everything else is data on a
# receiver row, never a fourth method on ir.http.
OWNED_METHODS = frozenset({"user", "none", "public", "bearer", "receiver"})
OWNER_MODULES = frozenset({"base", "integration", "test_auth_custom"})


@dataclass
class Violation:
    lineno: int
    col_offset: int
    message: str


def module_of(path: str) -> str:
    parts = path.split("/")
    for marker in ("addons",):
        while marker in parts:
            index = parts.index(marker)
            if index + 1 < len(parts):
                return parts[index + 1]
            parts = parts[index + 1 :]
    return ""


def check(tree: ast.Module, path: str) -> Iterator[Violation]:
    module = module_of(path)
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        if not node.name.startswith("_auth_method_"):
            continue
        scheme = node.name.removeprefix("_auth_method_")
        if module in OWNER_MODULES:
            continue
        if scheme in OWNED_METHODS:
            # An override of an owned scheme (website's `public`) keeps the
            # scheme; a new name is a new scheme.
            continue
        yield Violation(
            node.lineno,
            node.col_offset,
            f"{node.name}: a new `auth=` scheme outside base and integration",
        )
