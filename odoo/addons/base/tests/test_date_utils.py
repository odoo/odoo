# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date

from odoo.tests import BaseCase
from odoo.tools.date_utils import get_fiscal_year


class TestDateUtils(BaseCase):

    def test_fiscal_year(self):
        self.assertEqual(get_fiscal_year(date(2024, 12, 31)), (date(2024, 1, 1), date(2024, 12, 31)))
        self.assertEqual(get_fiscal_year(date(2024, 12, 31), 30, 11), (date(2024, 12, 1), date(2025, 11, 30)))
        self.assertEqual(get_fiscal_year(date(2024, 10, 31), 30, 11), (date(2023, 12, 1), date(2024, 11, 30)))
        self.assertEqual(get_fiscal_year(date(2024, 10, 31), 30, 12), (date(2023, 12, 31), date(2024, 12, 30)))

        self.assertEqual(get_fiscal_year(date(2024, 10, 31), month=11), (date(2023, 12, 1), date(2024, 11, 30)))
        self.assertEqual(get_fiscal_year(date(2024, 2, 29)), (date(2024, 1, 1), date(2024, 12, 31)))

        self.assertEqual(get_fiscal_year(date(2024, 12, 31), 29, 2), (date(2024, 3, 1), date(2025, 2, 28)))
        self.assertEqual(get_fiscal_year(date(2024, 12, 31), 28, 2), (date(2024, 3, 1), date(2025, 2, 28)))
        self.assertEqual(get_fiscal_year(date(2023, 12, 31), 28, 2), (date(2023, 3, 1), date(2024, 2, 29)))
        self.assertEqual(get_fiscal_year(date(2023, 12, 31), 29, 2), (date(2023, 3, 1), date(2024, 2, 29)))

        self.assertEqual(get_fiscal_year(date(2024, 2, 29), 28, 2), (date(2023, 3, 1), date(2024, 2, 29)))
        self.assertEqual(get_fiscal_year(date(2023, 2, 28), 28, 2), (date(2022, 3, 1), date(2023, 2, 28)))
        self.assertEqual(get_fiscal_year(date(2023, 2, 28), 29, 2), (date(2022, 3, 1), date(2023, 2, 28)))
