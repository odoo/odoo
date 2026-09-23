import unittest

from odoo.libs.numbers.amount_parse import parse_amount, split_amount_str


class TestParseAmount(unittest.TestCase):
    def test_dot_decimal_separator(self):
        self.assertEqual(parse_amount("1.5"), 1.5)

    def test_comma_decimal_separator(self):
        self.assertEqual(parse_amount("1,5"), 1.5)

    def test_groupings_are_dropped(self):
        for text in ("1 234,56", "1'234.56", "1\xa0234,56"):
            with self.subTest(text=text):
                self.assertEqual(parse_amount(text), 1234.56)

    def test_thousands_separator_of_either_convention(self):
        self.assertEqual(parse_amount("1,334,567"), 1334567.0)
        self.assertEqual(parse_amount("1.334.567"), 1334567.0)

    def test_signs(self):
        self.assertEqual(parse_amount("-50"), -50.0)
        self.assertEqual(parse_amount("+10"), 10.0)
        self.assertEqual(parse_amount(" -  50 "), -50.0)

    def test_bare_decimal_part(self):
        self.assertEqual(parse_amount(".5"), 0.5)

    def test_zero_is_a_value_not_a_failure(self):
        self.assertEqual(parse_amount("0"), 0.0)
        self.assertEqual(parse_amount("0,00"), 0.0)

    def test_non_numeric_is_rejected(self):
        for text in ("abc", "", None, "  ", "12a", "1..2.a"):
            with self.subTest(text=text):
                self.assertIsNone(parse_amount(text))

    def test_non_finite_literals_are_rejected(self):
        for text in ("inf", "-inf", "Infinity", "nan", "NaN", "1e400"):
            with self.subTest(text=text):
                self.assertIsNone(parse_amount(text))

    def test_overflowing_magnitude_is_rejected(self):
        self.assertIsNone(parse_amount("9" * 400))

    def test_underscores_are_not_python_literals(self):
        self.assertIsNone(parse_amount("1_000"))

    def test_non_decimal_digits_are_rejected_not_raised(self):
        for text in ("\u00b2", "1\u00b2", "\u2460"):
            with self.subTest(text=text):
                self.assertIsNone(parse_amount(text))

    def test_the_decimal_separator_follows_every_thousands_separator(self):
        for text in ("1,000.000.1", "1.2,3.4", "1,000.5,000"):
            with self.subTest(text=text):
                self.assertIsNone(parse_amount(text))

    def test_thousands_groups_are_three_digits(self):
        for text in ("1,2,3", "1.2.3", "12,3456.7", "1234,567.89", "1,23,4.5"):
            with self.subTest(text=text):
                self.assertIsNone(parse_amount(text))

    def test_lakh_grouping_is_a_grouping(self):
        self.assertEqual(parse_amount("12,34,567.89"), 1234567.89)


class TestSplitAmountStr(unittest.TestCase):
    def test_splits_into_parts(self):
        self.assertEqual(split_amount_str("1 234,56"), ("1234", "56"))
        self.assertEqual(split_amount_str("3358,07"), ("3358", "07"))

    def test_integer_only(self):
        self.assertEqual(split_amount_str("1334"), ("1334", "0"))

    def test_superscripts_are_not_digits(self):
        self.assertEqual(split_amount_str("1\u00b2"), ("0", "0"))

    def test_ambiguous_or_empty_reads_as_zero(self):
        for text in ("", "abc", "1,2,3.4,5.6"):
            with self.subTest(text=text):
                self.assertEqual(split_amount_str(text), ("0", "0"))
