"""
Implementation of the standard :mod:`thread` module that spawns greenlets.

.. note::

    This module is a helper for :mod:`gevent.monkey` and is not
    intended to be used directly. For spawning greenlets in your
    applications, prefer higher level constructs like
    :class:`gevent.Greenlet` class or :func:`gevent.spawn`.
"""
from __future__ import absolute_import
import sys

__implements__ = [
    'allocate_lock',
    'get_ident',
    'exit',
    'LockType',
    'stack_size',
    'start_new_thread',
    '_local',
]

__imports__ = ['error']
if sys.version_info[0] == 2:
    import thread as __thread__ # pylint:disable=import-error
    PY2 = True
    PY3 = False
    # Name the `future` backport that might already have been imported;
    # Importing `pkg_resources` imports this, for example.
    __alternate_targets__ = ('_thread',)
else:
    import _thread as __thread__ # pylint:disable=import-error
    PY2 = False
    PY3 = True
    __target__ = '_thread'
    __imports__ += [
        'TIMEOUT_MAX',
        'allocate',
        'exit_thread',
        'interrupt_main',
        'start_new'
    ]
    if sys.version_info[:2] >= (3, 8):
        # We can't actually produce a value that "may be used
        # to identify this particular thread system-wide", right?
        # Even if we could, I imagine people will want to pass this to
        # non-Python (native) APIs, so we shouldn't mess with it.
        __imports__.append('get_native_id')


error = __thread__.error

from gevent._compat import PYPY
from gevent._util import copy_globals
from gevent.hub import getcurrent
from gevent.hub import GreenletExit
from gevent.hub import sleep
from gevent._hub_local import get_hub_if_exists
from gevent.greenlet import Greenlet
from gevent.lock import BoundedSemaphore
from gevent.local import local as _local
from gevent.exceptions import LoopExit

if hasattr(__thread__, 'RLock'):
    assert PY3 or PYPY
    # Added in Python 3.4, backported to PyPy 2.7-7.0
    __imports__.append("RLock")



def get_ident(gr=None):
    if gr is None:
        gr = getcurrent()
    return id(gr)


def start_new_thread(function, args=(), kwargs=None):
    if kwargs is not None:
        greenlet = Greenlet.spawn(function, *args, **kwargs) # pylint:disable=not-a-mapping
    else:
        greenlet = Greenlet.spawn(function, *args)
    return get_ident(greenlet)


class LockType(BoundedSemaphore):
    # Change the ValueError into the appropriate thread error
    # and any other API changes we need to make to match behaviour
    _OVER_RELEASE_ERROR = __thread__.error

    if PYPY and PY3:
        _OVER_RELEASE_ERROR = RuntimeError

    if PY3:
        _TIMEOUT_MAX = __thread__.TIMEOUT_MAX # python 2: pylint:disable=no-member
    else:
        _TIMEOUT_MAX = 9223372036.0

    def acquire(self, blocking=True, timeout=-1):
        # This is the Python 3 signature.
        # On Python 2, Lock.acquire has the signature `Lock.acquire([wait])`
        # where `wait` is a boolean that cannot be passed by name, only position.
        # so we're fine to use the Python 3 signature.

        # Transform the default -1 argument into the None that our
        # semaphore implementation expects, and raise the same error
        # the stdlib implementation does.
        if timeout == -1:
            timeout = None
        if not blocking and timeout is not None:
            raise ValueError("can't specify a timeout for a non-blocking call")
        if timeout is not None:
            if timeout < 0:
                # in C: if(timeout < 0 && timeout != -1)
                raise ValueError("timeout value must be strictly positive")
            if timeout > self._TIMEOUT_MAX:
                raise OverflowError('timeout value is too large')


        try:
            acquired = BoundedSemaphore.acquire(self, blocking, timeout)
        except LoopExit:
            # Raised when the semaphore was not trivially ours, and we needed
            # to block. Some other thread presumably owns the semaphore, and there are no greenlets
            # running in this thread to switch to. So the best we can do is
            # release the GIL and try again later.
            if blocking: # pragma: no cover
                raise
            acquired = False

        if not acquired and not blocking and getcurrent() is not get_hub_if_exists():
            # Run other callbacks. This makes spin locks works.
            # We can't do this if we're in the hub, which we could easily be:
            # printing the repr of a thread checks its tstate_lock, and sometimes we
            # print reprs in the hub.
            # See https://github.com/gevent/gevent/issues/1464

            # By using sleep() instead of self.wait(0), we don't force a trip
            # around the event loop *unless* we've been running callbacks for
            # longer than our switch interval.
            sleep()
        return acquired

    # Should we implement _is_owned, at least for Python 2? See notes in
    # monkey.py's patch_existing_locks.

allocate_lock = LockType


def exit():
    raise GreenletExit


if hasattr(__thread__, 'stack_size'):
    _original_stack_size = __thread__.stack_size

    def stack_size(size=None):
        if size is None:
            return _original_stack_size()
        if size > _original_stack_size():
            return _original_stack_size(size)
        # not going to decrease stack_size, because otherwise other
        # greenlets in this thread will suffer
else:
    __implements__.remove('stack_size')

__imports__ = copy_globals(__thread__, globals(),
                           only_names=__imports__,
                           ignore_missing_names=True)

__all__ = __implements__ + __imports__
__all__.remove('_local')


# XXX interrupt_main
# XXX _count()
