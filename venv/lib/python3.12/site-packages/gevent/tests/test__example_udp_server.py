import socket

from gevent.testing import util
from gevent.testing import main


class Test(util.TestServer):
    example = 'udp_server.py'

    def _run_all_tests(self):
        sock = socket.socket(type=socket.SOCK_DGRAM)
        try:
            sock.connect(('127.0.0.1', 9000))
            sock.send(b'Test udp_server')
            data, _address = sock.recvfrom(8192)
            self.assertEqual(data, b'Received 15 bytes')
        finally:
            sock.close()


if __name__ == '__main__':
    main()
