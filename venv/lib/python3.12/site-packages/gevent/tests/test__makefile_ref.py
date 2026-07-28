from __future__ import print_function
import os
from gevent import monkey; monkey.patch_all()
import socket
import ssl
import threading
import errno
import weakref


import gevent.testing as greentest
from gevent.testing.params import DEFAULT_BIND_ADDR_TUPLE
from gevent.testing.params import DEFAULT_CONNECT
from gevent.testing.sockets import tcp_listener

dirname = os.path.dirname(os.path.abspath(__file__))
CERTFILE = os.path.join(dirname, '2_7_keycert.pem')
pid = os.getpid()

PY3 = greentest.PY3
PYPY = greentest.PYPY
CPYTHON = not PYPY
PY2 = not PY3
fd_types = int
if PY3:
    long = int
fd_types = (int, long)
WIN = greentest.WIN

from gevent.testing import get_open_files
try:
    import psutil
except ImportError:
    psutil = None

# wrap_socket() is considered deprecated in 3.9
# pylint:disable=deprecated-method

class Test(greentest.TestCase):

    extra_allowed_open_states = ()

    def tearDown(self):
        self.extra_allowed_open_states = ()
        super(Test, self).tearDown()

    def assert_raises_EBADF(self, func):
        try:
            result = func()
        except OSError as ex:
            # Windows/Py3 raises "OSError: [WinError 10038]"
            if ex.args[0] == errno.EBADF:
                return
            if WIN and ex.args[0] == 10038:
                return
            raise
        raise AssertionError('NOT RAISED EBADF: %r() returned %r' % (func, result))

    if WIN or (PYPY and greentest.LINUX):
        def __assert_fd_open(self, fileno):
            # We can't detect open file descriptors on Windows.
            # On PyPy 3.6-7.3 on Travis CI (linux), for some reason the
            # client file descriptors don't always show as open. Don't know why,
            # was fine in 7.2.
            # On March 23 2020 we had to pin psutil back to a version
            # for PyPy 2 (see setup.py) and this same problem started happening there.
            # PyPy on macOS was unaffected.
            pass
    else:
        def __assert_fd_open(self, fileno):
            assert isinstance(fileno, fd_types)
            open_files = get_open_files()
            if fileno not in open_files:
                raise AssertionError('%r is not open:\n%s' % (fileno, open_files['data']))

    def assert_fd_closed(self, fileno):
        assert isinstance(fileno, fd_types), repr(fileno)
        assert fileno > 0, fileno
        # Here, if we're in the process of closing, don't consider it open.
        # This goes into details of psutil
        open_files = get_open_files(count_closing_as_open=False)
        if fileno in open_files:
            raise AssertionError('%r is not closed:\n%s' % (fileno, open_files['data']))

    def _assert_sock_open(self, sock):
        # requires the psutil output
        open_files = get_open_files()
        sockname = sock.getsockname()
        for x in open_files['data']:
            if getattr(x, 'laddr', None) == sockname:
                assert x.status in (psutil.CONN_LISTEN, psutil.CONN_ESTABLISHED) + self.extra_allowed_open_states, x.status
                return
        raise AssertionError("%r is not open:\n%s" % (sock, open_files['data']))

    def assert_open(self, sock, *rest):
        if isinstance(sock, fd_types):
            self.__assert_fd_open(sock)
        else:
            fileno = sock.fileno()
            assert isinstance(fileno, fd_types), fileno
            sockname = sock.getsockname()
            assert isinstance(sockname, tuple), sockname
            if not WIN:
                self.__assert_fd_open(fileno)
            else:
                self._assert_sock_open(sock)
        if rest:
            self.assert_open(rest[0], *rest[1:])

    def assert_closed(self, sock, *rest):
        if isinstance(sock, fd_types):
            self.assert_fd_closed(sock)
        else:
            # Under Python3, the socket module returns -1 for a fileno
            # of a closed socket; under Py2 it raises
            if PY3:
                self.assertEqual(sock.fileno(), -1)
            else:
                self.assert_raises_EBADF(sock.fileno)
            self.assert_raises_EBADF(sock.getsockname)
            self.assert_raises_EBADF(sock.accept)
        if rest:
            self.assert_closed(rest[0], *rest[1:])

    def make_open_socket(self):
        s = socket.socket()
        try:
            s.bind(DEFAULT_BIND_ADDR_TUPLE)
            if WIN or greentest.LINUX:
                # Windows and linux (with psutil) doesn't show as open until
                # we call listen (linux with lsof accepts either)
                s.listen(1)
            self.assert_open(s, s.fileno())
        except:
            s.close()
            s = None
            raise
        return s

