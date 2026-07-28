# Copyright (c) 2012 Denis Bilenko. See LICENSE for details.
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys


from greenlet import greenlet as RawGreenlet

from gevent import monkey
from gevent._compat import integer_types
from gevent.event import AsyncResult
from gevent.exceptions import InvalidThreadUseError
from gevent.greenlet import Greenlet

from gevent._hub_local import get_hub_if_exists
from gevent.hub import _get_hub_noargs as get_hub
from gevent.hub import getcurrent
from gevent.hub import sleep
from gevent.lock import Semaphore
from gevent.pool import GroupMappingMixin
from gevent.util import clear_stack_frames

from gevent._threading import Queue
from gevent._threading import EmptyTimeout
from gevent._threading import start_new_thread
from gevent._threading import get_thread_ident


__all__ = [
    'ThreadPool',
    'ThreadResult',
]

def _format_hub(hub):
    if hub is None:
        return '<missing>'
    return '<%s at 0x%x thread_ident=0x%x>' % (
        hub.__class__.__name__, id(hub), hub.thread_ident
    )


def _get_thread_profile(_sys=sys):
    if 'threading' in _sys.modules:
        return _sys.modules['threading']._profile_hook


def _get_thread_trace(_sys=sys):
    if 'threading' in _sys.modules:
        return _sys.modules['threading']._trace_hook


