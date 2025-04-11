from __future__ import print_function
from __future__ import absolute_import

from gevent import monkey
# This line can be commented out so that most tests run with the
# system socket for comparison.
monkey.patch_all()

import sys
import array
import socket
import time
import unittest
from functools import wraps

import gevent
from gevent._compat import reraise

import gevent.testing as greentest

from gevent.testing import six
from gevent.testing import LARGE_TIMEOUT
from gevent.testing import support
from gevent.testing import params
from gevent.testing.sockets import tcp_listener
from gevent.testing.skipping import skipWithoutExternalNetwork
from gevent.testing.skipping import skipOnMacOnCI

# we use threading on purpose so that we can test both regular and
# gevent sockets with the same code
from threading import Thread as _Thread
from threading import Event

errno_types = int

# socket.accept/unwrap/makefile aren't found for some reason
# pylint:disable=no-member

class BaseThread(object):
    terminal_exc = None

    def __init__(self, target):
        @wraps(target)
        def errors_are_fatal(*args, **kwargs):
            try:
                return target(*args, **kwargs)
            except: # pylint:disable=bare-except
                self.terminal_exc = sys.exc_info()
                raise
        self.target = errors_are_fatal

class GreenletThread(BaseThread):

    def __init__(self, target=None, args=()):
        BaseThread.__init__(self, target)
        self.glet = gevent.spawn(self.target, *args)

    def join(self, *args, **kwargs):
        return self.glet.join(*args, **kwargs)

    def is_alive(self):
        return not self.glet.ready()

if not monkey.is_module_patched('threading'):
    class ThreadThread(BaseThread, _Thread):
        def __init__(self, **kwargs):
            target = kwargs.pop('target')
            BaseThread.__init__(self, target)
            _Thread.__init__(self, target=self.target, **kwargs)
            self.start()
    Thread = ThreadThread
else:
    Thread = GreenletThread

