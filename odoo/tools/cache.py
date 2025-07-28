# Part of Odoo. See LICENSE file for full copyright and licensing details.
# decorator makes wrappers that have the same API as their wrapped function
from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Collection
from decorator import decorator
from inspect import signature, Parameter
from itertools import chain
import logging
import signal
import sys
import threading
import time
import typing
import warnings

if typing.TYPE_CHECKING:
    from .lru import LRU
    from collections.abc import Callable, Iterable
    from odoo.models import BaseModel
    C = typing.TypeVar('C', bound=Callable)

unsafe_eval = eval

_logger = logging.getLogger(__name__)
_logger_lock = threading.RLock()
_logger_state: typing.Literal['wait', 'abort', 'run'] = 'wait'


class ormcache_counter:
    """ Statistic counters for cache entries. """
    __slots__ = ['hit', 'miss', 'err', 'gen_time', 'cache_name']

    def __init__(self):
        self.hit: int = 0
        self.miss: int = 0
        self.err: int = 0
        self.gen_time: float = 0.0
        self.cache_name: str = ''

    @property
    def ratio(self) -> float:
        return 100.0 * self.hit / (self.hit + self.miss or 1)


_COUNTERS: defaultdict[tuple[str, Callable], ormcache_counter] = defaultdict(ormcache_counter)
"""statistic counters dictionary, maps (dbname, method) to counter"""


class ormcache:
    """ LRU cache decorator for model methods.
    The parameters are strings that represent expressions referring to the
    signature of the decorated method, and are used to compute a cache key::

        @ormcache('model_name', 'mode')
        def _compute_domain(self, model_name, mode="read"):
            ...

    For the sake of backward compatibility, the decorator supports the named
    parameter `skiparg`::

        @ormcache(skiparg=1)
        def _compute_domain(self, model_name, mode="read"):
            ...

    Methods implementing this decorator should never return a Recordset,
    because the underlying cursor will eventually be closed and raise a
    `psycopg2.InterfaceError`.
    """
    key: Callable[..., tuple]

    def __init__(self, *args: str, cache: str = 'default', skiparg: int | None = None, **kwargs):
        self.args = args
        self.skiparg = skiparg
        self.cache_name = cache
        if skiparg is not None:
            warnings.warn("Deprecated since 19.0, ormcache(skiparg) will be removed", DeprecationWarning)

    def __call__(self, method: C) -> C:
        assert not hasattr(self, 'method'), "ormcache is already bound to a method"
        self.method = method
        self.determine_key()
        assert self.key is not None, "ormcache.key not initialized"
        lookup: C = decorator(self.lookup, method)  # type: ignore
        lookup.__cache__ = self  # type: ignore
        return lookup

    def add_value(self, *args, cache_value=None, **kwargs) -> None:
        model: BaseModel = args[0]
        d: LRU = model.pool._Registry__caches[self.cache_name]  # type: ignore
        key = self.key(*args, **kwargs)
        d[key] = cache_value

    def determine_key(self) -> None:
        """ Determine the function that computes a cache key from arguments. """
        assert self.method is not None
        if self.skiparg is not None:
            # backward-compatible function that uses self.skiparg
            self.key = lambda *args, **kwargs: (args[0]._name, self.method, *args[self.skiparg:])
            return
        # build a string that represents function code and evaluate it
        args = ', '.join(
            # remove annotations because lambdas can't be type-annotated,
            # and defaults because they are redundant (defaults are present
            # in the wrapper function itself)
            str(params.replace(annotation=Parameter.empty, default=Parameter.empty))
            for params in signature(self.method).parameters.values()
        )
        values = ['self._name', 'method', *self.args]
        code = f"lambda {args}: ({''.join(a for arg in values for a in (arg, ','))})"
        self.key = unsafe_eval(code, {'method': self.method})

    def lookup(self, method, *args, **kwargs):
        model: BaseModel = args[0]
        d: LRU = model.pool._Registry__caches[self.cache_name]  # type: ignore
        key = self.key(*args, **kwargs)
        counter = _COUNTERS[model.pool.db_name, self.method]
        counter.cache_name = self.cache_name
        try:
            r = d[key]
            counter.hit += 1
            return r
        except KeyError:
            counter.miss += 1
            start = time.monotonic()
            value = self.method(*args, **kwargs)
            counter.gen_time += time.monotonic() - start
            d[key] = value
            return value
        except TypeError:
            _logger.warning("cache lookup error on %r", key, exc_info=True)
            counter.err += 1
            return self.method(*args, **kwargs)


