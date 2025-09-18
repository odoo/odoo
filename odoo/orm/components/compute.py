"""Standalone compute-scheduling engine for the ORM.

This module provides :class:`ComputeEngine`, an isolated data structure
that manages pending field recomputations and field protection scopes.
It has **no dependency** on Environment, BaseModel, or database cursors,
making it fully testable with pure Python unit tests.

The engine tracks:

* **Pending recomputations** — ``{field: set_of_record_ids}`` marking which
  stored-computed fields need recomputation on which records.
* **Field protection** — a stack of ``{field: frozenset_of_ids}`` scopes
  that suppress recomputation/invalidation during write operations.

Usage from Transaction::

    engine = ComputeEngine()
    engine.schedule(field, record_ids)
    engine.mark_done(field, record_ids)
    engine.push_protection()
    engine.protect(field, frozenset(record_ids))
    engine.pop_protection()
"""

from collections import defaultdict
from collections.abc import Collection, Iterable, Iterator


class _StackMap:
    """Minimal stack of mappings for field protection scopes.

    Equivalent to ``odoo.libs.collections.misc.StackMap`` but without the
    Odoo import dependency, so the component remains standalone and testable
    with pure Python (see ``components/pytest.ini``).

    This intentional duplication is the cost of standalone testability:
    importing from ``odoo.libs`` would trigger the full ``odoo`` package
    init chain, defeating the purpose of the components package.

    Lookups search from top (most recent) to bottom.  Mutations affect
    the topmost mapping only.
    """

    __slots__ = ("_maps",)

    def __init__(self) -> None:
        self._maps: list[dict] = []

    def get(self, key, default=None):
        for mapping in reversed(self._maps):
            try:
                return mapping[key]
            except KeyError:
                pass
        return default

    def __contains__(self, key) -> bool:
        return any(key in m for m in self._maps)

    def __iter__(self) -> Iterator:
        return iter({key for m in self._maps for key in m})

    def pushmap(self, m: dict | None = None) -> None:
        self._maps.append(m if m is not None else {})

    def popmap(self) -> dict:
        return self._maps.pop()

    def __setitem__(self, key, value) -> None:
        self._maps[-1][key] = value

    def __getitem__(self, key):
        for mapping in reversed(self._maps):
            try:
                return mapping[key]
            except KeyError:
                pass
        raise KeyError(key)

    def __len__(self) -> int:
        return sum(1 for _ in self)


class ComputeEngine:
    """Manages pending recomputations and field protection.

    Testable without database — operates on field keys (any hashable) and
    record IDs (any hashable, typically ``int`` or ``NewId``).

    Internal data structures:

    * ``_pending``: ``defaultdict(set_factory)`` — ``{field: mutable_set_of_ids}``
    * ``_protected``: ``_StackMap`` — ``{field: frozenset_of_ids}``

    The ``_pending`` defaultdict uses a configurable factory (default:
    ``set``) so Transaction can pass ``OrderedSet`` for deterministic
    recomputation order.
    """

    __slots__ = ("_pending", "_protected")

    def __init__(self, pending_factory: type | None = None) -> None:
        self._pending: defaultdict = defaultdict(pending_factory or set)
        self._protected = _StackMap()

    # ------------------------------------------------------------------
    # Raw data access
    # ------------------------------------------------------------------

    @property
    def pending(self) -> defaultdict:
        """The raw pending-recomputation dict: ``{field: mutable_set_of_ids}``.

        Exposed for callers that need direct dict access — primarily
        :class:`RecomputeScheduler`, which reads it as a ``marked`` set
        for cycle detection when ``before=True``, and
        :meth:`~CacheMixin.modified`, which applies scheduler results
        via :meth:`schedule`.
        """
        return self._pending

    # ------------------------------------------------------------------
    # Scheduling
    # ------------------------------------------------------------------

    def schedule(self, field, ids: Iterable) -> None:
        """Mark *field* for recomputation on *ids*."""
        self._pending[field].update(ids)

    def mark_done(self, field, ids: Iterable) -> None:
        """Mark *field* as computed on *ids*.

        Removes *ids* from the pending set.  If the set becomes empty,
        the field entry is deleted to avoid accumulation.
        """
        pending = self._pending.get(field)
        if pending is None:
            return
        pending.difference_update(ids)
        if not pending:
            del self._pending[field]

    def is_pending(self, field, record_id) -> bool:
        """Return whether *record_id* needs recomputation for *field*."""
        return record_id in self._pending.get(field, ())

    def pending_ids(self, field):
        """Return the set of pending record IDs for *field* (may be empty)."""
        return self._pending.get(field, ())

    def pending_fields(self) -> Collection:
        """Return a view of fields with pending recomputations."""
        return self._pending.keys()

    def has_pending(self) -> bool:
        """Return whether any field has pending recomputations."""
        return bool(self._pending)

    def has_pending_field(self, field) -> bool:
        """Return whether *field* has any pending recomputations.

        Equivalent to ``bool(pending_ids(field))`` but avoids creating
        an intermediate return value — important for the ``Field.__get__``
        hot path where this is checked on every attribute access.
        """
        return field in self._pending

    def pending_real_fields(self) -> list:
        """Return fields with at least one real (truthy) pending record ID.

        Filters out fields where only NewIds (falsy) are pending, since
        new records are not recomputed by the fixpoint loop.
        """
        return [field for field, ids in self._pending.items() if any(ids)]

    def discard_field(self, field) -> None:
        """Remove *field* entirely from pending recomputations.

        No-op if the field is not pending.  Used when a field is deleted
        from the registry (e.g. ``ir.model.fields.unlink``).
        """
        self._pending.pop(field, None)

    def prune_empty(self) -> None:
        """Remove fields with empty pending sets.

        Called after recomputation to avoid accumulation of empty entries.
        """
        for field in [f for f in self._pending if not self._pending[f]]:
            del self._pending[field]

    # ------------------------------------------------------------------
    # Protection
    # ------------------------------------------------------------------

    def is_protected(self, field, record_id) -> bool:
        """Return whether *record_id* is protected for *field*."""
        return record_id in (self._protected.get(field) or ())

    def protected_ids(self, field) -> frozenset:
        """Return the set of protected IDs for *field*."""
        return self._protected.get(field) or frozenset()

    def push_protection(self) -> None:
        """Push a new protection scope onto the stack."""
        self._protected.pushmap()

    def pop_protection(self) -> dict:
        """Pop the most recent protection scope."""
        return self._protected.popmap()

    def protect(self, field, ids: frozenset) -> None:
        """Protect *ids* for *field* in the current scope.

        Merges with any existing protection for *field* in the current scope.
        """
        existing = self._protected.get(field)
        self._protected[field] = existing.union(ids) if existing else ids

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Clear all pending computations (protection is NOT cleared)."""
        self._pending.clear()

    def clear_all(self) -> None:
        """Clear everything: pending and protection."""
        self._pending.clear()
        self._protected._maps.clear()

    def __repr__(self) -> str:
        n_fields = len(self._pending)
        n_entries = sum(len(ids) for ids in self._pending.values())
        n_scopes = len(self._protected._maps)
        return f"<ComputeEngine pending={n_fields}f/{n_entries}e scopes={n_scopes}>"
