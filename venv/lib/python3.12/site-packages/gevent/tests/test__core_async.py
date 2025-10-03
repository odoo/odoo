from __future__ import print_function
import gevent
import gevent.core
import time
try:
    import thread
except ImportError:
    import _thread as thread

from gevent import testing as greentest

class Test(greentest.TestCase):
    def test(self):
        hub = gevent.get_hub()
        watcher = hub.loop.async_()

        # BWC for <3.7: This should still be an attribute
        assert hasattr(hub.loop, 'async')

        gevent.spawn_later(0.1, thread.start_new_thread, watcher.send, ())

        start = time.time()

        with gevent.Timeout(1.0): # Large timeout for appveyor
            hub.wait(watcher)

        print('Watcher %r reacted after %.6f seconds' % (watcher, time.time() - start - 0.1))


if __name__ == '__main__':
    greentest.main()
