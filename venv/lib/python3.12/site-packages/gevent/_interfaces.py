# -*- coding: utf-8 -*-
# Copyright (c) 2018 gevent contributors. See LICENSE for details.
"""
Interfaces gevent uses that don't belong any one place.

This is not a public module, these interfaces are not
currently exposed to the public, they mostly exist for
documentation and testing purposes.

.. versionadded:: 1.3b2

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys

from zope.interface import Interface
from zope.interface import Attribute

_text_type = type(u'')

try:
    from zope import schema
except ImportError: # pragma: no cover
    class _Field(Attribute):
        __allowed_kw__ = ('readonly', 'min',)
        def __init__(self, description, required=False, **kwargs):
            description = u"%s (required? %s)" % (description, required)
            assert isinstance(description, _text_type)
            for k in self.__allowed_kw__:
                kwargs.pop(k, None)
            if kwargs:
                raise TypeError("Unexpected keyword arguments: %r" % (kwargs,))
            Attribute.__init__(self, description)

    class schema(object):
        Bool = _Field
        Float = _Field


# pylint:disable=no-method-argument, unused-argument, no-self-argument
# pylint:disable=inherit-non-class

__all__ = [
    'ILoop',
    'IWatcher',
    'ICallback',
]

class ILoop(Interface):
    """
    The common interface expected for all event loops.

    .. caution::
       This is an internal, low-level interface. It may change
       between minor versions of gevent.

    .. rubric:: Watchers

    The methods that create event loop watchers are `io`, `timer`,
    `signal`, `idle`, `prepare`, `check`, `fork`, `async_`, `child`,
    `stat`. These all return various types of :class:`IWatcher`.

    All of those methods have one or two common arguments. *ref* is a
    boolean saying whether the event loop is allowed to exit even if
    this watcher is still started. *priority* is event loop specific.
    """

    default = schema.Bool(
        description=u"Boolean indicating whether this is the default loop",
        required=True,
        readonly=True,
    )

    approx_timer_resolution = schema.Float(
        description=u"Floating point number of seconds giving (approximately) the minimum "
        "resolution of a timer (and hence the minimun value the sleep can sleep for). "
        "On libuv, this is fixed by the library, but on libev it is just a guess "
        "and the actual value is system dependent.",
        required=True,
        min=0.0,
        readonly=True,
    )

    def run(nowait=False, once=False):
        """
        Run the event loop.

        This is usually called automatically by the hub greenlet, but
        in special cases (when the hub is *not* running) you can use
        this to control how the event loop runs (for example, to integrate
        it with another event loop).
        """

    def now():
        """
        now() -> float

        Return the loop's notion of the current time.

        This may not necessarily be related to :func:`time.time` (it
        may have a different starting point), but it must be expressed
        in fractional seconds (the same *units* used by :func:`time.time`).
        """

    def update_now():
        """
        Update the loop's notion of the current time.

        .. versionadded:: 1.3
           In the past, this available as ``update``. This is still available as
           an alias but will be removed in the future.
        """

    def destroy():
        """
        Clean up resources used by this loop.

        If you create loops
        (especially loops that are not the default) you *should* call
        this method when you are done with the loop.

        .. caution::

            As an implementation note, the libev C loop implementation has a
            finalizer (``__del__``) that destroys the object, but the libuv
            and libev CFFI implementations do not. The C implementation may change.

        """

    def io(fd, events, ref=True, priority=None):
        """
        Create and return a new IO watcher for the given *fd*.

        *events* is a bitmask specifying which events to watch
        for. 1 means read, and 2 means write.
        """

    def closing_fd(fd):
        """
        Inform the loop that the file descriptor *fd* is about to be closed.

        The loop may choose to schedule events to be delivered to any active
        IO watchers for the fd. libev does this so that the active watchers
        can be closed.

        :return: A boolean value that's true if active IO watchers were
           queued to run. Closing the FD should be deferred until the next
           run of the eventloop with a callback.
        """

    def timer(after, repeat=0.0, ref=True, priority=None):
        """
        Create and return a timer watcher that will fire after *after* seconds.

        If *repeat* is given, the timer will continue to fire every *repeat* seconds.
        """

    def signal(signum, ref=True, priority=None):
        """
        Create and return a signal watcher for the signal *signum*,
        one of the constants defined in :mod:`signal`.

        This is platform and event loop specific.
        """

    def idle(ref=True, priority=None):
        """
        Create and return a watcher that fires when the event loop is idle.
        """

    def prepare(ref=True, priority=None):
        """
        Create and return a watcher that fires before the event loop
        polls for IO.

        .. caution:: This method is not supported by libuv.
        """

    def check(ref=True, priority=None):
        """
        Create and return a watcher that fires after the event loop
        polls for IO.
        """

    def fork(ref=True, priority=None):
        """
        Create a watcher that fires when the process forks.

        Availability: Unix.
        """

    def async_(ref=True, priority=None):
        """
        Create a watcher that fires when triggered, possibly
        from another thread.

        .. versionchanged:: 1.3
           This was previously just named ``async``; for compatibility
           with Python 3.7 where ``async`` is a keyword it was renamed.
           On older versions of Python the old name is still around, but
           it will be removed in the future.
        """

    if sys.platform != "win32":

        def child(pid, trace=0, ref=True):
            """
            Create a watcher that fires for events on the child with process ID *pid*.

            This is platform specific and not available on Windows.

            Availability: Unix.
            """

    def stat(path, interval=0.0, ref=True, priority=None):
        """
        Create a watcher that monitors the filesystem item at *path*.

        If the operating system doesn't support event notifications
        from the filesystem, poll for changes every *interval* seconds.
        """

    def run_callback(func, *args):
        """
        Run the *func* passing it *args* at the next opportune moment.

        The next opportune moment may be the next iteration of the event loop,
        the current iteration, or some other time in the future.

        Returns a :class:`ICallback` object. See that documentation for
        important caveats.

        .. seealso:: :meth:`asyncio.loop.call_soon`
           The :mod:`asyncio` equivalent.
        """

    def run_callback_threadsafe(func, *args):
        """
        Like :meth:`run_callback`, but for use from *outside* the
        thread that is running this loop.

        This not only schedules the *func* to run, it also causes the
        loop to notice that the *func* has been scheduled (e.g., it causes
        the loop to wake up).

        .. versionadded:: 21.1.0

        .. seealso:: :meth:`asyncio.loop.call_soon_threadsafe`
           The :mod:`asyncio` equivalent.
        """

class IWatcher(Interface):
    """
    An event loop watcher.

    These objects call their *callback* function when the event
    loop detects the event has happened.

    .. important:: You *must* call :meth:`close` when you are
       done with this object to avoid leaking native resources.
    """

    def start(callback, *args, **kwargs):
        """
        Have the event loop begin watching for this event.

        When the event is detected, *callback* will be called with
        *args*.

        .. caution::

            Not all watchers accept ``**kwargs``,
            and some watchers define special meanings for certain keyword args.
        """

    def stop():
        """
        Have the event loop stop watching this event.

        In the future you may call :meth:`start` to begin watching
        again.
        """

    def close():
        """
        Dispose of any native resources associated with the watcher.

        If we were active, stop.

        Attempting to operate on this object after calling close is
        undefined. You should dispose of any references you have to it
        after calling this method.
        """

class ICallback(Interface):
    """
    Represents a function that will be run some time in the future.

    Callback functions run in the hub, and as such they cannot use
    gevent's blocking API; any exception they raise cannot be caught.
    """

    pending = schema.Bool(description=u"Has this callback run yet?",
                          readonly=True)

    def stop():
        """
        If this object is still `pending`, cause it to
        no longer be `pending`; the function will not be run.
        """

    def close():
        """
        An alias of `stop`.
        """
