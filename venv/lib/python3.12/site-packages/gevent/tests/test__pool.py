from time import time
import gevent
import gevent.pool
from gevent.event import Event
from gevent.queue import Queue

import gevent.testing as greentest
import gevent.testing.timing
import random
from gevent.testing import ExpectedException

import unittest


class TestCoroutinePool(unittest.TestCase):
    klass = gevent.pool.Pool

    def test_apply_async(self):
        done = Event()

        def some_work(_):
            done.set()

        pool = self.klass(2)
        pool.apply_async(some_work, ('x', ))
        done.wait()

    def test_apply(self):
        value = 'return value'

        def some_work():
            return value

        pool = self.klass(2)
        result = pool.apply(some_work)
        self.assertEqual(value, result)

    def test_apply_raises(self):
        pool = self.klass(1)

        def raiser():
            raise ExpectedException()
        try:
            pool.apply(raiser)
        except ExpectedException:
            pass
        else:
            self.fail("Should have raised ExpectedException")
    # Don't let the metaclass automatically force any error
    # that reaches the hub from a spawned greenlet to become
    # fatal; that defeats the point of the test.
    test_apply_raises.error_fatal = False

    def test_multiple_coros(self):
        evt = Event()
        results = []

        def producer():
            gevent.sleep(0.001)
            results.append('prod')
            evt.set()

        def consumer():
            results.append('cons1')
            evt.wait()
            results.append('cons2')

        pool = self.klass(2)
        done = pool.spawn(consumer)
        pool.apply_async(producer)
        done.get()
        self.assertEqual(['cons1', 'prod', 'cons2'], results)

    def dont_test_timer_cancel(self):
        timer_fired = []

        def fire_timer():
            timer_fired.append(True)

        def some_work():
            gevent.timer(0, fire_timer) # pylint:disable=no-member

        pool = self.klass(2)
        pool.apply(some_work)
        gevent.sleep(0)
        self.assertEqual(timer_fired, [])

    def test_reentrant(self):
        pool = self.klass(1)
        result = pool.apply(pool.apply, (lambda a: a + 1, (5, )))
        self.assertEqual(result, 6)
        evt = Event()
        pool.apply_async(evt.set)
        evt.wait()

    @greentest.skipOnPyPy("Does not work on PyPy") # Why?
    def test_stderr_raising(self):
        # testing that really egregious errors in the error handling code
        # (that prints tracebacks to stderr) don't cause the pool to lose
        # any members
        import sys
        pool = self.klass(size=1)

        # we're going to do this by causing the traceback.print_exc in
        # safe_apply to raise an exception and thus exit _main_loop
        normal_err = sys.stderr
        try:
            sys.stderr = FakeFile()
            waiter = pool.spawn(crash)
            with gevent.Timeout(2):
                # Without the timeout, we can get caught...doing something?
                # If we call PyErr_WriteUnraisable at a certain point,
                # we appear to switch back to the hub and do nothing,
                # meaning we sit forever. The timeout at least keeps us from
                # doing that and fails the test if we mess up error handling.
                self.assertRaises(RuntimeError, waiter.get)
            # the pool should have something free at this point since the
            # waiter returned
            # pool.Pool change: if an exception is raised during execution of a link,
            # the rest of the links are scheduled to be executed on the next hub iteration
            # this introduces a delay in updating pool.sem which makes pool.free_count() report 0
            # therefore, sleep:
            gevent.sleep(0)
            self.assertEqual(pool.free_count(), 1)
            # shouldn't block when trying to get
            with gevent.Timeout.start_new(0.1):
                pool.apply(gevent.sleep, (0, ))
        finally:
            sys.stderr = normal_err
            pool.join()


def crash(*_args, **_kw):
    raise RuntimeError("Raising an error from the crash() function")


class FakeFile(object):

    def write(self, *_args):
        raise RuntimeError('Writing to the file failed')


