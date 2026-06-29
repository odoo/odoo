###
# This file is test__semaphore.py only for organization purposes.
# The public API,
# and the *only* correct place to import Semaphore --- even in tests ---
# is ``gevent.lock``, never ``gevent._semaphore``.
##
from __future__ import print_function
from __future__ import absolute_import

import weakref

import gevent
import gevent.exceptions
from gevent.lock import Semaphore
from gevent.lock import BoundedSemaphore

import gevent.testing as greentest
from gevent.testing import timing

class TestSemaphore(greentest.TestCase):

    # issue 39
    def test_acquire_returns_false_after_timeout(self):
        s = Semaphore(value=0)
        result = s.acquire(timeout=0.01)
        assert result is False, repr(result)

    def test_release_twice(self):
        s = Semaphore()
        result = []
        s.rawlink(lambda s: result.append('a'))
        s.release()
        s.rawlink(lambda s: result.append('b'))
        s.release()
        gevent.sleep(0.001)
        # The order, though, is not guaranteed.
        self.assertEqual(sorted(result), ['a', 'b'])

    def test_semaphore_weakref(self):
        s = Semaphore()
        r = weakref.ref(s)
        self.assertEqual(s, r())

    @greentest.ignores_leakcheck
    def test_semaphore_in_class_with_del(self):
        # Issue #704. This used to crash the process
        # under PyPy through at least 4.0.1 if the Semaphore
        # was implemented with Cython.
        class X(object):
            def __init__(self):
                self.s = Semaphore()

            def __del__(self):
                self.s.acquire()

        X()
        import gc
        gc.collect()
        gc.collect()


    def test_rawlink_on_unacquired_runs_notifiers(self):
        # https://github.com/gevent/gevent/issues/1287

        # Rawlinking a ready semaphore should fire immediately,
        # not raise LoopExit
        s = Semaphore()
        gevent.wait([s])


