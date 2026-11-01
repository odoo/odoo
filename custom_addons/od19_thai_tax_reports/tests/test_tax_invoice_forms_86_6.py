# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Tests for Section 86/6 (abbreviated tax invoice) and Section 86/9-10
(debit/credit note document type and reference to the original invoice)."""
from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

ABBREV_REPORT_REF = "od19_thai_tax_reports.action_od19_abbreviated_tax_invoice"
COMMERCIAL_INVOICE_REPORT_REF = "l10n_th.action_report_commercial_invoice"


@tagged("post_install", "-at_install")
class TestTaxInvoiceForms866(TransactionCase):
    """Section 86/6 allows an abbreviated tax invoice for retail sales, while
    Sections 86/9-10 require a debit/credit note to identify its type and to
    refer back to the original tax invoice together with the reason."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        # Section 86/4 validation is exercised by its own test module; disable
        # it here so these documents can be posted without the full particulars.
        cls.company.od19_enforce_86_4_validation = False
        cls.company.partner_id.write(
            {
                "street": "1 Moo 1 Vibhavadi Rangsit Road",
                "vat": "0105555555554",
                "company_registry": "00000",
            }
        )
        cls.th_country = cls.env.ref("base.th")
        cls.company.partner_id.country_id = cls.th_country

        cls.vat_partner = cls.env["res.partner"].create(
            {
                "name": "VAT Buyer Co., Ltd.",
                "company_type": "company",
                "street": "99 Moo 9 Rama IX Road",
                "vat": "0105555555562",
                "company_registry": "00001",
                "country_id": cls.th_country.id,
            }
        )
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
        cls.reason = cls.env["account.move.dncn.reason"].create(
            {"name": "Price adjustment"}
        )
        cls._seq = 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _create_invoice(self, partner, move_type="out_invoice", with_tax=True, **extra):
        self.__class__._seq += 1
        vals = {
            "move_type": move_type,
            "partner_id": partner.id,
            "invoice_date": fields.Date.from_string("2026-03-15"),
            "invoice_line_ids": [
                (
                    0,
                    0,
                    {
                        "name": "Service #%03d" % self.__class__._seq,
                        "quantity": 1.0,
                        "price_unit": 10000.0,
                        "account_id": self.income_account.id,
                        "tax_ids": [(6, 0, [self.sale_tax.id] if with_tax else [])],
                    },
                )
            ],
        }
        vals.update(extra)
        return self.env["account.move"].create(vals)

    def _render(self, report_ref, moves):
        html, _report_type = self.env["ir.actions.report"]._render_qweb_html(
            report_ref, moves.ids
        )
        return html.decode() if isinstance(html, bytes) else html

    # ------------------------------------------------------------------
    # Document type computation (ม.86)
    # ------------------------------------------------------------------
    def test_doc_type_full_for_vat_buyer(self):
        invoice = self._create_invoice(self.vat_partner)
        self.assertEqual(invoice.od19_tax_invoice_doc_type, "full")
        self.assertFalse(invoice._od19_get_tax_invoice_doc_type() == "abbreviated")

    def test_doc_type_abbreviated_for_consumer(self):
        invoice = self._create_invoice(self.consumer)
        self.assertEqual(invoice.od19_tax_invoice_doc_type, "abbreviated")

    def test_doc_type_debit_note(self):
        invoice = self._create_invoice(
            self.vat_partner, dncn="dn", reason_id=self.reason.id
        )
        self.assertEqual(invoice.od19_tax_invoice_doc_type, "debit_note")

    def test_doc_type_credit_note(self):
        invoice = self._create_invoice(
            self.vat_partner, move_type="out_refund", dncn="cn", reason_id=self.reason.id
        )
        self.assertEqual(invoice.od19_tax_invoice_doc_type, "credit_note")

    def test_doc_type_out_refund_is_credit_note(self):
        invoice = self._create_invoice(self.vat_partner, move_type="out_refund")
        self.assertEqual(invoice.od19_tax_invoice_doc_type, "credit_note")

    def test_doc_type_none_for_vendor_bill(self):
        invoice = self._create_invoice(self.vat_partner, move_type="in_invoice")
        self.assertFalse(invoice.od19_tax_invoice_doc_type)

    # ------------------------------------------------------------------
    # ม.86/6 - Abbreviated tax invoice
    # ------------------------------------------------------------------
    def test_abbreviated_report_contains_heading(self):
        invoice = self._create_invoice(self.consumer)
        html = self._render(ABBREV_REPORT_REF, invoice)
        self.assertIn("ใบกำกับภาษีอย่างย่อ", html)
        self.assertIn("86/6", html)

    def test_abbreviated_report_shows_seller_and_buyer(self):
        invoice = self._create_invoice(self.consumer)
        html = self._render(ABBREV_REPORT_REF, invoice)
        self.assertIn(self.company.partner_id.name, html)
        self.assertIn("Walk-in Customer", html)

    # ------------------------------------------------------------------
    # ม.86/9-10 - Debit / credit note reference block
    # ------------------------------------------------------------------
    def test_note_reference_block_on_tax_invoice(self):
        original = self._create_invoice(self.vat_partner)
        original.action_post()
        debit_note = self._create_invoice(
            self.vat_partner,
            dncn="dn",
            parent_id=original.id,
            reason_id=self.reason.id,
        )
        html = self._render(COMMERCIAL_INVOICE_REPORT_REF, debit_note)
        self.assertIn("อ้างอิงใบกำกับภาษีเดิม", html)
        self.assertIn(original.name, html)
        self.assertIn("ใบเพิ่มหนี้", html)

    def test_original_invoice_has_no_reference_block(self):
        invoice = self._create_invoice(self.vat_partner)
        html = self._render(COMMERCIAL_INVOICE_REPORT_REF, invoice)
        self.assertNotIn("อ้างอิงใบกำกับภาษีเดิม", html)
