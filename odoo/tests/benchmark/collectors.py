"""Metric declarations, independent collectors and measurement scopes."""

import math
import statistics
import threading
import time
from contextlib import ExitStack, contextmanager
from dataclasses import KW_ONLY, dataclass
from typing import Protocol


@dataclass(frozen=True)
class Metric:
    key: str
    label: str
    _: KW_ONLY
    unit: str = ''
    precision: int = 0
    show_range: bool = False

    def format(self, value):
        if self.precision == 0 and type(value) is int:
            return str(value)
        return f'{value:.{self.precision}f}'


@dataclass(frozen=True)
class Aggregation:
    values: dict[str, float | int]
    warnings: tuple[str, ...] = ()


class Collector(Protocol):
    """Collect declared metrics with start()/stop(), then aggregate measured samples.

    stop() and aggregate().values must contain exactly the declared metric keys.
    Reporting aggregates on fresh instances, so aggregate() must depend only on
    its samples and declarations, never on state initialized by start(). Warmup
    and profiling executions are excluded from those samples.
    Lower start_order values start first; ties retain registration order.
    """
    name: str
    start_order: int
    metrics: tuple[Metric, ...]

    def start(self) -> None: ...

    def stop(self) -> dict[str, float | int]: ...

    def aggregate(self, samples: list[dict[str, float | int]]) -> Aggregation: ...


class WallCollector(Collector):
    """Elapsed time in seconds, including waits."""

    name = 'wall'
    start_order = 100
    metrics = (Metric('wall_s', 'wall', unit='s', precision=3, show_range=True),)
    start_time: float

    def start(self):
        self.start_time = time.perf_counter()

    def stop(self):
        return {'wall_s': time.perf_counter() - self.start_time}

    def aggregate(self, samples):
        return Aggregation({'wall_s': statistics.median(sample['wall_s'] for sample in samples)})


class CPUCollector(Collector):
    """Python process CPU time across all threads, excluding PostgreSQL CPU time."""

    name = 'cpu'
    start_order = 90
    metrics = (Metric('cpu_s', 'cpu', unit='s', precision=3),)
    start_time: float

    def start(self):
        self.start_time = time.process_time()

    def stop(self):
        return {'cpu_s': time.process_time() - self.start_time}

    def aggregate(self, samples):
        return Aggregation({'cpu_s': statistics.median(sample['cpu_s'] for sample in samples)})


class QueryCollector(Collector):
    """Client-observed SQL duration and counts on the current thread, across cursors.

    Classify by the first keyword: SELECT, INSERT, UPDATE and DELETE have their
    own counters; WITH-prefixed queries and transaction control count as other.
    """
    name = 'queries'
    start_order = 10
    counters = (
        Metric('queries', 'queries'),
        Metric('select', 'SELECT'),
        Metric('insert', 'INSERT'),
        Metric('update', 'UPDATE'),
        Metric('delete', 'DELETE'),
        Metric('other', 'other'),
    )
    metrics = (Metric('sql_s', 'sql', unit='s', precision=3), *counters)
    values: dict[str, float | int]
    thread: threading.Thread

    def start(self):
        self.values = dict.fromkeys((metric.key for metric in self.metrics), 0)
        self.thread = threading.current_thread()
        if not hasattr(self.thread, 'query_hooks'):
            self.thread.query_hooks = []
        self.thread.query_hooks.append(self.hook)

    def hook(self, cr, query, params, query_start, query_time):
        if isinstance(query, bytes):
            query = query.decode('ascii', errors='replace')
        elif not isinstance(query, str):
            query = query.as_string(cr._obj)
        words = query.lstrip().split(maxsplit=1)
        keyword = words[0].lower() if words else ''
        kind = keyword if keyword in ('select', 'insert', 'update', 'delete') else 'other'
        self.values['queries'] += 1
        self.values[kind] += 1

        # Hooks run before execution: query_time is not the final duration.
        # The returned callback receives the actual duration after completion.
        def completed(duration):
            self.values['sql_s'] += duration

        return completed

    def stop(self):
        self.thread.query_hooks.remove(self.hook)
        return self.values

    def aggregate(self, samples):
        # Separate medians can produce counters that no round actually had.
        # median_low picks an observed total even with an even number of rounds;
        # copying that round's breakdown keeps its sum equal to the total.
        query_count = statistics.median_low(sample['queries'] for sample in samples)
        representative = next(sample for sample in samples if sample['queries'] == query_count)
        counters = [metric.key for metric in self.counters]
        values = {'sql_s': statistics.median(sample['sql_s'] for sample in samples)}
        values.update((key, representative[key]) for key in counters)
        varies = len({tuple(sample[key] for key in counters) for sample in samples}) > 1
        warnings = ('Query count or breakdown varies across rounds',) if varies else ()
        return Aggregation(values, warnings)


# Install SQL hooks before starting timers so setup is excluded from timings.
# Start wall timing last to exclude the other collectors' setup and cleanup.
# Registration controls display order; start_order controls startup order.
COLLECTORS = (WallCollector, CPUCollector, QueryCollector)


def validate_values(values, metrics, source):
    keys = {metric.key for metric in metrics}
    if not isinstance(values, dict) or values.keys() != keys:
        raise ValueError(f'Metric keys from {source} do not match declarations: expected {sorted(keys)}, got {values!r}')
    if any(type(value) not in (int, float) or (type(value) is float and not math.isfinite(value)) for value in values.values()):
        raise ValueError(f'Invalid metric values from {source}: {values!r}')


@contextmanager
def collect():
    """Yield an empty metric dict, populated only after successful context exit.

    Stop collectors in reverse startup order, including on failure.
    """
    collectors = [factory() for factory in sorted(COLLECTORS, key=lambda factory: factory.start_order)]
    if any(collector.name == 'wall' for collector in collectors[:-1]):
        msg = "Wall timing must start last to exclude other collectors' setup and cleanup"
        raise ValueError(msg)
    values = {}
    stopped = {}

    def stop(collector):
        stopped[collector.name] = collector.stop()

    with ExitStack() as stack:
        for collector in collectors:
            collector.start()
            stack.callback(stop, collector)
        yield values

    # Check metric keys and numeric values after stopping timers so validation
    # work does not inflate the reported benchmark timings.
    for collector in collectors:
        measured = stopped[collector.name]
        validate_values(measured, collector.metrics, collector.name)
        values.update(measured)
