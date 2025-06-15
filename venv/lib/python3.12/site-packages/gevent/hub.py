# Copyright (c) 2009-2015 Denis Bilenko. See LICENSE for details.
"""
Event-loop hub.
"""
from __future__ import absolute_import, print_function
# XXX: FIXME: Refactor to make this smaller
# pylint:disable=too-many-lines
from functools import partial as _functools_partial

import sys
import traceback


from greenlet import greenlet as RawGreenlet
from greenlet import getcurrent
from greenlet import GreenletExit
from greenlet import error as GreenletError

__all__ = [
    'getcurrent',
    'GreenletExit',
    'spawn_raw',
    'sleep',
    'kill',
    'signal',
    'reinit',
    'get_hub',
    'Hub',
    'Waiter',
]

from gevent._config import config as GEVENT_CONFIG
from gevent._compat import thread_mod_name
from gevent._compat import reraise
from gevent._util import readproperty
from gevent._util import Lazy
from gevent._util import gmctime
from gevent._ident import IdentRegistry

from gevent._hub_local import get_hub
from gevent._hub_local import get_loop
from gevent._hub_local import set_hub
from gevent._hub_local import set_loop
from gevent._hub_local import get_hub_if_exists as _get_hub
from gevent._hub_local import get_hub_noargs as _get_hub_noargs
from gevent._hub_local import set_default_hub_class

from gevent._greenlet_primitives import TrackedRawGreenlet
from gevent._hub_primitives import WaitOperationsGreenlet

# Export
from gevent import _hub_primitives
wait = _hub_primitives.wait_on_objects
iwait = _hub_primitives.iwait_on_objects


from gevent.exceptions import LoopExit
from gevent.exceptions import HubDestroyed

from gevent._waiter import Waiter


# Need the real get_ident. We're imported early enough (by gevent/__init__.py)
# that we can be sure nothing is monkey patched yet.
get_thread_ident = __import__(thread_mod_name).get_ident
MAIN_THREAD_IDENT = get_thread_ident() # XXX: Assuming import is done on the main thread.



def spawn_raw(function, *args, **kwargs):
    """
    Create a new :class:`greenlet.greenlet` object and schedule it to
    run ``function(*args, **kwargs)``.

    This returns a raw :class:`~greenlet.greenlet` which does not have all the useful
    methods that :class:`gevent.Greenlet` has. Typically, applications
    should prefer :func:`~gevent.spawn`, but this method may
    occasionally be useful as an optimization if there are many
    greenlets involved.

    .. versionchanged:: 1.1a3
        Verify that ``function`` is callable, raising a TypeError if not. Previously,
        the spawned greenlet would have failed the first time it was switched to.

    .. versionchanged:: 1.1b1
       If *function* is not callable, immediately raise a :exc:`TypeError`
       instead of spawning a greenlet that will raise an uncaught TypeError.

    .. versionchanged:: 1.1rc2
        Accept keyword arguments for ``function`` as previously (incorrectly)
        documented. Note that this may incur an additional expense.

    .. versionchanged:: 1.3a2
       Populate the ``spawning_greenlet`` and ``spawn_tree_locals``
       attributes of the returned greenlet.

    .. versionchanged:: 1.3b1
       *Only* populate ``spawning_greenlet`` and ``spawn_tree_locals``
       if ``GEVENT_TRACK_GREENLET_TREE`` is enabled (the default). If not enabled,
       those attributes will not be set.

    .. versionchanged:: 1.5a3
       The returned greenlet always has a *loop* attribute matching the
       current hub's loop. This helps it work better with more gevent APIs.
    """
    if not callable(function):
        raise TypeError("function must be callable")

    # The hub is always the parent.
    hub = _get_hub_noargs()
    loop = hub.loop

    factory = TrackedRawGreenlet if GEVENT_CONFIG.track_greenlet_tree else RawGreenlet

    # The callback class object that we use to run this doesn't
    # accept kwargs (and those objects are heavily used, as well as being
    # implemented twice in core.ppyx and corecffi.py) so do it with a partial
    if kwargs:
        function = _functools_partial(function, *args, **kwargs)
        g = factory(function, hub)
        loop.run_callback(g.switch)
    else:
        g = factory(function, hub)
        loop.run_callback(g.switch, *args)
    g.loop = hub.loop
    return g


