# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import unittest

from odoo.tools import misc
from odoo.tests.common import TransactionCase


class TestCountingStream(unittest.TestCase):
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


class TestFormatLangDate(TransactionCase):
    def test_00_accepted_types(self):
        date_datetime = datetime.datetime.strptime('2017-01-31 12:00:00', "%Y-%m-%d %H:%M:%S")
        date_date = date_datetime.date()
        date_str = '2017-01-31'

        self.assertEqual(misc.format_date(self.env, date_datetime), '01/31/2017')
        self.assertEqual(misc.format_date(self.env, date_date), '01/31/2017')
        self.assertEqual(misc.format_date(self.env, date_str), '01/31/2017')
        self.assertEqual(misc.format_date(self.env, ''), '')
        self.assertEqual(misc.format_date(self.env, False), '')
        self.assertEqual(misc.format_date(self.env, None), '')

    def test_01_code_and_format(self):
        date_str = '2017-01-31'
        lang = self.env['res.lang']

        # Activate French and Simplified Chinese (test with non-ASCII characters)
        lang.search([('active', '=', False), ('code', 'in', ['fr_FR', 'zh_CN'])]).write({'active': True})

        # Change a single parameter
        self.assertEqual(misc.format_date(lang.with_context(lang='fr_FR').env, date_str), '31/01/2017')
        self.assertEqual(misc.format_date(lang.env, date_str, lang_code='fr_FR'), '31/01/2017')
        self.assertEqual(misc.format_date(lang.env, date_str, date_format='MMM d, y'), 'Jan 31, 2017')

        # Change 2 parameters
        self.assertEqual(misc.format_date(lang.with_context(lang='zh_CN').env, date_str, lang_code='fr_FR'), '31/01/2017')
        self.assertEqual(misc.format_date(lang.with_context(lang='zh_CN').env, date_str, date_format='MMM d, y'), u'1\u6708 31, 2017')
        self.assertEqual(misc.format_date(lang.env, date_str, lang_code='fr_FR', date_format='MMM d, y'), 'janv. 31, 2017')

        # Change 3 parameters
        self.assertEqual(misc.format_date(lang.with_context(lang='zh_CN').env, date_str, lang_code='en_US', date_format='MMM d, y'), 'Jan 31, 2017')
