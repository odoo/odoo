# -*- coding: utf-8 -*-
"""Tests for the payment certificate in lieu of receipt
(ใบรับรองแทนใบเสร็จรับเงิน) on hr.expense.

Covered: the document type selection, the input VAT creditable flag,
the VAT prohibition on a payment certificate, and the printable form.
"""

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged

REPORT_XMLID = "od19_hr_expense_enhanced.action_report_payment_certificate"
REPORT_NAME = "od19_hr_expense_enhanced.payment_certificate_document"


@tagged("post_install", "-at_install")
class TestPaymentCertificate(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Cert Employee"})
        cls.employee = cls.env["hr.employee"].create({
            "name": "Cert Employee",
            "work_contact_id": cls.partner.id,
        })
        cls.product = cls.env["product.product"].create({
            "name": "Cert Expense Product",
            "type": "service",
        })
        cls.purchase_tax = cls.env["account.tax"].create({
            "name": "Cert Input VAT 7%",
            "amount_type": "percent",
            "amount": 7.0,
            "type_tax_use": "purchase",
        })

    def _create_expense(self, document_type="tax_invoice", taxes=None):
        vals = {
            "name": "Payment certificate expense",
            "product_id": self.product.id,
            "total_amount": 1070.0,
            "employee_id": self.employee.id,
            "payment_mode": "own_account",
            "od19_document_type": document_type,
        }
        if taxes:
            vals["tax_ids"] = [(6, 0, [tax.id for tax in taxes])]
        return self.env["hr.expense"].create(vals)

    # ------------------------------------------------------------------
    # Document type / VAT creditable flag
    # ------------------------------------------------------------------
    def test_tax_invoice_is_creditable_by_default(self):
        expense = self._create_expense()
        self.assertEqual(expense.od19_document_type, "tax_invoice")
        self.assertTrue(expense.od19_vat_creditable)

    def test_payment_certificate_is_not_creditable(self):
        expense = self._create_expense("payment_certificate")
        self.assertFalse(expense.od19_vat_creditable)

    def test_receipt_is_creditable(self):
        expense = self._create_expense("receipt")
        self.assertTrue(expense.od19_vat_creditable)

    # ------------------------------------------------------------------
    # No input VAT on a payment certificate
    # ------------------------------------------------------------------
    def test_payment_certificate_rejects_vat(self):
        with self.assertRaises(ValidationError):
            self._create_expense("payment_certificate", taxes=[self.purchase_tax])

    def test_onchange_clears_taxes_for_payment_certificate(self):
        expense = self._create_expense(taxes=[self.purchase_tax])
        self.assertTrue(expense.tax_ids)
        expense.od19_document_type = "payment_certificate"
        expense._onchange_od19_document_type()
        self.assertFalse(expense.tax_ids)

    def test_payment_certificate_still_books_as_expense(self):
        """The whole amount stays on the expense (no VAT line is created)."""
        expense = self._create_expense("payment_certificate")
        self.assertFalse(expense.tax_ids)
        self.assertEqual(expense.total_amount, 1070.0)

    # ------------------------------------------------------------------
    # Printing
    # ------------------------------------------------------------------
    def test_report_is_bound(self):
        report = self.env.ref(REPORT_XMLID)
        self.assertEqual(report.model, "hr.expense")
        self.assertEqual(report.report_type, "qweb-pdf")
        self.assertEqual(report.report_name, REPORT_NAME)

    def test_report_renders(self):
        expense = self._create_expense("payment_certificate")
        expense.od19_certificate_number = "PC-0001"

        report = self.env.ref(REPORT_XMLID)
        html, _report_type = (
            self.env["ir.actions.report"]
            .with_context(discard_logo_check=True)
            ._render_qweb_html(report, expense.ids)
        )
        rendered = html.decode()
        self.assertIn("ใบรับรองแทนใบเสร็จรับเงิน", rendered)
        self.assertIn("PC-0001", rendered)
        self.assertIn("1,070.00", rendered)
