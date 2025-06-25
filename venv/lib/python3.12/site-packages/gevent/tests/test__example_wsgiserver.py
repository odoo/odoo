import sys

try:
    from urllib import request as urllib2
except ImportError:
    import urllib2


import socket
import ssl

import gevent.testing as greentest
from gevent.testing import DEFAULT_XPC_SOCKET_TIMEOUT
from gevent.testing import util
from gevent.testing import params

@greentest.skipOnCI("Timing issues sometimes lead to a connection refused")
class Test_wsgiserver(util.TestServer):
    example = 'wsgiserver.py'
    URL = 'http://%s:8088' % (params.DEFAULT_LOCAL_HOST_ADDR,)
    PORT = 8088
    not_found_message = b'<h1>Not Found</h1>'
    ssl_ctx = None
    _use_ssl = False

    def read(self, path='/'):
        url = self.URL + path
        try:
            kwargs = {}
            if self.ssl_ctx is not None:
                kwargs = {'context': self.ssl_ctx}

            response = urllib2.urlopen(url, None,
                                       DEFAULT_XPC_SOCKET_TIMEOUT,
                                       **kwargs)
        except urllib2.HTTPError:
            response = sys.exc_info()[1]
        result = '%s %s' % (response.code, response.msg), response.read()
        # XXX: It looks like under PyPy this isn't directly closing the socket
        # when SSL is in use. It takes a GC cycle to make that true.
        response.close()
        return result

    def _test_hello(self):
        status, data = self.read('/')
        self.assertEqual(status, '200 OK')
        self.assertEqual(data, b"<b>hello world</b>")

    def _test_not_found(self):
        status, data = self.read('/xxx')
        self.assertEqual(status, '404 Not Found')
        self.assertEqual(data, self.not_found_message)

    def _do_test_a_blocking_client(self):
        # We spawn this in a separate server because if it's broken
        # the whole server hangs
        with self.running_server():
            # First, make sure we can talk to it.
            self._test_hello()
            # Now create a connection and only partway finish
            # the transaction
            sock = socket.create_connection((params.DEFAULT_LOCAL_HOST_ADDR, self.PORT))
            ssl_sock = None
            if self._use_ssl:
                context = ssl.SSLContext()
                ssl_sock = context.wrap_socket(sock)
                sock_file = ssl_sock.makefile(mode='rwb')
            else:
                sock_file = sock.makefile(mode='rwb')
            # write an incomplete request
            sock_file.write(b'GET /xxx HTTP/1.0\r\n')
            sock_file.flush()
            # Leave it open and not doing anything
            # while the other request runs to completion.
            # This demonstrates that a blocking client
            # doesn't hang the whole server
            self._test_hello()

            # now finish the original request
            sock_file.write(b'\r\n')
            sock_file.flush()
            line = sock_file.readline()
            self.assertEqual(line, b'HTTP/1.1 404 Not Found\r\n')

            sock_file.close()
            if ssl_sock is not None:
                ssl_sock.close()
            sock.close()

    def test_a_blocking_client(self):
        self._do_test_a_blocking_client()

if __name__ == '__main__':
    greentest.main()
