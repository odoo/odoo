from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestDebitDocumentTitle(AccountTestInvoicingCommon):

    def test_document_title_for_debit_note(self):
        """Test the document title for Debit note."""

        moves = (
            self._create_invoice(move_type='out_invoice', post=True)
            | self._create_invoice(move_type='out_refund', post=True)
            | self._create_invoice(move_type='in_invoice', post=True)
            | self._create_invoice(move_type='in_refund', post=True)
        )

        debit_notes = self.env['account.move']
        for move in moves:
            debit_note = self._create_debit_note(move)
            debit_note.invoice_line_ids = [self._prepare_invoice_line(price_unit=10)]
            debit_notes |= debit_note

        # Draft debit notes
        self._assert_document_titles(
            debit_notes,
            [
                'Draft Debit Note',
                'Draft Debit Note',
                'Vendor Bill',
                'Vendor Bill',
            ],
        )

        # Posted debit notes
        debit_notes.action_post()
        self._assert_document_titles(
            debit_notes,
            [
                'Debit Note',
                'Debit Note',
                'Vendor Bill',
                'Vendor Bill',
            ],
        )

        # Cencelled debit notes
        debit_notes.button_cancel()
        self._assert_document_titles(
            debit_notes,
            [
                'Cancelled Debit Note',
                'Cancelled Debit Note',
                'Vendor Bill',
                'Vendor Bill',
            ],
        )
