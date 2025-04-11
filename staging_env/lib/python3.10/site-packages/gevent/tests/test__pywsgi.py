# Copyright (c) 2007, Linden Research, Inc.
# Copyright (c) 2009-2010 gevent contributors
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
# pylint: disable=too-many-lines,unused-argument,too-many-ancestors
from __future__ import print_function

from gevent import monkey

monkey.patch_all()

from contextlib import contextmanager
from urllib.parse import parse_qs
import os
import sys
from io import BytesIO as StringIO

import weakref
import unittest
from wsgiref.validate import validator

import gevent.testing as greentest
import gevent
from gevent.testing import PY3, PYPY
from gevent.testing.exception import ExpectedException
from gevent import socket
from gevent import pywsgi
from gevent.pywsgi import Input


class ExpectedAssertionError(ExpectedException, AssertionError):
    """An expected assertion error"""

CONTENT_LENGTH = 'Content-Length'
CONN_ABORTED_ERRORS = greentest.CONN_ABORTED_ERRORS

REASONS = {
    200: 'OK',
    500: 'Internal Server Error'
}


class ConnectionClosed(Exception):
    pass


def read_headers(fd):
    response_line = fd.readline()
    if not response_line:
        raise ConnectionClosed
    response_line = response_line.decode('latin-1')
    headers = {}
    while True:
        line = fd.readline().strip()
        if not line:
            break
        line = line.decode('latin-1')
        try:
            key, value = line.split(': ', 1)
        except:
            print('Failed to split: %r' % (line, ))
            raise
        assert key.lower() not in {x.lower() for x in headers}, 'Header %r:%r sent more than once: %r' % (key, value, headers)
        headers[key] = value
    return response_line, headers


def iread_chunks(fd):
    while True:
        line = fd.readline()
        chunk_size = line.strip()
        chunk_size = int(chunk_size, 16)
        if chunk_size == 0:
            crlf = fd.read(2)
            assert crlf == b'\r\n', repr(crlf)
            break
        data = fd.read(chunk_size)
        yield data
        crlf = fd.read(2)
        assert crlf == b'\r\n', repr(crlf)


class Response(object):

    def __init__(self, status_line, headers):
        self.status_line = status_line
        self.headers = headers
        self.body = None
        self.chunks = False
        try:
            version, code, self.reason = status_line[:-2].split(' ', 2)
            self.code = int(code)
            HTTP, self.version = version.split('/')
            assert HTTP == 'HTTP', repr(HTTP)
            assert self.version in ('1.0', '1.1'), repr(self.version)
        except Exception:
            print('Error: %r' % status_line)
            raise

    def __iter__(self):
        yield self.status_line
        yield self.headers
        yield self.body

    def __str__(self):
        args = (self.__class__.__name__, self.status_line, self.headers, self.body, self.chunks)
        return '<%s status_line=%r headers=%r body=%r chunks=%r>' % args

    def assertCode(self, code):
        if hasattr(code, '__contains__'):
            assert self.code in code, 'Unexpected code: %r (expected %r)\n%s' % (self.code, code, self)
        else:
            assert self.code == code, 'Unexpected code: %r (expected %r)\n%s' % (self.code, code, self)

    def assertReason(self, reason):
        assert self.reason == reason, 'Unexpected reason: %r (expected %r)\n%s' % (self.reason, reason, self)

    def assertVersion(self, version):
        assert self.version == version, 'Unexpected version: %r (expected %r)\n%s' % (self.version, version, self)

    def assertHeader(self, header, value):
        real_value = self.headers.get(header, False)
        assert real_value == value, \
            'Unexpected header %r: %r (expected %r)\n%s' % (header, real_value, value, self)

    def assertBody(self, body):
        if isinstance(body, str) and PY3:
            body = body.encode("ascii")
        assert self.body == body, 'Unexpected body: %r (expected %r)\n%s' % (self.body, body, self)

    @classmethod
    def read(cls, fd, code=200, reason='default', version='1.1',
             body=None, chunks=None, content_length=None):
        """
        Read an HTTP response, optionally perform assertions,
        and return the Response object.
        """
        # pylint:disable=too-many-branches
        _status_line, headers = read_headers(fd)
        self = cls(_status_line, headers)
        if code is not None:
            self.assertCode(code)
        if reason == 'default':
            reason = REASONS.get(code)
        if reason is not None:
            self.assertReason(reason)
        if version is not None:
            self.assertVersion(version)
        if self.code == 100:
            return self
        if content_length is not None:
            if isinstance(content_length, int):
                content_length = str(content_length)
            self.assertHeader('Content-Length', content_length)

        if 'chunked' in headers.get('Transfer-Encoding', ''):
            if CONTENT_LENGTH in headers:
                print("WARNING: server used chunked transfer-encoding despite having Content-Length header (libevent 1.x's bug)")
            self.chunks = list(iread_chunks(fd))
            self.body = b''.join(self.chunks)
        elif CONTENT_LENGTH in headers:
            num = int(headers[CONTENT_LENGTH])
            self.body = fd.read(num)
        else:
            self.body = fd.read()

        if body is not None:
            self.assertBody(body)
        if chunks is not None:
            assert chunks == self.chunks, (chunks, self.chunks)
        return self

read_http = Response.read


class TestCase(greentest.TestCase):
    server = None
    validator = staticmethod(validator)
    application = None

    # Bind to default address, which should give us ipv6 (when available)
    # and ipv4. (see self.connect())
    listen_addr = greentest.DEFAULT_BIND_ADDR
    # connect on ipv4, even though we bound to ipv6 too
    # to prove ipv4 works...except on Windows, it apparently doesn't.
    # So use the hostname.
    connect_addr = greentest.DEFAULT_LOCAL_HOST_ADDR

    class handler_class(pywsgi.WSGIHandler):
        ApplicationError = ExpectedAssertionError

    def init_logger(self):
        import logging
        logger = logging.getLogger('gevent.tests.pywsgi')
        logger.setLevel(logging.CRITICAL)
        return logger

    def init_server(self, application):
        logger = self.logger = self.init_logger()
        self.server = pywsgi.WSGIServer(
            (self.listen_addr, 0),
            application,
            log=logger, error_log=logger,
            handler_class=self.handler_class,
        )

    def setUp(self):
        application = self.application
        if self.validator is not None:
            application = self.validator(application)
        self.init_server(application)
        self.server.start()
        while not self.server.server_port:
            print("Waiting on server port")
        self.port = self.server.server_port
        assert self.port
        greentest.TestCase.setUp(self)

    if greentest.CPYTHON and greentest.PY2:
        # Keeping raw sockets alive keeps SSL sockets
        # from being closed too, at least on CPython2, so we
        # need to use weakrefs.

        # In contrast, on PyPy, *only* having a weakref lets the
        # original socket die and leak

        def _close_on_teardown(self, resource):
            self.close_on_teardown.append(weakref.ref(resource))
            return resource

        def _tearDownCloseOnTearDown(self):
            self.close_on_teardown = [r() for r in self.close_on_teardown if r() is not None]
            super(TestCase, self)._tearDownCloseOnTearDown()

    def tearDown(self):
        greentest.TestCase.tearDown(self)
        if self.server is not None:
            with gevent.Timeout.start_new(0.5):
                self.server.stop()
        self.server = None
        if greentest.PYPY:
            import gc
            gc.collect()
            gc.collect()


    @contextmanager
    def connect(self):
        conn = socket.create_connection((self.connect_addr, self.port))
        result = conn
        if PY3:
            conn_makefile = conn.makefile

            def makefile(*args, **kwargs):
                if 'bufsize' in kwargs:
                    kwargs['buffering'] = kwargs.pop('bufsize')

                if 'mode' in kwargs:
                    return conn_makefile(*args, **kwargs)

                # Under Python3, you can't read and write to the same
                # makefile() opened in (default) r, and r+ is not allowed
                kwargs['mode'] = 'rwb'
                rconn = conn_makefile(*args, **kwargs)
                _rconn_write = rconn.write

                def write(data):
                    if isinstance(data, str):
                        data = data.encode('ascii')
                    return _rconn_write(data)
                rconn.write = write
                self._close_on_teardown(rconn)
                return rconn

            class proxy(object):
                def __getattribute__(self, name):
                    if name == 'makefile':
                        return makefile
                    return getattr(conn, name)
            result = proxy()
        try:
            yield result
        finally:
            result.close()

    @contextmanager
    def makefile(self):
        with self.connect() as sock:
            try:
                result = sock.makefile(bufsize=1) # pylint:disable=unexpected-keyword-arg
                yield result
            finally:
                result.close()

    def urlopen(self, *args, **kwargs):
        with self.connect() as sock:
            with sock.makefile(bufsize=1) as fd: # pylint:disable=unexpected-keyword-arg
                fd.write('GET / HTTP/1.1\r\nHost: localhost\r\n\r\n')
                return read_http(fd, *args, **kwargs)

    HTTP_CLIENT_VERSION = '1.1'
    DEFAULT_EXTRA_CLIENT_HEADERS = {}

    def format_request(self, method='GET', path='/', **headers):
        def_headers = self.DEFAULT_EXTRA_CLIENT_HEADERS.copy()
        def_headers.update(headers)
        headers = def_headers

        headers = '\r\n'.join('%s: %s' % item for item in headers.items())
        headers = headers + '\r\n' if headers else headers
        result = (
            '%(method)s %(path)s HTTP/%(http_ver)s\r\n'
            'Host: localhost\r\n'
            '%(headers)s'
            '\r\n'
        )
        result = result % dict(
            method=method,
            path=path,
            http_ver=self.HTTP_CLIENT_VERSION,
            headers=headers
        )
        return result


