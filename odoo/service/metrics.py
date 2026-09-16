from __future__ import annotations

import math
import os
from typing import Any

from odoo.libs.debug_log import DebugLog
from odoo.modules.registry import Registry

from . import _process_state
from ._env import get_env_str

_debug = DebugLog(__name__)

CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"


def get_metrics_token() -> str:
    return get_env_str("ODOO_METRICS_TOKEN")


_BORROW_WAIT = "odoo_pool_borrow_wait_seconds"

_LABEL_ESCAPES = str.maketrans({"\\": "\\\\", '"': '\\"', "\n": "\\n"})


def _format_labels(pairs: dict[str, str]) -> str:
    if not pairs:
        return ""
    inner = ",".join(
        f'{k}="{str(v).translate(_LABEL_ESCAPES)}"' for k, v in pairs.items()
    )
    return "{" + inner + "}"


_SUFFIXES_BY_KIND = {
    "histogram": ("_bucket", "_sum", "_count"),
    "summary": ("_sum", "_count"),
}

_POSITIVE_INFINITY = "+Inf"


def _format_value(value: float | bool) -> str:
    if isinstance(value, bool):
        return str(int(value))
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return _POSITIVE_INFINITY if value > 0 else "-Inf"
    return str(value)


def _get_bucket_sort_key(sample: _Sample) -> tuple[int, float]:
    edge = sample.labels.get("le")
    if edge is None:
        return (1, 0.0)
    if edge == _POSITIVE_INFINITY:
        return (0, float("inf"))
    try:
        return (0, float(edge))
    except ValueError:
        return (0, float("inf"))


class _Sample:
    __slots__ = ("labels", "name", "value")

    def __init__(self, name: str, value: float | bool, labels: dict[str, str]) -> None:
        self.name = name
        self.value = value
        self.labels = labels

    def get_series_key(self) -> tuple[tuple[str, str], ...]:
        return tuple((k, v) for k, v in self.labels.items() if k != "le")

    def render(self) -> str:
        return f"{self.name}{_format_labels(self.labels)} {_format_value(self.value)}"


class _Family:
    __slots__ = ("help", "kind", "name", "samples")

    def __init__(self, name: str, kind: str, help: str) -> None:
        self.name = name
        self.kind = kind
        self.help = help
        self.samples: list[_Sample] = []

    def _get_samples_ordered(self) -> list[_Sample]:
        if self.kind not in _SUFFIXES_BY_KIND:
            return self.samples
        by_series: dict[tuple[tuple[str, str], ...], list[_Sample]] = {}
        for sample in self.samples:
            by_series.setdefault(sample.get_series_key(), []).append(sample)
        out: list[_Sample] = []
        for group in by_series.values():
            buckets = [s for s in group if s.name.endswith("_bucket")]
            rest = [s for s in group if not s.name.endswith("_bucket")]
            out.extend(sorted(buckets, key=_get_bucket_sort_key))
            out.extend(rest)
        return out

    def render(self) -> list[str]:
        lines = [f"# HELP {self.name} {self.help}", f"# TYPE {self.name} {self.kind}"]
        lines.extend(sample.render() for sample in self._get_samples_ordered())
        return lines


class _Exposition:
    def __init__(self, base_labels: dict[str, str] | None = None) -> None:
        self._families: dict[str, _Family] = {}
        self._owner: dict[str, str] = {}
        self._base = dict(base_labels or {})

    def declare(self, name: str, kind: str, help: str = "") -> None:
        if name in self._families:
            return
        self._families[name] = _Family(name, kind, help)
        self._owner[name] = name
        for suffix in _SUFFIXES_BY_KIND.get(kind, ()):
            self._owner.setdefault(name + suffix, name)

    def sample(
        self,
        name: str,
        value: float | bool,
        *,
        labels: dict[str, str] | None = None,
    ) -> None:
        owner = self._owner.get(name)
        if owner is None:
            _debug.logic("metrics.untyped_sample", name=name)
            self.declare(name, "untyped")
            owner = name
        self._families[owner].samples.append(
            _Sample(name, value, self._base | (labels or {}))
        )

    def add(
        self,
        name: str,
        value: float | bool,
        *,
        kind: str = "gauge",
        help: str = "",
        labels: dict[str, str] | None = None,
    ) -> None:
        self.declare(name, kind, help)
        self.sample(name, value, labels=labels)

    def render(self) -> str:
        lines: list[str] = []
        for family in self._families.values():
            lines.extend(family.render())
        return "\n".join(lines) + "\n"


def get_service_metrics() -> dict[str, Any]:
    server = _process_state.server
    out: dict[str, Any] = {
        "flavor": "none",
        "registries": len(Registry.registries),
    }
    if server is None:
        _debug.logic("metrics.no_server", registries=out["registries"])
        return out
    out["flavor"] = server.flavor
    with _debug.perf("metrics.service_collected", flavor=server.flavor) as span:
        out.update(server.get_metrics())
        span.set(keys=len(out))
    return out


