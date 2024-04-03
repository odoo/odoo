
from __future__ import absolute_import, print_function, division

import unittest
import sys
import gevent.testing as greentest

from gevent._config import Loop

available_loops = Loop().get_options()
available_loops.pop('libuv', None)

def not_available(name):
    return isinstance(available_loops[name], ImportError)


class WatcherTestMixin(object):
    kind = None

    def _makeOne(self):
        return self.kind(default=False) # pylint:disable=not-callable

    def destroyOne(self, loop):
        loop.destroy()

    def setUp(self):
        self.loop = self._makeOne()
        self.core = sys.modules[self.kind.__module__]

    def tearDown(self):
        self.destroyOne(self.loop)
        del self.loop

    def test_get_version(self):
        version = self.core.get_version() # pylint: disable=no-member
        self.assertIsInstance(version, str)
        self.assertTrue(version)
        header_version = self.core.get_header_version() # pylint: disable=no-member
        self.assertIsInstance(header_version, str)
        self.assertTrue(header_version)
        self.assertEqual(version, header_version)

    def test_events_conversion(self):
        self.assertEqual(self.core._events_to_str(self.core.READ | self.core.WRITE), # pylint: disable=no-member
                         'READ|WRITE')

    def test_EVENTS(self):
        self.assertEqual(str(self.core.EVENTS), # pylint: disable=no-member
                         'gevent.core.EVENTS')
        self.assertEqual(repr(self.core.EVENTS), # pylint: disable=no-member
                         'gevent.core.EVENTS')

    def test_io(self):
        if greentest.WIN:
            # libev raises IOError, libuv raises ValueError
            Error = (IOError, ValueError)
        else:
            Error = ValueError

        with self.assertRaises(Error):
            self.loop.io(-1, 1)

        if hasattr(self.core, 'TIMER'):
            # libev
            with self.assertRaises(ValueError):
                self.loop.io(1, self.core.TIMER) # pylint:disable=no-member

        # Test we can set events and io before it's started
        if not greentest.WIN:
            # We can't do this with arbitrary FDs on windows;
            # see libev_vfd.h
            io = self.loop.io(1, self.core.READ) # pylint:disable=no-member
            io.fd = 2
            self.assertEqual(io.fd, 2)
            io.events = self.core.WRITE # pylint:disable=no-member
            if not hasattr(self.core, 'libuv'):
                # libev
                # pylint:disable=no-member
                self.assertEqual(self.core._events_to_str(io.events), 'WRITE|_IOFDSET')
            else:

                self.assertEqual(self.core._events_to_str(io.events), # pylint:disable=no-member
                                 'WRITE')
            io.start(lambda: None)
            io.close()

    def test_timer_constructor(self):
        with self.assertRaises(ValueError):
            self.loop.timer(1, -1)

    def test_signal_constructor(self):
        with self.assertRaises(ValueError):
            self.loop.signal(1000)


class LibevTestMixin(WatcherTestMixin):

    def test_flags_conversion(self):
        # pylint: disable=no-member
        core = self.core
        if not greentest.WIN:
            self.assertEqual(core.loop(2, default=False).backend_int, 2)
        self.assertEqual(core.loop('select', default=False).backend, 'select')
        self.assertEqual(core._flags_to_int(None), 0)
        self.assertEqual(core._flags_to_int(['kqueue', 'SELECT']), core.BACKEND_KQUEUE | core.BACKEND_SELECT)
        self.assertEqual(core._flags_to_list(core.BACKEND_PORT | core.BACKEND_POLL), ['port', 'poll'])
        self.assertRaises(ValueError, core.loop, ['port', 'blabla'])
        self.assertRaises(TypeError, core.loop, object())

@unittest.skipIf(not_available('libev-cext'), "Needs libev-cext")
class TestLibevCext(LibevTestMixin, unittest.TestCase):
    kind = available_loops['libev-cext']

@unittest.skipIf(not_available('libev-cffi'), "Needs libev-cffi")
class TestLibevCffi(LibevTestMixin, unittest.TestCase):
    kind = available_loops['libev-cffi']

@unittest.skipIf(not_available('libuv-cffi'), "Needs libuv-cffi")
class TestLibuvCffi(WatcherTestMixin, unittest.TestCase):
    kind = available_loops['libuv-cffi']

    @greentest.skipOnLibev("libuv-specific")
    @greentest.skipOnWindows("Destroying the loop somehow fails")
    def test_io_multiplex_events(self):
        # pylint:disable=no-member
        import socket
        sock = socket.socket()
        fd = sock.fileno()
        core = self.core
        read = self.loop.io(fd, core.READ)
        write = self.loop.io(fd, core.WRITE)

        try:
            real_watcher = read._watcher_ref

            read.start(lambda: None)
            self.assertEqual(real_watcher.events, core.READ)

            write.start(lambda: None)
            self.assertEqual(real_watcher.events, core.READ | core.WRITE)

            write.stop()
            self.assertEqual(real_watcher.events, core.READ)

            write.start(lambda: None)
            self.assertEqual(real_watcher.events, core.READ | core.WRITE)

            read.stop()
            self.assertEqual(real_watcher.events, core.WRITE)

            write.stop()
            self.assertEqual(real_watcher.events, 0)
        finally:
            read.close()
            write.close()
            sock.close()


if __name__ == '__main__':
    greentest.main()
