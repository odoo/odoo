import sys
import gevent.testing as greentest
import gevent
from gevent.hub import get_hub

def raise_(ex):
    raise ex


MSG = 'should be re-raised and caught'


class Test(greentest.TestCase):
    x = None
    error_fatal = False

    def start(self, *args):
        raise NotImplementedError

    def setUp(self):
        self.x = None

    def test_sys_exit(self):
        self.start(sys.exit, MSG)

        try:
            gevent.sleep(0.001)
        except SystemExit as ex:
            assert str(ex) == MSG, repr(str(ex))
        else:
            raise AssertionError('must raise SystemExit')

    def test_keyboard_interrupt(self):
        self.start(raise_, KeyboardInterrupt)

        try:
            gevent.sleep(0.001)
        except KeyboardInterrupt:
            pass
        else:
            raise AssertionError('must raise KeyboardInterrupt')

    def test_keyboard_interrupt_stderr_patched(self):
        # XXX: This one non-top-level call prevents us from being
        # run in a process with other tests.
        from gevent import monkey
        monkey.patch_sys(stdin=False, stdout=False, stderr=True)
        try:
            try:
                self.start(raise_, KeyboardInterrupt)
                while True:
                    gevent.sleep(0.1)
            except KeyboardInterrupt:
                pass # expected
        finally:
            sys.stderr = monkey.get_original('sys', 'stderr')

    def test_system_error(self):
        self.start(raise_, SystemError(MSG))

        with self.assertRaisesRegex(SystemError,
                                    MSG):
            gevent.sleep(0.002)

    def test_exception(self):
        self.start(raise_, Exception('regular exception must not kill the program'))
        gevent.sleep(0.001)


class TestCallback(Test):

    def tearDown(self):
        if self.x is not None:
            # libuv: See the notes in libuv/loop.py:loop._start_callback_timer
            # If that's broken, test_exception can fail sporadically.
            # If the issue is the same, then adding `gevent.sleep(0)` here
            # will solve it. There's also a race condition for the first loop,
            # so we sleep twice.
            assert not self.x.pending, self.x

    def start(self, *args):
        self.x = get_hub().loop.run_callback(*args)

    if greentest.LIBUV:
        def test_exception(self):
            # This call will enter the loop for the very first time (if we're running
            # standalone). On libuv, where timers run first, that means that depending on the
            # amount of time that elapses between the call to uv_timer_start and uv_run,
            # this timer might fire before our check or prepare watchers, and hence callbacks,
            # run.
            # We make this call now so that the call in the super class is guaranteed to be
            # somewhere in the loop and not subject to that race condition.
            gevent.sleep(0.001)
            super(TestCallback, self).test_exception()

class TestSpawn(Test):

    def tearDown(self):
        gevent.sleep(0.0001)
        if self.x is not None:
            assert self.x.dead, self.x

    def start(self, *args):
        self.x = gevent.spawn(*args)


del Test

if __name__ == '__main__':
    greentest.main()
