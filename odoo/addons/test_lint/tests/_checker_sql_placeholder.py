import ast
import re
from collections.abc import Iterator
from dataclasses import dataclass

EXECUTORS = frozenset({"execute", "executemany", "execute_query", "execute_values"})
BUILDERS = frozenset({"SQL", "literal"})

SHAPES = (
    (re.compile(r"\bIN\s*%s", re.IGNORECASE), "IN %s"),
    (re.compile(r"\bINTERVAL\s*%s", re.IGNORECASE), "INTERVAL %s"),
)


@dataclass
class Violation:
    lineno: int
    col_offset: int
    message: str


def _statement_literals(call: ast.Call) -> list[ast.Constant]:
    """The string literals making up the statement, unless SQL() builds it."""
    if not call.args:
        return []
    literals = []
    for node in ast.walk(call.args[0]):
        if isinstance(node, ast.Call):
            name = getattr(node.func, "attr", getattr(node.func, "id", ""))
            if name in BUILDERS:
                return []
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            literals.append(node)
    return literals


def check(tree: ast.Module) -> Iterator[Violation]:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if getattr(node.func, "attr", getattr(node.func, "id", "")) not in EXECUTORS:
            continue
        for literal in _statement_literals(node):
            for pattern, shape in SHAPES:
                if pattern.search(literal.value):
                    yield Violation(
                        literal.lineno,
                        literal.col_offset,
                        f"`{shape}` binds a parameter where PostgreSQL parses "
                        f"syntax, so the statement never runs: build it with "
                        f"SQL() (a tuple expands, SQL.literal inlines) or pass "
                        f"a value the driver adapts",
                    )
