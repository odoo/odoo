# -*- coding: utf-8 -*-
import collections
import logging
import threading

from .func import locked

__all__ = ['LRU']

logger = logging.getLogger(__name__)


class LRU(object):
    """
    Implementation of a length-limited O(1) LRU map.

    Original Copyright 2003 Josiah Carlson, later rebuilt on OrderedDict.
    """
    def __init__(self, count, pairs=(), tag=None):
        self._lock = threading.RLock()
        self.count = max(count, 1)
        self.d = collections.OrderedDict()
        self.logger = logger.getChild(tag) if tag else logger
        self.logger.debug("INIT")

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
        self.logger.debug("ACCESS %s", obj)
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
        self.logger.debug("CLEAR")
        self.d.clear()
