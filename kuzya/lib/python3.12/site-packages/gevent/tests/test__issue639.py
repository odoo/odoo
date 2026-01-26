# Test idle
import gevent

from gevent import testing as greentest

class Test(greentest.TestCase):
    def test(self):
        gevent.sleep()
        gevent.idle()

if __name__ == '__main__':
    greentest.main()