class _WorkerGreenlet(RawGreenlet):
    # Exists to produce a more useful repr for worker pool
    # threads/greenlets, and manage the communication of the worker
    # thread with the threadpool.

    # Inform the gevent.util.GreenletTree that this should be
    # considered the root (for printing purposes)
    greenlet_tree_is_root = True

    _thread_ident = 0
    _exc_info = sys.exc_info
    _get_hub_if_exists = staticmethod(get_hub_if_exists)
    # We capture the hub each time through the loop in case its created
    # so we can destroy it after a fork.
    _hub_of_worker = None
    # The hub of the threadpool we're working for. Just for info.
    _hub = None

    # A cookie passed to task_queue.get()
    _task_queue_cookie = None

    # If not -1, how long to block waiting for a task before we
    # exit.
    _idle_task_timeout = -1

    def __init__(self, threadpool):
        # Construct in the main thread (owner of the threadpool)
        # The parent greenlet and thread identifier will be set once the
        # new thread begins running.
        RawGreenlet.__init__(self)

        self._hub = threadpool.hub
        # Avoid doing any imports in the background thread if it's not
        # necessary (monkey.get_original imports if not patched).
        # Background imports can hang Python 2 (gevent's thread resolver runs in the BG,
        # and resolving may have to import the idna module, which needs an import lock, so
        # resolving at module scope)
        if monkey.is_module_patched('sys'):
            stderr = monkey.get_original('sys', 'stderr')
        else:
            stderr = sys.stderr
        self._stderr = stderr
        # We can capture the task_queue; even though it can change if the threadpool
        # is re-innitted, we won't be running in that case
        self._task_queue = threadpool.task_queue # type:gevent._threading.Queue
        self._task_queue_cookie = self._task_queue.allocate_cookie()
        self._unregister_worker = threadpool._unregister_worker
        self._idle_task_timeout = threadpool._idle_task_timeout

        threadpool._register_worker(self)
        try:
            start_new_thread(self._begin, ())
        except:
            self._unregister_worker(self)
            raise

    def _begin(self, _get_c=getcurrent, _get_ti=get_thread_ident):
        # Pass arguments to avoid accessing globals during module shutdown.

        # we're in the new thread (but its root greenlet). Establish invariants and get going
        # by making this the current greenlet.
        self.parent = _get_c() # pylint:disable=attribute-defined-outside-init
        self._thread_ident = _get_ti()
        # ignore the parent attribute. (We can't set parent to None.)
        self.parent.greenlet_tree_is_ignored = True
        try:
            self.switch() # goto run()
        except: # pylint:disable=bare-except
            # run() will attempt to print any exceptions, but that might
            # not work during shutdown. sys.excepthook and such may be gone,
            # so things might not get printed at all except for a cryptic
            # message. This is especially true on Python 2 (doesn't seem to be
            # an issue on Python 3).
            pass

    def __fixup_hub_before_block(self):
        hub = self._get_hub_if_exists() # Don't create one; only set if a worker function did it
        if hub is not None:
            hub.name = 'ThreadPool Worker Hub'
            # While we block, don't let the monitoring thread, if any,
            # report us as blocked. Indeed, so long as we never
            # try to switch greenlets, don't report us as blocked---
            # the threadpool is *meant* to run blocking tasks
            if hub is not None and hub.periodic_monitoring_thread is not None:
                hub.periodic_monitoring_thread.ignore_current_greenlet_blocking()
            self._hub_of_worker = hub

    @staticmethod
    def __print_tb(tb, stderr):
        # Extracted from traceback to avoid accessing any module
        # globals (these sometimes happen during interpreter shutdown;
        # see test__subprocess_interrupted)
        while tb is not None:
            f = tb.tb_frame
            lineno = tb.tb_lineno
            co = f.f_code
            filename = co.co_filename
            name = co.co_name
            print('  File "%s", line %d, in %s' % (filename, lineno, name),
                  file=stderr)
            tb = tb.tb_next

    def _before_run_task(self, func, args, kwargs, thread_result,
                         _sys=sys,
                         _get_thread_profile=_get_thread_profile,
                         _get_thread_trace=_get_thread_trace):
        # pylint:disable=unused-argument
        _sys.setprofile(_get_thread_profile())
        _sys.settrace(_get_thread_trace())

    def _after_run_task(self, func, args, kwargs, thread_result, _sys=sys):
        # pylint:disable=unused-argument
        _sys.setprofile(None)
        _sys.settrace(None)

    def __run_task(self, func, args, kwargs, thread_result):
        self._before_run_task(func, args, kwargs, thread_result)
        try:
            thread_result.set(func(*args, **kwargs))
        except: # pylint:disable=bare-except
            thread_result.handle_error((self, func), self._exc_info())
        finally:
            self._after_run_task(func, args, kwargs, thread_result)
            del func, args, kwargs, thread_result

    def run(self):
        # pylint:disable=too-many-branches
        task = None
        exc_info = sys.exc_info
        fixup_hub_before_block = self.__fixup_hub_before_block
        task_queue_get = self._task_queue.get
        task_queue_cookie = self._task_queue_cookie
        run_task = self.__run_task
        task_queue_done = self._task_queue.task_done
        idle_task_timeout = self._idle_task_timeout
        try: # pylint:disable=too-many-nested-blocks
            while 1: # tiny bit faster than True on Py2
                fixup_hub_before_block()

                try:
                    task = task_queue_get(task_queue_cookie, idle_task_timeout)
                except EmptyTimeout:
                    # Nothing to do, exit the thread. Do not
                    # go into the next block where we would call
                    # queue.task_done(), because we didn't actually
                    # take a task.
                    return
                try:
                    if task is None:
                        return

                    run_task(*task)
                except:
                    task = repr(task)
                    raise
                finally:
                    task = None if not isinstance(task, str) else task
                    task_queue_done()
        except Exception as e: # pylint:disable=broad-except
            print(
                "Failed to run worker thread. Task=%r Exception=%r" % (
                    task, e
                ),
                file=self._stderr)
            self.__print_tb(exc_info()[-1], self._stderr)
        finally:
            # Re-check for the hub in case the task created it but then
            # failed.
            self.cleanup(self._get_hub_if_exists())

    def cleanup(self, hub_of_worker):
        if self._hub is not None:
            self._hub = None
            self._unregister_worker(self)
            self._unregister_worker = lambda _: None
            self._task_queue = None
            self._task_queue_cookie = None

        if hub_of_worker is not None:
            hub_of_worker.destroy(True)

    def __repr__(self, _format_hub=_format_hub):
        return "<ThreadPoolWorker at 0x%x thread_ident=0x%x threadpool-hub=%s>" % (
            id(self),
            self._thread_ident,
            _format_hub(self._hub)
        )


