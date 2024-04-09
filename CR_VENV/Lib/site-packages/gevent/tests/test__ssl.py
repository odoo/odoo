from __future__ import print_function, division, absolute_import
from gevent import monkey
monkey.patch_all()
import os

import socket
import gevent.testing as greentest
# Be careful not to have TestTCP as a bare attribute in this module,
# even aliased, to avoid running duplicate tests
from gevent.tests import test__socket
import ssl

from gevent.testing import PY2

def ssl_listener(private_key, certificate):
    raw_listener = socket.socket()
    greentest.bind_and_listen(raw_listener)
    # pylint:disable=deprecated-method
    sock = ssl.wrap_socket(raw_listener, private_key, certificate, server_side=True)
    return sock, raw_listener


class TestSSL(test__socket.TestTCP):

    # To generate:
    # openssl req -x509 -newkey rsa:4096 -keyout test_server.key -out test_server.crt -days 36500 -nodes -subj '/CN=localhost'
    certfile = os.path.join(os.path.dirname(__file__), 'test_server.crt')
    privfile = os.path.join(os.path.dirname(__file__), 'test_server.key')
    # Python 2.x has socket.sslerror (which  is an alias for
    # ssl.SSLError); That's gone in Py3 though. In Python 2, most timeouts are raised
    # as SSLError, but Python 3 raises the normal socket.timeout instead. So this has
    # the effect of making TIMEOUT_ERROR be SSLError on Py2 and socket.timeout on Py3
    # See https://bugs.python.org/issue10272.
    # PyPy3 7.2 has a bug, though: it shares much of the SSL implementation with Python 2,
    # and it unconditionally does `socket.sslerror = SSLError` when ssl is imported.
    # So we can't rely on getattr/hasattr tests, we must be explicit.
    TIMEOUT_ERROR = socket.sslerror if PY2 else socket.timeout # pylint:disable=no-member

    def _setup_listener(self):
        listener, raw_listener = ssl_listener(self.privfile, self.certfile)
        self._close_on_teardown(raw_listener)
        return listener

    def create_connection(self, *args, **kwargs): # pylint:disable=signature-differs
        return self._close_on_teardown(
            # pylint:disable=deprecated-method
            ssl.wrap_socket(super(TestSSL, self).create_connection(*args, **kwargs)))

    # The SSL library can take a long time to buffer the large amount of data we're trying
    # to send, so we can't compare to the timeout values
    _test_sendall_timeout_check_time = False

    # The SSL layer has extra buffering, so test_sendall needs
    # to send a very large amount to make it timeout
    _test_sendall_data = data_sent = b'hello' * 100000000

    test_sendall_array = greentest.skipOnMacOnCI("Sometimes misses data")(
        greentest.skipOnManylinux("Sometimes misses data")(
            test__socket.TestTCP.test_sendall_array
        )
    )

    test_sendall_str = greentest.skipOnMacOnCI("Sometimes misses data")(
        greentest.skipOnManylinux("Sometimes misses data")(
            test__socket.TestTCP.test_sendall_str
        )
    )

    @greentest.skipOnWindows("Not clear why we're skipping")
    def test_ssl_sendall_timeout0(self):
        # Issue #317: SSL_WRITE_PENDING in some corner cases

        server_sock = []
        acceptor = test__socket.Thread(target=lambda: server_sock.append(
            # pylint:disable=no-member
            self.listener.accept()))
        client = self.create_connection()
        client.setblocking(False)
        try:
            # Python 3 raises ssl.SSLWantWriteError; Python 2 simply *hangs*
            # on non-blocking sockets because it's a simple loop around
            # send(). Python 2.6 doesn't have SSLWantWriteError
            expected = getattr(ssl, 'SSLWantWriteError', ssl.SSLError)
            with self.assertRaises(expected):
                client.sendall(self._test_sendall_data)
        finally:
            acceptor.join()
            client.close()
            server_sock[0][0].close()

    # def test_fullduplex(self):
    #     try:
    #         super(TestSSL, self).test_fullduplex()
    #     except LoopExit:
    #         if greentest.LIBUV and greentest.WIN:
    #             # XXX: Unable to duplicate locally
    #             raise greentest.SkipTest("libuv on Windows sometimes raises LoopExit")
    #         raise

    @greentest.ignores_leakcheck
    @greentest.skipOnPy310("No longer raises SSLError")
    def test_empty_send(self):
        # Issue 719
        # Sending empty bytes with the 'send' method raises
        # ssl.SSLEOFError in the stdlib. PyPy 4.0 and CPython 2.6
        # both just raise the superclass, ssl.SSLError.

        # Ignored during leakchecks because the third or fourth iteration of the
        # test hangs on CPython 2/posix for some reason, likely due to
        # the use of _close_on_teardown keeping something alive longer than intended.
        # cf test__makefile_ref
        with self.assertRaises(ssl.SSLError):
            super(TestSSL, self).test_empty_send()

    @greentest.ignores_leakcheck
    def test_sendall_nonblocking(self):
        # Override; doesn't work with SSL sockets.
        pass

    @greentest.ignores_leakcheck
    def test_connect_with_type_flags_ignored(self):
        # Override; doesn't work with SSL sockets.
        pass



if __name__ == '__main__':
    greentest.main()
