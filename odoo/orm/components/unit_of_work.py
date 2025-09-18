"""Standalone flush scheduling engine for the ORM.

This module provides :class:`UnitOfWork`, an isolated component that
encapsulates the fixpoint convergence loop and dirty-tracking queries
currently embedded in ``Environment.flush_all()`` and
``Environment._recompute_all()``.

It has **no dependency** on Environment, BaseModel, or database cursors.
Actual recomputation and SQL flushing are injected via callbacks.

Usage::

    uow = UnitOfWork(cache_store, compute_engine)

    # Recompute loop only
    result = uow.run_recompute_loop(recompute_fn)

    # Full flush loop (recompute → flush → repeat)
    result = uow.run_flush_loop(recompute_fn, flush_fn)
"""

from collections.abc import Callable
from dataclasses import dataclass, field

from .cache import FieldCache
from .compute import ComputeEngine


@dataclass(slots=True)
class LoopResult:
    """Result of a convergence loop execution.

    Attributes:
        iterations: number of iterations executed
        converged: whether the loop converged before max_iterations
        stalled_fields: field keys that stalled (same snapshot twice)

    """

    iterations: int = 0
    converged: bool = True
    stalled_fields: list = field(default_factory=list)


class UnitOfWork:
    """Flush scheduling engine: convergence detection + ordering.

    Owns the algorithm for:

    * Determining which fields/models need flushing (dirty field scan)
    * Computing flush order
    * Detecting convergence stalls in recomputation
    * Tracking monotonicity (progress detection)

    Does NOT own: actual SQL execution, recomputation dispatch.
    These are injected via callbacks.
    """

    __slots__ = ("_recompute_order", "cache", "engine", "max_iterations")

    def __init__(
        self,
        cache: FieldCache,
        engine: ComputeEngine,
        max_iterations: int = 10,
    ) -> None:
        self.cache = cache
        self.engine = engine
        self.max_iterations = max_iterations
        self._recompute_order: dict | None = None

    def set_recompute_order(self, order: dict) -> None:
        """Set the topological recompute order from ModelGraph.

        :param order: ``{field: priority_int}`` — lower priority = compute first
        """
        self._recompute_order = order

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    def dirty_fields(self) -> list:
        """Return fields with dirty entries."""
        return list(self.cache.iter_dirty_fields())

    def dirty_models(self) -> list[str]:
        """Return unique model names with dirty fields, preserving order.

        This extracts the pattern from ``flush_all`` line 541:
        ``OrderedSet(field.model_name for field in cache_store.iter_dirty_fields())``

        Uses a dict for ordered-unique (preserves insertion order in Python 3.7+).
        """
        seen: dict[str, None] = {}
        for fld in self.cache.iter_dirty_fields():
            model_name = getattr(fld, "model_name", None)
            if model_name is not None and model_name not in seen:
                seen[model_name] = None
        return list(seen)

    def has_pending_work(self) -> bool:
        """Whether there are pending recomputations or dirty fields."""
        return self.engine.has_pending() or self.cache.is_any_dirty()

    # ------------------------------------------------------------------
    # Convergence detection
    # ------------------------------------------------------------------

    def recompute_snapshot(self) -> frozenset[tuple]:
        """Snapshot of ``(field, pending_count)`` for convergence detection.

        Only includes fields with at least one real (truthy) pending ID,
        matching the ``pending_real_fields()`` filter.
        """
        return frozenset(
            (field, len(self.engine.pending_ids(field)))
            for field in self.engine.pending_real_fields()
        )

    def check_convergence(
        self,
        prev_snapshot: frozenset[tuple] | None,
        curr_snapshot: frozenset[tuple],
    ) -> tuple[bool, list[str]]:
        """Check whether recomputation is making progress.

        Returns ``(progressing, stalled_field_descriptions)`` where:
        - ``progressing`` is True if the snapshot changed (or prev was None)
        - ``stalled_field_descriptions`` lists field info for diagnostics

        :param prev_snapshot: previous result of :meth:`recompute_snapshot`
        :param curr_snapshot: current result of :meth:`recompute_snapshot`
        """
        if prev_snapshot is None or curr_snapshot != prev_snapshot:
            return True, []

        # Stalled — same fields with same counts
        stalled = sorted(
            f"{getattr(f, 'model_name', '?')}.{getattr(f, 'name', f)}({cnt})"
            for f, cnt in curr_snapshot
        )
        return False, stalled

    def dirty_snapshot(self) -> int:
        """Return the total number of dirty entries for monotonicity tracking."""
        return self.cache.dirty_entry_count()

    def check_flush_progress(
        self, prev_dirty_count: int, curr_dirty_count: int
    ) -> tuple[bool, list[str]]:
        """Check whether flushing is making progress.

        Returns ``(progressing, stalled_field_descriptions)``.
        """
        if curr_dirty_count < prev_dirty_count:
            return True, []

        stalled = sorted(
            f"{getattr(f, 'model_name', '?')}.{getattr(f, 'name', f)}"
            for f in self.cache.iter_dirty_fields()
        )
        return False, stalled

    # ------------------------------------------------------------------
    # Convergence loops
    # ------------------------------------------------------------------

    def run_recompute_loop(
        self,
        recompute_fn: Callable,
    ) -> LoopResult:
        """Execute the fixpoint recompute loop.

        Repeatedly collects fields with pending real recomputations and
        calls ``recompute_fn(field)`` for each.  When a topological order
        is available (via :meth:`set_recompute_order`), fields are processed
        in dependency order — dependencies before dependents — so that a
        single pass resolves acyclic chains without re-iteration.

        Tracks monotonicity to detect stalls.

        :param recompute_fn: called as ``recompute_fn(field)`` for each
            field needing recomputation.  Expected to update the cache
            and call ``engine.mark_done()``.
        :returns: :class:`LoopResult` with iteration count and convergence info
        """
        result = LoopResult()
        prev_snapshot = None
        order = self._recompute_order

        for iteration in range(self.max_iterations):
            fields = self.engine.pending_real_fields()
            if not fields:
                result.iterations = iteration
                result.converged = True
                break

            curr_snapshot = frozenset(
                (f, len(self.engine.pending_ids(f))) for f in fields
            )
            progressing, stalled = self.check_convergence(prev_snapshot, curr_snapshot)
            if not progressing:
                result.stalled_fields = stalled

            prev_snapshot = curr_snapshot

            # Sort fields by topological priority when available.
            # Dependencies are processed first (lower priority value),
            # so their results are in cache when dependents compute.
            if order:
                # Unknown fields (not in the order map) get max priority,
                # placing them last — safe fallback for dynamic fields.
                _max = len(order)
                fields.sort(key=lambda f: order.get(f, _max))

            for fld in fields:
                recompute_fn(fld)
        else:
            result.iterations = self.max_iterations
            result.converged = not bool(self.engine.pending_real_fields())
            if not result.converged:
                result.stalled_fields = sorted(
                    f"{getattr(f, 'model_name', '?')}.{getattr(f, 'name', f)}"
                    for f in self.engine.pending_real_fields()
                )

        # Prune empty pending entries to avoid accumulation
        self.engine.prune_empty()
        return result

    def run_flush_loop(
        self,
        recompute_fn: Callable,
        flush_fn: Callable,
    ) -> LoopResult:
        """Execute the outer flush loop: recompute → flush → repeat.

        Each flush may trigger new computations (via ``modified()`` in
        write), which may dirty more fields, requiring another iteration.

        :param recompute_fn: called as ``recompute_fn(field)`` for each
            field needing recomputation
        :param flush_fn: called as ``flush_fn(model_names)`` with the list
            of model names that need flushing
        :returns: :class:`LoopResult`
        """
        result = LoopResult()
        prev_dirty_count = 0

        for iteration in range(self.max_iterations):
            # Inner recompute loop
            recompute_result = self.run_recompute_loop(recompute_fn)
            if not recompute_result.converged:
                # Propagate recompute non-convergence: break the flush loop
                # immediately (matching the original _recompute_all() which
                # raises before flushing when computes don't converge).
                result.iterations = iteration + 1
                result.converged = False
                result.stalled_fields = recompute_result.stalled_fields
                break

            # Collect dirty models
            model_names = self.dirty_models()
            if not model_names:
                result.iterations = iteration
                result.converged = True
                break

            curr_dirty_count = self.cache.dirty_entry_count()
            if iteration and curr_dirty_count >= prev_dirty_count:
                _, stalled = self.check_flush_progress(
                    prev_dirty_count, curr_dirty_count
                )
                result.stalled_fields = stalled

            prev_dirty_count = curr_dirty_count

            # Flush all dirty models
            flush_fn(model_names)
        else:
            result.iterations = self.max_iterations
            result.converged = not bool(self.dirty_models())
            if not result.converged:
                result.stalled_fields = sorted(
                    f"{getattr(f, 'model_name', '?')}.{getattr(f, 'name', f)}"
                    for f in self.cache.iter_dirty_fields()
                )

        return result

    def __repr__(self) -> str:
        n_dirty = self.cache.dirty_entry_count()
        n_pending = sum(
            len(self.engine.pending_ids(f)) for f in self.engine.pending_fields()
        )
        return f"<UnitOfWork dirty={n_dirty} pending={n_pending} max_iter={self.max_iterations}>"
