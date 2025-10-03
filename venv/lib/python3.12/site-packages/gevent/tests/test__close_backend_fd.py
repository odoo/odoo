from __future__ import print_function
import os
import unittest

import gevent
from gevent import core
from gevent.hub import Hub

from gevent.testing import sysinfo

@unittest.skipUnless(
    getattr(core, 'LIBEV_EMBED', False),
    "Needs embedded libev. "
    "hub.loop.fileno is only defined when "
    "we embed libev for some reason. "
    "Choosing specific backends is also only supported by libev "
    "(not libuv), and besides, libuv has a nasty tendency to "
    "abort() the process if its FD gets closed. "
)
class Test(unittest.TestCase):
    # NOTE that we extend unittest.TestCase, not greentest.TestCase
    # Extending the later causes the wrong hub to get used.

    BACKENDS_THAT_SUCCEED_WHEN_FD_CLOSED = (
        'kqueue',
        'epoll',
        'linux_aio',
        'linux_iouring',
    )

    BACKENDS_THAT_WILL_FAIL_TO_CREATE_AT_RUNTIME = (
        # This fails on the Fedora Rawhide 33 image. It's not clear
        # why; needs investigated.
        'linux_iouring',
    ) if not sysinfo.libev_supports_linux_iouring() else (

    )

    BACKENDS_THAT_WILL_FAIL_TO_CREATE_AT_RUNTIME += (
        # This can be compiled on any (?) version of
        # linux, but there's a runtime check that you're
        # running at least kernel 4.19, so we can fail to create
        # the hub. When we updated to libev 4.31 from 4.25, Travis Ci
        # was still on kernel 1.15 (Ubunto 16.04).
        'linux_aio',
    ) if not sysinfo.libev_supports_linux_aio() else (
    )

    def _check_backend(self, backend):
        hub = Hub(backend, default=False)

        try:
            self.assertEqual(hub.loop.backend, backend)

            gevent.sleep(0.001)
            fileno = hub.loop.fileno()
            if fileno is None:
                return # nothing to close, test implicitly passes.

            os.close(fileno)

            if backend in self.BACKENDS_THAT_SUCCEED_WHEN_FD_CLOSED:
                gevent.sleep(0.001)
            else:
                with self.assertRaisesRegex(SystemError, "(libev)"):
                    gevent.sleep(0.001)

            hub.destroy()
            self.assertIn('destroyed', repr(hub))
        finally:
            if hub.loop is not None:
                hub.destroy()

    @classmethod
    def _make_test(cls, count, backend): # pylint:disable=no-self-argument
        if backend in cls.BACKENDS_THAT_WILL_FAIL_TO_CREATE_AT_RUNTIME:
            def test(self):
                with self.assertRaisesRegex(SystemError, 'ev_loop_new'):
                    Hub(backend, default=False)
        else:
            def test(self):
                self._check_backend(backend)
        test.__name__ = 'test_' + backend + '_' + str(count)
        return test.__name__, test

    @classmethod
    def _make_tests(cls):
        count = backend = None

        for count in range(2):
            for backend in core.supported_backends():
                name, func = cls._make_test(count, backend)
                setattr(cls, name, func)
                name = func = None

Test._make_tests()

if __name__ == '__main__':
    unittest.main()
