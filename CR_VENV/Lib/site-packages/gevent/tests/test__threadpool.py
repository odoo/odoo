from __future__ import print_function

from time import time, sleep
import contextlib
import random
import weakref
import gc


import gevent.threadpool
from gevent.threadpool import ThreadPool
import gevent
from gevent.exceptions import InvalidThreadUseError

import gevent.testing as greentest
from gevent.testing import ExpectedException
from gevent.testing import PYPY



# pylint:disable=too-many-ancestors


@contextlib.contextmanager
def disabled_gc():
    was_enabled = gc.isenabled()
    gc.disable()
    try:
        yield
    finally:
        if was_enabled:
            gc.enable()


class TestCase(greentest.TestCase):
    # These generally need more time
    __timeout__ = greentest.LARGE_TIMEOUT
    pool = None
    _all_pools = ()

    ClassUnderTest = ThreadPool
    def _FUT(self):
        return self.ClassUnderTest

    def _makeOne(self, maxsize, create_all_worker_threads=greentest.RUN_LEAKCHECKS):
        self.pool = pool = self._FUT()(maxsize)
        self._all_pools += (pool,)
        if create_all_worker_threads:
            # Max size to help eliminate false positives
            self.pool.size = maxsize
        return pool

    def cleanup(self):
        self.pool = None
        all_pools, self._all_pools = self._all_pools, ()
        for pool in all_pools:
            kill = getattr(pool, 'kill', None) or getattr(pool, 'shutdown')
            kill()
            del kill

        if greentest.RUN_LEAKCHECKS:
            # Each worker thread created a greenlet object and switched to it.
            # It's a custom subclass, but even if it's not, it appears that
            # the root greenlet for the new thread sticks around until there's a
            # gc. Simply calling 'getcurrent()' is enough to "leak" a greenlet.greenlet
            # and a weakref.
            for _ in range(3):
                gc.collect()


class PoolBasicTests(TestCase):

    def test_execute_async(self):
        pool = self._makeOne(2)
        r = []
        first = pool.spawn(r.append, 1)
        first.get()
        self.assertEqual(r, [1])
        gevent.sleep(0)

        pool.apply_async(r.append, (2, ))
        self.assertEqual(r, [1])

        pool.apply_async(r.append, (3, ))
        self.assertEqual(r, [1])

        pool.apply_async(r.append, (4, ))
        self.assertEqual(r, [1])
        gevent.sleep(0.01)
        self.assertEqualFlakyRaceCondition(sorted(r), [1, 2, 3, 4])

    def test_apply(self):
        pool = self._makeOne(1)
        result = pool.apply(lambda a: ('foo', a), (1, ))
        self.assertEqual(result, ('foo', 1))

    def test_apply_raises(self):
        pool = self._makeOne(1)

        def raiser():
            raise ExpectedException()

        with self.assertRaises(ExpectedException):
            pool.apply(raiser)
    # Don't let the metaclass automatically force any error
    # that reaches the hub from a spawned greenlet to become
    # fatal; that defeats the point of the test.
    test_apply_raises.error_fatal = False

    def test_init_valueerror(self):
        self.switch_expected = False
        with self.assertRaises(ValueError):
            self._makeOne(-1)

#
# tests from standard library test/test_multiprocessing.py


class TimingWrapper(object):

    def __init__(self, the_func):
        self.func = the_func
        self.elapsed = None

    def __call__(self, *args, **kwds):
        t = time()
        try:
            return self.func(*args, **kwds)
        finally:
            self.elapsed = time() - t


def sqr(x, wait=0.0):
    sleep(wait)
    return x * x


def sqr_random_sleep(x):
    sleep(random.random() * 0.1)
    return x * x


TIMEOUT1, TIMEOUT2, TIMEOUT3 = 0.082, 0.035, 0.14

class _AbstractPoolTest(TestCase):

    size = 1

    MAP_IS_GEN = False

    def setUp(self):
        greentest.TestCase.setUp(self)
        self._makeOne(self.size)

    @greentest.ignores_leakcheck
    def test_map(self):
        pmap = self.pool.map
        if self.MAP_IS_GEN:
            pmap = lambda f, i: list(self.pool.map(f, i))
        self.assertEqual(pmap(sqr, range(10)), list(map(sqr, range(10))))
        self.assertEqual(pmap(sqr, range(100)), list(map(sqr, range(100))))

        self.pool.kill()
        del self.pool
        del pmap

