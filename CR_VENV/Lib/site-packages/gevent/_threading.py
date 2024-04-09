"""
A small selection of primitives that always work with
native threads. This has very limited utility and is
targeted only for the use of gevent's threadpool.
"""
from __future__ import absolute_import

from collections import deque

from gevent import monkey
from gevent._compat import thread_mod_name
from gevent._compat import PY3


__all__ = [
    'Lock',
    'Queue',
    'EmptyTimeout',
]


start_new_thread, Lock, get_thread_ident, = monkey.get_original(thread_mod_name, [
    'start_new_thread', 'allocate_lock', 'get_ident',
])


# We want to support timeouts on locks. In this way, we can allow idle threads to
# expire from a thread pool. On Python 3, this is native behaviour; on Python 2,
# we have to emulate it. For Python 3, we want this to have the lowest possible overhead,
# so we'd prefer to use a direct call, rather than go through a wrapper. But we also
# don't want to allocate locks at import time because..., so we swizzle out the method
# at runtime.
#
#
# In all cases, a timeout value of -1 means "infinite". Sigh.
if PY3:
    def acquire_with_timeout(lock, timeout=-1):
        globals()['acquire_with_timeout'] = type(lock).acquire
        return lock.acquire(timeout=timeout)
else:
    def acquire_with_timeout(lock, timeout=-1,
                             _time=monkey.get_original('time', 'time'),
                             _sleep=monkey.get_original('time', 'sleep')):
        deadline = _time() + timeout if timeout != -1 else None
        while 1:
            if lock.acquire(False): # Can we acquire non-blocking?
                return True
            if deadline is not None and _time() >= deadline:
                return False
            _sleep(0.005)

class _Condition(object):
    # We could use libuv's ``uv_cond_wait`` to implement this whole
    # class and get native timeouts and native performance everywhere.

    # pylint:disable=method-hidden

    __slots__ = (
        '_lock',
        '_waiters',
    )

    def __init__(self, lock):
        # This lock is used to protect our own data structures;
        # calls to ``wait`` and ``notify_one`` *must* be holding this
        # lock.
        self._lock = lock
        self._waiters = []

        # No need to special case for _release_save and
        # _acquire_restore; those are only used for RLock, and
        # we don't use those.

    def __enter__(self):
        return self._lock.__enter__()

    def __exit__(self, t, v, tb):
        return self._lock.__exit__(t, v, tb)

    def __repr__(self):
        return "<Condition(%s, %d)>" % (self._lock, len(self._waiters))

    def wait(self, wait_lock, timeout=-1, _wait_for_notify=acquire_with_timeout):
        # This variable is for the monitoring utils to know that
        # this is an idle frame and shouldn't be counted.
        gevent_threadpool_worker_idle = True # pylint:disable=unused-variable

        # The _lock must be held.
        # The ``wait_lock`` must be *un*owned, so the timeout doesn't apply there.
        # Take that lock now.
        wait_lock.acquire()
        self._waiters.append(wait_lock)

        self._lock.release()
        try:
            # We're already holding this native lock, so when we try to acquire it again,
            # that won't work and we'll block until someone calls notify_one() (which might
            # have already happened).
            notified = _wait_for_notify(wait_lock, timeout)
        finally:
            self._lock.acquire()

        # Now that we've acquired _lock again, no one can call notify_one(), or this
        # method.
        if not notified:
            # We need to come out of the waiters list. IF we're still there; it's
            # possible that between the call to _acquire() returning False,
            # and the time that we acquired _lock, someone did a ``notify_one``
            # and released the lock. For that reason, do a non-blocking acquire()
            notified = wait_lock.acquire(False)
        if not notified:
            # Well narf. No go. We must stil be in the waiters list, so take us out
            self._waiters.remove(wait_lock)
            # We didn't get notified, but we're still holding a lock that we
            # need to release.
            wait_lock.release()
        else:
            # We got notified, so we need to reset.
            wait_lock.release()
        return notified

    def notify_one(self):
        # The lock SHOULD be owned, but we don't check that.
        try:
            waiter = self._waiters.pop()
        except IndexError:
            # Nobody around
            pass
        else:
            # The owner of the ``waiter`` is blocked on
            # acquiring it again, so when we ``release`` it, it
            # is free to be scheduled and resume.
            waiter.release()

class EmptyTimeout(Exception):
    """Raised from :meth:`Queue.get` if no item is available in the timeout."""


class Queue(object):
    """
    Create a queue object.

    The queue is always infinite size.
    """

    __slots__ = ('_queue', '_mutex', '_not_empty', 'unfinished_tasks')

    def __init__(self):
        self._queue = deque()
        # mutex must be held whenever the queue is mutating.  All methods
        # that acquire mutex must release it before returning.  mutex
        # is shared between the three conditions, so acquiring and
        # releasing the conditions also acquires and releases mutex.
        self._mutex = Lock()
        # Notify not_empty whenever an item is added to the queue; a
        # thread waiting to get is notified then.
        self._not_empty = _Condition(self._mutex)

        self.unfinished_tasks = 0

    def task_done(self):
        """Indicate that a formerly enqueued task is complete.

        Used by Queue consumer threads.  For each get() used to fetch a task,
        a subsequent call to task_done() tells the queue that the processing
        on the task is complete.

        If a join() is currently blocking, it will resume when all items
        have been processed (meaning that a task_done() call was received
        for every item that had been put() into the queue).

        Raises a ValueError if called more times than there were items
        placed in the queue.
        """
        with self._mutex:
            unfinished = self.unfinished_tasks - 1
            if unfinished <= 0:
                if unfinished < 0:
                    raise ValueError(
                        'task_done() called too many times; %s remaining tasks' % (
                            self.unfinished_tasks
                        )
                    )
            self.unfinished_tasks = unfinished

    def qsize(self, len=len):
        """Return the approximate size of the queue (not reliable!)."""
        return len(self._queue)

    def empty(self):
        """Return True if the queue is empty, False otherwise (not reliable!)."""
        return not self.qsize()

    def full(self):
        """Return True if the queue is full, False otherwise (not reliable!)."""
        return False

    def put(self, item):
        """Put an item into the queue.
        """
        with self._mutex:
            self._queue.append(item)
            self.unfinished_tasks += 1
            self._not_empty.notify_one()

    def get(self, cookie, timeout=-1):
        """
        Remove and return an item from the queue.

        If *timeout* is given, and is not -1, then we will
        attempt to wait for only that many seconds to get an item.
        If those seconds elapse and no item has become available,
        raises :class:`EmptyTimeout`.
        """
        with self._mutex:
            while not self._queue:
                # Temporarily release our mutex and wait for someone
                # to wake us up. There *should* be an item in the queue
                # after that.
                notified = self._not_empty.wait(cookie, timeout)
                # Ok, we're holding the mutex again, so our state is guaranteed stable.
                # It's possible that in the brief window where we didn't hold the lock,
                # someone put something in the queue, and if so, we can take it.
                if not notified and not self._queue:
                    raise EmptyTimeout
            item = self._queue.popleft()
            return item

    def allocate_cookie(self):
        """
        Create and return the *cookie* to pass to `get()`.

        Each thread that will use `get` needs a distinct cookie.
        """
        return Lock()

    def kill(self):
        """
        Call to destroy this object.

        Use this when it's not possible to safely drain the queue, e.g.,
        after a fork when the locks are in an uncertain state.
        """
        self._queue = None
        self._mutex = None
        self._not_empty = None
        self.unfinished_tasks = None
