# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.tests import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install", "post_install_l10n")
class TestLkTaxInvoiceSequence(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country("lk")
    def setUpClass(cls):
        super().setUpClass()
        cls.change_company_country(cls.env.company, cls.env.ref("base.lk"))
        cls.sales_journal = cls.company_data["default_journal_sale"]
        cls.sales_journal.code = "BRN01"

    def _create_lk_invoice(self, invoice_date, post=True, journal=None):
        return self._create_invoice(
            move_type="out_invoice",
            invoice_date=invoice_date,
            post=post,
            journal_id=journal or self.sales_journal,
        )

    def test_default_lk_tax_invoice_sequence_format(self):
        """Test default invoice serial number format: YYMMM_QQQQ_XXXXX."""
        invoice = self._create_lk_invoice("2026-05-15")
        self.assertEqual(invoice.name, "26MAY_BRN01_00001")

    def test_consecutive_invoices_same_month(self):
        """Test that consecutive invoices in the same month increment correctly."""
        inv1 = self._create_lk_invoice("2026-05-15")
        inv2 = self._create_lk_invoice("2026-05-20")
        self.assertEqual(inv1.name, "26MAY_BRN01_00001")
        self.assertEqual(inv2.name, "26MAY_BRN01_00002")

    def test_sequence_continues_on_month_boundary(self):
        """Test that sequence continues when crossing month boundary."""
        inv1 = self._create_lk_invoice("2026-05-31")
        inv2 = self._create_lk_invoice("2026-06-01")
        self.assertEqual(inv1.name, "26MAY_BRN01_00001")
        self.assertEqual(inv2.name, "26JUN_BRN01_00002")

    def test_manual_sequence_change_updates_next_numbers(self):
        """Test that manually changing invoice number updates subsequent numbers."""
        self.env.company.document_sequence_editable = True
        invoice = self._create_lk_invoice("2026-05-15")
        invoice.name = "26MAY_R2_00500"

        next_invoice = self._create_lk_invoice("2026-05-16")
        self.assertEqual(next_invoice.name, "26MAY_R2_00501")

    def test_journal_code_used_as_qqqq(self):
        """Test that journal code is used as QQQQ component."""
        journal = self.sales_journal.copy({"code": "CUSTOM"})
        invoice = self._create_lk_invoice("2026-05-15", journal=journal)
        self.assertEqual(invoice.name, "26MAY_CUSTOM_00001")

    def test_journal_code_uppercase_conversion(self):
        """Test that lowercase journal codes are converted to uppercase."""
        journal = self.sales_journal.copy({"code": "lowcode"})
        invoice = self._create_lk_invoice("2026-05-15", journal=journal)
        self.assertEqual(invoice.name, "26MAY_LOWCODE_00001")

    def test_qqqq_with_mixed_alphanumeric(self):
        """Test that QQQQ accepts mixed alphanumeric codes."""
        journal = self.sales_journal.copy({"code": "BR24X1"})
        invoice = self._create_lk_invoice("2026-05-15", journal=journal)
        self.assertEqual(invoice.name, "26MAY_BR24X1_00001")

    def test_resequence_uses_lk_month_abbr(self):
        """Test resequence wizard keeps continuous numbering with LK month abbreviations."""
        invoices = self._create_lk_invoice("2026-05-31") + self._create_lk_invoice(
            "2026-06-01",
        )

        resequence_wizard = Form(
            self.env["account.resequence.wizard"].with_context(
                active_ids=invoices.ids,
                active_model="account.move",
            ),
        )
        resequence_wizard.first_name = "26MAY_X1_00010"
        new_values = json.loads(resequence_wizard.new_values)

        self.assertEqual(
            new_values[str(invoices[0].id)]["new_by_name"], "26MAY_X1_00010",
        )
        self.assertEqual(
            new_values[str(invoices[1].id)]["new_by_name"], "26JUN_X1_00011",
        )

        resequence_wizard.save().resequence()
        self.assertEqual(invoices[0].name, "26MAY_X1_00010")
        self.assertEqual(invoices[1].name, "26JUN_X1_00011")

    def test_resequence_preserves_qqqq(self):
        """Test that resequence preserves the QQQQ code across invoices."""
        journal = self.sales_journal.copy({"code": "BRANCH1"})
        invoices = self._create_lk_invoice(
            "2026-05-15", journal=journal,
        ) + self._create_lk_invoice("2026-05-20", journal=journal)

        resequence_wizard = Form(
            self.env["account.resequence.wizard"].with_context(
                active_ids=invoices.ids,
                active_model="account.move",
            ),
        )
        resequence_wizard.first_name = "26MAY_BRANCH1_00100"
        new_values = json.loads(resequence_wizard.new_values)

        self.assertEqual(
            new_values[str(invoices[0].id)]["new_by_name"], "26MAY_BRANCH1_00100",
        )
        self.assertEqual(
            new_values[str(invoices[1].id)]["new_by_name"], "26MAY_BRANCH1_00101",
        )

    def test_all_month_abbreviations(self):
        """Test that all 12 months generate correct abbreviations."""
        expected_months = [
            "26JAN",
            "26FEB",
            "26MAR",
            "26APR",
            "26MAY",
            "26JUN",
            "26JUL",
            "26AUG",
            "26SEP",
            "26OCT",
            "26NOV",
            "26DEC",
        ]
        for month_num in range(1, 13):
            invoice = self._create_lk_invoice(f"2026-{month_num:02d}-15")
            self.assertTrue(
                invoice.name.startswith(expected_months[month_num - 1]),
                f"Month {month_num:02d}: {invoice.name} should start with {expected_months[month_num - 1]}",
            )

    def test_tax_invoice_vat_registration(self):
        """Test that tax invoice detection requires both company and partner VAT registration."""
        invoice = self._create_lk_invoice("2026-05-15", post=False)

        # Neither registered
        self.env.company.l10n_lk_vat_registered = False
        invoice.partner_id.l10n_lk_vat_registered = False
        self.assertFalse(invoice._l10n_lk_is_tax_invoice_company())

        # Only company registered
        self.env.company.l10n_lk_vat_registered = True
        self.assertFalse(invoice._l10n_lk_is_tax_invoice_company())

        # Both registered
        invoice.partner_id.l10n_lk_vat_registered = True
        self.assertTrue(invoice._l10n_lk_is_tax_invoice_company())

    def test_vat_suffix_auto_detection(self):
        """Test that VAT suffix 7000 auto-sets vat_registered."""
        company_partner = self.env.company.partner_id
        company_partner.vat = "1234567897000"
        self.assertTrue(self.env.company.l10n_lk_vat_registered)

        company_partner.vat = "1234567890000"
        self.assertFalse(self.env.company.l10n_lk_vat_registered)

        # 9-digit TIN (no suffix)
        company_partner.vat = "123456789"
        self.assertFalse(self.env.company.l10n_lk_vat_registered)
