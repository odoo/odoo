import logging
import math
import statistics
import time
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Self

from odoo.libs.debug_log import DebugLog
from odoo.libs.worker_thread import current_worker_thread

if TYPE_CHECKING:
    from collections.abc import Callable

OUTLIER_PERCENTILE = 5

_benchmark_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


def percentile(data: list[float], p: float) -> float:
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
    return [data[i] for i in _inlier_indices(data, percentile_cutoff)]


def _inlier_indices(
    data: list[float], percentile_cutoff: float = OUTLIER_PERCENTILE
) -> list[int]:
    if len(data) < 10:
        _debug.logic("test.benchmark.outliers_kept", samples=len(data))
        return list(range(len(data)))
    lower = percentile(data, percentile_cutoff)
    upper = percentile(data, 100 - percentile_cutoff)
    kept = [i for i, x in enumerate(data) if lower <= x <= upper]
    _debug.logic(
        "test.benchmark.outliers_trimmed",
        samples=len(data),
        kept=len(kept),
        lower=lower,
        upper=upper,
    )
    return kept


@dataclass(slots=True)
class BenchmarkStats:
    name: str
    iterations: int
    total_samples: int

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

    query_count_mean: float
    query_count_min: int
    query_count_max: int

    db_time_us: float
    python_time_us: float
    db_ratio: float

    cv: float

    raw_times_us: list[float] = field(default_factory=list, repr=False)

    def __getattr__(self, name: str) -> float:
        if name.endswith("_ms"):
            try:
                return getattr(self, f"{name[:-3]}_us") / 1000
            except AttributeError:
                pass
        raise AttributeError(
            f"{type(self).__name__!r} object has no attribute {name!r}"
        )

    @property
    def python_ratio(self) -> float:
        return 1 - self.db_ratio

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("raw_times_us", None)
        d["p50_us"] = d["median_us"]
        return d

    def summary(self, unit: str = "auto") -> str:
        if unit == "auto":
            unit = "ms" if self.mean_us > 1000 else "us"
        return self._summary(unit)

    def _summary(self, unit: str) -> str:
        p = 1 if unit == "us" else 3
        v = {
            field: getattr(self, f"{field}_{unit}")
            for field in (
                "mean",
                "median",
                "std_dev",
                "min",
                "max",
                "p5",
                "p25",
                "p75",
                "p95",
                "p99",
                "db_time",
                "python_time",
            )
        }
        symbol = "\u00b5s" if unit == "us" else "ms"
        if self.cv < 0.1:
            stability = "stable"
        elif self.cv < 0.3:
            stability = "variable"
        else:
            stability = "unstable"
        return (
            f"\n{'=' * 70}\n"
            f"  {self.name}\n"
            f"{'=' * 70}\n"
            f"  Iterations: {self.iterations} (samples: {self.total_samples})\n"
            f"\n"
            f"  TIMING ({symbol}) -- Min/Max raw, mean and percentiles trimmed:\n"
            f"    Mean:   {v['mean']:10.{p}f}  (\u00b1{v['std_dev']:.{p}f} std)\n"
            f"    Median: {v['median']:10.{p}f}\n"
            f"    Min:    {v['min']:10.{p}f}    Max: {v['max']:.{p}f}\n"
            f"    P5:     {v['p5']:10.{p}f}    P95: {v['p95']:.{p}f}\n"
            f"    P25:    {v['p25']:10.{p}f}    P75: {v['p75']:.{p}f}\n"
            f"    P99:    {v['p99']:10.{p}f}\n"
            f"\n"
            f"  QUERIES:\n"
            f"    Count:  {self.query_count_mean:10.1f}  "
            f"(min: {self.query_count_min}, max: {self.query_count_max})\n"
            f"\n"
            f"  TIME BREAKDOWN:\n"
            f"    DB Time:     {v['db_time']:10.{p}f} {symbol} "
            f"({self.db_ratio * 100:5.1f}%)\n"
            f"    Python Time: {v['python_time']:10.{p}f} {symbol} "
            f"({self.python_ratio * 100:5.1f}%)\n"
            f"\n"
            f"  CONSISTENCY:\n"
            f"    Coeff. of Variation: {self.cv:.3f} ({stability})\n"
            f"{'=' * 70}"
        )


