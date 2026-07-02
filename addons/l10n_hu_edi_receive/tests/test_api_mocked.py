# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from odoo import fields
from odoo.addons.l10n_hu_edi_receive.tests.common import L10nHuEdiTestCommonReceive
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestApiMocked(L10nHuEdiTestCommonReceive):

    _test_groups = None  # FIXME list needed groups

    def _get_mocked_requests(self):
        return ['queryInvoiceDigest', 'queryInvoiceData']

    def _get_request_file_name(self, service, data):
        batch_suffix = '_batch' if b'batchIndex' in data else ''
        return f'{service + batch_suffix}_request'

    def _get_response_file_name(self, service, data):
        if service == 'queryInvoiceDigest':
            file_name = 'queryInvoiceDigest_response'
        else:
            query = etree.fromstring(data).find('{*}invoiceNumberQuery')
            file_name = query.findtext('{*}invoiceNumber').replace('/', '_')
            if batch_index := query.findtext('{*}batchIndex'):
                file_name += ('_' + batch_index)

        return file_name

    def test_fetching_bills_from_nav(self):
        wizard = self.env['l10n_hu_edi_receive.bills.wizard'].create({})
        with self.patch_post():
            action = wizard.action_receive_bills()
        moves = self.env['account.move'].search(action['params']['next']['domain'])

        self.assertRecordValues(moves, [
            {
                'move_type': 'in_refund',
                'ref': 'BATCH_MOD_2026_0002-2',
                'invoice_date': fields.Date.from_string('2026-02-01'),
                'delivery_date': fields.Date.from_string('2026-01-22'),
                'invoice_date_due': fields.Date.from_string('2026-01-22'),
                'currency_id': self.currency_huf.id,
                'invoice_currency_rate': 1.00,
                'l10n_hu_invoice_chain_index': 1,
                'l10n_hu_payment_mode': False,
                'amount_untaxed': 235.00,
                'amount_tax': 63.45,
                'amount_total': 298.45,
                'l10n_hu_edi_transaction_code': '59BG5EQ2PKD9KXZM',
                'l10n_hu_edi_batch_upload_index': 1,
                'l10n_hu_edi_send_time': fields.Datetime.from_string('2026-01-22 17:21:55'),
                'partner_bank_id': self.company.partner_id.bank_ids.id,
            },
            {
                'move_type': 'in_refund',
                'ref': 'BATCH_MOD_2026_0002-1',
                'invoice_date': fields.Date.from_string('2026-02-01'),
                'delivery_date': fields.Date.from_string('2026-01-22'),
                'invoice_date_due': fields.Date.from_string('2026-01-22'),
                'currency_id': self.currency_huf.id,
                'invoice_currency_rate': 1.00,
                'l10n_hu_invoice_chain_index': 1,
                'l10n_hu_payment_mode': False,
                'amount_untaxed': 735.00,
                'amount_tax': 36.75,
                'amount_total': 771.75,
                'l10n_hu_edi_transaction_code': '59BG5EQ2PKD9KXZM',
                'l10n_hu_edi_batch_upload_index': 1,
                'l10n_hu_edi_send_time': fields.Datetime.from_string('2026-01-22 17:21:55'),
                'partner_bank_id': self.company.partner_id.bank_ids.id,
            },
            {
                'move_type': 'in_invoice',
                'ref': 'INV/2026/00004',
                'invoice_date': fields.Date.from_string('2026-01-22'),
                'delivery_date': fields.Date.from_string('2026-01-22'),
                'invoice_date_due': fields.Date.from_string('2026-01-22'),
                'currency_id': self.currency_huf.id,
                'invoice_currency_rate': 1.00,
                'l10n_hu_invoice_chain_index': -1,
                'l10n_hu_payment_mode': False,
                'amount_untaxed': 235.00,
                'amount_tax': 63.45,
                'amount_total': 298.45,
                'l10n_hu_edi_transaction_code': '59BFCJN2FHW8OIGG',
                'l10n_hu_edi_batch_upload_index': 2,
                'l10n_hu_edi_send_time': fields.Datetime.from_string('2026-01-22 16:59:29'),
                'partner_bank_id': moves.partner_id.bank_ids.id,
            },
            {
                'move_type': 'in_invoice',
                'ref': 'INV/2026/00003',
                'invoice_date': fields.Date.from_string('2026-01-22'),
                'delivery_date': fields.Date.from_string('2026-01-22'),
                'invoice_date_due': fields.Date.from_string('2026-01-22'),
                'currency_id': self.currency_huf.id,
                'invoice_currency_rate': 1.00,
                'l10n_hu_invoice_chain_index': -1,
                'l10n_hu_payment_mode': False,
                'amount_untaxed': 735.00,
                'amount_tax': 36.75,
                'amount_total': 771.75,
                'l10n_hu_edi_transaction_code': '59BFCJN2FHW8OIGG',
                'l10n_hu_edi_batch_upload_index': 1,
                'l10n_hu_edi_send_time': fields.Datetime.from_string('2026-01-22 16:59:29'),
                'partner_bank_id': moves.partner_id.bank_ids.id,
            },
        ])

        self.assertRecordValues(moves[0].invoice_line_ids, [{
            'name': 'Correction – [E-COM10] Pedal Bin',
            'quantity': 5.00,
            'price_unit': 47.00,
            'discount': 0.00,
            'tax_ids': self.tax_purchase_27.ids,
        }])
        self.assertRecordValues(moves[1].invoice_line_ids, [{
            'name': 'Correction – [E-COM06] Corner Desk Right Sit',
            'quantity': 5.00,
            'price_unit': 147.00,
            'discount': 0.00,
            'tax_ids': self.tax_purchase_5.ids,
        }])
        self.assertRecordValues(moves[2].invoice_line_ids, [{
            'name': '[E-COM10] Pedal Bin',
            'quantity': 5.00,
            'price_unit': 47.00,
            'discount': 0.00,
            'tax_ids': self.tax_purchase_27.ids,
        }])
        self.assertRecordValues(moves[3].invoice_line_ids, [{
            'name': '[E-COM06] Corner Desk Right Sit',
            'quantity': 5.00,
            'price_unit': 147.00,
            'discount': 0.00,
            'tax_ids': self.tax_purchase_5.ids,
        }])
        self.assertRecordValues(moves.partner_id, [{
            'name': 'Goodo Systems Kft.',
            'vat': '27470217-2-42',
            'l10n_hu_group_vat': False,
        }])

        self.assertRecordValues(moves.partner_id.bank_ids, [{
            'account_number': 'HU55 1070 0024 7733 4423 2787 4189',
            'holder_name': 'Goodo Systems Kft.',
        }])
        self.assertRecordValues(self.company.partner_id.bank_ids, [{
            'account_number': 'HU55 1070 0024 7733 4423 2787 4189',
            'holder_name': 'company_1_data',
        }])

        move_count_before = self.env['account.move'].search_count([])
        with self.patch_post():
            action = wizard.action_receive_bills()
        moves_count_after = self.env['account.move'].search_count([])
        self.assertEqual(move_count_before, moves_count_after, "No new moves should be created when fetching the same bills again.")
