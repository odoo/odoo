# cython: auto_pickle=False,embedsignature=True,always_allow_keywords=False
###
# This file is ``gevent._semaphore`` so that it can be compiled by Cython
# individually. However, this is not the place to import from. Everyone,
# gevent internal code included, must import from ``gevent.lock``.
# The only exception are .pxd files which need access to the
# C code; the PURE_PYTHON things that have to happen and which are
# handled in ``gevent.lock``, do not apply to them.
###
from __future__ import print_function, absolute_import, division

__all__ = [
    'Semaphore',
    'BoundedSemaphore',
]

from time import sleep as _native_sleep

from gevent._compat import monotonic
from gevent.exceptions import InvalidThreadUseError
from gevent.exceptions import LoopExit
from gevent.timeout import Timeout

def _get_linkable():
    x = __import__('gevent._abstract_linkable')
    return x._abstract_linkable.AbstractLinkable
locals()['AbstractLinkable'] = _get_linkable()
del _get_linkable

from gevent._hub_local import get_hub_if_exists
from gevent._hub_local import get_hub
from gevent.hub import spawn_raw

class _LockReleaseLink(object):
    __slots__ = (
        'lock',
    )

    def __init__(self, lock):
        self.lock = lock

    def __call__(self, _):
        self.lock.release()

_UNSET = object()
_MULTI = object()

