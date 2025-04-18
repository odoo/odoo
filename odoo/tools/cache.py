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


STAT: defaultdict[tuple[str, str, Callable], ormcache_counter] = defaultdict(ormcache_counter)
"""statistic counters dictionary, maps (dbname, modelname, method) to counter"""


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
        model = args[0]
        d, key0, counter = self.lru(model)
        counter.cache_name = self.cache_name
        key = key0 + self.key(*args, **kwargs)
        d[key] = cache_value

    def determine_key(self) -> None:
        """ Determine the function that computes a cache key from arguments. """
        if self.skiparg is None:
            # build a string that represents function code and evaluate it
            args = ', '.join(
                # remove annotations because lambdas can't be type-annotated,
                # and defaults because they are redundant (defaults are present
                # in the wrapper function itself)
                str(params.replace(annotation=Parameter.empty, default=Parameter.empty))
                for params in signature(self.method).parameters.values()
            )
            if self.args:
                code = "lambda %s: (%s,)" % (args, ", ".join(self.args))
            else:
                code = "lambda %s: ()" % (args,)
            self.key = unsafe_eval(code)
        else:
            # backward-compatible function that uses self.skiparg
            self.key = lambda *args, **kwargs: args[self.skiparg:]

    def lru(self, model: BaseModel) -> tuple[LRU, tuple, ormcache_counter]:
        model_name = model._name or ''
        counter = STAT[model.pool.db_name, model_name, self.method]
        cache: LRU = model.pool._Registry__caches[self.cache_name]  # type: ignore
        return cache, (model_name, self.method), counter

    def lookup(self, method, *args, **kwargs):
        d, key0, counter = self.lru(args[0])
        key = key0 + self.key(*args, **kwargs)
        try:
            r = d[key]
            counter.hit += 1
            return r
        except KeyError:
            counter.miss += 1
            counter.cache_name = self.cache_name
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
        super().__init__(*args, **kwargs)
        self.keys = keys

    def determine_key(self) -> None:
        """ Determine the function that computes a cache key from arguments. """
        # build a string that represents function code and evaluate it
        sign = signature(self.method)
        args = ', '.join(
            str(params.replace(annotation=Parameter.empty, default=Parameter.empty))
            for params in sign.parameters.values()
        )
        cont_expr = "(context or {})" if 'context' in sign.parameters else "self._context"
        keys_expr = "tuple(%s.get(k) for k in %r)" % (cont_expr, self.keys)
        if self.args:
            code = "lambda %s: (%s, %s)" % (args, ", ".join(self.args), keys_expr)
        else:
            code = "lambda %s: (%s,)" % (args, keys_expr)
        self.key = unsafe_eval(code)


