# -*- coding: utf-8 -*-
# copyright 2018 gevent. See LICENSE
"""
Maintains the thread local hub.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


import _thread

__all__ = [
    'get_hub',
    'get_hub_noargs',
    'get_hub_if_exists',
]

# These must be the "real" native thread versions,
# not monkey-patched.
# We are imported early enough (by gevent/__init__) that
# we can rely on not being monkey-patched in any way yet.
assert 'gevent' not in str(_thread._local)
class _Threadlocal(_thread._local):

    def __init__(self):
        # Use a class with an initializer so that we can test
        # for 'is None' instead of catching AttributeError, making
        # the code cleaner and possibly solving some corner cases
        # (like #687).
        #
        # However, under some weird circumstances, it _seems_ like the
        # __init__ method doesn't get called properly ("seems" is the
        # keyword). We've seen at least one instance
        # (https://github.com/gevent/gevent/issues/1961) of
        # ``AttributeError: '_Threadlocal' object has no attribute # 'hub'``
        # which should be impossible unless:
        #
        # - Someone manually deletes the attribute
        # - The _threadlocal object itself is in the process of being
        #   deleted. The C ``tp_clear`` slot for it deletes the ``__dict__``
        #   of each instance in each thread (and/or the ``tp_clear`` of ``dict`` itself
        #   clears the instance). Now, how we could be getting
        #   cleared while still being used is unclear, but clearing is part of
        #   circular garbage collection, and in the bug report it looks like we're inside a
        #   weakref finalizer or ``__del__`` method, which could suggest that
        #   garbage collection is happening.
        #
        # See https://github.com/gevent/gevent/issues/1961
        # and ``get_hub_if_exists()``
        super(_Threadlocal, self).__init__()
        self.Hub = None
        self.loop = None
        self.hub = None

_threadlocal = _Threadlocal()

Hub = None # Set when gevent.hub is imported

def get_hub_class():
    """Return the type of hub to use for the current thread.

    If there's no type of hub for the current thread yet, 'gevent.hub.Hub' is used.
    """
    hubtype = _threadlocal.Hub
    if hubtype is None:
        hubtype = _threadlocal.Hub = Hub
    return hubtype

def set_default_hub_class(hubtype):
    global Hub
    Hub = hubtype

def get_hub():
    """
    Return the hub for the current thread.

    If a hub does not exist in the current thread, a new one is
    created of the type returned by :func:`get_hub_class`.

    .. deprecated:: 1.3b1
       The ``*args`` and ``**kwargs`` arguments are deprecated. They were
       only used when the hub was created, and so were non-deterministic---to be
       sure they were used, *all* callers had to pass them, or they were order-dependent.
       Use ``set_hub`` instead.

    .. versionchanged:: 1.5a3
       The *args* and *kwargs* arguments are now completely ignored.

    .. versionchanged:: 23.7.0
       The long-deprecated ``args`` and ``kwargs`` parameters are no
       longer accepted.
    """
    # See get_hub_if_exists
    try:
        hub = _threadlocal.hub
    except AttributeError:
        hub = None
    if hub is None:
        hubtype = get_hub_class()
        hub = _threadlocal.hub = hubtype()
    return hub

# For Cython purposes, we need to duplicate get_hub into this function so it
# can be directly called.
def get_hub_noargs():
    # See get_hub_if_exists
    try:
        hub = _threadlocal.hub
    except AttributeError:
        hub = None
    if hub is None:
        hubtype = get_hub_class()
        hub = _threadlocal.hub = hubtype()
    return hub

def get_hub_if_exists():
    """
    Return the hub for the current thread.

    Return ``None`` if no hub has been created yet.
    """
    # Attempt a band-aid for the poorly-understood behaviour
    # seen in https://github.com/gevent/gevent/issues/1961
    # where the ``hub`` attribute has gone missing.
    try:
        return _threadlocal.hub
    except AttributeError:
        # XXX: I'd really like to report this, but I'm not sure how
        # that can be done safely (because I don't know how we get
        # here in the first place). We may be in a place where imports
        # are unsafe, or the interpreter is shutting down, or the
        # thread is exiting, or...
        return None




def set_hub(hub):
    _threadlocal.hub = hub

def get_loop():
    return _threadlocal.loop

def set_loop(loop):
    _threadlocal.loop = loop

from gevent._util import import_c_accel
import_c_accel(globals(), 'gevent.__hub_local')