class CommonTestMixin(object):
    PIPELINE_NOT_SUPPORTED_EXS = ()
    EXPECT_CLOSE = False
    EXPECT_KEEPALIVE = False

    def test_basic(self):
        with self.makefile() as fd:
            fd.write(self.format_request())
            response = read_http(fd, body='hello world')
            if response.headers.get('Connection') == 'close':
                self.assertTrue(self.EXPECT_CLOSE, "Server closed connection, not expecting that")
                return response, None

            self.assertFalse(self.EXPECT_CLOSE)
            if self.EXPECT_KEEPALIVE:
                response.assertHeader('Connection', 'keep-alive')
            fd.write(self.format_request(path='/notexist'))
            dne_response = read_http(fd, code=404, reason='Not Found', body='not found')
            fd.write(self.format_request())
            response = read_http(fd, body='hello world')
            return response, dne_response



    def test_pipeline(self):
        exception = AssertionError('HTTP pipelining not supported; the second request is thrown away')
        with self.makefile() as fd:
            fd.write(self.format_request() + self.format_request(path='/notexist'))
            read_http(fd, body='hello world')

            try:
                timeout = gevent.Timeout.start_new(0.5, exception=exception)
                try:
                    read_http(fd, code=404, reason='Not Found', body='not found')
                finally:
                    timeout.close()
            except self.PIPELINE_NOT_SUPPORTED_EXS:
                pass
            except AssertionError as ex:
                if ex is not exception:
                    raise

    def test_connection_close(self):
        with self.makefile() as fd:
            fd.write(self.format_request())
            response = read_http(fd)
            if response.headers.get('Connection') == 'close':
                self.assertTrue(self.EXPECT_CLOSE, "Server closed connection, not expecting that")
                return
            self.assertFalse(self.EXPECT_CLOSE)
            if self.EXPECT_KEEPALIVE:
                response.assertHeader('Connection', 'keep-alive')

            fd.write(self.format_request(Connection='close'))
            read_http(fd)
            fd.write(self.format_request())
            # This may either raise, or it may return an empty response,
            # depend on timing and the Python version.
            try:
                result = fd.readline()
            except socket.error as ex:
                if ex.args[0] not in CONN_ABORTED_ERRORS:
                    raise
            else:
                self.assertFalse(
                    result,
                    'The remote side is expected to close the connection, but it sent %r'
                    % (result,))

    @unittest.skip("Not sure")
    def test_006_reject_long_urls(self):
        path_parts = []
        for _ in range(3000):
            path_parts.append('path')
        path = '/'.join(path_parts)

        with self.makefile() as fd:
            request = 'GET /%s HTTP/1.0\r\nHost: localhost\r\n\r\n' % path
            fd.write(request)
            result = fd.readline()
            status = result.split(' ')[1]
            self.assertEqual(status, '414')


class TestNoChunks(CommonTestMixin, TestCase):
    # when returning a list of strings a shortcut is employed by the server:
    # it calculates the content-length and joins all the chunks before sending
    validator = None
    last_environ = None

    def _check_environ(self, input_terminated=True):
        if input_terminated:
            self.assertTrue(self.last_environ.get('wsgi.input_terminated'))
        else:
            self.assertFalse(self.last_environ['wsgi.input_terminated'])

    def application(self, env, start_response):
        self.last_environ = env
        path = env['PATH_INFO']
        if path == '/':
            start_response('200 OK', [('Content-Type', 'text/plain')])
            return [b'hello ', b'world']
        if path == '/websocket':
            write = start_response('101 Switching Protocols',
                                   [('Content-Type', 'text/plain'),
                                    # Con:close is to make our simple client
                                    # happy; otherwise it wants to read data from the
                                    # body thot's being kept open.
                                    ('Connection', 'close')])
            write(b'') # Trigger finalizing the headers now.
            return [b'upgrading to', b'websocket']
        start_response('404 Not Found', [('Content-Type', 'text/plain')])
        return [b'not ', b'found']

    def test_basic(self):
        response, dne_response = super(TestNoChunks, self).test_basic()
        self._check_environ()
        self.assertFalse(response.chunks)
        response.assertHeader('Content-Length', '11')
        if dne_response is not None:
            self.assertFalse(dne_response.chunks)
            dne_response.assertHeader('Content-Length', '9')

    def test_dne(self):
        with self.makefile() as fd:
            fd.write(self.format_request(path='/notexist'))
            response = read_http(fd, code=404, reason='Not Found', body='not found')
        self.assertFalse(response.chunks)
        self._check_environ()
        response.assertHeader('Content-Length', '9')

class TestConnectionUpgrades(TestNoChunks):

    def test_connection_upgrade(self):
        with self.makefile() as fd:
            fd.write(self.format_request(path='/websocket', Connection='upgrade'))
            response = read_http(fd, code=101)

        self._check_environ(input_terminated=False)
        self.assertFalse(response.chunks)

    def test_upgrade_websocket(self):
        with self.makefile() as fd:
            fd.write(self.format_request(path='/websocket', Upgrade='websocket'))
            response = read_http(fd, code=101)

        self._check_environ(input_terminated=False)
        self.assertFalse(response.chunks)


class TestNoChunks10(TestNoChunks):
    HTTP_CLIENT_VERSION = '1.0'
    PIPELINE_NOT_SUPPORTED_EXS = (ConnectionClosed,)
    EXPECT_CLOSE = True

class TestNoChunks10KeepAlive(TestNoChunks10):
    DEFAULT_EXTRA_CLIENT_HEADERS = {
        'Connection': 'keep-alive',
    }
    EXPECT_CLOSE = False
    EXPECT_KEEPALIVE = True


class TestExplicitContentLength(TestNoChunks): # pylint:disable=too-many-ancestors
    # when returning a list of strings a shortcut is employed by the
    # server - it caculates the content-length

    def application(self, env, start_response):
        self.last_environ = env
        self.assertTrue(env.get('wsgi.input_terminated'))
        path = env['PATH_INFO']
        if path == '/':
            start_response('200 OK', [('Content-Type', 'text/plain'), ('Content-Length', '11')])
            return [b'hello ', b'world']

        start_response('404 Not Found', [('Content-Type', 'text/plain'), ('Content-Length', '9')])
        return [b'not ', b'found']


class TestYield(CommonTestMixin, TestCase):

    @staticmethod
    def application(env, start_response):
        path = env['PATH_INFO']
        if path == '/':
            start_response('200 OK', [('Content-Type', 'text/plain')])
            yield b"hello world"
        else:
            start_response('404 Not Found', [('Content-Type', 'text/plain')])
            yield b"not found"


class TestBytearray(CommonTestMixin, TestCase):

    validator = None

    @staticmethod
    def application(env, start_response):
        path = env['PATH_INFO']
        if path == '/':
            start_response('200 OK', [('Content-Type', 'text/plain')])
            return [bytearray(b"hello "), bytearray(b"world")]
        start_response('404 Not Found', [('Content-Type', 'text/plain')])
        return [bytearray(b"not found")]


class TestMultiLineHeader(TestCase):
    @staticmethod
    def application(env, start_response):
        assert "test.submit" in env["CONTENT_TYPE"]
        start_response('200 OK', [('Content-Type', 'text/plain')])
        return [b"ok"]

    def test_multiline_116(self):
        """issue #116"""
        request = '\r\n'.join((
            'POST / HTTP/1.0',
            'Host: localhost',
            'Content-Type: multipart/related; boundary="====XXXX====";',
            ' type="text/xml";start="test.submit"',
            'Content-Length: 0',
            '', ''))
        with self.makefile() as fd:
            fd.write(request)
            read_http(fd)


