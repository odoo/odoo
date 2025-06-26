from odoo.tests.common import tagged
from odoo.addons.l10n_hu_edi.tests.common import L10nHuEdiTestCommon
from freezegun import freeze_time


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestL10nHuEdiCreditDebitNotes(L10nHuEdiTestCommon):
    """Tests for Credit and Debit Notes in the Hungarian EDI localization."""

    @classmethod
    def setUpClass(cls, chart_template_ref='hu'):
        super().setUpClass(chart_template_ref=chart_template_ref)

    @freeze_time('2025-01-01')
    def test_credit_note_preserves_delivery_date(self):
        """Ensure that the credit note inherits the delivery date from the original invoice."""
        invoice = self.create_invoice_simple()
        invoice.action_post()

        credit_note = self.create_reversal(invoice)
        self.assertEqual(
            invoice.delivery_date,
            credit_note.delivery_date,
            "Credit note should inherit the delivery date from the original invoice."
        )

    @freeze_time('2025-01-01')
    def test_debit_note_preserves_delivery_date(self):
        """Ensure that the debit note inherits the delivery date from the original invoice."""
        invoice = self.create_invoice_simple()
        invoice.action_post()

        wizard = self.env['account.debit.note'].with_context(
            active_ids=invoice.ids,
            active_model='account.move'
        ).create({'reason': 'Test debit note'})
        wizard.create_debit()

        debit_note = invoice.debit_note_ids
        self.assertEqual(
            invoice.delivery_date,
            debit_note.delivery_date,
            "Debit note should inherit the delivery date from the original invoice."
        )