def _add_borrow_wait_histogram(exp: _Exposition, mode: str, stats: dict) -> None:
    label = {"pool": mode}

    exp.add(
        "odoo_pool_borrow_wait_seconds_max",
        stats.get("borrow_wait_seconds_max", 0.0),
        help="Longest single borrow wait observed.",
        labels=label,
    )

    buckets = stats.get("borrow_wait_seconds") or {}
    exp.declare(
        _BORROW_WAIT,
        "histogram",
        help="Time borrows spent waiting for a connection.",
    )
    for edge, count in buckets.items():
        exp.sample(
            f"{_BORROW_WAIT}_bucket",
            count,
            labels={"pool": mode, "le": edge.removeprefix("le_")},
        )
    exp.sample(
        f"{_BORROW_WAIT}_sum",
        stats.get("borrow_wait_seconds_total", 0.0),
        labels=label,
    )
    exp.sample(f"{_BORROW_WAIT}_count", buckets.get("le_+Inf", 0), labels=label)


_POOL_COUNTERS: dict[str, tuple[str, str]] = {
    "borrows": ("odoo_pool_borrows_total", "Connections borrowed from the pool."),
    "borrows_direct": (
        "odoo_pool_borrows_direct_total",
        "Borrows served outside the pooled path.",
    ),
    "borrows_failed": (
        "odoo_pool_borrows_failed_total",
        "Borrows that raised instead of yielding a connection.",
    ),
    "pools_created": ("odoo_pool_created_total", "Per-DSN pools created."),
    "pools_reaped": (
        "odoo_pool_reaped_total",
        "Per-DSN pools closed by the idle reaper.",
    ),
    "pools_evicted_stale": (
        "odoo_pool_evicted_stale_total",
        "Per-DSN pools evicted because their credentials changed.",
    ),
    "connections_discarded": (
        "odoo_pool_connections_discarded_total",
        "Connections dropped rather than returned to the pool.",
    ),
    "connections_trimmed": (
        "odoo_pool_connections_trimmed_total",
        "Idle connections closed to keep this process's backends within db_maxconn.",
    ),
    "probe_run": (
        "odoo_pool_probe_run_total",
        "Pre-flight connectability probes run.",
    ),
    "probe_permanent": (
        "odoo_pool_probe_permanent_total",
        "Probes that concluded the failure was permanent.",
    ),
    "probe_transient": (
        "odoo_pool_probe_transient_total",
        "Probes that concluded the failure was transient.",
    ),
    "probe_skipped_proven": (
        "odoo_pool_probe_skipped_total",
        "Probes skipped because the DSN was already proven.",
    ),
    "budget_exhausted": (
        "odoo_pool_budget_exhausted_total",
        "Times the shared connection budget was exhausted.",
    ),
    "leaks_reported": (
        "odoo_pool_leaks_reported_total",
        "Times a connection was found held past db_leak_detection.",
    ),
}
_POOL_GAUGES: dict[str, tuple[str, str]] = {
    "pools": ("odoo_pool_pools", "Per-DSN pools currently open."),
    "direct_out": (
        "odoo_pool_direct_out",
        "Direct (unpooled) connections outstanding.",
    ),
    "budget_maxconn": (
        "odoo_pool_budget_maxconn",
        "Shared connection budget ceiling.",
    ),
    "budget_available": ("odoo_pool_budget_available", "Unclaimed budget slots."),
    "budget_in_use": ("odoo_pool_budget_in_use", "Budget slots currently held."),
    "checked_out": (
        "odoo_pool_checked_out",
        "Connections currently checked out by a borrower.",
    ),
    "checked_out_oldest_seconds": (
        "odoo_pool_checked_out_oldest_seconds",
        "Age of the longest-held checkout; a rising floor is a leak.",
    ),
}


def _add_pool_family(exp: _Exposition, mode: str, health: dict) -> None:
    stats = health.get("pool") or {}
    label = {"pool": mode}
    for key, (name, help_text) in _POOL_COUNTERS.items():
        if key in stats:
            exp.add(name, stats[key], kind="counter", help=help_text, labels=label)
    for key, (name, help_text) in _POOL_GAUGES.items():
        if key in stats:
            exp.add(name, stats[key], help=help_text, labels=label)

    if "backends" in health:
        exp.add(
            "odoo_pool_backends",
            health["backends"],
            help=(
                "Server connections held (checked out + idle). Trimmed on every "
                "return to at most db_maxconn per pool mode; a transient "
                "excess is one in flight."
            ),
            labels=label,
        )

    _add_borrow_wait_histogram(exp, mode, stats)

    for database, per_db in (health.get("per_database") or {}).items():
        for key, value in (per_db or {}).items():
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                continue
            exp.add(
                f"odoo_db_pool_{key}",
                value,
                help="psycopg_pool per-database statistic.",
                labels={"pool": mode, "database": database},
            )


