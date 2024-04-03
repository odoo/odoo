"""
Implementation of the standard :mod:`threading` using greenlets.

.. note::

    This module is a helper for :mod:`gevent.monkey` and is not
    intended to be used directly. For spawning greenlets in your
    applications, prefer higher level constructs like
    :class:`gevent.Greenlet` class or :func:`gevent.spawn`. Attributes
    in this module like ``__threading__`` are implementation artifacts subject
    to change at any time.

.. versionchanged:: 1.2.3

   Defer adjusting the stdlib's list of active threads until we are
   monkey patched. Previously this was done at import time. We are
   documented to only be used as a helper for monkey patching, so this should
   functionally be the same, but some applications ignore the documentation and
   directly import this module anyway.

   A positive consequence is that ``import gevent.threading,
   threading; threading.current_thread()`` will no longer return a DummyThread
   before monkey-patching.
"""
from __future__ import absolute_import


__implements__ = [
    'local',
    '_start_new_thread',
    '_allocate_lock',
    'Lock',
    '_get_ident',
    '_sleep',
    '_DummyThread',
    # RLock cannot go here, even though we need to import it.
    # If it goes here, it replaces the RLock from the native
    # threading module, but we really just need it here when some
    # things import this module.
    #'RLock',
]


import threading as __threading__
_DummyThread_ = __threading__._DummyThread
from gevent.local import local
from gevent.thread import start_new_thread as _start_new_thread
from gevent.thread import allocate_lock as _allocate_lock
from gevent.thread import get_ident as _get_ident
from gevent.hub import sleep as _sleep, getcurrent
from gevent.lock import RLock

from gevent._compat import PY3
from gevent._compat import PYPY
from gevent._util import LazyOnClass

# Exports, prevent unused import warnings.
# XXX: Why don't we use __all__?
local = local
start_new_thread = _start_new_thread
allocate_lock = _allocate_lock
_get_ident = _get_ident
_sleep = _sleep
getcurrent = getcurrent

Lock = _allocate_lock
RLock = RLock


def _cleanup(g):
    __threading__._active.pop(_get_ident(g), None)

def _make_cleanup_id(gid):
    def _(_r):
        __threading__._active.pop(gid, None)
    return _

_weakref = None

class _DummyThread(_DummyThread_):
    # We avoid calling the superclass constructor. This makes us about
    # twice as fast (1.16 vs 0.68usec on PyPy, 29.3 vs 17.7usec on
    # CPython 2.7), and has the important effect of avoiding
    # allocation and then immediate deletion of _Thread__block, a
    # lock. This is especially important on PyPy where locks go
    # through the cpyext API and Cython, which is known to be slow and
    # potentially buggy (e.g.,
    # https://bitbucket.org/pypy/pypy/issues/2149/memory-leak-for-python-subclass-of-cpyext#comment-22347393)

    # These objects are constructed quite frequently in some cases, so
    # the optimization matters: for example, in gunicorn, which uses
    # pywsgi.WSGIServer, most every request is handled in a new greenlet,
    # and every request uses a logging.Logger to write the access log,
    # and every call to a log method captures the current thread (by
    # default).
    #
    # (Obviously we have to duplicate the effects of the constructor,
    # at least for external state purposes, which is potentially
    # slightly fragile.)

    # For the same reason, instances of this class will cleanup their own entry
    # in ``threading._active``

    # This class also solves a problem forking process with subprocess: after forking,
    # Thread.__stop is called, which throws an exception when __block doesn't
    # exist.

    # Capture the static things as class vars to save on memory/
    # construction time.
    # In Py2, they're all private; in Py3, they become protected
    _Thread__stopped = _is_stopped = _stopped = False
    _Thread__initialized = _initialized = True
    _Thread__daemonic = _daemonic = True
    _Thread__args = _args = ()
    _Thread__kwargs = _kwargs = None
    _Thread__target = _target = None
    _Thread_ident = _ident = None
    _Thread__started = _started = __threading__.Event()
    _Thread__started.set()
    _tstate_lock = None

    def __init__(self): # pylint:disable=super-init-not-called
        #_DummyThread_.__init__(self)

        # It'd be nice to use a pattern like "greenlet-%d", but there are definitely
        # third-party libraries checking thread names to detect DummyThread objects.
        self._name = self._Thread__name = __threading__._newname("Dummy-%d")
        # All dummy threads in the same native thread share the same ident
        # (that of the native thread), unless we're monkey-patched.
        self._set_ident()

        g = getcurrent()
        gid = _get_ident(g)
        __threading__._active[gid] = self
        rawlink = getattr(g, 'rawlink', None)
        if rawlink is not None:
            # raw greenlet.greenlet greenlets don't
            # have rawlink...
            rawlink(_cleanup)
        else:
            # ... so for them we use weakrefs.
            # See https://github.com/gevent/gevent/issues/918
            ref = self.__weakref_ref
            ref = ref(g, _make_cleanup_id(gid)) # pylint:disable=too-many-function-args
            self.__raw_ref = ref
            assert self.__raw_ref is ref # prevent pylint thinking its unused

    def _Thread__stop(self):
        pass

    _stop = _Thread__stop # py3

    def _wait_for_tstate_lock(self, *args, **kwargs): # pylint:disable=signature-differs
        pass

    @LazyOnClass
    def __weakref_ref(self):
        return __import__('weakref').ref

