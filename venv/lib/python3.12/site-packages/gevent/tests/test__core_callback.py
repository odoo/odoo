import gevent
from gevent.hub import get_hub

from gevent import testing as greentest

class Test(greentest.TestCase):

    def test(self):
        loop = get_hub().loop
        called = []

        def f():
            called.append(1)

        x = loop.run_callback(f)

        assert x, x
        gevent.sleep(0)
        assert called == [1], called
        assert not x, (x, bool(x))

        x = loop.run_callback(f)
        assert x, x
        x.stop()
        assert not x, x
        gevent.sleep(0)
        assert called == [1], called
        assert not x, x


if __name__ == '__main__':
    greentest.main()
