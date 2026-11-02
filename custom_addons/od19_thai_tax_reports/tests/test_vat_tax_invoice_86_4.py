# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Tests for Section 86/4 - full-form tax invoice required particulars."""
from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from ..models.account_move import OD19_SKIP_86_4_CONTEXT


@tagged("post_install", "-at_install")
class TestVatTaxInvoice864(TransactionCase):
    """A full-form tax invoice issued to a VAT-registered buyer must carry
    all 8 particulars required by Section 86/4 before it can be posted."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.od19_enforce_86_4_validation = True

        # Seller (company partner) must be complete: name / address / tax ID
        # and a branch number so item (8) is satisfied.
        cls.company.partner_id.write(
            {
                "street": "1 Moo 1 Vibhavadi Rangsit Road",
                "vat": "0105555555554",
                "company_registry": "00000",
            }
        )
        cls.th_country = cls.env.ref("base.th")
        cls.company.partner_id.country_id = cls.th_country

        # A fully-compliant VAT-registered buyer.
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Compliant Buyer Co., Ltd.",
                "company_type": "company",
                "street": "99 Moo 9 Rama IX Road",
                "vat": "0105555555562",
                "company_registry": "00001",
                "country_id": cls.th_country.id,
            }
        )
        # A retail consumer (no tax ID) -> abbreviated form allowed.
        cls.consumer = cls.env["res.partner"].create(
            {"name": "Walk-in Customer", "company_type": "person"}
        )

        cls.sale_tax = cls.company.account_sale_tax_id
        if not cls.sale_tax:
            cls.sale_tax = cls.env["account.tax"].create(
                {
                    "name": "Test Output VAT 7%",
                    "amount_type": "percent",
                    "amount": 7.0,
                    "type_tax_use": "sale",
                    "company_id": cls.company.id,
                }
            )
        cls.income_account = cls.env["account.account"].search(
            [
                ("account_type", "=", "income"),
                ("company_ids", "in", cls.company.id),
            ],
            limit=1,
        )
        cls._seq = 0

    def _create_invoice(self, partner, move_type="out_invoice", with_tax=True):
        self.__class__._seq += 1
        return self.env["account.move"].create(
            {
                "move_type": move_type,
                "partner_id": partner.id,
                "invoice_date": fields.Date.from_string("2026-03-15"),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Consulting service #%03d" % self.__class__._seq,
                            "quantity": 1.0,
                            "price_unit": 10000.0,
                            "account_id": self.income_account.id,
                            "tax_ids": [
                                (6, 0, [self.sale_tax.id] if with_tax else [])
                            ],
                        },
                    )
                ],
            }
        )

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    def test_validation_enabled_by_default(self):
        self.assertTrue(
            self.env["res.company"]._fields["od19_enforce_86_4_validation"].default
        )
        self.assertTrue(self.company.od19_enforce_86_4_validation)

    def test_requires_full_tax_invoice_for_vat_buyer(self):
        invoice = self._create_invoice(self.partner)
        self.assertTrue(invoice._od19_requires_full_tax_invoice())

    def test_consumer_invoice_does_not_require_full_form(self):
        invoice = self._create_invoice(self.consumer, with_tax=True)
        self.assertFalse(invoice._od19_requires_full_tax_invoice())

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------
    def test_complete_tax_invoice_posts(self):
        invoice = self._create_invoice(self.partner)
        self.assertEqual(invoice._od19_tax_invoice_missing_items(), [])
        invoice.action_post()
        self.assertEqual(invoice.state, "posted")

    def test_credit_note_is_validated_too(self):
        invoice = self._create_invoice(self.partner, move_type="out_refund")
        self.assertTrue(invoice._od19_requires_full_tax_invoice())
        invoice.action_post()
        self.assertEqual(invoice.state, "posted")

    # ------------------------------------------------------------------
    # Missing particulars
    # ------------------------------------------------------------------
    def test_missing_buyer_address_raises(self):
        buyer = self.env["res.partner"].create(
            {
                "name": "No Address Buyer Co., Ltd.",
                "company_type": "company",
                "vat": "0105555555571",
                "company_registry": "00002",
                "country_id": self.th_country.id,
            }
        )
        invoice = self._create_invoice(buyer)
        with self.assertRaises(UserError) as ctx:
            invoice.action_post()
        self.assertIn("86/4", str(ctx.exception))
        self.assertIn("(3)", str(ctx.exception))
        self.assertEqual(invoice.state, "draft")

    def test_missing_buyer_tax_id_skips_validation(self):
        """A buyer without a tax ID is not treated as a full-form case, so
        the invoice posts even though the address is incomplete."""
        buyer = self.env["res.partner"].create(
            {"name": "No Tax ID Buyer", "company_type": "company"}
        )
        invoice = self._create_invoice(buyer)
        self.assertFalse(invoice._od19_requires_full_tax_invoice())
        invoice.action_post()
        self.assertEqual(invoice.state, "posted")

    def test_missing_seller_address_raises(self):
        self.company.partner_id.street = False
        invoice = self._create_invoice(self.partner)
        with self.assertRaises(UserError) as ctx:
            invoice.action_post()
        self.assertIn("(2)", str(ctx.exception))

    def test_invoice_without_vat_line_skips_validation(self):
        """No output VAT line -> not a full-form tax invoice obligation."""
        invoice = self._create_invoice(self.partner, with_tax=False)
        self.assertFalse(invoice._od19_requires_full_tax_invoice())

    # ------------------------------------------------------------------
    # Bypass mechanisms
    # ------------------------------------------------------------------
    def test_context_flag_bypasses_validation(self):
        buyer = self.env["res.partner"].create(
            {
                "name": "Bypass Buyer",
                "company_type": "company",
                "vat": "0105555555589",
            }
        )
        invoice = self._create_invoice(buyer)
        invoice.with_context(**{OD19_SKIP_86_4_CONTEXT: True}).action_post()
        self.assertEqual(invoice.state, "posted")

    def test_disabling_setting_bypasses_validation(self):
        self.company.od19_enforce_86_4_validation = False
        buyer = self.env["res.partner"].create(
            {
                "name": "Setting Off Buyer",
                "company_type": "company",
                "vat": "0105555555597",
            }
        )
        invoice = self._create_invoice(buyer)
        invoice.action_post()
        self.assertEqual(invoice.state, "posted")
