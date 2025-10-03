from __future__ import print_function
from __future__ import absolute_import

from gevent.thread import allocate_lock

import gevent.testing as greentest

try:
    from _thread import allocate_lock as std_allocate_lock
except ImportError: # Py2
    from thread import allocate_lock as std_allocate_lock


class TestLock(greentest.TestCase):

    def test_release_unheld_lock(self):
        std_lock = std_allocate_lock()
        g_lock = allocate_lock()
        with self.assertRaises(Exception) as exc:
            std_lock.release()
        std_exc = exc.exception

        with self.assertRaises(Exception) as exc:
            g_lock.release()
        g_exc = exc.exception

        self.assertIsInstance(g_exc, type(std_exc))


if __name__ == '__main__':
    greentest.main()