class ormcache_context(ormcache):
    """ This LRU cache decorator is a variant of :class:`ormcache`, with an
    extra parameter ``keys`` that defines a sequence of dictionary keys. Those
    keys are looked up in the ``context`` parameter and combined to the cache
    key made by :class:`ormcache`.
    """
    def __init__(self, *args: str, keys, skiparg=None, **kwargs):
        assert skiparg is None, "ormcache_context() no longer supports skiparg"
        warnings.warn("Since 19.0, use ormcache directly, context values are available as `self.env.context.get`", DeprecationWarning)
        super().__init__(*args, **kwargs)

    def determine_key(self) -> None:
        assert self.method is not None
        sign = signature(self.method)
        cont_expr = "(context or {})" if 'context' in sign.parameters else "self.env.context"
        keys_expr = "tuple(%s.get(k) for k in %r)" % (cont_expr, self.keys)
        self.args += (keys_expr,)
        super().determine_key()


def log_ormcache_stats(sig=None, frame=None):    # noqa: ARG001 (arguments are there for signals)
    # collect and log data in a separate thread to avoid blocking the main thread
    # and avoid using logging module directly in the signal handler
    # https://docs.python.org/3/library/logging.html#thread-safety
    global _logger_state  # noqa: PLW0603
    with _logger_lock:
        if _logger_state != 'wait':
            # send the signal again to stop the logging thread
            _logger_state = 'abort'
            return
        _logger_state = 'run'

    def check_continue_logging():
        if _logger_state == 'run':
            return True
        _logger.info('Stopping logging ORM cache stats')
        return False

    class StatsLine:
        def __init__(self, method, counter: ormcache_counter):
            self.sz_entries_sum: int = 0
            self.sz_entries_max: int = 0
            self.nb_entries: int = 0
            self.counter = counter
            self.method = method

    def _log_ormcache_stats():
        """ Log statistics of ormcache usage by database, model, and method. """
        from odoo.modules.registry import Registry  # noqa: PLC0415
        try:
            # {dbname: {method: StatsLine}}
            cache_stats: defaultdict[str, dict[Callable, StatsLine]] = defaultdict(dict)

            # browse the values in cache
            registries = Registry.registries.snapshot
            class_slots = {}
            for i, (dbname, registry) in enumerate(registries.items(), start=1):
                if not check_continue_logging():
                    return
                _logger.info("Processing database %s (%d/%d)", dbname, i, len(registries))
                db_cache_stats = cache_stats[dbname]
                for cache in registry._Registry__caches.values():
                    for cache_key, cache_value in cache.snapshot.items():
                        method = cache_key[1]
                        stats = db_cache_stats.get(method)
                        if stats is None:
                            stats = db_cache_stats[method] = StatsLine(method, _COUNTERS[dbname, method])
                        stats.nb_entries += 1
                        if not show_size:
                            continue
                        size = get_cache_size(cache_value, cache_info=method.__qualname__, class_slots=class_slots)
                        stats.sz_entries_sum += size
                        stats.sz_entries_max = max(stats.sz_entries_max, size)

            # add counters that have no values in cache
            for (dbname, method), counter in _COUNTERS.copy().items():  # copy to avoid concurrent modification
                if not check_continue_logging():
                    return
                db_cache_stats = cache_stats[dbname]
                stats = db_cache_stats.get(method)
                if stats is None:
                    db_cache_stats[method] = StatsLine(method, counter)

            # Output the stats
            log_msgs = ['Caches stats:']
            size_column_info = (
                f"{'Memory %':>10},"
                f"{'Memory SUM':>12},"
                f"{'Memory MAX':>12},"
            ) if show_size else ''
            column_info = (
                f"{'Cache Name':>25},"
                f"{'Entry':>7},"
                f"{size_column_info}"
                f"{'Hit':>6},"
                f"{'Miss':>6},"
                f"{'Err':>6},"
                f"{'Gen Time [s]':>13},"
                f"{'Hit Ratio':>10},"
                "  Method"
            )

            for dbname, db_cache_stats in sorted(cache_stats.items(), key=lambda k: k[0] or '~'):
                if not check_continue_logging():
                    return
                log_msgs.extend((f'Database {dbname or "<no_db>"}:', column_info))

                # sort by -sz_entries_sum and method_name
                db_cache_stat = sorted(db_cache_stats.items(), key=lambda k: (-k[1].sz_entries_sum, k[0].__name__))
                sz_entries_all = sum(stat.sz_entries_sum for _, stat in db_cache_stat)
                for method, stat in db_cache_stat:
                    size_data = (
                        f'{stat.sz_entries_sum / (sz_entries_all or 1) * 100:9.1f}%,'
                        f'{stat.sz_entries_sum:12d},'
                        f'{stat.sz_entries_max:12d},'
                    ) if show_size else ''
                    log_msgs.append(
                        f'{stat.counter.cache_name:>25},'
                        f'{stat.nb_entries:7d},'
                        f'{size_data}'
                        f'{stat.counter.hit:6d},'
                        f'{stat.counter.miss:6d},'
                        f'{stat.counter.err:6d},'
                        f'{stat.counter.gen_time:13.3f},'
                        f'{stat.counter.ratio:9.1f}%,'
                        f'  {method.__qualname__}'
                    )
            _logger.info('\n'.join(log_msgs))
        except Exception:  # noqa: BLE001
            _logger.exception()
        finally:
            global _logger_state  # noqa: PLW0603
            with _logger_lock:
                _logger_state = 'wait'

    show_size = False
    if sig == signal.SIGUSR1:
        threading.Thread(target=_log_ormcache_stats,
                         name="odoo.signal.log_ormcache_stats").start()
    elif sig == signal.SIGUSR2:
        show_size = True
        threading.Thread(target=_log_ormcache_stats,
                         name="odoo.signal.log_ormcache_stats_with_size").start()


