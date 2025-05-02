"""
libuv loop implementation
"""
# pylint: disable=no-member
from __future__ import absolute_import, print_function

import os
from collections import defaultdict
from collections import namedtuple
from operator import delitem
import signal

from zope.interface import implementer

from gevent import getcurrent
from gevent.exceptions import LoopExit

from gevent._ffi import _dbg # pylint: disable=unused-import
from gevent._ffi.loop import AbstractLoop
from gevent._ffi.loop import assign_standard_callbacks
from gevent._ffi.loop import AbstractCallbacks
from gevent._interfaces import ILoop
from gevent.libuv import _corecffi # pylint:disable=no-name-in-module,import-error

ffi = _corecffi.ffi
libuv = _corecffi.lib

__all__ = [
]


class _Callbacks(AbstractCallbacks):

    def _find_loop_from_c_watcher(self, watcher_ptr):
        loop_handle = ffi.cast('uv_handle_t*', watcher_ptr).data
        return self.from_handle(loop_handle) if loop_handle else None

    def python_sigchld_callback(self, watcher_ptr, _signum):
        self.from_handle(ffi.cast('uv_handle_t*', watcher_ptr).data)._sigchld_callback()

    def python_timer0_callback(self, watcher_ptr):
        return self.python_prepare_callback(watcher_ptr)

    def python_queue_callback(self, watcher_ptr, revents):
        watcher_handle = watcher_ptr.data
        the_watcher = self.from_handle(watcher_handle)

        the_watcher.loop._queue_callback(watcher_ptr, revents)


_callbacks = assign_standard_callbacks(
    ffi, libuv, _Callbacks,
    [
        'python_sigchld_callback',
        'python_timer0_callback',
        'python_queue_callback',
    ]
)

from gevent._ffi.loop import EVENTS
GEVENT_CORE_EVENTS = EVENTS # export

from gevent.libuv import watcher as _watchers # pylint:disable=no-name-in-module

_events_to_str = _watchers._events_to_str # export

READ = libuv.UV_READABLE
WRITE = libuv.UV_WRITABLE

def get_version():
    uv_bytes = ffi.string(libuv.uv_version_string())
    if not isinstance(uv_bytes, str):
        # Py3
        uv_str = uv_bytes.decode("ascii")
    else:
        uv_str = uv_bytes

    return 'libuv-' + uv_str

def get_header_version():
    return 'libuv-%d.%d.%d' % (libuv.UV_VERSION_MAJOR, libuv.UV_VERSION_MINOR, libuv.UV_VERSION_PATCH)

def supported_backends():
    return ['default']

libuv.gevent_set_uv_alloc()

