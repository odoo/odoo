from __future__ import absolute_import, print_function

import gevent
import unittest

class TestDestroyHub(unittest.TestCase):

    def test_destroy_hub(self):
        # Loop of initial Hub is default loop.
        hub = gevent.get_hub()
        self.assertTrue(hub.loop.default)

        # Save `gevent.core.loop` object for later comparison.
        initloop = hub.loop

        # Increase test complexity via threadpool creation.
        # Implicitly creates fork watcher connected to the current event loop.
        tp = hub.threadpool
        self.assertIsNotNone(tp)

        # Destroy hub. Does not destroy libev default loop if not explicitly told to.
        hub.destroy()

        # Create new hub. Must re-use existing libev default loop.
        hub = gevent.get_hub()
        self.assertTrue(hub.loop.default)

        # Ensure that loop object is identical to the initial one.
        self.assertIs(hub.loop, initloop)

        # Destroy hub including default loop.
        hub.destroy(destroy_loop=True)

        # Create new hub and explicitly request creation of a new default loop.
        hub = gevent.get_hub(default=True)
        self.assertTrue(hub.loop.default)

        # `gevent.core.loop` objects as well as libev loop pointers must differ.
        self.assertIsNot(hub.loop, initloop)
        self.assertIsNot(hub.loop.ptr, initloop.ptr)
        self.assertNotEqual(hub.loop.ptr, initloop.ptr)

        # Destroy hub including default loop. The default loop regenerates.
        hub.destroy(destroy_loop=True)
        hub = gevent.get_hub()
        self.assertTrue(hub.loop.default)

        hub.destroy()

if __name__ == '__main__':
    unittest.main() # pragma: testrunner-no-combine
