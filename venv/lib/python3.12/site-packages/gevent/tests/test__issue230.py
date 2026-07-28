import gevent.monkey
gevent.monkey.patch_all()

import socket
import multiprocessing

from gevent import testing as greentest

# Make sure that using the resolver in a forked process
# doesn't hang forever.


def block():
    socket.getaddrinfo('localhost', 8001)



class Test(greentest.TestCase):
    def test(self):
        socket.getaddrinfo('localhost', 8001)

        p = multiprocessing.Process(target=block)
        p.start()
        p.join()

if __name__ == '__main__':
    greentest.main()