_REPLICA_GAUGES = {
    ("breaker", "closed"): (
        "odoo_replica_breaker_closed",
        (
            "1 while read-only cursors are routed to the replica; 0 while the "
            "circuit breaker holds them on the primary."
        ),
    ),
    ("breaker", "failures"): (
        "odoo_replica_breaker_failures",
        "Consecutive replica cursor failures counted by the breaker.",
    ),
    ("breaker", "trips"): (
        "odoo_replica_breaker_trips",
        "Times the breaker opened since the registry was built.",
    ),
    ("breaker", "cooldown_remaining_seconds"): (
        "odoo_replica_breaker_cooldown_remaining_seconds",
        "Seconds until the breaker lets one request try the replica again.",
    ),
    ("lag", "last_lag_seconds"): (
        "odoo_replica_lag_seconds",
        (
            "Apply lag measured on the last sample; +Inf for a standby that has "
            "replayed nothing yet."
        ),
    ),
    ("lag", "lagging"): (
        "odoo_replica_lagging",
        "1 while the lag gate routes read-only cursors to the primary.",
    ),
}


def _add_replica_family(exp: _Exposition, database: str, health: dict) -> None:
    label = {"database": database}
    for (section, key), (name, help_text) in _REPLICA_GAUGES.items():
        value = (health.get(section) or {}).get(key)
        if isinstance(value, (int, float)):
            exp.add(name, value, help=help_text, labels=label)
    if "write_pins" in health:
        exp.add(
            "odoo_replica_write_pins",
            health["write_pins"],
            help="Sessions currently reading from the primary because they wrote.",
            labels=label,
        )


def render_prometheus_exposition() -> str:
    from odoo import db

    exp = _Exposition({"pid": str(os.getpid())})
    exp.add("odoo_up", 1, help="1 when the metrics endpoint is serving.")

    try:
        svc = get_service_metrics()
    except Exception:
        _debug.logic("metrics.service_metrics_unavailable")
        svc = {}
    if svc:
        exp.add(
            "odoo_server_info",
            1,
            help="Server flavor, as a label on a constant 1.",
            labels={"flavor": svc.get("flavor", "unknown")},
        )
        exp.add(
            "odoo_registries",
            svc.get("registries", 0),
            help="Registries held in memory.",
        )
        for kind, count in (svc.get("workers") or {}).items():
            exp.add(
                "odoo_workers",
                count,
                help="Live prefork worker processes.",
                labels={"type": kind},
            )
        for outcome, count in (svc.get("worker_exits") or {}).items():
            exp.add(
                "odoo_worker_exits_total",
                count,
                kind="counter",
                help="Worker exits since the master started, by outcome.",
                labels={"outcome": outcome},
            )
        for kind, count in (svc.get("threads") or {}).items():
            exp.add(
                "odoo_threads",
                count,
                help="Live service threads.",
                labels={"type": kind},
            )
        for key, name, help_text in (
            (
                "worker_population",
                "odoo_worker_population",
                "Configured HTTP worker count.",
            ),
            (
                "worker_generation",
                "odoo_worker_generation",
                "Workers forked since start.",
            ),
            (
                "http_threads_max",
                "odoo_http_threads_max",
                "Bounded HTTP handler slots.",
            ),
            (
                "limits_reached_threads",
                "odoo_limits_reached_threads",
                "Threads over their time limit, pending recycle.",
            ),
            (
                "long_polling_alive",
                "odoo_long_polling_alive",
                "1 when the evented subprocess is running.",
            ),
        ):
            if key in svc:
                exp.add(name, svc[key], help=help_text)
        if "overruns_cancelled" in svc:
            exp.add(
                "odoo_overruns_cancelled_total",
                svc["overruns_cancelled"],
                kind="counter",
                help="Requests, sweeps and jobs over their wall-clock budget whose "
                "queries were cancelled, since the process started.",
            )

    try:
        pools = db.get_pool_health()
    except Exception:
        _debug.logic("metrics.pool_health_unavailable")
        pools = {}
    for mode, health in (pools or {}).items():
        if health:
            _add_pool_family(exp, mode, health)
            _debug.pipeline(
                "metrics.pool_family_added",
                pool=mode,
                stats=len(health.get("pool") or {}),
                databases=len(health.get("per_database") or {}),
            )
    try:
        replicas = db.get_replica_health()
    except Exception:
        _debug.logic("metrics.replica_health_unavailable")
        replicas = {}
    for database, health in replicas.items():
        _add_replica_family(exp, database, health)
    if replicas:
        _debug.pipeline("metrics.replica_families_added", databases=len(replicas))

    with _debug.perf("metrics.rendered", families=len(exp._families)) as span:
        text: str = exp.render()
        span.set(bytes=len(text))
    return text


__all__ = (
    "CONTENT_TYPE",
    "get_metrics_token",
    "get_service_metrics",
    "render_prometheus_exposition",
)
