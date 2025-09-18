"""
BaseModel mixins package - modular implementation of BaseModel functionality.

This package contains ALL mixins for the BaseModel class:

Core Operations:
- CrudMixin: Create, write, unlink, default_get (crud.py)
- CopyMixin: Record duplication — copy, copy_data, copy_translations (copy.py)
- IterationMixin: Record iteration and set operations (iteration.py)
- TraversalMixin: mapped, filtered, grouped, sorted, cycle detection (traversal.py)
- CacheMixin: Cache invalidation and recomputation (cache.py)
- EnvironmentMixin: Environment manipulation methods (env.py)
- LifecycleMixin: Hooks, archive, onchange, external IDs (lifecycle.py)

Data Access:
- ReadMixin: Read, fetch, field metadata operations (read.py)
- SearchMixin: Search, query, exists, locking operations (search.py)
- ReadGroupMixin: read_group operations (read_group/)

Features:
- TranslationMixin: Field translation methods (translation.py)
- SchemaMixin: Database schema management (schema.py)
- IOMixin: Import/export operations (io.py)
- AccessMixin: Access control methods (access.py)

Table Object Classes are in ``models/table_objects.py``.

The BaseModel class in models/base.py inherits from all these mixins.
"""

# Core operation mixins
from .access import AccessMixin
from .cache import CacheMixin
from .copy import CopyMixin
from .crud import CrudMixin
from .env import EnvironmentMixin
from .io import IOMixin
from .iteration import IterationMixin
from .lifecycle import LifecycleMixin
from .search import SearchMixin

# Data access mixins
from .read import ReadMixin
from .read_group import ReadGroupMixin
from .schema import SchemaMixin

# Feature mixins
from .translation import TranslationMixin
from .traversal import TraversalMixin

__all__ = [
    "AccessMixin",
    "CacheMixin",
    "CopyMixin",
    # Core operation mixins
    "CrudMixin",
    "EnvironmentMixin",
    "IOMixin",
    "IterationMixin",
    "LifecycleMixin",
    "ReadGroupMixin",
    # Data access mixins
    "ReadMixin",
    "SchemaMixin",
    "SearchMixin",
    # Feature mixins
    "TranslationMixin",
    "TraversalMixin",
]
