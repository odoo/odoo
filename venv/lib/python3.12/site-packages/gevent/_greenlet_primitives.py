# -*- coding: utf-8 -*-
# copyright (c) 2018 gevent. See  LICENSE.
# cython: auto_pickle=False,embedsignature=True,always_allow_keywords=False
"""
A collection of primitives used by the hub, and suitable for
compilation with Cython because of their frequency of use.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from weakref import ref as wref
from gc import get_objects

from greenlet import greenlet

from gevent.exceptions import BlockingSwitchOutError


# In Cython, we define these as 'cdef inline' functions. The
# compilation unit cannot have a direct assignment to them (import
# is assignment) without generating a 'lvalue is not valid target'
# error.
locals()['getcurrent'] = __import__('greenlet').getcurrent
locals()['greenlet_init'] = lambda: None
locals()['_greenlet_switch'] = greenlet.switch


__all__ = [
    'TrackedRawGreenlet',
    'SwitchOutGreenletWithLoop',
]

class TrackedRawGreenlet(greenlet):

    def __init__(self, function, parent):
        greenlet.__init__(self, function, parent)
        # See greenlet.py's Greenlet class. We capture the cheap
        # parts to maintain the tree structure, but we do not capture
        # the stack because that's too expensive for 'spawn_raw'.

        current = getcurrent() # pylint:disable=undefined-variable
        self.spawning_greenlet = wref(current)
        # See Greenlet for how trees are maintained.
        try:
            self.spawn_tree_locals = current.spawn_tree_locals
        except AttributeError:
            self.spawn_tree_locals = {}
            if current.parent:
                current.spawn_tree_locals = self.spawn_tree_locals


class SwitchOutGreenletWithLoop(TrackedRawGreenlet):
    # Subclasses must define:
    # - self.loop

    # This class defines loop in its .pxd for Cython. This lets us avoid
    # circular dependencies with the hub.

    def switch(self):
        switch_out = getattr(getcurrent(), 'switch_out', None) # pylint:disable=undefined-variable
        if switch_out is not None:
            switch_out()
        return _greenlet_switch(self) # pylint:disable=undefined-variable

    def switch_out(self):
        raise BlockingSwitchOutError('Impossible to call blocking function in the event loop callback')


def get_reachable_greenlets():
    # We compile this loop with Cython so that it's faster, and so that
    # the GIL isn't dropped at unpredictable times during the loop.
    # Dropping the GIL could lead to accessing partly constructed objects
    # in undefined states (particularly, tuples). This helps close a hole
    # where a `SystemError: Objects/tupleobject.c bad argument to internal function`
    # could get raised. (Note that this probably doesn't completely close the hole,
    # if other threads have dropped the GIL, but hopefully the speed makes that
    # more rare.) See https://github.com/gevent/gevent/issues/1302
    return [
        x for x in get_objects()
        if isinstance(x, greenlet) and not getattr(x, 'greenlet_tree_is_ignored', False)
    ]

# Cache the global memoryview so cython can optimize.
_memoryview = memoryview
try:
    if isinstance(__builtins__, dict):
        # Pure-python mode on CPython
        _buffer = __builtins__['buffer']
    else:
        # Cythonized mode, or PyPy
        _buffer = __builtins__.buffer
except (AttributeError, KeyError):
    # Python 3.
    _buffer = memoryview

def get_memory(data):
    # On Python 2, memoryview(memoryview()) can leak in some cases,
    # notably when an io.BufferedWriter object produced the memoryview.
    # So we need to check to see if we already have one before we convert.
    # We do this in Cython to mitigate the performance cost (which turns out to be a
    # net win.)

    # We don't specifically test for this leak.

    # https://github.com/gevent/gevent/issues/1318
    try:
        mv = _memoryview(data) if not isinstance(data, _memoryview) else data
        if mv.shape:
            return mv
        # No shape, probably working with a ctypes object,
        # or something else exotic that supports the buffer interface
        return mv.tobytes()
    except TypeError:
        # fixes "python2.7 array.array doesn't support memoryview used in
        # gevent.socket.send" issue
        # (http://code.google.com/p/gevent/issues/detail?id=94)
        if _buffer is _memoryview:
            # Py3
            raise
        return _buffer(data)



def _init():
    greenlet_init() # pylint:disable=undefined-variable

_init()

from gevent._util import import_c_accel
import_c_accel(globals(), 'gevent.__greenlet_primitives')
