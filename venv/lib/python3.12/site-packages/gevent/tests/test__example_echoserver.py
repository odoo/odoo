from gevent.socket import create_connection, timeout
import gevent.testing as greentest
import gevent

from gevent.testing import util
from gevent.testing import params

class Test(util.TestServer):
    example = 'echoserver.py'

    def _run_all_tests(self):
        def test_client(message):
            if greentest.PY3:
                kwargs = {'buffering': 1}
            else:
                kwargs = {'bufsize': 1}
            kwargs['mode'] = 'rb'
            conn = create_connection((params.DEFAULT_LOCAL_HOST_ADDR, 16000))
            conn.settimeout(greentest.DEFAULT_XPC_SOCKET_TIMEOUT)
            rfile = conn.makefile(**kwargs)

            welcome = rfile.readline()
            self.assertIn(b'Welcome', welcome)

            conn.sendall(message)
            received = rfile.read(len(message))
            self.assertEqual(received, message)

            self.assertRaises(timeout, conn.recv, 1)

            rfile.close()
            conn.close()

        client1 = gevent.spawn(test_client, b'hello\r\n')
        client2 = gevent.spawn(test_client, b'world\r\n')
        gevent.joinall([client1, client2], raise_error=True)


if __name__ == '__main__':
    greentest.main()
