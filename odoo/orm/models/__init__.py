"""
ORM Models package.

This package provides the base classes for Odoo models:
- BaseModel: The base class for all models
- Model: For regular database-persisted models
- AbstractModel: Alias for BaseModel (for abstract models)
- TransientModel: For temporary records with auto-cleanup
- MetaModel: Metaclass for model definitions

Table object classes for declarative SQL constraints and indexes:
- Constraint: SQL table constraint (CHECK, FOREIGN KEY, UNIQUE)
- Index: SQL index on the table
- UniqueIndex: Unique SQL index on the table

For constants, import from ``odoo.orm.primitives`` or ``odoo.orm.constants``.
For utilities, import from ``odoo.orm.helpers``, ``odoo.orm.parsing``, or ``odoo.orm.validation``.
"""

# Model classes
from .base import (
    AbstractModel,
    BaseModel,
    Model,
)
from .metaclass import MetaModel

# Mixins (used internally by BaseModel, exported for subclass access)
from .mixins import (
    AccessMixin,
    IOMixin,
    ReadGroupMixin,
    SchemaMixin,
    TranslationMixin,
)

# Table object classes
from .table_objects import (
    Constraint,
    Index,
    TableObject,
    UniqueIndex,
)
from .transient import TransientModel