SMALL_RANGE = 10
LARGE_RANGE = 1000

if (greentest.PYPY and (greentest.WIN or greentest.RUN_COVERAGE)) or greentest.RUN_LEAKCHECKS:
    # PyPy 5.10 is *really* slow at spawning or switching between
    # threads (especially on Windows or when coverage is enabled) Tests that happen
    # instantaneously on other platforms time out due to the overhead.

    # Leakchecks also take much longer due to all the calls into the GC,
    # most especially on Python 3
    LARGE_RANGE = 50

class TestPool(_AbstractPoolTest):

    def test_greenlet_class(self):
        from greenlet import getcurrent
        from gevent.threadpool import _WorkerGreenlet
        worker_greenlet = self.pool.apply(getcurrent)

        self.assertIsInstance(worker_greenlet, _WorkerGreenlet)
        r = repr(worker_greenlet)
        self.assertIn('ThreadPoolWorker', r)
        self.assertIn('thread_ident', r)
        self.assertIn('hub=', r)

        from gevent.util import format_run_info

        info = '\n'.join(format_run_info())
        self.assertIn("<ThreadPoolWorker", info)

    def test_apply(self):
        papply = self.pool.apply
        self.assertEqual(papply(sqr, (5,)), sqr(5))
        self.assertEqual(papply(sqr, (), {'x': 3}), sqr(x=3))

    def test_async(self):
        res = self.pool.apply_async(sqr, (7, TIMEOUT1,))
        get = TimingWrapper(res.get)
        self.assertEqual(get(), 49)
        self.assertTimeoutAlmostEqual(get.elapsed, TIMEOUT1, 1)

    def test_async_callback(self):
        result = []
        res = self.pool.apply_async(sqr, (7, TIMEOUT1,), callback=result.append)
        get = TimingWrapper(res.get)
        self.assertEqual(get(), 49)
        self.assertTimeoutAlmostEqual(get.elapsed, TIMEOUT1, 1)
        gevent.sleep(0)  # lets the callback run
        self.assertEqual(result, [49])

    def test_async_timeout(self):
        res = self.pool.apply_async(sqr, (6, TIMEOUT2 + 0.2))
        get = TimingWrapper(res.get)
        self.assertRaises(gevent.Timeout, get, timeout=TIMEOUT2)
        self.assertTimeoutAlmostEqual(get.elapsed, TIMEOUT2, 1)
        self.pool.join()

    def test_imap_list_small(self):
        it = self.pool.imap(sqr, range(SMALL_RANGE))
        self.assertEqual(list(it), list(map(sqr, range(SMALL_RANGE))))

    def test_imap_it_small(self):
        it = self.pool.imap(sqr, range(SMALL_RANGE))
        for i in range(SMALL_RANGE):
            self.assertEqual(next(it), i * i)
        self.assertRaises(StopIteration, next, it)

    def test_imap_it_large(self):
        it = self.pool.imap(sqr, range(LARGE_RANGE))
        for i in range(LARGE_RANGE):
            self.assertEqual(next(it), i * i)
        self.assertRaises(StopIteration, next, it)

    def test_imap_gc(self):
        it = self.pool.imap(sqr, range(SMALL_RANGE))
        for i in range(SMALL_RANGE):
            self.assertEqual(next(it), i * i)
            gc.collect()
        self.assertRaises(StopIteration, next, it)

    def test_imap_unordered_gc(self):
        it = self.pool.imap_unordered(sqr, range(SMALL_RANGE))
        result = []
        for _ in range(SMALL_RANGE):
            result.append(next(it))
            gc.collect()
        with self.assertRaises(StopIteration):
            next(it)
        self.assertEqual(sorted(result), [x * x for x in range(SMALL_RANGE)])

    def test_imap_random(self):
        it = self.pool.imap(sqr_random_sleep, range(SMALL_RANGE))
        self.assertEqual(list(it), list(map(sqr, range(SMALL_RANGE))))

    def test_imap_unordered(self):
        it = self.pool.imap_unordered(sqr, range(LARGE_RANGE))
        self.assertEqual(sorted(it), list(map(sqr, range(LARGE_RANGE))))

        it = self.pool.imap_unordered(sqr, range(LARGE_RANGE))
        self.assertEqual(sorted(it), list(map(sqr, range(LARGE_RANGE))))

    def test_imap_unordered_random(self):
        it = self.pool.imap_unordered(sqr_random_sleep, range(SMALL_RANGE))
        self.assertEqual(sorted(it), list(map(sqr, range(SMALL_RANGE))))

    def test_terminate(self):
        size = self.size or 10
        result = self.pool.map_async(sleep, [0.1] * (size * 2))
        gevent.sleep(0.1)
        try:
            with self.runs_in_given_time(0.1 * self.size + 0.5, min_time=0):
                self.pool.kill()
        finally:
            result.join()

    def sleep(self, x):
        sleep(float(x) / 10.0)
        return str(x)

    def test_imap_unordered_sleep(self):
        # testing that imap_unordered returns items in competion order
        result = list(self.pool.imap_unordered(self.sleep, [10, 1, 2]))
        if self.pool.size == 1:
            expected = ['10', '1', '2']
        else:
            expected = ['1', '2', '10']
        self.assertEqual(result, expected)