class TestGetArg(TestCase):

    @staticmethod
    def application(env, start_response):
        body = env['wsgi.input'].read(3)
        if PY3:
            body = body.decode('ascii')
        a = parse_qs(body).get('a', [1])[0]
        start_response('200 OK', [('Content-Type', 'text/plain')])
        return [('a is %s, body is %s' % (a, body)).encode('ascii')]

    def test_007_get_arg(self):
        # define a new handler that does a get_arg as well as a read_body

        request = '\r\n'.join((
            'POST / HTTP/1.0',
            'Host: localhost',
            'Content-Length: 3',
            '',
            'a=a'))
        with self.makefile() as fd:
            fd.write(request)

            # send some junk after the actual request
            fd.write('01234567890123456789')
            read_http(fd, body='a is a, body is a=a')


class TestCloseIter(TestCase):

    # The *Validator* closes the iterators!
    validator = None

    def application(self, env, start_response):
        start_response('200 OK', [('Content-Type', 'text/plain')])
        return self

    def __iter__(self):
        yield bytearray(b"Hello World")
        yield b"!"

    closed = False

    def close(self):
        self.closed += 1

    def test_close_is_called(self):
        self.closed = False
        with self.makefile() as fd:
            fd.write('GET / HTTP/1.1\r\nHost: localhost\r\n\r\n')
            read_http(fd, body=b"Hello World!", chunks=[b'Hello World', b'!'])
        # We got closed exactly once.
        self.assertEqual(self.closed, 1)

class TestChunkedApp(TestCase):

    chunks = [b'this', b'is', b'chunked']

    def body(self):
        return b''.join(self.chunks)

    def application(self, env, start_response):
        self.assertTrue(env.get('wsgi.input_terminated'))
        start_response('200 OK', [('Content-Type', 'text/plain')])
        for chunk in self.chunks:
            yield chunk

    def test_chunked_response(self):
        with self.makefile() as fd:
            fd.write('GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')
            response = read_http(fd, body=self.body(), chunks=None)

        response.assertHeader('Transfer-Encoding', 'chunked')
        self.assertEqual(response.chunks, self.chunks)

    def test_no_chunked_http_1_0(self):
        with self.makefile() as fd:
            fd.write('GET / HTTP/1.0\r\nHost: localhost\r\nConnection: close\r\n\r\n')
            response = read_http(fd)
        self.assertEqual(response.body, self.body())
        self.assertEqual(response.headers.get('Transfer-Encoding'), None)
        content_length = response.headers.get('Content-Length')
        if content_length is not None:
            self.assertEqual(content_length, str(len(self.body())))


class TestBigChunks(TestChunkedApp):
    chunks = [b'a' * 8192] * 3


class TestNegativeRead(TestCase):

    def application(self, env, start_response):
        self.assertTrue(env.get('wsgi.input_terminated'))
        start_response('200 OK', [('Content-Type', 'text/plain')])
        if env['PATH_INFO'] == '/read':
            data = env['wsgi.input'].read(-1)
            return [data]

    def test_negative_chunked_read(self):
        data = (b'POST /read HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n'
                b'Transfer-Encoding: chunked\r\n\r\n'
                b'2\r\noh\r\n4\r\n hai\r\n0\r\n\r\n')
        with self.makefile() as fd:
            fd.write(data)
            read_http(fd, body='oh hai')

    def test_negative_nonchunked_read(self):
        data = (b'POST /read HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n'
                b'Content-Length: 6\r\n\r\n'
                b'oh hai')
        with self.makefile() as fd:
            fd.write(data)
            read_http(fd, body='oh hai')


class TestNegativeReadline(TestCase):
    validator = None

    @staticmethod
    def application(env, start_response):
        start_response('200 OK', [('Content-Type', 'text/plain')])
        if env['PATH_INFO'] == '/readline':
            data = env['wsgi.input'].readline(-1)
            return [data]

    def test_negative_chunked_readline(self):
        data = (b'POST /readline HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n'
                b'Transfer-Encoding: chunked\r\n\r\n'
                b'2\r\noh\r\n4\r\n hai\r\n0\r\n\r\n')
        with self.makefile() as fd:
            fd.write(data)
            read_http(fd, body='oh hai')

    def test_negative_nonchunked_readline(self):
        data = (b'POST /readline HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n'
                b'Content-Length: 6\r\n\r\n'
                b'oh hai')
        with self.makefile() as fd:
            fd.write(data)
            read_http(fd, body='oh hai')


