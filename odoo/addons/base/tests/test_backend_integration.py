"""Integration tests requiring a loaded database.

Tests that need ``ormcache`` or ``env.ref()`` and cannot run against
DictBackend alone.  All other DictBackend tests have migrated to the
fast pytest suite at ``core/tests/models/``.

Remaining:
- ``TestAmountToTextBackend``: ``amount_to_text()`` calls ``tools.get_lang()``
  which relies on the ``res.lang`` ormcache being warm from a loaded database.
"""

from odoo.tests.common import TransactionCase


class TestAmountToTextBackend(TransactionCase):
    """res.currency.amount_to_text() — sign handling for negative fractional amounts.

    Validates the fix for amounts in (-1, 0) where int("-0") == 0 in Python
    would silently lose the negative sign.

    Uses real DB env since amount_to_text calls tools.get_lang() which relies
    on the res.lang ormcache being warm from the loaded database.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.usd = cls.env.ref("base.USD")

    def test_negative_fractional_amount(self):
        """amount_to_text(-0.50) should include the negative sign."""
        result = self.usd.amount_to_text(-0.50)
        # num2words renders negative numbers with "Minus" prefix
        self.assertIn("Minus", result, f"Negative sign lost in: {result}")

    def test_negative_one_dollar(self):
        """amount_to_text(-1.50) — standard negative with integral part."""
        result = self.usd.amount_to_text(-1.50)
        self.assertIn("Minus", result, f"Negative sign lost in: {result}")
        self.assertIn("Fifty", result, f"Fractional part wrong in: {result}")

    def test_positive_amount_unchanged(self):
        """Positive amounts are not affected by the sign fix."""
        result = self.usd.amount_to_text(1.50)
        self.assertNotIn("Minus", result)
        self.assertIn("One", result)
        self.assertIn("Fifty", result)

    def test_zero_amount(self):
        """Zero amount has no negative sign."""
        result = self.usd.amount_to_text(0.0)
        self.assertNotIn("Minus", result)
