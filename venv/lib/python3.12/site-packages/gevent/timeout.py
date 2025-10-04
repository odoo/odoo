# Copyright (c) 2009-2010 Denis Bilenko. See LICENSE for details.
"""
Timeouts.

Many functions in :mod:`gevent` have a *timeout* argument that allows
limiting the time the function will block. When that is not available,
the :class:`Timeout` class and :func:`with_timeout` function in this
module add timeouts to arbitrary code.

.. warning::

    Timeouts can only work when the greenlet switches to the hub.
    If a blocking function is called or an intense calculation is ongoing during
    which no switches occur, :class:`Timeout` is powerless.
"""
from __future__ import absolute_import, print_function, division

from gevent._compat import string_types
from gevent._util import _NONE

from greenlet import getcurrent
from gevent._hub_local import get_hub_noargs as get_hub

__all__ = [
    'Timeout',
    'with_timeout',
]


class _FakeTimer(object):
    # An object that mimics the API of get_hub().loop.timer, but
    # without allocating any native resources. This is useful for timeouts
    # that will never expire.
    # Also partially mimics the API of Timeout itself for use in _start_new_or_dummy

    # This object is used as a singleton, so it should be
    # immutable.
    __slots__ = ()

    @property
    def pending(self):
        return False

    active = pending

    @property
    def seconds(self):
        "Always returns None"

    timer = exception = seconds

    def start(self, *args, **kwargs):
        # pylint:disable=unused-argument
        raise AssertionError("non-expiring timer cannot be started")

    def stop(self):
        return

    cancel = stop

    stop = close = cancel

    def __enter__(self):
        return self

    def __exit__(self, _t, _v, _tb):
        return

_FakeTimer = _FakeTimer()