class TestChunkedPost(TestCase):

    calls = 0

    def setUp(self):
        super().setUp()
        self.calls = 0

    def application(self, env, start_response):
        self.calls += 1
        self.assertTrue(env.get('wsgi.input_terminated'))
        start_response('200 OK', [('Content-Type', 'text/plain')])
        if env['PATH_INFO'] == '/a':
            data = env['wsgi.input'].read(6)
            return [data]

        if env['PATH_INFO'] == '/b':
            lines = list(iter(lambda: env['wsgi.input'].read(6), b''))
            return lines

        if env['PATH_INFO'] == '/c':
            return list(iter(lambda: env['wsgi.input'].read(1), b''))

        return [b'We should not get here', env['PATH_INFO'].encode('ascii')]

    def test_014_chunked_post(self):
        data = (b'POST /a HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n'
                b'Transfer-Encoding: chunked\r\n\r\n'
                b'2\r\noh\r\n4\r\n hai\r\n0\r\n\r\n')
        with self.makefile() as fd:
            fd.write(data)
            read_http(fd, body='oh hai')
        # self.close_opened() # XXX: Why?

        with self.makefile() as fd:
            fd.write(data.replace(b'/a', b'/b'))
            read_http(fd, body='oh hai')

        with self.makefile() as fd:
            fd.write(data.replace(b'/a', b'/c'))
            read_http(fd, body='oh hai')

    def test_229_incorrect_chunk_no_newline(self):
        # Giving both a Content-Length and a Transfer-Encoding,
        # TE is preferred. But if the chunking is bad from the client,
        # missing its terminating newline,
        # the server doesn't hang
        data = (b'POST /a HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n'
                b'Content-Length: 12\r\n'
                b'Transfer-Encoding: chunked\r\n\r\n'
                b'{"hi": "ho"}')
        with self.makefile() as fd:
            fd.write(data)
            read_http(fd, code=400)

    def test_229_incorrect_chunk_non_hex(self):
        # Giving both a Content-Length and a Transfer-Encoding,
        # TE is preferred. But if the chunking is bad from the client,
        # the server doesn't hang
        data = (b'POST /a HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n'
                b'Content-Length: 12\r\n'
                b'Transfer-Encoding: chunked\r\n\r\n'
                b'{"hi": "ho"}\r\n')
        with self.makefile() as fd:
            fd.write(data)
            read_http(fd, code=400)

    def test_229_correct_chunk_quoted_ext(self):
        data = (b'POST /a HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n'
                b'Transfer-Encoding: chunked\r\n\r\n'
                b'2;token="oh hi"\r\noh\r\n4\r\n hai\r\n0\r\n\r\n')
        with self.makefile() as fd:
            fd.write(data)
            read_http(fd, body='oh hai')

    def test_229_correct_chunk_token_ext(self):
        data = (b'POST /a HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n'
                b'Transfer-Encoding: chunked\r\n\r\n'
                b'2;token=oh_hi\r\noh\r\n4\r\n hai\r\n0\r\n\r\n')
        with self.makefile() as fd:
            fd.write(data)
            read_http(fd, body='oh hai')

    def test_229_incorrect_chunk_token_ext_too_long(self):
        data = (b'POST /a HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n'
                b'Transfer-Encoding: chunked\r\n\r\n'
                b'2;token=oh_hi\r\noh\r\n4\r\n hai\r\n0\r\n\r\n')
        data = data.replace(b'oh_hi', b'_oh_hi' * 4000)
        with self.makefile() as fd:
            fd.write(data)
            read_http(fd, code=400)

    # XXX: Not sure which one, but one (or more) of these is leading to a
    # test timeout on Windows. Figure out what/why and solve.

    @greentest.skipOnWindows('Maybe hangs')
    def test_trailers_keepalive_ignored(self):
        # Trailers after a chunk are ignored.
        data1 = (
            b'POST /a HTTP/1.1\r\n'
            b'Host: localhost\r\n'
            b'Connection: keep-alive\r\n'
            b'Transfer-Encoding: chunked\r\n'
            b'\r\n'
            b'2\r\noh\r\n'
            b'4\r\n hai\r\n'
            b'0\r\n' # last-chunk
            # Normally the final CRLF would go here, but if you put in a
            # trailer, it doesn't.
            b'trailer1: value1\r\n'
            b'trailer2: value2\r\n'
            b'\r\n' # Really terminate the chunk.
        )
        data2 = (
            b'POST /a HTTP/1.1\r\n'
            b'Host: localhost\r\n'
            b'Connection: close\r\n'
            b'Transfer-Encoding: chunked\r\n'
            b'\r\n'
            b'2\r\noh\r\n'
            b'4\r\n bye\r\n'
            b'0\r\n' # last-chunk
        )
        with self.makefile() as fd:
            fd.write(data1)
            read_http(fd, body='oh hai')
            fd.write(data2)
            read_http(fd, body='oh bye')

        self.assertEqual(self.calls, 2)

    @greentest.skipOnWindows('Maybe hangs')
    def test_trailers_close_ignored(self):
        data = (
            b'POST /a HTTP/1.1\r\n'
            b'Host: localhost\r\n'
            b'Connection: close\r\n'
            b'Transfer-Encoding: chunked\r\n'
            b'\r\n'
            b'2\r\noh\r\n'
            b'4\r\n hai\r\n'
            b'0\r\n' # last-chunk
            # Normally the final CRLF would go here, but if you put in a
            # trailer, it doesn't.
            # b'\r\n'
            b'GETpath2a:123 HTTP/1.1\r\n'
            b'Host: a.com\r\n'
            b'Connection: close\r\n'
            b'\r\n'
        )
        with self.makefile() as fd:
            fd.write(data)
            read_http(fd, body='oh hai')
            with self.assertRaises(ConnectionClosed):
                read_http(fd)

    @greentest.skipOnWindows('Maybe hangs')
    def test_trailers_too_long(self):
        # Trailers after a chunk are ignored.
        data = (
            b'POST /a HTTP/1.1\r\n'
            b'Host: localhost\r\n'
            b'Connection: keep-alive\r\n'
            b'Transfer-Encoding: chunked\r\n'
            b'\r\n'
            b'2\r\noh\r\n'
            b'4\r\n hai\r\n'
            b'0\r\n' # last-chunk
            # Normally the final CRLF would go here, but if you put in a
            # trailer, it doesn't.
            b'trailer2: value2' # note lack of \r\n
        )
        data += b't' * pywsgi.MAX_REQUEST_LINE
        # No termination, because we detect the trailer as being too
        # long and abort the connection.
        with self.makefile() as fd:
            fd.write(data)
            read_http(fd, body='oh hai')
            with self.assertRaises(ConnectionClosed):
                read_http(fd, body='oh bye')

    @greentest.skipOnWindows('Maybe hangs')
    def test_trailers_request_smuggling_missing_last_chunk_keep_alive(self):
        # When something that looks like a request line comes in the trailer
        # as the first line, immediately after an invalid last chunk.
        # We detect this and abort the connection, because the
        # whitespace in the GET line isn't a legal part of a trailer.
        # If we didn't abort the connection, then, because we specified
        # keep-alive, the server would be hanging around waiting for more input.
        data = (
            b'POST /a HTTP/1.1\r\n'
            b'Host: localhost\r\n'
            b'Connection: keep-alive\r\n'
            b'Transfer-Encoding: chunked\r\n'
            b'\r\n'
            b'2\r\noh\r\n'
            b'4\r\n hai\r\n'
            b'0' # last-chunk, but missing the \r\n
            # Normally the final CRLF would go here, but if you put in a
            # trailer, it doesn't.
            # b'\r\n'
            b'GET /path2?a=:123 HTTP/1.1\r\n'
            b'Host: a.com\r\n'
            b'Connection: close\r\n'
            b'\r\n'
        )
        with self.makefile() as fd:
            fd.write(data)
            read_http(fd, body='oh hai')
            with self.assertRaises(ConnectionClosed):
                read_http(fd)

        self.assertEqual(self.calls, 1)

    @greentest.skipOnWindows('Maybe hangs')
    def test_trailers_request_smuggling_header_first(self):
        # When something that looks like a header comes in the first line.
        data = (
            b'POST /a HTTP/1.1\r\n'
            b'Host: localhost\r\n'
            b'Connection: keep-alive\r\n'
            b'Transfer-Encoding: chunked\r\n'
            b'\r\n'
            b'2\r\noh\r\n'
            b'4\r\n hai\r\n'
            b'0\r\n' # last-chunk, but only one CRLF
            b'Header: value\r\n'
            b'GET /path2?a=:123 HTTP/1.1\r\n'
            b'Host: a.com\r\n'
            b'Connection: close\r\n'
            b'\r\n'
        )
        with self.makefile() as fd:
            fd.write(data)
            read_http(fd, body='oh hai')
            with self.assertRaises(ConnectionClosed):
                read_http(fd, code=400)

        self.assertEqual(self.calls, 1)

    @greentest.skipOnWindows('Maybe hangs')
    def test_trailers_request_smuggling_request_terminates_then_header(self):
        data = (
            b'POST /a HTTP/1.1\r\n'
            b'Host: localhost\r\n'
            b'Connection: keep-alive\r\n'
            b'Transfer-Encoding: chunked\r\n'
            b'\r\n'
            b'2\r\noh\r\n'
            b'4\r\n hai\r\n'
            b'0\r\n' # last-chunk
            b'\r\n'
            b'Header: value'
            b'GET /path2?a=:123 HTTP/1.1\r\n'
            b'Host: a.com\r\n'
            b'Connection: close\r\n'
            b'\r\n'
        )
        with self.makefile() as fd:
            fd.write(data)
            read_http(fd, body='oh hai')
            read_http(fd, code=400)

        self.assertEqual(self.calls, 1)


class TestUseWrite(TestCase):

    body = b'abcde'
    end = b'end'
    content_length = str(len(body + end))

    def application(self, env, start_response):
        if env['PATH_INFO'] == '/explicit-content-length':
            write = start_response('200 OK', [('Content-Type', 'text/plain'),
                                              ('Content-Length', self.content_length)])
            write(self.body)
        elif env['PATH_INFO'] == '/no-content-length':
            write = start_response('200 OK', [('Content-Type', 'text/plain')])
            write(self.body)
        elif env['PATH_INFO'] == '/no-content-length-twice':
            write = start_response('200 OK', [('Content-Type', 'text/plain')])
            write(self.body)
            write(self.body)
        else:
            # pylint:disable-next=broad-exception-raised
            raise Exception('Invalid url')
        return [self.end]

    def test_explicit_content_length(self):
        with self.makefile() as fd:
            fd.write('GET /explicit-content-length HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')
            response = read_http(fd, body=self.body + self.end)
        response.assertHeader('Content-Length', self.content_length)
        response.assertHeader('Transfer-Encoding', False)

    def test_no_content_length(self):
        with self.makefile() as fd:
            fd.write('GET /no-content-length HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')
            response = read_http(fd, body=self.body + self.end)

        response.assertHeader('Content-Length', False)
        response.assertHeader('Transfer-Encoding', 'chunked')

    def test_no_content_length_twice(self):
        with self.makefile() as fd:
            fd.write('GET /no-content-length-twice HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')
            response = read_http(fd, body=self.body + self.body + self.end)

        response.assertHeader('Content-Length', False)
        response.assertHeader('Transfer-Encoding', 'chunked')
        self.assertEqual(response.chunks, [self.body, self.body, self.end])


class HttpsTestCase(TestCase):

    certfile = os.path.join(os.path.dirname(__file__), 'test_server.crt')
    keyfile = os.path.join(os.path.dirname(__file__), 'test_server.key')

    def init_server(self, application):
        self.server = pywsgi.WSGIServer((self.listen_addr, 0), application,
                                        certfile=self.certfile, keyfile=self.keyfile)

    def urlopen(self, method='GET', post_body=None, **kwargs): # pylint:disable=arguments-differ
        import ssl
        with self.connect() as raw_sock:
            with ssl.wrap_socket(raw_sock) as sock: # pylint:disable=deprecated-method
                with sock.makefile(bufsize=1) as fd: # pylint:disable=unexpected-keyword-arg
                    fd.write('%s / HTTP/1.1\r\nHost: localhost\r\n' % method)
                    if post_body is not None:
                        fd.write('Content-Length: %s\r\n\r\n' % len(post_body))
                        fd.write(post_body)
                        if kwargs.get('body') is None:
                            kwargs['body'] = post_body
                    else:
                        fd.write('\r\n')
                    fd.flush()

                    return read_http(fd, **kwargs)

    def application(self, environ, start_response):
        assert environ['wsgi.url_scheme'] == 'https', environ['wsgi.url_scheme']
        start_response('200 OK', [('Content-Type', 'text/plain')])
        return [environ['wsgi.input'].read(10)]


