import gevent
import gevent.testing as greentest
from gevent.testing.six import xrange


class appender(object):

    def __init__(self, lst, item):
        self.lst = lst
        self.item = item

    def __call__(self, *args):
        self.lst.append(self.item)


class Test(greentest.TestCase):

    count = 2

    def test_greenlet_link(self):
        lst = []

        # test that links are executed in the same order as they were added
        g = gevent.spawn(lst.append, 0)

        for i in xrange(1, self.count):
            g.link(appender(lst, i))
        g.join()
        self.assertEqual(lst, list(range(self.count)))


class Test3(Test):
    count = 3


class Test4(Test):
    count = 4


class TestM(Test):
    count = 1000


class TestSleep0(greentest.TestCase):

    def test(self):
        lst = []
        gevent.spawn(sleep0, lst, '1')
        gevent.spawn(sleep0, lst, '2')
        gevent.wait()
        self.assertEqual(' '.join(lst), '1A 2A 1B 2B')


def sleep0(lst, param):
    lst.append(param + 'A')
    gevent.sleep(0)
    lst.append(param + 'B')


if __name__ == '__main__':
    greentest.main()
