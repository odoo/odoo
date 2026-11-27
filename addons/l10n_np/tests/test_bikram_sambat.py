# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.addons.l10n_np.tools.bikram_sambat import convert_ad_to_bs, convert_ad_to_bs_with_formatting, convert_bs_to_ad, get_bs_month_ad_range
from odoo.tests import BaseCase, tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestBikramSambat(BaseCase):

    def test_convert_ad_to_bs_supported_range(self):
        self.assertEqual(convert_ad_to_bs(date(1943, 4, 14)), (2000, 1, 1))
        self.assertEqual(convert_ad_to_bs(date(2034, 4, 13)), (2090, 12, 30))
        with self.assertRaises(ValueError):
            convert_ad_to_bs(date(1943, 4, 13))
        with self.assertRaises(ValueError):
            convert_ad_to_bs(date(2034, 4, 14))

    def test_convert_ad_to_bs_known_dates(self):
        self.assertEqual(convert_ad_to_bs(date(2026, 4, 14)), (2083, 1, 1))
        self.assertEqual(convert_ad_to_bs(date(2026, 11, 6)), (2083, 7, 20))
        self.assertEqual(convert_ad_to_bs(date(2024, 8, 1)), (2081, 4, 17))

    def test_convert_ad_to_bs_with_formatting(self):
        bs_date, formatted = convert_ad_to_bs_with_formatting(date(2024, 8, 1), date_format='%m/%d/%Y')
        self.assertEqual(bs_date, (2081, 4, 17))
        self.assertEqual(formatted, '04/17/2081')
        _bs_date, formatted = convert_ad_to_bs_with_formatting(date(2024, 8, 1), date_format='%Y-%m-%d')
        self.assertEqual(formatted, '2081-04-17')

    def test_convert_bs_to_ad(self):
        self.assertEqual(convert_bs_to_ad(2083, 1, 1), date(2026, 4, 14))
        self.assertEqual(convert_bs_to_ad(2081, 4, 17), date(2024, 8, 1))
        self.assertEqual(convert_bs_to_ad(2083, 7, 20), date(2026, 11, 6))

    def test_get_bs_month_ad_range(self):
        start, end = get_bs_month_ad_range(2083, 1)
        self.assertEqual(start, date(2026, 4, 14))
        self.assertEqual(end, date(2026, 5, 14))
        start, end = get_bs_month_ad_range(2081, 4)
        self.assertEqual(start, date(2024, 7, 16))
        self.assertEqual(end, date(2024, 8, 16))