class TestPool2(TestPool):
    size = 2

    @greentest.ignores_leakcheck # Asking for the hub in the new thread shows up as a "leak"
    def test_recursive_apply(self):
        p = self.pool

        def a():
            return p.apply(b)

        def b():
            # make sure we can do both types of callbacks
            # (loop iteration and end-of-loop) in the recursive
            # call
            gevent.sleep()
            gevent.sleep(0.001)
            return "B"

        result = p.apply(a)
        self.assertEqual(result, "B")


@greentest.ignores_leakcheck
class TestPool3(TestPool):
    size = 3

@greentest.ignores_leakcheck
class TestPool10(TestPool):
    size = 10



# class TestJoinSleep(greentest.GenericGetTestCase):
#
#     def wait(self, timeout):
#         pool = ThreadPool(1)
#         pool.spawn(gevent.sleep, 10)
#         pool.join(timeout=timeout)
#
#
# class TestJoinSleep_raise_error(greentest.GenericWaitTestCase):
#
#     def wait(self, timeout):
#         pool = ThreadPool(1)
#         g = pool.spawn(gevent.sleep, 10)
#         pool.join(timeout=timeout, raise_error=True)


class TestJoinEmpty(TestCase):
    switch_expected = False

    @greentest.skipIf(greentest.PYPY and greentest.LIBUV and greentest.RUNNING_ON_TRAVIS,
                      "This sometimes appears to crash in PyPy2 5.9.0, "
                      "but never crashes on macOS or local Ubunto with same PyPy version")
    # Running this test standalone doesn't crash PyPy, only when it's run
    # as part of this whole file. Removing it does solve the crash though.
    def test(self):
        pool = self._makeOne(1)
        pool.join()


class TestSpawn(TestCase):
    switch_expected = True

    @greentest.ignores_leakcheck
    def test_basics(self):
        pool = self._makeOne(1)
        self.assertEqual(len(pool), 0)
        log = []
        sleep_n_log = lambda item, seconds: [sleep(seconds), log.append(item)]
        pool.spawn(sleep_n_log, 'a', 0.1)
        self.assertEqual(len(pool), 1)
        pool.spawn(sleep_n_log, 'b', 0.1)
        # even though the pool is of size 1, it can contain 2 items
        # since we allow +1 for better throughput
        self.assertEqual(len(pool), 2)
        gevent.sleep(0.15)
        self.assertEqual(log, ['a'])
        self.assertEqual(len(pool), 1)
        gevent.sleep(0.15)
        self.assertEqual(log, ['a', 'b'])
        self.assertEqual(len(pool), 0)

    @greentest.ignores_leakcheck
    def test_cannot_spawn_from_other_thread(self):
        # Only the thread that owns a threadpool can spawn to it;
        # this is because the threadpool uses the creating thread's hub,
        # which is not threadsafe.
        pool1 = self._makeOne(1)
        pool2 = self._makeOne(2)

        def func():
            pool2.spawn(lambda: "Hi")

        res = pool1.spawn(func)
        with self.assertRaises(InvalidThreadUseError):
            res.get()

