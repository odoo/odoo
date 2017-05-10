# -*- coding: utf-8 -*-
# taken from http://code.activestate.com/recipes/252524-length-limited-o1-lru-cache-implementation/
import threading

from odoo.tools import pycompat
from .func import synchronized

__all__ = ['LRU']

class LRUNode(object):
    __slots__ = ['prev', 'next', 'me']
    def __init__(self, prev, me):
        self.prev = prev
        self.me = me
        self.next = None

class LRU(object):
    """
    Implementation of a length-limited O(1) LRU queue.
    Built for and used by PyPE:
    http://pype.sourceforge.net
    Copyright 2003 Josiah Carlson.
    """
    def __init__(self, count, pairs=[]):
        self._lock = threading.RLock()
        self.count = max(count, 1)
        self.d = {}
        self.first = None
        self.last = None
        for key, value in pairs:
            self[key] = value

    @synchronized()
    def __contains__(self, obj):
        return obj in self.d

    def get(self, obj, val=None):
        try:
            return self[obj]
        except KeyError:
            return val

    @synchronized()
    def __getitem__(self, obj):
        a = self.d[obj].me
        self[a[0]] = a[1]
        return a[1]

    @synchronized()
    def __setitem__(self, obj, val):
        if obj in self.d:
            del self[obj]
        nobj = LRUNode(self.last, (obj, val))
        if self.first is None:
            self.first = nobj
        if self.last:
            self.last.next = nobj
        self.last = nobj
        self.d[obj] = nobj
        if len(self.d) > self.count:
            if self.first == self.last:
                self.first = None
                self.last = None
                return
            a = self.first
            a.next.prev = None
            self.first = a.next
            a.next = None
            del self.d[a.me[0]]
            del a

    @synchronized()
    def __delitem__(self, obj):
        nobj = self.d[obj]
        if nobj.prev:
            nobj.prev.next = nobj.next
        else:
            self.first = nobj.next
        if nobj.next:
            nobj.next.prev = nobj.prev
        else:
            self.last = nobj.prev
        del self.d[obj]

    @synchronized()
    def __iter__(self):
        cur = self.first
        while cur is not None:
            cur2 = cur.next
            yield cur.me[1]
            cur = cur2

    @synchronized()
    def __len__(self):
        return len(self.d)

    # FIXME: should this have a P2 and a P3 version or something?
    @synchronized()
    def iteritems(self):
        cur = self.first
        while cur is not None:
            cur2 = cur.next
            yield cur.me
            cur = cur2

    @synchronized()
    def iterkeys(self):
        return iter(self.d)

    @synchronized()
    def itervalues(self):
        for i,j in pycompat.items(self):
            yield j

    @synchronized()
    def keys(self):
        return list(pycompat.keys(self.d))

    @synchronized()
    def pop(self,key):
        v=self[key]
        del self[key]
        return v

    @synchronized()
    def clear(self):
        self.d = {}
        self.first = None
        self.last = None
