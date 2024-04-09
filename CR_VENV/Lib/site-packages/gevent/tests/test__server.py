from __future__ import print_function, division
from contextlib import contextmanager
import unittest
import errno
import os


import gevent.testing as greentest
from gevent.testing import PY3
from gevent.testing import sysinfo
from gevent.testing import DEFAULT_SOCKET_TIMEOUT as _DEFAULT_SOCKET_TIMEOUT
from gevent.testing.timing import SMALLEST_RELIABLE_DELAY
from gevent.testing.sockets import tcp_listener
from gevent.testing import WIN

from gevent import socket
import gevent
from gevent.server import StreamServer
from gevent.exceptions import LoopExit


class SimpleStreamServer(StreamServer):

    def handle(self, client_socket, _address): # pylint:disable=method-hidden
        fd = client_socket.makefile()
        try:
            request_line = fd.readline()
            if not request_line:
                return
            try:
                _method, path, _rest = request_line.split(' ', 3)
            except Exception:
                print('Failed to parse request line: %r' % (request_line, ))
                raise
            if path == '/ping':
                client_socket.sendall(b'HTTP/1.0 200 OK\r\n\r\nPONG')
            elif path in ['/long', '/short']:
                client_socket.sendall(b'hello')
                while True:
                    data = client_socket.recv(1)
                    if not data:
                        break
            else:
                client_socket.sendall(b'HTTP/1.0 404 WTF?\r\n\r\n')
        finally:
            fd.close()

def sleep_to_clear_old_sockets(*_args):
    try:
        # Allow any queued callbacks needed to close sockets
        # to run. On Windows, this needs to spin the event loop to
        # allow proper FD cleanup. Otherwise we risk getting an
        # old FD that's being closed and then get spurious connection
        # errors.
        gevent.sleep(0 if not WIN else SMALLEST_RELIABLE_DELAY)
    except Exception: # pylint:disable=broad-except
        pass


class Settings(object):
    ServerClass = StreamServer
    ServerSubClass = SimpleStreamServer
    restartable = True
    close_socket_detected = True

    @staticmethod
    def assertAcceptedConnectionError(inst):
        with inst.makefile() as conn:
            try:
                result = conn.read()
            except socket.timeout:
                result = None
        inst.assertFalse(result)

    assert500 = assertAcceptedConnectionError

    @staticmethod
    def assert503(inst):
        # regular reads timeout
        inst.assert500()
        # attempt to send anything reset the connection
        try:
            inst.send_request()
        except socket.error as ex:
            if ex.args[0] not in greentest.CONN_ABORTED_ERRORS:
                raise

    @staticmethod
    def assertPoolFull(inst):
        with inst.assertRaises(socket.timeout):
            inst.assertRequestSucceeded(timeout=0.01)

    @staticmethod
    def fill_default_server_args(inst, kwargs):
        kwargs.setdefault('spawn', inst.get_spawn())
        return kwargs

