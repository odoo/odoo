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
from decorator import decorator
from inspect import getargspec

import lru
import logging

logger = logging.getLogger(__name__)


class ormcache(object):
    """ LRU cache decorator for orm methods. """

    def __init__(self, skiparg=2, size=8192, multi=None, timeout=None):
        self.skiparg = skiparg
        self.size = size
        self.stat_miss = 0
        self.stat_hit = 0
        self.stat_err = 0

    def __call__(self, method):
        self.method = method
        lookup = decorator(self.lookup, method)
        lookup.clear_cache = self.clear
        return lookup

    def stat(self):
        return "lookup-stats hit=%s miss=%s err=%s ratio=%.1f" % \
            (self.stat_hit, self.stat_miss, self.stat_err,
                (100*float(self.stat_hit))/(self.stat_miss+self.stat_hit))

    def lru(self, model):
        ormcache = model._ormcache
        try:
            d = ormcache[self.method]
        except KeyError:
            d = ormcache[self.method] = lru.LRU(self.size)
        return d

    def lookup(self, method, *args, **kwargs):
        d = self.lru(args[0])
        key = args[self.skiparg:]
        try:
            r = d[key]
            self.stat_hit += 1
            return r
        except KeyError:
            self.stat_miss += 1
            value = d[key] = self.method(*args, **kwargs)
            return value
        except TypeError:
            self.stat_err += 1
            return self.method(*args, **kwargs)

    def clear(self, model, *args):
        """ Remove *args entry from the cache or all keys if *args is undefined """
        d = self.lru(model)
        if args:
            logger.warn("ormcache.clear arguments are deprecated and ignored "
                        "(while clearing caches on (%s).%s)",
                        model._name, self.method.__name__)
        d.clear()
        model.pool._any_cache_cleared = True


class ormcache_context(ormcache):
    def __init__(self, skiparg=2, size=8192, accepted_keys=()):
        super(ormcache_context,self).__init__(skiparg,size)
        self.accepted_keys = accepted_keys

    def __call__(self, method):
        # remember which argument is context
        args = getargspec(method)[0]
        self.context_pos = args.index('context')
        return super(ormcache_context, self).__call__(method)

    def lookup(self, method, *args, **kwargs):
        d = self.lru(args[0])

        # Note. The decorator() wrapper (used in __call__ above) will resolve
        # arguments, and pass them positionally to lookup(). This is why context
        # is not passed through kwargs!
        if self.context_pos < len(args):
            context = args[self.context_pos]
        else:
            context = kwargs.get('context') or {}
        ckey = [(k, context[k]) for k in self.accepted_keys if k in context]

        # Beware: do not take the context from args!
        key = args[self.skiparg:self.context_pos] + tuple(ckey)
        try:
            r = d[key]
            self.stat_hit += 1
            return r
        except KeyError:
            self.stat_miss += 1
            value = d[key] = self.method(*args, **kwargs)
            return value
        except TypeError:
            self.stat_err += 1
            return self.method(*args, **kwargs)


class ormcache_multi(ormcache):
    def __init__(self, skiparg=2, size=8192, multi=3):
        assert skiparg <= multi
        super(ormcache_multi, self).__init__(skiparg, size)
        self.multi = multi

    def lookup(self, method, *args, **kwargs):
        d = self.lru(args[0])
        base_key = args[self.skiparg:self.multi] + args[self.multi+1:]
        ids = args[self.multi]
        result = {}
        missed = []

        # first take what is available in the cache
        for i in ids:
            key = base_key + (i,)
            try:
                result[i] = d[key]
                self.stat_hit += 1
            except Exception:
                self.stat_miss += 1
                missed.append(i)

        if missed:
            # call the method for the ids that were not in the cache
            args = list(args)
            args[self.multi] = missed
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


# For backward compatibility
cache = ormcache

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
