# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import re

from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_lk.models.account_move import LK_TAX_INVOICE_MAX_LENGTH


@tagged("post_install", "-at_install", "post_install_l10n")
class TestLkTaxInvoiceSequence(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country("lk")
    def setUpClass(cls):
        super().setUpClass()
        cls.change_company_country(cls.env.company, cls.env.ref("base.lk"))
        cls.env.company.partner_id.write(
            {
                "vat": "12345678901237000",
                "country_id": cls.env.ref("base.lk").id,
            },
        )
        cls.sales_journal = cls.company_data["default_journal_sale"]
        cls.sales_journal.code = "BRN01"

        cls.lk_exempt_group = cls.env["account.tax.group"].search(
            [("country_id.code", "=", "LK"), ("name", "=", "Exempt")],
            limit=1,
        )
        cls.lk_exempt_tax = cls.env["account.tax"].create(
            {
                "name": "0% Exempt (test)",
                "amount": 0,
                "amount_type": "percent",
                "tax_group_id": cls.lk_exempt_group.id,
                "country_id": cls.env.ref("base.lk").id,
                "type_tax_use": "sale",
            },
        )
        cls.lk_group_18 = cls.env["account.tax.group"].search(
            [("country_id.code", "=", "LK"), ("name", "=", "18%")],
            limit=1,
        )
        cls.lk_taxable_tax = cls.env["account.tax"].create(
            {
                "name": "18% (test)",
                "amount": 18,
                "amount_type": "percent",
                "tax_group_id": cls.lk_group_18.id,
                "country_id": cls.env.ref("base.lk").id,
                "type_tax_use": "sale",
            },
        )
        cls.lk_group_zero_rated = cls.env["account.tax.group"].search(
            [("country_id.code", "=", "LK"), ("name", "=", "Zero-rated")],
            limit=1,
        )
        cls.lk_zero_rated_tax = cls.env["account.tax"].create(
            {
                "name": "0% Zero-rated (test)",
                "amount": 0,
                "amount_type": "percent",
                "tax_group_id": cls.lk_group_zero_rated.id,
                "country_id": cls.env.ref("base.lk").id,
                "type_tax_use": "sale",
            },
        )
        cls.lk_group_wht = cls.env["account.tax.group"].search(
            [("country_id.code", "=", "LK"), ("name", "=", "WHT")],
            limit=1,
        )
        cls.lk_wht_tax = cls.env["account.tax"].create(
            {
                "name": "5% WHT (test)",
                "amount": 5,
                "amount_type": "percent",
                "tax_group_id": cls.lk_group_wht.id,
                "country_id": cls.env.ref("base.lk").id,
                "type_tax_use": "sale",
            },
        )
        cls.lk_group_ait = cls.env["account.tax.group"].search(
            [("country_id.code", "=", "LK"), ("name", "=", "AIT")],
            limit=1,
        )
        cls.lk_ait_tax = cls.env["account.tax"].create(
            {
                "name": "2% AIT (test)",
                "amount": 2,
                "amount_type": "percent",
                "tax_group_id": cls.lk_group_ait.id,
                "country_id": cls.env.ref("base.lk").id,
                "type_tax_use": "sale",
            },
        )

    def _create_lk_invoice(self, invoice_date, post=True, journal=None):
        return self._create_invoice(
            move_type="out_invoice",
            invoice_date=invoice_date,
            post=post,
            journal_id=journal or self.sales_journal,
        )

    def _open_resequence_wizard(self, invoices, first_name="26MAY_X1_00010"):
        wizard = Form(
            self.env["account.resequence.wizard"].with_context(
                active_ids=invoices.ids,
                active_model="account.move",
            ),
        )
        wizard.first_name = first_name
        return wizard

    # ----------------------------------------
    # Sequence Format Generation
    # ----------------------------------------

    def test_sequence_progression(self):
        """LK sequences start at 00001, continue across months and years."""
        inv1 = self._create_lk_invoice("2025-12-31")
        self.assertEqual(inv1.name, "25DEC_BRN01_00001")

        inv2 = self._create_lk_invoice("2026-01-01")
        self.assertEqual(inv2.name, "26JAN_BRN01_00002", "Sequence should continue across years")

        inv3 = self._create_lk_invoice("2026-05-15")
        self.assertEqual(inv3.name, "26MAY_BRN01_00003", "Sequence should continue across months")

        inv4 = self._create_lk_invoice("2026-05-20")
        self.assertEqual(inv4.name, "26MAY_BRN01_00004", "Sequence should increment within a month")

    def test_all_month_abbreviations(self):
        """Verify all 12 months produce correct three-letter abbreviations."""
        expected = [
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
                invoice.name.startswith(expected[month_num - 1]),
                f"Month {month_num:02d}: {invoice.name} should start with {expected[month_num - 1]}",
            )

    # ----------------------------------------
    # Journal Code Handling
    # ----------------------------------------

    def test_journal_code_handling(self):
        """Journal codes are used as-is in the sequence (case, digits, hyphens)."""
        for code, expected in [
            ("lowcode", "26MAY_lowcode_00001"),
            ("BR24X", "26MAY_BR24X_00001"),
            ("BR-NC", "26MAY_BR-NC_00001"),
        ]:
            journal = self.sales_journal.copy({"code": code})
            invoice = self._create_lk_invoice("2026-05-15", journal=journal)
            self.assertEqual(invoice.name, expected)

        max_code = "A" * 5
        journal = self.sales_journal.copy({"code": max_code})
        invoice = self._create_lk_invoice("2026-05-15", journal=journal)
        self.assertIn(max_code, invoice.name)

    # ----------------------------------------
    # Starting Sequence and Format Params
    # ----------------------------------------

    def test_get_starting_sequence_format(self):
        """Initial LK sequence is YYMMM_JOURNAL_00000."""
        invoice = self._create_lk_invoice("2026-05-15", post=False)
        self.assertEqual(
            invoice._get_starting_sequence(),
            "26MAY_BRN01_00000",
        )

    def test_sequence_format_params(self):
        """Verify _get_sequence_format_param / _get_next_sequence_format
        return all expected values from the invoice date."""
        invoice = self._create_lk_invoice("2026-05-15")
        fmt, vals = invoice._get_sequence_format_param(invoice.name)
        expected_keys = {
            "year",
            "year_length",
            "year_end",
            "year_end_length",
            "month",
            "month_abbr",
            "journal_code",
            "seq",
            "seq_length",
            "suffix",
        }
        self.assertEqual(
            set(vals.keys()),
            expected_keys,
            "Should return all format parameters",
        )
        self.assertEqual(vals["year"], 26)
        self.assertEqual(vals["month"], 5)
        self.assertEqual(vals["month_abbr"], "MAY")
        self.assertEqual(vals["journal_code"], "BRN01")
        self.assertEqual(vals["seq"], 1)

        fmt, vals = invoice._get_next_sequence_format()
        self.assertEqual(vals["year"], 26, "Year should be 2-digit from invoice date")
        self.assertEqual(vals["month"], 5, "Month should match invoice date")
        self.assertEqual(vals["month_abbr"], "MAY", "Month abbr should match invoice date")
        formatted = fmt.format(**vals)
        self.assertLessEqual(len(formatted), LK_TAX_INVOICE_MAX_LENGTH)

    def test_sequence_format_param_non_lk_falls_back(self):
        """Verify _get_sequence_format_param falls back to super for non-LK."""
        self.change_company_country(self.env.company, self.env.ref("base.us"))
        us_invoice = self._create_invoice(move_type="out_invoice", invoice_date="2026-05-15", post=True)
        _fmt, vals = us_invoice._get_sequence_format_param(us_invoice.name)
        self.assertNotIn("month_abbr", vals)

    def test_manual_sequence_change_updates_next_numbers(self):
        """After manually renaming an invoice, the next number picks up from there."""
        invoice = self._create_lk_invoice("2026-05-15")
        invoice.name = "26MAY_R2_00500"
        next_invoice = self._create_lk_invoice("2026-05-16")
        self.assertEqual(next_invoice.name, "26MAY_R2_00501")

    # ----------------------------------------
    # Sequence Date Validation
    # ----------------------------------------

    def test_sequence_matches_date(self):
        """LK sequence matches its invoice date."""
        invoice = self._create_lk_invoice("2026-05-15")
        self.assertTrue(invoice._sequence_matches_date())

    def test_sequence_matches_date_handles_missing_name(self):
        """Verify _sequence_matches_date handles missing or empty names gracefully."""
        for name in (None, ""):
            invoice = self.env["account.move"].new(
                {
                    "name": name,
                    "date": "2026-05-15",
                    "move_type": "out_invoice",
                },
            )
            self.assertIsInstance(invoice._sequence_matches_date(), bool)

    def test_sequence_wrong_month_year_does_not_match(self):
        """Sequence with the wrong month or year fails to match."""
        for name in ("26JUN_BRN01_00001", "27MAY_BRN01_00001"):
            invoice = self.env["account.move"].new(
                {
                    "name": name,
                    "date": "2026-05-15",
                    "move_type": "out_invoice",
                },
            )
            self.assertFalse(invoice._sequence_matches_date())

    # ----------------------------------------
    # Sequence Never Resets
    # ----------------------------------------

    def test_sequence_number_reset_is_never(self):
        """LK sequences never reset."""
        invoice = self._create_lk_invoice("2026-05-15")
        self.assertEqual(
            invoice._deduce_sequence_number_reset(invoice.name),
            "never",
        )

    # ----------------------------------------
    # Max Length Enforcement
    # ----------------------------------------

    def test_constrains_l10n_lk_sequence_length(self):
        """Verify the max length constraint at the boundary (40 chars) and when exceeded."""
        invoice = self._create_lk_invoice("2026-05-15", post=False)
        valid_name = "26MAY_BRN01_0000000000000000000000000000"
        self.assertEqual(len(valid_name), 40)
        invoice.write({"name": valid_name})

        invalid_name = "26MAY_BRN01_000000000000000000000000000000000"
        with self.assertRaises(UserError):
            invoice.write({"name": invalid_name})

    # ----------------------------------------
    # _get_last_sequence
    # ----------------------------------------

    def test_get_last_sequence(self):
        """Verify _get_last_sequence returns the previous LK sequence,
        excluding the origin invoice, and handles NewId records."""
        self._create_lk_invoice("2026-05-15")
        inv2 = self._create_lk_invoice("2026-05-20")

        self.assertEqual(
            inv2._get_last_sequence(),
            "26MAY_BRN01_00001",
            "Should return the previous LK sequence",
        )

        new_record = self.env["account.move"].new(
            {
                "move_type": "out_invoice",
                "journal_id": self.sales_journal.id,
                "company_id": self.env.company.id,
                "partner_id": self.partner.id,
                "invoice_date": "2026-05-21",
            },
        )
        self.assertEqual(
            new_record._get_last_sequence(),
            "26MAY_BRN01_00002",
            "Should return the last posted LK sequence without raising",
        )

    def test_get_last_sequence_non_lk(self):
        """Verify _get_last_sequence delegates to super for non-LK."""
        self.change_company_country(self.env.company, self.env.ref("base.us"))
        us_invoice = self._create_invoice(move_type="out_invoice", invoice_date="2026-05-15", post=True)
        self.assertEqual(
            us_invoice.name,
            f"{us_invoice.journal_id.code}/2026/00001",
            "Non-LK invoices should not use LK sequence format",
        )

    # ----------------------------------------
    # _lk_sql_seq_regex
    # ----------------------------------------

    def test_lk_sql_seq_regex(self):
        """Verify the transformed regex is PSQL-safe and still matches valid LK sequences."""
        psql_regex = self.env["account.move"]._lk_sql_seq_regex()
        self.assertNotIn(
            "?P<",
            psql_regex,
            "PSQL-safe regex should not have named groups",
        )
        self.assertNotIn(
            "*?",
            psql_regex,
            "PSQL-safe regex should not have lazy quantifiers",
        )
        self.assertTrue(
            re.match(psql_regex, "26MAY_BRN01_00001"),
            "Should match valid LK sequence",
        )
        self.assertTrue(
            re.match(psql_regex, "26JUN_BR24X1_00001"),
            "Should match sequence with digits in journal code",
        )

    # ----------------------------------------
    # Non-LK Documents
    # ----------------------------------------

    def test_non_lk_documents_do_not_use_lk_sequence(self):
        """Refunds, vendor bills and receipts should not use the LK tax invoice sequence."""
        self.assertFalse(
            self.env["account.move"].with_context(default_move_type="out_refund")._l10n_lk_use_tax_invoice_sequence(),
            "Refunds should not use LK tax invoice sequence",
        )
        self.assertFalse(
            self.env["account.move"].with_context(default_move_type="in_invoice")._l10n_lk_use_tax_invoice_sequence(),
            "Vendor bills should not use LK tax invoice sequence",
        )
        product = self.env["product.product"].create({"name": "Test Product"})
        receipt = self.env["account.move"].create(
            {
                "move_type": "out_receipt",
                "partner_id": self.partner_a.id,
                "journal_id": self.sales_journal.id,
                "invoice_date": "2026-05-15",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "name": "Test Line",
                            "quantity": 1,
                            "price_unit": 100,
                        },
                    ),
                ],
            },
        )
        self.assertFalse(
            receipt._l10n_lk_use_tax_invoice_sequence(),
            "Receipts should not use LK sequence",
        )
        receipt.action_post()
        self.assertNotRegex(
            r"^\d{2}[A-Z]{3}_[A-Z0-9]+_\d+",
            receipt.name or "",
            "Receipt name should not match LK sequence pattern",
        )

    # ----------------------------------------
    # Report Name Routing
    # ----------------------------------------

    def test_get_name_invoice_report_lk(self):
        """LK invoices use a custom report template."""
        invoice = self._create_lk_invoice("2026-05-15", post=False)
        self.assertEqual(
            invoice._get_name_invoice_report(),
            "l10n_lk.report_invoice_document",
        )

    def test_get_name_invoice_report_non_lk(self):
        """Non-LK invoices use a standard report template."""
        self.change_company_country(self.env.company, self.env.ref("base.us"))
        us_invoice = self._create_invoice(
            move_type="out_invoice",
            invoice_date="2026-05-15",
        )
        self.assertEqual(
            us_invoice._get_name_invoice_report(),
            "account.report_invoice_document",
        )

    # ----------------------------------------
    # VAT Registration Fields
    # ----------------------------------------

    def test_vat_suffix_auto_detection(self):
        """l10n_lk_vat_registered is computed from VAT number suffix."""
        company_partner = self.env.company.partner_id
        company_partner.vat = "1234567897000"
        self.assertTrue(self.env.company.l10n_lk_vat_registered)

        company_partner.vat = "1234567890000"
        self.assertFalse(self.env.company.l10n_lk_vat_registered)

        company_partner.vat = "123456789"
        self.assertFalse(self.env.company.l10n_lk_vat_registered)

    # ----------------------------------------
    # Tax Invoice Qualification (_l10n_lk_is_tax_invoice_company)
    # Controls whether the PDF shows "Tax Invoice" / "Supply Date" etc.
    # ----------------------------------------

    def test_tax_invoice_requires_both_vat_registered(self):
        """Both company and partner must be VAT-registered."""
        invoice = self._create_lk_invoice("2026-05-15", post=False)

        self.env.company.l10n_lk_vat_registered = False
        invoice.partner_id.l10n_lk_vat_registered = False
        self.assertFalse(invoice._l10n_lk_is_tax_invoice_company())

        self.env.company.l10n_lk_vat_registered = True
        self.assertFalse(invoice._l10n_lk_is_tax_invoice_company())

        invoice.partner_id.l10n_lk_vat_registered = True
        self.assertTrue(invoice._l10n_lk_is_tax_invoice_company())

    def test_non_lk_country_not_tax_invoice(self):
        """Non-LK country invoices are not tax invoices."""
        self.change_company_country(self.env.company, self.env.ref("base.us"))
        invoice = self._create_invoice_one_line(
            invoice_date="2026-05-15",
            product_id=self.product_a.id,
            tax_ids=[self.lk_taxable_tax.id],
        )
        self.env.company.l10n_lk_vat_registered = True
        invoice.partner_id.l10n_lk_vat_registered = True
        self.assertFalse(invoice._l10n_lk_is_tax_invoice_company())

    def test_tax_invoice_requires_taxable_taxes(self):
        """A single product line qualifies when 18%/zero-rated, and not
        otherwise (no tax, exempt only, mixed exempt/taxable)."""
        self.env.company.l10n_lk_vat_registered = True
        invoice = self._create_invoice_one_line(
            invoice_date="2026-05-15",
            product_id=self.product_a.id,
            tax_ids=[self.lk_taxable_tax.id],
        )
        invoice.partner_id.l10n_lk_vat_registered = True

        self.assertTrue(invoice._l10n_lk_is_tax_invoice_company())

        invoice.invoice_line_ids.tax_ids = self.lk_taxable_tax | self.lk_zero_rated_tax
        self.assertTrue(invoice._l10n_lk_is_tax_invoice_company())

        invoice.invoice_line_ids.tax_ids = self.lk_zero_rated_tax
        self.assertTrue(invoice._l10n_lk_is_tax_invoice_company())

        invoice.invoice_line_ids.tax_ids = self.lk_exempt_tax
        self.assertFalse(invoice._l10n_lk_is_tax_invoice_company())

        invoice.invoice_line_ids.tax_ids = self.lk_exempt_tax | self.lk_taxable_tax
        self.assertFalse(invoice._l10n_lk_is_tax_invoice_company())

        invoice.invoice_line_ids.tax_ids = False
        self.assertFalse(invoice._l10n_lk_is_tax_invoice_company())

    def test_multi_line_taxable_and_other_lines_not_tax_invoice(self):
        """Mixed product lines (taxable + exempt/untaxed) are not tax invoices."""
        self.env.company.l10n_lk_vat_registered = True
        invoice = self._create_invoice(
            invoice_date="2026-05-15",
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=self.product_a.id,
                    tax_ids=[self.lk_taxable_tax.id],
                ),
                self._prepare_invoice_line(
                    product_id=self.product_b.id,
                    tax_ids=[self.lk_exempt_tax.id],
                ),
            ],
        )
        invoice.partner_id.l10n_lk_vat_registered = True
        self.assertFalse(invoice._l10n_lk_is_tax_invoice_company())

        invoice.invoice_line_ids.filtered(lambda line: line.product_id == self.product_b).tax_ids = False
        self.assertFalse(invoice._l10n_lk_is_tax_invoice_company())

    def test_wht_ait_taxes_do_not_block_tax_invoice(self):
        """WHT/AIT taxes on a line do not disqualify an otherwise taxable
        invoice (reviewer cases 1-3)."""
        self.env.company.l10n_lk_vat_registered = True
        invoice = self._create_invoice(
            invoice_date="2026-05-15",
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=self.product_a.id,
                    tax_ids=[self.lk_taxable_tax.id, self.lk_wht_tax.id],
                ),
                self._prepare_invoice_line(
                    product_id=self.product_b.id,
                    tax_ids=[self.lk_taxable_tax.id],
                ),
            ],
        )
        invoice.partner_id.l10n_lk_vat_registered = True
        self.assertTrue(
            invoice._l10n_lk_is_tax_invoice_company(),
            "18% + WHT on one line and 18% on the other is a tax invoice",
        )

        invoice.invoice_line_ids.filtered(lambda line: line.product_id == self.product_b).tax_ids = self.lk_ait_tax
        self.assertFalse(
            invoice._l10n_lk_is_tax_invoice_company(),
            "A line with WHT/AIT only is not a taxable supply (case 1)",
        )

        invoice.invoice_line_ids.filtered(lambda line: line.product_id == self.product_b).tax_ids = self.lk_exempt_tax
        self.assertFalse(
            invoice._l10n_lk_is_tax_invoice_company(),
            "An exempt line is still not a tax invoice (case 3)",
        )

    def test_commercial_partner_vat_status_used_for_tax_invoice(self):
        """The customer VAT status comes from the commercial partner, not the
        invoice's contact."""
        self.env.company.l10n_lk_vat_registered = True
        customer = self.env["res.partner"].create(
            {
                "name": "LK Customer",
                "is_company": True,
                "country_id": self.env.ref("base.lk").id,
                "vat": "12345678901237000",
            },
        )
        self.assertTrue(
            customer.l10n_lk_vat_registered,
            "LK company with vat ending in 7000 is VAT-registered",
        )
        contact = self.env["res.partner"].create(
            {
                "name": "Contact",
                "parent_id": customer.id,
                "type": "contact",
            },
        )
        contact.l10n_lk_vat_registered = False
        self.assertFalse(
            contact.l10n_lk_vat_registered,
            "The contact itself is not VAT-registered (flag unchecked)",
        )
        self.assertTrue(
            customer.l10n_lk_vat_registered,
            "The commercial partner still is VAT-registered",
        )
        invoice = self._create_invoice_one_line(
            invoice_date="2026-05-15",
            product_id=self.product_a.id,
            tax_ids=[self.lk_taxable_tax.id],
            partner_id=contact.id,
        )
        self.assertEqual(invoice.partner_id.commercial_partner_id, customer)
        self.assertTrue(
            invoice._l10n_lk_is_tax_invoice_company(),
            "Child contact without VAT flag still uses commercial partner status",
        )
        customer.vat = False
        self.assertFalse(
            invoice._l10n_lk_is_tax_invoice_company(),
            "Unregistered commercial partner means no tax invoice",
        )

    def test_debit_note_is_not_tax_invoice(self):
        """Debit notes are not tax invoices in terms of wording."""
        self.env.company.l10n_lk_vat_registered = True
        invoice = self._create_invoice_one_line(
            invoice_date="2026-05-15",
            product_id=self.product_a.id,
            tax_ids=[self.lk_taxable_tax.id],
        )
        invoice.partner_id.l10n_lk_vat_registered = True
        self.assertTrue(invoice._l10n_lk_is_tax_invoice_company())

        if "debit_origin_id" not in self.env["account.move"]._fields:
            self.skipTest("account_debit_note module not installed")
        invoice.write({"debit_origin_id": invoice.id})
        self.assertFalse(invoice._l10n_lk_is_tax_invoice_company())

    def test_section_and_note_lines_ignored_by_has_taxable_taxes(self):
        """Sections and notes are not counted; an invoice is a tax invoice only
        when it has taxable product lines."""
        invoice = self._create_invoice_one_line(
            invoice_date="2026-05-15",
            product_id=self.product_a.id,
            tax_ids=[self.lk_taxable_tax.id],
        )
        self.env.company.l10n_lk_vat_registered = True
        invoice.partner_id.l10n_lk_vat_registered = True
        self.env["account.move.line"].create(
            [
                {
                    "move_id": invoice.id,
                    "display_type": "line_section",
                    "name": "Section Header",
                },
                {
                    "move_id": invoice.id,
                    "display_type": "line_note",
                    "name": "Note",
                },
            ],
        )
        self.assertTrue(
            invoice._l10n_lk_is_tax_invoice_company(),
            "Section/note lines should not prevent a tax invoice",
        )

        invoice.invoice_line_ids.filtered(lambda line: line.display_type == "product").tax_ids = False
        self.assertFalse(
            invoice._l10n_lk_is_tax_invoice_company(),
            "Section/note lines alone should not make a tax invoice",
        )

    # ----------------------------------------
    # Resequence
    # ----------------------------------------

    def test_resequence_updates_month_abbr_on_boundary(self):
        """A resequencing spanning two months must use each record's actual month."""
        invoices = self._create_lk_invoice("2026-05-31") + self._create_lk_invoice("2026-06-01")

        resequence_wizard = self._open_resequence_wizard(invoices, "26MAY_X1_00010")
        new_values = json.loads(resequence_wizard.new_values)

        self.assertEqual(
            new_values[str(invoices[0].id)]["new_by_name"],
            "26MAY_X1_00010",
            "May invoice should keep May abbreviation",
        )
        self.assertEqual(
            new_values[str(invoices[1].id)]["new_by_name"],
            "26JUN_X1_00011",
            "June invoice should have June abbreviation",
        )

        resequence_wizard.save().resequence()
        self.assertEqual(
            invoices[0].name,
            "26MAY_X1_00010",
            "First invoice should have May in name",
        )
        self.assertEqual(
            invoices[1].name,
            "26JUN_X1_00011",
            "Second invoice should have June in name",
        )

    def test_resequence_preserves_journal_code(self):
        """Resequence preserves the journal code in the sequence."""
        journal = self.sales_journal.copy({"code": "BRANCH1"})
        invoices = self._create_lk_invoice("2026-05-15", journal=journal)
        invoices += self._create_lk_invoice("2026-05-20", journal=journal)

        resequence_wizard = self._open_resequence_wizard(
            invoices,
            "26MAY_BRANCH1_00100",
        )
        new_values = json.loads(resequence_wizard.new_values)

        self.assertEqual(
            new_values[str(invoices[0].id)]["new_by_name"],
            "26MAY_BRANCH1_00100",
        )
        self.assertEqual(
            new_values[str(invoices[1].id)]["new_by_name"],
            "26MAY_BRANCH1_00101",
        )

    def test_resequence_by_date_sorting(self):
        """By-date view orders by date; earlier date gets lower seq."""
        invoices = self._create_lk_invoice("2026-05-20") + self._create_lk_invoice("2026-05-15")

        resequence_wizard = self._open_resequence_wizard(invoices, "26MAY_X1_00010")
        new_values = json.loads(resequence_wizard.new_values)

        self.assertEqual(
            new_values[str(invoices[1].id)]["new_by_date"],
            "26MAY_X1_00010",
        )
        self.assertEqual(
            new_values[str(invoices[0].id)]["new_by_date"],
            "26MAY_X1_00011",
        )

    def test_resequence_by_date_cross_month_uses_per_record_abbr(self):
        """By-date resequence spanning months assigns the correct month abbreviation per record."""
        inv1 = self._create_lk_invoice("2026-05-20")
        inv2 = self._create_lk_invoice("2026-05-15")
        inv3 = self._create_lk_invoice("2026-06-15")
        invoices = inv1 + inv2 + inv3

        resequence_wizard = self._open_resequence_wizard(invoices, "26MAY_X1_00010")
        new_values = json.loads(resequence_wizard.new_values)

        self.assertEqual(
            new_values[str(inv2.id)]["new_by_date"],
            "26MAY_X1_00010",
        )
        self.assertEqual(
            new_values[str(inv1.id)]["new_by_date"],
            "26MAY_X1_00011",
        )
        self.assertEqual(
            new_values[str(inv3.id)]["new_by_date"],
            "26JUN_X1_00012",
        )

    def test_resequence_draft_without_name_no_crash(self):
        """Resequencing with draft invoices without names does not crash."""
        lk_invoice = self._create_lk_invoice("2026-05-15")
        draft = self._create_lk_invoice("2026-05-20", post=False)
        draft.name = False

        resequence_wizard = self._open_resequence_wizard(
            lk_invoice + draft,
            "26MAY_X1_00010",
        )
        new_values = json.loads(resequence_wizard.new_values)

        self.assertEqual(
            new_values[str(draft.id)]["new_by_name"],
            "26MAY_X1_00010",
        )
        self.assertEqual(
            new_values[str(lk_invoice.id)]["new_by_name"],
            "26MAY_X1_00011",
        )

    # ----------------------------------------
    # Sequence Chain Integrity
    # ----------------------------------------

    def test_sequence_chain_integrity(self):
        """Verify last/end-of-chain detection across months and journals."""
        journal2 = self.sales_journal.copy({"code": "BANK2"})
        inv1 = self._create_lk_invoice("2026-05-15")
        inv2 = self._create_lk_invoice("2026-06-15")
        inv3 = self._create_lk_invoice("2026-06-20")
        inv4 = self._create_lk_invoice("2026-05-15", journal=journal2)
        self.assertTrue(inv3._is_last_from_seq_chain())
        self.assertFalse(inv1._is_last_from_seq_chain())
        self.assertTrue((inv2 + inv3 + inv4)._is_end_of_seq_chain())
        self.assertFalse((inv1 + inv3)._is_end_of_seq_chain())
        self.assertFalse((inv1 + inv2)._is_end_of_seq_chain())