class TestTCP(greentest.TestCase):
    __timeout__ = None
    TIMEOUT_ERROR = socket.timeout
    long_data = ", ".join([str(x) for x in range(20000)])
    if not isinstance(long_data, bytes):
        long_data = long_data.encode('ascii')

    def setUp(self):
        super(TestTCP, self).setUp()
        if '-v' in sys.argv:
            printed = []
            try:
                from time import perf_counter as now
            except ImportError:
                from time import time as now
            def log(*args):
                if not printed:
                    print()
                    printed.append(1)
                print("\t -> %0.6f" % now(), *args)

            orig_cot = self._close_on_teardown
            def cot(o):
                log("Registering for teardown", o)
                def c(o=o):
                    log("Closing on teardown", o)
                    o.close()
                    o = None
                orig_cot(c)
                return o
            self._close_on_teardown = cot

        else:
            def log(*_args):
                "Does nothing"
        self.log = log


        self.listener = self._close_on_teardown(self._setup_listener())
        # It is important to watch the lifetimes of socket objects and
        # ensure that:
        # (1) they are closed; and
        # (2) *before* the next test begins.
        #
        # For example, it's a bad bad thing to leave a greenlet running past the
        # scope of the individual test method if that greenlet will close
        # a socket object --- especially if that socket object might also have been
        # closed explicitly.
        #
        # On Windows, we've seen issue with filenos getting reused while something
        # still thinks they have the original fileno around. When they later
        # close that fileno, a completely unrelated object is closed.
        self.port = self.listener.getsockname()[1]

    def _setup_listener(self):
        return tcp_listener()

    def create_connection(self, host=None, port=None, timeout=None,
                          blocking=None):
        sock = self._close_on_teardown(socket.socket())
        sock.connect((host or params.DEFAULT_CONNECT, port or self.port))
        if timeout is not None:
            sock.settimeout(timeout)
        if blocking is not None:
            sock.setblocking(blocking)
        return sock

    def _test_sendall(self, data, match_data=None, client_method='sendall',
                      **client_args):
        # pylint:disable=too-many-locals,too-many-branches,too-many-statements
        log = self.log
        log("test_sendall using method", client_method)

        read_data = []
        accepted_event = Event()

        def accept_and_read():
            log("\taccepting", self.listener)
            conn, _ = self.listener.accept()
            try:
                with conn.makefile(mode='rb') as r:
                    log("\taccepted on server; client conn is", conn, "file is", r)
                    accepted_event.set()
                    log("\treading")
                    read_data.append(r.read())
                    log("\tdone reading", r, "got bytes", len(read_data[0]))
                del r
            finally:
                conn.close()
                del conn


        server = Thread(target=accept_and_read)
        try:
            log("creating client connection")
            client = self.create_connection(**client_args)

            # It's important to wait for the server to fully accept before
            # we shutdown and close the socket. In SSL mode, the number
            # and timing of data exchanges to complete the handshake and
            # thus exactly when greenlet switches occur, varies by TLS version.
            #
            # It turns out that on < TLS1.3, we were getting lucky and the
            # server was the greenlet that raced ahead and blocked in r.read()
            # before the client returned from create_connection().
            #
            # But when TLS 1.3 was deployed (OpenSSL 1.1), the *client* was the
            # one that raced ahead while the server had yet to return from
            # self.listener.accept(). So the client sent the data to the socket,
            # and closed, before the server could do anything, and the server,
            # when it got switched to by server.join(), found its new socket
            # dead.
            accepted_event.wait()
            log("Client got accepted event from server", client, "; sending data", len(data))
            try:
                x = getattr(client, client_method)(data)
                log("Client sent data: result from method", x)
            finally:
                log("Client will unwrap and shutdown")
                if hasattr(client, 'unwrap'):
                    # Are we dealing with an SSLSocket? If so, unwrap it
                    # before attempting to shut down the socket. This does the
                    # SSL shutdown handshake and (hopefully) stops ``accept_and_read``
                    # from generating ``ConnectionResetError`` on AppVeyor.
                    try:
                        client = client.unwrap()
                    except (ValueError, OSError):
                        # PyPy raises _cffi_ssl._stdssl.error.SSLSyscallError,
                        # which is an IOError in 2.7 and OSError in 3.7
                        pass

                try:
                    # The implicit reference-based nastiness of Python 2
                    # sockets interferes, especially when using SSL sockets.
                    # The best way to get a decent FIN to the server is to shutdown
                    # the output. Doing that on Python 3, OTOH, is contraindicated
                    # except on PyPy, so this used to read ``PY2 or PYPY``. But
                    # it seems that a shutdown is generally good practice, and I didn't
                    # document what errors we saw without it. Per issue #1637
                    # lets do a shutdown everywhere, but only after removing any
                    # SSL wrapping.
                    client.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

                log("Client will close")
                client.close()
        finally:
            server.join(10)
            assert not server.is_alive()

        if server.terminal_exc:
            reraise(*server.terminal_exc)

        if match_data is None:
            match_data = self.long_data
        read_data = read_data[0].split(b',')
        match_data = match_data.split(b',')
        self.assertEqual(read_data[0], match_data[0])
        self.assertEqual(len(read_data), len(match_data))
        self.assertEqual(read_data, match_data)

    def test_sendall_str(self):
        self._test_sendall(self.long_data)

    if six.PY2:
        def test_sendall_unicode(self):
            self._test_sendall(six.text_type(self.long_data))

    @skipOnMacOnCI("Sometimes fails for no apparent reason (buffering?)")
    def test_sendall_array(self):
        data = array.array("B", self.long_data)
        self._test_sendall(data)

    def test_sendall_empty(self):
        data = b''
        self._test_sendall(data, data)

    def test_sendall_empty_with_timeout(self):
        # Issue 719
        data = b''
        self._test_sendall(data, data, timeout=10)

    def test_sendall_nonblocking(self):
        # https://github.com/benoitc/gunicorn/issues/1282
        # Even if the socket is non-blocking, we make at least
        # one attempt to send data. Under Py2 before this fix, we
        # would incorrectly immediately raise a timeout error
        data = b'hi\n'
        self._test_sendall(data, data, blocking=False)

    def test_empty_send(self):
        # Issue 719
        data = b''
        self._test_sendall(data, data, client_method='send')

    def test_fullduplex(self):
        N = 100000

        def server():
            remote_client, _ = self.listener.accept()
            self._close_on_teardown(remote_client)
            # start reading, then, while reading, start writing. the reader should not hang forever

            sender = Thread(target=remote_client.sendall,
                            args=((b't' * N),))
            try:
                result = remote_client.recv(1000)
                self.assertEqual(result, b'hello world')
            finally:
                sender.join()

        server_thread = Thread(target=server)
        client = self.create_connection()
        client_file = self._close_on_teardown(client.makefile())
        client_reader = Thread(target=client_file.read, args=(N, ))
        time.sleep(0.1)
        client.sendall(b'hello world')
        time.sleep(0.1)

        # close() used to hang
        client_file.close()
        client.close()

        # this tests "full duplex" bug;
        server_thread.join()

        client_reader.join()

    def test_recv_timeout(self):
        def accept():
            # make sure the conn object stays alive until the end;
            # premature closing triggers a ResourceWarning and
            # EOF on the client.
            conn, _ = self.listener.accept()
            self._close_on_teardown(conn)

        acceptor = Thread(target=accept)
        client = self.create_connection()
        try:
            client.settimeout(1)
            start = time.time()
            with self.assertRaises(self.TIMEOUT_ERROR):
                client.recv(1024)
            took = time.time() - start
            self.assertTimeWithinRange(took, 1 - 0.1, 1 + 0.1)
        finally:
            acceptor.join()

    # Subclasses can disable  this
    _test_sendall_timeout_check_time = True

    # Travis-CI container infrastructure is configured with
    # large socket buffers, at least 2MB, as-of Jun 3, 2015,
    # so we must be sure to send more data than that.
    # In 2018, this needs to be increased *again* as a smaller value was
    # still often being sent.
    _test_sendall_data = b'hello' * 100000000

    # This doesn't make much sense...why are we really skipping this?
    @greentest.skipOnWindows("On Windows send() accepts whatever is thrown at it")
    def test_sendall_timeout(self):
        client_sock = []
        acceptor = Thread(target=lambda: client_sock.append(self.listener.accept()))
        client = self.create_connection()
        time.sleep(0.1)
        assert client_sock
        client.settimeout(0.1)
        start = time.time()
        try:
            with self.assertRaises(self.TIMEOUT_ERROR):
                client.sendall(self._test_sendall_data)
            if self._test_sendall_timeout_check_time:
                took = time.time() - start
                self.assertTimeWithinRange(took, 0.09, 0.2)
        finally:
            acceptor.join()
            client.close()
            client_sock[0][0].close()

    def test_makefile(self):
        def accept_once():
            conn, _ = self.listener.accept()
            fd = conn.makefile(mode='wb')
            fd.write(b'hello\n')
            fd.flush()
            fd.close()
            conn.close()  # for pypy

        acceptor = Thread(target=accept_once)
        try:
            client = self.create_connection()
            # Closing the socket doesn't close the file
            client_file = client.makefile(mode='rb')
            client.close()
            line = client_file.readline()
            self.assertEqual(line, b'hello\n')
            self.assertEqual(client_file.read(), b'')
            client_file.close()
        finally:
            acceptor.join()

    def test_makefile_timeout(self):

        def accept_once():
            conn, _ = self.listener.accept()
            try:
                time.sleep(0.3)
            finally:
                conn.close()  # for pypy

        acceptor = Thread(target=accept_once)
        try:
            client = self.create_connection()
            client.settimeout(0.1)
            fd = client.makefile(mode='rb')
            self.assertRaises(self.TIMEOUT_ERROR, fd.readline)
            client.close()
            fd.close()
        finally:
            acceptor.join()

    def test_attributes(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
        self.assertIs(s.family, socket.AF_INET)
        self.assertEqual(s.type, socket.SOCK_DGRAM)
        self.assertEqual(0, s.proto)

        if hasattr(socket, 'SOCK_NONBLOCK'):
            s.settimeout(1)
            self.assertIs(s.family, socket.AF_INET)

            s.setblocking(0)
            std_socket = monkey.get_original('socket', 'socket')(socket.AF_INET, socket.SOCK_DGRAM, 0)
            try:
                std_socket.setblocking(0)
                self.assertEqual(std_socket.type, s.type)
            finally:
                std_socket.close()

        s.close()

    def test_connect_ex_nonblocking_bad_connection(self):
        # Issue 841
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.setblocking(False)
            ret = s.connect_ex((greentest.DEFAULT_LOCAL_HOST_ADDR, support.find_unused_port()))
            self.assertIsInstance(ret, errno_types)
        finally:
            s.close()

    @skipWithoutExternalNetwork("Tries to resolve hostname")
    def test_connect_ex_gaierror(self):
        # Issue 841
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            with self.assertRaises(socket.gaierror):
                s.connect_ex(('foo.bar.fizzbuzz', support.find_unused_port()))
        finally:
            s.close()

    @skipWithoutExternalNetwork("Tries to resolve hostname")
    def test_connect_ex_not_call_connect(self):
        # Issue 1931

        def do_it(sock):
            try:
                with self.assertRaises(socket.gaierror):
                    sock.connect_ex(('foo.bar.fizzbuzz', support.find_unused_port()))
            finally:
                sock.close()

        # An instance attribute doesn't matter because we can't set it
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with self.assertRaises(AttributeError):
            s.connect = None
        s.close()

        # A subclass
        class S(socket.socket):
            def connect(self, *args):
                raise AssertionError('Should not be called')

        s = S(socket.AF_INET, socket.SOCK_STREAM)
        do_it(s)

    def test_connect_ex_nonblocking_overflow(self):
        # Issue 841
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.setblocking(False)
            with self.assertRaises(OverflowError):
                s.connect_ex((greentest.DEFAULT_LOCAL_HOST_ADDR, 65539))
        finally:
            s.close()

    @unittest.skipUnless(hasattr(socket, 'SOCK_CLOEXEC'),
                         "Requires SOCK_CLOEXEC")
    def test_connect_with_type_flags_ignored(self):
        # Issue 944
        # If we have SOCK_CLOEXEC or similar, we shouldn't be passing
        # them through to the getaddrinfo call that connect() makes
        SOCK_CLOEXEC = socket.SOCK_CLOEXEC # pylint:disable=no-member
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM | SOCK_CLOEXEC)

        def accept_once():
            conn, _ = self.listener.accept()
            fd = conn.makefile(mode='wb')
            fd.write(b'hello\n')
            fd.close()
            conn.close()

        acceptor = Thread(target=accept_once)
        try:
            s.connect((params.DEFAULT_CONNECT, self.port))
            fd = s.makefile(mode='rb')
            self.assertEqual(fd.readline(), b'hello\n')

            fd.close()
            s.close()
        finally:
            acceptor.join()


