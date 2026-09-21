from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from odoo.libs.debug_log import DebugLog

if TYPE_CHECKING:
    from collections.abc import Callable

    from ._protocols import FieldKey
    from .cache import FieldCache
    from .compute import ComputeEngine

STALL_REPEATS = 16

SNAPSHOT_AFTER = 3

# distinct snapshots remembered per convergence loop: a cycle longer than
# this is reported by the iteration cap, not by the detector
STALL_MEMORY = 64

_debug = DebugLog(__name__)


class _StallDetector:
    """Counts how often a pending/dirty snapshot recurs. A compute cycle of
    period two never shows the same snapshot twice in a row, so the detector
    keys on the snapshot itself, not on the previous iteration."""

    __slots__ = ("_seen",)

    def __init__(self) -> None:
        self._seen: dict[Any, int] = {}

    def observe(self, snapshot: Any) -> int:
        key = _freeze(snapshot)
        seen = self._seen
        repeats = seen.get(key)
        if repeats is None:
            if len(seen) >= STALL_MEMORY:
                del seen[next(iter(seen))]
            seen[key] = 0
            return 0
        repeats += 1
        seen[key] = repeats
        return repeats


def _freeze(snapshot: Any) -> Any:
    if isinstance(snapshot, tuple):
        return tuple(_freeze(part) for part in snapshot)
    return frozenset(snapshot.items())


@dataclass(slots=True)
class ConvergenceResult:
    iterations: int = 0
    converged: bool = True
    stalled_fields: list[str] = field(default_factory=list)


class UnitOfWork[F: FieldKey = FieldKey]:
    __slots__ = ("_recompute_order", "cache", "engine", "max_iterations")

    def __init__(
        self,
        cache: FieldCache[F],
        engine: ComputeEngine[F],
        max_iterations: int = 1000,
    ) -> None:
        self.cache = cache
        self.engine = engine
        self.max_iterations = max_iterations
        self._recompute_order: (
            dict[Any, int] | Callable[[], dict[Any, int] | None] | None
        ) = None

    def set_recompute_order(
        self,
        order: dict[Any, int] | Callable[[], dict[Any, int] | None] | None,
    ) -> None:
        self._recompute_order = order

    def get_dirty_model_names(self) -> list[str]:
        seen: dict[str, None] = {}
        for fld in self.cache.iter_dirty_fields():
            model_name = getattr(fld, "model_name", None)
            if model_name is not None and model_name not in seen:
                seen[model_name] = None
        return list(seen)

    def _get_pending_snapshot(self) -> dict[Any, frozenset]:
        return {
            fld: frozenset(self.engine.get_pending_ids(fld))
            for fld in self.engine.get_pending_fields()
        }

    def _get_dirty_snapshot(self) -> dict[Any, frozenset]:
        return {
            fld: frozenset(self.cache.get_dirty(fld) or ())
            for fld in self.cache.iter_dirty_fields()
        }

    @staticmethod
    def _get_field_label(field: F) -> str:
        return f"{getattr(field, 'model_name', '?')}.{getattr(field, 'name', field)}"

    def recompute_until_converged(
        self,
        recompute_fn: Callable[[F], None],
    ) -> ConvergenceResult:
        result = ConvergenceResult()
        order = self._recompute_order
        if callable(order):
            order = order()

        detector = _StallDetector()
        for iteration in range(self.max_iterations):
            fields = self.engine.get_pending_fields_with_real_ids()
            if not fields:
                result.iterations = iteration
                result.converged = True
                result.stalled_fields = []
                break

            if iteration >= SNAPSHOT_AFTER:
                snapshot = self._get_pending_snapshot()
                repeats = detector.observe(snapshot)
                if _debug.logic.enabled and (iteration == SNAPSHOT_AFTER or repeats):
                    _debug.logic(
                        "unit_of_work.recompute.slow_convergence",
                        iteration=iteration,
                        repeats=repeats,
                        pending_fields=len(snapshot),
                    )
                if repeats >= STALL_REPEATS:
                    result.iterations = iteration
                    result.converged = False
                    result.stalled_fields = sorted(
                        self._get_field_label(f) for f in snapshot
                    )
                    _debug.logic(
                        "unit_of_work.recompute.stalled",
                        iteration=iteration,
                        stalled=result.stalled_fields,
                    )
                    break

            if order:
                _max = len(order)
                fields.sort(key=lambda f: order.get(f, _max))

            for fld in fields:
                recompute_fn(fld)
        else:
            result.iterations = self.max_iterations
            pending = self.engine.get_pending_fields_with_real_ids()
            result.converged = not pending
            if result.converged:
                result.stalled_fields = []
            else:
                result.stalled_fields = sorted(
                    self._get_field_label(f) for f in pending
                )

        return result

    def flush_until_converged(
        self,
        recompute_fn: Callable[[F], None],
        flush_fn: Callable[[list[str]], None],
    ) -> ConvergenceResult:
        result = ConvergenceResult()

        detector = _StallDetector()
        for iteration in range(self.max_iterations):
            recompute_result = self.recompute_until_converged(recompute_fn)
            if not recompute_result.converged:
                result.iterations = iteration + 1
                result.converged = False
                result.stalled_fields = recompute_result.stalled_fields
                break

            model_names = self.get_dirty_model_names()
            if not model_names:
                result.iterations = iteration + (
                    1 if recompute_result.iterations else 0
                )
                result.converged = True
                result.stalled_fields = []
                break

            if iteration >= SNAPSHOT_AFTER:
                snapshot = (self._get_dirty_snapshot(), self._get_pending_snapshot())
                repeats = detector.observe(snapshot)
                if _debug.logic.enabled and (iteration == SNAPSHOT_AFTER or repeats):
                    _debug.logic(
                        "unit_of_work.flush.slow_convergence",
                        iteration=iteration,
                        repeats=repeats,
                        dirty_fields=len(snapshot[0]),
                        pending_fields=len(snapshot[1]),
                    )
                if repeats >= STALL_REPEATS:
                    result.iterations = iteration
                    result.converged = False
                    result.stalled_fields = sorted(
                        {self._get_field_label(f) for f in snapshot[0]}
                        | {self._get_field_label(f) for f in snapshot[1]}
                    )
                    _debug.logic(
                        "unit_of_work.flush.stalled",
                        iteration=iteration,
                        stalled=result.stalled_fields,
                    )
                    break

            _debug.pipeline(
                "unit_of_work.flush.iteration",
                iteration=iteration,
                recompute_iterations=recompute_result.iterations,
                models=len(model_names),
            )
            flush_fn(model_names)
        else:
            result.iterations = self.max_iterations
            dirty_models = self.get_dirty_model_names()
            pending = self.engine.get_pending_fields_with_real_ids()
            result.converged = not dirty_models and not pending
            if result.converged:
                result.stalled_fields = []
            else:
                labels = {
                    self._get_field_label(f) for f in self.cache.iter_dirty_fields()
                }
                labels.update(self._get_field_label(f) for f in pending)
                result.stalled_fields = sorted(labels)

        return result

    def __repr__(self) -> str:
        n_dirty = self.cache.get_dirty_entry_count()
        n_pending = sum(
            len(self.engine.get_pending_ids(f))
            for f in self.engine.get_pending_fields()
        )
        return f"<UnitOfWork dirty={n_dirty} pending={n_pending} max_iter={self.max_iterations}>"
