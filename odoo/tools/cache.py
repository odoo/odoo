# Part of Odoo. See LICENSE file for full copyright and licensing details.
# decorator makes wrappers that have the same API as their wrapped function
from __future__ import annotations

from collections import Counter, defaultdict
from decorator import decorator
from inspect import signature, Parameter
import logging
import time
import typing
import warnings

if typing.TYPE_CHECKING:
    from collections.abc import Callable
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

    def lru(self, model: BaseModel) -> tuple[typing.Any, tuple, ormcache_counter]:
        model_name = model._name or ''
        counter = STAT[model.pool.db_name, model_name, self.method]
        cache = model.pool._Registry__caches[self.cache_name]  # type: ignore
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
            start = time.time()
            value = d[key] = self.method(*args, **kwargs)
            counter.gen_time += time.time() - start
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


def log_ormcache_stats(sig=None, frame=None):   # noqa: ARG001 (arguments are there for signals)
    """ Log statistics of ormcache usage by database, model, and method. """
    from odoo.modules.registry import Registry
    cache_entries = {}
    current_db = None
    cache_stats = ['Caches stats:']
    for (dbname, model, method), stat in sorted(STAT.items(), key=lambda k: (k[0][0] or '~', k[0][1], k[0][2].__name__)):
        dbname_display = dbname or "<no_db>"
        if current_db != dbname_display:
            current_db = dbname_display
            cache_stats.append(f"Database {dbname_display}")
        if dbname:   # mainly for MockPool
            if (dbname, stat.cache_name) not in cache_entries:
                cache = Registry.registries.d[dbname]._Registry__caches[stat.cache_name]
                cache_entries[dbname, stat.cache_name] = Counter(k[:2] for k in cache.d)
            nb_entries = cache_entries[dbname, stat.cache_name][model, method]
        else:
            nb_entries = 0
        cache_name = stat.cache_name.rjust(25)
        cache_stats.append(
            f"{cache_name}, {nb_entries:6d} entries, {stat.hit:6d} hit, {stat.miss:6d} miss, {stat.err:6d} err, {stat.gen_time:10.3f}s time, {stat.ratio:6.1f}% ratio for {model}.{method.__name__}"
        )
    _logger.info('\n'.join(cache_stats))


def get_cache_key_counter(bound_method: Callable, *args, **kwargs):
    """ Return the cache, key and stat counter for the given call. """
    model: BaseModel = bound_method.__self__  # type: ignore
    ormcache_instance: ormcache = bound_method.__cache__  # type: ignore
    cache, key0, counter = ormcache_instance.lru(model)
    key = key0 + ormcache_instance.key(model, *args, **kwargs)
    return cache, key, counter