import gevent.ssl
HAVE_SSLCONTEXT = getattr(gevent.ssl, 'create_default_context')
if HAVE_SSLCONTEXT:

    class HttpsSslContextTestCase(HttpsTestCase):
        def init_server(self, application):
            # On 2.7, our certs don't line up with hostname.
            # If we just use create_default_context as-is, we get
            # `ValueError: check_hostname requires server_hostname`.
            # If we set check_hostname to False, we get
            # `SSLError: [SSL: PEER_DID_NOT_RETURN_A_CERTIFICATE] peer did not return a certificate`
            # (Neither of which happens in Python 3.) But the unverified context
            # works both places. See also test___example_servers.py
            from gevent.ssl import _create_unverified_context # pylint:disable=no-name-in-module
            context = _create_unverified_context()
            context.load_cert_chain(certfile=self.certfile, keyfile=self.keyfile)
            self.server = pywsgi.WSGIServer((self.listen_addr, 0),
                                            application, ssl_context=context)

class TestHttps(HttpsTestCase):

    if hasattr(socket, 'ssl'):

        def test_012_ssl_server(self):
            result = self.urlopen(method="POST", post_body='abc')
            self.assertEqual(result.body, 'abc')

        def test_013_empty_return(self):
            result = self.urlopen()
            self.assertEqual(result.body, '')

if HAVE_SSLCONTEXT:
    class TestHttpsWithContext(HttpsSslContextTestCase, TestHttps): # pylint:disable=too-many-ancestors
        pass

class TestInternational(TestCase):
    validator = None  # wsgiref.validate.IteratorWrapper([]) does not have __len__

    def application(self, environ, start_response):
        path_bytes = b'/\xd0\xbf\xd1\x80\xd0\xb8\xd0\xb2\xd0\xb5\xd1\x82'
        if PY3:
            # Under PY3, the escapes were decoded as latin-1
            path_bytes = path_bytes.decode('latin-1')

        self.assertEqual(environ['PATH_INFO'], path_bytes)
        self.assertEqual(environ['QUERY_STRING'], '%D0%B2%D0%BE%D0%BF%D1%80%D0%BE%D1%81=%D0%BE%D1%82%D0%B2%D0%B5%D1%82')
        start_response("200 PASSED", [('Content-Type', 'text/plain')])
        return []

    def test(self):
        with self.connect() as sock:
            sock.sendall(
                b'''GET /%D0%BF%D1%80%D0%B8%D0%B2%D0%B5%D1%82?%D0%B2%D0%BE%D0%BF%D1%80%D0%BE%D1%81=%D0%BE%D1%82%D0%B2%D0%B5%D1%82 HTTP/1.1
Host: localhost
Connection: close

'''.replace(b'\n', b'\r\n'))
            with sock.makefile() as fd:
                read_http(fd, reason='PASSED', chunks=False, body='', content_length=0)


class TestNonLatin1HeaderFromApplication(TestCase):
    error_fatal = False # Allow sending the exception response, don't kill the greenlet

    validator = None # Don't validate the application, it's deliberately bad
    header = b'\xe1\xbd\x8a3' # bomb in utf-8 bytes
    should_error = PY3 # non-native string under Py3

    def setUp(self):
        super(TestNonLatin1HeaderFromApplication, self).setUp()
        self.errors = []

    def tearDown(self):
        self.errors = []
        super(TestNonLatin1HeaderFromApplication, self).tearDown()

    def application(self, environ, start_response):
        # We return a header that cannot be encoded in latin-1
        try:
            start_response("200 PASSED",
                           [('Content-Type', 'text/plain'),
                            ('Custom-Header', self.header)])
        except:
            self.errors.append(sys.exc_info()[:2])
            raise
        return []

    def test(self):
        with self.connect() as sock:
            self.expect_one_error()
            sock.sendall(b'''GET / HTTP/1.1\r\n\r\n''')
            with sock.makefile() as fd:
                if self.should_error:
                    read_http(fd, code=500, reason='Internal Server Error')
                    self.assert_error(where_type=pywsgi.SecureEnviron)
                    self.assertEqual(len(self.errors), 1)
                    _, v = self.errors[0]
                    self.assertIsInstance(v, UnicodeError)
                else:
                    read_http(fd, code=200, reason='PASSED')
                    self.assertEqual(len(self.errors), 0)


class TestNonLatin1UnicodeHeaderFromApplication(TestNonLatin1HeaderFromApplication):
    # Flip-flop of the superclass: Python 3 native string, Python 2 unicode object
    header = u"\u1f4a3" # bomb in unicode
    # Error both on py3 and py2. On py2, non-native string. On py3, native string
    # that cannot be encoded to latin-1
    should_error = True


class TestInputReadline(TestCase):
    # this test relies on the fact that readline() returns '' after it reached EOF
    # this behaviour is not mandated by WSGI spec, it's just happens that gevent.wsgi behaves like that
    # as such, this may change in the future

    validator = None

    def application(self, environ, start_response):
        input = environ['wsgi.input']
        lines = []
        while True:
            line = input.readline()
            if not line:
                break
            line = line.decode('ascii') if PY3 else line
            lines.append(repr(line) + ' ')
        start_response('200 hello', [])
        return [l.encode('ascii') for l in lines] if PY3 else lines

    def test(self):
        with self.makefile() as fd:
            content = 'hello\n\nworld\n123'
            fd.write('POST / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n'
                     'Content-Length: %s\r\n\r\n%s' % (len(content), content))
            fd.flush()
            read_http(fd, reason='hello', body="'hello\\n' '\\n' 'world\\n' '123' ")


class TestInputIter(TestInputReadline):

    def application(self, environ, start_response):
        input = environ['wsgi.input']
        lines = []
        for line in input:
            if not line:
                break
            line = line.decode('ascii') if PY3 else line
            lines.append(repr(line) + ' ')
        start_response('200 hello', [])
        return [l.encode('ascii') for l in lines] if PY3 else lines


class TestInputReadlines(TestInputReadline):

    def application(self, environ, start_response):
        input = environ['wsgi.input']
        lines = [l.decode('ascii') if PY3 else l for l in input.readlines()]
        lines = [repr(line) + ' ' for line in lines]
        start_response('200 hello', [])
        return [l.encode('ascii') for l in lines] if PY3 else lines


class TestInputN(TestCase):
    # testing for this:
    # File "/home/denis/work/gevent/gevent/pywsgi.py", line 70, in _do_read
    #   if length and length > self.content_length - self.position:
    # TypeError: unsupported operand type(s) for -: 'NoneType' and 'int'

    validator = None

    def application(self, environ, start_response):
        environ['wsgi.input'].read(5)
        start_response('200 OK', [])
        return []

    def test(self):
        self.urlopen()


class TestErrorInApplication(TestCase):

    error = object()
    error_fatal = False

    def application(self, env, start_response):
        self.error = greentest.ExpectedException('TestError.application')
        raise self.error

    def test(self):
        self.expect_one_error()
        self.urlopen(code=500)
        self.assert_error(greentest.ExpectedException, self.error)


class TestError_after_start_response(TestErrorInApplication):

    def application(self, env, start_response):
        self.error = greentest.ExpectedException('TestError_after_start_response.application')
        start_response('200 OK', [('Content-Type', 'text/plain')])
        raise self.error


class TestEmptyYield(TestCase):

    @staticmethod
    def application(env, start_response):
        start_response('200 OK', [('Content-Type', 'text/plain')])
        yield b""
        yield b""

    def test_err(self):
        chunks = []

        with self.makefile() as fd:
            fd.write('GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')

            read_http(fd, body='', chunks=chunks)

            garbage = fd.read()
        self.assertEqual(garbage, b"", "got garbage: %r" % garbage)


class TestFirstEmptyYield(TestCase):

    @staticmethod
    def application(env, start_response):
        start_response('200 OK', [('Content-Type', 'text/plain')])
        yield b""
        yield b"hello"

    def test_err(self):
        chunks = [b'hello']

        with self.makefile() as fd:
            fd.write('GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')

            read_http(fd, body='hello', chunks=chunks)

            garbage = fd.read()
        self.assertEqual(garbage, b"")


