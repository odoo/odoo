from odoo.tests import tagged
from odoo.tools import html2plaintext
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nTHCreditDebitNotePDFReport(AccountTestInvoicingCommon):
    """Test the amounts displayed in Thailand credit note and debit note PDF reports."""

    @classmethod
    @AccountTestInvoicingCommon.setup_country('th')
    def setUpClass(cls):
        super().setUpClass()

        cls.invoice = cls._create_invoice(
            move_type='out_invoice',
            invoice_date='2026-08-01',
            post=True,
            invoice_line_ids=[cls._prepare_invoice_line(1000)],
        )
        cls.IrActionsReport = cls.env['ir.actions.report']

    def _assert_report_contains(self, move, *expected_values):
        """Assert that the rendered report contains all expected values."""

        html = self.IrActionsReport._render_qweb_html('account.report_invoice_with_payments', move.ids)[0]
        text = html2plaintext(html)

        for value in expected_values:
            self.assertIn(value, text, f"Expected '{value}' to be present in the generated PDF report.")

    def test_th_credit_note_pdf_report_amounts(self):
        """Ensure credit note reports display the correct original and corrected amounts."""

        credit_note_1 = self._create_invoice(
            move_type='out_refund',
            invoice_date='2026-08-04',
            post=True,
            reversed_entry_id=self.invoice.id,
            invoice_line_ids=[self._prepare_invoice_line(100)],
        )

        self.assertEqual(
            tuple(a['amount'] for a in credit_note_1._l10n_th_get_credit_debit_note_amounts()),
            (1000.0, 900.0),
            "Unexpected amounts for the first credit note.",
        )

        credit_note_2 = self._create_invoice(
            move_type='out_refund',
            invoice_date='2026-08-04',
            post=True,
            reversed_entry_id=self.invoice.id,
            invoice_line_ids=[self._prepare_invoice_line(200)],
        )

        self.assertEqual(
            tuple(a['amount'] for a in credit_note_2._l10n_th_get_credit_debit_note_amounts()),
            (900.0, 700.0),
            "Unexpected amounts for the second credit note.",
        )

        self._assert_report_contains(
            credit_note_1,
            "Original Amount",
            "Correct Amount",
            "1,000.00",
            "900.00",
        )

    def test_th_debit_note_pdf_report_amounts(self):
        """Ensure debit note reports display the correct original and corrected amounts."""

        if not self.env['ir.module.module'].search([
            ('name', '=', 'account_debit_note'),
            ('state', '=', 'installed'),
        ]):
            self.skipTest("This test requires the account_debit_note module.")

        debit_note_1 = self._create_invoice(
            move_type='out_invoice',
            invoice_date='2026-08-04',
            post=True,
            debit_origin_id=self.invoice.id,
            invoice_line_ids=[self._prepare_invoice_line(100)],
        )

        self.assertEqual(
            tuple(a['amount'] for a in debit_note_1._l10n_th_get_credit_debit_note_amounts()),
            (1000.0, 1100.0),
            "Unexpected amounts for the first debit note.",
        )

        debit_note_2 = self._create_invoice(
            move_type='out_invoice',
            invoice_date='2026-08-04',
            post=True,
            debit_origin_id=self.invoice.id,
            invoice_line_ids=[self._prepare_invoice_line(200)],
        )

        self.assertEqual(
            tuple(a['amount'] for a in debit_note_2._l10n_th_get_credit_debit_note_amounts()),
            (1100.0, 1300.0),
            "Unexpected amounts for the second debit note.",
        )

        self._assert_report_contains(
            debit_note_1,
            "Original Amount",
            "Correct Amount",
            "1,000.00",
            "1,100.00",
        )

    def test_th_mixed_credit_debit_note_pdf_report_amounts(self):
        """Ensure reports display the correct amounts when an invoice has both credit and debit notes."""

        if not self.env['ir.module.module'].search([
            ('name', '=', 'account_debit_note'),
            ('state', '=', 'installed'),
        ]):
            self.skipTest("This test requires the account_debit_note module.")

        credit_note = self._create_invoice(
            move_type='out_refund',
            invoice_date='2026-08-04',
            post=True,
            reversed_entry_id=self.invoice.id,
            invoice_line_ids=[self._prepare_invoice_line(100)],
        )

        debit_note = self._create_invoice(
            move_type='out_invoice',
            invoice_date='2026-08-04',
            post=True,
            debit_origin_id=self.invoice.id,
            invoice_line_ids=[self._prepare_invoice_line(100)],
        )

        self.assertEqual(
            tuple(a['amount'] for a in credit_note._l10n_th_get_credit_debit_note_amounts()),
            (1000.0, 900.0),
            "Unexpected original or corrected amounts for the credit note when the invoice has both credit and debit notes.",
        )

        self.assertEqual(
            tuple(a['amount'] for a in debit_note._l10n_th_get_credit_debit_note_amounts()),
            (1000.0, 1100.0),
            "Unexpected original or corrected amounts for the debit note when the invoice has both credit and debit notes.",
        )

        self._assert_report_contains(
            credit_note,
            "Original Amount",
            "Correct Amount",
            "1,000.00",
            "900.00",
        )

        self._assert_report_contains(
            debit_note,
            "Original Amount",
            "Correct Amount",
            "1,000.00",
            "1,100.00",
        )

    def test_th_draft_credit_note_pdf_report_amounts(self):
        """Ensure a draft credit note reports display the correct original and corrected amounts."""

        credit_note_1 = self._create_invoice(
            move_type='out_refund',
            invoice_line_ids=[self._prepare_invoice_line(100)],
            invoice_date='2026-08-04',
            reversed_entry_id=self.invoice.id,
            post=True,
        )

        self.assertEqual(
            tuple(a['amount'] for a in credit_note_1._l10n_th_get_credit_debit_note_amounts()),
            (1000.0, 900.0),
            "Unexpected amounts for the first credit note.",
        )

        credit_note_2 = self._create_invoice(
            move_type='out_refund',
            invoice_line_ids=[self._prepare_invoice_line(200)],
            invoice_date='2026-08-04',
            name='/',
            reversed_entry_id=self.invoice.id,
        )

        self.assertEqual(
            tuple(a['amount'] for a in credit_note_2._l10n_th_get_credit_debit_note_amounts()),
            (900.0, 700.0),
            "Unexpected amounts for the second credit note.",
        )

        self._assert_report_contains(
            credit_note_1,
            "Original Amount",
            "Correct Amount",
            "1,000.00",
            "900.00",
        )
