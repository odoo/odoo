import unittest
from decimal import Decimal

from odoo.libs.numbers.float_utils import _INVERTDICT, _float_invert


def _decimal_intent(value: float) -> float:
    return float(1 / Decimal(repr(value)))


class TestFloatInvertRecoversDecimalIntent(unittest.TestCase):
    def test_one_over_ten_to_the_minus_eleven(self):
        self.assertEqual(_float_invert(1e-11), 1e11)

    def test_decimal_factors_all_recover_their_intent(self):
        wrong = [
            (value, _float_invert(value), _decimal_intent(value))
            for digits in range(26)
            for coefficient in (1, 2, 5)
            if (value := float(f"{coefficient}e-{digits}"))
            and _float_invert(value) != _decimal_intent(value)
        ]
        self.assertEqual(wrong, [])

    def test_plain_division_would_not_pass_the_above(self):
        self.assertNotEqual(1 / 1e-5, _decimal_intent(1e-5))

    def test_table_is_a_fast_path_not_a_correction(self):
        disagreeing = {
            value: (tabled, _decimal_intent(value))
            for value, tabled in _INVERTDICT.items()
            if tabled != _decimal_intent(value)
        }
        self.assertEqual(disagreeing, {})

    def test_non_decimal_values_still_invert(self):
        self.assertEqual(_float_invert(0.25), 4.0)
        self.assertEqual(_float_invert(0.125), 8.0)
        self.assertEqual(_float_invert(2.0), 0.5)

    def test_negative_values_keep_their_sign(self):
        self.assertEqual(_float_invert(-0.01), -100.0)
        self.assertEqual(_float_invert(-0.25), -4.0)

    def test_zero_raises_a_named_error(self):
        with self.assertRaises(ZeroDivisionError):
            _float_invert(0.0)


if __name__ == "__main__":
    unittest.main()
