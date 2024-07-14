# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import file_open


@tagged('post_install', '-at_install')
class TestAccountBankStatementImportCSV(AccountTestInvoicingCommon):

    def _import_file(self, csv_file_path):
        # Create a bank account and journal corresponding to the CSV file (same currency and account number)
        bank_journal = self.env['account.journal'].create({
            'name': 'Bank 123456',
            'code': 'BNK67',
            'type': 'bank',
            'bank_acc_number': '123456',
            'currency_id': self.env.ref("base.USD").id,
        })

        # Use an import wizard to process the file
        with file_open(csv_file_path, 'rb') as csv_file:
            action = bank_journal.create_document_from_attachment(self.env['ir.attachment'].create({
                'mimetype': 'text/csv',
                'name': 'test_csv.csv',
                'raw': csv_file.read(),
            }).ids)
        import_wizard = self.env['base_import.import'].browse(
            action['params']['context']['wizard_id']
        ).with_context(action['params']['context'])

        import_wizard_options = {
            'date_format': '%m %d %y',
            'keep_matches': False,
            'encoding': 'utf-8',
            'fields': [],
            'quoting': '"',
            'bank_stmt_import': True,
            'headers': True,
            'separator': ';',
            'float_thousand_separator': ',',
            'float_decimal_separator': '.',
            'advanced': False,
        }
        import_wizard_fields = ['date', False, 'payment_ref', 'amount', 'balance']
        import_wizard.execute_import(import_wizard_fields, [], import_wizard_options, dryrun=False)

    def test_csv_file_import(self):
        self._import_file('account_bank_statement_import_csv/test_csv_file/test_csv.csv')

        # Check the imported bank statement
        imported_statement = self.env['account.bank.statement'].search([('company_id', '=', self.env.company.id)])
        self.assertRecordValues(imported_statement, [{
            'reference': 'test_csv.csv',
            'balance_start': 21699.55,
            'balance_end_real': 23462.55,
        }])
        self.assertRecordValues(imported_statement.line_ids.sorted(lambda line: (line.date, line.payment_ref)), [
            {'date': fields.Date.from_string('2015-02-02'), 'amount': 3728.87,  'payment_ref': 'ACH CREDIT"AMERICAN EXPRESS-SETTLEMENT'},
            {'date': fields.Date.from_string('2015-02-02'), 'amount': -500.08,  'payment_ref': 'DEBIT CARD 6906 EFF 02-01"01/31 INDEED 203-564-2400 CT'},
            {'date': fields.Date.from_string('2015-02-02'), 'amount': -240.00,  'payment_ref': 'DEBIT CARD 6906 EFF 02-01"01/31 MAILCHIMP MAILCHIMP.COMGA'},
            {'date': fields.Date.from_string('2015-02-02'), 'amount': -2064.82, 'payment_ref': 'DEBIT CARD 6906"02/02 COMFORT INNS SAN FRANCISCOCA'},
            {'date': fields.Date.from_string('2015-02-02'), 'amount': -41.64,   'payment_ref': 'DEBIT CARD 6906"BAYSIDE MARKET/1 SAN FRANCISCO CA'},
            {'date': fields.Date.from_string('2015-02-03'), 'amount': 2500.00,  'payment_ref': 'ACH CREDIT"CHECKFLUID INC -013015'},
            {'date': fields.Date.from_string('2015-02-03'), 'amount': -25.00,   'payment_ref': 'ACH DEBIT"AUTHNET GATEWAY -BILLING'},
            {'date': fields.Date.from_string('2015-02-03'), 'amount': -7500.00, 'payment_ref': 'ACH DEBIT"WW 222 BROADWAY -ACH'},
            {'date': fields.Date.from_string('2015-02-03'), 'amount': -45.86,   'payment_ref': 'DEBIT CARD 6906"02/02 DISTRICT SF SAN FRANCISCOCA'},
            {'date': fields.Date.from_string('2015-02-03'), 'amount': -1284.33, 'payment_ref': 'DEBIT CARD 6906"02/02 VIR ATL 9327 180-08628621 CT'},
            {'date': fields.Date.from_string('2015-02-03'), 'amount': -1284.33, 'payment_ref': 'DEBIT CARD 6906"02/02 VIR ATL 9327 180-08628621 CT'},
            {'date': fields.Date.from_string('2015-02-03'), 'amount': -1284.33, 'payment_ref': 'DEBIT CARD 6906"02/02 VIR ATL 9327 180-08628621 CT'},
            {'date': fields.Date.from_string('2015-02-03'), 'amount': -1123.33, 'payment_ref': 'DEBIT CARD 6906"02/02 VIR ATL 9327 180-08628621 CT'},
            {'date': fields.Date.from_string('2015-02-03'), 'amount': -1123.33, 'payment_ref': 'DEBIT CARD 6906"02/02 VIR ATL 9327 180-08628621 CT'},
            {'date': fields.Date.from_string('2015-02-03'), 'amount': -4344.66, 'payment_ref': 'DEBIT CARD 6906"02/03 IBM USED PC 888S 188-874-6742 NY'},
            {'date': fields.Date.from_string('2015-02-03'), 'amount': 8366.00,  'payment_ref': 'DEPOSIT-WIRED FUNDS"TVET OPERATING PLLC'},
            {'date': fields.Date.from_string('2015-02-04'), 'amount': -1284.33, 'payment_ref': 'DEBIT CARD 6906"02/03 VIR ATL 9327 180-08628621 CT'},
            {'date': fields.Date.from_string('2015-02-04'), 'amount': -204.23,  'payment_ref': 'DEBIT CARD 6906"02/04 GROUPON INC 877-788-7858 IL'},
            {'date': fields.Date.from_string('2015-02-05'), 'amount': 9518.40,  'payment_ref': 'ACH CREDIT"MERCHE-SOLUTIONS-MERCH DEP'},
        ])

    def test_csv_file_import_non_ordered(self):
        with self.assertRaises(UserError):
            self._import_file('account_bank_statement_import_csv/test_csv_file/test_csv_non_sorted.csv')

    def test_csv_file_empty_date(self):
        with self.assertRaises(UserError):
            self._import_file('account_bank_statement_import_csv/test_csv_file/test_csv_empty_date.csv')