class TestEmptyYield304(TestCase):

    @staticmethod
    def application(env, start_response):
        start_response('304 Not modified', [])
        yield b""
        yield b""

    def test_err(self):
        with self.makefile() as fd:
            fd.write('GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')
            read_http(fd, code=304, body='', chunks=False)
            garbage = fd.read()
        self.assertEqual(garbage, b"")


class TestContentLength304(TestCase):
    validator = None

    def application(self, env, start_response):
        try:
            start_response('304 Not modified', [('Content-Length', '100')])
        except AssertionError as ex:
            start_response('200 Raised', [])
            return ex.args
        raise AssertionError('start_response did not fail but it should')

    def test_err(self):
        body = "Invalid Content-Length for 304 response: '100' (must be absent or zero)"
        with self.makefile() as fd:
            fd.write('GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')

            read_http(fd, code=200, reason='Raised', body=body, chunks=False)
            garbage = fd.read()
        self.assertEqual(garbage, b"")


class TestBody304(TestCase):
    validator = None

    def application(self, env, start_response):
        start_response('304 Not modified', [])
        return [b'body']

    def test_err(self):
        with self.makefile() as fd:
            fd.write('GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')
            with self.assertRaises(AssertionError) as exc:
                read_http(fd)
            ex = exc.exception
            self.assertEqual(str(ex), 'The 304 response must have no body')


class TestWrite304(TestCase):
    validator = None
    error_raised = None

    def application(self, env, start_response):
        write = start_response('304 Not modified', [])
        self.error_raised = False
        try:
            write('body')
        except AssertionError as ex:
            self.error_raised = True
            raise ExpectedAssertionError(*ex.args)

    def test_err(self):
        with self.makefile() as fd:
            fd.write(b'GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')
            with self.assertRaises(AssertionError) as exc:
                read_http(fd)
            ex = exc.exception

        self.assertEqual(str(ex), 'The 304 response must have no body')
        self.assertTrue(self.error_raised, 'write() must raise')


class TestEmptyWrite(TestEmptyYield):

    @staticmethod
    def application(env, start_response):
        write = start_response('200 OK', [('Content-Type', 'text/plain')])
        write(b"")
        write(b"")
        return []


class BadRequestTests(TestCase):
    validator = None
    # pywsgi checks content-length, but wsgi does not
    content_length = None

    assert TestCase.handler_class._print_unexpected_exc

    class handler_class(TestCase.handler_class):
        def _print_unexpected_exc(self):
            raise AssertionError("Should not print a traceback")

    def application(self, env, start_response):
        self.assertEqual(env['CONTENT_LENGTH'], self.content_length)
        start_response('200 OK', [('Content-Type', 'text/plain')])
        return [b'hello']

    def test_negative_content_length(self):
        self.content_length = '-100'
        with self.makefile() as fd:
            fd.write('GET / HTTP/1.1\r\nHost: localhost\r\nContent-Length: %s\r\n\r\n' % self.content_length)
            read_http(fd, code=(200, 400))

    def test_illegal_content_length(self):
        self.content_length = 'abc'
        with self.makefile() as fd:
            fd.write('GET / HTTP/1.1\r\nHost: localhost\r\nContent-Length: %s\r\n\r\n' % self.content_length)
            read_http(fd, code=(200, 400))

    def test_bad_request_line_with_percent(self):
        # If the request is invalid and contains Python formatting characters (%)
        # we don't fail to log the error and we do generate a 400.
        # https://github.com/gevent/gevent/issues/1708
        bad_request = 'GET / HTTP %\r\n'
        with self.makefile() as fd:
            fd.write(bad_request)
            read_http(fd, code=400)


class ChunkedInputTests(TestCase):
    dirt = ""
    validator = None

    def application(self, env, start_response):
        input = env['wsgi.input']
        response = []

        pi = env["PATH_INFO"]

        if pi == "/short-read":
            d = input.read(10)
            response = [d]
        elif pi == "/lines":
            for x in input:
                response.append(x)
        elif pi == "/ping":
            input.read(1)
            response.append(b"pong")
        else:
            raise RuntimeError("bad path")

        start_response('200 OK', [('Content-Type', 'text/plain')])
        return response

    def chunk_encode(self, chunks, dirt=None):
        if dirt is None:
            dirt = self.dirt

        return chunk_encode(chunks, dirt=dirt)

    def body(self, dirt=None):
        return self.chunk_encode(["this", " is ", "chunked", "\nline", " 2", "\n", "line3", ""], dirt=dirt)

    def ping(self, fd):
        fd.write("GET /ping HTTP/1.1\r\n\r\n")
        read_http(fd, body="pong")

    def ping_if_possible(self, fd):
        self.ping(fd)

    def test_short_read_with_content_length(self):
        body = self.body()
        req = b"POST /short-read HTTP/1.1\r\ntransfer-encoding: Chunked\r\nContent-Length:1000\r\n\r\n" + body
        with self.connect() as conn:
            with conn.makefile(bufsize=1) as fd: # pylint:disable=unexpected-keyword-arg
                fd.write(req)
                read_http(fd, body="this is ch")

                self.ping_if_possible(fd)

    def test_short_read_with_zero_content_length(self):
        body = self.body()
        req = b"POST /short-read HTTP/1.1\r\ntransfer-encoding: Chunked\r\nContent-Length:0\r\n\r\n" + body
        #print("REQUEST:", repr(req))

        with self.makefile() as fd:
            fd.write(req)
            read_http(fd, body="this is ch")

            self.ping_if_possible(fd)

    def test_short_read(self):
        body = self.body()
        req = b"POST /short-read HTTP/1.1\r\ntransfer-encoding: Chunked\r\n\r\n" + body

        with self.makefile() as fd:
            fd.write(req)
            read_http(fd, body="this is ch")

            self.ping_if_possible(fd)

    def test_dirt(self):
        body = self.body(dirt="; here is dirt\0bla")
        req = b"POST /ping HTTP/1.1\r\ntransfer-encoding: Chunked\r\n\r\n" + body

        with self.makefile() as fd:
            fd.write(req)
            read_http(fd, body="pong")

            self.ping_if_possible(fd)

    def test_chunked_readline(self):
        body = self.body()
        req = "POST /lines HTTP/1.1\r\nContent-Length: %s\r\ntransfer-encoding: Chunked\r\n\r\n" % (len(body))
        req = req.encode('latin-1')
        req += body

        with self.makefile() as fd:
            fd.write(req)
            read_http(fd, body='this is chunked\nline 2\nline3')

    def test_close_before_finished(self):
        self.expect_one_error()
        body = b'4\r\nthi'
        req = b"POST /short-read HTTP/1.1\r\ntransfer-encoding: Chunked\r\n\r\n" + body
        with self.connect() as sock:
            with sock.makefile(bufsize=1, mode='wb') as fd:# pylint:disable=unexpected-keyword-arg
                fd.write(req)
                fd.close()

        # Python 3 keeps the socket open even though the only
        # makefile is gone; python 2 closed them both (because there were
        # no outstanding references to the socket). Closing is essential for the server
        # to get the message that the read will fail. It's better to be explicit
        # to avoid a ResourceWarning
        sock.close()
        # Under Py2 it still needs to go away, which was implicit before
        del fd
        del sock

        gevent.get_hub().loop.update_now()
        gevent.sleep(0.01) # timing needed for cpython

        if greentest.PYPY:
            # XXX: Something is keeping the socket alive,
            # by which I mean, the close event is not propagating to the server
            # and waking up its recv() loop...we are stuck with the three bytes of
            # 'thi' in the buffer and trying to read the forth. No amount of tinkering
            # with the timing changes this...the only thing that does is running a
            # GC and letting some object get collected. Might this be a problem in real life?

            import gc
            gc.collect()
            gevent.sleep(0.01)
            gevent.get_hub().loop.update_now()
            gc.collect()
            gevent.sleep(0.01)

        # XXX2: Sometimes windows and PyPy/Travis fail to get this error, leading to a test failure.
        # This would have to be due to the socket being kept around and open,
        # not closed at the low levels. I haven't seen this locally.
        # In the PyPy case, I've seen the IOError reported on the console, but not
        # captured in the variables.
        # https://travis-ci.org/gevent/gevent/jobs/329232976#L1374
        self.assert_error(IOError, 'unexpected end of file while parsing chunked data')


