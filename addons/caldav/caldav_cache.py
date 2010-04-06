# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import time
import heapq

def memoize(maxsize):
    """decorator to 'memoize' a function - caching its results"""
    def decorating_function(f):
        cache = {}  # map from key to value
        heap = []   # list of keys, in LRU heap
        cursize = 0 # because len() is slow
        def wrapper(*args):
            key = repr(args)
            # performance crap
            _cache = cache
            _heap = heap
            _heappop = heapq.heappop
            _heappush = heapq.heappush
            _time = time.time
            _cursize = cursize
            _maxsize = maxsize
            if not _cache.has_key(key):
                if _cursize == _maxsize:
                    # pop oldest element
                    (_, oldkey) = _heappop(_heap)
                    _cache.pop(oldkey)
                else:
                    _cursize += 1
                # insert this element
                _cache[key] = f(*args)
                _heappush(_heap, (_time(), key))
                wrapper.misses += 1
            else:
                wrapper.hits += 1
            return cache[key]
        wrapper.__doc__ = f.__doc__
        wrapper.__name__ = f.__name__
        wrapper.hits = wrapper.misses = 0
        return wrapper
    return decorating_function


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: