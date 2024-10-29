"""Testing that greenlet restores sys.exc_info.

Passes with CPython + greenlet 0.4.0

Fails with PyPy 2.2.1
"""
from __future__ import print_function
import sys

from gevent import testing as greentest

class Test(greentest.TestCase):

    def test(self):
        import greenlet

        print('Your greenlet version: %s' % (getattr(greenlet, '__version__', None), ))

        result = []

        def func():
            result.append(repr(sys.exc_info()))

        g = greenlet.greenlet(func)
        try:
            1 / 0
        except ZeroDivisionError:
            g.switch()


        self.assertEqual(result, ['(None, None, None)'])

if __name__ == '__main__':
    greentest.main()
