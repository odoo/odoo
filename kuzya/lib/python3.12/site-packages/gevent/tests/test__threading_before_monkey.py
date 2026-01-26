# If stdlib threading is imported *BEFORE* monkey patching,
# we can still get the current (main) thread, and it's not a DummyThread.

import threading
from gevent import monkey
monkey.patch_all() # pragma: testrunner-no-monkey-combine

import gevent.testing as greentest


class Test(greentest.TestCase):

    def test_main_thread(self):
        current = threading.current_thread()
        self.assertFalse(isinstance(current, threading._DummyThread))
        self.assertTrue(isinstance(current, monkey.get_original('threading', 'Thread')))
        # in 3.4, if the patch is incorrectly done, getting the repr
        # of the thread fails
        repr(current)


if __name__ == '__main__':
    greentest.main()
