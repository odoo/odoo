from __future__ import print_function
from __future__ import absolute_import

import gevent
from gevent import socket
from gevent import backdoor

import gevent.testing as greentest
from gevent.testing.params import DEFAULT_BIND_ADDR_TUPLE
from gevent.testing.params import DEFAULT_CONNECT

def read_until(conn, postfix):
    read = b''
    assert isinstance(postfix, bytes)

    while not read.endswith(postfix):
        result = conn.recv(1)
        if not result:
            raise AssertionError('Connection ended before %r. Data read:\n%r' % (postfix, read))
        read += result

    return read if isinstance(read, str) else read.decode('utf-8')

def readline(conn):
    with conn.makefile() as f:
        return f.readline()


class WorkerGreenlet(gevent.Greenlet):
    spawning_stack_limit = 2

class SocketWithBanner(socket.socket):
    __slots__ = ('banner',)

    def __init__(self, *args, **kwargs):
        self.banner = None
        super(SocketWithBanner, self).__init__(*args, **kwargs)

    def __enter__(self):
        return socket.socket.__enter__(self)

    def __exit__(self, t, v, tb):
        return socket.socket.__exit__(self, t, v, tb)


@greentest.skipOnAppVeyor(
    "With the update to libev 4.31 and potentially closing sockets in the background, "
    "alternate tests started hanging on appveyor. Something like .E.E.E. "
    "See https://ci.appveyor.com/project/denik/gevent/build/job/n9fynkoyt2bvk8b5 "
    "It's not clear why, but presumably a socket isn't getting closed and a watcher is tied "
    "to the wrong file descriptor. I haven't been able to reproduce. If it were a systemic "
    "problem I'd expect to see more failures, so it is probably specific to resource management "
    "in this test."
)
class Test(greentest.TestCase):

    __timeout__ = 10

    def tearDown(self):
        gevent.sleep() # let spawned greenlets die
        super(Test, self).tearDown()

    def _make_and_start_server(self, *args, **kwargs):
        server = backdoor.BackdoorServer(DEFAULT_BIND_ADDR_TUPLE, *args, **kwargs)
        server.start()
        return server

    def _create_connection(self, server):
        conn = SocketWithBanner()
        conn.connect((DEFAULT_CONNECT, server.server_port))
        try:
            banner = self._wait_for_prompt(conn)
        except:
            conn.close()
            raise
        else:
            conn.banner = banner
        return conn

    def _wait_for_prompt(self, conn):
        return read_until(conn, b'>>> ')

    def _close(self, conn, cmd=b'quit()\r\n)'):
        conn.sendall(cmd)
        line = readline(conn)
        self.assertEqual(line, '')
        conn.close()

    @greentest.skipOnMacOnCI(
        "Sometimes fails to get the right answers; "
        "https://travis-ci.org/github/gevent/gevent/jobs/692184822"
    )
    @greentest.skipOnLibuvOnTravisOnCPython27(
        "segfaults; "
        "See https://github.com/gevent/gevent/pull/1156")
    def test_multi(self):
        with self._make_and_start_server() as server:
            def connect():
                with self._create_connection(server) as conn:
                    conn.sendall(b'2+2\r\n')
                    line = readline(conn)
                    self.assertEqual(line.strip(), '4', repr(line))
                    self._close(conn)

            jobs = [WorkerGreenlet.spawn(connect) for _ in range(10)]
            try:
                done = gevent.joinall(jobs, raise_error=True)
            finally:
                gevent.joinall(jobs, raise_error=False)

            self.assertEqual(len(done), len(jobs), done)

    def test_quit(self):
        with self._make_and_start_server() as server:
            with self._create_connection(server) as conn:
                self._close(conn)

    def test_sys_exit(self):
        with self._make_and_start_server() as server:
            with self._create_connection(server) as conn:
                self._close(conn, b'import sys; sys.exit(0)\r\n')

    def test_banner(self):
        expected_banner = "Welcome stranger!" # native string
        with self._make_and_start_server(banner=expected_banner) as server:
            with self._create_connection(server) as conn:
                banner = conn.banner
                self._close(conn)

        self.assertEqual(banner[:len(expected_banner)], expected_banner, banner)


    def test_builtins(self):
        with self._make_and_start_server() as server:
            with self._create_connection(server) as conn:
                conn.sendall(b'locals()["__builtins__"]\r\n')
                response = read_until(conn, b'>>> ')
                self._close(conn)

        self.assertLess(
            len(response), 300,
            msg="locals() unusable: %s..." % response)

    def test_switch_exc(self):
        from gevent.queue import Queue, Empty

        def bad():
            q = Queue()
            print('switching out, then throwing in')
            try:
                q.get(block=True, timeout=0.1)
            except Empty:
                print("Got Empty")
            print('switching out')
            gevent.sleep(0.1)
            print('switched in')

        with self._make_and_start_server(locals={'bad': bad}) as server:
            with self._create_connection(server) as conn:
                conn.sendall(b'bad()\r\n')
                response = self._wait_for_prompt(conn)
                self._close(conn)

        response = response.replace('\r\n', '\n')
        self.assertEqual(
            'switching out, then throwing in\nGot Empty\nswitching out\nswitched in\n>>> ',
            response)


if __name__ == '__main__':
    greentest.main() # pragma: testrunner-no-combine
