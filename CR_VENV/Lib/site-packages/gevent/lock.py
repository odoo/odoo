# Copyright (c) 2009-2012 Denis Bilenko. See LICENSE for details.
"""
Locking primitives.

These include semaphores with arbitrary bounds (:class:`Semaphore` and
its safer subclass :class:`BoundedSemaphore`) and a semaphore with
infinite bounds (:class:`DummySemaphore`), along with a reentrant lock
(:class:`RLock`) with the same API as :class:`threading.RLock`.
"""
from __future__ import absolute_import
from __future__ import print_function

from gevent.hub import getcurrent
from gevent._compat import PURE_PYTHON
from gevent._compat import PY2
# This is the one exception to the rule of where to
# import Semaphore, obviously
from gevent import monkey
from gevent._semaphore import Semaphore
from gevent._semaphore import BoundedSemaphore


__all__ = [
    'Semaphore',
    'BoundedSemaphore',
    'DummySemaphore',
    'RLock',
]

# On PyPy, we don't compile the Semaphore class with Cython. Under
# Cython, each individual method holds the GIL for its entire
# duration, ensuring that no other thread can interrupt us in an
# unsafe state (only when we _wait do we call back into Python and
# allow switching threads; this is broken down into the
# _drop_lock_for_switch_out and _acquire_lock_for_switch_in methods).
# Simulate that here through the use of a manual lock. (We use a
# separate lock for each semaphore to allow sys.settrace functions to
# use locks *other* than the one being traced.) This, of course, must
# also hold for PURE_PYTHON mode when no optional C extensions are
# used.

_allocate_lock, _get_ident = monkey.get_original(
    ('_thread', 'thread'),
    ('allocate_lock', 'get_ident')
)

def atomic(meth):
    def m(self, *args):
        with self._atomic:
            return meth(self, *args)
    return m


class _GILLock(object):
    __slots__ = (
        '_owned_thread_id',
        '_gil',
        '_atomic',
        '_recursion_depth',
    )
    # Don't allow re-entry to these functions in a single thread, as
    # can happen if a sys.settrace is used. (XXX: What does that even
    # mean? Our original implementation that did that has been
    # replaced by something more robust)
    #
    # This is essentially a variant of the (pure-Python) RLock from the
    # standard library.
    def __init__(self):
        self._owned_thread_id = None
        self._gil = _allocate_lock()
        self._atomic = _allocate_lock()
        self._recursion_depth = 0

    @atomic
    def acquire(self):
        current_tid = _get_ident()
        if self._owned_thread_id == current_tid:
            self._recursion_depth += 1
            return True

        # Not owned by this thread. Only one thread will make it through this point.
        while 1:
            self._atomic.release()
            try:
                self._gil.acquire()
            finally:
                self._atomic.acquire()
            if self._owned_thread_id is None:
                break

        self._owned_thread_id = current_tid
        self._recursion_depth = 1
        return True

    @atomic
    def release(self):
        current_tid = _get_ident()
        if current_tid != self._owned_thread_id:
            raise RuntimeError("%s: Releasing lock not owned by you. You: 0x%x; Owner: 0x%x" % (
                self,
                current_tid, self._owned_thread_id or 0,
            ))

        self._recursion_depth -= 1

        if not self._recursion_depth:
            self._owned_thread_id = None
            self._gil.release()

    def __enter__(self):
        self.acquire()

    def __exit__(self, t, v, tb):
        self.release()

    def locked(self):
        return self._gil.locked()

class _AtomicSemaphoreMixin(object):
    # Behaves as though the GIL was held for the duration of acquire, wait,
    # and release, just as if we were in Cython.
    #
    # acquire, wait, and release all acquire the lock on entry and release it
    # on exit. acquire and wait can call _wait, which must release it on entry
    # and re-acquire it for them on exit.
    #
    # Note that this does *NOT*, in-and-of itself, make semaphores safe to use from multiple threads
    __slots__ = ()
    def __init__(self, *args, **kwargs):
        self._lock_lock = _GILLock() # pylint:disable=assigning-non-slot
        super(_AtomicSemaphoreMixin, self).__init__(*args, **kwargs)

    def _acquire_lock_for_switch_in(self):
        self._lock_lock.acquire()

    def _drop_lock_for_switch_out(self):
        self._lock_lock.release()

    def _notify_links(self, arrived_while_waiting):
        with self._lock_lock:
            return super(_AtomicSemaphoreMixin, self)._notify_links(arrived_while_waiting)

    def release(self):
        with self._lock_lock:
            return super(_AtomicSemaphoreMixin, self).release()

    def acquire(self, blocking=True, timeout=None):
        with self._lock_lock:
            return super(_AtomicSemaphoreMixin, self).acquire(blocking, timeout)

    _py3k_acquire = acquire

    def wait(self, timeout=None):
        with self._lock_lock:
            return super(_AtomicSemaphoreMixin, self).wait(timeout)

class _AtomicSemaphore(_AtomicSemaphoreMixin, Semaphore):
    __doc__ = Semaphore.__doc__
    __slots__ = (
        '_lock_lock',
    )


class _AtomicBoundedSemaphore(_AtomicSemaphoreMixin, BoundedSemaphore):
    __doc__ = BoundedSemaphore.__doc__
    __slots__ = (
        '_lock_lock',
    )

    def release(self): # pylint:disable=useless-super-delegation
        # This method is duplicated here so that it can get
        # properly documented.
        return super(_AtomicBoundedSemaphore, self).release()


