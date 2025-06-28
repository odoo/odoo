# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# decorator makes wrappers that have the same API as their wrapped function
from collections import Counter, defaultdict
from decorator import decorator
from inspect import signature, Parameter
import logging
import warnings

unsafe_eval = eval

_logger = logging.getLogger(__name__)


class ormcache_counter(object):
    """ Statistic counters for cache entries. """
    __slots__ = ['hit', 'miss', 'err']

    def __init__(self):
        self.hit = 0
        self.miss = 0
        self.err = 0

    @property
    def ratio(self):
        return 100.0 * self.hit / (self.hit + self.miss or 1)

# statistic counters dictionary, maps (dbname, modelname, method) to counter
STAT = defaultdict(ormcache_counter)


class ormcache(object):
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
    def __init__(self, *args, **kwargs):
        self.args = args
        self.skiparg = kwargs.get('skiparg')
        self.cache_name = kwargs.get('cache', 'default')

    def __call__(self, method):
        self.method = method
        self.determine_key()
        lookup = decorator(self.lookup, method)
        lookup.__cache__ = self
        return lookup

    def add_value(self, *args, cache_value=None, **kwargs):
        model = args[0]
        d, key0, _ = self.lru(model)
        key = key0 + self.key(*args, **kwargs)
        d[key] = cache_value

    def determine_key(self):
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

    def lru(self, model):
        counter = STAT[(model.pool.db_name, model._name, self.method)]
        return model.pool._Registry__caches[self.cache_name], (model._name, self.method), counter

    def lookup(self, method, *args, **kwargs):
        d, key0, counter = self.lru(args[0])
        key = key0 + self.key(*args, **kwargs)
        try:
            r = d[key]
            counter.hit += 1
            return r
        except KeyError:
            counter.miss += 1
            value = d[key] = self.method(*args, **kwargs)
            return value
        except TypeError:
            _logger.warning("cache lookup error on %r", key, exc_info=True)
            counter.err += 1
            return self.method(*args, **kwargs)

    def clear(self, model, *args):
        """ Clear the registry cache """
        warnings.warn('Deprecated method ormcache.clear(model, *args), use registry.clear_cache() instead')
        model.pool.clear_all_caches()


class ormcache_context(ormcache):
    """ This LRU cache decorator is a variant of :class:`ormcache`, with an
    extra parameter ``keys`` that defines a sequence of dictionary keys. Those
    keys are looked up in the ``context`` parameter and combined to the cache
    key made by :class:`ormcache`.
    """
    def __init__(self, *args, **kwargs):
        super(ormcache_context, self).__init__(*args, **kwargs)
        self.keys = kwargs['keys']

    def determine_key(self):
        """ Determine the function that computes a cache key from arguments. """
        assert self.skiparg is None, "ormcache_context() no longer supports skiparg"
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


def log_ormcache_stats(sig=None, frame=None):
    """ Log statistics of ormcache usage by database, model, and method. """
    from odoo.modules.registry import Registry
    import threading

    me = threading.current_thread()
    me_dbname = getattr(me, 'dbname', 'n/a')

    def _log_ormcache_stats(cache_name, cache):
        entries = Counter(k[:2] for k in cache.d)
        # show entries sorted by model name, method name
        for key in sorted(entries, key=lambda key: (key[0], key[1].__name__)):
            model, method = key
            stat = STAT[(dbname, model, method)]
            _logger.info(
                "%s, %6d entries, %6d hit, %6d miss, %6d err, %4.1f%% ratio, for %s.%s",
                cache_name.rjust(25), entries[key], stat.hit, stat.miss, stat.err, stat.ratio, model, method.__name__,
            )

    for dbname, reg in sorted(Registry.registries.d.items()):
        # set logger prefix to dbname
        me.dbname = dbname
        for cache_name, cache in reg._Registry__caches.items():
            _log_ormcache_stats(cache_name, cache)

    me.dbname = me_dbname


def get_cache_key_counter(bound_method, *args, **kwargs):
    """ Return the cache, key and stat counter for the given call. """
    model = bound_method.__self__
    ormcache = bound_method.__cache__
    cache, key0, counter = ormcache.lru(model)
    key = key0 + ormcache.key(model, *args, **kwargs)
    return cache, key, counter

# For backward compatibility
cache = ormcache
