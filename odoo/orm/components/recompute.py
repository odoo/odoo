"""Standalone recomputation scheduler for the ORM.

This module provides :class:`RecomputeScheduler`, a pure-data processor
that converts trigger traversal results into recomputation scheduling
decisions.  It has **no dependency** on Environment, BaseModel, or
database cursors, making it fully testable with pure Python unit tests.

The scheduler processes (field, ids) trigger entries — produced by the
trigger tree traversal in ``CacheMixin._modified_triggers`` — and decides
for each entry whether to:

* **Schedule recomputation** (stored-computed fields) — accumulated in
  :attr:`to_recompute`
* **Request cache invalidation** (non-stored computed fields) — accumulated
  in :attr:`to_invalidate`
* **Request recursive traversal** (recursive fields) — accumulated
  internally and retrieved via :meth:`pop_recursive_requests`

All protection subtraction and cycle detection is handled internally
using the :class:`ComputeEngine` (which is itself standalone).

Usage from CacheMixin::

    scheduler = RecomputeScheduler(compute_engine, marked=engine.pending)
    for field, records, create in trigger_entries:
        cached_ids = field._get_all_cache_ids(env) if ... else None
        recursive_ids = scheduler.process_entry(field, set(records._ids), create, cached_ids)
        if recursive_ids:
            # resolve inverse dependencies (DB-coupled)
            todo.append(records.browse(recursive_ids)._modified([field], create))
    # apply accumulated results
    for field, ids in scheduler.to_recompute.items():
        engine.schedule(field, ids)
    for field, ids in scheduler.to_invalidate:
        field._invalidate_cache(env, ids)
"""

import typing
from collections import defaultdict
from collections.abc import Mapping

if typing.TYPE_CHECKING:
    from .compute import ComputeEngine


class RecomputeScheduler:
    """Processes trigger entries into recomputation scheduling decisions.

    Pure-data processor.  Works with field-like keys (any hashable with
    ``recursive`` and ``is_stored_computed`` boolean attributes) and ID
    sets (any hashable, typically ``int`` or ``NewId``).  No Odoo,
    database, or recordset dependency.

    The scheduler accumulates results across multiple :meth:`process_entry`
    calls, enabling the caller to interleave trigger traversal (DB-coupled)
    with scheduling decisions (pure logic).

    :param compute_engine: standalone compute engine for protection checks
    :param marked: read-only mapping of ``{field: set_of_ids}`` representing
        fields already known to be pending.  Used for cycle detection in
        recursive stored-computed fields.  Pass ``engine.pending`` for
        ``before=True`` mode, or ``{}`` for ``before=False`` mode.
    """

    __slots__ = (
        "_engine",
        "_marked",
        "_seen_recursive",
        "to_invalidate",
        "to_recompute",
    )

    def __init__(
        self,
        compute_engine: ComputeEngine,
        marked: Mapping | None = None,
    ) -> None:
        self._engine = compute_engine
        self._marked = marked if marked is not None else {}
        self._seen_recursive: dict = defaultdict(set)
        self.to_recompute: dict = defaultdict(set)
        self.to_invalidate: list[tuple] = []

    def process_entry(
        self,
        field,
        ids: set | frozenset,
        create: bool = False,
        cached_ids: set | None = None,
    ) -> frozenset:
        """Process one trigger entry.

        Applies protection subtraction and cycle detection, then routes
        the entry to :attr:`to_recompute` or :attr:`to_invalidate`.

        :param field: field-like object with ``.recursive`` and
            ``.is_stored_computed`` boolean attributes
        :param ids: set of record IDs affected by the modification
        :param create: whether in record-creation context (unused by the
            scheduler itself, but threaded through to recursive requests)
        :param cached_ids: for recursive non-stored fields, the set of IDs
            that currently have cached data.  Only IDs present in this set
            are processed (others have nothing to invalidate).  Pass
            ``None`` to skip this filter.
        :returns: frozenset of IDs needing recursive trigger traversal.
            Empty frozenset if no recursion is needed.  The caller should
            resolve inverse dependencies for these IDs (DB-coupled) and
            feed the resulting entries back into the scheduler.
        """
        # 1. Subtract protected IDs — records currently being computed
        #    for this field should not be re-marked.
        protected = self._engine.protected_ids(field)
        if protected:
            ids = ids - protected
        if not ids:
            return frozenset()

        # 2. Handle recursive fields — cycle detection
        #
        # Both stored-computed and non-stored recursive fields need explicit
        # cycle detection to prevent infinite trigger loops in cyclic
        # hierarchies (e.g. parent_id cycles).
        #
        # For stored-computed: skip IDs in ``_marked`` (externally pending)
        #     and ``to_recompute`` (accumulated in this run).
        # For non-stored: skip IDs in ``_seen_recursive`` (processed earlier
        #     in this run), and filter to ``cached_ids`` (only invalidate
        #     what's actually cached).
        recursive_ids = frozenset()
        if field.recursive:
            if field.is_stored_computed:
                known = set()
                m = self._marked.get(field)
                if m:
                    known.update(m)
                r = self.to_recompute.get(field)
                if r:
                    known.update(r)
                if known:
                    ids = ids - known
            else:
                # Explicit cycle detection for non-stored recursive fields.
                # The original code relied on inline _invalidate_cache as an
                # implicit cycle breaker (removing IDs from cache prevented
                # re-processing).  Since invalidation is now deferred, we
                # track processed IDs explicitly.
                seen = self._seen_recursive.get(field)
                if seen:
                    ids = ids - seen
                if cached_ids is not None:
                    ids = ids & cached_ids
            if not ids:
                return frozenset()
            # Track these IDs to prevent re-processing in future entries
            self._seen_recursive[field].update(ids)
            recursive_ids = frozenset(ids)

        # 3. Route to recompute or invalidate
        if field.is_stored_computed:
            self.to_recompute[field].update(ids)
        else:
            self.to_invalidate.append((field, frozenset(ids)))

        return recursive_ids

    def clear(self) -> None:
        """Reset all accumulated results."""
        self.to_recompute.clear()
        self.to_invalidate.clear()
        self._seen_recursive.clear()

    def __repr__(self) -> str:
        n_recompute = sum(len(ids) for ids in self.to_recompute.values())
        n_invalidate = sum(len(ids) for _, ids in self.to_invalidate)
        return (
            f"<RecomputeScheduler "
            f"recompute={len(self.to_recompute)}f/{n_recompute}e "
            f"invalidate={len(self.to_invalidate)}f/{n_invalidate}e>"
        )
