import gevent.testing as greentest
from gevent import socket
import errno
import sys


class TestClosedSocket(greentest.TestCase):

    switch_expected = False

    def test(self):
        sock = socket.socket()
        sock.close()
        try:
            sock.send(b'a', timeout=1)
            self.fail("Should raise socket error")
        except (socket.error, OSError) as ex:
            if ex.args[0] != errno.EBADF:
                if sys.platform.startswith('win'):
                    # Windows/Py3 raises "OSError: [WinError 10038] "
                    # which is not standard and not what it does
                    # on Py2.
                    pass
                else:
                    raise


class TestRef(greentest.TestCase):

    switch_expected = False

    def test(self):
        # pylint:disable=no-member
        sock = socket.socket()
        self.assertTrue(sock.ref)
        sock.ref = False
        self.assertFalse(sock.ref)
        self.assertFalse(sock._read_event.ref)
        self.assertFalse(sock._write_event.ref)
        sock.close()


if __name__ == '__main__':
    greentest.main()