class TestCase(greentest.TestCase):
    # pylint: disable=too-many-public-methods
    __timeout__ = greentest.LARGE_TIMEOUT
    Settings = Settings
    server = None

    def cleanup(self):
        if getattr(self, 'server', None) is not None:
            self.server.stop()
            self.server = None
        sleep_to_clear_old_sockets()

    def get_listener(self):
        return self._close_on_teardown(tcp_listener(backlog=5))

    def get_server_host_port_family(self):
        server_host = self.server.server_host
        if not server_host:
            server_host = greentest.DEFAULT_LOCAL_HOST_ADDR
        elif server_host == '::':
            server_host = greentest.DEFAULT_LOCAL_HOST_ADDR6

        try:
            family = self.server.socket.family
        except AttributeError:
            # server deletes socket when closed
            family = socket.AF_INET

        return server_host, self.server.server_port, family

    @contextmanager
    def makefile(self, timeout=_DEFAULT_SOCKET_TIMEOUT, bufsize=1, include_raw_socket=False):
        server_host, server_port, family = self.get_server_host_port_family()
        bufarg = 'buffering' if PY3 else 'bufsize'
        makefile_kwargs = {bufarg: bufsize}
        if PY3:
            # Under Python3, you can't read and write to the same
            # makefile() opened in r, and r+ is not allowed
            makefile_kwargs['mode'] = 'rwb'

        with socket.socket(family=family) as sock:
            rconn = None
            # We want the socket to be accessible from the fileobject
            # we return. On Python 2, natively this is available as
            # _sock, but Python 3 doesn't have that.
            sock.connect((server_host, server_port))
            sock.settimeout(timeout)
            with sock.makefile(**makefile_kwargs) as rconn:
                result = rconn if not include_raw_socket else (rconn, sock)
                yield result

    def send_request(self, url='/', timeout=_DEFAULT_SOCKET_TIMEOUT, bufsize=1):
        with self.makefile(timeout=timeout, bufsize=bufsize) as conn:
            self.send_request_to_fd(conn, url)

    def send_request_to_fd(self, fd, url='/'):
        fd.write(('GET %s HTTP/1.0\r\n\r\n' % url).encode('latin-1'))
        fd.flush()

    LOCAL_CONN_REFUSED_ERRORS = ()
    if greentest.OSX:
        # A kernel bug in OS X sometimes results in this
        LOCAL_CONN_REFUSED_ERRORS = (errno.EPROTOTYPE,)
    elif greentest.WIN and greentest.PYPY3:
        # We see WinError 10049: The requested address is not valid
        # which is not one of the errors we get anywhere else.
        # Not sure which errno constant this is?
        LOCAL_CONN_REFUSED_ERRORS = (10049,)

    def assertConnectionRefused(self, in_proc_server=True):
        try:
            with self.assertRaises(socket.error) as exc:
                with self.makefile() as conn:
                    conn.close()
        except LoopExit:
            if not in_proc_server:
                raise
            # A LoopExit is fine. If we've killed the server
            # and don't have any other greenlets to run, then
            # blocking to open the connection might raise this.
            # This became likely on Windows once we stopped
            # passing IP addresses through an extra call to
            # ``getaddrinfo``, which changed the number of switches
            return

        ex = exc.exception
        self.assertIn(ex.args[0],
                      (errno.ECONNREFUSED, errno.EADDRNOTAVAIL,
                       errno.ECONNRESET, errno.ECONNABORTED) + self.LOCAL_CONN_REFUSED_ERRORS,
                      (ex, ex.args))

    def assert500(self):
        self.Settings.assert500(self)

    def assert503(self):
        self.Settings.assert503(self)

    def assertAcceptedConnectionError(self):
        self.Settings.assertAcceptedConnectionError(self)

    def assertPoolFull(self):
        self.Settings.assertPoolFull(self)

    def assertNotAccepted(self):
        try:
            with self.makefile(include_raw_socket=True) as (conn, sock):
                conn.write(b'GET / HTTP/1.0\r\n\r\n')
                conn.flush()
                result = b''
                try:
                    while True:
                        data = sock.recv(1)
                        if not data:
                            break
                        result += data
                except socket.timeout:
                    self.assertFalse(result)
                    return
        except LoopExit:
            # See assertConnectionRefused
            return

        self.assertTrue(result.startswith(b'HTTP/1.0 500 Internal Server Error'), repr(result))


    def assertRequestSucceeded(self, timeout=_DEFAULT_SOCKET_TIMEOUT):
        with self.makefile(timeout=timeout) as conn:
            conn.write(b'GET /ping HTTP/1.0\r\n\r\n')
            result = conn.read()

        self.assertTrue(result.endswith(b'\r\n\r\nPONG'), repr(result))

    def start_server(self):
        self.server.start()
        self.assertRequestSucceeded()
        self.assertRequestSucceeded()

    def stop_server(self):
        self.server.stop()
        self.assertConnectionRefused()

    def report_netstat(self, _msg):
        # At one point this would call 'sudo netstat -anp | grep PID'
        # with os.system. We can probably do better with psutil.
        return

    def _create_server(self, *args, **kwargs):
        kind = kwargs.pop('server_kind', self.ServerSubClass)
        addr = kwargs.pop('server_listen_addr', (greentest.DEFAULT_BIND_ADDR, 0))
        return kind(addr, *args, **kwargs)

    def init_server(self, *args, **kwargs):
        self.server = self._create_server(*args, **kwargs)
        self.server.start()
        sleep_to_clear_old_sockets()

    @property
    def socket(self):
        return self.server.socket

    def _test_invalid_callback(self):
        if sysinfo.RUNNING_ON_APPVEYOR:
            self.skipTest("Sometimes misses the error") # XXX: Why?

        try:
            # Can't use a kwarg here, WSGIServer and StreamServer
            # take different things (application and handle)
            self.init_server(lambda: None)
            self.expect_one_error()

            self.assert500()
            self.assert_error(TypeError)
        finally:
            self.server.stop()
            # XXX: There's something unreachable (with a traceback?)
            # We need to clear it to make the leak checks work on Travis;
            # so far I can't reproduce it locally on OS X.
            import gc; gc.collect()

    def fill_default_server_args(self, kwargs):
        return self.Settings.fill_default_server_args(self, kwargs)

    def ServerClass(self, *args, **kwargs):
        return self.Settings.ServerClass(*args,
                                         **self.fill_default_server_args(kwargs))

    def ServerSubClass(self, *args, **kwargs):
        return self.Settings.ServerSubClass(*args,
                                            **self.fill_default_server_args(kwargs))

    def get_spawn(self):
        return None

