"""
Low-level operating system functions from :mod:`os`.

Cooperative I/O
===============

This module provides cooperative versions of :func:`os.read` and
:func:`os.write`. These functions are *not* monkey-patched; you
must explicitly call them or monkey patch them yourself.

POSIX functions
---------------

On POSIX, non-blocking IO is available.

- :func:`nb_read`
- :func:`nb_write`
- :func:`make_nonblocking`

All Platforms
-------------

On non-POSIX platforms (e.g., Windows), non-blocking IO is not
available. On those platforms (and on POSIX), cooperative IO can
be done with the threadpool.

- :func:`tp_read`
- :func:`tp_write`

Child Processes
===============

The functions :func:`fork` and (on POSIX) :func:`forkpty` and :func:`waitpid` can be used
to manage child processes.

.. warning::

   Forking a process that uses greenlets does not eliminate all non-running
   greenlets. Any that were scheduled in the hub of the forking thread in the parent
   remain scheduled in the child; compare this to how normal threads operate. (This behaviour
   may change is a subsequent major release.)
"""

from __future__ import absolute_import

import os
import sys
from gevent.hub import _get_hub_noargs as get_hub
from gevent.hub import reinit
from gevent._config import config
from gevent._compat import PY3
from gevent._util import copy_globals
import errno

EAGAIN = getattr(errno, 'EAGAIN', 11)

try:
    import fcntl
except ImportError:
    fcntl = None

__implements__ = ['fork']
__extensions__ = ['tp_read', 'tp_write']

_read = os.read
_write = os.write


ignored_errors = [EAGAIN, errno.EINTR]


if fcntl:

    __extensions__ += ['make_nonblocking', 'nb_read', 'nb_write']

    def make_nonblocking(fd):
        """Put the file descriptor *fd* into non-blocking mode if
        possible.

        :return: A boolean value that evaluates to True if successful.
        """
        flags = fcntl.fcntl(fd, fcntl.F_GETFL, 0)
        if not bool(flags & os.O_NONBLOCK):
            fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
            return True

    def nb_read(fd, n):
        """
        Read up to *n* bytes from file descriptor *fd*. Return a
        byte string containing the bytes read, which may be shorter than
        *n*. If end-of-file is reached, an empty string is returned.

        The descriptor must be in non-blocking mode.
        """
        hub = None
        event = None
        try:
            while 1:
                try:
                    result = _read(fd, n)
                    return result
                except OSError as e:
                    if e.errno not in ignored_errors:
                        raise
                    if not PY3:
                        sys.exc_clear()
                if hub is None:
                    hub = get_hub()
                    event = hub.loop.io(fd, 1)
                hub.wait(event)
        finally:
            if event is not None:
                event.close()
                event = None
                hub = None


    def nb_write(fd, buf):
        """
        Write some number of bytes from buffer *buf* to file
        descriptor *fd*. Return the number of bytes written, which may
        be less than the length of *buf*.

        The file descriptor must be in non-blocking mode.
        """
        hub = None
        event = None
        try:
            while 1:
                try:
                    result = _write(fd, buf)
                    return result
                except OSError as e:
                    if e.errno not in ignored_errors:
                        raise
                    if not PY3:
                        sys.exc_clear()
                if hub is None:
                    hub = get_hub()
                    event = hub.loop.io(fd, 2)
                hub.wait(event)
        finally:
            if event is not None:
                event.close()
                event = None
                hub = None


def tp_read(fd, n):
    """Read up to *n* bytes from file descriptor *fd*. Return a string
    containing the bytes read. If end-of-file is reached, an empty string
    is returned.

    Reading is done using the threadpool.
    """
    return get_hub().threadpool.apply(_read, (fd, n))


def tp_write(fd, buf):
    """Write bytes from buffer *buf* to file descriptor *fd*. Return the
    number of bytes written.

    Writing is done using the threadpool.
    """
    return get_hub().threadpool.apply(_write, (fd, buf))