class TestCreateConnection(greentest.TestCase):

    __timeout__ = LARGE_TIMEOUT

    def test_refuses(self, **conn_args):
        connect_port = support.find_unused_port()

        with self.assertRaisesRegex(
                socket.error,
                # We really expect "connection refused". It's unclear
                # where/why we would get '[errno -2] name or service
                # not known' but it seems some systems generate that.
                # https://github.com/gevent/gevent/issues/1389 Somehow
                # extremly rarely we've also seen 'address already in
                # use', which makes even less sense. The manylinux
                # 2010 environment produces 'errno 99 Cannot assign
                # requested address', which, I guess?
                # Meanwhile, the musllinux_1 environment produces
                # '[Errno 99] Address not available'
                'refused|not known|already in use|assign|not available'
        ):
            socket.create_connection(
                (greentest.DEFAULT_BIND_ADDR, connect_port),
                timeout=30,
                **conn_args
            )

    def test_refuses_from_port(self):
        source_port = support.find_unused_port()
        # Usually we don't want to bind/connect to '', but
        # using it as the source is required if we don't want to hang,
        # at least on some systems (OS X)
        self.test_refuses(source_address=('', source_port))


    @greentest.ignores_leakcheck
    @skipWithoutExternalNetwork("Tries to resolve hostname")
    def test_base_exception(self):
        # such as a GreenletExit or a gevent.timeout.Timeout

        class E(BaseException):
            pass

        class MockSocket(object):

            created = ()
            closed = False

            def __init__(self, *_):
                MockSocket.created += (self,)

            def connect(self, _):
                raise E(_)

            def close(self):
                self.closed = True

        def mockgetaddrinfo(*_):
            return [(1, 2, 3, 3, 5),]

        import gevent.socket as gsocket
        # Make sure we're monkey patched
        self.assertEqual(gsocket.create_connection, socket.create_connection)
        orig_socket = gsocket.socket
        orig_getaddrinfo = gsocket.getaddrinfo

        try:
            gsocket.socket = MockSocket
            gsocket.getaddrinfo = mockgetaddrinfo

            with self.assertRaises(E):
                socket.create_connection(('host', 'port'))

            self.assertEqual(1, len(MockSocket.created))
            self.assertTrue(MockSocket.created[0].closed)

        finally:
            MockSocket.created = ()
            gsocket.socket = orig_socket
            gsocket.getaddrinfo = orig_getaddrinfo