def sleep(seconds=0, ref=True):
    """
    Put the current greenlet to sleep for at least *seconds*.

    *seconds* may be specified as an integer, or a float if fractional
    seconds are desired.

    .. tip:: In the current implementation, a value of 0 (the default)
       means to yield execution to any other runnable greenlets, but
       this greenlet may be scheduled again before the event loop
       cycles (in an extreme case, a greenlet that repeatedly sleeps
       with 0 can prevent greenlets that are ready to do I/O from
       being scheduled for some (small) period of time); a value greater than
       0, on the other hand, will delay running this greenlet until
       the next iteration of the loop.

    If *ref* is False, the greenlet running ``sleep()`` will not prevent :func:`gevent.wait`
    from exiting.

    .. versionchanged:: 1.3a1
       Sleeping with a value of 0 will now be bounded to approximately block the
       loop for no longer than :func:`gevent.getswitchinterval`.

    .. seealso:: :func:`idle`
    """
    hub = _get_hub_noargs()
    loop = hub.loop
    if seconds <= 0:
        waiter = Waiter(hub)
        loop.run_callback(waiter.switch, None)
        waiter.get()
    else:
        with loop.timer(seconds, ref=ref) as t:
            # Sleeping is expected to be an "absolute" measure with
            # respect to time.time(), not a relative measure, so it's
            # important to update the loop's notion of now before we start
            loop.update_now()
            hub.wait(t)


def idle(priority=0):
    """
    Cause the calling greenlet to wait until the event loop is idle.

    Idle is defined as having no other events of the same or higher
    *priority* pending. That is, as long as sockets, timeouts or even
    signals of the same or higher priority are being processed, the loop
    is not idle.

    .. seealso:: :func:`sleep`
    """
    hub = _get_hub_noargs()
    with hub.loop.idle() as watcher:
        if priority:
            watcher.priority = priority
        hub.wait(watcher)


def kill(greenlet, exception=GreenletExit):
    """
    Kill greenlet asynchronously. The current greenlet is not unscheduled.

    .. note::

        The method :meth:`Greenlet.kill` method does the same and
        more (and the same caveats listed there apply here). However, the MAIN
        greenlet - the one that exists initially - does not have a
        ``kill()`` method, and neither do any created with :func:`spawn_raw`,
        so you have to use this function.

    .. caution:: Use care when killing greenlets. If they are not prepared for
       exceptions, this could result in corrupted state.

    .. versionchanged:: 1.1a2
        If the ``greenlet`` has a :meth:`kill <Greenlet.kill>` method, calls it. This prevents a
        greenlet from being switched to for the first time after it's been
        killed but not yet executed.
    """
    if not greenlet.dead:
        if hasattr(greenlet, 'kill'):
            # dealing with gevent.greenlet.Greenlet. Use it, especially
            # to avoid allowing one to be switched to for the first time
            # after it's been killed
            greenlet.kill(exception=exception, block=False)
        else:
            _get_hub_noargs().loop.run_callback(greenlet.throw, exception)


