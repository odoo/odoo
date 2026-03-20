from odoo.tests import tagged
from odoo.addons.l10n_it_edi.tests.common import TestItEdi


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestItDocumentType(TestItEdi):

    def test_l10n_it_edi_debit_note_document_type(self):
        original_move = self.init_invoice('out_invoice', amounts=[1000], post=True)

        self.assertEqual(original_move.l10n_it_document_type.code, 'TD01')

        move_debit_note_wiz = self.env['account.debit.note'].with_context(
            active_model='account.move',
            active_ids=original_move.ids,
        ).create({
            'copy_lines': True,
        })
        move_debit_note_wiz.create_debit()

        debit_note = self.env['account.move'].search([('debit_origin_id', '=', original_move.id)])
        debit_note.ensure_one()

        # when debit note is created, it has no document type
        self.assertFalse(debit_note.l10n_it_document_type)

        debit_note.action_post()

        # when debit note is posted, the IT document type changes to correct type of debit note
        self.assertEqual(debit_note.l10n_it_document_type.code, 'TD05')
