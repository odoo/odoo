"""Database-free tests for ``res.currency`` model methods.

Tests pure arithmetic/business methods: ``round()``, ``is_zero()``,
``compare_amounts()``, ``_compute_decimal_places()``.  These methods
depend only on ``self.rounding`` and require no relational traversal
or database access.

Run with::

    python -m pytest core/tests/models/test_res_currency.py -v
"""

import pytest

# ── round() ──────────────────────────────────────────────────────


class TestRound:
    """``res.currency.round()`` — delegates to ``tools.float_round``."""

    def test_standard_two_decimals(self, make_currency):
        usd = make_currency("USD", "$", 0.01)
        assert usd.round(1.005) == 1.01
        assert usd.round(1.004) == 1.0
        assert usd.round(1.555) == 1.56

    def test_negative_amount(self, make_currency):
        usd = make_currency("USD", "$", 0.01)
        assert usd.round(-1.005) == -1.01
        assert usd.round(-0.004) == 0.0

    def test_zero(self, make_currency):
        usd = make_currency("USD", "$", 0.01)
        assert usd.round(0.0) == 0.0

    def test_high_precision_three_decimals(self, make_currency):
        """BHD, KWD, OMR use 3 decimal places."""
        bhd = make_currency("BHD", "BD", 0.001)
        assert bhd.round(1.0005) == 1.001
        assert bhd.round(1.0004) == 1.0

    def test_zero_decimal_currency(self, make_currency):
        """JPY, KRW have rounding=1 (no decimals)."""
        jpy = make_currency("JPY", "¥", 1.0, decimal_places=0)
        assert jpy.round(100.456) == 100.0
        assert jpy.round(100.5) == 101.0

    def test_five_cent_rounding(self, make_currency):
        """Swiss cash rounding: 0.05 CHF."""
        chf = make_currency("CHF", "Fr", 0.05)
        assert chf.round(1.02) == 1.0
        assert chf.round(1.03) == 1.05
        assert chf.round(1.07) == 1.05
        assert chf.round(1.08) == 1.10


# ── is_zero() ────────────────────────────────────────────────────


class TestIsZero:
    """``res.currency.is_zero()`` — tests against rounding threshold."""

    def test_below_threshold(self, make_currency):
        usd = make_currency("USD", "$", 0.01)
        assert usd.is_zero(0.004)
        assert usd.is_zero(0.0)
        assert usd.is_zero(-0.004)

    def test_above_threshold(self, make_currency):
        usd = make_currency("USD", "$", 0.01)
        assert not usd.is_zero(0.01)
        assert not usd.is_zero(0.006)
        assert not usd.is_zero(-0.01)

    def test_high_precision(self, make_currency):
        bhd = make_currency("BHD", "BD", 0.001)
        assert bhd.is_zero(0.0004)
        assert not bhd.is_zero(0.001)


# ── compare_amounts() ────────────────────────────────────────────


class TestCompareAmounts:
    """``res.currency.compare_amounts()`` — rounded comparison."""

    def test_equal_after_rounding(self, make_currency):
        usd = make_currency("USD", "$", 0.01)
        assert usd.compare_amounts(1.004, 1.001) == 0

    def test_first_greater(self, make_currency):
        usd = make_currency("USD", "$", 0.01)
        assert usd.compare_amounts(1.006, 1.001) == 1

    def test_first_less(self, make_currency):
        usd = make_currency("USD", "$", 0.01)
        assert usd.compare_amounts(1.001, 1.006) == -1

    def test_negative_amounts(self, make_currency):
        usd = make_currency("USD", "$", 0.01)
        assert usd.compare_amounts(-1.006, -1.001) == -1
        assert usd.compare_amounts(-1.001, -1.006) == 1

    def test_zero_comparison(self, make_currency):
        usd = make_currency("USD", "$", 0.01)
        assert usd.compare_amounts(0.0, 0.004) == 0
        assert usd.compare_amounts(0.0, 0.006) == -1


# ── _compute_decimal_places() ────────────────────────────────────


class TestDecimalPlaces:
    """``_compute_decimal_places`` — logarithmic formula."""

    @pytest.mark.parametrize(
        "rounding, expected",
        [
            (0.01, 2),      # USD, EUR, GBP
            (0.001, 3),     # BHD, KWD, OMR
            (0.1, 1),       # MRU
            (1.0, 0),       # JPY, KRW
            (5.0, 0),       # 5-unit cash rounding
            (0.05, 2),      # 5-cent rounding: ceil(log10(20)) = 2
            (0.0001, 4),    # Ultra-high precision
        ],
    )
    def test_decimal_places(self, make_currency, rounding, expected):
        currency = make_currency(f"C{rounding}", "X", rounding)
        currency._compute_decimal_places()
        assert currency.decimal_places == expected

    def test_multiple_currencies_batch(self, env):
        """Batch compute across multiple currencies."""
        Currency = env["res.currency"]
        usd = Currency.create(
            {"name": "USD", "symbol": "$", "rounding": 0.01, "active": True}
        )
        jpy = Currency.create(
            {"name": "JPY", "symbol": "¥", "rounding": 1.0, "active": True}
        )
        batch = usd | jpy
        batch._compute_decimal_places()
        assert usd.decimal_places == 2
        assert jpy.decimal_places == 0