class TestDefaultSpawn(TestCase):

    def get_spawn(self):
        return gevent.spawn

    def _test_server_start_stop(self, restartable):
        self.report_netstat('before start')
        self.start_server()
        self.report_netstat('after start')
        if restartable and self.Settings.restartable:
            self.server.stop_accepting()
            self.report_netstat('after stop_accepting')
            self.assertNotAccepted()
            self.server.start_accepting()
            self.report_netstat('after start_accepting')
            sleep_to_clear_old_sockets()
            self.assertRequestSucceeded()
        self.stop_server()
        self.report_netstat('after stop')

    def test_backlog_is_not_accepted_for_socket(self):
        self.switch_expected = False
        with self.assertRaises(TypeError):
            self.ServerClass(self.get_listener(), backlog=25)

    @greentest.skipOnLibuvOnCIOnPyPy("Sometimes times out")
    @greentest.skipOnAppVeyor("Sometimes times out.")
    def test_backlog_is_accepted_for_address(self):
        self.server = self.ServerSubClass((greentest.DEFAULT_BIND_ADDR, 0), backlog=25)
        self.assertConnectionRefused()
        self._test_server_start_stop(restartable=False)

    def test_subclass_just_create(self):
        self.server = self.ServerSubClass(self.get_listener())
        self.assertNotAccepted()

    @greentest.skipOnAppVeyor("Sometimes times out.")
    def test_subclass_with_socket(self):
        self.server = self.ServerSubClass(self.get_listener())
        # the connection won't be refused, because there exists a
        # listening socket, but it won't be handled also
        self.assertNotAccepted()
        self._test_server_start_stop(restartable=True)

    def test_subclass_with_address(self):
        self.server = self.ServerSubClass((greentest.DEFAULT_BIND_ADDR, 0))
        self.assertConnectionRefused()
        self._test_server_start_stop(restartable=True)

    def test_invalid_callback(self):
        self._test_invalid_callback()

    @greentest.reraises_flaky_timeout(socket.timeout)
    def _test_serve_forever(self):
        g = gevent.spawn(self.server.serve_forever)
        try:
            sleep_to_clear_old_sockets()
            self.assertRequestSucceeded()
            self.server.stop()
            self.assertFalse(self.server.started)
            self.assertConnectionRefused()
        finally:
            g.kill()
            g.get()
            self.server.stop()

    def test_serve_forever(self):
        self.server = self.ServerSubClass((greentest.DEFAULT_BIND_ADDR, 0))
        self.assertFalse(self.server.started)
        self.assertConnectionRefused()
        self._test_serve_forever()

    def test_serve_forever_after_start(self):
        self.server = self.ServerSubClass((greentest.DEFAULT_BIND_ADDR, 0))
        self.assertConnectionRefused()
        self.assertFalse(self.server.started)
        self.server.start()
        self.assertTrue(self.server.started)
        self._test_serve_forever()

    @greentest.skipIf(greentest.EXPECT_POOR_TIMER_RESOLUTION, "Sometimes spuriously fails")
    def test_server_closes_client_sockets(self):
        self.server = self.ServerClass((greentest.DEFAULT_BIND_ADDR, 0), lambda *args: [])
        self.server.start()
        sleep_to_clear_old_sockets()
        with self.makefile() as conn:
            self.send_request_to_fd(conn)
            # use assert500 below?
            with gevent.Timeout._start_new_or_dummy(1):
                try:
                    result = conn.read()
                    if result:
                        assert result.startswith('HTTP/1.0 500 Internal Server Error'), repr(result)
                except socket.timeout:
                    pass
                except socket.error as ex:
                    if ex.args[0] == 10053:
                        pass  # "established connection was aborted by the software in your host machine"
                    elif ex.args[0] == errno.ECONNRESET:
                        pass
                    else:
                        raise

        self.stop_server()

    @property
    def socket(self):
        return self.server.socket

    def test_error_in_spawn(self):
        self.init_server()
        self.assertTrue(self.server.started)
        error = ExpectedError('test_error_in_spawn')
        def _spawn(*_args):
            gevent.getcurrent().throw(error)
        self.server._spawn = _spawn
        self.expect_one_error()
        self.assertAcceptedConnectionError()
        self.assert_error(ExpectedError, error)

    def test_server_repr_when_handle_is_instancemethod(self):
        # PR 501
        self.init_server()
        assert self.server.started
        self.assertIn('Server', repr(self.server))

        self.server.set_handle(self.server.handle)
        self.assertIn('handle=<bound method', repr(self.server))
        self.assertIn('of self>', repr(self.server))

        self.server.set_handle(self.test_server_repr_when_handle_is_instancemethod)
        self.assertIn('test_server_repr_when_handle_is_instancemethod', repr(self.server))

        def handle():
            pass
        self.server.set_handle(handle)
        self.assertIn('handle=<function', repr(self.server))


