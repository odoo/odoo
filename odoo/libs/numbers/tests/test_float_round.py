import random
import unittest
from decimal import (
    ROUND_DOWN,
    ROUND_HALF_DOWN,
    ROUND_HALF_EVEN,
    ROUND_HALF_UP,
    ROUND_UP,
    Decimal,
)

from odoo.libs.numbers.float_utils import RoundingMethod, float_repr, float_round


class TestFloatRound(unittest.TestCase):
    def test_normalization_underflow_returns_zero(self):
        self.assertEqual(float_round(1e-320, precision_rounding=1e20), 0.0)

    def test_zero_input(self):
        self.assertEqual(float_round(0.0, precision_rounding=0.01), 0.0)

    def test_normal_rounding(self):
        self.assertEqual(float_round(1.3, precision_rounding=0.5), 1.5)
        self.assertEqual(float_round(2.675, precision_digits=2), 2.68)

    def test_a_step_without_an_exact_inverse_lands_on_its_multiples(self):
        self.assertEqual(float_round(8.97, precision_rounding=0.03), 8.97)
        for step in ("0.03", "0.07", "0.3", "0.15", "0.0003"):
            for k in range(-600, 600):
                expected = float(Decimal(step) * k)
                for method in ("HALF-UP", "HALF-EVEN", "HALF-DOWN", "UP", "DOWN"):
                    got = float_round(
                        expected, precision_rounding=float(step), rounding_method=method
                    )
                    self.assertEqual(got, expected, (step, k, method))

    def test_returns_float_not_int(self):
        for method in ("HALF-UP", "HALF-EVEN", "HALF-DOWN", "UP", "DOWN"):
            r = float_round(2.5, precision_digits=0, rounding_method=method)
            self.assertIsInstance(r, float, method)

    def test_large_magnitude_down_does_not_inflate(self):
        self.assertEqual(
            float_round(12000000000000.0, precision_digits=2, rounding_method="DOWN"),
            12000000000000.0,
        )
        self.assertEqual(
            float_round(50000000000000.0, precision_digits=2, rounding_method="DOWN"),
            50000000000000.0,
        )

    def test_large_magnitude_up_does_not_overshoot(self):
        self.assertEqual(
            float_round(2.0**52, precision_digits=0, rounding_method="UP"), 2.0**52
        )
        self.assertEqual(
            float_round(50000000000000.0, precision_digits=2, rounding_method="UP"),
            50000000000000.0,
        )

    def test_large_magnitude_half_even_tie_is_even(self):
        self.assertEqual(
            float_round(2**50 + 0.5, precision_digits=0, rounding_method="HALF-EVEN"),
            float(2**50),
        )

    def test_half_even_ties(self):
        self.assertEqual(
            float_round(0.5, precision_digits=0, rounding_method="HALF-EVEN"), 0.0
        )
        self.assertEqual(
            float_round(1.5, precision_digits=0, rounding_method="HALF-EVEN"), 2.0
        )
        self.assertEqual(
            float_round(2.5, precision_digits=0, rounding_method="HALF-EVEN"), 2.0
        )

    def test_half_down_ties_round_toward_zero(self):
        self.assertEqual(
            float_round(2.5, precision_digits=0, rounding_method="HALF-DOWN"), 2.0
        )
        self.assertEqual(
            float_round(-2.5, precision_digits=0, rounding_method="HALF-DOWN"), -2.0
        )
        self.assertEqual(
            float_round(3.5, precision_digits=0, rounding_method="HALF-DOWN"), 3.0
        )

    def test_matches_decimal_over_money_range(self):
        dmeth: dict[RoundingMethod, str] = {
            "HALF-UP": ROUND_HALF_UP,
            "HALF-EVEN": ROUND_HALF_EVEN,
            "HALF-DOWN": ROUND_HALF_DOWN,
            "UP": ROUND_UP,
            "DOWN": ROUND_DOWN,
        }
        rng = random.Random(20260723)
        for _ in range(20000):
            value = round(rng.uniform(-1e6, 1e6), 6)
            digits = rng.choice([0, 1, 2, 3, 4])
            quantum = Decimal(1).scaleb(-digits)
            for method, dm in dmeth.items():
                got = float_round(
                    value, precision_digits=digits, rounding_method=method
                )
                want = float(Decimal(str(value)).quantize(quantum, rounding=dm))
                self.assertAlmostEqual(
                    got,
                    want,
                    delta=10 ** -(digits + 3),
                    msg=f"{method} value={value} digits={digits}",
                )

    def test_extended_float_range(self):
        fractions = [0.0, 0.015, 0.01499, 0.675, 0.67499, 0.4555, 0.4555, 0.45555]
        expecteds = [".00", ".02", ".01", ".68", ".67", ".46", ".456", ".4556"]
        precisions = [2, 2, 2, 2, 2, 2, 3, 4]
        for magnitude in range(7):
            for frac, exp, prec in zip(fractions, expecteds, precisions, strict=True):
                for sign in (-1, 1):
                    for x in range(0, 10000, 97):
                        n = x * 10**magnitude
                        value = sign * (n + frac)
                        expected = (
                            ("-" if value != 0 and sign == -1 else "") + str(n) + exp
                        )
                        self.assertEqual(
                            float_repr(
                                float_round(value, precision_digits=prec),
                                precision_digits=prec,
                            ),
                            expected,
                            f"rounding {value!r} at {prec} digits",
                        )

    def test_idempotent_on_its_own_grid(self):
        for digits in range(16):
            for n in range(500):
                once = float_round(n * 10**-digits, precision_digits=digits)
                self.assertEqual(
                    float_round(once, precision_digits=digits), once, f"{digits=} {n=}"
                )


if __name__ == "__main__":
    unittest.main()