class PoolBasicTests(greentest.TestCase):
    klass = gevent.pool.Pool

    def test_execute_async(self):
        p = self.klass(size=2)
        self.assertEqual(p.free_count(), 2)
        r = []

        first = p.spawn(r.append, 1)
        self.assertEqual(p.free_count(), 1)
        first.get()
        self.assertEqual(r, [1])
        gevent.sleep(0)
        self.assertEqual(p.free_count(), 2)

        #Once the pool is exhausted, calling an execute forces a yield.

        p.apply_async(r.append, (2, ))
        self.assertEqual(1, p.free_count())
        self.assertEqual(r, [1])

        p.apply_async(r.append, (3, ))
        self.assertEqual(0, p.free_count())
        self.assertEqual(r, [1])

        p.apply_async(r.append, (4, ))
        self.assertEqual(r, [1])
        gevent.sleep(0.01)
        self.assertEqual(sorted(r), [1, 2, 3, 4])

    def test_discard(self):
        p = self.klass(size=1)
        first = p.spawn(gevent.sleep, 1000)
        p.discard(first)
        first.kill()
        self.assertFalse(first)
        self.assertEqual(len(p), 0)
        self.assertEqual(p._semaphore.counter, 1)

    def test_add_method(self):
        p = self.klass(size=1)
        first = gevent.spawn(gevent.sleep, 1000)
        try:
            second = gevent.spawn(gevent.sleep, 1000)
            try:
                self.assertEqual(p.free_count(), 1)
                self.assertEqual(len(p), 0)
                p.add(first)
                self.assertEqual(p.free_count(), 0)
                self.assertEqual(len(p), 1)

                with self.assertRaises(gevent.Timeout):
                    with gevent.Timeout(0.1):
                        p.add(second)

                self.assertEqual(p.free_count(), 0)
                self.assertEqual(len(p), 1)
            finally:
                second.kill()
        finally:
            first.kill()

    @greentest.ignores_leakcheck
    def test_add_method_non_blocking(self):
        p = self.klass(size=1)
        first = gevent.spawn(gevent.sleep, 1000)
        try:
            second = gevent.spawn(gevent.sleep, 1000)
            try:
                p.add(first)
                with self.assertRaises(gevent.pool.PoolFull):
                    p.add(second, blocking=False)
            finally:
                second.kill()
        finally:
            first.kill()

    @greentest.ignores_leakcheck
    def test_add_method_timeout(self):
        p = self.klass(size=1)
        first = gevent.spawn(gevent.sleep, 1000)
        try:
            second = gevent.spawn(gevent.sleep, 1000)
            try:
                p.add(first)
                with self.assertRaises(gevent.pool.PoolFull):
                    p.add(second, timeout=0.100)
            finally:
                second.kill()
        finally:
            first.kill()

    @greentest.ignores_leakcheck
    def test_start_method_timeout(self):
        p = self.klass(size=1)
        first = gevent.spawn(gevent.sleep, 1000)
        try:
            second = gevent.Greenlet(gevent.sleep, 1000)
            try:
                p.add(first)
                with self.assertRaises(gevent.pool.PoolFull):
                    p.start(second, timeout=0.100)
            finally:
                second.kill()
        finally:
            first.kill()

    def test_apply(self):
        p = self.klass()
        result = p.apply(lambda a: ('foo', a), (1, ))
        self.assertEqual(result, ('foo', 1))

    def test_init_error(self):
        self.switch_expected = False
        self.assertRaises(ValueError, self.klass, -1)

#
# tests from standard library test/test_multiprocessing.py


class TimingWrapper(object):

    def __init__(self, func):
        self.func = func
        self.elapsed = None

    def __call__(self, *args, **kwds):
        t = time()
        try:
            return self.func(*args, **kwds)
        finally:
            self.elapsed = time() - t


def sqr(x, wait=0.0):
    gevent.sleep(wait)
    return x * x


def squared(x):
    return x * x


def sqr_random_sleep(x):
    gevent.sleep(random.random() * 0.1)
    return x * x


def final_sleep():
    for i in range(3):
        yield i
    gevent.sleep(0.2)


TIMEOUT1, TIMEOUT2, TIMEOUT3 = 0.082, 0.035, 0.14


SMALL_RANGE = 10
LARGE_RANGE = 1000

if (greentest.PYPY and greentest.WIN) or greentest.RUN_LEAKCHECKS or greentest.RUN_COVERAGE:
    # See comments in test__threadpool.py.
    LARGE_RANGE = 25
elif greentest.RUNNING_ON_CI or greentest.EXPECT_POOR_TIMER_RESOLUTION:
    LARGE_RANGE = 100

