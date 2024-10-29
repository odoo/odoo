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
    '_start_new_thread', # Gone in 3.13; now start_joinable_thread
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


import threading as __threading__ # imports os, sys, _thread, functools, time, itertools
_DummyThread_ = __threading__._DummyThread
_MainThread_ = __threading__._MainThread
import os
import sys

from gevent.local import local
from gevent.thread import start_new_thread as _start_new_thread
from gevent.thread import allocate_lock as _allocate_lock
from gevent.thread import get_ident as _get_ident
from gevent.hub import sleep as _sleep, getcurrent
from gevent.lock import RLock


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
    # twice as fast:
    #
    # - 1.16 vs 0.68usec on PyPy (unknown version, older Intel mac)
    # - 29.3 vs 17.7usec on CPython 2.7 (older intel Mac)
    # - 0.98 vs 2.95usec on CPython 3.12.2 (newer M2 mac)
    #
    # It als has the important effect of avoiding allocation and then
    # immediate deletion of _Thread__block, a lock. This is especially
    # important on PyPy where locks go through the cpyext API and
    # Cython, which is known to be slow and potentially buggy (e.g.,
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
    _handle = None # 3.13

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

    # In Python 3.11.8+ and 3.12.2+ (yes, minor patch releases),
    # CPython's ``threading._after_fork`` hook began swizzling the
    # type of the _DummyThread into _MainThread if such a dummy thread
    # was the current thread when ``os.fork()`` gets called.
    # From CPython's perspective, that's a more-or-less fine thing to do.
    # While _DummyThread isn't a subclass of _MainThread, they are both
    # subclasses of Thread, and _MainThread doesn't add any new instance
    # variables.
    #
    # From gevent's perspective, that's NOT good. Our _DummyThread
    # doesn't have all the instance variables that Thread does, and so
    # attempting to do anything with this now-fake _MainThread doesn't work.
    # You in fact immediately get assertion errors from inside ``_after_fork``.
    # Now, these are basically harmless ---  they're printed, and they prevent the cleanup
    # of some globals in _threading, but that probably doesn't matter --- but
    # people complained, and it could break some test scenarios (due to unexpected
    # output on stderr, for example)
    #
    # We thought of a few options to patch around this:
    #
    # - Live with the performance penalty. Newer CPythons are making it
    #   harder and harder to perform well, so if we can possibly avoid
    #   adding our own performance regressions, that would be good.
    #
    # - ``after_fork`` uses ``isinstance(current, _DummyThread)``
    #   before swizzling, so we could use a metaclass to make that
    #   check return false. That's a fairly large compatibility risk,
    #   both because of the use of a metaclass (what if some other
    #   subclass of _DummyTHread is using an incompatible metaclass?)
    #   and the change in ``isinstance`` behaviour. We could limit the latter
    #   to a window around the fork, using ``os.register_at_fork(before, after_in_parent=)``,
    #   but that's a lot of moving pieces requiring the use of a global or class
    #   variable to track state.
    #
    # - We could copy the ivars of the current main thread into the
    #   _DummyThread in ``register_at_fork(before=)``. That appears to
    #   work, but also requires the use of
    #   ``register_at_fork(after_in_parent=)`` to reverse it.
    #
    # - We could simply prevent swizzling the class in the first
    #   place. In combination with
    #   ``register_at_fork(after_in_child=)`` to establish a *real*
    #   new _MainThread, that's a clean solution. Establishing a real
    #   new _MainThread is something that CPython itself is prepared
    #   to do if it can't figure out what the current thread is. The
    #   compatibility risk of this is relatively low: swizzling
    #   classes is frowned upon and uncommon, and we can limit it to
    #   just preventing this specific case. And if somebody was
    #   attempting this already with some other thread subclass, it
    #   would (probably?) have the exact same issues, so we can be pretty
    #   sure nobody is doing that.
    #
    # We're initially going with the last fix; the __class__ part is here,
    # the ``after_in_child`` fixup we only apply if we're monkey-patching.
    #
    # Now, all of this is moot in 3.13, which takes a very different
    # approach to handling this, and also changes some names. See
    # https://github.com/python/cpython/commit/0e9c364f4ac18a2237bdbac702b96bcf8ef9cb09

    # Tests pass just fine in 3.8 (and presumably 3.9 and 3.10) with these fixes
    # applied, but just in case, we only do it where we know it's necessary.
    _NEEDS_CLASS_FORK_FIXUP = (
        (sys.version_info[:2] == (3, 11) and sys.version_info[:3] >= (3, 11, 8))
        or sys.version_info[:3] >= (3, 12, 2)
    )

    if _NEEDS_CLASS_FORK_FIXUP:
        # Override with a property, as opposed to using __setattr__,
        # to avoid adding overhead on any other attribute setting.
        @property
        def __class__(self):
            return type(self)

        @__class__.setter
        def __class__(self, new_class):
            # Even if we wanted to allow setting this, I'm not sure
            # exactly how to do so when we have a property object handling it.
            # Getting the descriptor from ``object.__dict__['__class__']``
            # and using its ``__set__`` method raises a TypeError (as does
            # the simpler ``super().__class__``).
            #
            # Better allow the TypeError for now as opposed to silently ignoring
            # the assignment.
            if new_class is not _MainThread_:
                object.__dict__['__class__'].__set__(self, new_class)



def _after_fork_in_child():
    # We've already imported threading, which installed its "after" hook,
    # so we're going to be called after that hook.
    # Note that this is only installed when monkey-patching.
    # TODO: Is there any point to checking to see if the current thread is
    # our dummy thread before doing this?
    active = __threading__._active
    assert len(active) == 1
    main = __threading__._MainThread()
    __threading__._active[__threading__.get_ident()] = main
    __threading__._main_thread = main
    assert main.ident == __threading__.get_ident()



def main_native_thread():
    return __threading__.main_thread() # pylint:disable=no-member


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

    if _DummyThread._NEEDS_CLASS_FORK_FIXUP and hasattr(os, 'register_at_fork'):
        os.register_at_fork(after_in_child=_after_fork_in_child)
