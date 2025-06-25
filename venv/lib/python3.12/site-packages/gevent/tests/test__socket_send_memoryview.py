# See issue #466
import unittest
import ctypes

import gevent.testing as greentest

class AnStructure(ctypes.Structure):
    _fields_ = [("x", ctypes.c_int)]


def _send(socket):
    for meth in ('sendall', 'send'):
        anStructure = AnStructure()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect((greentest.DEFAULT_CONNECT_HOST, 12345))
        getattr(sock, meth)(anStructure)
        sock.close()

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect((greentest.DEFAULT_CONNECT_HOST, 12345))
        sock.settimeout(1.0)
        getattr(sock, meth)(anStructure)
        sock.close()

class TestSendBuiltinSocket(unittest.TestCase):

    def test_send(self):
        import socket
        _send(socket)


class TestSendGeventSocket(unittest.TestCase):

    def test_send(self):
        import gevent.socket
        _send(gevent.socket)


if __name__ == '__main__':
    greentest.main()