class OrmCacheStatsLogger:
    loggings = set()
    stop_time = 0.0

    def __init__(self, start_time):
        self.start_time = start_time

    def check_continue_logging(self):
        if self.start_time > self.stop_time:
            return True
        _logger.info('Stopping logging ORM cache stats')
        return False

    def log_ormcache_stats(self, size=False):
        """ Log statistics of ormcache usage by database, model, and method. """
        from odoo.modules.registry import Registry  # noqa: PLC0415
        try:
            self.loggings.add(self)
            log_msgs = ['Caches stats:']
            # {dbname: sz_entries_all}
            db_size = defaultdict(lambda: 0)
            # {dbname: {(model, method): [sz_entries_sum, sz_entries_max, nb_entries, stat]}}
            cache_stats = defaultdict(lambda: defaultdict(lambda: [0, 0, 0, None]))

            size_column_info = (
                f"{'Memory SUM [Bytes]':>20},"
                f"{'Memory MAX [Bytes]':>20},"
            ) if size else ''
            column_info = (
                f"{'Cache Name':>25},"
                f"{'Entry':>7},"
                f"{size_column_info}"
                f"{'Hit':>6},"
                f"{'Miss':>6},"
                f"{'Err':>6},"
                f"{'Gen Time [s]':>14},"
                f"{'Hit Ratio':>11},"
                f"{'Model.Method':>15}"
            )

            if size:
                registries = Registry.registries.snapshot
                for i, (dbname, registry) in enumerate(registries.items(), start=1):
                    if not self.check_continue_logging():
                        return
                    _logger.info("Processing database %s (%d/%d)", dbname, i, len(registries))
                    db_cache_stats = cache_stats[dbname]
                    sz_entries_all = 0
                    for cache in registry._Registry__caches.values():
                        for cache_key, cache_value in cache.snapshot.items():
                            model_name, method = cache_key[:2]
                            stats = db_cache_stats[model_name, method]
                            cache_info = f'{model_name}.{method.__name__}'
                            size = get_cache_size(cache_value, cache_info=cache_info)
                            sz_entries_all += size
                            stats[0] += size  # sz_entries_sum
                            stats[1] = max(stats[1], size)  # sz_entries_max
                            stats[2] += 1  # nb_entries
                    db_size[dbname] = sz_entries_all

            for (dbname, model_name, method), stat in STAT.copy().items():  # copy to avoid concurrent modification
                if not self.check_continue_logging():
                    return
                cache_stats[dbname][model_name, method][3] = stat

            for dbname, db_cache_stats in sorted(cache_stats.items(), key=lambda k: k[0] or '~'):
                if not self.check_continue_logging():
                    return
                sz_entries_all = db_size[dbname]
                log_msgs.append(f'Database {dbname or "<no_db>"}:')
                log_msgs.append(column_info)

                # sort by -sz_entries_sum, model and method_name
                db_cache_stat = sorted(db_cache_stats.items(), key=lambda k: (-k[1][0], k[0][0], k[0][1].__name__))
                for (model_name, method), (sz_entries_sum, sz_entries_max, nb_entries, stat) in db_cache_stat:
                    size_data = (
                        f'{sz_entries_sum:11d} ({sz_entries_sum / (sz_entries_all or 1) * 100:5.1f}%),'
                        f'{sz_entries_max:20d},'
                    ) if size else ''
                    log_msgs.append(
                        f'{stat.cache_name:>25},'
                        f'{nb_entries:7d},'
                        f'{size_data}'
                        f'{stat.hit:6d},'
                        f'{stat.miss:6d},'
                        f'{stat.err:6d},'
                        f'{stat.gen_time:14.3f},'
                        f'{stat.ratio:10.1f}%,'
                        f'   {model_name}.{method.__name__}'
                    )
            _logger.info('\n'.join(log_msgs))
        except Exception as e:  # noqa: BLE001
            _logger.error(e)
        finally:
            self.loggings.remove(self)


def log_ormcache_stats(sig=None, frame=None):    # noqa: ARG001 (arguments are there for signals)
    # collect and log data in a separate thread to avoid blocking the main thread
    # and avoid using logging module directly in the signal handler
    # https://docs.python.org/3/library/logging.html#thread-safety
    cur_time = time.monotonic()
    if OrmCacheStatsLogger.loggings:
        # send the signal again to stop the logging thread
        OrmCacheStatsLogger.stop_time = cur_time
        return
    if sig == signal.SIGUSR1:
        threading.Thread(target=OrmCacheStatsLogger(cur_time).log_ormcache_stats,
                         name="odoo.signal.log_ormcache_stats").start()
    elif sig == signal.SIGUSR2:
        threading.Thread(target=OrmCacheStatsLogger(cur_time).log_ormcache_stats, args=(True,),
                         name="odoo.signal.log_ormcache_stats_with_size").start()


def get_cache_key_counter(bound_method: Callable, *args, **kwargs):
    """ Return the cache, key and stat counter for the given call. """
    model: BaseModel = bound_method.__self__  # type: ignore
    ormcache_instance: ormcache = bound_method.__cache__  # type: ignore
    cache, key0, counter = ormcache_instance.lru(model)
    key = key0 + ormcache_instance.key(model, *args, **kwargs)
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
