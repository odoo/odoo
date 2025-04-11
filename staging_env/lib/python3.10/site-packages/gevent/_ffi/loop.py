"""
Basic loop implementation for ffi-based cores.
"""
# pylint: disable=too-many-lines, protected-access, redefined-outer-name, not-callable
from __future__ import absolute_import, print_function

from collections import deque
import sys
import os
import traceback

from gevent._ffi import _dbg
from gevent._ffi import GEVENT_DEBUG_LEVEL
from gevent._ffi import TRACE
from gevent._ffi.callback import callback
from gevent._compat import PYPY
from gevent.exceptions import HubDestroyed

from gevent import getswitchinterval

__all__ = [
    'AbstractLoop',
    'assign_standard_callbacks',
]


class _EVENTSType(object):
    def __repr__(self):
        return 'gevent.core.EVENTS'

EVENTS = GEVENT_CORE_EVENTS = _EVENTSType()


class _DiscardedSet(frozenset):
    __slots__ = ()

    def discard(self, o):
        "Does nothing."

#####
## Note on CFFI objects, callbacks and the lifecycle of watcher objects
#
# Each subclass of `watcher` allocates a C structure of the
# appropriate type e.g., struct gevent_ev_io and holds this pointer in
# its `_gwatcher` attribute. When that watcher instance is garbage
# collected, then the C structure is also freed. The C structure is
# passed to libev from the watcher's start() method and then to the
# appropriate C callback function, e.g., _gevent_ev_io_callback, which
# passes it back to python's _python_callback where we need the
# watcher instance. Therefore, as long as that callback is active (the
# watcher is started), the watcher instance must not be allowed to get
# GC'd---any access at the C level or even the FFI level to the freed
# memory could crash the process.
#
# However, the typical idiom calls for writing something like this:
#  loop.io(fd, python_cb).start()
# thus forgetting the newly created watcher subclass and allowing it to be immediately
# GC'd. To combat this, when the watcher is started, it places itself into the loop's
# `_keepaliveset`, and it only removes itself when the watcher's `stop()` method is called.
# Often, this is the *only* reference keeping the watcher object, and hence its C structure,
# alive.
#
# This is slightly complicated by the fact that the python-level
# callback, called from the C callback, could choose to manually stop
# the watcher. When we return to the C level callback, we now have an
# invalid pointer, and attempting to pass it back to Python (e.g., to
# handle an error) could crash. Hence, _python_callback,
# _gevent_io_callback, and _python_handle_error cooperate to make sure
# that the watcher instance stays in the loops `_keepaliveset` while
# the C code could be running---and if it gets removed, to not call back
# to Python again.
# See also https://github.com/gevent/gevent/issues/676
####
class AbstractCallbacks(object):


    def __init__(self, ffi):
        self.ffi = ffi
        self.callbacks = []
        if GEVENT_DEBUG_LEVEL < TRACE:
            self.from_handle = ffi.from_handle

    def from_handle(self, handle): # pylint:disable=method-hidden
        x = self.ffi.from_handle(handle)
        return x

    def python_callback(self, handle, revents):
        """
        Returns an integer having one of three values:

        - -1
          An exception occurred during the callback and you must call
          :func:`_python_handle_error` to deal with it. The Python watcher
          object will have the exception tuple saved in ``_exc_info``.
        - 1
          Everything went according to plan. You should check to see if the native
          watcher is still active, and call :func:`python_stop` if it is not. This will
          clean up the memory. Finding the watcher still active at the event loop level,
          but not having stopped itself at the gevent level is a buggy scenario and
          shouldn't happen.
        - 2
          Everything went according to plan, but the watcher has already
          been stopped. Its memory may no longer be valid.

        This function should never return 0, as that's the default value that
        Python exceptions will produce.
        """
        #_dbg("Running callback", handle)
        orig_ffi_watcher = None
        orig_loop = None
        try:
            # Even dereferencing the handle needs to be inside the try/except;
            # if we don't return normally (e.g., a signal) then we wind up going
            # to the 'onerror' handler (unhandled_onerror), which
            # is not what we want; that can permanently wedge the loop depending
            # on which callback was executing.
            # XXX: See comments in that function. We may be able to restart and do better?
            if not handle:
                # Hmm, a NULL handle. That's not supposed to happen.
                # We can easily get into a loop if we deref it and allow that
                # to raise.
                _dbg("python_callback got null handle")
                return 1
            the_watcher = self.from_handle(handle)
            orig_ffi_watcher = the_watcher._watcher
            orig_loop = the_watcher.loop
            args = the_watcher.args
            if args is None:
                # Legacy behaviour from corecext: convert None into ()
                # See test__core_watcher.py
                args = _NOARGS
            if args and args[0] == GEVENT_CORE_EVENTS:
                args = (revents, ) + args[1:]
            the_watcher.callback(*args) # None here means we weren't started
        except: # pylint:disable=bare-except
            # It's possible for ``the_watcher`` to be undefined (UnboundLocalError)
            # if we threw an exception (signal) on the line that created that variable.
            # This is typically the case with a signal under libuv
            try:
                the_watcher
            except UnboundLocalError:
                the_watcher = self.from_handle(handle)

            # It may not be safe to do anything with `handle` or `orig_ffi_watcher`
            # anymore. If the watcher closed or stopped itself *before* throwing the exception,
            # then the `handle` and `orig_ffi_watcher` may no longer be valid. Attempting to
            # e.g., dereference the handle is likely to crash the process.
            the_watcher._exc_info = sys.exc_info()


            # If it hasn't been stopped, we need to make sure its
            # memory stays valid so we can stop it at the native level if needed.
            # If its loop is gone, it has already been stopped,
            # see https://github.com/gevent/gevent/issues/1295 for a case where
            # that happened, as well as issue #1482
            if (
                    # The last thing it does. Full successful close.
                    the_watcher.loop is None
                    # Only a partial close. We could leak memory and even crash later.
                    or the_watcher._handle is None
            ):
                # Prevent unhandled_onerror from using the invalid handle
                handle = None
                exc_info = the_watcher._exc_info
                del the_watcher._exc_info
                try:
                    if orig_loop is not None:
                        orig_loop.handle_error(the_watcher, *exc_info)
                    else:
                        self.unhandled_onerror(*exc_info)
                except:
                    print("WARNING: gevent: Error when handling error",
                          file=sys.stderr)
                    traceback.print_exc()
                # Signal that we're closed, no need to do more.
                return 2

            # Keep it around so we can close it later.
            the_watcher.loop._keepaliveset.add(the_watcher)
            return -1

        if (the_watcher.loop is not None
                and the_watcher in the_watcher.loop._keepaliveset
                and the_watcher._watcher is orig_ffi_watcher):
            # It didn't stop itself, *and* it didn't stop itself, reset
            # its watcher, and start itself again. libuv's io watchers
            # multiplex and may do this.

            # The normal, expected scenario when we find the watcher still
            # in the keepaliveset is that it is still active at the event loop
            # level, so we don't expect that python_stop gets called.
            #_dbg("The watcher has not stopped itself, possibly still active", the_watcher)
            return 1
        return 2 # it stopped itself

    def python_handle_error(self, handle, _revents):
        _dbg("Handling error for handle", handle)
        if not handle:
            return
        try:
            watcher = self.from_handle(handle)
            exc_info = watcher._exc_info
            del watcher._exc_info
            # In the past, we passed the ``watcher`` itself as the context,
            # which typically meant that the Hub would just print
            # the exception. This is a problem because sometimes we can't
            # detect signals until late in ``python_callback``; specifically,
            # test_selectors.py:DefaultSelectorTest.test_select_interrupt_exc
            # installs a SIGALRM handler that raises an exception. That exception can happen
            # before we enter ``python_callback`` or at any point within it because of the way
            # libuv swallows signals. By passing None, we get the exception prapagated into
            # the main greenlet (which is probably *also* not what we always want, but
            # I see no way to distinguish the cases).
            watcher.loop.handle_error(None, *exc_info)
        finally:
            # XXX Since we're here on an error condition, and we
            # made sure that the watcher object was put in loop._keepaliveset,
            # what about not stopping the watcher? Looks like a possible
            # memory leak?
            # XXX: This used to do "if revents & (libev.EV_READ | libev.EV_WRITE)"
            # before stopping. Why?
            try:
                watcher.stop()
            except: # pylint:disable=bare-except
                watcher.loop.handle_error(watcher, *sys.exc_info())
            return # pylint:disable=lost-exception

    def unhandled_onerror(self, t, v, tb):
        # This is supposed to be called for signals, etc.
        # This is the onerror= value for CFFI.
        # If we return None, C will get a value of 0/NULL;
        # if we raise, CFFI will print the exception and then
        # return 0/NULL; (unless error= was configured)
        # If things go as planned, we return the value that asks
        # C to call back and check on if the watcher needs to be closed or
        # not.

        # XXX: TODO: Could this cause events to be lost? Maybe we need to return
        # a value that causes the C loop to try the callback again?
        # at least for signals under libuv, which are delivered at very odd times.
        # Hopefully the event still shows up when we poll the next time.
        watcher = None
        handle = tb.tb_frame.f_locals.get('handle') if tb is not None else None
        if handle: # handle could be NULL
            watcher = self.from_handle(handle)
        if watcher is not None:
            watcher.loop.handle_error(None, t, v, tb)
            return 1

        # Raising it causes a lot of noise from CFFI
        print("WARNING: gevent: Unhandled error with no watcher",
              file=sys.stderr)
        traceback.print_exception(t, v, tb)

    def python_stop(self, handle):
        if not handle: # pragma: no cover
            print(
                "WARNING: gevent: Unable to dereference handle; not stopping watcher. "
                "Native resources may leak. This is most likely a bug in gevent.",
                file=sys.stderr)
            # The alternative is to crash with no helpful information
            # NOTE: Raising exceptions here does nothing, they're swallowed by CFFI.
            # Since the C level passed in a null pointer, even dereferencing the handle
            # will just produce some exceptions.
            return
        watcher = self.from_handle(handle)
        watcher.stop()

    if not PYPY:
        def python_check_callback(self, watcher_ptr): # pylint:disable=unused-argument
            # If we have the onerror callback, this is a no-op; all the real
            # work to rethrow the exception is done by the onerror callback

            # NOTE: Unlike the rest of the functions, this is called with a pointer
            # to the C level structure, *not* a pointer to the void* that represents a
            # <cdata> for the Python Watcher object.
            pass
    else: # PyPy
        # On PyPy, we need the function to have some sort of body, otherwise
        # the signal exceptions don't always get caught, *especially* with
        # libuv (however, there's no reason to expect this to only be a libuv
        # issue; it's just that we don't depend on the periodic signal timer
        # under libev, so the issue is much more pronounced under libuv)
        # test_socket's test_sendall_interrupted can hang.
        # See https://github.com/gevent/gevent/issues/1112

        def python_check_callback(self, watcher_ptr): # pylint:disable=unused-argument
            # Things we've tried that *don't* work:
            # greenlet.getcurrent()
            # 1 + 1
            try:
                raise MemoryError()
            except MemoryError:
                pass

    def python_prepare_callback(self, watcher_ptr):
        loop = self._find_loop_from_c_watcher(watcher_ptr)
        if loop is None: # pragma: no cover
            print("WARNING: gevent: running prepare callbacks from a destroyed handle: ",
                  watcher_ptr)
            return
        loop._run_callbacks()

    def check_callback_onerror(self, t, v, tb):
        watcher_ptr = self._find_watcher_ptr_in_traceback(tb)
        if watcher_ptr:
            loop = self._find_loop_from_c_watcher(watcher_ptr)
        if loop is not None:
            # None as the context argument causes the exception to be raised
            # in the main greenlet.
            loop.handle_error(None, t, v, tb)
            return None
        raise v # Let CFFI print

    def _find_loop_from_c_watcher(self, watcher_ptr):
        raise NotImplementedError()

    def _find_watcher_ptr_in_traceback(self, tb):
        return tb.tb_frame.f_locals['watcher_ptr'] if tb is not None else None


