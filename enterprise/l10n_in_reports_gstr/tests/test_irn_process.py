# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import jwt

from odoo.addons.l10n_in_reports_gstr.tests.common import L10nInTestAccountGstReportsCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestIrnProcess(L10nInTestAccountGstReportsCommon):

    def convert_json_in_encoded_format(self, json_data):
        new_json_data = {'data': json.dumps(json_data)}
        encoded_json = jwt.encode(new_json_data, key='', algorithm='none')
        return encoded_json

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_b.vat = "36AABCT1332L011"
        cls.report = cls.gstr_report = cls.env['l10n_in.gst.return.period'].create({
            'company_id': cls.default_company.id,
            'periodicity': 'monthly',
            'year': cls.test_date.strftime('%Y'),
            'month': cls.test_date.strftime('%m'),
        })
        cls.purchase_igst_1 = cls._get_company_tax('igst_purchase_1')
        cls.purchase_igst_18 = cls._get_company_tax('igst_purchase_18')
        cls.purchase_igst_1_rc = cls._get_company_tax('igst_purchase_1_rc')
        cls.purchase_igst_18_rc = cls._get_company_tax('igst_purchase_18_rc')

    def test_irn_process(self):
        # Attach list of IRN JSON data as attachments
        irn_list = self._read_mock_json('list_of_irn_response.json')
        self.report.list_of_irn_json_attachment_ids = self.env['ir.attachment'].create([
            {
                'name': 'file_for_list_of_irn.json',
                'mimetype': 'application/json',
                'raw': json.dumps(irn_list),
            }
        ])

        # Process IRN match data
        self.report.irn_match_data()
        move = self.env['account.move'].search([('state', '=', 'draft'), ('l10n_in_irn_number', '!=', False)])
        self.assertEqual(len(move), 1)

        # for detail IRN
        bill_details = self._read_mock_json('irn_doc_details.json')
        detail_json = self._read_mock_json('irn_doc_response.json')
        detail_json["SignedInvoice"] = self.convert_json_in_encoded_format(bill_details)
        attachment = self.env['ir.attachment'].create({
            'name': f'{move.l10n_in_irn_number}.json',
            'mimetype': 'application/json',
            'raw': json.dumps(detail_json),
            'res_model': 'account.move',
            'res_id': move.id,
        })
        move._extend_with_attachments(attachment, new=True)

        self.assertInvoiceValues(move, [
            {'name': 'Customizable Desk', 'quantity': 1.0, 'tax_ids': self.purchase_igst_18.ids, 'credit': 0.0, 'debit': 500.0, 'amount_currency': 500.0},
            {'name': 'Rounding Value', 'quantity': 1.0, 'tax_ids': [], 'credit': 5.0, 'debit': 0.0, 'amount_currency': -5.0},
            {'name': 'Whiteboard Pen', 'quantity': 5.0, 'tax_ids': self.purchase_igst_1.ids, 'credit': 0.0, 'debit': 500.0, 'amount_currency': 500.0},
            {'name': '1% IGST P', 'quantity': 0.0, 'tax_ids': [], 'credit': 0.0, 'debit': 5.0, 'amount_currency': 5.0},
            {'name': '18% IGST P', 'quantity': 0.0, 'tax_ids': [], 'credit': 0.0, 'debit': 90.0, 'amount_currency': 90.0},
            {'name': 'TEST/0001 installment #1', 'quantity': 0.0, 'tax_ids': [], 'credit': 327.0, 'debit': 0.0, 'amount_currency': -327.0},
            {'name': 'TEST/0001 installment #2', 'quantity': 0.0, 'tax_ids': [], 'credit': 763.0, 'debit': 0.0, 'amount_currency': -763.0}
        ], {'ref': "TEST/0001", 'invoice_date': self.test_date, 'partner_id': self.partner_b.id})

    def test_irn_process_with_reverse_charge_taxes(self):
        # Attach list of IRN JSON data as attachments
        irn_list = self._read_mock_json('list_of_irn_response.json')
        self.report.list_of_irn_json_attachment_ids = self.env['ir.attachment'].create([
            {
                'name': 'file_for_list_of_irn.json',
                'mimetype': 'application/json',
                'raw': json.dumps(irn_list),
            }
        ])

        # Process IRN match data
        self.report.irn_match_data()
        move = self.env['account.move'].search([('state', '=', 'draft'), ('l10n_in_irn_number', '!=', False)])
        self.assertEqual(len(move), 1)

        # for detail IRN
        bill_details = self._read_mock_json('irn_doc_details_with_reverse_charge.json')
        detail_json = self._read_mock_json('irn_doc_response.json')
        detail_json["SignedInvoice"] = self.convert_json_in_encoded_format(bill_details)
        attachment = self.env['ir.attachment'].create({
            'name': f'{move.l10n_in_irn_number}.json',
            'mimetype': 'application/json',
            'raw': json.dumps(detail_json),
            'res_model': 'account.move',
            'res_id': move.id,
        })
        move._extend_with_attachments(attachment, new=True)

        self.assertInvoiceValues(move, [
            {'name': 'Customizable Desk', 'quantity': 1.0, 'tax_ids': self.purchase_igst_18_rc.ids, 'credit': 0.0, 'debit': 500.0, 'amount_currency': 500.0},
            {'name': 'Whiteboard Pen', 'quantity': 5.0, 'tax_ids': self.purchase_igst_1_rc.ids, 'credit': 0.0, 'debit': 500.0, 'amount_currency': 500.0},
            {'name': '1% IGST RC', 'quantity': 0.0, 'tax_ids': [], 'credit': 5.0, 'debit': 0.0, 'amount_currency': -5.0},
            {'name': '1% IGST RC', 'quantity': 0.0, 'tax_ids': [], 'credit': 0.0, 'debit': 5.0, 'amount_currency': 5.0},
            {'name': '18% IGST RC', 'quantity': 0.0, 'tax_ids': [], 'credit': 90.0, 'debit': 0.0, 'amount_currency': -90.0},
            {'name': '18% IGST RC', 'quantity': 0.0, 'tax_ids': [], 'credit': 0.0, 'debit': 90.0, 'amount_currency': 90.0},
            {'name': 'TEST/0001 installment #1', 'quantity': 0.0, 'tax_ids': [], 'credit': 300.0, 'debit': 0.0, 'amount_currency': -300.0},
            {'name': 'TEST/0001 installment #2', 'quantity': 0.0, 'tax_ids': [], 'credit': 700.0, 'debit': 0.0, 'amount_currency': -700.0},
        ], {'ref': "TEST/0001", 'invoice_date': self.test_date, 'partner_id': self.partner_b.id})

    def test_irn_process_with_unknown_taxes(self):
        # Attach list of IRN JSON data as attachments
        irn_list = self._read_mock_json('list_of_irn_response.json')
        self.report.list_of_irn_json_attachment_ids = self.env['ir.attachment'].create([
            {
                'name': 'file_for_list_of_irn.json',
                'mimetype': 'application/json',
                'raw': json.dumps(irn_list),
            }
        ])

        # Process IRN match data
        self.report.irn_match_data()
        move = self.env['account.move'].search([('state', '=', 'draft'), ('l10n_in_irn_number', '!=', False)])
        self.assertEqual(len(move), 1)

        # for detail IRN
        bill_details = self._read_mock_json('irn_doc_details_with_unknown_taxes.json')
        detail_json = self._read_mock_json('irn_doc_response.json')
        detail_json["SignedInvoice"] = self.convert_json_in_encoded_format(bill_details)
        attachment = self.env['ir.attachment'].create({
            'name': f'{move.l10n_in_irn_number}.json',
            'mimetype': 'application/json',
            'raw': json.dumps(detail_json),
            'res_model': 'account.move',
            'res_id': move.id,
        })
        move._extend_with_attachments(attachment, new=True)

        self.assertInvoiceValues(move, [
            {'name': '10.0% (IGST)', 'quantity': 1.0, 'tax_ids': [], 'credit': 0.0, 'debit': 50.0, 'amount_currency': 50.0},
            {'name': 'Customizable Desk', 'quantity': 1.0, 'tax_ids': [], 'credit': 0.0, 'debit': 500.0, 'amount_currency': 500.0},
            {'name': 'Whiteboard Pen', 'quantity': 5.0, 'tax_ids': self.purchase_igst_1.ids, 'credit': 0.0, 'debit': 500.0, 'amount_currency': 500.0},
            {'name': '1% IGST P', 'quantity': 0.0, 'tax_ids': [], 'credit': 0.0, 'debit': 5.0, 'amount_currency': 5.0},
            {'name': 'TEST/0001 installment #1', 'quantity': 0.0, 'tax_ids': [], 'credit': 316.5, 'debit': 0.0, 'amount_currency': -316.5},
            {'name': 'TEST/0001 installment #2', 'quantity': 0.0, 'tax_ids': [], 'credit': 738.5, 'debit': 0.0, 'amount_currency': -738.5}
        ], {'ref': "TEST/0001", 'invoice_date': self.test_date, 'partner_id': self.partner_b.id})