class TestSemaphoreMultiThread(greentest.TestCase):
    # Tests that the object can be acquired correctly across
    # multiple threads.
    # Used as a base class.

    # See https://github.com/gevent/gevent/issues/1437

    def _getTargetClass(self):
        return Semaphore

    def _makeOne(self):
        # Create an object that is associated with the current hub. If
        # we don't do this now, it gets initialized lazily the first
        # time it would have to block, which, in the event of threads,
        # would be from an arbitrary thread.
        return self._getTargetClass()(1)

    def _makeThreadMain(self, thread_running, thread_acquired, sem,
                        acquired, exc_info,
                        **thread_acquire_kwargs):
        from gevent._hub_local import get_hub_if_exists
        import sys

        def thread_main():
            thread_running.set()
            try:
                acquired.append(
                    sem.acquire(**thread_acquire_kwargs)
                )
            except:
                exc_info[:] = sys.exc_info()
                raise # Print
            finally:
                hub = get_hub_if_exists()
                if hub is not None:
                    hub.join()
                    hub.destroy(destroy_loop=True)
                thread_acquired.set()
        return thread_main

    IDLE_ITERATIONS = 5

    def _do_test_acquire_in_one_then_another(self,
                                             release=True,
                                             require_thread_acquired_to_finish=False,
                                             **thread_acquire_kwargs):
        from gevent import monkey
        self.assertFalse(monkey.is_module_patched('threading'))

        import threading
        thread_running = threading.Event()
        thread_acquired = threading.Event()

        sem = self._makeOne()
        # Make future acquires block
        sem.acquire()

        exc_info = []
        acquired = []

        t = threading.Thread(target=self._makeThreadMain(
            thread_running, thread_acquired, sem,
            acquired, exc_info,
            **thread_acquire_kwargs
        ))
        t.daemon = True
        t.start()
        thread_running.wait(10) # implausibly large time
        if release:
            sem.release()
            # Spin the loop to be sure the release gets through.
            # (Release schedules the notifier to run, and when the
            # notifier run it sends the async notification to the
            # other thread. Depending on exactly where we are in the
            # event loop, and the limit to the number of callbacks
            # that get run (including time-based) the notifier may or
            # may not be immediately ready to run, so this can take up
            # to two iterations.)
            for _ in range(self.IDLE_ITERATIONS):
                gevent.idle()
                if thread_acquired.wait(timing.LARGE_TICK):
                    break

            self.assertEqual(acquired, [True])

        if not release and thread_acquire_kwargs.get("timeout"):
            # Spin the loop to be sure that the timeout has a chance to
            # process. Interleave this with something that drops the GIL
            # so the background thread has a chance to notice that.
            for _ in range(self.IDLE_ITERATIONS):
                gevent.idle()
                if thread_acquired.wait(timing.LARGE_TICK):
                    break
        thread_acquired.wait(timing.LARGE_TICK * 5)

        if require_thread_acquired_to_finish:
            self.assertTrue(thread_acquired.is_set())
        try:
            self.assertEqual(exc_info, [])
        finally:
            exc_info = None

        return sem, acquired

    def test_acquire_in_one_then_another(self):
        self._do_test_acquire_in_one_then_another(release=True)

    def test_acquire_in_one_then_another_timed(self):
        sem, acquired_in_thread = self._do_test_acquire_in_one_then_another(
            release=False,
            require_thread_acquired_to_finish=True,
            timeout=timing.SMALLEST_RELIABLE_DELAY)
        self.assertEqual([False], acquired_in_thread)
        # This doesn't, of course, notify anything, because
        # the waiter has given up.
        sem.release()
        notifier = getattr(sem, '_notifier', None)
        self.assertIsNone(notifier)

    def test_acquire_in_one_wait_greenlet_wait_thread_gives_up(self):
        # The waiter in the thread both arrives and gives up while
        # the notifier is already running...or at least, that's what
        # we'd like to arrange, but the _notify_links function doesn't
        # drop the GIL/object lock, so the other thread is stuck and doesn't
        # actually get to call into the acquire method.

        from gevent import monkey
        self.assertFalse(monkey.is_module_patched('threading'))

        import threading

        sem = self._makeOne()
        # Make future acquires block
        sem.acquire()

        def greenlet_one():
            ack = sem.acquire()
            # We're running in the notifier function right now. It switched to
            # us.
            thread.start()
            gevent.sleep(timing.LARGE_TICK)
            return ack

        exc_info = []
        acquired = []

        glet = gevent.spawn(greenlet_one)
        thread = threading.Thread(target=self._makeThreadMain(
            threading.Event(), threading.Event(),
            sem,
            acquired, exc_info,
            timeout=timing.LARGE_TICK
        ))
        thread.daemon = True
        gevent.idle()
        sem.release()
        glet.join()
        for _ in range(3):
            gevent.idle()
            thread.join(timing.LARGE_TICK)

        self.assertEqual(glet.value, True)
        self.assertEqual([], exc_info)
        self.assertEqual([False], acquired)
        self.assertTrue(glet.dead, glet)
        glet = None

    def assertOneHasNoHub(self, sem):
        self.assertIsNone(sem.hub, sem)

    @greentest.skipOnPyPyOnWindows("Flaky there; can't reproduce elsewhere")
    def test_dueling_threads(self, acquire_args=(), create_hub=None):
        # pylint:disable=too-many-locals,too-many-statements

        # Threads doing nothing but acquiring and releasing locks, without
        # having any other greenlets to switch to.
        # https://github.com/gevent/gevent/issues/1698
        from gevent import monkey
        from gevent._hub_local import get_hub_if_exists

        self.assertFalse(monkey.is_module_patched('threading'))

        import threading
        from time import sleep as native_sleep

        sem = self._makeOne()
        self.assertOneHasNoHub(sem)
        count = 10000
        results = [-1, -1]
        run = True
        def do_it(ix):
            if create_hub:
                gevent.get_hub()

            try:
                for i in range(count):
                    if not run:
                        break

                    acquired = sem.acquire(*acquire_args)
                    assert acquire_args or acquired
                    if acquired:
                        sem.release()
                    results[ix] = i
                    if not create_hub:
                        # We don't artificially create the hub.
                        self.assertIsNone(
                            get_hub_if_exists(),
                            (get_hub_if_exists(), ix, i)
                        )
                    if create_hub and i % 10 == 0:
                        gevent.sleep(timing.SMALLEST_RELIABLE_DELAY)
                    elif i % 100 == 0:
                        native_sleep(timing.SMALLEST_RELIABLE_DELAY)
            except Exception as ex: # pylint:disable=broad-except
                import traceback; traceback.print_exc()
                results[ix] = str(ex)
                ex = None
            finally:
                hub = get_hub_if_exists()
                if hub is not None:
                    hub.join()
                    hub.destroy(destroy_loop=True)

        t1 = threading.Thread(target=do_it, args=(0,))
        t1.daemon = True
        t2 = threading.Thread(target=do_it, args=(1,))
        t2.daemon = True
        t1.start()
        t2.start()

        t1.join(1)
        t2.join(1)

        while t1.is_alive() or t2.is_alive():
            cur = list(results)
            t1.join(7)
            t2.join(7)
            if cur == results:
                # Hmm, after two seconds, no progress
                run = False
                break

        self.assertEqual(results, [count - 1, count - 1])

    def test_dueling_threads_timeout(self):
        self.test_dueling_threads((True, 4))

    def test_dueling_threads_with_hub(self):
        self.test_dueling_threads(create_hub=True)


    # XXX: Need a test with multiple greenlets in a non-primary
    # thread. Things should work, just very slowly; instead of moving through
    # greenlet.switch(), they'll be moving with async watchers.

