# Tests for the monkey-patched select module.
from gevent import monkey
monkey.patch_all()

import select

import gevent.testing as greentest


class TestSelect(greentest.TestCase):

    def _make_test(name, ns): # pylint:disable=no-self-argument
        def test(self):
            self.assertIs(getattr(select, name, self), self)
            self.assertFalse(hasattr(select, name))
        test.__name__ = 'test_' + name + '_removed'
        ns[test.__name__] = test

    for name in (
            'epoll',
            'kqueue',
            'kevent',
            'devpoll',
    ):
        _make_test(name, locals()) # pylint:disable=too-many-function-args

    del name
    del _make_test


if __name__ == '__main__':
    greentest.main()
