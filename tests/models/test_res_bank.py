"""Database-free tests for ``res.bank`` and ``res.partner.bank``.

Tests ``sanitize_account_number()`` (pure function), bank display name
formatting, and partner bank account computations.

Run with::

    python -m pytest core/tests/models/test_res_bank.py -v
"""

from odoo.addons.base.models.res_bank import sanitize_account_number

# ── sanitize_account_number() (module-level pure function) ───────


class TestSanitizeAccountNumber:
    """``sanitize_account_number()``: strip non-word chars, uppercase."""

    def test_removes_dashes_and_spaces(self):
        assert sanitize_account_number("1234-5678-9012") == "123456789012"

    def test_removes_spaces(self):
        assert sanitize_account_number("NL91 ABNA 0417 1643 00") == "NL91ABNA0417164300"

    def test_uppercases(self):
        assert sanitize_account_number("nl91abna0417164300") == "NL91ABNA0417164300"

    def test_mixed_special_chars(self):
        assert sanitize_account_number("IBAN-123.ABC/456") == "IBAN123ABC456"

    def test_already_clean(self):
        assert sanitize_account_number("ABC123") == "ABC123"

    def test_false_input(self):
        assert sanitize_account_number(False) is False

    def test_empty_string(self):
        assert sanitize_account_number("") is False


# ── ResBank._compute_display_name ────────────────────────────────


class TestBankDisplayName:
    """``ResBank._compute_display_name``: name + optional BIC."""

    def test_name_only(self, env):
        bank = env["res.bank"].create({"name": "Test Bank"})
        bank._compute_display_name()
        assert bank.display_name == "Test Bank"

    def test_name_and_bic(self, env):
        bank = env["res.bank"].create({"name": "Test Bank", "bic": "TESTXX22"})
        bank._compute_display_name()
        assert bank.display_name == "Test Bank - TESTXX22"

    def test_empty_bic(self, env):
        bank = env["res.bank"].create({"name": "Test Bank", "bic": ""})
        bank._compute_display_name()
        assert bank.display_name == "Test Bank"


# ── ResPartnerBank compute methods ───────────────────────────────


class TestPartnerBankCompute:
    """Compute methods on ``res.partner.bank``."""

    def test_sanitized_acc_number(self, env):
        partner = env["res.partner"].create({"name": "Test"})
        bank_acc = env["res.partner.bank"].create({
            "acc_number": "NL91 ABNA 0417 1643 00",
            "partner_id": partner.id,
        })
        bank_acc._compute_sanitized_acc_number()
        assert bank_acc.sanitized_acc_number == "NL91ABNA0417164300"

    def test_acc_type_default(self, env):
        """Default acc_type is 'bank'."""
        partner = env["res.partner"].create({"name": "Test"})
        bank_acc = env["res.partner.bank"].create({
            "acc_number": "123456",
            "partner_id": partner.id,
        })
        bank_acc._compute_acc_type()
        assert bank_acc.acc_type == "bank"
