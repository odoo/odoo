# -*- coding: utf-8 -*-
# copyright 2018 gevent
"""
Exceptions.

.. versionadded:: 1.3b1

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from greenlet import GreenletExit

__all__ = [
    'LoopExit',
]


class LoopExit(Exception):
    """
    Exception thrown when the hub finishes running (`gevent.hub.Hub.run`
    would return).

    In a normal application, this is never thrown or caught
    explicitly. The internal implementation of functions like
    :meth:`gevent.hub.Hub.join` and :func:`gevent.joinall` may catch it, but user code
    generally should not.

    .. caution::
       Errors in application programming can also lead to this exception being
       raised. Some examples include (but are not limited too):

       - greenlets deadlocking on a lock;
       - using a socket or other gevent object with native thread
         affinity from a different thread

    """

    @property
    def hub(self):
        """
        The (optional) hub that raised the error.

        .. versionadded:: 20.12.0
        """
        # XXX: Note that semaphore.py does this manually.
        if len(self.args) == 3: # From the hub
            return self.args[1]

    def __repr__(self):
        # pylint:disable=unsubscriptable-object
        if len(self.args) == 3: # From the hub
            import pprint
            return (
                "%s\n"
                "\tHub: %s\n"
                "\tHandles:\n%s"
            ) % (
                self.args[0],
                self.args[1],
                pprint.pformat(self.args[2])
            )
        return Exception.__repr__(self)

    def __str__(self):
        return repr(self)

class BlockingSwitchOutError(AssertionError):
    """
    Raised when a gevent synchronous function is called from a
    low-level event loop callback.

    This is usually a programming error.
    """


class InvalidSwitchError(AssertionError):
    """
    Raised when the event loop returns control to a greenlet in an
    unexpected way.

    This is usually a bug in gevent, greenlet, or the event loop.
    """

class ConcurrentObjectUseError(AssertionError):
    """
    Raised when an object is used (waited on) by two greenlets
    independently, meaning the object was entered into a blocking
    state by one greenlet and then another while still blocking in the
    first one.

    This is usually a programming error.

    .. seealso:: `gevent.socket.wait`
    """

class InvalidThreadUseError(RuntimeError):
    """
    Raised when an object is used from a different thread than
    the one it is bound to.

    Some objects, such as gevent sockets, semaphores, and threadpools,
    are tightly bound to their hub and its loop. The hub and loop
    are not thread safe, with a few exceptions. Attempting to use
    such objects from a different thread is an error, and may cause
    problems ranging from incorrect results to memory corruption
    and a crashed process.

    In some cases, gevent catches this "accidentally", and the result is
    a `LoopExit`. In some cases, gevent doesn't catch this at all.

    In other cases (typically when the consequences are suspected to
    be more on the more severe end of the scale, and when the operation in
    question is already relatively heavyweight), gevent explicitly checks
    for this usage and will raise this exception when it is detected.

    .. versionadded:: 1.5a3
    """


class HubDestroyed(GreenletExit):
    """
    Internal exception, raised when we're trying to destroy the
    hub and we want the loop to stop running callbacks now.

    This must not be subclassed; the type is tested by identity.

    Clients outside of gevent must not raise this exception.

    .. versionadded:: 20.12.0
    """

    def __init__(self, destroy_loop):
        GreenletExit.__init__(self, destroy_loop)
        self.destroy_loop = destroy_loop
