# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from freezegun import freeze_time

from odoo.tests.common import TransactionCase

class test_res_lang(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.lang_0 = cls.env['res.lang'].create({
            'name': 'Test Lang',
            'iso_code': 'test_lang',
            'code': 'test_lang',
            'grouping': '[3,0]',
        })

    def test_00_intersperse(self):
        from odoo.addons.base.models.res_lang import intersperse

        assert intersperse("", []) == ("", 0)
        assert intersperse("0", []) == ("0", 0)
        assert intersperse("012", []) == ("012", 0)
        assert intersperse("1", []) == ("1", 0)
        assert intersperse("12", []) == ("12", 0)
        assert intersperse("123", []) == ("123", 0)
        assert intersperse("1234", []) == ("1234", 0)
        assert intersperse("123456789", []) == ("123456789", 0)
        assert intersperse("&ab%#@1", []) == ("&ab%#@1", 0)

        assert intersperse("0", []) == ("0", 0)
        assert intersperse("0", [1]) == ("0", 0)
        assert intersperse("0", [2]) == ("0", 0)
        assert intersperse("0", [200]) == ("0", 0)

        assert intersperse("12345678", [1], '.') == ('1234567.8', 1)
        assert intersperse("12345678", [1], '.') == ('1234567.8', 1)
        assert intersperse("12345678", [2], '.') == ('123456.78', 1)
        assert intersperse("12345678", [2,1], '.') == ('12345.6.78', 2)
        assert intersperse("12345678", [2,0], '.') == ('12.34.56.78', 3)
        assert intersperse("12345678", [-1,2], '.') == ('12345678', 0)
        assert intersperse("12345678", [2,-1], '.') == ('123456.78', 1)
        assert intersperse("12345678", [2,0,1], '.') == ('12.34.56.78', 3)
        assert intersperse("12345678", [2,0,0], '.') == ('12.34.56.78', 3)
        assert intersperse("12345678", [2,0,-1], '.') == ('12.34.56.78', 3)
        assert intersperse("12345678", [3,3,3,3], '.') == ('12.345.678', 2)

        assert intersperse("abc1234567xy", [2], '.') == ('abc1234567.xy', 1)
        assert intersperse("abc1234567xy8", [2], '.') == ('abc1234567x.y8', 1) # ... w.r.t. here.
        assert intersperse("abc12", [3], '.') == ('abc12', 0)
        assert intersperse("abc12", [2], '.') == ('abc12', 0)
        assert intersperse("abc12", [1], '.') == ('abc1.2', 1)

    def test_res_lang_decimal_point_preview(self):
        self.assertEqual(self.lang_0.decimal_point_preview, '(e.g. "99.00")')
        self.lang_0.decimal_point = ','
        self.assertEqual(self.lang_0.decimal_point_preview, '(e.g. "99,00")')

    def test_res_lang_thousand_sep_preview(self):
        self.assertEqual(self.lang_0.thousand_sep_preview, '(e.g. "999,999,999")')
        self.lang_0.thousands_sep = '.'
        self.assertEqual(self.lang_0.thousand_sep_preview, '(e.g. "999.999.999")')

    @freeze_time("2020-01-01 16:00:00")
    def test_res_lang_date_format_preview(self):
        lang_0, lang_1 = self.env['res.lang'].with_context(active_test=False).search(
            [('iso_code', 'in', ['en', 'fr'])]
        )

        self.assertEqual(lang_0.date_format_preview, '(e.g. "01/01/2020")')
        self.assertEqual(lang_1.date_format_preview, '(e.g. "01/01/2020")')

        (lang_0 | lang_1).date_format = '%A-%B-%Y'

        self.assertEqual(lang_0.date_format_preview, '(e.g. "Wednesday-January-2020")')
        self.assertEqual(lang_1.date_format_preview, '(e.g. "mercredi-janvier-2020")')

    @freeze_time("2020-01-01 16:00:00")
    def test_res_lang_time_format_preview(self):
        lang_0, lang_1 = self.env['res.lang'].with_context(active_test=False).search(
            [('iso_code', 'in', ['en', 'fr'])]
        )

        self.assertEqual(lang_0.time_format_preview, '(e.g. "16:00:00")')
        self.assertEqual(lang_1.time_format_preview, '(e.g. "16:00:00")')

        (lang_0 | lang_1).time_format = '%M-%I-%S'

        self.assertEqual(lang_0.time_format_preview, '(e.g. "00-04-00")')
        self.assertEqual(lang_1.time_format_preview, '(e.g. "00-04-00")')
