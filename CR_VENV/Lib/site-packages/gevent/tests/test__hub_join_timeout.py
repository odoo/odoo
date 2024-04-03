import functools
import unittest

import gevent
import gevent.core
from gevent.event import Event

from gevent.testing.testcase import TimeAssertMixin

SMALL_TICK = 0.05

# setting up signal does not affect join()
gevent.signal_handler(1, lambda: None)  # wouldn't work on windows


def repeated(func, repetitions=2):
    @functools.wraps(func)
    def f(self):
        for _ in range(repetitions):
            func(self)
    return f

class Test(TimeAssertMixin, unittest.TestCase):

    @repeated
    def test_callback(self):
        # exiting because the spawned greenlet finished execution (spawn (=callback) variant)
        x = gevent.spawn(lambda: 5)
        with self.runs_in_no_time():
            result = gevent.wait(timeout=10)
        self.assertTrue(result)
        self.assertTrue(x.dead, x)
        self.assertEqual(x.value, 5)

    @repeated
    def test_later(self):
        # exiting because the spawned greenlet finished execution (spawn_later (=timer) variant)
        x = gevent.spawn_later(SMALL_TICK, lambda: 5)
        with self.runs_in_given_time(SMALL_TICK):
            result = gevent.wait(timeout=10)
        self.assertTrue(result)
        self.assertTrue(x.dead, x)

    @repeated
    def test_timeout(self):
        # exiting because of timeout (the spawned greenlet still runs)
        x = gevent.spawn_later(10, lambda: 5)
        with self.runs_in_given_time(SMALL_TICK):
            result = gevent.wait(timeout=SMALL_TICK)
        self.assertFalse(result)
        self.assertFalse(x.dead, x)
        x.kill()
        with self.runs_in_no_time():
            result = gevent.wait()

        self.assertTrue(result)

    @repeated
    def test_event(self):
        # exiting because of event (the spawned greenlet still runs)
        x = gevent.spawn_later(10, lambda: 5)
        event = Event()
        event_set = gevent.spawn_later(SMALL_TICK, event.set)
        with self.runs_in_given_time(SMALL_TICK):
            result = gevent.wait([event])
        self.assertEqual(result, [event])
        self.assertFalse(x.dead, x)
        self.assertTrue(event_set.dead)
        self.assertTrue(event.is_set)
        x.kill()
        with self.runs_in_no_time():
            result = gevent.wait()

        self.assertTrue(result)

    @repeated
    def test_ref_arg(self):
        # checking "ref=False" argument
        gevent.get_hub().loop.timer(10, ref=False).start(lambda: None)
        with self.runs_in_no_time():
            result = gevent.wait()
        self.assertTrue(result)

    @repeated
    def test_ref_attribute(self):
        # checking "ref=False" attribute
        w = gevent.get_hub().loop.timer(10)
        w.start(lambda: None)
        w.ref = False
        with self.runs_in_no_time():
            result = gevent.wait()
        self.assertTrue(result)


class TestAgain(Test):
    "Repeat the same tests"

if __name__ == '__main__':
    unittest.main()
