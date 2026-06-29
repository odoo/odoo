# Copyright (c) 2009-2016 Denis Bilenko, gevent contributors. See LICENSE for details.
# cython: auto_pickle=False,embedsignature=True,always_allow_keywords=False,infer_types=True

"""Basic synchronization primitives: Event and AsyncResult"""
from __future__ import print_function

from gevent._util import _NONE
from gevent._compat import reraise
from gevent._tblib import dump_traceback, load_traceback

from gevent.timeout import Timeout


__all__ = [
    'Event',
    'AsyncResult',
]

def _get_linkable():
    x = __import__('gevent._abstract_linkable')
    return x._abstract_linkable.AbstractLinkable
locals()['AbstractLinkable'] = _get_linkable()
del _get_linkable


class Event(AbstractLinkable): # pylint:disable=undefined-variable
    """
    A synchronization primitive that allows one greenlet to wake up
    one or more others. It has the same interface as
    :class:`threading.Event` but works across greenlets.

    .. important::
       This object is for communicating among greenlets within the
       same thread *only*! Do not try to use it to communicate across threads.

    An event object manages an internal flag that can be set to true
    with the :meth:`set` method and reset to false with the
    :meth:`clear` method. The :meth:`wait` method blocks until the
    flag is true; as soon as the flag is set to true, all greenlets
    that are currently blocked in a call to :meth:`wait` will be scheduled
    to awaken.

    Note that the flag may be cleared and set many times before
    any individual greenlet runs; all the greenlet can know for sure is that the
    flag was set *at least once* while it was waiting.
    If the greenlet cares whether the flag is still
    set, it must check with :meth:`ready` and possibly call back into
    :meth:`wait` again.

    .. note::

        The exact order and timing in which waiting greenlets are awakened is not determined.

        Once the event is set, other greenlets may run before any waiting greenlets
        are awakened.

        While the code here will awaken greenlets in the order in which they
        waited, each such greenlet that runs may in turn cause other greenlets
        to run.

        These details may change in the future.

    .. versionchanged:: 1.5a3

        Waiting greenlets are now awakened in
        the order in which they waited.

    .. versionchanged:: 1.5a3

        The low-level ``rawlink`` method (most users won't use this) now
        automatically unlinks waiters before calling them.

    .. versionchanged:: 20.5.1

        Callers to ``wait`` that find the event already set will now run
        after any other waiters that had to block. See :issue:`1520`.
    """

    __slots__ = ('_flag',)

    def __init__(self):
        super(Event, self).__init__()
        self._flag = False

    def __str__(self):
        return '<%s %s _links[%s]>' % (
            self.__class__.__name__,
            'set' if self._flag else 'clear',
            self.linkcount()
        )

    def is_set(self):
        """Return true if and only if the internal flag is true."""
        return self._flag

    def isSet(self):
        # makes it a better drop-in replacement for threading.Event
        return self._flag

    def ready(self):
        # makes it compatible with AsyncResult and Greenlet (for
        # example in wait())
        return self._flag

    def set(self):
        """
        Set the internal flag to true.

        All greenlets waiting for it to become true are awakened in
        some order at some time in the future. Greenlets that call
        :meth:`wait` once the flag is true will not block at all
        (until :meth:`clear` is called).
        """
        self._flag = True
        self._check_and_notify()

    def clear(self):
        """
        Reset the internal flag to false.

        Subsequently, threads calling :meth:`wait` will block until
        :meth:`set` is called to set the internal flag to true again.
        """
        self._flag = False

    def _wait_return_value(self, waited, wait_success):
        # To avoid the race condition outlined in http://bugs.python.org/issue13502,
        # if we had to wait, then we need to return whether or not
        # the condition got changed. Otherwise we simply echo
        # the current state of the flag (which should be true)
        if not waited:
            flag = self._flag
            assert flag, "if we didn't wait we should already be set"
            return flag

        return wait_success

    def wait(self, timeout=None):
        """
        Block until this object is :meth:`ready`.

        If the internal flag is true on entry, return immediately. Otherwise,
        block until another thread (greenlet) calls :meth:`set` to set the flag to true,
        or until the optional *timeout* expires.

        When the *timeout* argument is present and not ``None``, it should be a
        floating point number specifying a timeout for the operation in seconds
        (or fractions thereof).

        :return: This method returns true if and only if the internal flag has been set to
            true, either before the wait call or after the wait starts, so it will
            always return ``True`` except if a timeout is given and the operation
            times out.

        .. versionchanged:: 1.1
            The return value represents the flag during the elapsed wait, not
            just after it elapses. This solves a race condition if one greenlet
            sets and then clears the flag without switching, while other greenlets
            are waiting. When the waiters wake up, this will return True; previously,
            they would still wake up, but the return value would be False. This is most
            noticeable when the *timeout* is present.
        """
        return self._wait(timeout)

    def _reset_internal_locks(self): # pragma: no cover
        # for compatibility with threading.Event
        #  Exception AttributeError: AttributeError("'Event' object has no attribute '_reset_internal_locks'",)
        # in <module 'threading' from '/usr/lib/python2.7/threading.pyc'> ignored
        pass