class Expect100ContinueTests(TestCase):
    validator = None

    def application(self, environ, start_response):
        content_length = int(environ['CONTENT_LENGTH'])
        if content_length > 1024:
            start_response('417 Expectation Failed', [('Content-Length', '7'), ('Content-Type', 'text/plain')])
            return [b'failure']

        # pywsgi did sent a "100 continue" for each read
        # see http://code.google.com/p/gevent/issues/detail?id=93
        text = environ['wsgi.input'].read(1)
        text += environ['wsgi.input'].read(content_length - 1)
        start_response('200 OK', [('Content-Length', str(len(text))), ('Content-Type', 'text/plain')])
        return [text]

    def test_continue(self):
        with self.makefile() as fd:
            fd.write('PUT / HTTP/1.1\r\nHost: localhost\r\nContent-length: 1025\r\nExpect: 100-continue\r\n\r\n')
            read_http(fd, code=417, body="failure")

            fd.write('PUT / HTTP/1.1\r\nHost: localhost\r\nContent-length: 7\r\nExpect: 100-continue\r\n\r\ntesting')
            read_http(fd, code=100)
            read_http(fd, body="testing")


class MultipleCookieHeadersTest(TestCase):

    validator = None

    def application(self, environ, start_response):
        self.assertEqual(environ['HTTP_COOKIE'], 'name1="value1"; name2="value2"')
        self.assertEqual(environ['HTTP_COOKIE2'], 'nameA="valueA"; nameB="valueB"')
        start_response('200 OK', [])
        return []

    def test(self):
        with self.makefile() as fd:
            fd.write('''GET / HTTP/1.1
Host: localhost
Cookie: name1="value1"
Cookie2: nameA="valueA"
Cookie2: nameB="valueB"
Cookie: name2="value2"\n\n'''.replace('\n', '\r\n'))
            read_http(fd)


class TestLeakInput(TestCase):

    _leak_wsgi_input = None
    _leak_environ = None

    def tearDown(self):
        TestCase.tearDown(self)
        self._leak_wsgi_input = None
        self._leak_environ = None

    def application(self, environ, start_response):
        pi = environ["PATH_INFO"]
        self._leak_wsgi_input = environ["wsgi.input"]
        self._leak_environ = environ
        if pi == "/leak-frame":
            environ["_leak"] = sys._getframe(0)

        text = b"foobar"
        start_response('200 OK', [('Content-Length', str(len(text))), ('Content-Type', 'text/plain')])
        return [text]

    def test_connection_close_leak_simple(self):
        with self.makefile() as fd:
            fd.write(b"GET / HTTP/1.0\r\nConnection: close\r\n\r\n")
            d = fd.read()
        self.assertTrue(d.startswith(b"HTTP/1.1 200 OK"), d)

    def test_connection_close_leak_frame(self):
        with self.makefile() as fd:
            fd.write(b"GET /leak-frame HTTP/1.0\r\nConnection: close\r\n\r\n")
            d = fd.read()
        self.assertTrue(d.startswith(b"HTTP/1.1 200 OK"), d)
        self._leak_environ.pop('_leak')

class TestHTTPResponseSplitting(TestCase):
    # The validator would prevent the app from doing the
    # bad things it needs to do
    validator = None

    status = '200 OK'
    headers = ()
    start_exc = None

    def setUp(self):
        TestCase.setUp(self)
        self.start_exc = None
        self.status = TestHTTPResponseSplitting.status
        self.headers = TestHTTPResponseSplitting.headers

    def tearDown(self):
        TestCase.tearDown(self)
        self.start_exc = None

    def application(self, environ, start_response):
        try:
            start_response(self.status, self.headers)
        except Exception as e: # pylint: disable=broad-except
            self.start_exc = e
        else:
            self.start_exc = None
        return ()

    def _assert_failure(self, message):
        with self.makefile() as fd:
            fd.write('GET / HTTP/1.0\r\nHost: localhost\r\n\r\n')
            fd.read()
        self.assertIsInstance(self.start_exc, ValueError)
        self.assertEqual(self.start_exc.args[0], message)

    def test_newline_in_status(self):
        self.status = '200 OK\r\nConnection: close\r\nContent-Length: 0\r\n\r\n'
        self._assert_failure('carriage return or newline in status')

    def test_newline_in_header_value(self):
        self.headers = [('Test', 'Hi\r\nConnection: close')]
        self._assert_failure('carriage return or newline in header value')

    def test_newline_in_header_name(self):
        self.headers = [('Test\r\n', 'Hi')]
        self._assert_failure('carriage return or newline in header name')


class TestInvalidEnviron(TestCase):
    validator = None
    # check that WSGIServer does not insert any default values for CONTENT_LENGTH

    def application(self, environ, start_response):
        for key, value in environ.items():
            if key in ('CONTENT_LENGTH', 'CONTENT_TYPE') or key.startswith('HTTP_'):
                if key != 'HTTP_HOST':
                    raise ExpectedAssertionError('Unexpected environment variable: %s=%r' % (
                        key, value))
        start_response('200 OK', [])
        return []

    def test(self):
        with self.makefile() as fd:
            fd.write('GET / HTTP/1.0\r\nHost: localhost\r\n\r\n')
            read_http(fd)
        with self.makefile() as fd:
            fd.write('GET / HTTP/1.1\r\nHost: localhost\r\n\r\n')
            read_http(fd)


class TestInvalidHeadersDropped(TestCase):
    validator = None
    # check that invalid headers with a _ are dropped

    def application(self, environ, start_response):
        self.assertNotIn('HTTP_X_AUTH_USER', environ)
        start_response('200 OK', [])
        return []

    def test(self):
        with self.makefile() as fd:
            fd.write('GET / HTTP/1.0\r\nx-auth_user: bob\r\n\r\n')
            read_http(fd)


class TestHandlerSubclass(TestCase):

    validator = None

    class handler_class(TestCase.handler_class):

        def read_requestline(self):
            data = self.rfile.read(7)
            if data[0] == b'<'[0]: # py3: indexing bytes returns ints. sigh.
                # Returning nothing stops handle_one_request()
                # Note that closing or even deleting self.socket() here
                # can lead to the read side throwing Connection Reset By Peer,
                # depending on the Python version and OS
                data += self.rfile.read(15)
                if data.lower() == b'<policy-file-request/>':
                    self.socket.sendall(b'HELLO')
                else:
                    self.log_error('Invalid request: %r', data)
                return None
            return data + self.rfile.readline()

    def application(self, environ, start_response):
        start_response('200 OK', [])
        return []

    def test(self):
        with self.makefile() as fd:
            fd.write(b'<policy-file-request/>\x00')
            fd.flush() # flush() is needed on PyPy, apparently it buffers slightly differently
            self.assertEqual(fd.read(), b'HELLO')

        with self.makefile() as fd:
            fd.write('GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')
            fd.flush()
            read_http(fd)

        with self.makefile() as fd:
            # Trigger an error
            fd.write('<policy-file-XXXuest/>\x00')
            fd.flush()
            self.assertEqual(fd.read(), b'')


class TestErrorAfterChunk(TestCase):
    validator = None

    @staticmethod
    def application(env, start_response):
        start_response('200 OK', [('Content-Type', 'text/plain')])
        yield b"hello"
        raise greentest.ExpectedException('TestErrorAfterChunk')

    def test(self):
        with self.makefile() as fd:
            self.expect_one_error()
            fd.write('GET / HTTP/1.1\r\nHost: localhost\r\nConnection: keep-alive\r\n\r\n')
            with self.assertRaises(ValueError):
                read_http(fd)
        self.assert_error(greentest.ExpectedException)


def chunk_encode(chunks, dirt=None):
    if dirt is None:
        dirt = ""

    b = b""
    for c in chunks:
        x = "%x%s\r\n%s\r\n" % (len(c), dirt, c)
        b += x.encode('ascii')
    return b


