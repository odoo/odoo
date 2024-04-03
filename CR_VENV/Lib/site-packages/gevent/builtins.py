# Copyright (c) 2015 gevent contributors. See LICENSE for details.
"""gevent friendly implementations of builtin functions."""
from __future__ import absolute_import

import weakref

from gevent.lock import RLock
from gevent._compat import PY3
from gevent._compat import imp_acquire_lock
from gevent._compat import imp_release_lock


# Normally we'd have the "expected" case inside the try
# (Python 3, because Python 3 is the way forward). But
# under Python 2, the popular `future` library *also* provides
# a `builtins` module---which lacks the __import__ attribute.
# So we test for the old, deprecated version first

try: # Py2
    import __builtin__ as __gbuiltins__
    _allowed_module_name_types = (basestring,) # pylint:disable=undefined-variable
    __target__ = '__builtin__'
except ImportError:
    import builtins as __gbuiltins__ # pylint: disable=import-error
    _allowed_module_name_types = (str,)
    __target__ = 'builtins'

_import = __gbuiltins__.__import__

# We need to protect imports both across threads and across greenlets.
# And the order matters. Note that under 3.4, the global import lock
# and imp module are deprecated. It seems that in all Py3 versions, a
# module lock is used such that this fix is not necessary.

# We emulate the per-module locking system under Python 2 in order to
# avoid issues acquiring locks in multiple-level-deep imports
# that attempt to use the gevent blocking API at runtime; using one lock
# could lead to a LoopExit error as a greenlet attempts to block on it while
# it's already held by the main greenlet (issue #798).

# We base this approach on a simplification of what `importlib._bootstrap`
# does; notably, we don't check for deadlocks

_g_import_locks = {} # name -> wref of RLock

__lock_imports = True


def __module_lock(name):
    # Return the lock for the given module, creating it if necessary.
    # It will be removed when no longer needed.
    # Nothing in this function yields, so we're multi-greenlet safe
    # (But not multi-threading safe.)
    # XXX: What about on PyPy, where the GC is asynchronous (not ref-counting)?
    # (Does it stop-the-world first?)
    lock = None
    try:
        lock = _g_import_locks[name]()
    except KeyError:
        pass

    if lock is None:
        lock = RLock()

        def cb(_):
            # We've seen a KeyError on PyPy on RPi2
            _g_import_locks.pop(name, None)
        _g_import_locks[name] = weakref.ref(lock, cb)
    return lock


def __import__(*args, **kwargs):
    """
    __import__(name, globals=None, locals=None, fromlist=(), level=0) -> object

    Normally python protects imports against concurrency by doing some locking
    at the C level (at least, it does that in CPython).  This function just
    wraps the normal __import__ functionality in a recursive lock, ensuring that
    we're protected against greenlet import concurrency as well.
    """
    if args and not issubclass(type(args[0]), _allowed_module_name_types):
        # if a builtin has been acquired as a bound instance method,
        # python knows not to pass 'self' when the method is called.
        # No such protection exists for monkey-patched builtins,
        # however, so this is necessary.
        args = args[1:]

    if not __lock_imports:
        return _import(*args, **kwargs)

    module_lock = __module_lock(args[0]) # Get a lock for the module name
    imp_acquire_lock()
    try:
        module_lock.acquire()
        try:
            result = _import(*args, **kwargs)
        finally:
            module_lock.release()
    finally:
        imp_release_lock()
    return result


def _unlock_imports():
    """
    Internal function, called when gevent needs to perform imports
    lazily, but does not know the state of the system. It may be impossible
    to take the import lock because there are no other running greenlets, for
    example. This causes a monkey-patched __import__ to avoid taking any locks.
    until the corresponding call to lock_imports. This should only be done for limited
    amounts of time and when the set of imports is statically known to be "safe".
    """
    global __lock_imports
    # This could easily become a list that we push/pop from or an integer
    # we increment if we need to do this recursively, but we shouldn't get
    # that complex.
    __lock_imports = False


def _lock_imports():
    global __lock_imports
    __lock_imports = True

if PY3:
    __implements__ = []
    __import__ = _import
else:
    __implements__ = ['__import__']
__all__ = __implements__


from gevent._util import copy_globals

__imports__ = copy_globals(__gbuiltins__, globals(),
                           names_to_ignore=__implements__)
