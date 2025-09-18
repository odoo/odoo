"""Shared benchmark statistical utilities.

Used by test_benchmark, test_sql_benchmark, and test_perf to compute
consistent statistics from timing data.

See Also
--------
- ``odoo.tools.orm_profiler`` — Aggregate per-model/operation stats per transaction
- ``odoo.tools.nplusone`` — N+1 CRUD detection (repeated single-record calls)
- ``odoo.tools.profiler`` — Sampling profiler (flamegraphs, SQL tracing)
- ``odoo.tools.mixin_profiler`` — Method-level profiler (per-method timing)
- ``.claude/rules/profiling.md`` — Decision tree: which tool to use when
"""

import json
import math
import statistics
import threading
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from odoo.tools.misc import real_time

OUTLIER_PERCENTILE = 5


def percentile(data: list[float], p: float) -> float:
    """Calculate percentile using linear interpolation."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * (p / 100)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_data[int(k)]
    return sorted_data[f] * (c - k) + sorted_data[c] * (k - f)


def remove_outliers(
    data: list[float], percentile_cutoff: float = OUTLIER_PERCENTILE
) -> list[float]:
    """Remove outliers outside the given percentile range."""
    if len(data) < 10:
        return data
    lower = percentile(data, percentile_cutoff)
    upper = percentile(data, 100 - percentile_cutoff)
    return [x for x in data if lower <= x <= upper]


# ---------------------------------------------------------------------------
# BenchmarkStats — unified dataclass for all benchmark suites
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class BenchmarkStats:
    """Statistical summary of benchmark results.

    All timing values are stored in **microseconds** (µs).  Use the ``_ms``
    properties for millisecond access.
    """

    name: str
    iterations: int
    total_samples: int

    # Timing (µs)
    mean_us: float
    median_us: float
    std_dev_us: float
    min_us: float
    max_us: float
    p5_us: float
    p25_us: float
    p75_us: float
    p95_us: float
    p99_us: float

    # Query stats
    query_count_mean: float
    query_count_min: int
    query_count_max: int

    # Time breakdown (µs)
    db_time_us: float  # mean DB time
    python_time_us: float  # mean Python time (total − DB)
    db_ratio: float  # DB time as fraction of total (0..1)

    # Variance
    cv: float  # coefficient of variation (std_dev / mean)

    # Raw data (µs)
    raw_times_us: list[float] = field(default_factory=list, repr=False)

    # -- millisecond properties -----------------------------------------------

    @property
    def mean_ms(self) -> float:
        return self.mean_us / 1000

    @property
    def median_ms(self) -> float:
        return self.median_us / 1000

    @property
    def std_dev_ms(self) -> float:
        return self.std_dev_us / 1000

    @property
    def min_ms(self) -> float:
        return self.min_us / 1000

    @property
    def max_ms(self) -> float:
        return self.max_us / 1000

    @property
    def p5_ms(self) -> float:
        return self.p5_us / 1000

    @property
    def p25_ms(self) -> float:
        return self.p25_us / 1000

    @property
    def p75_ms(self) -> float:
        return self.p75_us / 1000

    @property
    def p95_ms(self) -> float:
        return self.p95_us / 1000

    @property
    def p99_ms(self) -> float:
        return self.p99_us / 1000

    @property
    def db_time_ms(self) -> float:
        return self.db_time_us / 1000

    @property
    def python_time_ms(self) -> float:
        return self.python_time_us / 1000

    @property
    def python_ratio(self) -> float:
        return 1 - self.db_ratio

    # -- serialization --------------------------------------------------------

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("raw_times_us", None)
        return d

    # -- human-readable summaries ---------------------------------------------

    def summary(self, unit: str = "auto") -> str:
        """Return a human-readable summary.

        *unit*: ``"us"`` for microseconds, ``"ms"`` for milliseconds,
        ``"auto"`` picks ms when mean > 1000 µs.
        """
        if unit == "auto":
            unit = "ms" if self.mean_us > 1000 else "us"
        if unit == "ms":
            return self._summary_ms()
        return self._summary_us()

    def _summary_us(self) -> str:
        return (
            f"\n{'=' * 70}\n"
            f"  {self.name}\n"
            f"{'=' * 70}\n"
            f"  Iterations: {self.iterations} (samples: {self.total_samples})\n"
            f"\n"
            f"  TIMING (µs):\n"
            f"    Mean:   {self.mean_us:10.1f}  (±{self.std_dev_us:.1f} std)\n"
            f"    Median: {self.median_us:10.1f}\n"
            f"    Min:    {self.min_us:10.1f}    Max: {self.max_us:.1f}\n"
            f"    P5:     {self.p5_us:10.1f}    P95: {self.p95_us:.1f}\n"
            f"    P99:    {self.p99_us:10.1f}\n"
            f"\n"
            f"  QUERIES: {self.query_count_mean:.1f} (min: {self.query_count_min}, max: {self.query_count_max})\n"
            f"\n"
            f"  TIME BREAKDOWN:\n"
            f"    DB Time:     {self.db_time_us:10.1f} µs ({self.db_ratio * 100:5.1f}%)\n"
            f"    Python Time: {self.python_time_us:10.1f} µs ({self.python_ratio * 100:5.1f}%)\n"
            f"\n"
            f"  CONSISTENCY: CV={self.cv:.3f}"
            f" ({'stable' if self.cv < 0.1 else 'variable'})\n"
            f"{'=' * 70}"
        )

    def _summary_ms(self) -> str:
        return (
            f"\n{'=' * 70}\n"
            f"  {self.name}\n"
            f"{'=' * 70}\n"
            f"  Iterations: {self.iterations} (samples: {self.total_samples})\n"
            f"\n"
            f"  TIMING (ms):\n"
            f"    Mean:   {self.mean_ms:10.3f}  (±{self.std_dev_ms:.3f} std)\n"
            f"    Median: {self.median_ms:10.3f}\n"
            f"    Min:    {self.min_ms:10.3f}    Max: {self.max_ms:.3f}\n"
            f"    P5:     {self.p5_ms:10.3f}    P95: {self.p95_ms:.3f}\n"
            f"    P25:    {self.p25_ms:10.3f}    P75: {self.p75_ms:.3f}\n"
            f"    P99:    {self.p99_ms:10.3f}\n"
            f"\n"
            f"  QUERIES:\n"
            f"    Count:  {self.query_count_mean:10.1f}  (min: {self.query_count_min}, max: {self.query_count_max})\n"
            f"\n"
            f"  TIME BREAKDOWN:\n"
            f"    DB Time:     {self.db_time_ms:10.3f} ms ({self.db_ratio * 100:5.1f}%)\n"
            f"    Python Time: {self.python_time_ms:10.3f} ms ({self.python_ratio * 100:5.1f}%)\n"
            f"\n"
            f"  CONSISTENCY:\n"
            f"    Coeff. of Variation: {self.cv:.3f}"
            f" ({'stable' if self.cv < 0.1 else 'variable' if self.cv < 0.3 else 'unstable'})\n"
            f"{'=' * 70}"
        )


def compute_stats(
    name: str,
    times_us: list[float],
    query_counts: list[int],
    db_times_us: list[float],
) -> BenchmarkStats:
    """Compute comprehensive statistics from benchmark timing data.

    All input lists must be in **microseconds**.
    """
    clean_times = remove_outliers(times_us)
    clean_db_times = remove_outliers(db_times_us)

    if not clean_times:
        clean_times = times_us

    mean_time = statistics.mean(clean_times)
    std_dev = statistics.stdev(clean_times) if len(clean_times) > 1 else 0

    mean_db = statistics.mean(clean_db_times) if clean_db_times else 0
    python_time = mean_time - mean_db

    return BenchmarkStats(
        name=name,
        iterations=len(times_us),
        total_samples=len(clean_times),
        mean_us=mean_time,
        median_us=statistics.median(clean_times),
        std_dev_us=std_dev,
        min_us=min(clean_times),
        max_us=max(clean_times),
        p5_us=percentile(clean_times, 5),
        p25_us=percentile(clean_times, 25),
        p75_us=percentile(clean_times, 75),
        p95_us=percentile(clean_times, 95),
        p99_us=percentile(clean_times, 99),
        query_count_mean=statistics.mean(query_counts) if query_counts else 0,
        query_count_min=min(query_counts) if query_counts else 0,
        query_count_max=max(query_counts) if query_counts else 0,
        db_time_us=mean_db,
        python_time_us=python_time,
        db_ratio=mean_db / mean_time if mean_time > 0 else 0,
        cv=std_dev / mean_time if mean_time > 0 else 0,
        raw_times_us=times_us,
    )


def run_benchmark(
    name: str,
    func: Callable[[], Any],
    *,
    iterations: int = 50,
    warmup: int = 5,
    setup: Callable[[], None] | None = None,
    teardown: Callable[[], None] | None = None,
    invalidate: Callable[[], None] | None = None,
) -> BenchmarkStats:
    """Run a benchmark function and return statistical results.

    Args:
        name: Descriptive name for the benchmark.
        func: Function to benchmark (no arguments).
        iterations: Number of measured iterations.
        warmup: Number of warmup iterations (excluded from stats).
        setup: Called before each iteration (including warmup).
        teardown: Called after each iteration (including warmup).
        invalidate: Called before each iteration to clear caches (e.g.
            ``env.invalidate_all``).  Pass ``None`` to skip.
    """
    times_us: list[float] = []
    query_counts: list[int] = []
    db_times_us: list[float] = []

    total_runs = warmup + iterations

    for i in range(total_runs):
        if setup:
            setup()
        if invalidate:
            invalidate()

        with BenchmarkTimer() as timer:
            func()

        if teardown:
            teardown()

        if i >= warmup:
            times_us.append(timer.elapsed_us)
            query_counts.append(timer.query_count)
            db_times_us.append(timer.db_time_us)

    return compute_stats(name, times_us, query_counts, db_times_us)


# ---------------------------------------------------------------------------
# PerfTimer — nanosecond-precision timer for micro-benchmarks
# ---------------------------------------------------------------------------


class PerfTimer:
    """Minimal timer for micro-benchmarks.  Measures only wall-clock time
    using ``time.perf_counter_ns`` for sub-microsecond precision.

    Usage::

        timer = PerfTimer()
        for _ in range(N):
            timer.start()
            func()
            timer.stop()
        print(timer.stats("my_func"))
    """

    __slots__ = ("_t0", "samples_ns")

    def __init__(self):
        self._t0: int = 0
        self.samples_ns: list[int] = []

    def start(self):
        self._t0 = time.perf_counter_ns()

    def stop(self):
        self.samples_ns.append(time.perf_counter_ns() - self._t0)

    def stats(self, name: str = "", *, warmup: int = 0) -> dict:
        """Compute statistics from collected samples.

        Returns a dict with p50/p95/p99/mean/min/max in **nanoseconds**
        and human-readable ``summary`` string.
        """
        raw = self.samples_ns[warmup:]
        if not raw:
            return {"name": name, "n": 0}

        us = [ns / 1000.0 for ns in raw]
        clean = remove_outliers(us) or us
        n = len(clean)
        mean = sum(clean) / n
        p50 = percentile(clean, 50)
        p95 = percentile(clean, 95)
        p99 = percentile(clean, 99)
        mn = min(clean)
        mx = max(clean)
        std = statistics.stdev(clean) if n > 1 else 0

        result = {
            "name": name,
            "n": n,
            "mean_us": round(mean, 3),
            "p50_us": round(p50, 3),
            "p95_us": round(p95, 3),
            "p99_us": round(p99, 3),
            "min_us": round(mn, 3),
            "max_us": round(mx, 3),
            "std_us": round(std, 3),
            "cv": round(std / mean, 4) if mean > 0 else 0,
        }
        result["summary"] = (
            f"{name:<55s}  n={n:>4d}  "
            f"p50={p50:>10.1f}µs  p95={p95:>10.1f}µs  "
            f"mean={mean:>10.1f}µs  cv={result['cv']:.2f}"
        )
        return result


# ---------------------------------------------------------------------------
# BenchmarkTimer — context manager with query tracking
# ---------------------------------------------------------------------------


class BenchmarkTimer:
    """Context manager for precise timing with query tracking.

    Stores raw seconds internally; exposes both millisecond and microsecond
    accessors so SQL-level and ORM-level benchmarks can share the same timer.

    Usage::

        with BenchmarkTimer() as t:
            do_something()
        print(f"{t.elapsed_us:.1f} µs, {t.query_count} queries")
    """

    def __init__(self):
        self.start_time: float = 0
        self.end_time: float = 0
        self.start_query_count: int = 0
        self.end_query_count: int = 0
        self.start_query_time: float = 0
        self.end_query_time: float = 0

    def __enter__(self):
        thread = threading.current_thread()
        if not hasattr(thread, "query_count"):
            thread.query_count = 0
        if not hasattr(thread, "query_time"):
            thread.query_time = 0

        self.start_query_count = thread.query_count
        self.start_query_time = thread.query_time
        self.start_time = real_time()
        return self

    def __exit__(self, *args):
        self.end_time = real_time()
        thread = threading.current_thread()
        self.end_query_count = thread.query_count
        self.end_query_time = thread.query_time

    @property
    def elapsed_us(self) -> float:
        """Total elapsed time in microseconds."""
        return (self.end_time - self.start_time) * 1_000_000

    @property
    def elapsed_ms(self) -> float:
        """Total elapsed time in milliseconds."""
        return (self.end_time - self.start_time) * 1000

    @property
    def query_count(self) -> int:
        """Number of SQL queries executed."""
        return self.end_query_count - self.start_query_count

    @property
    def db_time_us(self) -> float:
        """Time spent waiting for database in microseconds."""
        return (self.end_query_time - self.start_query_time) * 1_000_000

    @property
    def db_time_ms(self) -> float:
        """Time spent waiting for database in milliseconds."""
        return (self.end_query_time - self.start_query_time) * 1000

    @property
    def orm_overhead_us(self) -> float:
        """Time spent in Python (non-DB) in microseconds."""
        return self.elapsed_us - self.db_time_us

    @property
    def python_time_ms(self) -> float:
        """Time spent in Python (non-DB) in milliseconds."""
        return self.elapsed_ms - self.db_time_ms


# ---------------------------------------------------------------------------
# JSON persistence for before/after comparison
# ---------------------------------------------------------------------------


def save_results(results: list[dict], path: str):
    """Append benchmark results to a JSON-lines file for before/after comparison."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("a") as f:
        f.writelines(json.dumps(r, default=str) + "\n" for r in results)


def compare_results(baseline: list[dict], current: list[dict]) -> str:
    """Compare two sets of benchmark results and return a report."""
    base_map = {r["name"]: r for r in baseline if r.get("name")}
    lines = []
    lines.extend((f"\n{'Test':<55s} {'Base p50':>10s} {'Curr p50':>10s} {'Speedup':>8s}", "-" * 90))
    for r in current:
        name = r.get("name", "")
        base = base_map.get(name)
        if not base:
            lines.append(
                f"{name:<55s} {'N/A':>10s} {r.get('p50_us', 0):>10.1f} {'NEW':>8s}"
            )
            continue
        bp = base.get("p50_us", 0)
        cp = r.get("p50_us", 0)
        if cp > 0:
            speedup = bp / cp
            marker = "+" if speedup >= 1.05 else ("-" if speedup <= 0.95 else "=")
            lines.append(
                f"{name:<55s} {bp:>10.1f} {cp:>10.1f} {speedup:>7.2f}x {marker}"
            )
        else:
            lines.append(f"{name:<55s} {bp:>10.1f} {cp:>10.1f} {'inf':>8s}")
    return "\n".join(lines)
