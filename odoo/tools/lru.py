# -*- coding: utf-8 -*-
import collections
import sys
import threading

from collections.abc import Mapping
from .func import locked

__all__ = ['LRU']

class LRU:
    """
    Implementation of a length-limited O(1) LRU map.

    Original Copyright 2003 Josiah Carlson, later rebuilt on OrderedDict.
    """
    def __init__(self, size, mode='count', pairs=()):
        self.mode = mode
        self.current_size = 0
        self.maximum_size = max(size, 0)
        self._lock = threading.RLock()
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
        a = self.d[obj][0]
        self.d.move_to_end(obj, last=False)
        return a

    @locked
    def __setitem__(self, obj, val):
        size = get_memory_footprint(obj, val) if self.mode == 'footprint' else 1
        self.d[obj] = (val, size)
        self.d.move_to_end(obj, last=False)
        self.current_size += size
        while self.current_size > self.maximum_size:
            self.current_size -= self.d.popitem(last=True)[1][1]

    @locked
    def __delitem__(self, obj):
        self.pop(obj)

    @locked
    def __len__(self):
        return len(self.d)

    @locked
    def pop(self, key):
        value, size = self.d.pop(key)
        self.current_size += size
        return value

    @locked
    def clear(self):
        self.d.clear()
        self.current_size = 0


def get_memory_footprint(*args):
    seen_ids = set()
    total_size = 0
    objects = collections.deque(args)

    while objects:
        cur_obj = objects.popleft()
        if id(cur_obj) in seen_ids or callable(cur_obj):
            continue

        seen_ids.add(id(cur_obj))
        total_size += sys.getsizeof(cur_obj)
        if hasattr(cur_obj, '__dict__'):
            objects.append(cur_obj.__dict__.values())
            objects.append(cur_obj.__dict__.keys())
        if isinstance(cur_obj, Mapping):
            objects.extend(cur_obj.values())
        if hasattr(cur_obj, '__iter__') and not isinstance(cur_obj, (str, bytes, bytearray)):
            try:
                objects.extend(cur_obj)
            except TypeError:
                pass
        if hasattr(cur_obj, '__slot__'):
            objects.extend(getattr(cur_obj, s) for s in cur_obj.__slots__ if hasattr(cur_obj, s))

    return total_size