class TestRawSpawn(TestDefaultSpawn):

    def get_spawn(self):
        return gevent.spawn_raw


class TestPoolSpawn(TestDefaultSpawn):

    def get_spawn(self):
        return 2

    @greentest.skipIf(greentest.EXPECT_POOR_TIMER_RESOLUTION,
                      "If we have bad timer resolution and hence increase timeouts, "
                      "it can be hard to sleep for a correct amount of time that lets "
                      "requests in the pool be full.")
    def test_pool_full(self):
        self.init_server()
        with self.makefile() as long_request:
            with self.makefile() as short_request:
                self.send_request_to_fd(short_request, '/short')
                self.send_request_to_fd(long_request, '/long')

                # keep long_request in scope, otherwise the connection will be closed
                gevent.get_hub().loop.update_now()
                gevent.sleep(_DEFAULT_SOCKET_TIMEOUT / 10.0)
                self.assertPoolFull()
                self.assertPoolFull()
                # XXX Not entirely clear why this fails (timeout) on appveyor;
                # underlying socket timeout causing the long_request to close?
                self.assertPoolFull()

        # gevent.http and gevent.wsgi cannot detect socket close, so sleep a little
        # to let /short request finish
        gevent.sleep(_DEFAULT_SOCKET_TIMEOUT)
        # XXX: This tends to timeout. Which is weird, because what would have
        # been the third call to assertPoolFull() DID NOT timeout, hence why it
        # was removed.
        try:
            self.assertRequestSucceeded()
        except socket.timeout:
            greentest.reraiseFlakyTestTimeout()

    test_pool_full.error_fatal = False


class TestNoneSpawn(TestCase):

    def get_spawn(self):
        return None

    def test_invalid_callback(self):
        self._test_invalid_callback()

    @greentest.skipOnAppVeyor("Sometimes doesn't get the error.")
    def test_assertion_in_blocking_func(self):
        def sleep(*_args):
            gevent.sleep(SMALLEST_RELIABLE_DELAY)
        self.init_server(sleep, server_kind=self.ServerSubClass, spawn=None)
        self.expect_one_error()
        self.assert500()
        self.assert_error(AssertionError, 'Impossible to call blocking function in the event loop callback')


class ExpectedError(Exception):
    pass



class TestSSLSocketNotAllowed(TestCase):

    switch_expected = False

    def get_spawn(self):
        return gevent.spawn

    @unittest.skipUnless(hasattr(socket, 'ssl'), "Uses socket.ssl")
    def test(self):
        from gevent.socket import ssl
        listener = self._close_on_teardown(tcp_listener(backlog=5))
        listener = ssl(listener)
        self.assertRaises(TypeError, self.ServerSubClass, listener)

def _file(name, here=os.path.dirname(__file__)):
    return os.path.abspath(os.path.join(here, name))


class BadWrapException(BaseException):
    pass


class TestSSLGetCertificate(TestCase):

    def _create_server(self): # pylint:disable=arguments-differ
        return self.ServerSubClass((greentest.DEFAULT_BIND_ADDR, 0),
                                   keyfile=_file('server.key'),
                                   certfile=_file('server.crt'))

    def get_spawn(self):
        return gevent.spawn

    def test_certificate(self):
        # Issue 801
        from gevent import monkey, ssl
        # only broken if *not* monkey patched
        self.assertFalse(monkey.is_module_patched('ssl'))
        self.assertFalse(monkey.is_module_patched('socket'))

        self.init_server()

        server_host, server_port, _family = self.get_server_host_port_family()
        ssl.get_server_certificate((server_host, server_port)) # pylint:disable=no-member


    def test_wrap_socket_and_handle_wrap_failure(self):
        # A failure to wrap the socket doesn't have follow on effects
        # like failing with a UnboundLocalError.

        # See https://github.com/gevent/gevent/issues/1236
        self.init_server()

        def bad_wrap(_client_socket, **_wrap_args):
            raise BadWrapException()

        self.server.wrap_socket = bad_wrap

        with self.assertRaises(BadWrapException):
            self.server._handle(None, None)

# test non-socket.error exception in accept call: fatal
# test error in spawn(): non-fatal
# test error in spawned handler: non-fatal


if __name__ == '__main__':
    greentest.main()