class TestBoundedSemaphoreMultiThread(TestSemaphoreMultiThread):

    def _getTargetClass(self):
        return BoundedSemaphore

@greentest.skipOnPurePython("Needs C extension")
class TestCExt(greentest.TestCase):

    def test_c_extension(self):
        self.assertEqual(Semaphore.__module__,
                         'gevent._gevent_c_semaphore')


class SwitchWithFixedHash(object):
    # Replaces greenlet.switch with a callable object
    # with a hash code we control. This only matters if
    # we're hashing this somewhere (which we used to), but
    # that doesn't preserve order, so we don't do
    # that anymore.

    def __init__(self, greenlet, hashcode):
        self.switch = greenlet.switch
        self.hashcode = hashcode

    def __hash__(self):
        raise AssertionError

    def __eq__(self, other):
        raise AssertionError

    def __call__(self, *args, **kwargs):
        return self.switch(*args, **kwargs)

    def __repr__(self):
        return repr(self.switch)

class FirstG(gevent.Greenlet):
    # A greenlet whose switch method will have a low hashcode.

    hashcode = 10

    def __init__(self, *args, **kwargs):
        gevent.Greenlet.__init__(self, *args, **kwargs)
        self.switch = SwitchWithFixedHash(self, self.hashcode)


class LastG(FirstG):
    # A greenlet whose switch method will have a high hashcode.
    hashcode = 12


def acquire_then_exit(sem, should_quit):
    sem.acquire()
    should_quit.append(True)


def acquire_then_spawn(sem, should_quit):
    if should_quit:
        return
    sem.acquire()
    g = FirstG.spawn(release_then_spawn, sem, should_quit)
    g.join()

def release_then_spawn(sem, should_quit):
    sem.release()
    if should_quit: # pragma: no cover
        return
    g = FirstG.spawn(acquire_then_spawn, sem, should_quit)
    g.join()

class TestSemaphoreFair(greentest.TestCase):

    def test_fair_or_hangs(self):
        # If the lock isn't fair, this hangs, spinning between
        # the last two greenlets.
        # See https://github.com/gevent/gevent/issues/1487
        sem = Semaphore()
        should_quit = []

        keep_going1 = FirstG.spawn(acquire_then_spawn, sem, should_quit)
        keep_going2 = FirstG.spawn(acquire_then_spawn, sem, should_quit)
        exiting = LastG.spawn(acquire_then_exit, sem, should_quit)

        with self.assertRaises(gevent.exceptions.LoopExit):
            gevent.joinall([keep_going1, keep_going2, exiting])

        self.assertTrue(exiting.dead, exiting)
        self.assertTrue(keep_going2.dead, keep_going2)
        self.assertFalse(keep_going1.dead, keep_going1)

        sem.release()
        keep_going1.kill()
        keep_going2.kill()
        exiting.kill()

        gevent.idle()

if __name__ == '__main__':
    greentest.main()