def compute_stats(
    name: str,
    times_us: list[float],
    query_counts: list[int],
    db_times_us: list[float],
) -> BenchmarkStats:
    if not times_us:
        _debug.logic("test.benchmark.no_samples", name=name)
        raise ValueError(
            f"benchmark {name!r} collected no samples: check that iterations > 0"
        )

    indices = _inlier_indices(times_us) or range(len(times_us))
    clean_times = [times_us[i] for i in indices]
    clean_db_times = (
        [db_times_us[i] for i in indices]
        if len(db_times_us) == len(times_us)
        else db_times_us
    )
    clean_query_counts = (
        [query_counts[i] for i in indices]
        if len(query_counts) == len(times_us)
        else query_counts
    )

    mean_time = statistics.mean(clean_times)
    std_dev = statistics.stdev(clean_times) if len(clean_times) > 1 else 0

    mean_db = statistics.mean(clean_db_times) if clean_db_times else 0
    python_time = mean_time - mean_db

    _debug.perf.count(
        "test.benchmark.stats",
        name=name,
        samples=len(times_us),
        kept=len(clean_times),
        db_aligned=len(db_times_us) == len(times_us),
        queries_aligned=len(query_counts) == len(times_us),
        mean_us=mean_time,
        db_us=mean_db,
        cv=std_dev / mean_time if mean_time > 0 else 0,
    )
    return BenchmarkStats(
        name=name,
        iterations=len(times_us),
        total_samples=len(clean_times),
        mean_us=mean_time,
        median_us=statistics.median(clean_times),
        std_dev_us=std_dev,
        min_us=min(times_us),
        max_us=max(times_us),
        p5_us=percentile(clean_times, 5),
        p25_us=percentile(clean_times, 25),
        p75_us=percentile(clean_times, 75),
        p95_us=percentile(clean_times, 95),
        p99_us=percentile(clean_times, 99),
        query_count_mean=statistics.mean(clean_query_counts)
        if clean_query_counts
        else 0,
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
    times_us: list[float] = []
    query_counts: list[int] = []
    db_times_us: list[float] = []

    total_runs = warmup + iterations
    _debug.pipeline(
        "test.benchmark.start",
        name=name,
        iterations=iterations,
        warmup=warmup,
        setup=setup is not None,
        teardown=teardown is not None,
        invalidate=invalidate is not None,
    )

    with _debug.perf("test.benchmark.run", name=name, runs=total_runs) as span:
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
        span.set(samples=len(times_us))

    return compute_stats(name, times_us, query_counts, db_times_us)


class PerfTimer:
    __slots__ = ("_t0", "samples_ns")

    def __init__(self) -> None:
        self._t0: int = 0
        self.samples_ns: list[int] = []

    def start(self) -> None:
        self._t0 = time.perf_counter_ns()

    def stop(self) -> None:
        self.samples_ns.append(time.perf_counter_ns() - self._t0)

    def stats(self, name: str = "", *, warmup: int = 0) -> dict:
        raw = self.samples_ns[warmup:]
        _debug.perf.count(
            "test.benchmark.perf_timer",
            name=name,
            samples=len(self.samples_ns),
            warmup=warmup,
        )
        if not raw:
            return {"name": name, "n": 0}

        us = [ns / 1000.0 for ns in raw]
        clean = remove_outliers(us) or us
        n = len(clean)
        mean = sum(clean) / n
        p50 = percentile(clean, 50)
        p95 = percentile(clean, 95)
        p99 = percentile(clean, 99)
        mn = min(us)
        mx = max(us)
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


class BenchmarkTimer:
    def __init__(self) -> None:
        self.start_time: float = 0
        self.end_time: float = 0
        self.start_query_count: int = 0
        self.end_query_count: int = 0
        self.start_query_time: float = 0
        self.end_query_time: float = 0

    def __enter__(self) -> Self:
        thread = current_worker_thread()
        if not hasattr(thread, "query_count"):
            _debug.logic("test.benchmark.thread_counter_initialised", counter="count")
            thread.query_count = 0
        if not hasattr(thread, "query_time"):
            _debug.logic("test.benchmark.thread_counter_initialised", counter="time")
            thread.query_time = 0

        self.start_query_count = thread.query_count
        self.start_query_time = thread.query_time
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args: object) -> None:
        self.end_time = time.perf_counter()
        thread = current_worker_thread()
        self.end_query_count = thread.query_count
        self.end_query_time = thread.query_time

    @property
    def elapsed_us(self) -> float:
        return (self.end_time - self.start_time) * 1_000_000

    @property
    def elapsed_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000

    @property
    def query_count(self) -> int:
        return self.end_query_count - self.start_query_count

    @property
    def db_time_us(self) -> float:
        return (self.end_query_time - self.start_query_time) * 1_000_000

    @property
    def db_time_ms(self) -> float:
        return (self.end_query_time - self.start_query_time) * 1000

    @property
    def orm_overhead_us(self) -> float:
        return self.elapsed_us - self.db_time_us

    @property
    def python_time_ms(self) -> float:
        return self.elapsed_ms - self.db_time_ms