def error_iter():
    yield 1
    yield 2
    raise greentest.ExpectedException


class TestErrorInIterator(TestCase):

    error_fatal = False

    def test(self):
        self.pool = self._makeOne(3)
        self.assertRaises(greentest.ExpectedException, self.pool.map, lambda x: None, error_iter())
        gevent.sleep(0.001)

    def test_unordered(self):
        self.pool = self._makeOne(3)

        def unordered():
            return list(self.pool.imap_unordered(lambda x: None, error_iter()))

        self.assertRaises(greentest.ExpectedException, unordered)
        gevent.sleep(0.001)


class TestMaxsize(TestCase):

    def test_inc(self):
        self.pool = self._makeOne(0)
        done = []
        # Try to be careful not to tick over the libuv timer.
        # See libuv/loop.py:_start_callback_timer
        gevent.spawn(self.pool.spawn, done.append, 1)
        gevent.spawn_later(0.01, self.pool.spawn, done.append, 2)
        gevent.sleep(0.02)
        self.assertEqual(done, [])
        self.pool.maxsize = 1
        gevent.sleep(0.02)

        self.assertEqualFlakyRaceCondition(done, [1, 2])

    @greentest.ignores_leakcheck
    def test_setzero(self):
        pool = self.pool = self._makeOne(3)
        pool.spawn(sleep, 0.1)
        pool.spawn(sleep, 0.2)
        pool.spawn(sleep, 0.3)
        gevent.sleep(0.2)
        self.assertGreaterEqual(pool.size, 2)
        pool.maxsize = 0
        gevent.sleep(0.2)
        self.assertEqualFlakyRaceCondition(pool.size, 0)


class TestSize(TestCase):

    @greentest.reraises_flaky_race_condition()
    def test(self):
        pool = self.pool = self._makeOne(2, create_all_worker_threads=False)
        self.assertEqual(pool.size, 0)
        pool.size = 1
        self.assertEqual(pool.size, 1)
        pool.size = 2
        self.assertEqual(pool.size, 2)
        pool.size = 1
        self.assertEqual(pool.size, 1)

        with self.assertRaises(ValueError):
            pool.size = -1

        with self.assertRaises(ValueError):
            pool.size = 3

        pool.size = 0
        self.assertEqual(pool.size, 0)
        pool.size = 2
        self.assertEqual(pool.size, 2)


class TestRef(TestCase):

    def test(self):
        pool = self.pool = self._makeOne(2)

        refs = []
        obj = SomeClass()
        obj.refs = refs
        func = obj.func
        del obj

        with disabled_gc():
            # we do this:
            #     result = func(Object(), kwarg1=Object())
            # but in a thread pool and see that arguments', result's and func's references are not leaked
            result = pool.apply(func, (Object(), ), {'kwarg1': Object()})
            self.assertIsInstance(result, Object)
            gevent.sleep(0.1)  # XXX should not be needed

            refs.append(weakref.ref(func))
            del func, result
            if PYPY:
                gc.collect()
                gc.collect()
            for r in refs:
                self.assertIsNone(r())

            self.assertEqual(4, len(refs))


class Object(object):
    pass


class SomeClass(object):

    refs = None

    def func(self, arg1, kwarg1=None):
        result = Object()
        self.refs.extend([weakref.ref(x) for x in [arg1, kwarg1, result]])
        return result


def noop():
    pass


class TestRefCount(TestCase):

    def test(self):
        pool = self._makeOne(1)
        pool.spawn(noop)
        gevent.sleep(0)
        pool.kill()



from gevent import monkey

@greentest.skipUnless(
    hasattr(gevent.threadpool, 'ThreadPoolExecutor'),
    "Requires ThreadPoolExecutor")
