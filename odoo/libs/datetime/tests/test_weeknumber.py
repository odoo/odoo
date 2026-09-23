import unittest
from datetime import date

import babel

from odoo.libs.datetime.date_utils import weeknumber


class TestWeeknumber(unittest.TestCase):
    def test_the_week_rule_is_the_locale_s_alone(self):
        with self.assertRaises(TypeError):
            weeknumber(babel.Locale.parse("en_US"), date(2026, 1, 4), 0)  # type: ignore[call-arg]

    def test_an_iso_locale_reads_iso_weeks(self):
        de_de = babel.Locale.parse("de_DE")
        self.assertEqual(weeknumber(de_de, date(2021, 1, 2)), (2020, 53))
        self.assertEqual(weeknumber(de_de, date(2026, 1, 4)), (2026, 1))

    def test_default_uses_locale(self):
        en_us = babel.Locale.parse("en_US")
        self.assertEqual(weeknumber(en_us, date(2026, 1, 4)), (2026, 2))


if __name__ == "__main__":
    unittest.main()