class signal(object):
    """
    signal_handler(signalnum, handler, *args, **kwargs) -> object

    Call the *handler* with the *args* and *kwargs* when the process
    receives the signal *signalnum*.

    The *handler* will be run in a new greenlet when the signal is
    delivered.

    This returns an object with the useful method ``cancel``, which,
    when called, will prevent future deliveries of *signalnum* from
    calling *handler*. It's best to keep the returned object alive
    until you call ``cancel``.

    .. note::

        This may not operate correctly with ``SIGCHLD`` if libev child
        watchers are used (as they are by default with
        `gevent.os.fork`). See :mod:`gevent.signal` for a more
        general purpose solution.

    .. versionchanged:: 1.2a1

        The ``handler`` argument is required to
        be callable at construction time.

    .. versionchanged:: 20.5.1
       The ``cancel`` method now properly cleans up all native resources,
       and drops references to all the arguments of this function.
    """
    # This is documented as a function, not a class,
    # so we're free to change implementation details.

    greenlet_class = None

    def __init__(self, signalnum, handler, *args, **kwargs):
        if not callable(handler):
            raise TypeError("signal handler must be callable.")

        self.hub = _get_hub_noargs()
        self.watcher = self.hub.loop.signal(signalnum, ref=False)
        self.handler = handler
        self.args = args
        self.kwargs = kwargs
        if self.greenlet_class is None:
            from gevent import Greenlet
            type(self).greenlet_class = Greenlet
            self.greenlet_class = Greenlet

        self.watcher.start(self._start)

    ref = property(
        lambda self: self.watcher.ref,
        lambda self, nv: setattr(self.watcher, 'ref', nv)
    )

    def cancel(self):
        if self.watcher is not None:
            self.watcher.stop()
            # Must close the watcher at a deterministic time, otherwise
            # when CFFI reclaims the memory, the native loop might still
            # have some reference to it; if anything tries to touch it
            # we can wind up writing to memory that is no longer valid,
            # leading to a wide variety of crashes.
            self.watcher.close()
        self.watcher = None
        self.handler = None
        self.args = None
        self.kwargs = None
        self.hub = None
        self.greenlet_class = None

    def _start(self):
        # TODO: Maybe this should just be Greenlet.spawn()?
        try:
            greenlet = self.greenlet_class(self.handle)
            greenlet.switch()
        except: # pylint:disable=bare-except
            self.hub.handle_error(None, *sys._exc_info()) # pylint:disable=no-member

    def handle(self):
        try:
            self.handler(*self.args, **self.kwargs)
        except: # pylint:disable=bare-except
            self.hub.handle_error(None, *sys.exc_info())


def reinit(hub=None):
    """
    reinit() -> None

    Prepare the gevent hub to run in a new (forked) process.

    This should be called *immediately* after :func:`os.fork` in the
    child process. This is done automatically by
    :func:`gevent.os.fork` or if the :mod:`os` module has been
    monkey-patched. If this function is not called in a forked
    process, symptoms may include hanging of functions like
    :func:`socket.getaddrinfo`, and the hub's threadpool is unlikely
    to work.

    .. note:: Registered fork watchers may or may not run before
       this function (and thus ``gevent.os.fork``) return. If they have
       not run, they will run "soon", after an iteration of the event loop.
       You can force this by inserting a few small (but non-zero) calls to :func:`sleep`
       after fork returns. (As of gevent 1.1 and before, fork watchers will
       not have run, but this may change in the future.)

    .. note:: This function may be removed in a future major release
       if the fork process can be more smoothly managed.

    .. warning:: See remarks in :func:`gevent.os.fork` about greenlets
       and event loop watchers in the child process.
    """
    # Note the signature line in the docstring: hub is not a public param.

    # The loop reinit function in turn calls libev's ev_loop_fork
    # function.
    hub = _get_hub() if hub is None else hub
    if hub is None:
        return

    # Note that we reinit the existing loop, not destroy it.
    # See https://github.com/gevent/gevent/issues/200.
    hub.loop.reinit()
    # libev's fork watchers are slow to fire because the only fire
    # at the beginning of a loop; due to our use of callbacks that
    # run at the end of the loop, that may be too late. The
    # threadpool and resolvers depend on the fork handlers being
    # run (specifically, the threadpool will fail in the forked
    # child if there were any threads in it, which there will be
    # if the resolver_thread was in use (the default) before the
    # fork.)
    #
    # If the forked process wants to use the threadpool or
    # resolver immediately (in a queued callback), it would hang.
    #
    # The below is a workaround. Fortunately, all of these
    # methods are idempotent and can be called multiple times
    # following a fork if the suddenly started working, or were
    # already working on some platforms. Other threadpools and fork handlers
    # will be called at an arbitrary time later ('soon')
    for obj in (hub._threadpool, hub._resolver, hub.periodic_monitoring_thread):
        getattr(obj, '_on_fork', lambda: None)()

    # TODO: We'd like to sleep for a non-zero amount of time to force the loop to make a
    # pass around before returning to this greenlet. That will allow any
    # user-provided fork watchers to run. (Two calls are necessary.) HOWEVER, if
    # we do this, certain tests that heavily mix threads and forking,
    # like 2.7/test_threading:test_reinit_tls_after_fork, fail. It's not immediately clear
    # why.
    #sleep(0.00001)
    #sleep(0.00001)