def compare_results(baseline: list[dict], current: list[dict]) -> str:
    base_map = {r["name"]: r for r in baseline if r.get("name")}
    _debug.perf.count(
        "test.benchmark.compare",
        baseline=len(base_map),
        current=len(current),
        new=sum(1 for r in current if r.get("name", "") not in base_map),
    )
    lines: list[str] = []
    lines.extend(
        (
            f"\n{'Test':<55s} {'Base p50':>10s} {'Curr p50':>10s} {'Speedup':>8s}",
            "-" * 90,
        )
    )
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


class BenchmarkCase:
    benchmark_log_prefix = "BENCHMARK"
    benchmark_iterations = 30
    benchmark_warmup = 5

    all_results: ClassVar[list[BenchmarkStats]]
    env: Any

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()  # type: ignore[misc]  # the concrete suite mixes in TransactionCase
        cls.all_results = []

    def _run_benchmark(
        self,
        name: str,
        func: Callable[[], Any],
        *,
        iterations: int | None = None,
        warmup: int | None = None,
        setup: Callable[[], None] | None = None,
        teardown: Callable[[], None] | None = None,
        invalidate_cache: bool = True,
    ) -> BenchmarkStats:
        _debug.pipeline(
            "test.benchmark.case",
            cls=type(self).__qualname__,
            name=name,
            invalidate_cache=invalidate_cache,
        )
        stats = run_benchmark(
            name,
            func,
            iterations=self.benchmark_iterations if iterations is None else iterations,
            warmup=self.benchmark_warmup if warmup is None else warmup,
            setup=setup,
            teardown=teardown,
            invalidate=self.env.invalidate_all if invalidate_cache else None,
        )
        self.all_results.append(stats)
        _benchmark_logger.info("[%s] %s", self.benchmark_log_prefix, stats.summary())
        return stats

    def log_benchmark_summary(self, unit: str = "auto") -> None:
        prefix = self.benchmark_log_prefix
        _debug.lifecycle(
            "test.benchmark.summary",
            cls=type(self).__qualname__,
            results=len(self.all_results),
            unit=unit,
        )
        if not self.all_results:
            _benchmark_logger.info("[%s] no results to summarise", prefix)
            return

        _benchmark_logger.info(
            "[%s] %d benchmarks, slowest first:", prefix, len(self.all_results)
        )
        for stat in sorted(self.all_results, key=lambda s: -s.mean_us):
            _benchmark_logger.info("[%s]   %s", prefix, stat.summary(unit))
