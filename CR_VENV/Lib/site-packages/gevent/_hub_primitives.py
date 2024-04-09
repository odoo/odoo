# -*- coding: utf-8 -*-
# copyright (c) 2018 gevent. See  LICENSE.
# cython: auto_pickle=False,embedsignature=True,always_allow_keywords=False,binding=True
"""
A collection of primitives used by the hub, and suitable for
compilation with Cython because of their frequency of use.


"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import traceback

from gevent.exceptions import InvalidSwitchError
from gevent.exceptions import ConcurrentObjectUseError

from gevent import _greenlet_primitives
from gevent import _waiter
from gevent._util import _NONE
from gevent._hub_local import get_hub_noargs as get_hub
from gevent.timeout import Timeout

# In Cython, we define these as 'cdef inline' functions. The
# compilation unit cannot have a direct assignment to them (import
# is assignment) without generating a 'lvalue is not valid target'
# error.
locals()['getcurrent'] = __import__('greenlet').getcurrent
locals()['greenlet_init'] = lambda: None
locals()['Waiter'] = _waiter.Waiter
locals()['MultipleWaiter'] = _waiter.MultipleWaiter
locals()['SwitchOutGreenletWithLoop'] = _greenlet_primitives.SwitchOutGreenletWithLoop

__all__ = [
    'WaitOperationsGreenlet',
    'iwait_on_objects',
    'wait_on_objects',
    'wait_read',
    'wait_write',
    'wait_readwrite',
]

class WaitOperationsGreenlet(SwitchOutGreenletWithLoop): # pylint:disable=undefined-variable

    def wait(self, watcher):
        """
        Wait until the *watcher* (which must not be started) is ready.

        The current greenlet will be unscheduled during this time.
        """
        waiter = Waiter(self) # pylint:disable=undefined-variable
        watcher.start(waiter.switch, waiter)
        try:
            result = waiter.get()
            if result is not waiter:
                raise InvalidSwitchError(
                    'Invalid switch into %s: got %r (expected %r; waiting on %r with %r)' % (
                        getcurrent(), # pylint:disable=undefined-variable
                        result,
                        waiter,
                        self,
                        watcher
                    )
                )
        finally:
            watcher.stop()

    def cancel_waits_close_and_then(self, watchers, exc_kind, then, *then_args):
        deferred = []
        for watcher in watchers:
            if watcher is None:
                continue
            if watcher.callback is None:
                watcher.close()
            else:
                deferred.append(watcher)
        if deferred:
            self.loop.run_callback(self._cancel_waits_then, deferred, exc_kind, then, then_args)
        else:
            then(*then_args)

    def _cancel_waits_then(self, watchers, exc_kind, then, then_args):
        for watcher in watchers:
            self._cancel_wait(watcher, exc_kind, True)
        then(*then_args)

    def cancel_wait(self, watcher, error, close_watcher=False):
        """
        Cancel an in-progress call to :meth:`wait` by throwing the given *error*
        in the waiting greenlet.

        .. versionchanged:: 1.3a1
           Added the *close_watcher* parameter. If true, the watcher
           will be closed after the exception is thrown. The watcher should then
           be discarded. Closing the watcher is important to release native resources.
        .. versionchanged:: 1.3a2
           Allow the *watcher* to be ``None``. No action is taken in that case.

        """
        if watcher is None:
            # Presumably already closed.
            # See https://github.com/gevent/gevent/issues/1089
            return

        if watcher.callback is not None:
            self.loop.run_callback(self._cancel_wait, watcher, error, close_watcher)
            return

        if close_watcher:
            watcher.close()

    def _cancel_wait(self, watcher, error, close_watcher):
        # Running in the hub. Switches to the waiting greenlet to raise
        # the error; assuming the waiting greenlet dies, switches back
        # to this  (because the waiting greenlet's parent is the hub.)

        # We have to check again to see if it was still active by the time
        # our callback actually runs.
        active = watcher.active
        cb = watcher.callback
        if close_watcher:
            watcher.close()
        if active:
            # The callback should be greenlet.switch(). It may or may not be None.
            glet = getattr(cb, '__self__', None)
            if glet is not None:
                glet.throw(error)


class _WaitIterator(object):

    def __init__(self, objects, hub, timeout, count):
        self._hub = hub
        self._waiter = MultipleWaiter(hub) # pylint:disable=undefined-variable
        self._switch = self._waiter.switch
        self._timeout = timeout
        self._objects = objects

        self._timer = None
        self._begun = False

        # Even if we're only going to return 1 object,
        # we must still rawlink() *all* of them, so that no
        # matter which one finishes first we find it.
        self._count = len(objects) if count is None else min(count, len(objects))

    def _begin(self):
        if self._begun:
            return

        self._begun = True

        # XXX: If iteration doesn't actually happen, we
        # could leave these links around!
        for obj in self._objects:
            obj.rawlink(self._switch)

        if self._timeout is not None:
            self._timer = self._hub.loop.timer(self._timeout, priority=-1)
            self._timer.start(self._switch, self)

    def __iter__(self):
        return self

    def __next__(self):
        self._begin()

        if self._count == 0:
            # Exhausted
            self._cleanup()
            raise StopIteration()

        self._count -= 1
        try:
            item = self._waiter.get()
            self._waiter.clear()
            if item is self:
                # Timer expired, no more
                self._cleanup()
                raise StopIteration()
            return item
        except:
            self._cleanup()
            raise

    next = __next__

    def _cleanup(self):
        if self._timer is not None:
            self._timer.close()
            self._timer = None

        objs = self._objects
        self._objects = ()
        for aobj in objs:
            unlink = getattr(aobj, 'unlink', None)
            if unlink is not None:
                try:
                    unlink(self._switch)
                except: # pylint:disable=bare-except
                    traceback.print_exc()

    def __enter__(self):
        return self

    def __exit__(self, typ, value, tb):
        self._cleanup()


def iwait_on_objects(objects, timeout=None, count=None):
    """
    Iteratively yield *objects* as they are ready, until all (or *count*) are ready
    or *timeout* expired.

    If you will only be consuming a portion of the *objects*, you should
    do so inside a ``with`` block on this object to avoid leaking resources::

        with gevent.iwait((a, b, c)) as it:
            for i in it:
                if i is a:
                    break

    :param objects: A sequence (supporting :func:`len`) containing objects
        implementing the wait protocol (rawlink() and unlink()).
    :keyword int count: If not `None`, then a number specifying the maximum number
        of objects to wait for. If ``None`` (the default), all objects
        are waited for.
    :keyword float timeout: If given, specifies a maximum number of seconds
        to wait. If the timeout expires before the desired waited-for objects
        are available, then this method returns immediately.

    .. seealso:: :func:`wait`

    .. versionchanged:: 1.1a1
       Add the *count* parameter.
    .. versionchanged:: 1.1a2
       No longer raise :exc:`LoopExit` if our caller switches greenlets
       in between items yielded by this function.
    .. versionchanged:: 1.4
       Add support to use the returned object as a context manager.
    """
    # QQQ would be nice to support iterable here that can be generated slowly (why?)
    hub = get_hub()
    if objects is None:
        return [hub.join(timeout=timeout)]
    return _WaitIterator(objects, hub, timeout, count)


def wait_on_objects(objects=None, timeout=None, count=None):
    """
    Wait for ``objects`` to become ready or for event loop to finish.

    If ``objects`` is provided, it must be a list containing objects
    implementing the wait protocol (rawlink() and unlink() methods):

    - :class:`gevent.Greenlet` instance
    - :class:`gevent.event.Event` instance
    - :class:`gevent.lock.Semaphore` instance
    - :class:`gevent.subprocess.Popen` instance

    If ``objects`` is ``None`` (the default), ``wait()`` blocks until
    the current event loop has nothing to do (or until ``timeout`` passes):

    - all greenlets have finished
    - all servers were stopped
    - all event loop watchers were stopped.

    If ``count`` is ``None`` (the default), wait for all ``objects``
    to become ready.

    If ``count`` is a number, wait for (up to) ``count`` objects to become
    ready. (For example, if count is ``1`` then the function exits
    when any object in the list is ready).

    If ``timeout`` is provided, it specifies the maximum number of
    seconds ``wait()`` will block.

    Returns the list of ready objects, in the order in which they were
    ready.

    .. seealso:: :func:`iwait`
    """
    if objects is None:
        hub = get_hub()
        return hub.join(timeout=timeout) # pylint:disable=
    return list(iwait_on_objects(objects, timeout, count))

_timeout_error = Exception

def set_default_timeout_error(e):
    global _timeout_error
    _timeout_error = e

def _primitive_wait(watcher, timeout, timeout_exc, hub):
    if watcher.callback is not None:
        raise ConcurrentObjectUseError('This socket is already used by another greenlet: %r'
                                       % (watcher.callback, ))

    if hub is None:
        hub = get_hub()

    if timeout is None:
        hub.wait(watcher)
        return

    timeout = Timeout._start_new_or_dummy(
        timeout,
        (timeout_exc
         if timeout_exc is not _NONE or timeout is None
         else _timeout_error('timed out')))

    with timeout:
        hub.wait(watcher)

# Suitable to be bound as an instance method
def wait_on_socket(socket, watcher, timeout_exc=None):
    if socket is None or watcher is None:
        # test__hub TestCloseSocketWhilePolling, on Python 2; Python 3
        # catches the EBADF differently.
        raise ConcurrentObjectUseError("The socket has already been closed by another greenlet")
    _primitive_wait(watcher, socket.timeout,
                    timeout_exc if timeout_exc is not None else _NONE,
                    socket.hub)

def wait_on_watcher(watcher, timeout=None, timeout_exc=_NONE, hub=None):
    """
    wait(watcher, timeout=None, [timeout_exc=None]) -> None

    Block the current greenlet until *watcher* is ready.

    If *timeout* is non-negative, then *timeout_exc* is raised after
    *timeout* second has passed.

    If :func:`cancel_wait` is called on *io* by another greenlet,
    raise an exception in this blocking greenlet
    (``socket.error(EBADF, 'File descriptor was closed in another
    greenlet')`` by default).

    :param io: An event loop watcher, most commonly an IO watcher obtained from
        :meth:`gevent.core.loop.io`
    :keyword timeout_exc: The exception to raise if the timeout expires.
        By default, a :class:`socket.timeout` exception is raised.
        If you pass a value for this keyword, it is interpreted as for
        :class:`gevent.timeout.Timeout`.

    :raises ~gevent.hub.ConcurrentObjectUseError: If the *watcher* is
        already started.
    """
    _primitive_wait(watcher, timeout, timeout_exc, hub)


def wait_read(fileno, timeout=None, timeout_exc=_NONE):
    """
    wait_read(fileno, timeout=None, [timeout_exc=None]) -> None

    Block the current greenlet until *fileno* is ready to read.

    For the meaning of the other parameters and possible exceptions,
    see :func:`wait`.

    .. seealso:: :func:`cancel_wait`
    """
    hub = get_hub()
    io = hub.loop.io(fileno, 1)
    try:
        return wait_on_watcher(io, timeout, timeout_exc, hub)
    finally:
        io.close()


def wait_write(fileno, timeout=None, timeout_exc=_NONE, event=_NONE):
    """
    wait_write(fileno, timeout=None, [timeout_exc=None]) -> None

    Block the current greenlet until *fileno* is ready to write.

    For the meaning of the other parameters and possible exceptions,
    see :func:`wait`.

    .. deprecated:: 1.1
       The keyword argument *event* is ignored. Applications should not pass this parameter.
       In the future, doing so will become an error.

    .. seealso:: :func:`cancel_wait`
    """
    # pylint:disable=unused-argument
    hub = get_hub()
    io = hub.loop.io(fileno, 2)
    try:
        return wait_on_watcher(io, timeout, timeout_exc, hub)
    finally:
        io.close()


def wait_readwrite(fileno, timeout=None, timeout_exc=_NONE, event=_NONE):
    """
    wait_readwrite(fileno, timeout=None, [timeout_exc=None]) -> None

    Block the current greenlet until *fileno* is ready to read or
    write.

    For the meaning of the other parameters and possible exceptions,
    see :func:`wait`.

    .. deprecated:: 1.1
       The keyword argument *event* is ignored. Applications should not pass this parameter.
       In the future, doing so will become an error.

    .. seealso:: :func:`cancel_wait`
    """
    # pylint:disable=unused-argument
    hub = get_hub()
    io = hub.loop.io(fileno, 3)
    try:
        return wait_on_watcher(io, timeout, timeout_exc, hub)
    finally:
        io.close()


def _init():
    greenlet_init() # pylint:disable=undefined-variable

_init()

from gevent._util import import_c_accel
import_c_accel(globals(), 'gevent.__hub_primitives')
