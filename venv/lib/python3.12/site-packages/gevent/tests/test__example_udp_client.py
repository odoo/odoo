from gevent import monkey
monkey.patch_all()


from gevent.server import DatagramServer

from gevent.testing import util
from gevent.testing import main

class Test_udp_client(util.TestServer):

    start_kwargs = {'timeout': 10}
    example = 'udp_client.py'
    example_args = ['Test_udp_client']

    def test(self):
        log = []

        def handle(message, address):
            log.append(message)
            server.sendto(b'reply-from-server', address)

        server = DatagramServer('127.0.0.1:9001', handle)
        server.start()
        try:
            self.run_example()
        finally:
            server.close()
        self.assertEqual(log, [b'Test_udp_client'])


if __name__ == '__main__':
    # Running this following test__example_portforwarder on Appveyor
    # doesn't work in the same process for some reason.
    main() # pragma: testrunner-no-combine
