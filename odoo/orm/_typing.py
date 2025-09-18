# ruff: noqa: F401
"""
Type aliases for the ORM.

This is the canonical location for composite ORM type aliases that depend
on multiple ORM layers:

- DomainType: Search domain (Domain object or list of tuples)
- ModelType: Generic type for model classes

Simple type aliases (Self, ContextType, ValuesType, IdType) live in
``odoo.orm.primitives`` which has zero ORM dependencies.

Note: This module is named _typing.py (with underscore) to avoid shadowing
Python's standard library 'types' module.

At runtime, this module only imports from ``primitives`` (Layer 0).
Cross-layer imports (Domain, BaseModel, etc.) are deferred to TYPE_CHECKING.
"""

import typing
from typing import Self

# Re-export from primitives for convenience (zero-dep, Layer 0)
from .primitives import ContextType, IdType, ValuesType

if typing.TYPE_CHECKING:
    from .domain import Domain
    from .fields import Field
    from .models import BaseModel
    from .primitives import CommandValue
    from .runtime import Environment, Registry

# Composite type aliases (PEP 695 — RHS lazily evaluated, no runtime import needed)
type DomainType = Domain | list[str | tuple[str, str, typing.Any]]
ModelType = typing.TypeVar("ModelType", bound="BaseModel")

__all__ = [
    "ContextType",
    "DomainType",
    "IdType",
    "ModelType",
    # Type aliases
    "Self",
    "ValuesType",
]