class TestFunctions(greentest.TestCase):

    @greentest.ignores_leakcheck
    # Creating new types in the function takes a cycle to cleanup.
    def test_wait_timeout(self):
        # Issue #635
        from gevent import socket as gsocket
        class io(object):
            callback = None

            def start(self, *_args):
                gevent.sleep(10)

        with self.assertRaises(gsocket.timeout):
            gsocket.wait(io(), timeout=0.01) # pylint:disable=no-member


    def test_signatures(self):
        # https://github.com/gevent/gevent/issues/960
        exclude = []
        if greentest.PYPY:
            # Up through at least PyPy 5.7.1, they define these as
            # gethostbyname(host), whereas the official CPython argument name
            # is hostname. But cpython doesn't allow calling with keyword args.
            # Likewise for gethostbyaddr: PyPy uses host, cpython uses ip_address
            exclude.append('gethostbyname')
            exclude.append('gethostbyname_ex')
            exclude.append('gethostbyaddr')
        if sys.version_info[:2] < (3, 11):
            # 3.11+ add ``*, all_errors=False``. We allow that on all versions,
            # forcing it to a false value if the user sends a true value before
            # exception groups exist.
            exclude.append('create_connection')
        self.assertMonkeyPatchedFuncSignatures('socket', exclude=exclude)

    def test_resolve_ipv6_scope_id(self):
        from gevent import _socketcommon as SC
        if not SC.__socket__.has_ipv6:
            self.skipTest("Needs IPv6") # pragma: no cover
        if not hasattr(SC.__socket__, 'inet_pton'):
            self.skipTest("Needs inet_pton") # pragma: no cover

        # A valid IPv6 address, with a scope.
        addr = ('2607:f8b0:4000:80e::200e', 80, 0, 9)
        # Mock socket
        class sock(object):
            family = SC.AF_INET6 # pylint:disable=no-member
        self.assertIs(addr, SC._resolve_addr(sock, addr))

class TestSocket(greentest.TestCase):

    def test_shutdown_when_closed(self):
        # https://github.com/gevent/gevent/issues/1089
        # we once raised an AttributeError.
        s = socket.socket()
        s.close()
        with self.assertRaises(socket.error):
            s.shutdown(socket.SHUT_RDWR)

    def test_can_be_weak_ref(self):
        # stdlib socket can be weak reffed.
        import weakref
        s = socket.socket()
        try:
            w = weakref.ref(s)
            self.assertIsNotNone(w)
        finally:
            s.close()

    def test_has_no_dict(self):
        # stdlib socket has no dict
        s = socket.socket()
        try:
            with self.assertRaises(AttributeError):
                getattr(s, '__dict__')
        finally:
            s.close()


if __name__ == '__main__':
    greentest.main()
