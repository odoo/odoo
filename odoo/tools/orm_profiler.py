"""
Aggregate ORM profiler for transaction-level performance analysis.

Collects per-model, per-operation timing statistics across an entire
transaction (HTTP request / RPC call / test), then emits a structured
summary at flush time.

Activation: ``ODOO_ORM_PROFILE=1`` environment variable (opt-in).

When enabled, lightweight recording hooks in the ORM mixins (crud.py,
read.py, search.py, cache.py) call ``record_*()`` methods on the
``OrmProfiler`` instance attached to the current ``Transaction``.
At the end of the request (``Transaction.flush()``), the profiler
emits a summary to the ``odoo.orm.profile`` logger.

When **disabled** the only overhead is a single boolean check per ORM
call (module-level ``_orm_profiling_enabled`` flag).

See Also
--------
- ``odoo.tools.nplusone`` — N+1 CRUD detection (repeated single-record calls)
- ``odoo.tools.profiler`` — Sampling profiler (flamegraphs, SQL tracing)
- ``odoo.tools.mixin_profiler`` — Method-level profiler (per-method timing)
- ``odoo.tests.benchmark`` — Micro-benchmark statistics
- ``.claude/rules/profiling.md`` — Decision tree: which tool to use when
"""

import logging
import os

_logger = logging.getLogger("odoo.orm.profile")

# ---------------------------------------------------------------------------
# Module-level fast flag – one LOAD_GLOBAL + branch per ORM call when off.
# ---------------------------------------------------------------------------
_orm_profiling_enabled: bool = os.environ.get("ODOO_ORM_PROFILE", "").lower() in (
    "1",
    "true",
    "yes",
)

if _orm_profiling_enabled:
    _logger.info("ORM aggregate profiling enabled (ODOO_ORM_PROFILE=1)")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class _OpStats:
    """Accumulator for a single (operation, model_name) bucket."""

    __slots__ = ("count", "records", "time")

    def __init__(self) -> None:
        self.count: int = 0
        self.records: int = 0
        self.time: float = 0.0


# Key: (operation, model_name)
type _Key = tuple[str, str]


class OrmProfiler:
    """Collects aggregate ORM statistics within a single transaction.

    Attached to ``Transaction._orm_profiler`` when profiling is enabled.
    """

    __slots__ = ("_data", "_total_time")

    def __init__(self) -> None:
        self._data: dict[_Key, _OpStats] = {}
        self._total_time: float = 0.0

    # -- recording ----------------------------------------------------------

    def _record(
        self,
        operation: str,
        model_name: str,
        record_count: int,
        elapsed: float,
    ) -> None:
        """Record a single ORM operation."""
        key: _Key = (operation, model_name)
        stats = self._data.get(key)
        if stats is None:
            stats = _OpStats()
            self._data[key] = stats
        stats.count += 1
        stats.records += record_count
        stats.time += elapsed
        self._total_time += elapsed

    def record_create(self, model_name: str, record_count: int, elapsed: float) -> None:
        self._record("create", model_name, record_count, elapsed)

    def record_write(self, model_name: str, record_count: int, elapsed: float) -> None:
        self._record("write", model_name, record_count, elapsed)

    def record_unlink(self, model_name: str, record_count: int, elapsed: float) -> None:
        self._record("unlink", model_name, record_count, elapsed)

    def record_read(self, model_name: str, record_count: int, elapsed: float) -> None:
        self._record("read", model_name, record_count, elapsed)

    def record_search(self, model_name: str, record_count: int, elapsed: float) -> None:
        self._record("search", model_name, record_count, elapsed)

    def record_recompute(
        self, model_name: str, record_count: int, elapsed: float
    ) -> None:
        self._record("recompute", model_name, record_count, elapsed)

    def record_flush(self, model_name: str, record_count: int, elapsed: float) -> None:
        self._record("flush", model_name, record_count, elapsed)

    def record_modified(
        self, model_name: str, record_count: int, elapsed: float
    ) -> None:
        self._record("modified", model_name, record_count, elapsed)

    # -- reporting ----------------------------------------------------------

    def report(self) -> None:
        """Emit a structured summary to the logger."""
        if not self._data or not _logger.isEnabledFor(logging.WARNING):
            return

        # Sort by total time descending — biggest hotspots first
        sorted_entries = sorted(
            self._data.items(),
            key=lambda item: item[1].time,
            reverse=True,
        )

        # Aggregate per-operation totals
        op_totals: dict[str, _OpStats] = {}
        for (operation, _model), stats in self._data.items():
            agg = op_totals.get(operation)
            if agg is None:
                agg = _OpStats()
                op_totals[operation] = agg
            agg.count += stats.count
            agg.records += stats.records
            agg.time += stats.time

        lines = [
            f"ORM Profile Summary ({len(self._data)} model/op pairs, "
            f"{self._total_time * 1000:.1f} ms total):"
        ]

        # Operation totals
        lines.append("  Operation totals:")
        for op, agg in sorted(op_totals.items(), key=lambda x: x[1].time, reverse=True):
            lines.append(
                f"    {op:>10s}: {agg.count:4d} calls, "
                f"{agg.records:6d} records, {agg.time * 1000:8.1f} ms"
            )

        # Top hotspots (cap at 20 to avoid log spam)
        lines.append("  Top hotspots by time:")
        for (operation, model_name), stats in sorted_entries[:20]:
            pct = (stats.time / self._total_time * 100) if self._total_time else 0
            lines.append(
                f"    {operation:>10s} {model_name}: "
                f"{stats.count:4d} calls, {stats.records:6d} records, "
                f"{stats.time * 1000:8.1f} ms ({pct:4.1f}%)"
            )

        _logger.warning("\n".join(lines))

    def clear(self) -> None:
        self._data.clear()
        self._total_time = 0.0