class Hub(WaitOperationsGreenlet):
    """
    A greenlet that runs the event loop.

    It is created automatically by :func:`get_hub`.

    .. rubric:: Switching

    Every time this greenlet (i.e., the event loop) is switched *to*,
    if the current greenlet has a ``switch_out`` method, it will be
    called. This allows a greenlet to take some cleanup actions before
    yielding control. This method should not call any gevent blocking
    functions.
    """

    #: If instances of these classes are raised into the event loop,
    #: they will be propagated out to the main greenlet (where they will
    #: usually be caught by Python itself)
    SYSTEM_ERROR = (KeyboardInterrupt, SystemExit, SystemError)

    #: Instances of these classes are not considered to be errors and
    #: do not get logged/printed when raised by the event loop.
    NOT_ERROR = (GreenletExit, SystemExit)

    #: The size we use for our threadpool. Either use a subclass
    #: for this, or change it immediately after creating the hub.
    threadpool_size = 10

    # An instance of PeriodicMonitoringThread, if started.
    periodic_monitoring_thread = None

    # The ident of the thread we were created in, which should be the
    # thread that we run in.
    thread_ident = None

    #: A string giving the name of this hub. Useful for associating hubs
    #: with particular threads. Printed as part of the default repr.
    #:
    #: .. versionadded:: 1.3b1
    name = ''

    # NOTE: We cannot define a class-level 'loop' attribute
    # because that conflicts with the slot we inherit from the
    # Cythonized-bases.

    # This is the source for our 'minimal_ident' property. We don't use a
    # IdentRegistry because we've seen some crashes having to do with
    # clearing weak references on shutdown in Windows (see known_failures.py).
    # This gives us slightly different semantics than a greenlet's minimal_ident
    # (notably, there can be holes) but we never documented this object's minimal_ident,
    # and there should be few enough hub's over the lifetime of a process so as not
    # to matter much.
    _hub_counter = 0

    def __init__(self, loop=None, default=None):
        WaitOperationsGreenlet.__init__(self, None, None)
        self.thread_ident = get_thread_ident()
        if hasattr(loop, 'run'):
            if default is not None:
                raise TypeError("Unexpected argument: default")
            self.loop = loop
        elif get_loop() is not None:
            # Reuse a loop instance previously set by
            # destroying a hub without destroying the associated
            # loop. See #237 and #238.
            self.loop = get_loop()
        else:
            if default is None and self.thread_ident != MAIN_THREAD_IDENT:
                default = False

            if loop is None:
                loop = self.backend
            self.loop = self.loop_class(flags=loop, default=default) # pylint:disable=not-callable
        self._resolver = None
        self._threadpool = None
        self.format_context = GEVENT_CONFIG.format_context

        Hub._hub_counter += 1
        self.minimal_ident = Hub._hub_counter

    @Lazy
    def ident_registry(self):
        return IdentRegistry()

    @property
    def loop_class(self):
        return GEVENT_CONFIG.loop

    @property
    def backend(self):
        return GEVENT_CONFIG.libev_backend

    @property
    def main_hub(self):
        """
        Is this the hub for the main thread?

        .. versionadded:: 1.3b1
        """
        return self.thread_ident == MAIN_THREAD_IDENT

    def __repr__(self):
        if self.loop is None:
            info = 'destroyed'
        else:
            try:
                info = self.loop._format()
            except Exception as ex: # pylint:disable=broad-except
                info = str(ex) or repr(ex) or 'error'
        result = '<%s %r at 0x%x %s' % (
            self.__class__.__name__,
            self.name,
            id(self),
            info)
        if self._resolver is not None:
            result += ' resolver=%r' % self._resolver
        if self._threadpool is not None:
            result += ' threadpool=%r' % self._threadpool
        result += ' thread_ident=%s' % (hex(self.thread_ident), )
        return result + '>'

    def _normalize_exception(self, t, v, tb):
        # Allow passing in all None if the caller doesn't have
        # easy access to sys.exc_info()
        if (t, v, tb) == (None, None, None):
            t, v, tb = sys.exc_info()

        if isinstance(v, str):
            # Cython can raise errors where the value is a plain string
            # e.g., AttributeError, "_semaphore.Semaphore has no attr", <traceback>
            v = t(v)

        return t, v, tb

    def handle_error(self, context, type, value, tb):
        """
        Called by the event loop when an error occurs. The default
        action is to print the exception to the :attr:`exception
        stream <exception_stream>`.

        The arguments ``type``, ``value``, and ``tb`` are the standard
        tuple as returned by :func:`sys.exc_info`. (Note that when
        this is called, it may not be safe to call
        :func:`sys.exc_info`.)

        Errors that are :attr:`not errors <NOT_ERROR>` are not
        printed.

        Errors that are :attr:`system errors <SYSTEM_ERROR>` are
        passed to :meth:`handle_system_error` after being printed.

        Applications can set a property on the hub instance with this
        same signature to override the error handling provided by this
        class. This is an advanced usage and requires great care. This
        function *must not* raise any exceptions.

        :param context: If this is ``None``, indicates a system error
            that should generally result in exiting the loop and being
            thrown to the parent greenlet.
        """
        type, value, tb = self._normalize_exception(type, value, tb)

        if type is HubDestroyed:
            # We must continue propagating this for it to properly
            # exit.
            reraise(type, value, tb)

        if not issubclass(type, self.NOT_ERROR):
            self.print_exception(context, type, value, tb)
        if context is None or issubclass(type, self.SYSTEM_ERROR):
            self.handle_system_error(type, value, tb)

    def handle_system_error(self, type, value, tb=None):
        """
        Called from `handle_error` when the exception type is determined
        to be a :attr:`system error <SYSTEM_ERROR>`.

        System errors cause the exception to be raised in the main
        greenlet (the parent of this hub).

        .. versionchanged:: 20.5.1
           Allow passing the traceback to associate with the
           exception if it is rethrown into the main greenlet.
        """
        current = getcurrent()
        if current is self or current is self.parent or self.loop is None:
            self.parent.throw(type, value, tb)
        else:
            # in case system error was handled and life goes on
            # switch back to this greenlet as well
            cb = None
            try:
                cb = self.loop.run_callback(current.switch)
            except: # pylint:disable=bare-except
                traceback.print_exc(file=self.exception_stream)
            try:
                self.parent.throw(type, value, tb)
            finally:
                if cb is not None:
                    cb.stop()

    @readproperty
    def exception_stream(self):
        """
        The stream to which exceptions will be written.
        Defaults to ``sys.stderr`` unless assigned. Assigning a
        false (None) value disables printing exceptions.

        .. versionadded:: 1.2a1
        """
        # Unwrap any FileObjectThread we have thrown around sys.stderr
        # (because it can't be used in the hub). Tricky because we are
        # called in error situations when it's not safe to import.
        # Be careful not to access sys if we're in the process of interpreter
        # shutdown.
        stderr = sys.stderr if sys else None # pylint:disable=using-constant-test
        if type(stderr).__name__ == 'FileObjectThread':
            stderr = stderr.io # pylint:disable=no-member
        return stderr

    def print_exception(self, context, t, v, tb):
        # Python 3 does not gracefully handle None value or tb in
        # traceback.print_exception() as previous versions did.
        # pylint:disable=no-member
        errstream = self.exception_stream
        if not errstream: # pragma: no cover
            # If the error stream is gone, such as when the sys dict
            # gets cleared during interpreter shutdown,
            # don't cause follow-on errors.
            # See https://github.com/gevent/gevent/issues/1295
            return

        t, v, tb = self._normalize_exception(t, v, tb)

        if v is None:
            errstream.write('%s\n' % t.__name__)
        else:
            traceback.print_exception(t, v, tb, file=errstream)
        del tb

        try:
            errstream.write(gmctime())
            errstream.write(' ' if context is not None else '\n')
        except: # pylint:disable=bare-except
            # Possible not safe to import under certain
            # error conditions in Python 2
            pass

        if context is not None:
            if not isinstance(context, str):
                try:
                    context = self.format_context(context)
                except: # pylint:disable=bare-except
                    traceback.print_exc(file=self.exception_stream)
                    context = repr(context)
            errstream.write('%s failed with %s\n\n' % (context, getattr(t, '__name__', 'exception'), ))


    def run(self):
        """
        Entry-point to running the loop. This method is called automatically
        when the hub greenlet is scheduled; do not call it directly.

        :raises gevent.exceptions.LoopExit: If the loop finishes running. This means
           that there are no other scheduled greenlets, and no active
           watchers or servers. In some situations, this indicates a
           programming error.
        """
        assert self is getcurrent(), 'Do not call Hub.run() directly'
        self.start_periodic_monitoring_thread()
        while 1:
            loop = self.loop
            loop.error_handler = self
            try:
                loop.run()
            finally:
                loop.error_handler = None  # break the refcount cycle

            # This function must never return, as it will cause
            # switch() in the parent greenlet to return an unexpected
            # value. This can show up as unexpected failures e.g.,
            # from Waiters raising AssertionError or MulitpleWaiter
            # raising invalid IndexError.
            #
            # It is still possible to kill this greenlet with throw.
            # However, in that case switching to it is no longer safe,
            # as switch will return immediately.
            #
            # Note that there's a problem with simply doing
            # ``self.parent.throw()`` and never actually exiting this
            # greenlet: The greenlet tends to stay alive. This is
            # because throwing the exception captures stack frames
            # (regardless of what we do with the argument) and those
            # get saved. In addition to this object having
            # ``gr_frame`` pointing to this method, which contains
            # ``self``, which points to the parent, and both of which point to
            # an internal thread state dict that points back to the current greenlet for the thread,
            # which is likely to be the parent: a cycle.
            #
            # We can't have ``join()`` tell us to finish, because we
            # need to be able to resume after this throw. The only way
            # to dispose of the greenlet is to use ``self.destroy()``.

            debug = []
            if hasattr(loop, 'debug'):
                debug = loop.debug()
            loop = None

            self.parent.throw(LoopExit('This operation would block forever',
                                       self,
                                       debug))
            # Execution could resume here if another blocking API call is made
            # in the same thread and the hub hasn't been destroyed, so clean
            # up anything left.
            debug = None

    def start_periodic_monitoring_thread(self):
        if self.periodic_monitoring_thread is None and GEVENT_CONFIG.monitor_thread:
            # Note that it is possible for one real thread to
            # (temporarily) wind up with multiple monitoring threads,
            # if hubs are started and stopped within the thread. This shows up
            # in the threadpool tests. The monitoring threads will eventually notice their
            # hub object is gone.
            from gevent._monitor import PeriodicMonitoringThread
            from gevent.events import PeriodicMonitorThreadStartedEvent
            from gevent.events import notify_and_call_entry_points
            self.periodic_monitoring_thread = PeriodicMonitoringThread(self)

            if self.main_hub:
                self.periodic_monitoring_thread.install_monitor_memory_usage()

            notify_and_call_entry_points(PeriodicMonitorThreadStartedEvent(
                self.periodic_monitoring_thread))

        return self.periodic_monitoring_thread

    def join(self, timeout=None):
        """
        Wait for the event loop to finish. Exits only when there
        are no more spawned greenlets, started servers, active
        timeouts or watchers.

        .. caution:: This doesn't clean up all resources associated
           with the hub. For that, see :meth:`destroy`.

        :param float timeout: If *timeout* is provided, wait no longer
            than the specified number of seconds.

        :return: `True` if this method returns because the loop
                 finished execution. Or `False` if the timeout
                 expired.
        """
        assert getcurrent() is self.parent, "only possible from the MAIN greenlet"
        if self.dead:
            return True

        waiter = Waiter(self)

        if timeout is not None:
            timeout = self.loop.timer(timeout, ref=False)
            timeout.start(waiter.switch, None)

        try:
            try:
                # Switch to the hub greenlet and let it continue.
                # Since we're the parent greenlet of the hub, when it exits
                # by `parent.throw(LoopExit)`, control will resume here.
                # If the timer elapses, however, ``waiter.switch()`` is called and
                # again control resumes here, but without an exception.
                waiter.get()
            except LoopExit:
                # Control will immediately be returned to this greenlet.
                return True
        finally:
            # Clean up as much junk as we can. There is a small cycle in the frames,
            # and it won't be GC'd.
            # this greenlet -> this frame
            # this greenlet -> the exception that was thrown
            # the exception that was thrown -> a bunch of other frames, including this frame.
            # some frame calling self.run() -> self
            del waiter # this frame -> waiter -> self
            del self # this frame -> self
            if timeout is not None:
                timeout.stop()
                timeout.close()
            del timeout
        return False

    def destroy(self, destroy_loop=None):
        """
        Destroy this hub and clean up its resources.

        If you manually create hubs, or you use a hub or the gevent
        blocking API from multiple native threads, you *should* call this
        method before disposing of the hub object reference. Ideally,
        this should be called from the same thread running the hub, but
        it can be called from other threads after that thread has exited.

        Once this is done, it is impossible to continue running the
        hub. Attempts to use the blocking gevent API with pre-existing
        objects from this native thread and bound to this hub will fail.

        .. versionchanged:: 20.5.1
            Attempt to ensure that Python stack frames and greenlets referenced by this
            hub are cleaned up. This guarantees that switching to the hub again
            is not safe after this. (It was never safe, but it's even less safe.)

            Note that this only works if the hub is destroyed in the same thread it
            is running in. If the hub is destroyed by a different thread
            after a ``fork()``, for example, expect some garbage to leak.
        """
        if destroy_loop is None:
            destroy_loop = not self.loop.default

        if self.periodic_monitoring_thread is not None:
            self.periodic_monitoring_thread.kill()
            self.periodic_monitoring_thread = None
        if self._resolver is not None:
            self._resolver.close()
            del self._resolver
        if self._threadpool is not None:
            self._threadpool.kill()
            del self._threadpool

        # Let the frame be cleaned up by causing the run() function to
        # exit. This is the only way to guarantee that the hub itself
        # and the main greenlet, if this was a secondary thread, get
        # cleaned up. Otherwise there are likely to be reference
        # cycles still around. We MUST do this before we destroy the
        # loop; if we destroy the loop and then switch into the hub,
        # things will go VERY, VERY wrong (because we will have destroyed
        # the C datastructures in the middle of the C function that's
        # using them; the best we can hope for is a segfault).
        try:
            self.throw(HubDestroyed(destroy_loop))
        except LoopExit:
            # Expected.
            pass
        except GreenletError:
            # Must be coming from a different thread.
            # Note that python stack frames are likely to leak
            # in this case.
            pass

        if destroy_loop:
            if get_loop() is self.loop:
                # Don't let anyone try to reuse this
                set_loop(None)
            self.loop.destroy()
        else:
            # Store in case another hub is created for this
            # thread.
            set_loop(self.loop)

        self.loop = None
        if _get_hub() is self:
            set_hub(None)



    # XXX: We can probably simplify the resolver and threadpool properties.

    @property
    def resolver_class(self):
        return GEVENT_CONFIG.resolver

    def _get_resolver(self):
        if self._resolver is None:
            self._resolver = self.resolver_class(hub=self) # pylint:disable=not-callable
        return self._resolver

    def _set_resolver(self, value):
        self._resolver = value

    def _del_resolver(self):
        self._resolver = None

    resolver = property(_get_resolver, _set_resolver, _del_resolver,
                        """
                        The DNS resolver that the socket functions will use.

                        .. seealso:: :doc:`/dns`
                        """)


    @property
    def threadpool_class(self):
        return GEVENT_CONFIG.threadpool

    def _get_threadpool(self):
        if self._threadpool is None:
            # pylint:disable=not-callable
            self._threadpool = self.threadpool_class(
                self.threadpool_size,
                hub=self,
                idle_task_timeout=GEVENT_CONFIG.threadpool_idle_task_timeout
            )
        return self._threadpool

    def _set_threadpool(self, value):
        self._threadpool = value

    def _del_threadpool(self):
        self._threadpool = None

    threadpool = property(_get_threadpool, _set_threadpool, _del_threadpool,
                          """
                          The threadpool associated with this hub.

                          Usually this is a
                          :class:`gevent.threadpool.ThreadPool`, but
                          you :attr:`can customize that
                          <gevent._config.Config.threadpool>`.

                          Use this object to schedule blocking
                          (non-cooperative) operations in a different
                          thread to prevent them from halting the event loop.
                          """)


set_default_hub_class(Hub)



class linkproxy(object):
    __slots__ = ['callback', 'obj']

    def __init__(self, callback, obj):
        self.callback = callback
        self.obj = obj

    def __call__(self, *args):
        callback = self.callback
        obj = self.obj
        self.callback = None
        self.obj = None
        callback(obj)