# Sometimes its this one, sometimes it's test_ssl. No clue why or how.
@greentest.skipOnAppVeyor("This sometimes times out for no apparent reason.")
class TestSocket(Test):

    def test_simple_close(self):
        with Closing() as closer:
            s = closer(self.make_open_socket())
            fileno = s.fileno()
            s.close()
        self.assert_closed(s, fileno)

    def test_makefile1(self):
        with Closing() as closer:
            s = closer(self.make_open_socket())
            fileno = s.fileno()
            f = closer(s.makefile())

            self.assert_open(s, fileno)
            # Under python 2, this closes socket wrapper object but not the file descriptor;
            # under python 3, both stay open
            s.close()
            if PY3:
                self.assert_open(s, fileno)
            else:
                self.assert_closed(s)
                self.assert_open(fileno)
            f.close()
            self.assert_closed(s)
            self.assert_closed(fileno)

    def test_makefile2(self):
        with Closing() as closer:
            s = closer(self.make_open_socket())
            fileno = s.fileno()
            self.assert_open(s, fileno)
            f = closer(s.makefile())
            self.assert_open(s)
            self.assert_open(s, fileno)
            f.close()
            # closing fileobject does not close the socket
            self.assert_open(s, fileno)
            s.close()
            self.assert_closed(s, fileno)

    def test_server_simple(self):
        with Closing() as closer:
            listener = closer(tcp_listener(backlog=1))
            port = listener.getsockname()[1]

            connector = closer(socket.socket())

            def connect():
                connector.connect((DEFAULT_CONNECT, port))

            closer.running_task(threading.Thread(target=connect))

            client_socket = closer.accept(listener)
            fileno = client_socket.fileno()
            self.assert_open(client_socket, fileno)
            client_socket.close()
            self.assert_closed(client_socket)

    def test_server_makefile1(self):
        with Closing() as closer:
            listener = closer(tcp_listener(backlog=1))
            port = listener.getsockname()[1]

            connector = closer(socket.socket())

            def connect():
                connector.connect((DEFAULT_CONNECT, port))

            closer.running_task(threading.Thread(target=connect))


            client_socket = closer.accept(listener)
            fileno = client_socket.fileno()
            f = closer(client_socket.makefile())
            self.assert_open(client_socket, fileno)
            client_socket.close()
            # Under python 2, this closes socket wrapper object but not the file descriptor;
            # under python 3, both stay open
            if PY3:
                self.assert_open(client_socket, fileno)
            else:
                self.assert_closed(client_socket)
                self.assert_open(fileno)
            f.close()
            self.assert_closed(client_socket, fileno)

    def test_server_makefile2(self):
        with Closing() as closer:
            listener = closer(tcp_listener(backlog=1))
            port = listener.getsockname()[1]

            connector = closer(socket.socket())

            def connect():
                connector.connect((DEFAULT_CONNECT, port))

            closer.running_task(threading.Thread(target=connect))
            client_socket = closer.accept(listener)

            fileno = client_socket.fileno()
            f = closer(client_socket.makefile())
            self.assert_open(client_socket, fileno)
            # closing fileobject does not close the socket
            f.close()
            self.assert_open(client_socket, fileno)
            client_socket.close()
            self.assert_closed(client_socket, fileno)


