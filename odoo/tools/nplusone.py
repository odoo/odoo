"""
N+1 CRUD detection for Odoo ORM.

Detects repeated single-record create/write/unlink calls from the same call
site within a transaction — a pattern that is 5-15× slower than batching.

Activation: ``--dev=n1`` (opt-in, NOT part of ``--dev=all``).

When enabled, a lightweight tracker on the ``Transaction`` object records each
CRUD call keyed by ``(operation, model, caller_file, caller_line)``.  At the
end of the request (``Transaction.flush()``), violations above the threshold
are reported via the ``odoo.orm.nplusone`` logger.

When **disabled** the only overhead is a single boolean check per CRUD call
(module-level ``_n1_enabled`` flag).

See Also
--------
- ``odoo.tools.orm_profiler`` — Aggregate per-model/operation stats per transaction
- ``odoo.tools.profiler`` — Sampling profiler (flamegraphs, SQL tracing)
- ``odoo.tools.mixin_profiler`` — Method-level profiler (per-method timing)
- ``odoo.tests.benchmark`` — Micro-benchmark statistical utilities
- ``.claude/rules/profiling.md`` — Decision tree: which tool to use when
"""

import logging
import sys
from pathlib import Path

_logger = logging.getLogger("odoo.orm.nplusone")

# ---------------------------------------------------------------------------
# Module-level fast flag – one LOAD_GLOBAL + branch per CRUD call when off.
# ---------------------------------------------------------------------------
_n1_enabled: bool = False

# Precomputed path prefix of the ORM package.  Frames whose filename starts
# with this prefix are considered "internal" and skipped when determining the
# external caller.
_ODOO_DIR = Path(__file__).resolve().parent.parent
_ORM_PREFIX: str = str(_ODOO_DIR / "orm") + "/"

# Also skip frames from the mail module's model layer (its create/write
# wrappers are internal too) and from decorators.py.
_SKIP_PREFIXES: tuple[str, ...] = (
    _ORM_PREFIX,
    # decorators.py lives outside orm/ but is still framework-internal
    str(_ODOO_DIR / "api") + "/",
)


def setup(dev_mode: list[str] | None = None) -> None:
    """Initialise the N+1 detection system.

    Called once during server startup after config is parsed.
    """
    global _n1_enabled
    if dev_mode is None:
        from odoo.tools import config

        dev_mode = config.get("dev_mode", [])
    _n1_enabled = "n1" in dev_mode
    if _n1_enabled:
        _logger.info("N+1 CRUD detection enabled (--dev=n1)")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class _NplusOneEntry:
    """Accumulator for a single (operation, model, file, line) call site."""

    __slots__ = ("count", "total_records", "vals_fingerprints")

    def __init__(self) -> None:
        self.count: int = 0
        self.total_records: int = 0
        self.vals_fingerprints: set[frozenset[str]] = set()


# Key: (operation, model_name, filename, lineno)
type _Key = tuple[str, str, str, int]


class NplusOneTracker:
    """Collects N+1 CRUD call patterns within a single transaction."""

    __slots__ = ("_data",)

    THRESHOLD = 3  # minimum calls from same site to trigger a warning

    def __init__(self) -> None:
        self._data: dict[_Key, _NplusOneEntry] = {}

    # -- recording ----------------------------------------------------------

    def record(
        self,
        operation: str,
        model_name: str,
        record_count: int,
        field_fingerprint: frozenset[str],
    ) -> None:
        """Record a CRUD call.  Called from ``crud.py``."""
        # Walk the stack to find the first frame outside ORM internals.
        frame = sys._getframe(2)  # skip record() + the CRUD method itself
        while frame is not None:
            fn = frame.f_code.co_filename
            if not any(fn.startswith(p) for p in _SKIP_PREFIXES):
                break
            frame = frame.f_back

        if frame is None:
            return

        key: _Key = (
            operation,
            model_name,
            frame.f_code.co_filename,
            frame.f_lineno,
        )

        entry = self._data.get(key)
        if entry is None:
            entry = _NplusOneEntry()
            self._data[key] = entry

        entry.count += 1
        entry.total_records += record_count
        entry.vals_fingerprints.add(field_fingerprint)

    # -- reporting ----------------------------------------------------------

    def report(self) -> None:
        """Emit warnings for call sites that exceed the threshold."""
        if not _logger.isEnabledFor(logging.WARNING):
            return

        violations: list[tuple[_Key, _NplusOneEntry]] = [
            (key, entry)
            for key, entry in self._data.items()
            if entry.count >= self.THRESHOLD
        ]
        if not violations:
            return

        lines = [f"N+1 CRUD detected ({len(violations)} call site(s)):"]
        for (operation, model_name, filename, lineno), entry in violations:
            if len(entry.vals_fingerprints) == 1:
                hint = " [same fields every call — easily batchable]"
            elif len(entry.vals_fingerprints) <= 3:
                hint = f" [{len(entry.vals_fingerprints)} distinct field sets]"
            else:
                hint = ""
            lines.append(
                f"  {operation}() on {model_name}: "
                f"{entry.count} calls, {entry.total_records} records total"
                f" @ {filename}:{lineno}{hint}"
            )
        _logger.warning("\n".join(lines))

    def clear(self) -> None:
        self._data.clear()
