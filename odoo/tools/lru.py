# -*- coding: utf-8 -*-
import collections
import threading

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

    def __contains__(self, obj):
        with self._lock:
            return obj in self.d

    def get(self, obj, val=None):
        try:
            return self[obj]
        except KeyError:
            return val

    def __getitem__(self, obj):
        with self._lock:
            a = self.d[obj]
            self.d.move_to_end(obj, last=False)
            return a

    def __setitem__(self, obj, val):
        with self._lock:
            self.d[obj] = val
            self.d.move_to_end(obj, last=False)
            while len(self.d) > self.count:
                self.d.popitem(last=True)

    def __delitem__(self, obj):
        with self._lock:
            del self.d[obj]

    def __len__(self):
        with self._lock:
            return len(self.d)

    def pop(self,key):
        with self._lock:
            return self.d.pop(key)

    def clear(self):
        with self._lock:
            self.d.clear()