def get_cache_key_counter(bound_method: Callable, *args, **kwargs) -> tuple[LRU, tuple, ormcache_counter]:
    """ Return the cache, key and stat counter for the given call. """
    model: BaseModel = bound_method.__self__  # type: ignore
    ormcache_instance: ormcache = bound_method.__cache__  # type: ignore
    cache: LRU = model.pool._Registry__caches[ormcache_instance.cache_name]  # type: ignore
    key = ormcache_instance.key(model, *args, **kwargs)
    counter = _COUNTERS[model.pool.db_name, ormcache_instance.method]
    return cache, key, counter


def get_cache_size(
        obj,
        *,
        cache_info: str = '',
        seen_ids: set[int] | None = None,
        class_slots: dict[type, Iterable[str]] | None = None
    ) -> int:
    """ A non-thread-safe recursive object size estimator """
    from odoo.models import BaseModel  # noqa: PLC0415
    from odoo.api import Environment  # noqa: PLC0415

    if seen_ids is None:
        seen_ids = set()
    if class_slots is None:
        class_slots = {}  # {class_name: combined_slots}
    total_size = 0
    objects = [obj]

    while objects:
        cur_obj = objects.pop()
        if id(cur_obj) in seen_ids:
            continue

        if cache_info and isinstance(cur_obj, (BaseModel, Environment)):
            _logger.error('%s is cached by %s', cur_obj, cache_info)
            continue

        seen_ids.add(id(cur_obj))
        total_size += sys.getsizeof(cur_obj)

        if hasattr(cur_obj, '__slots__'):
            cur_obj_cls = type(cur_obj)
            if cur_obj_cls not in class_slots:
                class_slots[cur_obj_cls] = tuple(set(chain.from_iterable(
                    getattr(cls, '__slots__', ())
                    for cls in cur_obj_cls.mro()
                )))
            objects.extend(getattr(cur_obj, s) for s in class_slots[cur_obj_cls] if hasattr(cur_obj, s))
        if hasattr(cur_obj, '__dict__'):
            objects.append(object.__dict__)

        if isinstance(cur_obj, Mapping):
            objects.extend(cur_obj.values())
            objects.extend(cur_obj.keys())
        elif isinstance(cur_obj, Collection) and not isinstance(cur_obj, (str, bytes, bytearray)):
            objects.extend(cur_obj)

    return total_size
