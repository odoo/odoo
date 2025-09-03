from odoo import fields
from odoo.tests import tagged
from odoo.addons.l10n_it_edi.tests.common import TestItEdi


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestItAccountMoveDocumentType(TestItEdi):

    def test_account_move_document_type(self):
        # l10n_it_document_type_01: "TD01 - Invoice (Immediate or Accompanying if <DatiTrasporto> or <DatiDDT> are completed)"
        # l10n_it_document_type_04: "TD04 - Credit note"
        dt_invoice = self.env.ref('l10n_it_edi.l10n_it_document_type_01')
        dt_credit_note = self.env.ref('l10n_it_edi.l10n_it_document_type_04')

        invoice_x = self.init_invoice("out_invoice", amounts=[1000])
        # the compute method does nothing for moves that are not posted
        self.assertFalse(invoice_x.l10n_it_document_type)

        invoice_x.action_post()
        self.assertEqual(invoice_x.l10n_it_document_type, dt_invoice)
        # create a draft credit note
        reversal_wizard = self.env['account.move.reversal'].with_context(active_model='account.move', active_ids=invoice_x.ids).create({
            'reason': 'XXX',
            'journal_id': invoice_x.journal_id.id,
        })
        reversal = reversal_wizard.refund_moves()
        credit_note_x = self.env['account.move'].browse(reversal['res_id'])
        self.assertFalse(credit_note_x.l10n_it_document_type)
        # post the credit note
        credit_note_x.action_post()
        self.assertEqual(credit_note_x.l10n_it_document_type, dt_credit_note)

        invoice_y = self.init_invoice("out_invoice", amounts=[2000], post=True)
        self.assertEqual(invoice_y.l10n_it_document_type, dt_invoice)
        # create a credit note that is posted directly
        reversal_wizard = self.env['account.move.reversal'].with_context(active_model='account.move', active_ids=invoice_y.ids).create({
            'reason': 'YYY',
            'journal_id': invoice_y.journal_id.id,
        })
        reversal_wizard.modify_moves()
        credit_note_y = invoice_y.reversal_move_ids[0]
        self.assertEqual(credit_note_y.l10n_it_document_type, dt_credit_note)

    def test_td01_assigned_on_posted_in_invoice(self):
        """Test that TD01 is correctly assigned to an in_invoice after posting."""
        dt_invoice = self.env.ref('l10n_it_edi.l10n_it_document_type_01')

        invoice_x = self.init_invoice("in_invoice", amounts=[1000])
        self.assertFalse(invoice_x.l10n_it_document_type)

        invoice_x.action_post()
        self.assertEqual(invoice_x.l10n_it_document_type, dt_invoice)

    def test_td01_assigned_on_imported_in_invoice(self):
        td01 = self.env.ref('l10n_it_edi.l10n_it_document_type_01')
        self._assert_import_invoice('IT01234567890_FPR01.xml', [{
            'move_type': 'in_invoice',
            'invoice_date': fields.Date.from_string('2014-12-18'),
            'amount_untaxed': 5.0,
            'amount_tax': 1.1,
            'invoice_line_ids': [{
                'quantity': 5.0,
                'price_unit': 1.0,
                'debit': 5.0,
            }],
            'l10n_it_payment_method': 'MP01',
            'l10n_it_document_type': td01.id,
        }])
