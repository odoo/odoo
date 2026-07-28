import socket

import gevent.testing as greentest
import gevent
from gevent import pywsgi

from gevent.tests import test__server


def application(environ, start_response):
    if environ['PATH_INFO'] == '/':
        start_response("200 OK", [])
        return [b"PONG"]
    if environ['PATH_INFO'] == '/ping':
        start_response("200 OK", [])
        return [b"PONG"]
    if environ['PATH_INFO'] == '/short':
        gevent.sleep(0.5)
        start_response("200 OK", [])
        return []
    if environ['PATH_INFO'] == '/long':
        gevent.sleep(10)
        start_response("200 OK", [])
        return []

    start_response("404 pywsgi WTF?", [])
    return []


class SimpleWSGIServer(pywsgi.WSGIServer):
    application = staticmethod(application)


internal_error_start = b'HTTP/1.1 500 Internal Server Error\n'.replace(b'\n', b'\r\n')
internal_error_end = b'\n\nInternal Server Error'.replace(b'\n', b'\r\n')

internal_error503 = b'''HTTP/1.1 503 Service Unavailable
Connection: close
Content-type: text/plain
Content-length: 31

Service Temporarily Unavailable'''.replace(b'\n', b'\r\n')


class Settings(test__server.Settings):
    ServerClass = pywsgi.WSGIServer
    ServerSubClass = SimpleWSGIServer
    close_socket_detected = True
    restartable = False
    close_socket_detected = False

    @staticmethod
    def assert500(inst):
        with inst.makefile() as conn:
            conn.write(b'GET / HTTP/1.0\r\n\r\n')
            result = conn.read()
            inst.assertTrue(result.startswith(internal_error_start),
                            (result, internal_error_start))
            inst.assertTrue(result.endswith(internal_error_end),
                            (result, internal_error_end))

    @staticmethod
    def assert503(inst):
        with inst.makefile() as conn:
            conn.write(b'GET / HTTP/1.0\r\n\r\n')
            result = conn.read()
            inst.assertEqual(result, internal_error503)

    @staticmethod
    def assertPoolFull(inst):
        with inst.assertRaises(socket.timeout):
            inst.assertRequestSucceeded()

    @staticmethod
    def assertAcceptedConnectionError(inst):
        with inst.makefile() as conn:
            result = conn.read()
            inst.assertFalse(result)

    @staticmethod
    def fill_default_server_args(inst, kwargs):
        kwargs = test__server.Settings.fill_default_server_args(inst, kwargs)
        kwargs.setdefault('log', pywsgi._NoopLog())
        return kwargs


class TestCase(test__server.TestCase):
    Settings = Settings

class TestDefaultSpawn(test__server.TestDefaultSpawn):
    Settings = Settings

class TestSSLSocketNotAllowed(test__server.TestSSLSocketNotAllowed):
    Settings = Settings

class TestRawSpawn(test__server.TestRawSpawn): # pylint:disable=too-many-ancestors
    Settings = Settings

class TestSSLGetCertificate(test__server.TestSSLGetCertificate):
    Settings = Settings

class TestPoolSpawn(test__server.TestPoolSpawn): # pylint:disable=too-many-ancestors
    Settings = Settings

if __name__ == '__main__':
    greentest.main()
