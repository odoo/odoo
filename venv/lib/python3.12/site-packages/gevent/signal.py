"""
Cooperative implementation of special cases of :func:`signal.signal`.

This module is designed to work with libev's child watchers, as used
by default in :func:`gevent.os.fork` Note that each ``SIGCHLD``
handler will be run in a new greenlet when the signal is delivered
(just like :class:`gevent.hub.signal`)

The implementations in this module are only monkey patched if
:func:`gevent.os.waitpid` is being used (the default) and if
:const:`signal.SIGCHLD` is available; see :func:`gevent.os.fork` for
information on configuring this not to be the case for advanced uses.

.. versionadded:: 1.1b4
.. versionchanged:: 1.5a4
   Previously there was a backwards compatibility alias
   ``gevent.signal``, introduced in 1.1b4, that partly shadowed this
   module, confusing humans and static analysis tools alike. That alias
   has been removed. (See `gevent.signal_handler`.)
"""

from __future__ import absolute_import

from gevent._util import _NONE as _INITIAL
from gevent._util import copy_globals

import signal as _signal

__implements__ = []
__extensions__ = []


_child_handler = _INITIAL

_signal_signal = _signal.signal
_signal_getsignal = _signal.getsignal


def getsignal(signalnum):
    """
    Exactly the same as :func:`signal.getsignal` except where
    :const:`signal.SIGCHLD` is concerned.

    For :const:`signal.SIGCHLD`, this cooperates with :func:`signal`
    to provide consistent answers.
    """
    if signalnum != _signal.SIGCHLD:
        return _signal_getsignal(signalnum)

    global _child_handler
    if _child_handler is _INITIAL:
        _child_handler = _signal_getsignal(_signal.SIGCHLD)

    return _child_handler


def signal(signalnum, handler):
    """
    Exactly the same as :func:`signal.signal` except where
    :const:`signal.SIGCHLD` is concerned.

    .. note::

       A :const:`signal.SIGCHLD` handler installed with this function
       will only be triggered for children that are forked using
       :func:`gevent.os.fork` (:func:`gevent.os.fork_and_watch`);
       children forked before monkey patching, or otherwise by the raw
       :func:`os.fork`, will not trigger the handler installed by this
       function. (It's unlikely that a SIGCHLD handler installed with
       the builtin :func:`signal.signal` would be triggered either;
       libev typically overwrites such a handler at the C level. At
       the very least, it's full of race conditions.)

    .. note::

        Use of ``SIG_IGN`` and ``SIG_DFL`` may also have race conditions
        with libev child watchers and the :mod:`gevent.subprocess` module.

    .. versionchanged:: 1.2a1
         If ``SIG_IGN`` or ``SIG_DFL`` are used to ignore ``SIGCHLD``, a
         future use of ``gevent.subprocess`` and libev child watchers
         will once again work. However, on Python 2, use of ``os.popen``
         will fail.

    .. versionchanged:: 1.1rc2
         Allow using ``SIG_IGN`` and ``SIG_DFL`` to reset and ignore ``SIGCHLD``.
         However, this allows the possibility of a race condition if ``gevent.subprocess``
         had already been used.
    """
    if signalnum != _signal.SIGCHLD:
        return _signal_signal(signalnum, handler)

    # TODO: raise value error if not called from the main
    # greenlet, just like threads

    if handler != _signal.SIG_IGN and handler != _signal.SIG_DFL and not callable(handler):
        # exact same error message raised by the stdlib
        raise TypeError("signal handler must be signal.SIG_IGN, signal.SIG_DFL, or a callable object")

    old_handler = getsignal(signalnum)
    global _child_handler
    _child_handler = handler
    if handler in (_signal.SIG_IGN, _signal.SIG_DFL):
        # Allow resetting/ignoring this signal at the process level.
        # Note that this conflicts with gevent.subprocess and other users
        # of child watchers, until the next time gevent.subprocess/loop.install_sigchld()
        # is called.
        from gevent.hub import get_hub # Are we always safe to import here?
        _signal_signal(signalnum, handler)
        get_hub().loop.reset_sigchld()
    return old_handler


def _on_child_hook():
    # This is called in the hub greenlet. To let the function
    # do more useful work, like use blocking functions,
    # we run it in a new greenlet; see gevent.hub.signal
    if callable(_child_handler):
        # None is a valid value for the frame argument
        from gevent import Greenlet
        greenlet = Greenlet(_child_handler, _signal.SIGCHLD, None)
        greenlet.switch()


import gevent.os

if 'waitpid' in gevent.os.__implements__ and hasattr(_signal, 'SIGCHLD'):
    # Tightly coupled here to gevent.os and its waitpid implementation; only use these
    # if necessary.
    gevent.os._on_child_hook = _on_child_hook
    __implements__.append("signal")
    __implements__.append("getsignal")
else:
    # XXX: This breaks test__all__ on windows
    __extensions__.append("signal")
    __extensions__.append("getsignal")

__imports__ = copy_globals(_signal, globals(),
                           names_to_ignore=__implements__ + __extensions__,
                           dunder_names_to_keep=())

__all__ = __implements__ + __extensions__
