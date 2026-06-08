from odoo import Command
from odoo.tests.common import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('-at_install', 'post_install', 'post_install_l10n')
class TestL10nPeLatamDocTypes(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('pe')
    def setUpClass(cls):
        super().setUpClass()

        cls.company_data['company'].partner_id.write({
            'vat': '20557912879',
            'l10n_latam_identification_type_id': cls.env.ref('l10n_pe.it_RUC').id,
        })
        cls.company_data['default_journal_sale'].l10n_latam_use_documents = True
        cls.company_data['default_journal_purchase'].l10n_latam_use_documents = True

        cls.partner_pe_dni, cls.partner_pe_ruc = cls.env['res.partner'].create([
            {
                'name': 'test partner PE DNI',
                'l10n_latam_identification_type_id': cls.env.ref('l10n_pe.it_DNI').id,
                'vat': '20121888549',
            },
            {
                'name': 'test partner PE RUC',
                'l10n_latam_identification_type_id': cls.env.ref('l10n_pe.it_RUC').id,
                'vat': '20462509236',
            },
        ])

        cls.product_pe = cls.env['product.product'].create([{
            'name': 'test product PE',
            'lst_price': 1000.0,
            'default_code': 'VAT 22',
        }])

        cls.document_type01 = cls.env.ref('l10n_pe.document_type01').id
        cls.document_type02 = cls.env.ref('l10n_pe.document_type02').id
        cls.document_type07 = cls.env.ref('l10n_pe.document_type07').id
        cls.document_type07b = cls.env.ref('l10n_pe.document_type07b').id
        cls.document_type08 = cls.env.ref('l10n_pe.document_type08').id
        cls.document_type08b = cls.env.ref('l10n_pe.document_type08b').id

    def test_l10n_pe_document_type(self):
        """Test that the l10n latam document type is correctly set"""

        boleta = self.env['account.move'].create([{
            'partner_id': self.partner_pe_dni.id,
            'move_type': 'out_invoice',
            'journal_id': self.company_data['default_journal_sale'].id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_pe.id,
                'quantity': 1.0,
                'price_unit': 100.0,
            })]
        }])
        boleta.action_post()

        invoice = self.env['account.move'].create([{
            'partner_id': self.partner_pe_ruc.id,
            'move_type': 'out_invoice',
            'journal_id': self.company_data['default_journal_sale'].id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_pe.id,
                'quantity': 1.0,
                'price_unit': 100.0,
            })]
        }])
        invoice.action_post()

        self.assertEqual(boleta.l10n_latam_document_type_id.id, self.document_type02, 'Not Boleta')
        self.assertEqual(invoice.l10n_latam_document_type_id.id, self.document_type01, 'Not Invoice')

        # Test that the credit note wizard apply the correct document type
        refund_wizard_boleta = self.env['account.move.reversal']\
            .with_context(active_ids=boleta.ids, active_model='account.move')\
            .create([{
                'reason': 'Mercadería defectuosa',
                'journal_id': boleta.journal_id.id,
            }])
        refund_boleta = self.env['account.move'].browse(refund_wizard_boleta.reverse_moves()['res_id'])
        self.assertRecordValues(refund_boleta, [{
            'l10n_latam_document_type_id': self.document_type07b,
            'l10n_latam_available_document_type_ids': [self.document_type07b],
        }])

        refund_wizard_invoice = self.env['account.move.reversal']\
            .with_context({'active_ids': invoice.ids, 'active_model': 'account.move'})\
            .create([{
                'reason': 'Mercadería defectuosa',
                'journal_id': invoice.journal_id.id,
            }])
        refund_invoice = self.env['account.move'].browse(refund_wizard_invoice.reverse_moves()['res_id'])
        self.assertRecordValues(refund_invoice, [{
            'l10n_latam_document_type_id': self.document_type07,
            'l10n_latam_available_document_type_ids': [self.document_type07],
        }])

        # Test that the debit note wizard apply the correct document type
        debit_note_wizard_boleta = self.env['account.debit.note']\
            .with_context({'active_ids': boleta.ids, 'active_model': 'account.move'})\
            .create([{
                'reason': 'Mercadería defectuosa',
                'journal_id': boleta.journal_id.id,
            }])
        debit_note_boleta = self.env['account.move'].browse(debit_note_wizard_boleta.create_debit()['res_id'])
        self.assertRecordValues(debit_note_boleta, [{
            'l10n_latam_document_type_id': self.document_type08b,
            'l10n_latam_available_document_type_ids': [self.document_type08b],
        }])

        debit_note_wizard_invoice = self.env['account.debit.note']\
            .with_context({'active_ids': invoice.ids, 'active_model': 'account.move'})\
            .create([{
                'reason': 'Mercadería defectuosa',
                'journal_id': invoice.journal_id.id,
            }])
        debit_note_invoice = self.env['account.move'].browse(debit_note_wizard_invoice.create_debit()['res_id'])
        self.assertRecordValues(debit_note_invoice, [{
            'l10n_latam_document_type_id': self.document_type08,
            'l10n_latam_available_document_type_ids': [self.document_type08],
        }])
