from __future__ import print_function
import gevent

import unittest

class TestDestroyDefaultLoop(unittest.TestCase):

    def tearDown(self):
        self._reset_hub()
        super(TestDestroyDefaultLoop, self).tearDown()

    def _reset_hub(self):
        from gevent._hub_local import set_hub
        from gevent._hub_local import set_loop
        from gevent._hub_local import get_hub_if_exists
        hub = get_hub_if_exists()
        if hub is not None:
            hub.destroy(destroy_loop=True)
        set_hub(None)
        set_loop(None)

    def test_destroy_gc(self):
        # Issue 1098: destroying the default loop
        # while using the C extension could crash
        # the interpreter when it exits

        # Create the hub greenlet. This creates one loop
        # object pointing to the default loop.
        gevent.get_hub()

        # Get a new loop object, but using the default
        # C loop
        loop = gevent.config.loop(default=True)
        self.assertTrue(loop.default)
        # Destroy it

        loop.destroy()
        # It no longer claims to be the default
        self.assertFalse(loop.default)

        # Delete it
        del loop
        # Delete the hub. This prompts garbage
        # collection of it and its loop object.
        # (making this test more repeatable; the exit
        # crash only happened when that greenlet object
        # was collected at exit time, which was most common
        # in CPython 3.5)
        self._reset_hub()

    def test_destroy_two(self):
        # Get two new loop object, but using the default
        # C loop
        loop1 = gevent.config.loop(default=True)
        loop2 = gevent.config.loop(default=True)
        self.assertTrue(loop1.default)
        self.assertTrue(loop2.default)
        # Destroy the first
        loop1.destroy()
        # It no longer claims to be the default
        self.assertFalse(loop1.default)

        # Destroy the second. This doesn't crash.
        loop2.destroy()
        self.assertFalse(loop2.default)
        self.assertFalse(loop2.ptr)
        self._reset_hub()
        self.assertTrue(gevent.get_hub().loop.ptr)


if __name__ == '__main__':
    unittest.main()
