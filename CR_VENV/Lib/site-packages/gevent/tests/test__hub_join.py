from contextlib import contextmanager
import unittest


import gevent
from gevent.testing import ignores_leakcheck

class TestJoin(unittest.TestCase):

    def test_join_many_times(self):
        # hub.join() guarantees that loop has exited cleanly
        res = gevent.get_hub().join()
        self.assertTrue(res)
        self.assertFalse(gevent.get_hub().dead)

        res = gevent.get_hub().join()
        self.assertTrue(res)

        # but it is still possible to use gevent afterwards
        gevent.sleep(0.01)

        res = gevent.get_hub().join()
        self.assertTrue(res)

    @staticmethod
    def __clean():
        import gc
        for _ in range(2):
            while gc.collect():
                pass

    @contextmanager
    def assert_no_greenlet_growth(self):
        from gevent._greenlet_primitives import get_reachable_greenlets
        clean = self.__clean
        clean()
        count_before = len(get_reachable_greenlets())

        yield

        count_after = len(get_reachable_greenlets())
        if count_after > count_before:
            # We could be off by exactly 1. Not entirely clear where.
            # But it only happens the first time.
            count_after -= 1
        # If we were run in multiple process, our count could actually have
        # gone down due to the GC's we did.
        self.assertEqual(count_after, count_before)

    @ignores_leakcheck
    def test_join_in_new_thread_doesnt_leak_hub_or_greenlet(self):
        # https://github.com/gevent/gevent/issues/1601
        import threading
        clean = self.__clean

        def thread_main():
            g = gevent.Greenlet(run=lambda: 0)
            g.start()
            g.join()
            hub = gevent.get_hub()
            hub.join()
            hub.destroy(destroy_loop=True)
            del hub

        def tester(main):
            t = threading.Thread(target=main)
            t.start()
            t.join()

            clean()

        with self.assert_no_greenlet_growth():
            for _ in range(10):
                tester(thread_main)

            del tester
            del thread_main

    @ignores_leakcheck
    def test_destroy_in_main_thread_from_new_thread(self):
        # https://github.com/gevent/gevent/issues/1631
        import threading

        clean = self.__clean
        class Thread(threading.Thread):
            hub = None
            def run(self):
                g = gevent.Greenlet(run=lambda: 0)
                g.start()
                g.join()
                del g
                hub = gevent.get_hub()
                hub.join()
                self.hub = hub

        def tester(Thread, clean):
            t = Thread()
            t.start()
            t.join()
            t.hub.destroy(destroy_loop=True)
            t.hub = None
            del t
            clean()

        # Unfortunately, this WILL leak greenlets,
        # at least on CPython. The frames of the dead threads
        # are referenced by the hub in some sort of cycle, and
        # greenlets don't particpate in GC.
        for _ in range(10):
            tester(Thread, clean)

        del tester
        del Thread


if __name__ == '__main__':
    unittest.main()
