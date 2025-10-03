import sys
import unittest
import threading
import gevent
import gevent.monkey
gevent.monkey.patch_all()


@unittest.skipUnless(
    sys.version_info[0] == 2,
    "Only on Python 2"
)
class Test(unittest.TestCase):

    def test(self):
        self.assertIs(threading._sleep, gevent.sleep)

if __name__ == '__main__':
    unittest.main()
