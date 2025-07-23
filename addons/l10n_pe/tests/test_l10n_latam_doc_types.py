from odoo import Command
from odoo.tests.common import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('-at_install', 'post_install', 'post_install_l10n')
class TestL10nLatamDocTypes(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_pe.pe_chart_template'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.company_data['company'].write({
            'country_id': cls.env.ref('base.pe').id,
        })
        cls.company_data['company'].partner_id.write({
            'vat': '20557912879',
            'l10n_latam_identification_type_id': cls.env.ref('l10n_pe.it_RUC').id,
        })
        cls.company_data['default_journal_sale'].l10n_latam_use_documents = True
        cls.company_data['default_journal_purchase'].l10n_latam_use_documents = True

        cls.partner_dni = cls.env['res.partner'].create({
            'name': 'test partner PE',
            'l10n_latam_identification_type_id': cls.env.ref('l10n_pe.it_DNI').id,
            'vat': '20121888549',
        })

        cls.partner_ruc = cls.env['res.partner'].create({
            'name': 'test partner PE',
            'l10n_latam_identification_type_id': cls.env.ref('l10n_pe.it_RUC').id,
            'vat': '20462509236',
        })

        cls.product_pe = cls.env['product.product'].create({
            'name': 'product_pe',
            'lst_price': 1000.0,
            'default_code': 'VAT 22',
        })

    def test_sale_document_l10n_latam_document_type(self):
        """Test that the l10n latam document type is correctly set in the sale documents"""

        boleta = self.env['account.move'].create({
            'partner_id': self.partner_dni.id,
            'move_type': 'out_invoice',
            'journal_id': self.company_data['default_journal_sale'].id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_pe.id,
                'quantity': 1.0,
                'price_unit': 100.0,
            })]
        })
        boleta.action_post()

        invoice = self.env['account.move'].create({
            'partner_id': self.partner_ruc.id,
            'move_type': 'out_invoice',
            'journal_id': self.company_data['default_journal_sale'].id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_pe.id,
                'quantity': 1.0,
                'price_unit': 100.0,
            })]
        })
        invoice.action_post()

        self.assertEqual(boleta.l10n_latam_document_type_id.id, self.env.ref('l10n_pe.document_type02').id, 'Not Boleta')
        self.assertEqual(invoice.l10n_latam_document_type_id.id, self.env.ref('l10n_pe.document_type01').id, 'Not Invoice')

        # Test that the credit note wizard apply the correct document type
        refund_wizard_boleta = self.env['account.move.reversal']\
            .with_context({'active_ids': boleta.ids, 'active_model': 'account.move'})\
            .create({
                'reason': 'Mercadería defectuosa',
                'journal_id': boleta.journal_id.id,
            })
        refund_boleta = self.env['account.move'].browse(refund_wizard_boleta.reverse_moves()['res_id'])

        refund_wizard_invoice = self.env['account.move.reversal']\
            .with_context({'active_ids': invoice.ids, 'active_model': 'account.move'})\
            .create({
                'reason': 'Mercadería defectuosa',
                'journal_id': invoice.journal_id.id,
            })
        refund_invoice = self.env['account.move'].browse(refund_wizard_invoice.reverse_moves()['res_id'])

        self.assertEqual(refund_boleta.l10n_latam_document_type_id.id, self.env.ref('l10n_pe.document_type07b').id, 'Not Nota de Crédito Boleta')
        expected_ids_boleta = [self.env.ref('l10n_pe.document_type07b').id]
        self.assertEqual(refund_boleta.l10n_latam_available_document_type_ids.mapped('id'), expected_ids_boleta, 'Bad Domain For Boleta Credit Note')

        self.assertEqual(refund_invoice.l10n_latam_document_type_id.id, self.env.ref('l10n_pe.document_type07').id, 'Not Nota de Crédito')
        expected_ids_invoice = [self.env.ref('l10n_pe.document_type07').id]
        self.assertEqual(refund_invoice.l10n_latam_available_document_type_ids.mapped('id'), expected_ids_invoice, 'Bad Domain For Invoice Credit Note')

        # Test that the debit note wizard apply the correct document type
        debit_note_wizard_boleta = self.env['account.debit.note']\
            .with_context({'active_ids': boleta.ids, 'active_model': 'account.move'})\
            .create({
                'reason': 'Mercadería defectuosa',
                'journal_id': boleta.journal_id.id,
            })
        debit_note_boleta = self.env['account.move'].browse(debit_note_wizard_boleta.create_debit()['res_id'])

        debit_note_wizard_invoice = self.env['account.debit.note']\
            .with_context({'active_ids': invoice.ids, 'active_model': 'account.move'})\
            .create({
                'reason': 'Mercadería defectuosa',
                'journal_id': invoice.journal_id.id,
            })
        debit_note_invoice = self.env['account.move'].browse(debit_note_wizard_invoice.create_debit()['res_id'])

        self.assertEqual(debit_note_boleta.l10n_latam_document_type_id.id, self.env.ref('l10n_pe.document_type08b').id, 'Not Nota de Débito Boleta')
        expected_ids_boleta = [self.env.ref('l10n_pe.document_type08b').id]
        self.assertEqual(debit_note_boleta.l10n_latam_available_document_type_ids.mapped('id'), expected_ids_boleta, 'Bad Domain For Boleta Debit Note')

        self.assertEqual(debit_note_invoice.l10n_latam_document_type_id.id, self.env.ref('l10n_pe.document_type08').id, 'Not Nota de Débito Boleta')
        expected_ids_invoice = [self.env.ref('l10n_pe.document_type08').id]
        self.assertEqual(debit_note_invoice.l10n_latam_available_document_type_ids.mapped('id'), expected_ids_invoice, 'Bad Domain For Invoice Debit Note')

    def test_purchase_document_l10n_latam_document_type(self):
        """Test that the l10n latam document type is correctly set in the purchase documents"""

        boleta = self.env['account.move'].create({
            'partner_id': self.partner_ruc.id,
            'move_type': 'in_invoice',
            'invoice_date': '2025-01-01',
            'journal_id': self.company_data['default_journal_purchase'].id,
            'l10n_latam_document_type_id': self.env.ref('l10n_pe.document_type02').id,
            'l10n_latam_document_number': 'BBB-000032',
            'invoice_line_ids': [Command.create({
                'product_id': self.product_pe.id,
                'quantity': 1.0,
                'price_unit': 100.0,
            })]
        })
        boleta.action_post()

        invoice = self.env['account.move'].create({
            'partner_id': self.partner_ruc.id,
            'move_type': 'in_invoice',
            'invoice_date': '2025-01-02',
            'journal_id': self.company_data['default_journal_purchase'].id,
            'l10n_latam_document_type_id': self.env.ref('l10n_pe.document_type01').id,
            'l10n_latam_document_number': 'FFF-000032',
            'invoice_line_ids': [Command.create({
                'product_id': self.product_pe.id,
                'quantity': 1.0,
                'price_unit': 100.0,
            })]
        })
        invoice.action_post()

        # Test that the credit note wizard apply the correct document type
        refund_wizard_boleta = self.env['account.move.reversal']\
            .with_context({'active_ids': boleta.ids, 'active_model': 'account.move'})\
            .create({
                'reason': 'Mercadería defectuosa',
                'journal_id': boleta.journal_id.id,
            })
        refund_boleta = self.env['account.move'].browse(refund_wizard_boleta.reverse_moves()['res_id'])

        refund_wizard_invoice = self.env['account.move.reversal']\
            .with_context({'active_ids': invoice.ids, 'active_model': 'account.move'})\
            .create({
                'reason': 'Mercadería defectuosa',
                'journal_id': invoice.journal_id.id,
            })
        refund_invoice = self.env['account.move'].browse(refund_wizard_invoice.reverse_moves()['res_id'])

        self.assertEqual(refund_boleta.l10n_latam_document_type_id.id, self.env.ref('l10n_pe.document_type07b').id, 'Not Nota de Crédito Boleta')
        expected_ids_boleta = [self.env.ref('l10n_pe.document_type07b').id]
        self.assertEqual(refund_boleta.l10n_latam_available_document_type_ids.mapped('id'), expected_ids_boleta, 'Bad Domain For Boleta Credit Note')

        self.assertEqual(refund_invoice.l10n_latam_document_type_id.id, self.env.ref('l10n_pe.document_type07').id, 'Not Nota de Crédito')
        expected_ids_invoice = [self.env.ref('l10n_pe.document_type07').id]
        self.assertEqual(refund_invoice.l10n_latam_available_document_type_ids.mapped('id'), expected_ids_invoice, 'Bad Domain For Invoice Credit Note')

        # Test that the debit note wizard apply the correct document type
        debit_note_wizard_boleta = self.env['account.debit.note']\
            .with_context({'active_ids': boleta.ids, 'active_model': 'account.move'})\
            .create({
                'reason': 'Mercadería defectuosa',
                'journal_id': boleta.journal_id.id,
            })
        debit_note_boleta = self.env['account.move'].browse(debit_note_wizard_boleta.create_debit()['res_id'])

        debit_note_wizard_invoice = self.env['account.debit.note']\
            .with_context({'active_ids': invoice.ids, 'active_model': 'account.move'})\
            .create({
                'reason': 'Mercadería defectuosa',
                'journal_id': invoice.journal_id.id,
            })
        debit_note_invoice = self.env['account.move'].browse(debit_note_wizard_invoice.create_debit()['res_id'])

        self.assertEqual(debit_note_boleta.l10n_latam_document_type_id.id, self.env.ref('l10n_pe.document_type08b').id, 'Not Nota de Débito Boleta')
        expected_ids_boleta = [self.env.ref('l10n_pe.document_type08b').id]
        self.assertEqual(debit_note_boleta.l10n_latam_available_document_type_ids.mapped('id'), expected_ids_boleta, 'Bad Domain For Boleta Debit Note')

        self.assertEqual(debit_note_invoice.l10n_latam_document_type_id.id, self.env.ref('l10n_pe.document_type08').id, 'Not Nota de Débito Boleta')
        expected_ids_invoice = [self.env.ref('l10n_pe.document_type08').id]
        self.assertEqual(debit_note_invoice.l10n_latam_available_document_type_ids.mapped('id'), expected_ids_invoice, 'Bad Domain For Invoice Debit Note')
