# If stdlib threading is imported *BEFORE* monkey patching, *and*
# there is a native thread created, we can still get the current
# (main) thread, and it's not a DummyThread.
# Joining the native thread also does not fail

import threading
from time import sleep as time_sleep

import gevent.testing as greentest

class NativeThread(threading.Thread):
    do_run = True

    def run(self):
        while self.do_run:
            time_sleep(0.1)

    def stop(self, timeout=None):
        self.do_run = False
        self.join(timeout=timeout)

native_thread = None

class Test(greentest.TestCase):

    @classmethod
    def tearDownClass(cls):
        global native_thread
        if native_thread is not None:
            native_thread.stop(1)
            native_thread = None

    def test_main_thread(self):
        current = threading.current_thread()
        self.assertNotIsInstance(current, threading._DummyThread)
        self.assertIsInstance(current, monkey.get_original('threading', 'Thread'))
        # in 3.4, if the patch is incorrectly done, getting the repr
        # of the thread fails
        repr(current)

        if hasattr(threading, 'main_thread'): # py 3.4
            self.assertEqual(threading.current_thread(), threading.main_thread())

    @greentest.ignores_leakcheck # because it can't be run multiple times
    def test_join_native_thread(self):
        if native_thread is None or not native_thread.do_run: # pragma: no cover
            self.skipTest("native_thread already closed")

        self.assertTrue(native_thread.is_alive())

        native_thread.stop(timeout=1)
        self.assertFalse(native_thread.is_alive())

        # again, idempotent
        native_thread.stop()
        self.assertFalse(native_thread.is_alive())


if __name__ == '__main__':
    native_thread = NativeThread()
    native_thread.daemon = True
    native_thread.start()

    # Only patch after we're running
    from gevent import monkey
    monkey.patch_all() # pragma: testrunner-no-monkey-combine

    greentest.main()