def assign_standard_callbacks(ffi, lib, callbacks_class, extras=()): # pylint:disable=unused-argument
    """
    Given the typical *ffi* and *lib* arguments, and a subclass of :class:`AbstractCallbacks`
    in *callbacks_class*, set up the ``def_extern`` Python callbacks from C
    into an instance of *callbacks_class*.

    :param tuple extras: If given, this is a sequence of ``(name, error_function)``
      additional callbacks to register. Each *name* is an attribute of
      the *callbacks_class* instance. (Each element cas also be just a *name*.)
    :return: The *callbacks_class* instance. This object must be kept alive,
      typically at module scope.
    """
    # callbacks keeps these cdata objects alive at the python level
    callbacks = callbacks_class(ffi)
    extras = [extra if len(extra) == 2 else (extra, None) for extra in extras]
    extras = tuple((getattr(callbacks, name), error) for name, error in extras)
    for (func, error_func) in (
            (callbacks.python_callback, None),
            (callbacks.python_handle_error, None),
            (callbacks.python_stop, None),
            (callbacks.python_check_callback, callbacks.check_callback_onerror),
            (callbacks.python_prepare_callback, callbacks.check_callback_onerror)
    ) + extras:
        # The name of the callback function matches the 'extern Python' declaration.
        error_func = error_func or callbacks.unhandled_onerror
        callback = ffi.def_extern(onerror=error_func)(func)
        # keep alive the cdata
        # (def_extern returns the original function, and it requests that
        # the function be "global", so maybe it keeps a hard reference to it somewhere now
        # unlike ffi.callback(), and we don't need to do this?)
        callbacks.callbacks.append(callback)

        # At this point, the library C variable (static function, actually)
        # is filled in.

    return callbacks