class TestInputRaw(greentest.BaseTestCase):
    def make_input(self, data, content_length=None, chunked_input=False):
        if isinstance(data, list):
            data = chunk_encode(data)
            chunked_input = True
        elif isinstance(data, str) and PY3:
            data = data.encode("ascii")
        return Input(StringIO(data), content_length=content_length, chunked_input=chunked_input)

    if PY3:
        def assertEqual(self, first, second, msg=None):
            if isinstance(second, str):
                second = second.encode('ascii')
            super(TestInputRaw, self).assertEqual(first, second, msg)

    def test_short_post(self):
        i = self.make_input("1", content_length=2)
        self.assertRaises(IOError, i.read)

    def test_short_post_read_with_length(self):
        i = self.make_input("1", content_length=2)
        self.assertRaises(IOError, i.read, 2)

    def test_short_post_readline(self):
        i = self.make_input("1", content_length=2)
        self.assertRaises(IOError, i.readline)

    def test_post(self):
        i = self.make_input("12", content_length=2)
        data = i.read()
        self.assertEqual(data, "12")

    def test_post_read_with_length(self):
        i = self.make_input("12", content_length=2)
        data = i.read(10)
        self.assertEqual(data, "12")

    def test_chunked(self):
        i = self.make_input(["1", "2", ""])
        data = i.read()
        self.assertEqual(data, "12")

    def test_chunked_read_with_length(self):
        i = self.make_input(["1", "2", ""])
        data = i.read(10)
        self.assertEqual(data, "12")

    def test_chunked_missing_chunk(self):
        i = self.make_input(["1", "2"])
        self.assertRaises(IOError, i.read)

    def test_chunked_missing_chunk_read_with_length(self):
        i = self.make_input(["1", "2"])
        self.assertRaises(IOError, i.read, 10)

    def test_chunked_missing_chunk_readline(self):
        i = self.make_input(["1", "2"])
        self.assertRaises(IOError, i.readline)

    def test_chunked_short_chunk(self):
        i = self.make_input("2\r\n1", chunked_input=True)
        self.assertRaises(IOError, i.read)

    def test_chunked_short_chunk_read_with_length(self):
        i = self.make_input("2\r\n1", chunked_input=True)
        self.assertRaises(IOError, i.read, 2)

    def test_chunked_short_chunk_readline(self):
        i = self.make_input("2\r\n1", chunked_input=True)
        self.assertRaises(IOError, i.readline)

    def test_32bit_overflow(self):
        # https://github.com/gevent/gevent/issues/289
        # Should not raise an OverflowError on Python 2
        data = b'asdf\nghij\n'
        long_data = b'a' * (pywsgi.MAX_REQUEST_LINE + 10)
        long_data += b'\n'
        data += long_data
        partial_data = b'qjk\n' # Note terminating \n
        n = 25 * 1000000000
        if hasattr(n, 'bit_length'):
            self.assertEqual(n.bit_length(), 35)
        if not PY3 and not PYPY:
            # Make sure we have the impl we think we do
            self.assertRaises(OverflowError, StringIO(data).readline, n)

        i = self.make_input(data, content_length=n)
        # No size hint, but we have too large a content_length to fit
        self.assertEqual(i.readline(), b'asdf\n')
        # Large size hint
        self.assertEqual(i.readline(n), b'ghij\n')
        self.assertEqual(i.readline(n), long_data)

        # Now again with the real content length, assuring we can't read past it
        i = self.make_input(data + partial_data, content_length=len(data) + 1)
        self.assertEqual(i.readline(), b'asdf\n')
        self.assertEqual(i.readline(n), b'ghij\n')
        self.assertEqual(i.readline(n), long_data)
        # Now we've reached content_length so we shouldn't be able to
        # read anymore except the one byte remaining
        self.assertEqual(i.readline(n), b'q')


class Test414(TestCase):

    @staticmethod
    def application(env, start_response):
        raise AssertionError('should not get there')

    def test(self):
        longline = 'x' * 20000
        with self.makefile() as fd:
            fd.write(('''GET /%s HTTP/1.0\r\nHello: world\r\n\r\n''' % longline).encode('latin-1'))
            read_http(fd, code=414)


class TestLogging(TestCase):

    # Something that gets wrapped in a LoggingLogAdapter
    class Logger(object):
        accessed = None
        logged = None
        thing = None

        def log(self, level, msg):
            self.logged = (level, msg)

        def access(self, msg):
            self.accessed = msg

        def get_thing(self):
            return self.thing

    def init_logger(self):
        return self.Logger()

    @staticmethod
    def application(env, start_response):
        start_response('200 OK', [('Content-Type', 'text/plain')])
        return [b'hello']

    # Tests for issue #663

    def test_proxy_methods_on_log(self):
        # An object that looks like a logger gets wrapped
        # with a proxy that
        self.assertTrue(isinstance(self.server.log, pywsgi.LoggingLogAdapter))
        self.server.log.access("access")
        self.server.log.write("write")
        self.assertEqual(self.server.log.accessed, "access")
        self.assertEqual(self.server.log.logged, (20, "write"))

    def test_set_attributes(self):
        # Not defined by the wrapper, it goes to the logger
        self.server.log.thing = 42
        self.assertEqual(self.server.log.get_thing(), 42)

        del self.server.log.thing
        self.assertEqual(self.server.log.get_thing(), None)

    def test_status_log(self):
        # Issue 664: Make sure we format the status line as a string
        self.urlopen()
        msg = self.server.log.logged[1]
        self.assertTrue('"GET / HTTP/1.1" 200 ' in msg, msg)

        # Issue 756: Make sure we don't throw a newline on the end
        self.assertTrue('\n' not in msg, msg)

class TestEnviron(TestCase):

    # The wsgiref validator asserts type(environ) is dict.
    # https://mail.python.org/pipermail/web-sig/2016-March/005455.html
    validator = None

    def init_server(self, application):
        super(TestEnviron, self).init_server(application)
        self.server.environ_class = pywsgi.SecureEnviron

    def application(self, env, start_response):
        self.assertIsInstance(env, pywsgi.SecureEnviron)
        start_response('200 OK', [('Content-Type', 'text/plain')])
        return []

    def test_environ_is_secure_by_default(self):
        self.urlopen()

    def test_default_secure_repr(self):
        environ = pywsgi.SecureEnviron()
        self.assertIn('<pywsgi.SecureEnviron dict (keys: 0) at', repr(environ))
        self.assertIn('<pywsgi.SecureEnviron dict (keys: 0) at', str(environ))

        environ['key'] = 'value'
        self.assertIn('<pywsgi.SecureEnviron dict (keys: 1) at', repr(environ))
        self.assertIn('<pywsgi.SecureEnviron dict (keys: 1) at', str(environ))

        environ.secure_repr = False
        self.assertEqual(str({'key': 'value'}), str(environ))
        self.assertEqual(repr({'key': 'value'}), repr(environ))

        del environ.secure_repr

        environ.whitelist_keys = ('missing value',)
        self.assertEqual(str({'key': "<MASKED>"}), str(environ))
        self.assertEqual(repr({'key': "<MASKED>"}), repr(environ))

        environ.whitelist_keys = ('key',)
        self.assertEqual(str({'key': 'value'}), str(environ))
        self.assertEqual(repr({'key': 'value'}), repr(environ))

        del environ.whitelist_keys

    def test_override_class_defaults(self):
        class EnvironClass(pywsgi.SecureEnviron):
            __slots__ = ()

        environ = EnvironClass()

        self.assertTrue(environ.secure_repr)
        EnvironClass.default_secure_repr = False
        self.assertFalse(environ.secure_repr)

        self.assertEqual(str({}), str(environ))
        self.assertEqual(repr({}), repr(environ))

        EnvironClass.default_secure_repr = True
        EnvironClass.default_whitelist_keys = ('key',)

        environ['key'] = 1
        self.assertEqual(str({'key': 1}), str(environ))
        self.assertEqual(repr({'key': 1}), repr(environ))

        # Clean up for leaktests
        del environ
        del EnvironClass
        import gc; gc.collect()


    def test_copy_still_secure(self):
        for cls in (pywsgi.Environ, pywsgi.SecureEnviron):
            self.assertIsInstance(cls().copy(), cls)

    def test_pickle_copy_returns_dict(self):
        # Anything going through copy.copy/pickle should
        # return the same pickle that a dict would.
        import pickle
        import json

        for cls in (pywsgi.Environ, pywsgi.SecureEnviron):
            bltin = {'key': 'value'}
            env = cls(bltin)
            self.assertIsInstance(env, cls)
            self.assertEqual(bltin, env)
            self.assertEqual(env, bltin)

            for protocol in range(0, pickle.HIGHEST_PROTOCOL + 1):
                # It's impossible to get a subclass of dict to pickle
                # identically, but it can restore identically
                env_dump = pickle.dumps(env, protocol)
                self.assertNotIn(b'Environ', env_dump)
                loaded = pickle.loads(env_dump)
                self.assertEqual(type(loaded), dict)

            self.assertEqual(json.dumps(bltin), json.dumps(env))


if __name__ == '__main__':
    greentest.main()
