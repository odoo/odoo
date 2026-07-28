from gevent.testing import six
import sys
import os
import errno
from gevent import select, socket
import gevent.core
import gevent.testing as greentest
import gevent.testing.timing
import unittest


class TestSelect(gevent.testing.timing.AbstractGenericWaitTestCase):

    def wait(self, timeout):
        select.select([], [], [], timeout)



@greentest.skipOnWindows("Cant select on files")
class TestSelectRead(gevent.testing.timing.AbstractGenericWaitTestCase):

    def wait(self, timeout):
        r, w = os.pipe()
        try:
            select.select([r], [], [], timeout)
        finally:
            os.close(r)
            os.close(w)

    # Issue #12367: http://www.freebsd.org/cgi/query-pr.cgi?pr=kern/155606
    @unittest.skipIf(sys.platform.startswith('freebsd'),
                     'skip because of a FreeBSD bug: kern/155606')
    def test_errno(self):
        # Backported from test_select.py in 3.4
        with open(__file__, 'rb') as fp:
            fd = fp.fileno()
            fp.close()
            try:
                select.select([fd], [], [], 0)
            except OSError as err:
                # Python 3
                self.assertEqual(err.errno, errno.EBADF)
            except select.error as err: # pylint:disable=duplicate-except
                # Python 2 (select.error is OSError on py3)
                self.assertEqual(err.args[0], errno.EBADF)
            else:
                self.fail("exception not raised")


@unittest.skipUnless(hasattr(select, 'poll'), "Needs poll")
@greentest.skipOnWindows("Cant poll on files")
class TestPollRead(gevent.testing.timing.AbstractGenericWaitTestCase):
    def wait(self, timeout):
        # On darwin, the read pipe is reported as writable
        # immediately, for some reason. So we carefully register
        # it only for read events (the default is read and write)
        r, w = os.pipe()
        try:
            poll = select.poll()
            poll.register(r, select.POLLIN)
            poll.poll(timeout * 1000)
        finally:
            poll.unregister(r)
            os.close(r)
            os.close(w)

    def test_unregister_never_registered(self):
        # "Attempting to remove a file descriptor that was
        # never registered causes a KeyError exception to be
        # raised."
        poll = select.poll()
        self.assertRaises(KeyError, poll.unregister, 5)

    def test_poll_invalid(self):
        self.skipTest(
            "libev >= 4.27 aborts the process if built with EV_VERIFY >= 2. "
            "For libuv, depending on whether the fileno is reused or not "
            "this either crashes or does nothing.")
        with open(__file__, 'rb') as fp:
            fd = fp.fileno()

            poll = select.poll()
            poll.register(fd, select.POLLIN)
            # Close after registering; libuv refuses to even
            # create a watcher if it would get EBADF (so this turns into
            # a test of whether or not we successfully initted the watcher).
            fp.close()
            result = poll.poll(0)
            self.assertEqual(result, [(fd, select.POLLNVAL)]) # pylint:disable=no-member

class TestSelectTypes(greentest.TestCase):

    def test_int(self):
        sock = socket.socket()
        try:
            select.select([int(sock.fileno())], [], [], 0.001)
        finally:
            sock.close()

    if hasattr(six.builtins, 'long'):
        def test_long(self):
            sock = socket.socket()
            try:
                select.select(
                    [six.builtins.long(sock.fileno())], [], [], 0.001)
            finally:
                sock.close()

    def test_iterable(self):
        sock = socket.socket()

        def fileno_iter():
            yield int(sock.fileno())

        try:
            select.select(fileno_iter(), [], [], 0.001)
        finally:
            sock.close()

    def test_string(self):
        self.switch_expected = False
        self.assertRaises(TypeError, select.select, ['hello'], [], [], 0.001)


if __name__ == '__main__':
    greentest.main()
