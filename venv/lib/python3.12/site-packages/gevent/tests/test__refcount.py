# Copyright (c) 2008 AG Projects
# Author: Denis Bilenko
#
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

"""This test checks that underlying socket instances (gevent.socket.socket._sock)
are not leaked by the hub.
"""
from __future__ import print_function

from _socket import socket as c_socket
import sys
if sys.version_info[0] >= 3:
    # Python3 enforces that __weakref__ appears only once,
    # and not when a slotted class inherits from an unslotted class.
    # We mess around with the class MRO below and violate that rule
    # (because socket.socket defines __slots__ with __weakref__),
    # so import socket.socket before that can happen.
    __import__('socket')
    Socket = c_socket
else:
    class Socket(c_socket):
        "Something we can have a weakref to"

import _socket
_socket.socket = Socket


from gevent import monkey; monkey.patch_all()

import gevent.testing as greentest
from gevent.testing import support
from gevent.testing import params


try:
    from thread import start_new_thread
except ImportError:
    from _thread import start_new_thread
from time import sleep
import weakref
import gc

import socket
socket._realsocket = Socket

SOCKET_TIMEOUT = 0.1
if greentest.RESOLVER_DNSPYTHON:
    # Takes a bit longer to resolve the client
    # address initially.
    SOCKET_TIMEOUT *= 2

if greentest.RUNNING_ON_CI:
    SOCKET_TIMEOUT *= 2


class Server(object):

    listening = False
    client_data = None
    server_port = None

    def __init__(self, raise_on_timeout):
        self.raise_on_timeout = raise_on_timeout
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.server_port = support.bind_port(self.socket, params.DEFAULT_BIND_ADDR)
        except:
            self.close()
            raise

    def close(self):
        self.socket.close()
        self.socket = None

    def handle_request(self):
        try:
            self.socket.settimeout(SOCKET_TIMEOUT)

            self.socket.listen(5)

            self.listening = True

            try:
                conn, _ = self.socket.accept() # pylint:disable=no-member
            except socket.timeout:
                if self.raise_on_timeout:
                    raise
                return

            try:
                self.client_data = conn.recv(100)
                conn.send(b'bye')
            finally:
                conn.close()
        finally:
            self.close()


class Client(object):

    server_data = None

    def __init__(self, server_port):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_port = server_port


    def close(self):
        self.socket.close()
        self.socket = None

    def make_request(self):
        try:
            self.socket.connect((params.DEFAULT_CONNECT, self.server_port))
            self.socket.send(b'hello')
            self.server_data = self.socket.recv(100)
        finally:
            self.close()


class Test(greentest.TestCase):
    __timeout__ = greentest.LARGE_TIMEOUT

    def run_interaction(self, run_client):
        server = Server(raise_on_timeout=run_client)
        wref_to_hidden_server_socket = weakref.ref(server.socket._sock)
        client = None
        start_new_thread(server.handle_request)
        if run_client:
            client = Client(server.server_port)
            start_new_thread(client.make_request)

        # Wait until we do our business; we will always close
        # the server; We may also close the client.
        # On PyPy, we may not actually see the changes they write to
        # their dicts immediately.
        for obj in server, client:
            if obj is None:
                continue
            while obj.socket is not None:
                sleep(0.01)

        # If we have a client, then we should have data
        if run_client:
            self.assertEqual(server.client_data, b'hello')
            self.assertEqual(client.server_data, b'bye')

        return wref_to_hidden_server_socket

    def run_and_check(self, run_client):
        wref_to_hidden_server_socket = self.run_interaction(run_client=run_client)
        greentest.gc_collect_if_needed()
        if wref_to_hidden_server_socket():
            from pprint import pformat
            print(pformat(gc.get_referrers(wref_to_hidden_server_socket())))
            for x in gc.get_referrers(wref_to_hidden_server_socket()):
                print(pformat(x))
                for y in gc.get_referrers(x):
                    print('-', pformat(y))
            self.fail('server socket should be dead by now')

    def test_clean_exit(self):
        self.run_and_check(True)
        self.run_and_check(True)

    def test_timeout_exit(self):
        self.run_and_check(False)
        self.run_and_check(False)


if __name__ == '__main__':
    greentest.main()
