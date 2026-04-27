# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import file_open


@tagged('post_install', '-at_install')
class TestAccountBankStatementImportOFX(AccountTestInvoicingCommon):

    def test_ofx_file_import(self):
        bank_journal = self.env['account.journal'].create({
            'name': 'Bank 123456',
            'code': 'BNK67',
            'type': 'bank',
            'bank_acc_number': '123456',
            'currency_id': self.env.ref('base.USD').id,
        })

        partner_norbert = self.env['res.partner'].create({
            'name': 'Norbert Brant',
            'is_company': True,
        })
        bank_norbert = self.env['res.bank'].create({'name': 'test'})
        partner_bank_norbert = self.env['res.partner.bank'].create({
            'acc_number': 'BE93999574162167',
            'partner_id': partner_norbert.id,
            'bank_id': bank_norbert.id,
        })

        # Get OFX file content
        ofx_file_path = 'account_bank_statement_import_ofx/static/ofx/test_ofx.ofx'
        with file_open(ofx_file_path, 'rb') as ofx_file:
            bank_journal.create_document_from_attachment(self.env['ir.attachment'].create({
                'mimetype': 'application/xml',
                'name': 'test_ofx.ofx',
                'raw': ofx_file.read(),
            }).ids)

        # Check the imported bank statement
        imported_statement = self.env['account.bank.statement'].search([('company_id', '=', self.env.company.id)])
        self.assertRecordValues(imported_statement, [{
            'reference': 'test_ofx.ofx',
            'balance_start': 2516.56,
            'balance_end_real': 2156.56,
        }])
        self.assertRecordValues(imported_statement.line_ids.sorted('payment_ref'), [
            {
                'payment_ref': 'Axelor Scuba',
                'amount': -100.0,
                'partner_id': False,
                'account_number': False,
            },
            {
                'payment_ref': 'China Export',
                'amount': -90.0,
                'partner_id': False,
                'account_number': False,
            },
            {
                'payment_ref': 'China Scuba',
                'amount': -90.0,
                'partner_id': False,
                'account_number': False,
            },
            {
                'payment_ref': partner_norbert.name,
                'amount': -80.0,
                'partner_id': partner_norbert.id,
                'account_number': partner_bank_norbert.acc_number,
            },
        ])

    def test_ofx_file_import_error(self):
        """
        Check if a UserError is triggered when importing a file that contains characters that cannot be decoded with the default encoding
        """
        bank_journal = self.env['account.journal'].create({
            'name': 'Bank 123456',
            'code': 'BNK67',
            'type': 'bank',
            'bank_acc_number': '123456',
            'currency_id': self.env.ref('base.USD').id,
        })

        # Get OFX file content
        # This file contains characters that cannot be decoded with the default encoding - PLEASE DO NOT UPDATE THIS FILE
        ofx_file_path = 'account_bank_statement_import_ofx/static/ofx/test_ofx_unicode_error.ofx'
        with self.assertRaises(UserError, msg="There was an issue decoding the file. Please check the file encoding."):
            with file_open(ofx_file_path, 'rb') as ofx_file:
                bank_journal.create_document_from_attachment(self.env['ir.attachment'].create({
                    'mimetype': 'application/xml',
                    'name': 'test_ofx.ofx',
                    'raw': ofx_file.read(),
                }).ids)
