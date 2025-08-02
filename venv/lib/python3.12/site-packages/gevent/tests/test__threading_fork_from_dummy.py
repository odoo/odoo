# -*- coding: utf-8 -*-
"""
Tests for `issue 2020 <https://github.com/gevent/gevent/issues/2020>`_:
3.11.8 and 3.12.2 try to swizzle ``__class__`` of the dummy thread
found when forking from inside a greenlet.

"""
from gevent import monkey; monkey.patch_all() # pragma: testrunner-no-monkey-combine

import unittest
import gevent.testing as greentest

import tempfile

@greentest.skipOnWindows("Uses os.fork")
class Test(greentest.TestCase):


    def test_fork_from_dummy_thread(self):
        import os
        import threading
        import contextlib

        import gevent
        from gevent.threading import _DummyThread
        if not _DummyThread._NEEDS_CLASS_FORK_FIXUP:
            self.skipTest('No patch need be applied')

        def do_it(out):
            # Be sure we've put the DummyThread in the threading
            # maps
            assert isinstance(threading.current_thread(), threading._DummyThread)

            with open(out, 'wt', encoding='utf-8') as f:
                with contextlib.redirect_stderr(f):
                    r = os.fork()
                    if r == 0:
                        # In the child.
                        # Our stderr redirect above will capture the
                        # "Exception ignored in _after_fork()" that the interpreter
                        # prints; actually printing the main_thread will result in
                        # raising an exception if our patch doesn't work.
                        main = threading.main_thread()
                        print(main, file=f)
                        print(type(main), file=f)
                    return r

        with tempfile.NamedTemporaryFile('w+t', suffix='.gevent_threading.txt') as tf:
            glet = gevent.spawn(do_it, tf.name)
            glet.join()
            pid = glet.get()
            if pid == 0:
                # Dump the child process quickly
                os._exit(0)

            os.waitpid(pid, 0)
            tf.seek(0, 0)
            contents = tf.read()


        self.assertIn("<class 'threading._MainThread'>", contents)
        self.assertNotIn("_DummyThread", contents)


if __name__ == '__main__':
    unittest.main()