if hasattr(os, 'fork'):
    # pylint:disable=function-redefined,redefined-outer-name

    _raw_fork = os.fork

    def fork_gevent():
        """
        Forks the process using :func:`os.fork` and prepares the
        child process to continue using gevent before returning.

        .. note::

            The PID returned by this function may not be waitable with
            either the original :func:`os.waitpid` or this module's
            :func:`waitpid` and it may not generate SIGCHLD signals if
            libev child watchers are or ever have been in use. For
            example, the :mod:`gevent.subprocess` module uses libev
            child watchers (which parts of gevent use libev child
            watchers is subject to change at any time). Most
            applications should use :func:`fork_and_watch`, which is
            monkey-patched as the default replacement for
            :func:`os.fork` and implements the ``fork`` function of
            this module by default, unless the environment variable
            ``GEVENT_NOWAITPID`` is defined before this module is
            imported.

        .. versionadded:: 1.1b2
        """
        result = _raw_fork()
        if not result:
            reinit()
        return result

    def fork():
        """
        A wrapper for :func:`fork_gevent` for non-POSIX platforms.
        """
        return fork_gevent()

    if hasattr(os, 'forkpty'):
        _raw_forkpty = os.forkpty

        def forkpty_gevent():
            """
            Forks the process using :func:`os.forkpty` and prepares the
            child process to continue using gevent before returning.

            Returns a tuple (pid, master_fd). The `master_fd` is *not* put into
            non-blocking mode.

            Availability: Some Unix systems.

            .. seealso:: This function has the same limitations as :func:`fork_gevent`.

            .. versionadded:: 1.1b5
            """
            pid, master_fd = _raw_forkpty()
            if not pid:
                reinit()
            return pid, master_fd

        forkpty = forkpty_gevent

        __implements__.append('forkpty')
        __extensions__.append("forkpty_gevent")

    if hasattr(os, 'WNOWAIT') or hasattr(os, 'WNOHANG'):
        # We can only do this on POSIX
        import time

        _waitpid = os.waitpid
        _WNOHANG = os.WNOHANG

        # replaced by the signal module.
        _on_child_hook = lambda: None

        # {pid -> watcher or tuple(pid, rstatus, timestamp)}
        _watched_children = {}

        def _on_child(watcher, callback):
            # XXX: Could handle tracing here by not stopping
            # until the pid is terminated
            watcher.stop()
            try:
                _watched_children[watcher.pid] = (watcher.pid, watcher.rstatus, time.time())
                if callback:
                    callback(watcher)
                # dispatch an "event"; used by gevent.signal.signal
                _on_child_hook()
                # now is as good a time as any to reap children
                _reap_children()
            finally:
                watcher.close()

        def _reap_children(timeout=60):
            # Remove all the dead children that haven't been waited on
            # for the *timeout* seconds.
            # Some platforms queue delivery of SIGCHLD for all children that die;
            # in that case, a well-behaved application should call waitpid() for each
            # signal.
            # Some platforms (linux) only guarantee one delivery if multiple children
            # die. On that platform, the well-behave application calls waitpid() in a loop
            # until it gets back -1, indicating no more dead children need to be waited for.
            # In either case, waitpid should be called the same number of times as dead children,
            # thus removing all the watchers when a SIGCHLD arrives. The (generous) timeout
            # is to work with applications that neglect to call waitpid and prevent "unlimited"
            # growth.
            # Note that we don't watch for the case of pid wraparound. That is, we fork a new
            # child with the same pid as an existing watcher, but the child is already dead,
            # just not waited on yet.
            now = time.time()
            oldest_allowed = now - timeout
            dead = [
                pid for pid, val
                in _watched_children.items()
                if isinstance(val, tuple) and val[2] < oldest_allowed
            ]
            for pid in dead:
                del _watched_children[pid]

        def waitpid(pid, options):
            """
            Wait for a child process to finish.

            If the child process was spawned using
            :func:`fork_and_watch`, then this function behaves
            cooperatively. If not, it *may* have race conditions; see
            :func:`fork_gevent` for more information.

            The arguments are as for the underlying
            :func:`os.waitpid`. Some combinations of *options* may not
            be supported cooperatively (as of 1.1 that includes
            WUNTRACED). Using a *pid* of 0 to request waiting on only processes
            from the current process group is not cooperative. A *pid* of -1
            to wait for any child is non-blocking, but may or may not
            require a trip around the event loop, depending on whether any children
            have already terminated but not been waited on.

            Availability: POSIX.

            .. versionadded:: 1.1b1
            .. versionchanged:: 1.2a1
               More cases are handled in a cooperative manner.
            """
            # pylint: disable=too-many-return-statements
            # XXX Does not handle tracing children

            # So long as libev's loop doesn't run, it's OK to add
            # child watchers. The SIGCHLD handler only feeds events
            # for the next iteration of the loop to handle. (And the
            # signal handler itself is only called from the next loop
            # iteration.)

            if pid <= 0:
                # magic functions for multiple children.
                if pid == -1:
                    # Any child. If we have one that we're watching
                    # and that finished, we will use that one,
                    # preferring the oldest. Otherwise, let the OS
                    # take care of it.
                    finished_at = None
                    for k, v in _watched_children.items():
                        if (
                                isinstance(v, tuple)
                                and (finished_at is None or v[2] < finished_at)
                        ):
                            pid = k
                            finished_at = v[2]

                if pid <= 0:
                    # We didn't have one that was ready. If there are
                    # no funky options set, and the pid was -1
                    # (meaning any process, not 0, which means process
                    # group--- libev doesn't know about process
                    # groups) then we can use a child watcher of pid 0; otherwise,
                    # pass through to the OS.
                    if pid == -1 and options == 0:
                        hub = get_hub()
                        with hub.loop.child(0, False) as watcher:
                            hub.wait(watcher)
                            return watcher.rpid, watcher.rstatus
                    # There were funky options/pid, so we must go to the OS.
                    return _waitpid(pid, options)

            if pid in _watched_children:
                # yes, we're watching it

                # Note that the remainder of this code must be careful to NOT
                # yield to the event loop except at well known times, or
                # we have a race condition between the _on_child callback and the
                # code here that could lead to a process to hang.
                if options & _WNOHANG or isinstance(_watched_children[pid], tuple):
                    # We're either asked not to block, or it already finished, in which
                    # case blocking doesn't matter
                    result = _watched_children[pid]
                    if isinstance(result, tuple):
                        # it finished. libev child watchers
                        # are one-shot
                        del _watched_children[pid]
                        return result[:2]
                    # it's not finished
                    return (0, 0)

                # Ok, we need to "block". Do so via a watcher so that we're
                # cooperative. We know it's our child, etc, so this should work.
                watcher = _watched_children[pid]
                # We can't start a watcher that's already started,
                # so we can't reuse the existing watcher. Notice that the
                # old watcher must not have fired already, or during this time, but
                # only after we successfully `start()` the watcher. So this must
                # not yield to the event loop.
                with watcher.loop.child(pid, False) as new_watcher:
                    get_hub().wait(new_watcher)
                # Ok, so now the new watcher is done. That means
                # the old watcher's callback (_on_child) should
                # have fired, potentially taking this child out of
                # _watched_children (but that could depend on how
                # many callbacks there were to run, so use the
                # watcher object directly; libev sets all the
                # watchers at the same time).
                return watcher.rpid, watcher.rstatus

            # we're not watching it and it may not even  be our child,
            # so we must go to the OS to be sure to get the right semantics (exception)
            # XXX
            # libuv has a race condition because the signal
            # handler is a Python function, so the InterruptedError
            # is raised before the signal handler runs and calls the
            # child watcher
            # we're not watching it
            return _waitpid(pid, options)

        def _watch_child(pid, callback=None, loop=None, ref=False):
            loop = loop or get_hub().loop
            watcher = loop.child(pid, ref=ref)
            _watched_children[pid] = watcher
            watcher.start(_on_child, watcher, callback)

        def fork_and_watch(callback=None, loop=None, ref=False, fork=fork_gevent):
            """
            Fork a child process and start a child watcher for it in the parent process.

            This call cooperates with :func:`waitpid` to enable cooperatively waiting
            for children to finish. When monkey-patching, these functions are patched in as
            :func:`os.fork` and :func:`os.waitpid`, respectively.

            In the child process, this function calls :func:`gevent.hub.reinit` before returning.

            Availability: POSIX.

            :keyword callback: If given, a callable that will be called with the child watcher
                when the child finishes.
            :keyword loop: The loop to start the watcher in. Defaults to the
                loop of the current hub.
            :keyword fork: The fork function. Defaults to :func:`the one defined in this
                module <gevent.os.fork_gevent>` (which automatically calls :func:`gevent.hub.reinit`).
                Pass the builtin :func:`os.fork` function if you do not need to
                initialize gevent in the child process.

            .. versionadded:: 1.1b1
            .. seealso::
                :func:`gevent.monkey.get_original` To access the builtin :func:`os.fork`.
            """
            pid = fork()
            if pid:
                # parent
                _watch_child(pid, callback, loop, ref)
            return pid

        __extensions__.append('fork_and_watch')
        __extensions__.append('fork_gevent')

        if 'forkpty' in __implements__:
            def forkpty_and_watch(callback=None, loop=None, ref=False, forkpty=forkpty_gevent):
                """
                Like :func:`fork_and_watch`, except using :func:`forkpty_gevent`.

                Availability: Some Unix systems.

                .. versionadded:: 1.1b5
                """
                result = []

                def _fork():
                    pid_and_fd = forkpty()
                    result.append(pid_and_fd)
                    return pid_and_fd[0]
                fork_and_watch(callback, loop, ref, _fork)
                return result[0]

            __extensions__.append('forkpty_and_watch')

        # Watch children by default
        if not config.disable_watch_children:
            # Broken out into separate functions instead of simple name aliases
            # for documentation purposes.
            def fork(*args, **kwargs):
                """
                Forks a child process and starts a child watcher for it in the
                parent process so that ``waitpid`` and SIGCHLD work as expected.

                This implementation of ``fork`` is a wrapper for :func:`fork_and_watch`
                when the environment variable ``GEVENT_NOWAITPID`` is *not* defined.
                This is the default and should be used by most applications.

                .. versionchanged:: 1.1b2
                """
                # take any args to match fork_and_watch
                return fork_and_watch(*args, **kwargs)

            if 'forkpty' in __implements__:
                def forkpty(*args, **kwargs):
                    """
                    Like :func:`fork`, but using :func:`forkpty_gevent`.

                    This implementation of ``forkpty`` is a wrapper for :func:`forkpty_and_watch`
                    when the environment variable ``GEVENT_NOWAITPID`` is *not* defined.
                    This is the default and should be used by most applications.

                    .. versionadded:: 1.1b5
                    """
                    # take any args to match fork_and_watch
                    return forkpty_and_watch(*args, **kwargs)
            __implements__.append("waitpid")

            if hasattr(os, 'posix_spawn'):
                _raw_posix_spawn = os.posix_spawn
                _raw_posix_spawnp = os.posix_spawnp

                def posix_spawn(*args, **kwargs):
                    pid = _raw_posix_spawn(*args, **kwargs)
                    _watch_child(pid)
                    return pid

                def posix_spawnp(*args, **kwargs):
                    pid = _raw_posix_spawnp(*args, **kwargs)
                    _watch_child(pid)
                    return pid

                __implements__.append("posix_spawn")
                __implements__.append("posix_spawnp")
        else:
            def fork():
                """
                Forks a child process, initializes gevent in the child,
                but *does not* prepare the parent to wait for the child or receive SIGCHLD.

                This implementation of ``fork`` is a wrapper for :func:`fork_gevent`
                when the environment variable ``GEVENT_NOWAITPID`` *is* defined.
                This is not recommended for most applications.
                """
                return fork_gevent()

            if 'forkpty' in __implements__:
                def forkpty():
                    """
                    Like :func:`fork`, but using :func:`os.forkpty`

                    This implementation of ``forkpty`` is a wrapper for :func:`forkpty_gevent`
                    when the environment variable ``GEVENT_NOWAITPID`` *is* defined.
                    This is not recommended for most applications.

                    .. versionadded:: 1.1b5
                    """
                    return forkpty_gevent()
            __extensions__.append("waitpid")

else:
    __implements__.remove('fork')


__imports__ = copy_globals(os, globals(),
                           names_to_ignore=__implements__ + __extensions__,
                           dunder_names_to_keep=())

__all__ = list(set(__implements__ + __extensions__))
