"""Layer 1 facade — unified cache + compute operations.

:class:`OrmCore` composes :class:`FieldCache` and :class:`ComputeEngine`
behind a single flat API, eliminating the multi-attribute traversal chains
that internal ORM consumers currently navigate::

    # Before (3 attr lookups + method):
    env.transaction.compute_engine.has_pending_field(field)
    env.transaction.cache_store.get_field_data(field)

    # After (1 attr lookup + method):
    env._core.has_pending(field)
    env._core.field_data(field)

This is the **Layer 1** of the three-layer ORM architecture:

- Layer 1 (Core): cache, compute, triggers — pure data, no I/O
- Layer 2 (Persistence): SQL, cursors, fetch, write — DB ops
- Layer 3 (API): ACL, descriptors, translations — user-facing

OrmCore has **zero Odoo imports** and is fully testable with pure Python.
"""

from collections import defaultdict
from collections.abc import Collection, Iterable, Iterator

from .cache import FieldCache
from .compute import ComputeEngine


class OrmCore:
    """Unified Layer 1 facade over FieldCache + ComputeEngine.

    Designed as a single-object entry point that internal ORM code
    (``_read_format``, ``mapped``, ``filtered``, ``sorted``, ``modified``,
    ``flush_model``, ``_make_scalar_get``) accesses via ``env._core``.

    All methods delegate to the underlying components with zero overhead
    beyond the attribute lookup on *this* object.

    Usage::

        core = OrmCore()
        core.set_value(field, record_id, value)
        core.mark_dirty(field, [record_id])
        core.schedule(field, [record_id])

        # Hot-path cache resolve: pending check + dict get
        value = core.resolve(field, record_id)

        # Batch cache access: return the raw dict
        field_cache = core.field_data(field)
    """

    __slots__ = ("cache", "engine")

    def __init__(
        self,
        cache: FieldCache | None = None,
        engine: ComputeEngine | None = None,
    ) -> None:
        self.cache = cache if cache is not None else FieldCache()
        self.engine = engine if engine is not None else ComputeEngine()

    # ------------------------------------------------------------------
    # Cache: data access
    # ------------------------------------------------------------------

    def field_data(self, field) -> dict:
        """Return the live cache dict for *field* (``{id: value}``).

        This is the primary batch-access API.  Internal consumers that
        iterate over records (``_read_format``, ``mapped``, ``sorted``)
        call this once, then loop with ``dict.get``.

        Replaces: ``env.transaction.cache_store.get_field_data(field)``
        """
        return self.cache._data[field]

    def field_data_or_none(self, field) -> dict | None:
        """Return the cache dict for *field*, or ``None`` if nothing cached."""
        return self.cache._data.get(field)

    def get_value(self, field, record_id, default=None):
        """Return a single cached value, or *default*."""
        field_cache = self.cache._data.get(field)
        if field_cache is None:
            return default
        return field_cache.get(record_id, default)

    def set_value(self, field, record_id, value) -> None:
        """Set a single cached value."""
        self.cache._data[field][record_id] = value

    def insert_if_absent(self, field, ids: Iterable, values: Iterable) -> None:
        """Set values only for IDs not already cached (``setdefault`` in bulk)."""
        self.cache.insert_if_absent(field, ids, values)

    def update_batch(self, field, ids: tuple, value) -> None:
        """Set the same *value* for all *ids*."""
        self.cache.update_batch(field, ids, value)

    def pop_value(self, field, record_id, default=None):
        """Remove and return a cached value."""
        return self.cache.pop_value(field, record_id, default)

    # ------------------------------------------------------------------
    # Cache: dirty tracking
    # ------------------------------------------------------------------

    def mark_dirty(self, field, ids: Iterable) -> None:
        """Mark *ids* as dirty for *field*."""
        self.cache._dirty[field].update(ids)

    def get_dirty(self, field):
        """Return the dirty IDs for *field*, or ``None``."""
        return self.cache._dirty.get(field)

    def pop_dirty(self, field):
        """Remove and return the dirty IDs for *field*."""
        return self.cache._dirty.pop(field, None)

    def pop_dirty_for_model(self, model_name: str) -> dict:
        """Pop all dirty fields belonging to *model_name*."""
        return self.cache.pop_dirty_for_model(model_name)

    def has_dirty_field(self, field) -> bool:
        """Return whether *field* has any dirty entries."""
        return bool(self.cache._dirty.get(field))

    def is_any_dirty(self) -> bool:
        """Return whether any field has dirty entries."""
        return bool(self.cache._dirty)

    def iter_dirty_fields(self) -> Iterator:
        """Iterate over fields that have dirty entries."""
        return iter(self.cache._dirty)

    # ------------------------------------------------------------------
    # Cache: patches (x2many)
    # ------------------------------------------------------------------

    def add_patch(self, field, record_id, new_id) -> None:
        """Record a deferred x2many addition."""
        self.cache.add_patch(field, record_id, new_id)

    def get_patches(self, field) -> dict | None:
        """Return the patches dict for *field*, or ``None``."""
        return self.cache.get_patches(field)

    # ------------------------------------------------------------------
    # Cache: invalidation
    # ------------------------------------------------------------------

    def invalidate_field(self, field, ids: Collection | None = None) -> None:
        """Invalidate cached values for *field*."""
        self.cache.invalidate_field(field, ids)

    def invalidate_all(self) -> None:
        """Clear all cached data (but not dirty or patches)."""
        self.cache.invalidate_all()

    # ------------------------------------------------------------------
    # Cache: iteration
    # ------------------------------------------------------------------

    def iter_fields(self) -> Iterator:
        """Iterate over fields with cached data."""
        return iter(self.cache._data)

    def iter_field_items(self) -> Iterator:
        """Iterate over ``(field, cache_dict)`` pairs."""
        return iter(self.cache._data.items())

    def has_field(self, field) -> bool:
        """Return whether *field* has cached data."""
        return field in self.cache._data

    # ------------------------------------------------------------------
    # Compute: scheduling
    # ------------------------------------------------------------------

    def schedule(self, field, ids: Iterable) -> None:
        """Mark *field* for recomputation on *ids*."""
        self.engine.schedule(field, ids)

    def mark_done(self, field, ids: Iterable) -> None:
        """Mark *field* as computed on *ids*."""
        self.engine.mark_done(field, ids)

    def is_pending(self, field, record_id) -> bool:
        """Check whether a specific *record_id* needs recomputation for *field*."""
        return record_id in self.engine._pending.get(field, ())

    def has_pending(self, field) -> bool:
        """Fast check: does *field* have pending recomputations?

        This is the hot-path guard in ``_make_scalar_get`` and
        ``ensure_computed``.  A single ``__contains__`` on the pending dict.
        """
        return field in self.engine._pending

    def has_any_pending(self) -> bool:
        """Return whether any field has pending recomputations."""
        return bool(self.engine._pending)

    def pending_ids(self, field):
        """Return the set of pending record IDs for *field*."""
        return self.engine._pending.get(field, ())

    def pending_fields(self) -> Collection:
        """Return a view of fields with pending recomputations."""
        return self.engine._pending.keys()

    @property
    def pending(self) -> defaultdict:
        """Raw pending dict — for RecomputeScheduler cycle detection."""
        return self.engine._pending

    def pending_real_fields(self) -> list:
        """Fields with at least one real (truthy) pending record ID."""
        return self.engine.pending_real_fields()

    def discard_field(self, field) -> None:
        """Remove *field* from pending recomputations."""
        self.engine._pending.pop(field, None)

    # ------------------------------------------------------------------
    # Compute: protection
    # ------------------------------------------------------------------

    def is_protected(self, field, record_id) -> bool:
        """Return whether *record_id* is protected for *field*."""
        return self.engine.is_protected(field, record_id)

    def protected_ids(self, field) -> frozenset:
        """Return the set of protected IDs for *field*."""
        return self.engine.protected_ids(field)

    def push_protection(self) -> None:
        """Push a new protection scope."""
        self.engine.push_protection()

    def pop_protection(self) -> dict:
        """Pop the most recent protection scope."""
        return self.engine.pop_protection()

    def protect(self, field, ids: frozenset) -> None:
        """Protect *ids* for *field* in the current scope."""
        self.engine.protect(field, ids)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Clear all cached data, dirty flags, patches, and pending computations."""
        self.cache.clear()
        self.engine.clear()

    def clear_cache(self) -> None:
        """Clear only cache data + dirty + patches (not compute state)."""
        self.cache.clear()

    def clear_compute(self) -> None:
        """Clear only pending computations (not cache)."""
        self.engine.clear()

    def __repr__(self) -> str:
        return f"<OrmCore {self.cache!r} {self.engine!r}>"