class Timeout(BaseException):
    """
    Timeout(seconds=None, exception=None, ref=True, priority=-1)

    Raise *exception* in the current greenlet after *seconds*
    have elapsed::

        timeout = Timeout(seconds, exception)
        timeout.start()
        try:
            ...  # exception will be raised here, after *seconds* passed since start() call
        finally:
            timeout.close()

    .. warning::

        You must **always** call `close` on a ``Timeout`` object you have created,
        whether or not the code that the timeout was protecting finishes
        executing before the timeout elapses (whether or not the
        ``Timeout`` exception is raised)  This ``try/finally``
        construct or a ``with`` statement is a good pattern. (If
        the timeout object will be started again, use `cancel` instead
        of `close`; this is rare. You must still `close` it when you are
        done.)

    When *exception* is omitted or ``None``, the ``Timeout`` instance
    itself is raised::

        >>> import gevent
        >>> gevent.Timeout(0.1).start()
        >>> gevent.sleep(0.2)  #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
         ...
        Timeout: 0.1 seconds

    If the *seconds* argument is not given or is ``None`` (e.g.,
    ``Timeout()``), then the timeout will never expire and never raise
    *exception*. This is convenient for creating functions which take
    an optional timeout parameter of their own. (Note that this is **not**
    the same thing as a *seconds* value of ``0``.)

    ::

       def function(args, timeout=None):
          "A function with an optional timeout."
          timer = Timeout(timeout)
          with timer:
             ...

    .. caution::

        A *seconds* value less than ``0.0`` (e.g., ``-1``) is poorly defined. In the future,
        support for negative values is likely to do the same thing as a value
        of ``None`` or ``0``

    A *seconds* value of ``0`` requests that the event loop spin and poll for I/O;
    it will immediately expire as soon as control returns to the event loop.

    .. rubric:: Use As A Context Manager

    To simplify starting and canceling timeouts, the ``with``
    statement can be used::

        with gevent.Timeout(seconds, exception) as timeout:
            pass  # ... code block ...

    This is equivalent to the try/finally block above with one
    additional feature: if *exception* is the literal ``False``, the
    timeout is still raised, but the context manager suppresses it, so
    the code outside the with-block won't see it.

    This is handy for adding a timeout to the functions that don't
    support a *timeout* parameter themselves::

        data = None
        with gevent.Timeout(5, False):
            data = mysock.makefile().readline()
        if data is None:
            ...  # 5 seconds passed without reading a line
        else:
            ...  # a line was read within 5 seconds

    .. caution::

        If ``readline()`` above catches and doesn't re-raise
        :exc:`BaseException` (for example, with a bare ``except:``), then
        your timeout will fail to function and control won't be returned
        to you when you expect.

    .. rubric:: Catching Timeouts

    When catching timeouts, keep in mind that the one you catch may
    not be the one you have set (a calling function may have set its
    own timeout); if you going to silence a timeout, always check that
    it's the instance you need::

        timeout = Timeout(1)
        timeout.start()
        try:
            ...
        except Timeout as t:
            if t is not timeout:
                raise # not my timeout
        finally:
            timeout.close()


    .. versionchanged:: 1.1b2

        If *seconds* is not given or is ``None``, no longer allocate a
        native timer object that will never be started.

    .. versionchanged:: 1.1

        Add warning about negative *seconds* values.

    .. versionchanged:: 1.3a1

        Timeout objects now have a :meth:`close`
        method that *must* be called when the timeout will no longer be
        used to properly clean up native resources.
        The ``with`` statement does this automatically.

    """

    # We inherit a __dict__ from BaseException, so __slots__ actually
    # makes us larger.

    def __init__(self, seconds=None, exception=None, ref=True, priority=-1,
                 _one_shot=False):
        BaseException.__init__(self)
        self.seconds = seconds
        self.exception = exception
        self._one_shot = _one_shot
        if seconds is None:
            # Avoid going through the timer codepath if no timeout is
            # desired; this avoids some CFFI interactions on PyPy that can lead to a
            # RuntimeError if this implementation is used during an `import` statement. See
            # https://bitbucket.org/pypy/pypy/issues/2089/crash-in-pypy-260-linux64-with-gevent-11b1
            # and https://github.com/gevent/gevent/issues/618.
            # Plus, in general, it should be more efficient

            self.timer = _FakeTimer
        else:
            # XXX: A timer <= 0 could cause libuv to block the loop; we catch
            # that case in libuv/loop.py
            self.timer = get_hub().loop.timer(seconds or 0.0, ref=ref, priority=priority)

    def start(self):
        """Schedule the timeout."""
        if self.pending:
            raise AssertionError('%r is already started; to restart it, cancel it first' % self)

        if self.seconds is None:
            # "fake" timeout (never expires)
            return

        if self.exception is None or self.exception is False or isinstance(self.exception, string_types):
            # timeout that raises self
            throws = self
        else:
            # regular timeout with user-provided exception
            throws = self.exception

        # Make sure the timer updates the current time so that we don't
        # expire prematurely.
        self.timer.start(self._on_expiration, getcurrent(), throws, update=True)

    def _on_expiration(self, prev_greenlet, ex):
        # Hook for subclasses.
        prev_greenlet.throw(ex)

    @classmethod
    def start_new(cls, timeout=None, exception=None, ref=True, _one_shot=False):
        """Create a started :class:`Timeout`.

        This is a shortcut, the exact action depends on *timeout*'s type:

        * If *timeout* is a :class:`Timeout`, then call its :meth:`start` method
          if it's not already begun.
        * Otherwise, create a new :class:`Timeout` instance, passing (*timeout*, *exception*) as
          arguments, then call its :meth:`start` method.

        Returns the :class:`Timeout` instance.
        """
        if isinstance(timeout, Timeout):
            if not timeout.pending:
                timeout.start()
            return timeout
        timeout = cls(timeout, exception, ref=ref, _one_shot=_one_shot)
        timeout.start()
        return timeout

    @staticmethod
    def _start_new_or_dummy(timeout, exception=None, ref=True):
        # Internal use only in 1.1
        # Return an object with a 'cancel' method; if timeout is None,
        # this will be a shared instance object that does nothing. Otherwise,
        # return an actual Timeout. A 0 value is allowed and creates a real Timeout.

        # Because negative values are hard to reason about,
        # and are often used as sentinels in Python APIs, in the future it's likely
        # that a negative timeout will also return the shared instance.
        # This saves the previously common idiom of
        # 'timer = Timeout.start_new(t) if t is not None else None'
        # followed by 'if timer is not None: timer.cancel()'.
        # That idiom was used to avoid any object allocations.

        # A staticmethod is slightly faster under CPython, compared to a classmethod;
        # under PyPy in synthetic benchmarks it makes no difference.
        if timeout is None:
            return _FakeTimer
        return Timeout.start_new(timeout, exception, ref, _one_shot=True)

    @property
    def pending(self):
        """True if the timeout is scheduled to be raised."""
        return self.timer.pending or self.timer.active

    def cancel(self):
        """
        If the timeout is pending, cancel it. Otherwise, do nothing.

        The timeout object can be :meth:`started <start>` again. If
        you will not start the timeout again, you should use
        :meth:`close` instead.
        """
        self.timer.stop()
        if self._one_shot:
            self.close()

    def close(self):
        """
        Close the timeout and free resources. The timer cannot be started again
        after this method has been used.
        """
        self.timer.stop()
        self.timer.close()
        self.timer = _FakeTimer

    def __repr__(self):
        classname = type(self).__name__
        if self.pending:
            pending = ' pending'
        else:
            pending = ''
        if self.exception is None:
            exception = ''
        else:
            exception = ' exception=%r' % self.exception
        return '<%s at %s seconds=%s%s%s>' % (classname, hex(id(self)), self.seconds, exception, pending)

    def __str__(self):
        """
        >>> raise Timeout #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
            ...
        Timeout
        """
        if self.seconds is None:
            return ''

        suffix = '' if self.seconds == 1 else 's'

        if self.exception is None:
            return '%s second%s' % (self.seconds, suffix)
        if self.exception is False:
            return '%s second%s (silent)' % (self.seconds, suffix)
        return '%s second%s: %s' % (self.seconds, suffix, self.exception)

    def __enter__(self):
        """
        Start and return the timer. If the timer is already started, just return it.
        """
        if not self.pending:
            self.start()
        return self

    def __exit__(self, typ, value, tb):
        """
        Stop the timer.

        .. versionchanged:: 1.3a1
           The underlying native timer is also stopped. This object cannot be
           used again.
        """
        self.close()
        if value is self and self.exception is False:
            return True # Suppress the exception


def with_timeout(seconds, function, *args, **kwds):
    """Wrap a call to *function* with a timeout; if the called
    function fails to return before the timeout, cancel it and return a
    flag value, provided by *timeout_value* keyword argument.

    If timeout expires but *timeout_value* is not provided, raise :class:`Timeout`.

    Keyword argument *timeout_value* is not passed to *function*.
    """
    timeout_value = kwds.pop("timeout_value", _NONE)
    timeout = Timeout.start_new(seconds, _one_shot=True)
    try:
        try:
            return function(*args, **kwds)
        except Timeout as ex:
            if ex is timeout and timeout_value is not _NONE:
                return timeout_value
            raise
    finally:
        timeout.cancel()