class TestTPE(_AbstractPoolTest):
    size = 1

    MAP_IS_GEN = True

    @property
    def ClassUnderTest(self):
        return gevent.threadpool.ThreadPoolExecutor

    MONKEY_PATCHED = False

    @property
    def FutureTimeoutError(self):
        from concurrent.futures import TimeoutError as FutureTimeoutError
        return FutureTimeoutError

    @property
    def cf_wait(self):
        from concurrent.futures import wait as cf_wait
        return cf_wait

    @property
    def cf_as_completed(self):
        from concurrent.futures import as_completed as cf_as_completed
        return cf_as_completed

    @greentest.ignores_leakcheck
    def test_future(self):
        self.assertEqual(monkey.is_module_patched('threading'),
                         self.MONKEY_PATCHED)
        pool = self.pool

        calledback = []

        def fn():
            gevent.sleep(0.5)
            return 42

        def callback(future):
            future.calledback += 1
            raise greentest.ExpectedException("Expected, ignored")

        future = pool.submit(fn) # pylint:disable=no-member
        future.calledback = 0
        future.add_done_callback(callback)
        self.assertRaises(self.FutureTimeoutError, future.result, timeout=0.001)

        def spawned():
            return 2016

        spawned_greenlet = gevent.spawn(spawned)

        # Whether or not we are monkey patched, the background
        # greenlet we spawned got to run while we waited.

        self.assertEqual(future.result(), 42)
        self.assertTrue(future.done())
        self.assertFalse(future.cancelled())
        # Make sure the notifier has a chance to run so the call back
        # gets called
        gevent.sleep()
        self.assertEqual(future.calledback, 1)

        self.assertTrue(spawned_greenlet.ready())
        self.assertEqual(spawned_greenlet.value, 2016)

        # Adding the callback again runs immediately
        future.add_done_callback(lambda f: calledback.append(True))
        self.assertEqual(calledback, [True])

        # We can wait on the finished future
        done, _not_done = self.cf_wait((future,))
        self.assertEqual(list(done), [future])

        self.assertEqual(list(self.cf_as_completed((future,))), [future])
        # Doing so does not call the callback again
        self.assertEqual(future.calledback, 1)
        # even after a trip around the event loop
        gevent.sleep()
        self.assertEqual(future.calledback, 1)

        pool.kill()
        del future
        del pool
        del self.pool

    @greentest.ignores_leakcheck
    def test_future_wait_module_function(self):
        # Instead of waiting on the result, we can wait
        # on the future using the module functions
        self.assertEqual(monkey.is_module_patched('threading'),
                         self.MONKEY_PATCHED)
        pool = self.pool

        def fn():
            gevent.sleep(0.5)
            return 42

        future = pool.submit(fn) # pylint:disable=no-member
        if self.MONKEY_PATCHED:
            # Things work as expected when monkey-patched
            _done, not_done = self.cf_wait((future,), timeout=0.001)
            self.assertEqual(list(not_done), [future])

            def spawned():
                return 2016

            spawned_greenlet = gevent.spawn(spawned)

            done, _not_done = self.cf_wait((future,))
            self.assertEqual(list(done), [future])
            self.assertTrue(spawned_greenlet.ready())
            self.assertEqual(spawned_greenlet.value, 2016)
        else:
            # When not monkey-patched, raises an AttributeError
            self.assertRaises(AttributeError, self.cf_wait, (future,))

        pool.kill()
        del future
        del pool
        del self.pool

    @greentest.ignores_leakcheck
    def test_future_wait_gevent_function(self):
        # The future object can be waited on with gevent functions.
        self.assertEqual(monkey.is_module_patched('threading'),
                         self.MONKEY_PATCHED)
        pool = self.pool

        def fn():
            gevent.sleep(0.5)
            return 42

        future = pool.submit(fn) # pylint:disable=no-member

        def spawned():
            return 2016

        spawned_greenlet = gevent.spawn(spawned)

        done = gevent.wait((future,))
        self.assertEqual(list(done), [future])
        self.assertTrue(spawned_greenlet.ready())
        self.assertEqual(spawned_greenlet.value, 2016)

        pool.kill()
        del future
        del pool
        del self.pool


