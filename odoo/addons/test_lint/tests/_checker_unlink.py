"""Unlink override checker using stdlib ``ast``.

Detects ``raise`` statements inside ``unlink()`` methods on ORM model
classes.  The recommended pattern is ``@api.ondelete(at_uninstall=False)``
on a separate method.

Replaces the former ``_odoo_checker_unlink_override.py`` (which required
``astroid`` + ``pylint``).
"""

import ast
from collections.abc import Iterator
from dataclasses import dataclass

# Base class names that indicate an ORM model.  In the astroid-based checker,
# ``node.ancestors()`` resolved the full MRO at analysis time.  With stdlib
# ``ast`` we can only inspect the literal base-class expressions, so we match
# any name containing "Model" (covers ``models.Model``, ``models.TransientModel``,
# ``models.AbstractModel``, ``BaseModel``).
_MODEL_BASE_NAMES = frozenset(
    {
        "Model",
        "TransientModel",
        "AbstractModel",
        "BaseModel",
    }
)


@dataclass
class Violation:
    """A single unlink-override warning."""

    lineno: int
    col_offset: int
    message: str = (
        "Raise inside unlink override. Use @api.ondelete(at_uninstall=False) instead."
    )


def _looks_like_model_class(node: ast.ClassDef) -> bool:
    """Heuristic: does *node* look like an ORM model class?

    Checks whether any base class expression mentions a known model name.
    Handles patterns like ``models.Model``, ``Model``, ``BaseModel``.
    """
    for base in node.bases:
        match base:
            case ast.Attribute(attr=attr) if attr in _MODEL_BASE_NAMES:
                return True
            case ast.Name(id=name) if name in _MODEL_BASE_NAMES:
                return True
    return False


def check(tree: ast.Module) -> Iterator[Violation]:
    """Walk *tree* and yield unlink-override violations."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if not _looks_like_model_class(node):
            continue

        for item in node.body:
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if item.name != "unlink":
                continue

            # Walk the unlink method body for raise statements
            for child in ast.walk(item):
                if isinstance(child, ast.Raise):
                    yield Violation(child.lineno, child.col_offset)