def _fixup_docstrings():
    for c in _AtomicSemaphore, _AtomicBoundedSemaphore:
        b = c.__mro__[2]
        assert b.__name__.endswith('Semaphore') and 'Atomic' not in b.__name__
        assert c.__doc__ == b.__doc__
        for m in 'acquire', 'release', 'wait':
            c_meth = getattr(c, m)
            if PY2:
                c_meth = c_meth.__func__
            b_meth = getattr(b, m)
            c_meth.__doc__ = b_meth.__doc__

_fixup_docstrings()
del _fixup_docstrings


if PURE_PYTHON:
    Semaphore = _AtomicSemaphore
    Semaphore.__name__ = 'Semaphore'
    BoundedSemaphore = _AtomicBoundedSemaphore
    BoundedSemaphore.__name__ = 'BoundedSemaphore'


class DummySemaphore(object):
    """
    DummySemaphore(value=None) -> DummySemaphore

    An object with the same API as :class:`Semaphore`,
    initialized with "infinite" initial value. None of its
    methods ever block.

    This can be used to parameterize on whether or not to actually
    guard access to a potentially limited resource. If the resource is
    actually limited, such as a fixed-size thread pool, use a real
    :class:`Semaphore`, but if the resource is unbounded, use an
    instance of this class. In that way none of the supporting code
    needs to change.

    Similarly, it can be used to parameterize on whether or not to
    enforce mutual exclusion to some underlying object. If the
    underlying object is known to be thread-safe itself mutual
    exclusion is not needed and a ``DummySemaphore`` can be used, but
    if that's not true, use a real ``Semaphore``.
    """

    # Internally this is used for exactly the purpose described in the
    # documentation. gevent.pool.Pool uses it instead of a Semaphore
    # when the pool size is unlimited, and
    # gevent.fileobject.FileObjectThread takes a parameter that
    # determines whether it should lock around IO to the underlying
    # file object.

    def __init__(self, value=None):
        """
        .. versionchanged:: 1.1rc3
            Accept and ignore a *value* argument for compatibility with Semaphore.
        """

    def __str__(self):
        return '<%s>' % self.__class__.__name__

    def locked(self):
        """A DummySemaphore is never locked so this always returns False."""
        return False

    def ready(self):
        """A DummySemaphore is never locked so this always returns True."""
        return True

    def release(self):
        """Releasing a dummy semaphore does nothing."""

    def rawlink(self, callback):
        # XXX should still work and notify?
        pass

    def unlink(self, callback):
        pass

    def wait(self, timeout=None): # pylint:disable=unused-argument
        """Waiting for a DummySemaphore returns immediately."""
        return 1

    def acquire(self, blocking=True, timeout=None):
        """
        A DummySemaphore can always be acquired immediately so this always
        returns True and ignores its arguments.

        .. versionchanged:: 1.1a1
           Always return *true*.
        """
        # pylint:disable=unused-argument
        return True

    def __enter__(self):
        pass

    def __exit__(self, typ, val, tb):
        pass


class RLock(object):
    """
    A mutex that can be acquired more than once by the same greenlet.

    A mutex can only be locked by one greenlet at a time. A single greenlet
    can `acquire` the mutex as many times as desired, though. Each call to
    `acquire` must be paired with a matching call to `release`.

    It is an error for a greenlet that has not acquired the mutex
    to release it.

    Instances are context managers.
    """

    __slots__ = (
        '_block',
        '_owner',
        '_count',
        '__weakref__',
    )

    def __init__(self, hub=None):
        """
        .. versionchanged:: 20.5.1
           Add the ``hub`` argument.
        """
        self._block = Semaphore(1, hub)
        self._owner = None
        self._count = 0

    def __repr__(self):
        return "<%s at 0x%x _block=%s _count=%r _owner=%r)>" % (
            self.__class__.__name__,
            id(self),
            self._block,
            self._count,
            self._owner)

    def acquire(self, blocking=True, timeout=None):
        """
        Acquire the mutex, blocking if *blocking* is true, for up to
        *timeout* seconds.

        .. versionchanged:: 1.5a4
           Added the *timeout* parameter.

        :return: A boolean indicating whether the mutex was acquired.
        """
        me = getcurrent()
        if self._owner is me:
            self._count = self._count + 1
            return 1
        rc = self._block.acquire(blocking, timeout)
        if rc:
            self._owner = me
            self._count = 1
        return rc

    def __enter__(self):
        return self.acquire()

    def release(self):
        """
        Release the mutex.

        Only the greenlet that originally acquired the mutex can
        release it.
        """
        if self._owner is not getcurrent():
            raise RuntimeError("cannot release un-acquired lock. Owner: %r Current: %r" % (
                self._owner, getcurrent()
            ))
        self._count = count = self._count - 1
        if not count:
            self._owner = None
            self._block.release()

    def __exit__(self, typ, value, tb):
        self.release()

    # Internal methods used by condition variables

    def _acquire_restore(self, count_owner):
        count, owner = count_owner
        self._block.acquire()
        self._count = count
        self._owner = owner

    def _release_save(self):
        count = self._count
        self._count = 0
        owner = self._owner
        self._owner = None
        self._block.release()
        return (count, owner)

    def _is_owned(self):
        return self._owner is getcurrent()
