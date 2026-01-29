from odoo import Command
from odoo.tests import tagged
from odoo.addons.l10n_it_edi.tests.common import TestItEdi
from odoo.addons.l10n_it_edi.tests.test_edi_reverse_charge import TestItEdiReverseCharge


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
        credit_note_y = invoice_y.reversal_move_id
        self.assertEqual(credit_note_y.l10n_it_document_type, dt_credit_note)


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestItReverseChargeDocumentType(TestItEdiReverseCharge):

    def test_credit_note_export_document_type(self):
        """Test that manually setting document type will be kept into account when exporting xml"""
        self.module = 'l10n_it_edi_ndd'
        # Partner -----------
        self.non_eu_partner = self.env['res.partner'].create({
            'name': 'Alessi',
            'vat': 'FR15437982937',
            'country_id': self.env.ref('base.cn').id,
            'street': 'Street test',
            'zip': '518000',
            'city': 'baoanqu',
            'is_company': True
        })

        dt_18 = self.env.ref('l10n_it_edi_ndd.l10n_it_document_type_18')

        bill = self.env['account.move'].with_company(self.company).create({
            'move_type': 'in_invoice',
            'invoice_date': '2022-03-24',
            'invoice_date_due': '2022-03-24',
            'date': '2022-04-01',
            'partner_id': self.non_eu_partner.id,
            'l10n_it_document_type': dt_18.id,
            'invoice_line_ids': [
                Command.create({
                    'name': "Product A",
                    'product_id': self.product_a.id,
                    'price_unit': 800.40,
                    'tax_ids': [Command.set(self.purchase_tax_22p.ids)],
                }),
            ],
        })
        bill.action_post()

        reversal_wizard = self.env['account.move.reversal'].with_context(active_model='account.move', active_ids=bill.ids).create({
            'reason': 'test',
            'journal_id': bill.journal_id.id,
            'date': '2022-04-01',
        })
        reversal = reversal_wizard.refund_moves()
        credit_note = self.env['account.move'].browse(reversal['res_id'])
        credit_note.write({'l10n_it_document_type': dt_18.id})
        credit_note.action_post()

        self._assert_export_invoice(credit_note, 'credit_note_export_document_type.xml')
