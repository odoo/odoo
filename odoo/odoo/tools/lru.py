# -*- coding: utf-8 -*-
import collections
import threading

from .func import locked

__all__ = ['LRU']

class LRU(object):
    """
    Implementation of a length-limited O(1) LRU map.

    Original Copyright 2003 Josiah Carlson, later rebuilt on OrderedDict.
    """
    def __init__(self, count, pairs=()):
        self._lock = threading.RLock()
        self.count = max(count, 1)
        self.d = collections.OrderedDict()
        for key, value in pairs:
            self[key] = value

    @locked
    def __contains__(self, obj):
        return obj in self.d

    def get(self, obj, val=None):
        try:
            return self[obj]
        except KeyError:
            return val

    @locked
    def __getitem__(self, obj):
        a = self.d[obj]
        self.d.move_to_end(obj, last=False)
        return a

    @locked
    def __setitem__(self, obj, val):
        self.d[obj] = val
        self.d.move_to_end(obj, last=False)
        while len(self.d) > self.count:
            self.d.popitem(last=True)

    @locked
    def __delitem__(self, obj):
        del self.d[obj]

    @locked
    def __len__(self):
        return len(self.d)

    @locked
    def pop(self,key):
        return self.d.pop(key)

    @locked
    def clear(self):
        self.d.clear()
