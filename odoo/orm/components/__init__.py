"""Standalone ORM components — testable without database or Odoo server.

These components encapsulate the core data structures and algorithms of
the ORM (cache, compute scheduling, storage, field metadata, dependency
graph, flush scheduling) behind clean APIs that can be unit-tested with
pure Python.
"""

from .cache import FieldCache
from .compute import ComputeEngine
from .core import OrmCore
from .field_spec import FieldSpec
from .model_graph import ModelGraph, TriggerTree
from .recompute import RecomputeScheduler
from .storage import DictBackend, StorageBackend
from .testing import FieldDef, InMemoryEnvironment, ModelDef
from .unit_of_work import LoopResult, UnitOfWork

__all__ = [
    # Data structures
    "ComputeEngine",
    "DictBackend",
    "FieldCache",
    # Testing
    "FieldDef",
    "FieldSpec",
    "InMemoryEnvironment",
    # Flush scheduling
    "LoopResult",
    "ModelDef",
    "ModelGraph",
    # Layer 1 facade
    "OrmCore",
    # Recomputation scheduling
    "RecomputeScheduler",
    "StorageBackend",
    "TriggerTree",
    "UnitOfWork",
]