class ThreadPool(GroupMappingMixin):
    """
    A pool of native worker threads.

    This can be useful for CPU intensive functions, or those that
    otherwise will not cooperate with gevent. The best functions to execute
    in a thread pool are small functions with a single purpose; ideally they release
    the CPython GIL. Such functions are extension functions implemented in C.

    It implements the same operations as a :class:`gevent.pool.Pool`,
    but using threads instead of greenlets.

    .. note:: The method :meth:`apply_async` will always return a new
       greenlet, bypassing the threadpool entirely.

    Most users will not need to create instances of this class. Instead,
    use the threadpool already associated with gevent's hub::

        pool = gevent.get_hub().threadpool
        result = pool.spawn(lambda: "Some func").get()

    .. important:: It is only possible to use instances of this class from
       the thread running their hub. Typically that means from the thread that
       created them. Using the pattern shown above takes care of this.

       There is no gevent-provided way to have a single process-wide limit on the
       number of threads in various pools when doing that, however. The suggested
       way to use gevent and threadpools is to have a single gevent hub
       and its one threadpool (which is the default without doing any extra work).
       Only dispatch minimal blocking functions to the threadpool, functions that
       do not use the gevent hub.

    The `len` of instances of this class is the number of enqueued
    (unfinished) tasks.

    Just before a task starts running in a worker thread,
    the values of :func:`threading.setprofile` and :func:`threading.settrace`
    are consulted. Any values there are installed in that thread for the duration
    of the task (using :func:`sys.setprofile` and :func:`sys.settrace`, respectively).
    (Because worker threads are long-lived and outlast any given task, this arrangement
    lets the hook functions change between tasks, but does not let them see the
    bookkeeping done by the worker thread itself.)

    .. caution:: Instances of this class are only true if they have
       unfinished tasks.

    .. versionchanged:: 1.5a3
       The undocumented ``apply_e`` function, deprecated since 1.1,
       was removed.
    .. versionchanged:: 20.12.0
       Install the profile and trace functions in the worker thread while
       the worker thread is running the supplied task.
    .. versionchanged:: 22.08.0
       Add the option to let idle threads expire and be removed
       from the pool after *idle_task_timeout* seconds (-1 for no
       timeout)
    """

    __slots__ = (
        'hub',
        '_maxsize',
        # A Greenlet that runs to adjust the number of worker
        # threads.
        'manager',
        # The PID of the process we were created in.
        # Used to help detect a fork and then re-create
        # internal state.
        'pid',
        'fork_watcher',
        # A semaphore initialized with ``maxsize`` counting the
        # number of available worker threads we have. As a
        # gevent.lock.Semaphore, this is only safe to use from a single
        # native thread.
        '_available_worker_threads_greenlet_sem',
        # A set of running or pending _WorkerGreenlet objects;
        # we rely on the GIL for thread safety.
        '_worker_greenlets',
        # The task queue is itself safe to use from multiple
        # native threads.
        'task_queue',
        '_idle_task_timeout',
    )

    _WorkerGreenlet = _WorkerGreenlet

    def __init__(self, maxsize, hub=None, idle_task_timeout=-1):
        if hub is None:
            hub = get_hub()
        self.hub = hub
        self.pid = os.getpid()
        self.manager = None
        self.task_queue = Queue()
        self.fork_watcher = None
        self._idle_task_timeout = idle_task_timeout

        self._worker_greenlets = set()
        self._maxsize = 0
        # Note that by starting with 1, we actually allow
        # maxsize + 1 tasks in the queue.
        self._available_worker_threads_greenlet_sem = Semaphore(1, hub)
        self._set_maxsize(maxsize)
        self.fork_watcher = hub.loop.fork(ref=False)

    def _register_worker(self, worker):
        self._worker_greenlets.add(worker)

    def _unregister_worker(self, worker):
        self._worker_greenlets.discard(worker)

    def _set_maxsize(self, maxsize):
        if not isinstance(maxsize, integer_types):
            raise TypeError('maxsize must be integer: %r' % (maxsize, ))
        if maxsize < 0:
            raise ValueError('maxsize must not be negative: %r' % (maxsize, ))
        difference = maxsize - self._maxsize
        self._available_worker_threads_greenlet_sem.counter += difference
        self._maxsize = maxsize
        self.adjust()
        # make sure all currently blocking spawn() start unlocking if maxsize increased
        self._available_worker_threads_greenlet_sem._start_notify()

    def _get_maxsize(self):
        return self._maxsize

    maxsize = property(_get_maxsize, _set_maxsize, doc="""\
    The maximum allowed number of worker threads.

    This is also (approximately) a limit on the number of tasks that
    can be queued without blocking the waiting greenlet. If this many
    tasks are already running, then the next greenlet that submits a task
    will block waiting for a task to finish.
    """)

    def __repr__(self, _format_hub=_format_hub):
        return '<%s at 0x%x tasks=%s size=%s maxsize=%s hub=%s>' % (
            self.__class__.__name__,
            id(self),
            len(self), self.size, self.maxsize,
            _format_hub(self.hub),
        )

    def __len__(self):
        # XXX just do unfinished_tasks property
        # Note that this becomes the boolean value of this class,
        # that's probably not what we want!
        return self.task_queue.unfinished_tasks

    def _get_size(self):
        return len(self._worker_greenlets)

    def _set_size(self, size):
        if size < 0:
            raise ValueError('Size of the pool cannot be negative: %r' % (size, ))
        if size > self._maxsize:
            raise ValueError('Size of the pool cannot be bigger than maxsize: %r > %r' % (size, self._maxsize))
        if self.manager:
            self.manager.kill()
        while len(self._worker_greenlets) < size:
            self._add_thread()
        delay = self.hub.loop.approx_timer_resolution
        while len(self._worker_greenlets) > size:
            while len(self._worker_greenlets) - size > self.task_queue.unfinished_tasks:
                self.task_queue.put(None)
            if getcurrent() is self.hub:
                break
            sleep(delay)
            delay = min(delay * 2, .05)
        if self._worker_greenlets:
            self.fork_watcher.start(self._on_fork)
        else:
            self.fork_watcher.stop()

    size = property(_get_size, _set_size, doc="""\
    The number of running pooled worker threads.

    Setting this attribute will add or remove running
    worker threads, up to `maxsize`.

    Initially there are no pooled running worker threads, and
    threads are created on demand to satisfy concurrent
    requests up to `maxsize` threads.
    """)


    def _on_fork(self):
        # fork() only leaves one thread; also screws up locks;
        # let's re-create locks and threads, and do our best to
        # clean up any worker threads left behind.
        # NOTE: See comment in gevent.hub.reinit.
        pid = os.getpid()
        if pid != self.pid:
            # The OS threads have been destroyed, but the Python
            # objects may live on, creating refcount "leaks". Python 2
            # leaves dead frames (those that are for dead OS threads)
            # around; Python 3.8 does not.
            thread_ident_to_frame = dict(sys._current_frames())
            for worker in list(self._worker_greenlets):
                frame = thread_ident_to_frame.get(worker._thread_ident)
                clear_stack_frames(frame)
                worker.cleanup(worker._hub_of_worker)
                # We can't throw anything to the greenlet, nor can we
                # switch to it or set a parent. Those would all be cross-thread
                # operations, which aren't allowed.
                worker.__dict__.clear()

            # We've cleared f_locals and on Python 3.4, possibly the actual
            # array locals of the stack frame, but the task queue may still be
            # referenced if we didn't actually get all the locals. Shut it down
            # and clear it before we throw away our reference.
            self.task_queue.kill()
            self.__init__(self._maxsize)


    def join(self):
        """Waits until all outstanding tasks have been completed."""
        delay = max(0.0005, self.hub.loop.approx_timer_resolution)
        while self.task_queue.unfinished_tasks > 0:
            sleep(delay)
            delay = min(delay * 2, .05)

    def kill(self):
        self.size = 0
        self.fork_watcher.close()

    def _adjust_step(self):
        # if there is a possibility & necessity for adding a thread, do it
        while (len(self._worker_greenlets) < self._maxsize
               and self.task_queue.unfinished_tasks > len(self._worker_greenlets)):
            self._add_thread()
        # while the number of threads is more than maxsize, kill one
        # we do not check what's already in task_queue - it could be all Nones
        while len(self._worker_greenlets) - self._maxsize > self.task_queue.unfinished_tasks:
            self.task_queue.put(None)
        if self._worker_greenlets:
            self.fork_watcher.start(self._on_fork)
        elif self.fork_watcher is not None:
            self.fork_watcher.stop()

    def _adjust_wait(self):
        delay = self.hub.loop.approx_timer_resolution
        while True:
            self._adjust_step()
            if len(self._worker_greenlets) <= self._maxsize:
                return
            sleep(delay)
            delay = min(delay * 2, .05)

    def adjust(self):
        self._adjust_step()
        if not self.manager and len(self._worker_greenlets) > self._maxsize:
            # might need to feed more Nones into the pool to shutdown
            # threads.
            self.manager = Greenlet.spawn(self._adjust_wait)

    def _add_thread(self):
        self._WorkerGreenlet(self)

    def spawn(self, func, *args, **kwargs):
        """
        Add a new task to the threadpool that will run ``func(*args,
        **kwargs)``.

        Waits until a slot is available. Creates a new native thread
        if necessary.

        This must only be called from the native thread that owns this
        object's hub. This is because creating the necessary data
        structures to communicate back to this thread isn't thread
        safe, so the hub must not be running something else. Also,
        ensuring the pool size stays correct only works within a
        single thread.

        :return: A :class:`gevent.event.AsyncResult`.
        :raises InvalidThreadUseError: If called from a different thread.

        .. versionchanged:: 1.5
           Document the thread-safety requirements.
        """
        if self.hub != get_hub():
            raise InvalidThreadUseError

        while 1:
            semaphore = self._available_worker_threads_greenlet_sem
            semaphore.acquire()
            if semaphore is self._available_worker_threads_greenlet_sem:
                # If we were asked to change size or re-init we could have changed
                # semaphore objects.
                break

        # Returned; lets a greenlet in this thread wait
        # for the pool thread. Signaled when the async watcher
        # is fired from the pool thread back into this thread.
        result = AsyncResult()
        task_queue = self.task_queue
        # Encapsulates the async watcher the worker thread uses to
        # call back into this thread. Immediately allocates and starts the
        # async watcher in this thread, because it uses this hub/loop,
        # which is not thread safe.
        thread_result = None
        try:
            thread_result = ThreadResult(result, self.hub, semaphore.release)
            task_queue.put((func, args, kwargs, thread_result))
            self.adjust()
        except:
            if thread_result is not None:
                thread_result.destroy_in_main_thread()
            semaphore.release()
            raise
        return result

    def _apply_immediately(self):
        # If we're being called from a different thread than the one that
        # created us, e.g., because a worker task is trying to use apply()
        # recursively, we have no choice but to run the task immediately;
        # if we try to AsyncResult.get() in the worker thread, it's likely to have
        # nothing to switch to and lead to a LoopExit.
        return get_hub() is not self.hub

    def _apply_async_cb_spawn(self, callback, result):
        callback(result)

    def _apply_async_use_greenlet(self):
        # Always go to Greenlet because our self.spawn uses threads
        return True

