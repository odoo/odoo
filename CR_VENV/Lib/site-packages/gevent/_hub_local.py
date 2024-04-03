# -*- coding: utf-8 -*-
# copyright 2018 gevent. See LICENSE
"""
Maintains the thread local hub.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


from gevent._compat import thread_mod_name

__all__ = [
    'get_hub',
    'get_hub_noargs',
    'get_hub_if_exists',
]

# These must be the "real" native thread versions,
# not monkey-patched.
# We are imported early enough (by gevent/__init__) that
# we can rely on not being monkey-patched in any way yet.
class _Threadlocal(__import__(thread_mod_name)._local):

    def __init__(self):
        # Use a class with an initializer so that we can test
        # for 'is None' instead of catching AttributeError, making
        # the code cleaner and possibly solving some corner cases
        # (like #687)
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

def get_hub(*args, **kwargs): # pylint:disable=unused-argument
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
    """

    return get_hub_noargs()

def get_hub_noargs():
    # Just like get_hub, but cheaper to call because it
    # takes no arguments or kwargs. See also a copy in
    # gevent/greenlet.py
    hub = _threadlocal.hub
    if hub is None:
        hubtype = get_hub_class()
        hub = _threadlocal.hub = hubtype()
    return hub

def get_hub_if_exists():
    """Return the hub for the current thread.

    Return ``None`` if no hub has been created yet.
    """
    return _threadlocal.hub


def set_hub(hub):
    _threadlocal.hub = hub

def get_loop():
    return _threadlocal.loop

def set_loop(loop):
    _threadlocal.loop = loop

from gevent._util import import_c_accel
import_c_accel(globals(), 'gevent.__hub_local')
