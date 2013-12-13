# This test can be run stand-alone with something like:
# > PYTHONPATH=. python2 openerp/tests/test_misc.py
import datetime
import locale
import unittest2

import babel
import babel.dates

from ..tools import misc


class test_countingstream(unittest2.TestCase):
    def test_empty_stream(self):
        s = misc.CountingStream(iter([]))
        self.assertEqual(s.index, -1)
        self.assertIsNone(next(s, None))
        self.assertEqual(s.index, 0)

    def test_single(self):
        s = misc.CountingStream(xrange(1))
        self.assertEqual(s.index, -1)
        self.assertEqual(next(s, None), 0)
        self.assertIsNone(next(s, None))
        self.assertEqual(s.index, 1)

    def test_full(self):
        s = misc.CountingStream(xrange(42))
        for _ in s:
            pass
        self.assertEqual(s.index, 42)

    def test_repeated(self):
        """ Once the CountingStream has stopped iterating, the index should not
        increase anymore (the internal state should not be allowed to change)
        """
        s = misc.CountingStream(iter([]))
        self.assertIsNone(next(s, None))
        self.assertEqual(s.index, 0)
        self.assertIsNone(next(s, None))
        self.assertEqual(s.index, 0)

class TestPosixToBabel(unittest2.TestCase):
    def setUp(self):
        super(TestPosixToBabel, self).setUp()
        self.d = datetime.datetime(2007, 9, 8, 4, 5, 1)

    def assert_eq(self, fmt, d=None):
        if d is None: d = self.d

        locale = babel.Locale.default('LC_TIME')
        ldml_format = misc.posix_to_ldml(fmt, locale=locale)
        self.assertEqual(
            d.strftime(fmt),
            babel.dates.format_datetime(d, format=ldml_format, locale=locale),
            "%r resulted in a different result than %r for %s" % (
                ldml_format, fmt, d))

    def test_empty(self):
        self.assert_eq("")

    def test_literal(self):
        self.assert_eq("Raw test string")

    def test_mixed(self):
        self.assert_eq("m:%m d:%d y:%y")
        self.assert_eq("m:%m d:%d y:%y H:%H M:%M S:%S")

    def test_escape(self):
        self.assert_eq("%%m:%m %%d:%d %%y:%y")

    def test_xX(self):
        self.assert_eq('%x %X')

    def test_various_examples(self):
        self.assert_eq("%x - %I:%M%p")
        self.assert_eq('%Y-%m-%dT%H:%M:%S')
        self.assert_eq("%Y-%j")
        self.assert_eq("%a, %d %b %Y %H:%M:%S")
        self.assert_eq("%a, %b %d %I:%M.%S")

if __name__ == '__main__':
    unittest2.main()