class Semaphore(AbstractLinkable): # pylint:disable=undefined-variable
    """
    Semaphore(value=1) -> Semaphore

    .. seealso:: :class:`BoundedSemaphore` for a safer version that prevents
       some classes of bugs. If unsure, most users should opt for `BoundedSemaphore`.

    A semaphore manages a counter representing the number of `release`
    calls minus the number of `acquire` calls, plus an initial value.
    The `acquire` method blocks if necessary until it can return
    without making the counter negative. A semaphore does not track ownership
    by greenlets; any greenlet can call `release`, whether or not it has previously
    called `acquire`.

    If not given, ``value`` defaults to 1.

    The semaphore is a context manager and can be used in ``with`` statements.

    This Semaphore's ``__exit__`` method does not call the trace function
    on CPython, but does under PyPy.

    .. versionchanged:: 1.4.0
        Document that the order in which waiters are awakened is not specified. It was not
        specified previously, but due to CPython implementation quirks usually went in FIFO order.
    .. versionchanged:: 1.5a3
       Waiting greenlets are now awakened in the order in which they waited.
    .. versionchanged:: 1.5a3
       The low-level ``rawlink`` method (most users won't use this) now automatically
       unlinks waiters before calling them.
    .. versionchanged:: 20.12.0
       Improved support for multi-threaded usage. When multi-threaded usage is detected,
       instances will no longer create the thread's hub if it's not present.

    .. versionchanged:: 24.2.1
       Uses Python 3 native lock timeouts for cross-thread operations instead
       of spinning.
    """

    __slots__ = (
        'counter',
        # long integer, signed (Py2) or unsigned (Py3); see comments
        # in the .pxd file for why we store as Python object. Set to ``_UNSET``
        # initially. Set to the ident of the first thread that
        # acquires us. If we later see a different thread ident, set
        # to ``_MULTI``.
        '_multithreaded',
    )

    def __init__(self, value=1, hub=None):
        self.counter = value
        if self.counter < 0: # Do the check after Cython native int conversion
            raise ValueError("semaphore initial value must be >= 0")
        super(Semaphore, self).__init__(hub)
        self._notify_all = False
        self._multithreaded = _UNSET

    def __str__(self):
        return '<%s at 0x%x counter=%s _links[%s]>' % (
            self.__class__.__name__,
            id(self),
            self.counter,
            self.linkcount()
        )

    def locked(self):
        """
        Return a boolean indicating whether the semaphore can be
        acquired (`False` if the semaphore *can* be acquired). Most
        useful with binary semaphores (those with an initial value of 1).

        :rtype: bool
        """
        return self.counter <= 0

    def release(self):
        """
        Release the semaphore, notifying any waiters if needed. There
        is no return value.

        .. note::

            This can be used to over-release the semaphore.
            (Release more times than it has been acquired or was initially
            created with.)

            This is usually a sign of a bug, but under some circumstances it can be
            used deliberately, for example, to model the arrival of additional
            resources.

        :rtype: None
        """
        self.counter += 1
        self._check_and_notify()
        return self.counter

    def ready(self):
        """
        Return a boolean indicating whether the semaphore can be
        acquired (`True` if the semaphore can be acquired).

        :rtype: bool
        """
        return self.counter > 0

    def _start_notify(self):
        self._check_and_notify()

    def _wait_return_value(self, waited, wait_success):
        if waited:
            return wait_success
        # We didn't even wait, we must be good to go.
        # XXX: This is probably dead code, we're careful not to go into the wait
        # state if we don't expect to need to
        return True

    def wait(self, timeout=None):
        """
        Wait until it is possible to acquire this semaphore, or until the optional
        *timeout* elapses.

        .. note:: If this semaphore was initialized with a *value* of 0,
           this method will block forever if no timeout is given.

        :keyword float timeout: If given, specifies the maximum amount of seconds
           this method will block.
        :return: A number indicating how many times the semaphore can be acquired
            before blocking. *This could be 0,* if other waiters acquired
            the semaphore.
        :rtype: int
        """
        if self.counter > 0:
            return self.counter

        self._wait(timeout) # return value irrelevant, whether we got it or got a timeout
        return self.counter

    def acquire(self, blocking=True, timeout=None):
        """
        acquire(blocking=True, timeout=None) -> bool

        Acquire the semaphore.

        .. note:: If this semaphore was initialized with a *value* of 0,
           this method will block forever (unless a timeout is given or blocking is
           set to false).

        :keyword bool blocking: If True (the default), this function will block
           until the semaphore is acquired.
        :keyword float timeout: If given, and *blocking* is true,
           specifies the maximum amount of seconds
           this method will block.
        :return: A `bool` indicating whether the semaphore was acquired.
           If ``blocking`` is True and ``timeout`` is None (the default), then
           (so long as this semaphore was initialized with a size greater than 0)
           this will always return True. If a timeout was given, and it expired before
           the semaphore was acquired, False will be returned. (Note that this can still
           raise a ``Timeout`` exception, if some other caller had already started a timer.)
        """
        # pylint:disable=too-many-return-statements,too-many-branches
        # Sadly, the body of this method is rather complicated.
        if self._multithreaded is _UNSET:
            self._multithreaded = self._get_thread_ident()
        elif self._multithreaded != self._get_thread_ident():
            self._multithreaded = _MULTI

        # We conceptually now belong to the hub of the thread that
        # called this, whether or not we have to block. Note that we
        # cannot force it to be created yet, because Semaphore is used
        # by importlib.ModuleLock which is used when importing the hub
        # itself! This also checks for cross-thread issues.
        invalid_thread_use = None
        try:
            self._capture_hub(False)
        except InvalidThreadUseError as e:
            # My hub belongs to some other thread. We didn't release the GIL/object lock
            # by raising the exception, so we know this is still true.
            invalid_thread_use = e.args
            e = None
            if not self.counter and blocking:
                # We would need to block. So coordinate with the main hub.
                return self.__acquire_from_other_thread(invalid_thread_use, blocking, timeout)

        if self.counter > 0:
            self.counter -= 1
            return True

        if not blocking:
            return False

        if self._multithreaded is not _MULTI and self.hub is None: # pylint:disable=access-member-before-definition
            self.hub = get_hub() # pylint:disable=attribute-defined-outside-init

        if self.hub is None and not invalid_thread_use:
            # Someone else is holding us. There's not a hub here,
            # nor is there a hub in that thread. We'll need to use regular locks.
            # This will be unfair to yet a third thread that tries to use us with greenlets.
            return self.__acquire_from_other_thread(
                (None, None, self._getcurrent(), "NoHubs"),
                blocking,
                timeout
            )

        # self._wait may drop both the GIL and the _lock_lock.
        # By the time we regain control, both have been reacquired.
        try:
            success = self._wait(timeout)
        except LoopExit as ex:
            args = ex.args
            ex = None
            if self.counter:
                success = True
            else:
                # Avoid using ex.hub property to keep holding the GIL
                if len(args) == 3 and args[1].main_hub:
                    # The main hub, meaning the main thread. We probably can do nothing with this.
                    raise
                return self.__acquire_from_other_thread(
                    (self.hub, get_hub_if_exists(), self._getcurrent(), "LoopExit"),
                    blocking,
                    timeout)

        if not success:
            assert timeout is not None
            # Our timer expired.
            return False

        # Neither our timer or another one expired, so we blocked until
        # awoke. Therefore, the counter is ours
        assert self.counter > 0, (self.counter, blocking, timeout, success,)
        self.counter -= 1
        return True

    _py3k_acquire = acquire # PyPy needs this; it must be static for Cython

    def __enter__(self):
        self.acquire()

    def __exit__(self, t, v, tb):
        self.release()

    def _handle_unswitched_notifications(self, unswitched):
        # If we fail to switch to a greenlet in another thread to send
        # a notification, just re-queue it, in the hopes that the
        # other thread will eventually run notifications itself.
        #
        # We CANNOT do what the ``super()`` does and actually allow
        # this notification to get run sometime in the future by
        # scheduling a callback in the other thread. The algorithm
        # that we use to handle cross-thread locking/unlocking was
        # designed before the schedule-a-callback mechanism was
        # implemented. If we allow this to be run as a callback, we
        # can find ourself the victim of ``InvalidSwitchError`` (or
        # worse, silent corruption) because the switch can come at an
        # unexpected time: *after* the destination thread has already
        # acquired the lock.
        #
        # This manifests in a fairly reliable test failure,
        # ``gevent.tests.test__semaphore``
        # ``TestSemaphoreMultiThread.test_dueling_threads_with_hub``,
        # but ONLY when running in PURE_PYTHON mode.
        #
        # TODO: Maybe we can rewrite that part of the algorithm to be friendly to
        # running the callbacks?
        self._links.extend(unswitched)

    def __add_link(self, link):
        if not self._notifier:
            self.rawlink(link)
        else:
            self._notifier.args[0].append(link)

    def __acquire_from_other_thread(self, ex_args, blocking, timeout):
        assert blocking
        # Some other hub owns this object. We must ask it to wake us
        # up. In general, we can't use a Python-level ``Lock`` because
        #
        # (1) it doesn't support a timeout on all platforms; and
        # (2) we don't want to block this hub from running.
        #
        # So we need to do so in a way that cooperates with *two*
        # hubs. That's what an async watcher is built for.
        #
        # Of course, if we don't actually have two hubs, then we must find some other
        # solution. That involves using a lock.

        # We have to take an action that drops the GIL and drops the object lock
        # to allow the main thread (the thread for our hub) to advance.
        owning_hub = ex_args[0]
        hub_for_this_thread = ex_args[1]
        current_greenlet = ex_args[2]

        if owning_hub is None and hub_for_this_thread is None:
            return self.__acquire_without_hubs(timeout)

        if hub_for_this_thread is None:
            # Probably a background worker thread. We don't want to create
            # the hub if not needed, and since it didn't exist there are no
            # other greenlets that we could yield to anyway, so there's nothing
            # to block and no reason to try to avoid blocking, so using a native
            # lock is the simplest way to go.
            return self.__acquire_using_other_hub(owning_hub, timeout)

        # We have a hub we don't want to block. Use an async watcher
        # and ask the next releaser of this object to wake us up.
        return self.__acquire_using_two_hubs(hub_for_this_thread,
                                             current_greenlet,
                                             timeout)

    def __acquire_using_two_hubs(self,
                                 hub_for_this_thread,
                                 current_greenlet,
                                 timeout):
        # Allocating and starting the watcher *could* release the GIL.
        # with the libev corcext, allocating won't, but starting briefly will.
        # With other backends, allocating might, and starting might also.
        # So...
        watcher = hub_for_this_thread.loop.async_()
        send = watcher.send_ignoring_arg
        watcher.start(current_greenlet.switch, self)
        try:
            with Timeout._start_new_or_dummy(timeout) as timer:
                # ... now that we're back holding the GIL, we need to verify our
                # state.
                try:
                    while 1:
                        if self.counter > 0:
                            self.counter -= 1
                            assert self.counter >= 0, (self,)
                            return True

                        self.__add_link(send)

                        # Releases the object lock
                        self._switch_to_hub(hub_for_this_thread)
                        # We waited and got notified. We should be ready now, so a non-blocking
                        # acquire() should succeed. But sometimes we get spurious notifications?
                        # It's not entirely clear how. So we need to loop until we get it, or until
                        # the timer expires
                        result = self.acquire(0)
                        if result:
                            return result
                except Timeout as tex:
                    if tex is not timer:
                        raise
                    return False
        finally:
            self._quiet_unlink_all(send)
            watcher.stop()
            watcher.close()

    def __acquire_from_other_thread_cb(self, results, blocking, timeout, thread_lock):
        try:
            result = self.acquire(blocking, timeout)
            results.append(result)
        finally:
            thread_lock.release()
        return result

    def __acquire_using_other_hub(self, owning_hub, timeout):
        assert owning_hub is not get_hub_if_exists()
        thread_lock = self._allocate_lock()
        thread_lock.acquire()
        results = []

        owning_hub.loop.run_callback_threadsafe(
            spawn_raw,
            self.__acquire_from_other_thread_cb,
            results,
            1,       # blocking,
            timeout, # timeout,
            thread_lock)

        # We MUST use a blocking acquire here, or at least be sure we keep going
        # until we acquire it. If we timed out waiting here,
        # just before the callback runs, then we would be out of sync.
        self.__spin_on_native_lock(thread_lock, None)
        return results[0]

    def __acquire_without_hubs(self, timeout):
        thread_lock = self._allocate_lock()
        thread_lock.acquire()
        absolute_expiration = 0
        begin = 0
        if timeout:
            absolute_expiration = monotonic() + timeout

        # Cython won't compile a lambda here
        link = _LockReleaseLink(thread_lock)
        while 1:
            self.__add_link(link)
            if absolute_expiration:
                begin = monotonic()

            got_native = self.__spin_on_native_lock(thread_lock, timeout)
            self._quiet_unlink_all(link)
            if got_native:
                if self.acquire(0):
                    return True
            if absolute_expiration:
                now = monotonic()
                if now >= absolute_expiration:
                    return False
                duration = now - begin
                timeout -= duration
                if timeout <= 0:
                    return False

    def __spin_on_native_lock(self, thread_lock, timeout):
        self._drop_lock_for_switch_out()
        try:
            # Unlike Python 2, Python 3 thread locks
            # can be interrupted when blocking, with or
            # without a timeout. Python 2 didn't even
            # support a timeout for non -blocking.
            if timeout:
                return thread_lock.acquire(True, timeout)

            return thread_lock.acquire()
        finally:
            self._acquire_lock_for_switch_in()