class _FakeAsync(object):

    def send(self):
        pass
    close = stop = send

    def __call__(self, result):
        "fake out for 'receiver'"

    def __bool__(self):
        return False

    __nonzero__ = __bool__

_FakeAsync = _FakeAsync()

class ThreadResult(object):
    """
    A one-time event for cross-thread communication.

    Uses a hub's "async" watcher capability; it must be constructed and
    destroyed in the thread running the hub (because creating, starting, and
    destroying async watchers isn't guaranteed to be thread safe).
    """

    # Using slots here helps to debug reference cycles/leaks
    __slots__ = ('exc_info', 'async_watcher', '_call_when_ready', 'value',
                 'context', 'hub', 'receiver')

    def __init__(self, receiver, hub, call_when_ready):
        self.receiver = receiver
        self.hub = hub
        self.context = None
        self.value = None
        self.exc_info = ()
        self.async_watcher = hub.loop.async_()
        self._call_when_ready = call_when_ready
        self.async_watcher.start(self._on_async)

    @property
    def exception(self):
        return self.exc_info[1] if self.exc_info else None

    def _on_async(self):
        # Called in the hub thread.

        aw = self.async_watcher
        self.async_watcher = _FakeAsync

        aw.stop()
        aw.close()

        # Typically this is pool.semaphore.release and we have to
        # call this in the Hub; if we don't we get the dreaded
        # LoopExit (XXX: Why?)
        try:
            self._call_when_ready()
            if self.exc_info:
                self.hub.handle_error(self.context, *self.exc_info)
            self.context = None
            self.async_watcher = _FakeAsync
            self.hub = None
            self._call_when_ready = _FakeAsync

            self.receiver(self)
        finally:
            self.receiver = _FakeAsync
            self.value = None
            if self.exc_info:
                self.exc_info = (self.exc_info[0], self.exc_info[1], None)

    def destroy_in_main_thread(self):
        """
        This must only be called from the thread running the hub.
        """
        self.async_watcher.stop()
        self.async_watcher.close()
        self.async_watcher = _FakeAsync

        self.context = None
        self.hub = None
        self._call_when_ready = _FakeAsync
        self.receiver = _FakeAsync

    def set(self, value):
        self.value = value
        self.async_watcher.send()

    def handle_error(self, context, exc_info):
        self.context = context
        self.exc_info = exc_info
        self.async_watcher.send()

    # link protocol:
    def successful(self):
        return self.exception is None


