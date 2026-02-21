from odoo import Command
from odoo.tests import tagged
from odoo.addons.l10n_it_edi.tests.common import TestItEdi


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestItDocumentType(TestItEdi):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.module = 'l10n_it_edi_ndd_account_dn'

    def test_l10n_it_edi_debit_note_document_type(self):
        original_move = self.init_invoice('out_invoice', amounts=[1000], post=True)

        self.assertEqual(original_move.l10n_it_document_type.code, 'TD01')

        move_debit_note_wiz = self.env['account.debit.note'].with_context(
            active_model='account.move',
            active_ids=original_move.ids
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

    def test_l10n_it_edi_export_debit_note(self):
        """ Test that a Debit Note generates the 'DatiFattureCollegate' tag correctly
        """
        original_invoice = self.env['account.move'].with_company(self.company).create({
            'name': 'INV/2022/00001',
            'move_type': 'out_invoice',
            'invoice_date': '2022-03-24',
            'invoice_date_due': '2022-03-24',
            'partner_id': self.italian_partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'Original Service',
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(self.default_tax.ids)],
                }),
            ],
        })
        original_invoice.action_post()

        debit_note = self.env['account.move'].with_company(self.company).create({
            'name': 'DN/2022/00001',
            'move_type': 'out_invoice',
            'invoice_date': '2022-03-25',
            'invoice_date_due': '2022-03-25',
            'partner_id': self.italian_partner_a.id,
            'debit_origin_id': original_invoice.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'Debit Note Adjustment',
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(self.default_tax.ids)],
                }),
            ],
        })
        debit_note.action_post()

        self._assert_export_invoice(debit_note, 'it_edi_debit_note.xml')
