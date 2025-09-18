"""Unit tests for odoo.libs.res_bank — no Odoo ORM dependency."""

import unittest

from odoo.libs.res_bank import sanitize_account_number


class TestSanitizeAccountNumber(unittest.TestCase):
    """Test sanitize_account_number pure function."""

    def test_normal_number(self):
        self.assertEqual(
            sanitize_account_number("BE68539007547034"), "BE68539007547034"
        )

    def test_with_spaces(self):
        self.assertEqual(
            sanitize_account_number("BE68 5390 0754 7034"), "BE68539007547034"
        )

    def test_with_dashes(self):
        self.assertEqual(
            sanitize_account_number("BE68-5390-0754-7034"), "BE68539007547034"
        )

    def test_with_mixed_separators(self):
        self.assertEqual(
            sanitize_account_number("be68 5390-0754.7034"), "BE68539007547034"
        )

    def test_lowercase_uppercased(self):
        self.assertEqual(
            sanitize_account_number("be68539007547034"), "BE68539007547034"
        )

    def test_empty_string(self):
        self.assertFalse(sanitize_account_number(""))

    def test_none(self):
        self.assertFalse(sanitize_account_number(None))

    def test_false(self):
        self.assertFalse(sanitize_account_number(False))

    def test_already_clean(self):
        self.assertEqual(sanitize_account_number("ABC123"), "ABC123")


if __name__ == "__main__":
    unittest.main()
