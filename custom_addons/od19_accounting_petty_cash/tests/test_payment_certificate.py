# -*- coding: utf-8 -*-
"""Tests for the payment certificate in lieu of receipt
(ใบรับรองแทนใบเสร็จรับเงิน) on petty cash transactions.

Covered: the document type selection, the input VAT creditable flag and
the printable form.
"""

from odoo.tests.common import TransactionCase, tagged

REPORT_XMLID = "od19_accounting_petty_cash.action_report_payment_certificate"
REPORT_NAME = "od19_accounting_petty_cash.payment_certificate_document"


@tagged("post_install", "-at_install")
class TestPettyCashPaymentCertificate(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fund = cls.env["petty.cash.fund"].create({
            "name": "Certificate Petty Cash",
            "account_id": cls.env["account.account"].create({
                "name": "Petty Cash Cert",
                "code": "111003",
                "account_type": "asset_cash",
            }).id,
            "amount": 10000.0,
        })
        cls.expense_account = cls.env["account.account"].create({
            "name": "Cert Expense",
            "code": "511003",
            "account_type": "expense",
        })

    def _create_transaction(self, document_type="tax_invoice"):
        return self.env["petty.cash.transaction"].create({
            "fund_id": self.fund.id,
            "name": "Office supplies",
            "amount": 500.0,
            "transaction_type": "expense",
            "expense_account_id": self.expense_account.id,
            "date": "2024-01-15",
            "od19_document_type": document_type,
        })

    # ------------------------------------------------------------------
    # Document type / VAT creditable flag
    # ------------------------------------------------------------------
    def test_default_document_type_is_creditable(self):
        transaction = self._create_transaction()
        self.assertEqual(transaction.od19_document_type, "tax_invoice")
        self.assertTrue(transaction.od19_vat_creditable)

    def test_payment_certificate_is_not_creditable(self):
        transaction = self._create_transaction("payment_certificate")
        self.assertFalse(transaction.od19_vat_creditable)

    def test_payment_certificate_still_books_as_expense(self):
        transaction = self._create_transaction("payment_certificate")
        journal = self.env["account.journal"].create({
            "name": "Cert Journal",
            "type": "general",
            "code": "PCC",
        })
        transaction.journal_id = journal.id
        transaction.action_post()
        self.assertEqual(transaction.state, "posted")
        # No VAT line: the whole amount is debited to the expense account.
        debit = transaction.move_id.line_ids.filtered(
            lambda line: line.account_id == self.expense_account
        )
        self.assertAlmostEqual(sum(debit.mapped("debit")), 500.0)

    # ------------------------------------------------------------------
    # Printing
    # ------------------------------------------------------------------
    def test_report_is_bound(self):
        report = self.env.ref(REPORT_XMLID)
        self.assertEqual(report.model, "petty.cash.transaction")
        self.assertEqual(report.report_type, "qweb-pdf")
        self.assertEqual(report.report_name, REPORT_NAME)

    def test_report_renders(self):
        transaction = self._create_transaction("payment_certificate")
        transaction.od19_certificate_number = "PC-0002"
        transaction.od19_payee_name = "Somchai Jaidee"

        report = self.env.ref(REPORT_XMLID)
        html, _report_type = (
            self.env["ir.actions.report"]
            .with_context(discard_logo_check=True)
            ._render_qweb_html(report, transaction.ids)
        )
        rendered = html.decode()
        self.assertIn("ใบรับรองแทนใบเสร็จรับเงิน", rendered)
        self.assertIn("PC-0002", rendered)
        self.assertIn("Somchai Jaidee", rendered)
        self.assertIn("500.00", rendered)
