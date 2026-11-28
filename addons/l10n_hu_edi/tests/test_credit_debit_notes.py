from odoo.tests.common import tagged
from odoo.addons.l10n_hu_edi.tests.common import L10nHuEdiTestCommon
from freezegun import freeze_time


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestL10nHuEdiCreditDebitNotes(L10nHuEdiTestCommon):
    """Tests for Credit and Debit Notes in the Hungarian EDI localization."""
    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    @freeze_time('2025-01-01')
    def test_credit_note_preserves_taxable_supply_date(self):
        """Ensure that the credit note inherits the taxable supply date from the original invoice."""
        invoice = self.create_invoice_simple()
        invoice.taxable_supply_date = self.yesterday
        invoice.action_post()

        credit_note = self.create_reversal(invoice)
        self.assertEqual(
            invoice.taxable_supply_date,
            credit_note.taxable_supply_date,
            "Credit note should inherit the taxable supply date from the original invoice."
        )
        # The credit note is accounted at its own date, not at the taxable supply date
        self.assertEqual(credit_note.date, credit_note.invoice_date)
        self.assertNotEqual(credit_note.date, credit_note.taxable_supply_date)

    @freeze_time('2025-01-01')
    def test_debit_note_preserves_taxable_supply_date(self):
        """Ensure that the debit note inherits the taxable supply date from the original invoice."""
        invoice = self.create_invoice_simple()
        invoice.taxable_supply_date = self.yesterday
        invoice.action_post()

        wizard = self.env['account.debit.note'].with_context(
            active_ids=invoice.ids,
            active_model='account.move'
        ).create({'reason': 'Test debit note'})
        wizard.create_debit()

        debit_note = invoice.debit_note_ids
        self.assertEqual(
            invoice.taxable_supply_date,
            debit_note.taxable_supply_date,
            "Debit note should inherit the taxable supply date from the original invoice."
        )