class AsyncResult(AbstractLinkable): # pylint:disable=undefined-variable
    """
    A one-time event that stores a value or an exception.

    Like :class:`Event` it wakes up all the waiters when :meth:`set`
    or :meth:`set_exception` is called. Waiters may receive the passed
    value or exception by calling :meth:`get` instead of :meth:`wait`.
    An :class:`AsyncResult` instance cannot be reset.

    .. important::
       This object is for communicating among greenlets within the
       same thread *only*! Do not try to use it to communicate across threads.

    To pass a value call :meth:`set`. Calls to :meth:`get` (those that
    are currently blocking as well as those made in the future) will
    return the value::

        >>> from gevent.event import AsyncResult
        >>> result = AsyncResult()
        >>> result.set(100)
        >>> result.get()
        100

    To pass an exception call :meth:`set_exception`. This will cause
    :meth:`get` to raise that exception::

        >>> result = AsyncResult()
        >>> result.set_exception(RuntimeError('failure'))
        >>> result.get()
        Traceback (most recent call last):
         ...
        RuntimeError: failure

    :class:`AsyncResult` implements :meth:`__call__` and thus can be
    used as :meth:`link` target::

        >>> import gevent
        >>> result = AsyncResult()
        >>> gevent.spawn(lambda : 1/0).link(result)
        >>> try:
        ...     result.get()
        ... except ZeroDivisionError:
        ...     print('ZeroDivisionError')
        ZeroDivisionError

    .. note::

        The order and timing in which waiting greenlets are awakened is not determined.
        As an implementation note, in gevent 1.1 and 1.0, waiting greenlets are awakened in a
        undetermined order sometime *after* the current greenlet yields to the event loop. Other greenlets
        (those not waiting to be awakened) may run between the current greenlet yielding and
        the waiting greenlets being awakened. These details may change in the future.

    .. versionchanged:: 1.1

       The exact order in which waiting greenlets
       are awakened is not the same as in 1.0.

    .. versionchanged:: 1.1

       Callbacks :meth:`linked <rawlink>` to this object are required to
       be hashable, and duplicates are merged.

    .. versionchanged:: 1.5a3

       Waiting greenlets are now awakened in the order in which they
       waited.

    .. versionchanged:: 1.5a3

       The low-level ``rawlink`` method
       (most users won't use this) now automatically unlinks waiters
       before calling them.
    """

    __slots__ = ('_value', '_exc_info', '_imap_task_index')

    def __init__(self):
        super(AsyncResult, self).__init__()
        self._value = _NONE
        self._exc_info = ()

    @property
    def _exception(self):
        return self._exc_info[1] if self._exc_info else _NONE

    @property
    def value(self):
        """
        Holds the value passed to :meth:`set` if :meth:`set` was called. Otherwise,
        ``None``
        """
        return self._value if self._value is not _NONE else None

    @property
    def exc_info(self):
        """
        The three-tuple of exception information if :meth:`set_exception` was called.
        """
        if self._exc_info:
            return (self._exc_info[0], self._exc_info[1], load_traceback(self._exc_info[2]))
        return ()

    def __str__(self):
        result = '<%s ' % (self.__class__.__name__, )
        if self.value is not None or self._exception is not _NONE:
            result += 'value=%r ' % self.value
        if self._exception is not None and self._exception is not _NONE:
            result += 'exception=%r ' % self._exception
        if self._exception is _NONE:
            result += 'unset '
        return result + ' _links[%s]>' % self.linkcount()

    def ready(self):
        """Return true if and only if it holds a value or an exception"""
        return self._exc_info or self._value is not _NONE

    def successful(self):
        """Return true if and only if it is ready and holds a value"""
        return self._value is not _NONE

    @property
    def exception(self):
        """Holds the exception instance passed to :meth:`set_exception` if :meth:`set_exception` was called.
        Otherwise ``None``."""
        if self._exc_info:
            return self._exc_info[1]

    def set(self, value=None):
        """Store the value and wake up any waiters.

        All greenlets blocking on :meth:`get` or :meth:`wait` are awakened.
        Subsequent calls to :meth:`wait` and :meth:`get` will not block at all.
        """
        self._value = value
        self._check_and_notify()

    def set_exception(self, exception, exc_info=None):
        """Store the exception and wake up any waiters.

        All greenlets blocking on :meth:`get` or :meth:`wait` are awakened.
        Subsequent calls to :meth:`wait` and :meth:`get` will not block at all.

        :keyword tuple exc_info: If given, a standard three-tuple of type, value, :class:`traceback`
            as returned by :func:`sys.exc_info`. This will be used when the exception
            is re-raised to propagate the correct traceback.
        """
        if exc_info:
            self._exc_info = (exc_info[0], exc_info[1], dump_traceback(exc_info[2]))
        else:
            self._exc_info = (type(exception), exception, dump_traceback(None))

        self._check_and_notify()

    def _raise_exception(self):
        reraise(*self.exc_info)

    def get(self, block=True, timeout=None):
        """Return the stored value or raise the exception.

        If this instance already holds a value or an exception, return  or raise it immediately.
        Otherwise, block until another greenlet calls :meth:`set` or :meth:`set_exception` or
        until the optional timeout occurs.

        When the *timeout* argument is present and not ``None``, it should be a
        floating point number specifying a timeout for the operation in seconds
        (or fractions thereof). If the *timeout* elapses, the *Timeout* exception will
        be raised.

        :keyword bool block: If set to ``False`` and this instance is not ready,
            immediately raise a :class:`Timeout` exception.
        """
        if self._value is not _NONE:
            return self._value
        if self._exc_info:
            return self._raise_exception()

        if not block:
            # Not ready and not blocking, so immediately timeout
            raise Timeout()

        self._capture_hub(True)

        # Wait, raising a timeout that elapses
        self._wait_core(timeout, ())

        # by definition we are now ready
        return self.get(block=False)

    def get_nowait(self):
        """
        Return the value or raise the exception without blocking.

        If this object is not yet :meth:`ready <ready>`, raise
        :class:`gevent.Timeout` immediately.
        """
        return self.get(block=False)

    def _wait_return_value(self, waited, wait_success):
        # pylint:disable=unused-argument
        # Always return the value. Since this is a one-shot event,
        # no race condition should reset it.
        return self.value

    def wait(self, timeout=None):
        """Block until the instance is ready.

        If this instance already holds a value, it is returned immediately. If this
        instance already holds an exception, ``None`` is returned immediately.

        Otherwise, block until another greenlet calls :meth:`set` or :meth:`set_exception`
        (at which point either the value or ``None`` will be returned, respectively),
        or until the optional timeout expires (at which point ``None`` will also be
        returned).

        When the *timeout* argument is present and not ``None``, it should be a
        floating point number specifying a timeout for the operation in seconds
        (or fractions thereof).

        .. note:: If a timeout is given and expires, ``None`` will be returned
            (no timeout exception will be raised).

        """
        return self._wait(timeout)

    # link protocol
    def __call__(self, source):
        if source.successful():
            self.set(source.value)
        else:
            self.set_exception(source.exception, getattr(source, 'exc_info', None))

    # Methods to make us more like concurrent.futures.Future

    def result(self, timeout=None):
        return self.get(timeout=timeout)

    set_result = set

    def done(self):
        return self.ready()

    # we don't support cancelling

    def cancel(self):
        return False

    def cancelled(self):
        return False

    # exception is a method, we use it as a property


from gevent._util import import_c_accel
import_c_accel(globals(), 'gevent._event')
