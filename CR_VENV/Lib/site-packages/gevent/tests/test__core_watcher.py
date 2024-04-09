from __future__ import absolute_import, print_function

import gevent.testing as greentest
from gevent import config
from gevent.testing.sysinfo import CFFI_BACKEND

from gevent.core import READ # pylint:disable=no-name-in-module
from gevent.core import WRITE # pylint:disable=no-name-in-module


class Test(greentest.TestCase):

    __timeout__ = None

    def setUp(self):
        super(Test, self).setUp()
        self.loop = config.loop(default=False)
        self.timer = self.loop.timer(0.01)

    def tearDown(self):
        if self.timer is not None:
            self.timer.close()
        if self.loop is not None:
            self.loop.destroy()
        self.loop = self.timer = None
        super(Test, self).tearDown()

    def test_non_callable_to_start(self):
        # test that cannot pass non-callable thing to start()
        self.assertRaises(TypeError, self.timer.start, None)
        self.assertRaises(TypeError, self.timer.start, 5)

    def test_non_callable_after_start(self):
        # test that cannot set 'callback' to non-callable thing later either
        lst = []
        timer = self.timer
        timer.start(lst.append)


        with self.assertRaises(TypeError):
            timer.callback = False

        with self.assertRaises(TypeError):
            timer.callback = 5

    def test_args_can_be_changed_after_start(self):
        lst = []
        timer = self.timer
        self.timer.start(lst.append)
        self.assertEqual(timer.args, ())
        timer.args = (1, 2, 3)
        self.assertEqual(timer.args, (1, 2, 3))

        # Only tuple can be args
        with self.assertRaises(TypeError):
            timer.args = 5
        with self.assertRaises(TypeError):
            timer.args = [4, 5]

        self.assertEqual(timer.args, (1, 2, 3))

        # None also works, means empty tuple
        # XXX why?
        timer.args = None
        self.assertEqual(timer.args, None)


    def test_run(self):
        loop = self.loop
        lst = []

        self.timer.start(lambda *args: lst.append(args))

        loop.run()
        loop.update_now()

        self.assertEqual(lst, [()])

        # Even if we lose all references to it, the ref in the callback
        # keeps it alive
        self.timer.start(reset, self.timer, lst)
        self.timer = None
        loop.run()
        self.assertEqual(lst, [(), 25])

    def test_invalid_fd(self):
        loop = self.loop

        # Negative case caught everywhere. ValueError
        # on POSIX, OSError on Windows Py3, IOError on Windows Py2
        with self.assertRaises((ValueError, OSError, IOError)):
            loop.io(-1, READ)


    @greentest.skipOnWindows("Stdout can't be watched on Win32")
    def test_reuse_io(self):
        loop = self.loop

        # Watchers aren't reused once all outstanding
        # refs go away BUT THEY MUST BE CLOSED
        tty_watcher = loop.io(1, WRITE)
        watcher_handle = tty_watcher._watcher if CFFI_BACKEND else tty_watcher
        tty_watcher.close()
        del tty_watcher
        # XXX: Note there is a cycle in the CFFI code
        # from watcher_handle._handle -> watcher_handle.
        # So it doesn't go away until a GC runs.
        import gc
        gc.collect()

        tty_watcher = loop.io(1, WRITE)
        self.assertIsNot(tty_watcher._watcher if CFFI_BACKEND else tty_watcher, watcher_handle)
        tty_watcher.close()


def reset(watcher, lst):
    watcher.args = None
    watcher.callback = lambda: None
    lst.append(25)
    watcher.close()


if __name__ == '__main__':
    greentest.main()