@greentest.skipOnAppVeyor("This sometimes times out for no apparent reason.")
class TestSSL(Test):

    def _ssl_connect_task(self, connector, port, accepted_event):
        connector.connect((DEFAULT_CONNECT, port))

        try:
            # Note: We get ResourceWarning about 'x'
            # on Python 3 if we don't join the spawned thread
            x = ssl.SSLContext().wrap_socket(connector)
            # Wait to be fully accepted. We could otherwise raise ahead
            # of the server and close ourself before it's ready to read.
            accepted_event.wait()
        except socket.error:
            # Observed on Windows with PyPy2 5.9.0 and libuv:
            # if we don't switch in a timely enough fashion,
            # the server side runs ahead of us and closes
            # our socket first, so this fails.
            pass
        else:
            x.close()

    def _make_ssl_connect_task(self, connector, port):
        accepted_event = threading.Event()
        t = threading.Thread(target=self._ssl_connect_task,
                             args=(connector, port, accepted_event))
        t.daemon = True
        t.accepted_event = accepted_event
        return t

    def test_simple_close(self):
        with Closing() as closer:
            s = closer(self.make_open_socket())
            fileno = s.fileno()
            s = closer(ssl.SSLContext().wrap_socket(s))
            fileno = s.fileno()
            self.assert_open(s, fileno)
            s.close()
            self.assert_closed(s, fileno)

    def test_makefile1(self):
        with Closing() as closer:
            raw_s = closer(self.make_open_socket())
            s = closer(ssl.SSLContext().wrap_socket(raw_s))

            fileno = s.fileno()
            self.assert_open(s, fileno)
            f = closer(s.makefile())
            self.assert_open(s, fileno)
            s.close()
            self.assert_open(s, fileno)
            f.close()
            raw_s.close()
            self.assert_closed(s, fileno)

    def test_makefile2(self):
        with Closing() as closer:
            s = closer(self.make_open_socket())
            fileno = s.fileno()

            s = closer(ssl.SSLContext().wrap_socket(s))
            fileno = s.fileno()
            self.assert_open(s, fileno)
            f = closer(s.makefile())
            self.assert_open(s, fileno)
            f.close()
            # closing fileobject does not close the socket
            self.assert_open(s, fileno)
            s.close()
            self.assert_closed(s, fileno)

    def _wrap_socket(self, sock, *, keyfile, certfile, server_side=False):
        context = ssl.SSLContext()
        context.load_cert_chain(certfile=certfile, keyfile=keyfile)
        return context.wrap_socket(sock, server_side=server_side)

    def test_server_simple(self):
        with Closing() as closer:
            listener = closer(tcp_listener(backlog=1))
            port = listener.getsockname()[1]

            connector = closer(socket.socket())

            t = self._make_ssl_connect_task(connector, port)
            closer.running_task(t)

            client_socket = closer.accept(listener)
            t.accepted_event.set()
            client_socket = closer(
                self._wrap_socket(client_socket, keyfile=CERTFILE, certfile=CERTFILE,
                                  server_side=True))
            fileno = client_socket.fileno()
            self.assert_open(client_socket, fileno)
            client_socket.close()
            self.assert_closed(client_socket, fileno)

    def test_server_makefile1(self):
        with Closing() as closer:
            listener = closer(tcp_listener(backlog=1))
            port = listener.getsockname()[1]

            connector = closer(socket.socket())

            t = self._make_ssl_connect_task(connector, port)
            closer.running_task(t)

            client_socket = closer.accept(listener)
            t.accepted_event.set()
            client_socket = closer(
                self._wrap_socket(client_socket, keyfile=CERTFILE, certfile=CERTFILE,
                                  server_side=True))
            fileno = client_socket.fileno()
            self.assert_open(client_socket, fileno)
            f = client_socket.makefile()
            self.assert_open(client_socket, fileno)
            client_socket.close()
            self.assert_open(client_socket, fileno)
            f.close()
            self.assert_closed(client_socket, fileno)

    def test_server_makefile2(self):
        with Closing() as closer:
            listener = closer(tcp_listener(backlog=1))
            port = listener.getsockname()[1]

            connector = closer(socket.socket())
            t = self._make_ssl_connect_task(connector, port)
            closer.running_task(t)

            t.accepted_event.set()
            client_socket = closer.accept(listener)
            client_socket = closer(
                self._wrap_socket(client_socket, keyfile=CERTFILE, certfile=CERTFILE,
                                  server_side=True))

            fileno = client_socket.fileno()
            self.assert_open(client_socket, fileno)
            f = client_socket.makefile()
            self.assert_open(client_socket, fileno)
            # Closing fileobject does not close SSLObject
            f.close()
            self.assert_open(client_socket, fileno)
            client_socket.close()
            self.assert_closed(client_socket, fileno)

    def test_serverssl_makefile1(self):
        raw_listener = tcp_listener(backlog=1)
        fileno = raw_listener.fileno()
        port = raw_listener.getsockname()[1]
        listener = self._wrap_socket(raw_listener, keyfile=CERTFILE, certfile=CERTFILE)

        connector = socket.socket()
        t = self._make_ssl_connect_task(connector, port)
        t.start()

        with CleaningUp(t, listener, raw_listener, connector) as client_socket:
            t.accepted_event.set()
            fileno = client_socket.fileno()
            self.assert_open(client_socket, fileno)
            f = client_socket.makefile()
            self.assert_open(client_socket, fileno)
            client_socket.close()
            self.assert_open(client_socket, fileno)
            f.close()
            self.assert_closed(client_socket, fileno)

    def test_serverssl_makefile2(self):
        raw_listener = tcp_listener(backlog=1)
        port = raw_listener.getsockname()[1]
        listener = self._wrap_socket(raw_listener, keyfile=CERTFILE, certfile=CERTFILE)

        accepted_event = threading.Event()
        def connect(connector=socket.socket()):
            try:
                connector.connect((DEFAULT_CONNECT, port))
                s = ssl.SSLContext().wrap_socket(connector)
                accepted_event.wait()
                s.sendall(b'test_serverssl_makefile2')
                s.shutdown(socket.SHUT_RDWR)
                s.close()
            finally:
                connector.close()

        t = threading.Thread(target=connect)
        t.daemon = True
        t.start()
        client_socket = None
        with CleaningUp(t, listener, raw_listener) as client_socket:
            accepted_event.set()
            fileno = client_socket.fileno()
            self.assert_open(client_socket, fileno)
            f = client_socket.makefile()
            self.assert_open(client_socket, fileno)
            self.assertEqual(f.read(), 'test_serverssl_makefile2')
            self.assertEqual(f.read(), '')
            # Closing file object does not close the socket.
            f.close()
            if WIN and psutil:
                # Hmm?
                self.extra_allowed_open_states = (psutil.CONN_CLOSE_WAIT,)

            self.assert_open(client_socket, fileno)
            client_socket.close()
            self.assert_closed(client_socket, fileno)


