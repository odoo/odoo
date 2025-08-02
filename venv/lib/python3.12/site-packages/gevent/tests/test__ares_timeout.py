from __future__ import print_function

import unittest

import gevent
try:
    from gevent.resolver.ares import Resolver
except ImportError as ex:
    Resolver = None
from gevent import socket

import gevent.testing as greentest
from gevent.testing.sockets import udp_listener

@unittest.skipIf(
    Resolver is None,
    "Needs ares resolver"
)
class TestTimeout(greentest.TestCase):

    __timeout__ = 30

    def test(self):
        listener = self._close_on_teardown(udp_listener())
        address = listener.getsockname()


        def reader():
            while True:
                listener.recvfrom(10000)

        greader = gevent.spawn(reader)
        self._close_on_teardown(greader.kill)

        r = Resolver(servers=[address[0]], timeout=0.001, tries=1,
                     udp_port=address[-1])
        self._close_on_teardown(r)

        with self.assertRaisesRegex(socket.herror, "ARES_ETIMEOUT"):
            r.gethostbyname('www.google.com')


if __name__ == '__main__':
    greentest.main()