try:
    import concurrent.futures
except ImportError:
    pass
else:
    __all__.append("ThreadPoolExecutor")

    from gevent.timeout import Timeout as GTimeout
    from gevent._util import Lazy
    from concurrent.futures import _base as cfb

    def _ignore_error(future_proxy, fn):
        def cbwrap(_):
            del _
            # We're called with the async result (from the threadpool), but
            # be sure to pass in the user-visible _FutureProxy object..
            try:
                fn(future_proxy)
            except Exception: # pylint: disable=broad-except
                # Just print, don't raise to the hub's parent.
                future_proxy.hub.print_exception((fn, future_proxy), None, None, None)
        return cbwrap

    def _wrap(future_proxy, fn):
        def f(_):
            fn(future_proxy)
        return f

    class _FutureProxy(object):
        def __init__(self, asyncresult):
            self.asyncresult = asyncresult

        # Internal implementation details of a c.f.Future

        @Lazy
        def _condition(self):
            if monkey.is_module_patched('threading') or self.done():
                import threading
                return threading.Condition()
            # We can only properly work with conditions
            # when we've been monkey-patched. This is necessary
            # for the wait/as_completed module functions.
            raise AttributeError("_condition")

        @Lazy
        def _waiters(self):
            self.asyncresult.rawlink(self.__when_done)
            return []

        def __when_done(self, _):
            # We should only be called when _waiters has
            # already been accessed.
            waiters = getattr(self, '_waiters')
            for w in waiters: # pylint:disable=not-an-iterable
                if self.successful():
                    w.add_result(self)
                else:
                    w.add_exception(self)

        @property
        def _state(self):
            if self.done():
                return cfb.FINISHED
            return cfb.RUNNING

        def set_running_or_notify_cancel(self):
            # Does nothing, not even any consistency checks. It's
            # meant to be internal to the executor and we don't use it.
            return

        def result(self, timeout=None):
            try:
                return self.asyncresult.result(timeout=timeout)
            except GTimeout:
                # XXX: Theoretically this could be a completely
                # unrelated timeout instance. Do we care about that?
                raise concurrent.futures.TimeoutError()

        def exception(self, timeout=None):
            try:
                self.asyncresult.get(timeout=timeout)
                return self.asyncresult.exception
            except GTimeout:
                raise concurrent.futures.TimeoutError()

        def add_done_callback(self, fn):
            """Exceptions raised by *fn* are ignored."""
            if self.done():
                fn(self)
            else:
                self.asyncresult.rawlink(_ignore_error(self, fn))

        def rawlink(self, fn):
            self.asyncresult.rawlink(_wrap(self, fn))

        def __str__(self):
            return str(self.asyncresult)

        def __getattr__(self, name):
            return getattr(self.asyncresult, name)

    class ThreadPoolExecutor(concurrent.futures.ThreadPoolExecutor):
        """
        A version of :class:`concurrent.futures.ThreadPoolExecutor` that
        always uses native threads, even when threading is monkey-patched.

        The ``Future`` objects returned from this object can be used
        with gevent waiting primitives like :func:`gevent.wait`.

        .. caution:: If threading is *not* monkey-patched, then the ``Future``
           objects returned by this object are not guaranteed to work with
           :func:`~concurrent.futures.as_completed` and :func:`~concurrent.futures.wait`.
           The individual blocking methods like :meth:`~concurrent.futures.Future.result`
           and :meth:`~concurrent.futures.Future.exception` will always work.

        .. versionadded:: 1.2a1
           This is a provisional API.
        """

        def __init__(self, *args, **kwargs):
            """
            Takes the same arguments as ``concurrent.futures.ThreadPoolExecuter``, which
            vary between Python versions.

            The first argument is always *max_workers*, the maximum number of
            threads to use. Most other arguments, while accepted, are ignored.
            """
            super(ThreadPoolExecutor, self).__init__(*args, **kwargs)
            self._threadpool = ThreadPool(self._max_workers)

        def submit(self, fn, *args, **kwargs): # pylint:disable=arguments-differ
            with self._shutdown_lock: # pylint:disable=not-context-manager
                if self._shutdown:
                    raise RuntimeError('cannot schedule new futures after shutdown')

                future = self._threadpool.spawn(fn, *args, **kwargs)
                return _FutureProxy(future)

        def shutdown(self, wait=True, **kwargs): # pylint:disable=arguments-differ
            # In 3.9, this added ``cancel_futures=False``
            super(ThreadPoolExecutor, self).shutdown(wait, **kwargs)
            # XXX: We don't implement wait properly
            kill = getattr(self._threadpool, 'kill', None)
            if kill: # pylint:disable=using-constant-test
                self._threadpool.kill()
            self._threadpool = None

        kill = shutdown # greentest compat

        def _adjust_thread_count(self):
            # Does nothing. We don't want to spawn any "threads",
            # let the threadpool handle that.
            pass
