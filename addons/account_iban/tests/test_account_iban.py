from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged

from odoo.addons.account_iban.models.res_partner_bank_account import (
    check_iban,
    get_bban_from_iban,
    get_iban_part,
    normalize_iban,
    pretty_iban,
)

# Canonical valid Belgian IBAN (Wikipedia example), 16 chars.
VALID_IBAN = "BE68539007547034"


@tagged("post_install", "-at_install")
class TestAccountIban(TransactionCase):
    """Tests for the IBAN helper functions and validation in account_iban."""

    def test_normalize_iban_strips_separators(self):
        """normalize_iban removes spaces and punctuation, keeping alphanumerics."""
        self.assertEqual(normalize_iban("BE68 5390-0754_7034"), VALID_IBAN)

    def test_pretty_iban_groups_valid_in_fours(self):
        """A valid IBAN is reformatted into space-separated groups of four."""
        self.assertEqual(pretty_iban(VALID_IBAN), "BE68 5390 0754 7034")

    def test_pretty_iban_leaves_invalid_untouched(self):
        """Boundary: an invalid IBAN is returned unchanged (no grouping)."""
        self.assertEqual(pretty_iban("XX"), "XX")

    def test_pretty_iban_normalizes_punctuated_input(self):
        """A valid IBAN typed with separators is normalized before grouping."""
        self.assertEqual(pretty_iban("BE68 5390-0754_7034"), "BE68 5390 0754 7034")

    def test_get_bban_from_iban_drops_country_and_check(self):
        """The BBAN is the IBAN without its leading country code and check digits."""
        self.assertEqual(get_bban_from_iban(VALID_IBAN), "539007547034")

    def test_validate_iban_accepts_valid(self):
        """check_iban returns None (no error) for a well-formed IBAN."""
        self.assertIsNone(check_iban(VALID_IBAN))

    def test_validate_iban_empty_raises(self):
        """An empty IBAN is rejected."""
        with self.assertRaises(ValidationError):
            check_iban("")

    def test_validate_iban_unknown_country_raises(self):
        """An IBAN whose country code is not in the template map is rejected."""
        with self.assertRaises(ValidationError):
            check_iban("ZZ68539007547034")

    def test_validate_iban_wrong_length_raises(self):
        """An IBAN of the wrong length for its country is rejected."""
        with self.assertRaises(ValidationError):
            check_iban("BE123")

    def test_validate_iban_bad_check_digits_raises(self):
        """Tampering with the check digits fails the mod-97 validation."""
        with self.assertRaises(ValidationError):
            check_iban("BE69539007547034")

    def test_check_iban_returns_bool(self):
        """res.partner.bank.account.is_valid_iban returns True for valid, False for invalid."""
        Bank = self.env["res.partner.bank.account"]
        self.assertTrue(Bank.is_valid_iban(VALID_IBAN))
        self.assertFalse(Bank.is_valid_iban("not-an-iban"))

    def test_create_does_not_mutate_caller_vals(self):
        """create() must not rewrite acc_number in the caller's own vals dict."""
        partner = self.env["res.partner"].create({"name": "IBAN mutation probe"})
        vals = {"partner_id": partner.id, "acc_number": "BE68 5390-0754_7034"}
        original = dict(vals)
        bank = self.env["res.partner.bank.account"].create(vals)
        self.assertEqual(vals, original)
        self.assertEqual(bank.acc_number, "BE68 5390 0754 7034")

    def test_write_does_not_mutate_caller_vals(self):
        """write() must not rewrite acc_number in the caller's own vals dict."""
        partner = self.env["res.partner"].create({"name": "IBAN mutation probe"})
        bank = self.env["res.partner.bank.account"].create(
            {"partner_id": partner.id, "acc_number": VALID_IBAN}
        )
        vals = {"acc_number": "BE68 5390-0754_7034"}
        original = dict(vals)
        bank.write(vals)
        self.assertEqual(vals, original)
        self.assertEqual(bank.acc_number, "BE68 5390 0754 7034")

    def test_get_iban_part_extracts_masked_segment(self):
        """Docstring example: extract the bank/account segments of an Italian IBAN."""
        it_iban = "IT60X0542811101000000123456"
        self.assertEqual(get_iban_part(it_iban, "bank"), "05428")
        self.assertEqual(get_iban_part(it_iban, "account"), "000000123456")

    def test_get_iban_part_unrecognized_kind_returns_false(self):
        """An unrecognized number_kind returns False, not a falsy string."""
        self.assertIs(get_iban_part(VALID_IBAN, "not_a_kind"), False)

    def test_get_iban_part_unmapped_country_returns_false(self):
        """A country code absent from the template map returns False, not ''."""
        self.assertIs(get_iban_part("ZZ68539007547034", "bank"), False)

    def test_get_bban_returns_bban_for_iban_account(self):
        """get_bban() returns the BBAN for an account whose acc_type is iban."""
        partner = self.env["res.partner"].create({"name": "IBAN mutation probe"})
        bank = self.env["res.partner.bank.account"].create(
            {"partner_id": partner.id, "acc_number": VALID_IBAN}
        )
        self.assertEqual(bank.acc_type, "iban")
        self.assertEqual(bank.get_bban(), "539007547034")

    def test_get_bban_raises_for_non_iban_account(self):
        """get_bban() raises UserError when acc_type is not iban."""
        partner = self.env["res.partner"].create({"name": "IBAN mutation probe"})
        bank = self.env["res.partner.bank.account"].create(
            {"partner_id": partner.id, "acc_number": "not-an-iban"}
        )
        self.assertNotEqual(bank.acc_type, "iban")
        with self.assertRaises(UserError):
            bank.get_bban()

    def test_get_acc_type_detects_iban(self):
        """_get_acc_type() returns 'iban' for a well-formed IBAN."""
        Bank = self.env["res.partner.bank.account"]
        self.assertEqual(Bank._get_acc_type(VALID_IBAN), "iban")

    def test_get_acc_type_falls_back_for_non_iban(self):
        """_get_acc_type() delegates to super() for a non-IBAN account number."""
        Bank = self.env["res.partner.bank.account"]
        self.assertEqual(Bank._get_acc_type("not-an-iban"), "bank")