if hasattr(__threading__, 'main_thread'): # py 3.4+
    def main_native_thread():
        return __threading__.main_thread() # pylint:disable=no-member
else:
    def main_native_thread():
        main_threads = [v for v in __threading__._active.values()
                        if isinstance(v, __threading__._MainThread)]
        assert len(main_threads) == 1, "Too many main threads"

        return main_threads[0]

if PY3:
    # XXX: Issue 18808 breaks us on Python 3.4+.
    # Thread objects now expect a callback from the interpreter itself
    # (threadmodule.c:release_sentinel) when the C-level PyThreadState
    # object is being deallocated. Because this never happens
    # when a greenlet exits, join() and friends will block forever.
    # Fortunately this is easy to fix: just ensure that the allocation of the
    # lock, _set_sentinel, creates a *gevent* lock, and release it when
    # we're done. The main _shutdown code is in Python and deals with
    # this gracefully.

    class Thread(__threading__.Thread):

        def _set_tstate_lock(self):
            super(Thread, self)._set_tstate_lock()
            greenlet = getcurrent()
            greenlet.rawlink(self.__greenlet_finished)

        def __greenlet_finished(self, _):
            if self._tstate_lock:
                self._tstate_lock.release()
                self._stop()

    __implements__.append('Thread')

    class Timer(Thread, __threading__.Timer): # pylint:disable=abstract-method,inherit-non-class
        pass

    __implements__.append('Timer')

    _set_sentinel = allocate_lock
    __implements__.append('_set_sentinel')
    # The main thread is patched up with more care
    # in _gevent_will_monkey_patch

if PY3:
    __implements__.remove('_get_ident')
    __implements__.append('get_ident')
    get_ident = _get_ident
    __implements__.remove('_sleep')

if hasattr(__threading__, '_CRLock'):
    # Python 3 changed the implementation of threading.RLock
    # Previously it was a factory function around threading._RLock
    # which in turn used _allocate_lock. Now, it wants to use
    # threading._CRLock, which is imported from _thread.RLock and as such
    # is implemented in C. So it bypasses our _allocate_lock function.
    # Fortunately they left the Python fallback in place and use it
    # if the imported _CRLock is None; this arranges for that to be the case.

    # This was also backported to PyPy 2.7-7.0
    assert PY3 or PYPY, "Unsupported Python version"
    _CRLock = None
    __implements__.append('_CRLock')

def _gevent_will_monkey_patch(native_module, items, warn): # pylint:disable=unused-argument
    # Make sure the MainThread can be found by our current greenlet ID,
    # otherwise we get a new DummyThread, which cannot be joined.
    # Fixes tests in test_threading_2 under PyPy.
    main_thread = main_native_thread()
    if __threading__.current_thread() != main_thread:
        warn("Monkey-patching outside the main native thread. Some APIs "
             "will not be available. Expect a KeyError to be printed at shutdown.")
        return

    if _get_ident() not in __threading__._active:
        main_id = main_thread.ident
        del __threading__._active[main_id]
        main_thread._ident = main_thread._Thread__ident = _get_ident()
        __threading__._active[_get_ident()] = main_thread