class TestPool(greentest.TestCase): # pylint:disable=too-many-public-methods
    __timeout__ = greentest.LARGE_TIMEOUT
    size = 1

    def setUp(self):
        greentest.TestCase.setUp(self)
        self.pool = gevent.pool.Pool(self.size)

    def cleanup(self):
        self.pool.join()

    def test_apply(self):
        papply = self.pool.apply
        self.assertEqual(papply(sqr, (5,)), 25)
        self.assertEqual(papply(sqr, (), {'x': 3}), 9)

    def test_map(self):
        pmap = self.pool.map
        self.assertEqual(pmap(sqr, range(SMALL_RANGE)), list(map(squared, range(SMALL_RANGE))))
        self.assertEqual(pmap(sqr, range(100)), list(map(squared, range(100))))

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

    def test_imap_random(self):
        it = self.pool.imap(sqr_random_sleep, range(SMALL_RANGE))
        self.assertEqual(list(it), list(map(squared, range(SMALL_RANGE))))

    def test_imap_unordered(self):
        it = self.pool.imap_unordered(sqr, range(LARGE_RANGE))
        self.assertEqual(sorted(it), list(map(squared, range(LARGE_RANGE))))

        it = self.pool.imap_unordered(sqr, range(LARGE_RANGE))
        self.assertEqual(sorted(it), list(map(squared, range(LARGE_RANGE))))

    def test_imap_unordered_random(self):
        it = self.pool.imap_unordered(sqr_random_sleep, range(SMALL_RANGE))
        self.assertEqual(sorted(it), list(map(squared, range(SMALL_RANGE))))

    def test_empty_imap_unordered(self):
        it = self.pool.imap_unordered(sqr, [])
        self.assertEqual(list(it), [])

    def test_empty_imap(self):
        it = self.pool.imap(sqr, [])
        self.assertEqual(list(it), [])

    def test_empty_map(self):
        self.assertEqual(self.pool.map(sqr, []), [])

    def test_terminate(self):
        result = self.pool.map_async(gevent.sleep, [0.1] * ((self.size or 10) * 2))
        gevent.sleep(0.1)
        kill = TimingWrapper(self.pool.kill)
        kill()
        self.assertTimeWithinRange(kill.elapsed, 0.0, 0.5)
        result.join()

    def sleep(self, x):
        gevent.sleep(float(x) / 10.)
        return str(x)

    def test_imap_unordered_sleep(self):
        # testing that imap_unordered returns items in competion order
        result = list(self.pool.imap_unordered(self.sleep, [10, 1, 2]))
        if self.pool.size == 1:
            expected = ['10', '1', '2']
        else:
            expected = ['1', '2', '10']
        self.assertEqual(result, expected)

    # https://github.com/gevent/gevent/issues/423
    def test_imap_no_stop(self):
        q = Queue()
        q.put(123)
        gevent.spawn_later(0.1, q.put, StopIteration)
        result = list(self.pool.imap(lambda _: _, q))
        self.assertEqual(result, [123])

    def test_imap_unordered_no_stop(self):
        q = Queue()
        q.put(1234)
        gevent.spawn_later(0.1, q.put, StopIteration)
        result = list(self.pool.imap_unordered(lambda _: _, q))
        self.assertEqual(result, [1234])

    # same issue, but different test: https://github.com/gevent/gevent/issues/311
    def test_imap_final_sleep(self):
        result = list(self.pool.imap(sqr, final_sleep()))
        self.assertEqual(result, [0, 1, 4])

    def test_imap_unordered_final_sleep(self):
        result = list(self.pool.imap_unordered(sqr, final_sleep()))
        self.assertEqual(result, [0, 1, 4])

    # Issue 638
    def test_imap_unordered_bounded_queue(self):
        iterable = list(range(100))

        running = [0]

        def short_running_func(i, _j):
            running[0] += 1
            return i

        def make_reader(mapping):
            # Simulate a long running reader. No matter how many workers
            # we have, we will never have a queue more than size 1
            def reader():
                result = []
                for i, x in enumerate(mapping):
                    self.assertTrue(running[0] <= i + 2, running[0])
                    result.append(x)
                    gevent.sleep(0.01)
                    self.assertTrue(len(mapping.queue) <= 2, len(mapping.queue))
                return result
            return reader

        # Send two iterables to make sure varargs and kwargs are handled
        # correctly
        for meth in self.pool.imap_unordered, self.pool.imap:
            running[0] = 0
            mapping = meth(short_running_func, iterable, iterable,
                           maxsize=1)

            reader = make_reader(mapping)
            l = reader()
            self.assertEqual(sorted(l), iterable)

