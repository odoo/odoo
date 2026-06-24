# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.addons.l10n_hu_edi.tests.common import L10nHuEdiTestCommon
from odoo.tests import tagged
from odoo.tools.misc import file_open


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestBillXmlUpload(L10nHuEdiTestCommon):

    def upload_xml(self, filename):
        file_path = f'l10n_hu_edi/tests/invoice_xmls/{filename}'
        with file_open(file_path, 'rb') as file:
            content = file.read()
        attachment = self.env['ir.attachment'].create({
            'raw': content,
            'name': filename,
        })
        return self.company_data['default_journal_purchase'].with_context(default_move_type='in_invoice')._create_document_from_attachment(attachment.id)

    def test_normal_invoice_upload(self):
        bill = self.upload_xml('normal_invoice.xml')
        self.assertRecordValues(bill, [{
            'move_type': 'in_invoice',
            'ref': '2023/CT23026441',
            'invoice_date': fields.Date.from_string('2023-08-17'),
            'delivery_date': fields.Date.from_string('2023-08-18'),
            'invoice_date_due': False,
            'currency_id': self.currency_huf.id,
            'invoice_currency_rate': 1.00,
            'l10n_hu_invoice_chain_index': -1,
            'l10n_hu_payment_mode': False,
            'amount_untaxed': 29666.91,
            'amount_tax': 8010.09,
            'amount_total': 37677.00,
        }])
        self.assertRecordValues(bill.invoice_line_ids, [
            {
                'name': 'Uruguay 22',
                'quantity': 48.00,
                'price_unit': 136.708333,
                'discount': 0.00,
                'tax_ids': self.tax_purchase_27.ids,
            },
            {
                'name': 'Irtysh 11',
                'quantity': 120.00,
                'price_unit': 182.541667,
                'discount': 0.00,
                'tax_ids': self.tax_purchase_27.ids,
            },
            {
                'name': 'Taieri 12',
                'quantity': 1.00,
                'price_unit': 1200.00,
                'discount': 0.00,
                'tax_ids': self.tax_purchase_27.ids,
            },
            {
                'name': 'Cocytus 12',
                'quantity': 1.00,
                'price_unit': -0.09,
                'discount': 0.00,
                'tax_ids': [],
            },
        ])
        self.assertRecordValues(bill.partner_id, [{
            'name': 'Hadik András 2',
            'vat': '99909032',
            'l10n_hu_group_vat': '99999394-2-44',
        }])

    def test_simplified_invoice_upload(self):
        bill = self.upload_xml('simplified_invoice.xml')
        self.assertRecordValues(bill, [{
            'move_type': 'in_invoice',
            'ref': 'A06600324/1285/00009',
            'invoice_date': fields.Date.from_string('2023-01-27'),
            'delivery_date': fields.Date.from_string('2023-01-27'),
            'invoice_date_due': False,
            'currency_id': self.currency_huf.id,
            'invoice_currency_rate': 1.00,
            'l10n_hu_invoice_chain_index': -1,
            'l10n_hu_payment_mode': False,
            'amount_untaxed': 21794.00,
            'amount_tax': 0.00,
            'amount_total': 21794.00,
        }])
        self.assertRecordValues(bill.invoice_line_ids, [
            {
                'name': 'Jubba 31',
                'quantity': 1.00,
                'price_unit': 4799.00,
                'discount': 0.00,
                'tax_ids': [],
            },
            {
                'name': 'Nelson 23',
                'quantity': 2.00,
                'price_unit': 6499.00,
                'discount': 0.00,
                'tax_ids': [],
            },
            {
                'name': 'Daugava 16',
                'quantity': 1.00,
                'price_unit': 999.00,
                'discount': 0.00,
                'tax_ids': [],
            },
            {
                'name': 'Daugava 16',
                'quantity': 1.00,
                'price_unit': 799.00,
                'discount': 0.00,
                'tax_ids': [],
            },
            {
                'name': 'Kolyma 26',
                'quantity': 1.00,
                'price_unit': 2199.00,
                'discount': 0.00,
                'tax_ids': [],
            },
        ])
        self.assertRecordValues(bill.partner_id, [{
            'name': 'Jurisics Miklós',
            'vat': '99943339',
            'l10n_hu_group_vat': False,
        }])

    def test_batch_modifications_upload(self):
        self.upload_xml('batch_modifications.xml')
        refunds = self.env['account.move'].search([('ref', '=ilike', '1562695%')])
        self.assertRecordValues(refunds, [
            {
                'move_type': 'in_refund',
                'ref': '1562695-2',
                'invoice_date': fields.Date.from_string('2024-11-29'),
                'delivery_date': fields.Date.from_string('2024-11-29'),
                'invoice_date_due': fields.Date.from_string('2024-12-20'),
                'currency_id': self.currency_huf.id,
                'invoice_currency_rate': 1.00,
                'l10n_hu_invoice_chain_index': 1,
                'l10n_hu_payment_mode': 'TRANSFER',
                'amount_untaxed': 1200.00,
                'amount_tax': 0.00,
                'amount_total': 1200.00,
            },
            {
                'move_type': 'in_refund',
                'ref': '1562695-1',
                'invoice_date': fields.Date.from_string('2024-11-29'),
                'delivery_date': fields.Date.from_string('2024-11-29'),
                'invoice_date_due': fields.Date.from_string('2024-12-20'),
                'currency_id': self.currency_huf.id,
                'invoice_currency_rate': 1.00,
                'l10n_hu_invoice_chain_index': 1,
                'l10n_hu_payment_mode': 'TRANSFER',
                'amount_untaxed': 4752.48,
                'amount_tax': 1283.17,
                'amount_total': 6035.65,
            },
        ])
        self.assertRecordValues(refunds[0].invoice_line_ids, [
            {
                'name': 'Delaware 19',
                'quantity': 6.00,
                'price_unit': 50.00,
                'discount': 0.00,
                'tax_ids': self.tax_purchase_exempt.ids,
            },
            {
                'name': 'Delaware 19',
                'quantity': 12.00,
                'price_unit': 50.00,
                'discount': 0.00,
                'tax_ids': self.tax_purchase_exempt.ids,
            },
            {
                'name': 'Delaware 19',
                'quantity': 6.00,
                'price_unit': 50.00,
                'discount': 0.00,
                'tax_ids': self.tax_purchase_exempt.ids,
            },
        ])
        self.assertRecordValues(refunds[1].invoice_line_ids, [
            {
                'name': 'Murrumbidgee 17',
                'quantity': 24.00,
                'price_unit': 198.02,
                'discount': 0.00,
                'tax_ids': self.tax_purchase_27.ids,
            },
        ])
        self.assertRecordValues(refunds.partner_id, [{
            'name': 'Almásy László 1',
            'vat': '99938620',
            'l10n_hu_group_vat': False,
        }])

    def test_query_invoice_data_response_upload(self):
        bill = self.upload_xml('query_invoice_data_response.xml')
        self.assertRecordValues(bill, [{
            'move_type': 'in_invoice',
            'ref': '2023/XT23022800',
            'invoice_date': fields.Date.from_string('2023-08-17'),
            'delivery_date': fields.Date.from_string('2023-08-18'),
            'invoice_date_due': False,
            'currency_id': self.currency_huf.id,
            'invoice_currency_rate': 1.00,
            'l10n_hu_invoice_chain_index': -1,
            'l10n_hu_payment_mode': False,
            'amount_untaxed': 148889.70,
            'amount_tax': 40200.30,
            'amount_total': 189090.00,
            'l10n_hu_edi_transaction_code': '4A0GZERATZ6GZ19L',
            'l10n_hu_edi_batch_upload_index': 1,
            'l10n_hu_edi_send_time': fields.Datetime.from_string('2023-08-17 05:50:06'),
        }])
        self.assertRecordValues(bill.invoice_line_ids, [
            {
                'name': 'Seine 14',
                'quantity': 48.00,
                'price_unit': 291.208333,
                'discount': 0.00,
                'tax_ids': self.tax_purchase_27.ids,
            },
            {
                'name': 'Beni 13',
                'quantity': 24.00,
                'price_unit': 236.875000,
                'discount': 0.00,
                'tax_ids': self.tax_purchase_27.ids,
            },
            {
                'name': 'Platte 9',
                'quantity': 192.00,
                'price_unit': 236.890625,
                'discount': 0.00,
                'tax_ids': self.tax_purchase_27.ids,
            },
            {
                'name': 'Sao Francisco 15',
                'quantity': 72.00,
                'price_unit': 211.930556,
                'discount': 0.00,
                'tax_ids': self.tax_purchase_27.ids,
            },
            {
                'name': 'Snake 17',
                'quantity': 240.00,
                'price_unit': 211.929167,
                'discount': 0.00,
                'tax_ids': self.tax_purchase_27.ids,
            },
            {
                'name': 'Saint Lawrence 17',
                'quantity': 48.00,
                'price_unit': 244.750000,
                'discount': 0.00,
                'tax_ids': self.tax_purchase_27.ids,
            },
            {
                'name': 'James 11',
                'quantity': 24.00,
                'price_unit': 244.750000,
                'discount': 0.00,
                'tax_ids': self.tax_purchase_27.ids,
            },
            {
                'name': 'Cocytus 12',
                'quantity': 1.00,
                'price_unit': -0.300000,
                'discount': 0.00,
                'tax_ids': [],
            },
        ])
        self.assertRecordValues(bill.partner_id, [{
            'name': 'Hadik András 2',
            'vat': '99999394-2-44',
            'l10n_hu_group_vat': False,
        }])

    def test_query_invoice_data_response_gzip_upload(self):
        bill = self.upload_xml('query_invoice_data_response_gzip.xml')
        self.assertRecordValues(bill, [{
            'move_type': 'in_invoice',
            'ref': '9859711680',
            'invoice_date': fields.Date.from_string('2024-05-21'),
            'delivery_date': fields.Date.from_string('2024-05-21'),
            'invoice_date_due': False,
            'currency_id': self.currency_huf.id,
            'invoice_currency_rate': 1.00,
            'l10n_hu_invoice_chain_index': -1,
            'l10n_hu_payment_mode': False,
            'amount_untaxed': 126404.56,
            'amount_tax': 32725.23,
            'amount_total': 159129.79,
            'l10n_hu_edi_transaction_code': '4L21E9MOAB7T6DC7',
            'l10n_hu_edi_batch_upload_index': 1,
            'l10n_hu_edi_send_time': fields.Datetime.from_string('2024-05-21 11:26:03'),
        }])

    def test_credit_debit_note_upload(self):
        credit_note_original_bill = self.upload_xml('credit_note_original_bill.xml')
        credit_note = self.upload_xml('credit_note_receive.xml')
        self.assertEqual(credit_note.reversed_entry_id, credit_note_original_bill)

        debit_note_original_bill = self.upload_xml('debit_note_original_bill.xml')
        debit_note = self.upload_xml('debit_note.xml')
        self.assertEqual(debit_note.debit_origin_id, debit_note_original_bill)