if sys.version_info[0] >= 3:
    basestring = (bytes, str)
    integer_types = (int,)
else:
    import __builtin__ # pylint:disable=import-error
    basestring = (__builtin__.basestring,)
    integer_types = (int, __builtin__.long)




_NOARGS = ()


class AbstractLoop(object):
    # pylint:disable=too-many-public-methods,too-many-instance-attributes

    # How many callbacks we should run between checking against the
    # switch interval.
    CALLBACK_CHECK_COUNT = 50

    error_handler = None

    _CHECK_POINTER = None

    _TIMER_POINTER = None
    _TIMER_CALLBACK_SIG = None

    _PREPARE_POINTER = None

    starting_timer_may_update_loop_time = False

    # Subclasses should set this in __init__ to reflect
    # whether they were the default loop.
    _default = None

    _keepaliveset = _DiscardedSet()
    _threadsafe_async = None

    def __init__(self, ffi, lib, watchers, flags=None, default=None):
        self._ffi = ffi
        self._lib = lib
        self._ptr = None
        self._handle_to_self = self._ffi.new_handle(self) # XXX: Reference cycle?
        self._watchers = watchers
        self._in_callback = False
        self._callbacks = deque()
        # Stores python watcher objects while they are started
        self._keepaliveset = set()
        self._init_loop_and_aux_watchers(flags, default)

    def _init_loop_and_aux_watchers(self, flags=None, default=None):
        self._ptr = self._init_loop(flags, default)

        # self._check is a watcher that runs in each iteration of the
        # mainloop, just after the blocking call. It's point is to handle
        # signals. It doesn't run watchers or callbacks, it just exists to give
        # CFFI a chance to raise signal exceptions so we can handle them.
        self._check = self._ffi.new(self._CHECK_POINTER)
        self._check.data = self._handle_to_self
        self._init_and_start_check()

        # self._prepare is a watcher that runs in each iteration of the mainloop,
        # just before the blocking call. It's where we run deferred callbacks
        # from self.run_callback. This cooperates with _setup_for_run_callback()
        # to schedule self._timer0 if needed.
        self._prepare = self._ffi.new(self._PREPARE_POINTER)
        self._prepare.data = self._handle_to_self
        self._init_and_start_prepare()

        # A timer we start and stop on demand. If we have callbacks,
        # too many to run in one iteration of _run_callbacks, we turn this
        # on so as to have the next iteration of the run loop return to us
        # as quickly as possible.
        # TODO: There may be a more efficient way to do this using ev_timer_again;
        # see the "ev_timer" section of the ev manpage (http://linux.die.net/man/3/ev)
        # Alternatively, setting the ev maximum block time may also work.
        self._timer0 = self._ffi.new(self._TIMER_POINTER)
        self._timer0.data = self._handle_to_self
        self._init_callback_timer()

        self._threadsafe_async = self.async_(ref=False)
        # No need to do anything with this on ``fork()``, both libev and libuv
        # take care of creating a new pipe in their respective ``loop_fork()`` methods.
        self._threadsafe_async.start(lambda: None)
        # TODO: We may be able to do something nicer and use the existing python_callback
        # combined with onerror and the class check/timer/prepare to simplify things
        # and unify our handling

    def _init_loop(self, flags, default):
        """
        Called by __init__ to create or find the loop. The return value
        is assigned to self._ptr.
        """
        raise NotImplementedError()

    def _init_and_start_check(self):
        raise NotImplementedError()

    def _init_and_start_prepare(self):
        raise NotImplementedError()

    def _init_callback_timer(self):
        raise NotImplementedError()

    def _stop_callback_timer(self):
        raise NotImplementedError()

    def _start_callback_timer(self):
        raise NotImplementedError()

    def _check_callback_handle_error(self, t, v, tb):
        self.handle_error(None, t, v, tb)

    def _run_callbacks(self): # pylint:disable=too-many-branches
        # When we're running callbacks, its safe for timers to
        # update the notion of the current time (because if we're here,
        # we're not running in a timer callback that may let other timers
        # run; this is mostly an issue for libuv).

        # That's actually a bit of a lie: on libev, self._timer0 really is
        # a timer, and so sometimes this is running in a timer callback, not
        # a prepare callback. But that's OK, libev doesn't suffer from cascading
        # timer expiration and its safe to update the loop time at any
        # moment there.
        self.starting_timer_may_update_loop_time = True
        try:
            count = self.CALLBACK_CHECK_COUNT
            now = self.now()
            expiration = now + getswitchinterval()
            self._stop_callback_timer()
            while self._callbacks:
                cb = self._callbacks.popleft() # pylint:disable=assignment-from-no-return
                count -= 1
                self.unref() # XXX: libuv doesn't have a global ref count!
                callback = cb.callback
                cb.callback = None
                args = cb.args
                if callback is None or args is None:
                    # it's been stopped
                    continue

                try:
                    callback(*args)
                except: # pylint:disable=bare-except
                    # If we allow an exception to escape this method (while we are running the ev callback),
                    # then CFFI will print the error and libev will continue executing.
                    # There are two problems with this. The first is that the code after
                    # the loop won't run. The second is that any remaining callbacks scheduled
                    # for this loop iteration will be silently dropped; they won't run, but they'll
                    # also not be *stopped* (which is not a huge deal unless you're looking for
                    # consistency or checking the boolean/pending status; the loop doesn't keep
                    # a reference to them like it does to watchers...*UNLESS* the callback itself had
                    # a reference to a watcher; then I don't know what would happen, it depends on
                    # the state of the watcher---a leak or crash is not totally inconceivable).
                    # The Cython implementation in core.ppyx uses gevent_call from callbacks.c
                    # to run the callback, which uses gevent_handle_error to handle any errors the
                    # Python callback raises...it unconditionally simply prints any error raised
                    # by loop.handle_error and clears it, so callback handling continues.
                    # We take a similar approach (but are extra careful about printing)
                    try:
                        self.handle_error(cb, *sys.exc_info())
                    except: # pylint:disable=bare-except
                        try:
                            print("Exception while handling another error", file=sys.stderr)
                            traceback.print_exc()
                        except: # pylint:disable=bare-except
                            pass # Nothing we can do here
                finally:
                    # NOTE: this must be reset here, because cb.args is used as a flag in
                    # the callback class so that bool(cb) of a callback that has been run
                    # becomes False
                    cb.args = None

                # We've finished running one group of callbacks
                # but we may have more, so before looping check our
                # switch interval.
                if count == 0 and self._callbacks:
                    count = self.CALLBACK_CHECK_COUNT
                    self.update_now()
                    if self.now() >= expiration:
                        now = 0
                        break

            # Update the time before we start going again, if we didn't
            # just do so.
            if now != 0:
                self.update_now()

            if self._callbacks:
                self._start_callback_timer()
        finally:
            self.starting_timer_may_update_loop_time = False

    def _stop_aux_watchers(self):
        if self._threadsafe_async is not None:
            self._threadsafe_async.close()
            self._threadsafe_async = None

    def destroy(self):
        ptr = self.ptr
        if ptr:
            try:
                if not self._can_destroy_loop(ptr):
                    return False
                self._stop_aux_watchers()
                self._destroy_loop(ptr)
            finally:
                # not ffi.NULL, we don't want something that can be
                # passed to C and crash later. This will create nice friendly
                # TypeError from CFFI.
                self._ptr = None
                del self._handle_to_self
                del self._callbacks
                del self._keepaliveset

            return True

    def _can_destroy_loop(self, ptr):
        raise NotImplementedError()

    def _destroy_loop(self, ptr):
        raise NotImplementedError()

    @property
    def ptr(self):
        # Use this when you need to be sure the pointer is valid.
        return self._ptr

    @property
    def WatcherType(self):
        return self._watchers.watcher

    @property
    def MAXPRI(self):
        return 1

    @property
    def MINPRI(self):
        return 1

    def _handle_syserr(self, message, errno):
        try:
            errno = os.strerror(errno)
        except: # pylint:disable=bare-except
            traceback.print_exc()
        try:
            message = '%s: %s' % (message, errno)
        except: # pylint:disable=bare-except
            traceback.print_exc()
        self.handle_error(None, SystemError, SystemError(message), None)

    def handle_error(self, context, type, value, tb):
        if type is HubDestroyed:
            self._callbacks.clear()
            self.break_()
            return

        handle_error = None
        error_handler = self.error_handler
        if error_handler is not None:
            # we do want to do getattr every time so that setting Hub.handle_error property just works
            handle_error = getattr(error_handler, 'handle_error', error_handler)
            handle_error(context, type, value, tb)
        else:
            self._default_handle_error(context, type, value, tb)

    def _default_handle_error(self, context, type, value, tb): # pylint:disable=unused-argument
        # note: Hub sets its own error handler so this is not used by gevent
        # this is here to make core.loop usable without the rest of gevent
        # Should cause the loop to stop running.
        traceback.print_exception(type, value, tb)


    def run(self, nowait=False, once=False):
        raise NotImplementedError()

    def reinit(self):
        raise NotImplementedError()

    def ref(self):
        # XXX: libuv doesn't do it this way
        raise NotImplementedError()

    def unref(self):
        raise NotImplementedError()

    def break_(self, how=None):
        raise NotImplementedError()

    def verify(self):
        pass

    def now(self):
        raise NotImplementedError()

    def update_now(self):
        raise NotImplementedError()

    def update(self):
        import warnings
        warnings.warn("'update' is deprecated; use 'update_now'",
                      DeprecationWarning,
                      stacklevel=2)
        self.update_now()

    def __repr__(self):
        return '<%s.%s at 0x%x %s>' % (
            self.__class__.__module__,
            self.__class__.__name__,
            id(self),
            self._format()
        )

    @property
    def default(self):
        return self._default if self.ptr else False

    @property
    def iteration(self):
        return -1

    @property
    def depth(self):
        return -1

    @property
    def backend_int(self):
        return 0

    @property
    def backend(self):
        return "default"

    @property
    def pendingcnt(self):
        return 0

    def io(self, fd, events, ref=True, priority=None):
        return self._watchers.io(self, fd, events, ref, priority)

    def closing_fd(self, fd): # pylint:disable=unused-argument
        return False

    def timer(self, after, repeat=0.0, ref=True, priority=None):
        return self._watchers.timer(self, after, repeat, ref, priority)

    def signal(self, signum, ref=True, priority=None):
        return self._watchers.signal(self, signum, ref, priority)

    def idle(self, ref=True, priority=None):
        return self._watchers.idle(self, ref, priority)

    def prepare(self, ref=True, priority=None):
        return self._watchers.prepare(self, ref, priority)

    def check(self, ref=True, priority=None):
        return self._watchers.check(self, ref, priority)

    def fork(self, ref=True, priority=None):
        return self._watchers.fork(self, ref, priority)

    def async_(self, ref=True, priority=None):
        return self._watchers.async_(self, ref, priority)

    # Provide BWC for those that can use 'async' as is
    locals()['async'] = async_

    if sys.platform != "win32":

        def child(self, pid, trace=0, ref=True):
            return self._watchers.child(self, pid, trace, ref)

        def install_sigchld(self):
            pass

    def stat(self, path, interval=0.0, ref=True, priority=None):
        return self._watchers.stat(self, path, interval, ref, priority)

    def callback(self, priority=None):
        return callback(self, priority)

    def _setup_for_run_callback(self):
        raise NotImplementedError()

    def run_callback(self, func, *args):
        # If we happen to already be running callbacks (inside
        # _run_callbacks), this could happen almost immediately,
        # without the loop cycling.
        cb = callback(func, args)
        self._callbacks.append(cb) # Relying on the GIL for this to be threadsafe
        self._setup_for_run_callback() # XXX: This may not be threadsafe.
        return cb

    def run_callback_threadsafe(self, func, *args):
        cb = self.run_callback(func, *args)
        self._threadsafe_async.send()
        return cb

    def _format(self):
        ptr = self.ptr
        if not ptr:
            return 'destroyed'
        msg = "backend=" + self.backend
        msg += ' ptr=' + str(ptr)
        if self.default:
            msg += ' default'
        msg += ' pending=%s' % self.pendingcnt
        msg += self._format_details()
        return msg

    def _format_details(self):
        msg = ''
        fileno = self.fileno() # pylint:disable=assignment-from-none
        try:
            activecnt = self.activecnt
        except AttributeError:
            activecnt = None
        if activecnt is not None:
            msg += ' ref=' + repr(activecnt)
        if fileno is not None:
            msg += ' fileno=' + repr(fileno)
        #if sigfd is not None and sigfd != -1:
        #    msg += ' sigfd=' + repr(sigfd)
        msg += ' callbacks=' + str(len(self._callbacks))
        return msg

    def fileno(self):
        return None

    @property
    def activecnt(self):
        if not self.ptr:
            raise ValueError('operation on destroyed loop')
        return 0
