# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 OpenERP (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

# decorator makes wrappers that have the same API as their wrapped function;
# this is important for the openerp.api.guess() that relies on signatures
from collections import defaultdict
from decorator import decorator
from inspect import formatargspec, getargspec
import logging

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
        def _compute_domain(self, cr, uid, model_name, mode="read"):
            ...

    For the sake of backward compatibility, the decorator supports the named
    parameter `skiparg`::

        @ormcache(skiparg=3)
        def _compute_domain(self, cr, uid, model_name, mode="read"):
            ...
    """
    def __init__(self, *args, **kwargs):
        self.args = args
        self.skiparg = kwargs.get('skiparg')

    def __call__(self, method):
        self.method = method
        self.determine_key()
        lookup = decorator(self.lookup, method)
        lookup.clear_cache = self.clear
        return lookup

    def determine_key(self):
        """ Determine the function that computes a cache key from arguments. """
        if self.skiparg is None:
            # build a string that represents function code and evaluate it
            args = formatargspec(*getargspec(self.method))[1:-1]
            if self.args:
                code = "lambda %s: (%s,)" % (args, ", ".join(self.args))
            else:
                code = "lambda %s: ()" % (args,)
            self.key = eval(code)
        else:
            # backward-compatible function that uses self.skiparg
            self.key = lambda *args, **kwargs: args[self.skiparg:]

    def lru(self, model):
        counter = STAT[(model.pool.db_name, model._name, self.method)]
        return model.pool.cache, (model._name, self.method), counter

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
            counter.err += 1
            return self.method(*args, **kwargs)

    def clear(self, model, *args):
        """ Remove *args entry from the cache or all keys if *args is undefined """
        d, key0, _ = self.lru(model)
        if args:
            _logger.warn("ormcache.clear arguments are deprecated and ignored "
                         "(while clearing caches on (%s).%s)",
                         model._name, self.method.__name__)
        d.clear_prefix(key0)
        model.pool._any_cache_cleared = True


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
        spec = getargspec(self.method)
        args = formatargspec(*spec)[1:-1]
        cont_expr = "(context or {})" if 'context' in spec.args else "self._context"
        keys_expr = "tuple(map(%s.get, %r))" % (cont_expr, self.keys)
        if self.args:
            code = "lambda %s: (%s, %s)" % (args, ", ".join(self.args), keys_expr)
        else:
            code = "lambda %s: (%s,)" % (args, keys_expr)
        self.key = eval(code)


class ormcache_multi(ormcache):
    """ This LRU cache decorator is a variant of :class:`ormcache`, with an
    extra parameter ``multi`` that gives the name of a parameter. Upon call, the
    corresponding argument is iterated on, and every value leads to a cache
    entry under its own key.
    """
    def __init__(self, *args, **kwargs):
        super(ormcache_multi, self).__init__(*args, **kwargs)
        self.multi = kwargs['multi']

    def determine_key(self):
        """ Determine the function that computes a cache key from arguments. """
        assert self.skiparg is None, "ormcache_multi() no longer supports skiparg"
        assert isinstance(self.multi, basestring), "ormcache_multi() parameter multi must be an argument name"

        super(ormcache_multi, self).determine_key()

        # key_multi computes the extra element added to the key
        spec = getargspec(self.method)
        args = formatargspec(*spec)[1:-1]
        code_multi = "lambda %s: %s" % (args, self.multi)
        self.key_multi = eval(code_multi)

        # self.multi_pos is the position of self.multi in args
        self.multi_pos = spec.args.index(self.multi)

    def lookup(self, method, *args, **kwargs):
        d, key0, counter = self.lru(args[0])
        base_key = key0 + self.key(*args, **kwargs)
        ids = self.key_multi(*args, **kwargs)
        result = {}
        missed = []

        # first take what is available in the cache
        for i in ids:
            key = base_key + (i,)
            try:
                result[i] = d[key]
                counter.hit += 1
            except Exception:
                counter.miss += 1
                missed.append(i)

        if missed:
            # call the method for the ids that were not in the cache; note that
            # thanks to decorator(), the multi argument will be bound and passed
            # positionally in args.
            args = list(args)
            args[self.multi_pos] = missed
            result.update(method(*args, **kwargs))

            # store those new results back in the cache
            for i in missed:
                key = base_key + (i,)
                d[key] = result[i]

        return result


class dummy_cache(object):
    """ Cache decorator replacement to actually do no caching. """
    def __init__(self, *l, **kw):
        pass

    def __call__(self, fn):
        fn.clear_cache = self.clear
        return fn

    def clear(self, *l, **kw):
        pass


def log_ormcache_stats(sig=None, frame=None):
    """ Log statistics of ormcache usage by database, model, and method. """
    from openerp.modules.registry import RegistryManager
    import threading

    me = threading.currentThread()
    me_dbname = me.dbname
    entries = defaultdict(int)
    for dbname, reg in RegistryManager.registries.iteritems():
        for key in reg.cache.iterkeys():
            entries[(dbname,) + key[:2]] += 1
    for key, count in sorted(entries.items()):
        dbname, model_name, method = key
        me.dbname = dbname
        stat = STAT[key]
        _logger.info("%6d entries, %6d hit, %6d miss, %6d err, %4.1f%% ratio, for %s.%s",
                     count, stat.hit, stat.miss, stat.err, stat.ratio, model_name, method.__name__)

    me.dbname = me_dbname


def get_cache_key_counter(bound_method, *args, **kwargs):
    """ Return the cache, key and stat counter for the given call. """
    model = bound_method.im_self
    ormcache = bound_method.clear_cache.im_self
    cache, key0, counter = ormcache.lru(model)
    key = key0 + ormcache.key(model, *args, **kwargs)
    return cache, key, counter

# For backward compatibility
cache = ormcache
