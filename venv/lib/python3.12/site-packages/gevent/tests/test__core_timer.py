from __future__ import print_function
from gevent import config

import gevent.testing as greentest
from gevent.testing import TestCase
from gevent.testing import LARGE_TIMEOUT
from gevent.testing.sysinfo import CFFI_BACKEND
from gevent.testing.flaky import reraises_flaky_timeout


class Test(TestCase):
    __timeout__ = LARGE_TIMEOUT

    repeat = 0
    timer_duration = 0.001

    def setUp(self):
        super(Test, self).setUp()
        self.called = []
        self.loop = config.loop(default=False)
        self.timer = self.loop.timer(self.timer_duration, repeat=self.repeat)
        assert not self.loop.default

    def cleanup(self):
        # cleanup instead of tearDown to cooperate well with
        # leakcheck.py
        self.timer.close()
        # cycle the loop so libuv close callbacks fire
        self.loop.run()
        self.loop.destroy()
        self.loop = None
        self.timer = None

    def f(self, x=None):
        self.called.append(1)
        if x is not None:
            x.stop()

    def assertTimerInKeepalive(self):
        if CFFI_BACKEND:
            self.assertIn(self.timer, self.loop._keepaliveset)

    def assertTimerNotInKeepalive(self):
        if CFFI_BACKEND:
            self.assertNotIn(self.timer, self.loop._keepaliveset)

    def test_main(self):
        loop = self.loop
        x = self.timer
        x.start(self.f)
        self.assertTimerInKeepalive()
        self.assertTrue(x.active, x)

        with self.assertRaises((AttributeError, ValueError)):
            x.priority = 1

        loop.run()
        self.assertEqual(x.pending, 0)
        self.assertEqual(self.called, [1])
        self.assertIsNone(x.callback)
        self.assertIsNone(x.args)

        if x.priority is not None:
            self.assertEqual(x.priority, 0)
            x.priority = 1
            self.assertEqual(x.priority, 1)

        x.stop()
        self.assertTimerNotInKeepalive()

class TestAgain(Test):
    repeat = 1

    def test_main(self):
        # Again works for a new timer
        x = self.timer
        x.again(self.f, x)
        self.assertTimerInKeepalive()

        self.assertEqual(x.args, (x,))

        # XXX: On libev, this takes 1 second. On libuv,
        # it takes the expected time.
        self.loop.run()

        self.assertEqual(self.called, [1])

        x.stop()
        self.assertTimerNotInKeepalive()


class TestTimerResolution(Test):

    # On CI, with *all* backends, sometimes we get timer values of
    # 0.02 or higher.
    @reraises_flaky_timeout(AssertionError)
    def test_resolution(self): # pylint:disable=too-many-locals
        # Make sure that having an active IO watcher
        # doesn't badly throw off our timer resolution.
        # (This was a specific problem with libuv)

        # https://github.com/gevent/gevent/pull/1194
        from gevent._compat import perf_counter

        import socket
        s = socket.socket()
        self._close_on_teardown(s)
        fd = s.fileno()

        ran_at_least_once = False
        fired_at = []

        def timer_counter():
            fired_at.append(perf_counter())

        loop = self.loop

        timer_multiplier = 11
        max_time = self.timer_duration * timer_multiplier
        assert max_time < 0.3

        for _ in range(150):
            # in libuv, our signal timer fires every 300ms; depending on
            # when this runs, we could artificially get a better
            # resolution than we expect. Run it multiple times to be more sure.
            io = loop.io(fd, 1)
            io.start(lambda events=None: None)


            now = perf_counter()
            del fired_at[:]
            timer = self.timer
            timer.start(timer_counter)

            loop.run(once=True)

            io.stop()
            io.close()

            timer.stop()

            if fired_at:
                ran_at_least_once = True
                self.assertEqual(1, len(fired_at))
                self.assertTimeWithinRange(fired_at[0] - now,
                                           0,
                                           max_time)


        if not greentest.RUNNING_ON_CI:
            # Hmm, this always fires locally on mocOS but
            # not an Travis?
            self.assertTrue(ran_at_least_once)


if __name__ == '__main__':
    greentest.main()