@greentest.ignores_leakcheck
class TestPool2(TestPool):
    size = 2

@greentest.ignores_leakcheck
class TestPool3(TestPool):
    size = 3

@greentest.ignores_leakcheck
class TestPool10(TestPool):
    size = 10


class TestPoolUnlimit(TestPool):
    size = None


class TestPool0(greentest.TestCase):
    size = 0

    def test_wait_full(self):
        p = gevent.pool.Pool(size=0)
        self.assertEqual(0, p.free_count())
        self.assertTrue(p.full())
        self.assertEqual(0, p.wait_available(timeout=0.01))


class TestJoinSleep(gevent.testing.timing.AbstractGenericWaitTestCase):

    def wait(self, timeout):
        p = gevent.pool.Pool()
        g = p.spawn(gevent.sleep, 10)
        try:
            p.join(timeout=timeout)
        finally:
            g.kill()


class TestJoinSleep_raise_error(gevent.testing.timing.AbstractGenericWaitTestCase):

    def wait(self, timeout):
        p = gevent.pool.Pool()
        g = p.spawn(gevent.sleep, 10)
        try:
            p.join(timeout=timeout, raise_error=True)
        finally:
            g.kill()


class TestJoinEmpty(greentest.TestCase):
    switch_expected = False

    def test(self):
        p = gevent.pool.Pool()
        res = p.join()
        self.assertTrue(res, "empty should return true")


class TestSpawn(greentest.TestCase):
    switch_expected = True

    def test(self):
        p = gevent.pool.Pool(1)
        self.assertEqual(len(p), 0)
        p.spawn(gevent.sleep, 0.1)
        self.assertEqual(len(p), 1)
        p.spawn(gevent.sleep, 0.1)  # this spawn blocks until the old one finishes
        self.assertEqual(len(p), 1)
        gevent.sleep(0.19 if not greentest.EXPECT_POOR_TIMER_RESOLUTION else 0.5)
        self.assertEqual(len(p), 0)

    def testSpawnAndWait(self):
        p = gevent.pool.Pool(1)
        self.assertEqual(len(p), 0)
        p.spawn(gevent.sleep, 0.1)
        self.assertEqual(len(p), 1)
        res = p.join(0.01)
        self.assertFalse(res, "waiting on a full pool should return false")
        res = p.join()
        self.assertTrue(res, "waiting to finish should be true")
        self.assertEqual(len(p), 0)

def error_iter():
    yield 1
    yield 2
    raise ExpectedException


class TestErrorInIterator(greentest.TestCase):
    error_fatal = False

    def test(self):
        p = gevent.pool.Pool(3)
        self.assertRaises(ExpectedException, p.map, lambda x: None, error_iter())
        gevent.sleep(0.001)

    def test_unordered(self):
        p = gevent.pool.Pool(3)

        def unordered():
            return list(p.imap_unordered(lambda x: None, error_iter()))

        self.assertRaises(ExpectedException, unordered)
        gevent.sleep(0.001)


def divide_by(x):
    return 1.0 / x


class TestErrorInHandler(greentest.TestCase):
    error_fatal = False

    def test_map(self):
        p = gevent.pool.Pool(3)
        self.assertRaises(ZeroDivisionError, p.map, divide_by, [1, 0, 2])

    def test_imap(self):
        p = gevent.pool.Pool(1)
        it = p.imap(divide_by, [1, 0, 2])
        self.assertEqual(next(it), 1.0)
        self.assertRaises(ZeroDivisionError, next, it)
        self.assertEqual(next(it), 0.5)
        self.assertRaises(StopIteration, next, it)

    def test_imap_unordered(self):
        p = gevent.pool.Pool(1)
        it = p.imap_unordered(divide_by, [1, 0, 2])
        self.assertEqual(next(it), 1.0)
        self.assertRaises(ZeroDivisionError, next, it)
        self.assertEqual(next(it), 0.5)
        self.assertRaises(StopIteration, next, it)


if __name__ == '__main__':
    greentest.main()