@implementer(ILoop)
class loop(AbstractLoop):

    # libuv parameters simply won't accept anything lower than 1ms. In
    # practice, looping on gevent.sleep(0.001) takes about 0.00138 s
    # (+- 0.000036s)
    approx_timer_resolution = 0.001 # 1ms

    # It's relatively more expensive to break from the callback loop
    # because we don't do it "inline" from C, we're looping in Python
    CALLBACK_CHECK_COUNT = max(AbstractLoop.CALLBACK_CHECK_COUNT, 100)

    # Defines the maximum amount of time the loop will sleep waiting for IO,
    # which is also the interval at which signals are checked and handled.
    SIGNAL_CHECK_INTERVAL_MS = 300

    error_handler = None

    _CHECK_POINTER = 'uv_check_t *'

    _PREPARE_POINTER = 'uv_prepare_t *'
    _PREPARE_CALLBACK_SIG = "void(*)(void*)"

    _TIMER_POINTER = _CHECK_POINTER # This is poorly named. It's for the callback "timer"

    def __init__(self, flags=None, default=None):
        AbstractLoop.__init__(self, ffi, libuv, _watchers, flags, default)
        self._child_watchers = defaultdict(list)
        self._io_watchers = {}
        self._fork_watchers = set()
        self._pid = os.getpid()
        # pylint:disable-next=superfluous-parens
        self._default = (self._ptr == libuv.uv_default_loop())
        self._queued_callbacks = []

    def _queue_callback(self, watcher_ptr, revents):
        self._queued_callbacks.append((watcher_ptr, revents))

    def _init_loop(self, flags, default):
        if default is None:
            default = True
            # Unlike libev, libuv creates a new default
            # loop automatically if the old default loop was
            # closed.

        if default:
            # XXX: If the default loop had been destroyed, this
            # will create a new one, but we won't destroy it
            ptr = libuv.uv_default_loop()
        else:
            ptr = libuv.uv_loop_new()


        if not ptr:
            raise SystemError("Failed to get loop")

        # Track whether or not any object has destroyed
        # this loop. See _can_destroy_default_loop
        ptr.data = self._handle_to_self
        return ptr

    _signal_idle = None

    @property
    def ptr(self):
        if not self._ptr:
            return None
        if self._ptr and not self._ptr.data:
            # Another instance of the Python loop destroyed
            # the C loop. It was probably the default.
            self._ptr = None
        return self._ptr

    def _init_and_start_check(self):
        libuv.uv_check_init(self.ptr, self._check)
        libuv.uv_check_start(self._check, libuv.python_check_callback)
        libuv.uv_unref(self._check)

        # We also have to have an idle watcher to be able to handle
        # signals in a timely manner. Without them, libuv won't loop again
        # and call into its check and prepare handlers.
        # Note that this basically forces us into a busy-loop
        # XXX: As predicted, using an idle watcher causes our process
        # to eat 100% CPU time. We instead use a timer with a max of a .3 second
        # delay to notice signals. Note that this timeout also implements fork
        # watchers, effectively.

        # XXX: Perhaps we could optimize this to notice when there are other
        # timers in the loop and start/stop it then. When we have a callback
        # scheduled, this should also be the same and unnecessary?
        # libev does takes this basic approach on Windows.
        self._signal_idle = ffi.new("uv_timer_t*")
        libuv.uv_timer_init(self.ptr, self._signal_idle)
        self._signal_idle.data = self._handle_to_self
        sig_cb = ffi.cast('void(*)(uv_timer_t*)', libuv.python_check_callback)
        libuv.uv_timer_start(self._signal_idle,
                             sig_cb,
                             self.SIGNAL_CHECK_INTERVAL_MS,
                             self.SIGNAL_CHECK_INTERVAL_MS)
        libuv.uv_unref(self._signal_idle)

    def __check_and_die(self):
        if not self.ptr:
            # We've been destroyed during the middle of self.run().
            # This method is being called into from C, and it's not
            # safe to go back to C (Windows in particular can abort
            # the process with "GetQueuedCompletionStatusEx: (6) The
            # handle is invalid.") So switch to the parent greenlet.
            getcurrent().parent.throw(LoopExit('Destroyed during run'))

    def _run_callbacks(self):
        self.__check_and_die()
        # Manually handle fork watchers.
        curpid = os.getpid()
        if curpid != self._pid:
            self._pid = curpid
            for watcher in self._fork_watchers:
                watcher._on_fork()


        # The contents of queued_callbacks at this point should be timers
        # that expired when the loop began along with any idle watchers.
        # We need to run them so that any manual callbacks they want to schedule
        # get added to the list and ran next before we go on to poll for IO.
        # This is critical for libuv on linux: closing a socket schedules some manual
        # callbacks to actually stop the watcher; if those don't run before
        # we poll for IO, then libuv can abort the process for the closed file descriptor.

        # XXX: There's still a race condition here because we may not run *all* the manual
        # callbacks. We need a way to prioritize those.

        # Running these before the manual callbacks lead to some
        # random test failures. In test__event.TestEvent_SetThenClear
        # we would get a LoopExit sometimes. The problem occurred when
        # a timer expired on entering the first loop; we would process
        # it there, and then process the callback that it created
        # below, leaving nothing for the loop to do. Having the
        # self.run() manually process manual callbacks before
        # continuing solves the problem. (But we must still run callbacks
        # here again.)
        self._prepare_ran_callbacks = self.__run_queued_callbacks()

        super(loop, self)._run_callbacks()

    def _init_and_start_prepare(self):
        libuv.uv_prepare_init(self.ptr, self._prepare)
        libuv.uv_prepare_start(self._prepare, libuv.python_prepare_callback)
        libuv.uv_unref(self._prepare)

    def _init_callback_timer(self):
        libuv.uv_check_init(self.ptr, self._timer0)

    def _stop_callback_timer(self):
        libuv.uv_check_stop(self._timer0)

    def _start_callback_timer(self):
        # The purpose of the callback timer is to ensure that we run
        # callbacks as soon as possible on the next iteration of the event loop.

        # In libev, we set a 0 duration timer with a no-op callback.
        # This executes immediately *after* the IO poll is done (it
        # actually determines the time that the IO poll will block
        # for), so having the timer present simply spins the loop, and
        # our normal prepare watcher kicks in to run the callbacks.

        # In libuv, however, timers are run *first*, before prepare
        # callbacks and before polling for IO. So a no-op 0 duration
        # timer actually does *nothing*. (Also note that libev queues all
        # watchers found during IO poll to run at the end (I think), while libuv
        # runs them in uv__io_poll itself.)

        # From the loop inside uv_run:
        # while True:
        #   uv__update_time(loop);
        #   uv__run_timers(loop);
        #   # we don't use pending watchers. They are how libuv
        #   # implements the pipe/udp/tcp streams.
        #   ran_pending = uv__run_pending(loop);
        #   uv__run_idle(loop);
        #   uv__run_prepare(loop);
        #   ...
        #   uv__io_poll(loop, timeout); # <--- IO watchers run here!
        #   uv__run_check(loop);

        # libev looks something like this (pseudo code because the real code is
        # hard to read):
        #
        # do {
        #    run_fork_callbacks();
        #    run_prepare_callbacks();
        #    timeout = min(time of all timers or normal block time)
        #    io_poll() # <--- Only queues IO callbacks
        #    update_now(); calculate_expired_timers();
        #    run callbacks in this order: (although specificying priorities changes it)
        #        check
        #        stat
        #        child
        #        signal
        #        timer
        #        io
        # }

        # So instead of running a no-op and letting the side-effect of spinning
        # the loop run the callbacks, we must explicitly run them here.

        # If we don't, test__systemerror:TestCallback will be flaky, failing
        # one time out of ~20, depending on timing.

        # To get them to run immediately after this current loop,
        # we use a check watcher, instead of a 0 duration timer entirely.
        # If we use a 0 duration timer, we can get stuck in a timer loop.
        # Python 3.6 fails in test_ftplib.py

        # As a final note, if we have not yet entered the loop *at
        # all*, and a timer was created with a duration shorter than
        # the amount of time it took for us to enter the loop in the
        # first place, it may expire and get called before our callback
        # does. This could also lead to test__systemerror:TestCallback
        # appearing to be flaky.

        # As yet another final note, if we are currently running a
        # timer callback, meaning we're inside uv__run_timers() in C,
        # and the Python starts a new timer, if the Python code then
        # update's the loop's time, it's possible that timer will
        # expire *and be run in the same iteration of the loop*. This
        # is trivial to do: In sequential code, anything after
        # `gevent.sleep(0.1)` is running in a timer callback. Starting
        # a new timer---e.g., another gevent.sleep() call---will
        # update the time, *before* uv__run_timers exits, meaning
        # other timers get a chance to run before our check or prepare
        # watcher callbacks do. Therefore, we do indeed have to have a 0
        # timer to run callbacks---it gets inserted before any other user
        # timers---ideally, this should be especially careful about how much time
        # it runs for.

        # AND YET: We can't actually do that. We get timeouts that I haven't fully
        # investigated if we do. Probably stuck in a timer loop.

        # As a partial remedy to this, unlike libev, our timer watcher
        # class doesn't update the loop time by default.

        libuv.uv_check_start(self._timer0, libuv.python_timer0_callback)


    def _stop_aux_watchers(self):
        super(loop, self)._stop_aux_watchers()
        assert self._prepare
        assert self._check
        assert self._signal_idle
        libuv.uv_prepare_stop(self._prepare)
        libuv.uv_ref(self._prepare) # Why are we doing this?

        libuv.uv_check_stop(self._check)
        libuv.uv_ref(self._check)

        libuv.uv_timer_stop(self._signal_idle)
        libuv.uv_ref(self._signal_idle)

        libuv.uv_check_stop(self._timer0)

    def _setup_for_run_callback(self):
        self._start_callback_timer()
        libuv.uv_ref(self._timer0)

    def _can_destroy_loop(self, ptr):
        return ptr

    def __close_loop(self, ptr):
        closed_failed = 1

        while closed_failed:
            closed_failed = libuv.uv_loop_close(ptr)
            if not closed_failed:
                break

            if closed_failed != libuv.UV_EBUSY:
                raise SystemError("Unknown close failure reason", closed_failed)
            # We already closed all the handles. Run the loop
            # once to let them be cut off from the loop.
            ran_has_more_callbacks = libuv.uv_run(ptr, libuv.UV_RUN_ONCE)
            if ran_has_more_callbacks:
                libuv.uv_run(ptr, libuv.UV_RUN_NOWAIT)


    def _destroy_loop(self, ptr):
        # We're being asked to destroy a loop that's, potentially, at
        # the time it was constructed, was the default loop. If loop
        # objects were constructed more than once, it may have already
        # been destroyed, though. We track this in the data member.
        data = ptr.data
        ptr.data = ffi.NULL
        try:
            if data:
                libuv.uv_stop(ptr)
                libuv.gevent_close_all_handles(ptr)
        finally:
            ptr.data = ffi.NULL

        try:
            if data:
                self.__close_loop(ptr)
        finally:
            # Destroy the native resources *after* we have closed
            # the loop. If we do it before, walking the handles
            # attached to the loop is likely to segfault.
            # Note that these may have been closed already if the default loop was shared.
            if data:
                libuv.gevent_zero_check(self._check)
                libuv.gevent_zero_check(self._timer0)
                libuv.gevent_zero_prepare(self._prepare)
                libuv.gevent_zero_timer(self._signal_idle)
                libuv.gevent_zero_loop(ptr)

            del self._check
            del self._prepare
            del self._signal_idle
            del self._timer0

            # Destroy any watchers we're still holding on to.
            del self._io_watchers
            del self._fork_watchers
            del self._child_watchers

    _HandleState = namedtuple("HandleState",
                              ['handle',
                               'type',
                               'watcher',
                               'ref',
                               'active',
                               'closing'])
    def debug(self):
        """
        Return all the handles that are open and their ref status.
        """
        if not self.ptr:
            return ["Loop has been destroyed"]

        handle_state = self._HandleState
        handles = []

        # XXX: Convert this to a modern callback.
        def walk(handle, _arg):
            data = handle.data
            if data:
                watcher = ffi.from_handle(data)
            else:
                watcher = None
            handles.append(handle_state(handle,
                                        ffi.string(libuv.uv_handle_type_name(handle.type)),
                                        watcher,
                                        libuv.uv_has_ref(handle),
                                        libuv.uv_is_active(handle),
                                        libuv.uv_is_closing(handle)))

        libuv.uv_walk(self.ptr,
                      ffi.callback("void(*)(uv_handle_t*,void*)",
                                   walk),
                      ffi.NULL)
        return handles

    def ref(self):
        pass

    def unref(self):
        # XXX: Called by _run_callbacks.
        pass

    def break_(self, how=None):
        if self.ptr:
            libuv.uv_stop(self.ptr)

    def reinit(self):
        # TODO: How to implement? We probably have to simply
        # re-__init__ this whole class? Does it matter?
        # OR maybe we need to uv_walk() and close all the handles?

        # XXX: libuv < 1.12 simply CANNOT handle a fork unless you immediately
        # exec() in the child. There are multiple calls to abort() that
        # will kill the child process:
        # - The OS X poll implementation (kqueue) aborts on an error return
        # value; since kqueue FDs can't be inherited, then the next call
        # to kqueue in the child will fail and get aborted; fork() is likely
        # to be called during the gevent loop, meaning we're deep inside the
        # runloop already, so we can't even close the loop that we're in:
        # it's too late, the next call to kqueue is already scheduled.
        # - The threadpool, should it be in use, also aborts
        # (https://github.com/joyent/libuv/pull/1136)
        # - There global shared state that breaks signal handling
        # and leads to an abort() in the child, EVEN IF the loop in the parent
        # had already been closed
        # (https://github.com/joyent/libuv/issues/1405)

        # In 1.12, the uv_loop_fork function was added (by gevent!)
        libuv.uv_loop_fork(self.ptr)

    _prepare_ran_callbacks = False

    def __run_queued_callbacks(self):
        if not self._queued_callbacks:
            return False

        cbs = self._queued_callbacks[:]
        del self._queued_callbacks[:]

        for watcher_ptr, arg in cbs:
            handle = watcher_ptr.data
            if not handle:
                # It's been stopped and possibly closed
                assert not libuv.uv_is_active(watcher_ptr)
                continue
            val = _callbacks.python_callback(handle, arg)
            if val == -1: # Failure.
                _callbacks.python_handle_error(handle, arg)
            elif val == 1: # Success, and we may need to close the Python watcher.
                if not libuv.uv_is_active(watcher_ptr):
                    # The callback closed the native watcher resources. Good.
                    # It's *supposed* to also reset the .data handle to NULL at
                    # that same time. If it resets it to something else, we're
                    # re-using the same watcher object, and that's not correct either.
                    # On Windows in particular, if the .data handle is changed because
                    # the IO multiplexer is being restarted, trying to dereference the
                    # *old* handle can crash with an FFI error.
                    handle_after_callback = watcher_ptr.data
                    try:
                        if handle_after_callback and handle_after_callback == handle:
                            _callbacks.python_stop(handle_after_callback)
                    finally:
                        watcher_ptr.data = ffi.NULL
        return True


    def run(self, nowait=False, once=False):
        # we can only respect one flag or the other.
        # nowait takes precedence because it can't block
        mode = libuv.UV_RUN_DEFAULT
        if once:
            mode = libuv.UV_RUN_ONCE
        if nowait:
            mode = libuv.UV_RUN_NOWAIT

        if mode == libuv.UV_RUN_DEFAULT:
            while self._ptr and self._ptr.data:
                # This is here to better preserve order guarantees.
                # See _run_callbacks for details.

                # It may get run again from the prepare watcher, so
                # potentially we could take twice as long as the
                # switch interval.
                # If we have *lots* of callbacks to run, we may not actually
                # get through them all before we're requested to poll for IO;
                # so in that case, just spin the loop once (UV_RUN_NOWAIT) and
                # go again.
                self._run_callbacks()
                self._prepare_ran_callbacks = False

                # UV_RUN_ONCE will poll for IO, blocking for up to the time needed
                # for the next timer to expire. Worst case, that's our _signal_idle
                # timer, about 1/3 second. UV_RUN_ONCE guarantees that some forward progress
                # is made, either by an IO watcher or a timer.
                #
                # In contrast, UV_RUN_NOWAIT makes no such guarantee, it only polls for IO once and
                # immediately returns; it does not update the loop time or timers after
                # polling for IO.
                run_mode = (
                    libuv.UV_RUN_ONCE
                    if not self._callbacks and not self._queued_callbacks
                    else libuv.UV_RUN_NOWAIT
                )

                ran_status = libuv.uv_run(self._ptr, run_mode)
                # Note that we run queued callbacks when the prepare watcher runs,
                # thus accounting for timers that expired before polling for IO,
                # and idle watchers. This next call should get IO callbacks and
                # callbacks from timers that expired *after* polling for IO.
                ran_callbacks = self.__run_queued_callbacks()

                if not ran_status and not ran_callbacks and not self._prepare_ran_callbacks:
                    # A return of 0 means there are no referenced and
                    # active handles. The loop is over.
                    # If we didn't run any callbacks, then we couldn't schedule
                    # anything to switch in the future, so there's no point
                    # running again.
                    return ran_status
            return 0 # Somebody closed the loop

        result = libuv.uv_run(self._ptr, mode)
        self.__run_queued_callbacks()
        return result

    def now(self):
        self.__check_and_die()
        # libuv's now is expressed as an integer number of
        # milliseconds, so to get it compatible with time.time units
        # that this method is supposed to return, we have to divide by 1000.0
        now = libuv.uv_now(self.ptr)
        return now / 1000.0

    def update_now(self):
        self.__check_and_die()
        libuv.uv_update_time(self.ptr)

    def fileno(self):
        if self.ptr:
            fd = libuv.uv_backend_fd(self._ptr)
            if fd >= 0:
                return fd

    _sigchld_watcher = None
    _sigchld_callback_ffi = None

    def install_sigchld(self):
        if not self.default:
            return

        if self._sigchld_watcher:
            return

        self._sigchld_watcher = ffi.new('uv_signal_t*')
        libuv.uv_signal_init(self.ptr, self._sigchld_watcher)
        self._sigchld_watcher.data = self._handle_to_self
        # Don't let this keep the loop alive
        libuv.uv_unref(self._sigchld_watcher)

        libuv.uv_signal_start(self._sigchld_watcher,
                              libuv.python_sigchld_callback,
                              signal.SIGCHLD)

    def reset_sigchld(self):
        if not self.default or not self._sigchld_watcher:
            return

        libuv.uv_signal_stop(self._sigchld_watcher)
        # Must go through this to manage the memory lifetime
        # correctly. Alternately, we could just stop it and restart
        # it in install_sigchld?
        _watchers.watcher._watcher_ffi_close(self._sigchld_watcher)
        del self._sigchld_watcher


    def _sigchld_callback(self):
        # Signals can arrive at (relatively) any time. To eliminate
        # race conditions, and behave more like libev, we "queue"
        # sigchld to run when we run callbacks.
        while True:
            try:
                pid, status, _usage = os.wait3(os.WNOHANG)
            except OSError:
                # Python 3 raises ChildProcessError
                break

            if pid == 0:
                break
            children_watchers = self._child_watchers.get(pid, []) + self._child_watchers.get(0, [])
            for watcher in children_watchers:
                self.run_callback(watcher._set_waitpid_status, pid, status)

            # Don't invoke child watchers for 0 more than once
            self._child_watchers[0] = []

    def _register_child_watcher(self, watcher):
        self._child_watchers[watcher._pid].append(watcher)

    def _unregister_child_watcher(self, watcher):
        try:
            # stop() should be idempotent
            self._child_watchers[watcher._pid].remove(watcher)
        except ValueError:
            pass

        # Now's a good time to clean up any dead watchers we don't need
        # anymore
        for pid in list(self._child_watchers):
            if not self._child_watchers[pid]:
                del self._child_watchers[pid]

    def io(self, fd, events, ref=True, priority=None):
        # We rely on hard references here and explicit calls to
        # close() on the returned object to correctly manage
        # the watcher lifetimes.

        io_watchers = self._io_watchers
        try:
            io_watcher = io_watchers[fd]
            assert io_watcher._multiplex_watchers, ("IO Watcher %s unclosed but should be dead" % io_watcher)
        except KeyError:
            # Start the watcher with just the events that we're interested in.
            # as multiplexers are added, the real event mask will be updated to keep in sync.
            # If we watch for too much, we get spurious wakeups and busy loops.
            io_watcher = self._watchers.io(self, fd, 0)
            io_watchers[fd] = io_watcher
            io_watcher._no_more_watchers = lambda: delitem(io_watchers, fd)

        return io_watcher.multiplex(events)

    def prepare(self, ref=True, priority=None):
        # We run arbitrary code in python_prepare_callback. That could switch
        # greenlets. If it does that while also manipulating the active prepare
        # watchers, we could corrupt the process state, since the prepare watcher
        # queue is iterated on the stack (on unix). We could workaround this by implementing
        # prepare watchers in pure Python.
        # See https://github.com/gevent/gevent/issues/1126
        raise TypeError("prepare watchers are not currently supported in libuv. "
                        "If you need them, please contact the maintainers.")