class TestThreadResult(greentest.TestCase):

    def test_exception_in_on_async_doesnt_crash(self):
        # Issue 1482. An FFI-based loop could crash the whole process
        # by dereferencing a handle after it was closed.
        called = []
        class MyException(Exception):
            pass

        def bad_when_ready():
            called.append(1)
            raise MyException

        tr = gevent.threadpool.ThreadResult(None, gevent.get_hub(), bad_when_ready)

        def wake():
            called.append(1)
            tr.set(42)

        gevent.spawn(wake).get()
        # Spin the loop a few times to make sure we run the callbacks.
        # If we neglect to spin, we don't trigger the bug.
        # If error handling is correct, the exception raised from the callback
        # will be surfaced in the main greenlet. On windows, it can sometimes take
        # more than one spin for some reason; if we don't catch it here, then
        # some other test is likely to die unexpectedly with MyException.
        with self.assertRaises(MyException):
            for _ in range(5):
                gevent.sleep(0.001)


        self.assertEqual(called, [1, 1])
        # But value was cleared in a finally block
        self.assertIsNone(tr.value)
        self.assertIsNotNone(tr.receiver)


class TestWorkerProfileAndTrace(TestCase):
    # Worker threads should execute the test and trace functions.
    # (When running the user code.)
    # https://github.com/gevent/gevent/issues/1670

    old_profile = None
    old_trace = None

    def setUp(self):
        super(TestWorkerProfileAndTrace, self).setUp()
        self.old_profile = gevent.threadpool._get_thread_profile()
        self.old_trace = gevent.threadpool._get_thread_trace()

    def tearDown(self):
        import threading
        threading.setprofile(self.old_profile)
        threading.settrace(self.old_trace)
        super(TestWorkerProfileAndTrace, self).tearDown()

    def test_get_profile(self):
        import threading
        threading.setprofile(self)
        self.assertIs(gevent.threadpool._get_thread_profile(), self)

    def test_get_trace(self):
        import threading
        threading.settrace(self)
        self.assertIs(gevent.threadpool._get_thread_trace(), self)

    def _test_func_called_in_task(self, func):
        import threading
        import sys

        setter = getattr(threading, 'set' + func)
        getter = getattr(sys, 'get' + func)

        called = [0]
        def callback(*_args):
            called[0] += 1

        def task():
            test.assertIsNotNone(getter)
            return 1701


        before_task = []
        after_task = []

        test = self
        class Pool(ThreadPool):
            class _WorkerGreenlet(ThreadPool._WorkerGreenlet):
                # pylint:disable=signature-differs
                def _before_run_task(self, func, *args):
                    before_task.append(func)
                    before_task.append(getter())
                    ThreadPool._WorkerGreenlet._before_run_task(self, func, *args)
                    before_task.append(getter())

                def _after_run_task(self, func, *args):
                    after_task.append(func)
                    after_task.append(getter())
                    ThreadPool._WorkerGreenlet._after_run_task(self, func, *args)
                    after_task.append(getter())

        self.ClassUnderTest = Pool

        pool = self._makeOne(1, create_all_worker_threads=True)
        assert isinstance(pool, Pool)

        # Do this after creating the pool and its thread to verify we don't
        # capture the function at thread creation time.
        setter(callback)


        res = pool.apply(task)
        self.assertEqual(res, 1701)
        self.assertGreaterEqual(called[0], 1)

        # Shutdown the pool. PyPy2.7-7.3.1 on Windows/Appveyor was
        # properly seeing the before_task value, but after_task was empty.
        # That suggested a memory consistency type issue, where the updates
        # written by the other thread weren't fully visible to this thread
        # yet. Try to kill it to see if that helps. (Couldn't reproduce
        # on macOS).
        #
        # https://ci.appveyor.com/project/jamadden/gevent/build/job/wo9likk85cduui7n#L867
        pool.kill()

        # The function is active only for the scope of the function
        self.assertEqual(before_task, [task, None, callback])
        self.assertEqual(after_task, [task, callback, None])

    def test_profile_called_in_task(self):
        self._test_func_called_in_task('profile')

    def test_trace_called_in_task(self):
        self._test_func_called_in_task('trace')



if __name__ == '__main__':
    greentest.main()
