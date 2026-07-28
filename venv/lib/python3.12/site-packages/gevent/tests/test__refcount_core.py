import sys
import weakref

from gevent import testing as greentest


class Dummy(object):
    def __init__(self):
        __import__('gevent.core')

@greentest.skipIf(weakref.ref(Dummy())() is not None,
                  "Relies on refcounting for fast weakref cleanup")
class Test(greentest.TestCase):
    def test(self):
        from gevent import socket
        s = socket.socket()
        r = weakref.ref(s)
        s.close()
        del s
        self.assertIsNone(r())

assert weakref.ref(Dummy())() is None or hasattr(sys, 'pypy_version_info')

if __name__ == '__main__':
    greentest.main()
