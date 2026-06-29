from gevent import monkey; monkey.patch_all()
import socket
import unittest


class TestSocketpair(unittest.TestCase):

    def test_makefile(self):
        msg = b'hello world'
        x, y = socket.socketpair()
        x.sendall(msg)
        x.close()
        with y.makefile('rb') as f:
            read = f.read()
        self.assertEqual(msg, read)
        y.close()

    @unittest.skipUnless(hasattr(socket, 'fromfd'),
                         'Needs socket.fromfd')
    def test_fromfd(self):
        msg = b'hello world'
        x, y = socket.socketpair()
        xx = socket.fromfd(x.fileno(), x.family, socket.SOCK_STREAM)
        x.close()
        yy = socket.fromfd(y.fileno(), y.family, socket.SOCK_STREAM)
        y.close()

        xx.sendall(msg)
        xx.close()
        with yy.makefile('rb') as f:
            read = f.read()
        self.assertEqual(msg, read)
        yy.close()


if __name__ == '__main__':
    unittest.main()