class Closing(object):

    def __init__(self, *init):
        self._objects = []
        for i in init:
            self.closing(i)
        self.task = None

    def accept(self, listener):
        client_socket, _addr = listener.accept()
        return self.closing(client_socket)

    def __enter__(self):
        o = self.objects()
        if len(o) == 1:
            return o[0]
        return self

    if PY2 and CPYTHON:
        # This implementation depends or refcounting
        # for things to close. Eww.
        def closing(self, o):
            self._objects.append(weakref.ref(o))
            return o
        def objects(self):
            return [r() for r in self._objects if r() is not None]

    else:
        def objects(self):
            # PyPy returns an object without __len__...
            return list(reversed(self._objects))

        def closing(self, o):
            self._objects.append(o)
            return o

    __call__ = closing

    def running_task(self, thread):
        assert self.task is None
        self.task = thread
        self.task.start()
        return self.task

    def __exit__(self, t, v, tb):
        # workaround for test_server_makefile1, test_server_makefile2,
        # test_server_simple, test_serverssl_makefile1.

        # On PyPy on Linux, it is important to join the SSL Connect
        # Task FIRST, before closing the sockets. If we do it after
        # (which makes more sense) we hang. It's not clear why, except
        # that it has something to do with context switches. Inserting a call to
        # gevent.sleep(0.1) instead of joining the task has the same
        # effect. If the previous tests hang, then later tests can fail with
        # SSLError: unknown alert type.

        # XXX: Why do those two things happen?

        # On PyPy on macOS, we don't have that problem and can use the
        # more logical order.
        try:
            if self.task is not None:
                self.task.join()
        finally:
            self.task = None
            for o in self.objects():
                try:
                    o.close()
                except Exception: # pylint:disable=broad-except
                    pass

        self._objects = ()

class CleaningUp(Closing):

    def __init__(self, task, listener, *other_sockets):
        super(CleaningUp, self).__init__(listener, *other_sockets)
        self.task = task
        self.listener = listener

    def __enter__(self):
        return self.accept(self.listener)

    def __exit__(self, t, v, tb):
        try:
            Closing.__exit__(self, t, v, tb)
        finally:
            self.listener = None



if __name__ == '__main__':
    greentest.main()
