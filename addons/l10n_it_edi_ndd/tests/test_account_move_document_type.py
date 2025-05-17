from odoo.tests import tagged
from odoo.addons.l10n_it_edi.tests.common import TestItEdi


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestItAccountMoveDocumentType(TestItEdi):

    def test_account_move_document_type(self):
        # l10n_it_document_type_01: "TD01 - Invoice (Immediate or Accompanying if <DatiTrasporto> or <DatiDDT> are completed)"
        # l10n_it_document_type_04: "TD04 - Credit note"
        dt_invoice = self.env.ref('l10n_it_edi_ndd.l10n_it_document_type_01')
        dt_credit_note = self.env.ref('l10n_it_edi_ndd.l10n_it_document_type_04')

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