class BoundedSemaphore(Semaphore):
    """
    BoundedSemaphore(value=1) -> BoundedSemaphore

    A bounded semaphore checks to make sure its current value doesn't
    exceed its initial value. If it does, :class:`ValueError` is
    raised. In most situations semaphores are used to guard resources
    with limited capacity. If the semaphore is released too many times
    it's a sign of a bug.

    If not given, *value* defaults to 1.
    """

    __slots__ = (
        '_initial_value',
    )

    #: For monkey-patching, allow changing the class of error we raise
    _OVER_RELEASE_ERROR = ValueError

    def __init__(self, *args, **kwargs):
        Semaphore.__init__(self, *args, **kwargs)
        self._initial_value = self.counter

    def release(self):
        """
        Like :meth:`Semaphore.release`, but raises :class:`ValueError`
        if the semaphore is being over-released.
        """
        if self.counter >= self._initial_value:
            raise self._OVER_RELEASE_ERROR("Semaphore released too many times")
        counter = Semaphore.release(self)
        # When we are absolutely certain that no one holds this semaphore,
        # release our hub and go back to floating. This assists in cross-thread
        # uses.
        if counter == self._initial_value:
            self.hub = None # pylint:disable=attribute-defined-outside-init
        return counter

    def _at_fork_reinit(self):
        super(BoundedSemaphore, self)._at_fork_reinit()
        self.counter = self._initial_value


# By building the semaphore with Cython under PyPy, we get
# atomic operations (specifically, exiting/releasing), at the
# cost of some speed (one trivial semaphore micro-benchmark put the pure-python version
# at around 1s and the compiled version at around 4s). Some clever subclassing
# and having only the bare minimum be in cython might help reduce that penalty.
# NOTE: You must use version 0.23.4 or later to avoid a memory leak.
# https://mail.python.org/pipermail/cython-devel/2015-October/004571.html
# However, that's all for naught on up to and including PyPy 4.0.1 which
# have some serious crashing bugs with GC interacting with cython.
# It hasn't been tested since then, and PURE_PYTHON is assumed to be true
# for PyPy in all cases anyway, so this does nothing.

from gevent._util import import_c_accel
import_c_accel(globals(), 'gevent.__semaphore')
