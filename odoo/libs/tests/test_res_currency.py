"""Unit tests for odoo.libs.res_currency — no Odoo ORM dependency."""

import unittest

from odoo.libs.res_currency import (
    amount_to_text_parts,
    decimal_places_from_rounding,
    number_to_words,
)


class TestDecimalPlacesFromRounding(unittest.TestCase):
    """Test decimal_places_from_rounding pure function."""

    def test_two_decimals(self):
        self.assertEqual(decimal_places_from_rounding(0.01), 2)

    def test_three_decimals(self):
        self.assertEqual(decimal_places_from_rounding(0.001), 3)

    def test_one_decimal(self):
        self.assertEqual(decimal_places_from_rounding(0.1), 1)

    def test_four_decimals(self):
        self.assertEqual(decimal_places_from_rounding(0.0001), 4)

    def test_rounding_one(self):
        self.assertEqual(decimal_places_from_rounding(1.0), 0)

    def test_rounding_five(self):
        self.assertEqual(decimal_places_from_rounding(5.0), 0)

    def test_nickel_rounding(self):
        """0.05 rounding → 2 decimal places (rounds up from 1.30)."""
        self.assertEqual(decimal_places_from_rounding(0.05), 2)

    def test_zero_rounding(self):
        """Zero rounding should return 0 (edge case)."""
        self.assertEqual(decimal_places_from_rounding(0), 0)

    def test_negative_rounding(self):
        """Negative rounding should return 0 (invalid but handled)."""
        self.assertEqual(decimal_places_from_rounding(-0.01), 0)


class TestNumberToWords(unittest.TestCase):
    """Test number_to_words pure function."""

    def test_zero(self):
        self.assertEqual(number_to_words(0), "Zero")

    def test_one(self):
        self.assertEqual(number_to_words(1), "One")

    def test_forty_two(self):
        self.assertEqual(number_to_words(42), "Forty-Two")

    def test_thousand(self):
        result = number_to_words(1000)
        self.assertIn("Thousand", result)

    def test_negative(self):
        result = number_to_words(-1)
        self.assertIn("Minus", result)

    def test_french(self):
        result = number_to_words(42, lang="fr")
        self.assertEqual(result, "Quarante-Deux")


class TestAmountToTextParts(unittest.TestCase):
    """Test amount_to_text_parts pure function."""

    def test_positive_with_fractional(self):
        integral, fractional, frac_val = amount_to_text_parts(100.50, 2)
        self.assertEqual(integral, "One Hundred")
        self.assertEqual(fractional, "Fifty")
        self.assertEqual(frac_val, 50)

    def test_positive_no_fractional(self):
        integral, _fractional, frac_val = amount_to_text_parts(100.0, 2)
        self.assertEqual(integral, "One Hundred")
        self.assertEqual(frac_val, 0)

    def test_zero_amount(self):
        integral, _fractional, frac_val = amount_to_text_parts(0.0, 2)
        self.assertEqual(integral, "Zero")
        self.assertEqual(frac_val, 0)

    def test_negative_amount(self):
        """Negative amounts: num2words handles the sign for integer_value > 0."""
        integral, _fractional, _frac_val = amount_to_text_parts(-42.50, 2)
        self.assertIn("Minus", integral)
        self.assertIn("Forty", integral)

    def test_negative_between_minus_one_and_zero(self):
        """Amounts in (-1, 0): must prepend minus manually since int part is 0."""
        integral, _fractional, frac_val = amount_to_text_parts(-0.50, 2)
        self.assertIn("Minus", integral)
        self.assertIn("Zero", integral)
        self.assertEqual(frac_val, 50)

    def test_with_language(self):
        integral, _fractional, frac_val = amount_to_text_parts(42.10, 2, lang="fr")
        self.assertEqual(integral, "Quarante-Deux")
        self.assertEqual(frac_val, 10)

    def test_large_amount(self):
        integral, _fractional, _frac_val = amount_to_text_parts(1_000_000.99, 2)
        self.assertIn("Million", integral)


if __name__ == "__main__":
    unittest.main()
