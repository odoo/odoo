from __future__ import print_function, division, absolute_import
import time
import gevent.testing as greentest

from gevent.testing import timing
import gevent
from gevent import pool
from gevent.timeout import Timeout

DELAY = timing.LARGE_TICK


class SpecialError(Exception):
    pass


class Undead(object):

    def __init__(self):
        self.shot_count = 0

    def __call__(self):
        while True:
            try:
                gevent.sleep(1)
            except SpecialError:
                break
            except: # pylint:disable=bare-except
                self.shot_count += 1


class Test(greentest.TestCase):

    __timeout__ = greentest.LARGE_TIMEOUT

    def test_basic(self):
        s = pool.Group()
        s.spawn(gevent.sleep, timing.LARGE_TICK)
        self.assertEqual(len(s), 1, s)
        s.spawn(gevent.sleep, timing.LARGE_TICK * 5)
        self.assertEqual(len(s), 2, s)
        gevent.sleep()
        gevent.sleep(timing.LARGE_TICK * 2 + timing.LARGE_TICK_MIN_ADJ)
        self.assertEqual(len(s), 1, s)
        gevent.sleep(timing.LARGE_TICK * 5 + timing.LARGE_TICK_MIN_ADJ)
        self.assertFalse(s)

    def test_waitall(self):
        s = pool.Group()
        s.spawn(gevent.sleep, DELAY)
        s.spawn(gevent.sleep, DELAY * 2)
        assert len(s) == 2, s
        start = time.time()
        s.join(raise_error=True)
        delta = time.time() - start
        self.assertFalse(s)
        self.assertEqual(len(s), 0)
        self.assertTimeWithinRange(delta, DELAY * 1.9, DELAY * 2.5)

    def test_kill_block(self):
        s = pool.Group()
        s.spawn(gevent.sleep, DELAY)
        s.spawn(gevent.sleep, DELAY * 2)
        assert len(s) == 2, s
        start = time.time()
        s.kill()
        self.assertFalse(s)
        self.assertEqual(len(s), 0)
        delta = time.time() - start
        assert delta < DELAY * 0.8, delta

    def test_kill_noblock(self):
        s = pool.Group()
        s.spawn(gevent.sleep, DELAY)
        s.spawn(gevent.sleep, DELAY * 2)
        assert len(s) == 2, s
        s.kill(block=False)
        assert len(s) == 2, s
        gevent.sleep(0.0001)
        self.assertFalse(s)
        self.assertEqual(len(s), 0)

    def test_kill_fires_once(self):
        u1 = Undead()
        u2 = Undead()
        p1 = gevent.spawn(u1)
        p2 = gevent.spawn(u2)

        def check(count1, count2):
            self.assertTrue(p1)
            self.assertTrue(p2)
            self.assertFalse(p1.dead, p1)
            self.assertFalse(p2.dead, p2)
            self.assertEqual(u1.shot_count, count1)
            self.assertEqual(u2.shot_count, count2)

        gevent.sleep(0.01)
        s = pool.Group([p1, p2])
        self.assertEqual(len(s), 2, s)
        check(0, 0)
        s.killone(p1, block=False)
        check(0, 0)
        gevent.sleep(0)
        check(1, 0)
        s.killone(p1)
        check(1, 0)
        s.killone(p1)
        check(1, 0)
        s.kill(block=False)
        s.kill(block=False)
        s.kill(block=False)
        check(1, 0)
        gevent.sleep(DELAY)
        check(1, 1)
        X = object()
        kill_result = gevent.with_timeout(DELAY, s.kill, block=True, timeout_value=X)
        assert kill_result is X, repr(kill_result)
        assert len(s) == 2, s
        check(1, 1)

        p1.kill(SpecialError)
        p2.kill(SpecialError)

    def test_killall_subclass(self):
        p1 = GreenletSubclass.spawn(lambda: 1 / 0)
        p2 = GreenletSubclass.spawn(lambda: gevent.sleep(10))
        s = pool.Group([p1, p2])
        s.kill()

    def test_killall_iterable_argument_non_block(self):
        p1 = GreenletSubclass.spawn(lambda: gevent.sleep(0.5))
        p2 = GreenletSubclass.spawn(lambda: gevent.sleep(0.5))
        s = set()
        s.add(p1)
        s.add(p2)
        gevent.killall(s, block=False)
        gevent.sleep(0.5)
        for g in s:
            assert g.dead

    def test_killall_iterable_argument_timeout_not_started(self):
        def f():
            try:
                gevent.sleep(1.5)
            except: # pylint:disable=bare-except
                gevent.sleep(1)
        p1 = GreenletSubclass.spawn(f)
        p2 = GreenletSubclass.spawn(f)
        s = set()
        s.add(p1)
        s.add(p2)
        gevent.killall(s, timeout=0.5)

        for g in s:
            self.assertTrue(g.dead, g)

    def test_killall_iterable_argument_timeout_started(self):
        def f():
            try:
                gevent.sleep(1.5)
            except: # pylint:disable=bare-except
                gevent.sleep(1)
        p1 = GreenletSubclass.spawn(f)
        p2 = GreenletSubclass.spawn(f)

        s = set()
        s.add(p1)
        s.add(p2)
        # Get them both running.
        gevent.sleep(timing.SMALLEST_RELIABLE_DELAY)
        with self.assertRaises(Timeout):
            gevent.killall(s, timeout=0.5)

        for g in s:
            self.assertFalse(g.dead, g)


class GreenletSubclass(gevent.Greenlet):
    pass


if __name__ == '__main__':
    greentest.main()
