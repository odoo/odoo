"""Metric declarations, independent collectors and measurement scopes."""

import math
import statistics
import threading
import time
from contextlib import ExitStack, contextmanager
from dataclasses import KW_ONLY, dataclass


@dataclass(frozen=True)
class Metric:
    key: str
    label: str | None = None
    _: KW_ONLY
    unit: str = ''
    precision: int = 0
    show_range: bool = False

    def __post_init__(self):
        if self.label is None:
            object.__setattr__(self, 'label', self.key)

    def format(self, value):
        if self.precision == 0 and type(value) is int:
            return str(value)
        return f'{value:.{self.precision}f}'


@dataclass(frozen=True)
class Aggregation:
    values: dict[str, float | int]
    warnings: tuple[str, ...] = ()


class Collector:
    """Add metrics by defining name, metrics, start() and stop().

    Select a collector on a benchmark class with collectors = ('name',).
    Declare a unique, non-empty name on each concrete subclass to register it.
    Inherited names do not register subclasses; duplicate names raise ValueError.

    stop() returns a numeric value for each declared metric. Results use medians
    unless aggregate() is overridden. Each measurement gets a fresh collector;
    aggregate() is a class method and receives the measured samples.

    After start() succeeds, stop() is called even if the measured code raises.
    stop() must remove instrumentation and return its readings. If start() raises,
    it must undo its own partial setup: stop() will not be called for that instance.

    Lower start_order values start first and stop last.
    """
    name = None
    start_order = 0
    metrics = ()
    _registry = {}

    def __init_subclass__(cls):
        super().__init_subclass__()
        name = cls.__dict__.get('name')
        if name is None:
            return
        if not isinstance(name, str) or not name:
            raise ValueError(f'Collector name must be a non-empty string: {name!r}')
        if name in cls._registry:
            raise ValueError(f'Benchmark collector {name!r} is already registered')
        cls._registry[name] = cls

    def __init__(self, case=None):
        self.case = case

    def __class_getitem__(cls, name):
        try:
            return cls._registry[name]
        except KeyError:
            raise ValueError(f'Unknown benchmark collector {name!r}') from None

    def start(self):
        pass

    def stop(self):
        raise NotImplementedError

    @classmethod
    def aggregate(cls, samples: list[dict[str, float | int]]) -> Aggregation:
        """Summarize one metric dictionary per measured execution.

        For 'wall', samples could be [{'wall_s': 0.12}, {'wall_s': 0.10}].
        Each dictionary contains only this collector's declared metric keys.
        Warmups are excluded. The default returns the median of each metric.
        """
        return Aggregation({
            metric.key: statistics.median(sample[metric.key] for sample in samples)
            for metric in cls.metrics
        })


class WallCollector(Collector):
    """Elapsed time in seconds, including waits."""

    name = 'wall'
    start_order = 1001  # Start timers after observers to exclude their setup and cleanup.
    metrics = (Metric('wall_s', 'wall', unit='s', precision=3, show_range=True),)
    start_time: float

    def start(self):
        self.start_time = time.perf_counter()

    def stop(self):
        return {'wall_s': time.perf_counter() - self.start_time}


class CPUCollector(Collector):
    """Python process CPU time across all threads, excluding PostgreSQL CPU time."""

    name = 'cpu'
    start_order = 1000
    metrics = (Metric('cpu_s', 'cpu', unit='s', precision=3),)
    start_time: float

    def start(self):
        self.start_time = time.process_time()

    def stop(self):
        return {'cpu_s': time.process_time() - self.start_time}


class QueryCollector(Collector):
    """SQL duration and counts on the test thread and its HTTP request cursors.

    Classify by the first keyword: SELECT, INSERT, UPDATE and DELETE have their
    own counters; WITH-prefixed queries and transaction control count as other.
    """
    name = 'sql'
    start_order = 10
    counters = (
        Metric('queries'),
        Metric('select', 'SELECT'),
        Metric('insert', 'INSERT'),
        Metric('update', 'UPDATE'),
        Metric('delete', 'DELETE'),
        Metric('other'),
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
        if self.case is not None:
            self.case.cr.query_hooks.append(self._cursor_hook)

    def _cursor_hook(self, *args):
        # The thread hook already handles this thread, including other cursors.
        # Shared test cursors need observation when used by HTTP request threads.
        if threading.current_thread() is not self.thread:
            return self.hook(*args)
        return None

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
        if self.case is not None:
            self.case.cr.query_hooks.remove(self._cursor_hook)
        return self.values

    @classmethod
    def aggregate(cls, samples: list[dict[str, float | int]]) -> Aggregation:
        # Separate medians can produce counters that no round actually had.
        # median_low picks an observed total even with an even number of rounds;
        # copying that round's breakdown keeps its sum equal to the total.
        query_count = statistics.median_low(sample['queries'] for sample in samples)
        representative = next(sample for sample in samples if sample['queries'] == query_count)
        counters = [metric.key for metric in cls.counters]
        values = {'sql_s': statistics.median(sample['sql_s'] for sample in samples)}
        values.update((key, representative[key]) for key in counters)
        varies = len({tuple(sample[key] for key in counters) for sample in samples}) > 1
        warnings = ('Query count or breakdown varies across rounds',) if varies else ()
        return Aggregation(values, warnings)


def validate_values(values, metrics, source):
    keys = {metric.key for metric in metrics}
    if not isinstance(values, dict) or values.keys() != keys:
        raise ValueError(f'Metric keys from {source} do not match declarations: expected {sorted(keys)}, got {values!r}')
    if any(type(value) not in (int, float) or (type(value) is float and not math.isfinite(value)) for value in values.values()):
        raise ValueError(f'Invalid metric values from {source}: {values!r}')


@contextmanager
def collect(factories, case=None):
    """Measure code and retain readings on both normal and exceptional exit."""
    collectors = [factory(case) for factory in sorted(factories, key=lambda factory: factory.start_order)]
    values = {}
    stopped = {}

    def stop(collector):
        stopped[collector.name] = collector.stop()

    try:
        with ExitStack() as stack:
            for collector in collectors:
                collector.start()
                stack.callback(stop, collector)
            yield values
    finally:
        # Keep readings when an enclosing assertion catches the exception.
        # Validate after all timers stop, including after partial startup failure.
        for collector in collectors:
            if collector.name in stopped:
                measured = stopped[collector.name]
                validate_values(measured, collector.metrics, collector.name)
                values.update(measured)
