from odoo import Command
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class SpreadsheetAccountingFunctionsTest(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.move_22 = cls.env['account.move'].create(
            {
                'company_id': cls.company_data['company'].id,
                'move_type': 'entry',
                'date': '2022-02-02',
                'partner_id': cls.partner_a.id,
                'line_ids': [
                    Command.create(
                        {
                            'name': "line_debit_22",
                            'account_id': cls.company_data['default_account_receivable'].id,
                            'debit': 1500,
                            'company_id': cls.company_data['company'].id,
                        },
                    ),
                    Command.create(
                        {
                            'name': "line_credit_22",
                            'account_id': cls.company_data['default_account_revenue'].id,
                            'credit': 1500,
                            'company_id': cls.company_data['company'].id,
                        },
                    ),
                ],
            }
        )
        cls.move_23 = cls.env['account.move'].create(
            {
                'company_id': cls.company_data['company'].id,
                'move_type': 'entry',
                'date': '2023-02-02',
                'partner_id': cls.partner_a.id,
                'line_ids': [
                    Command.create(
                        {
                            'name': "line_debit_23",
                            'account_id': cls.company_data['default_account_expense'].id,
                            'debit': 2500,
                            'company_id': cls.company_data['company'].id,
                        },
                    ),
                    Command.create(
                        {
                            'name': "line_credit_23",
                            'account_id': cls.company_data['default_account_payable'].id,
                            'credit': 2500,
                            'company_id': cls.company_data['company'].id,
                        },
                    ),
                ],
            }
        )
        cls.move_23_partner_b = cls.move_23.copy({'partner_id': cls.partner_b.id})

    def test_partner_balance_empty_params(self):
        self.assertEqual(self.env['account.account'].spreadsheet_fetch_partner_balance([]), [])

    def test_partner_balance_no_account_codes(self):
        ''' Tests that when no account codes are provided, we are returned the residual
            amount for the receivable and payable accounts.
        '''
        (self.move_22 + self.move_23).action_post()
        partner_balance = self.env['account.account'].spreadsheet_fetch_partner_balance([
            {
                'partner_ids': [self.move_23.partner_id.id],
                'date_range': {
                    'range_type': 'year',
                    'year': 2023,
                },
                'codes': [],
                'company_id': None,
                'include_unposted': False,
            },
            {
                'partner_ids': [self.move_23.partner_id.id],
                'date_range': {
                    'range_type': 'year',
                    'year': 2023,
                },
                'codes': [self.company_data['default_account_receivable'].code],
                'company_id': None,
                'include_unposted': False,
            }
        ])
        self.assertEqual(partner_balance, [{'balance': 1500 - 2500}, {'balance': 1500}])

    def test_partner_balance_yearly(self):
        ''' Test that only moves in the given year are returned when performing a yearly filtering. '''
        partner_balance = self.env['account.account'].spreadsheet_fetch_partner_balance([
            {
                'partner_ids': [self.move_23.partner_id.id],
                'date_range': {
                    'range_type': 'year',
                    'year': 2022,
                },
                'codes': [],
                'company_id': None,
                'include_unposted': True,
            }
        ])
        self.assertEqual(partner_balance, [{'balance': 1500}])

    def test_partner_balance_quarterly(self):
        ''' Test that only moves in the given quarter are returned when performing a quarterly filtering. '''
        partner_balance = self.env['account.account'].spreadsheet_fetch_partner_balance([
            {
                'partner_ids': [self.move_23.partner_id.id],
                'date_range': {
                    'range_type': 'quarter',
                    'year': 2022,
                    'quarter': 4,
                },
                'codes': [],
                'company_id': None,
                'include_unposted': True,
            },
            {
                'partner_ids': [self.move_23.partner_id.id],
                'date_range': {
                    'range_type': 'quarter',
                    'year': 2023,
                    'quarter': 1,
                },
                'codes': [],
                'company_id': None,
                'include_unposted': True,
            }
        ])
        self.assertEqual(partner_balance, [{'balance': 1500}, {'balance': 1500 - 2500}])

    def test_partner_balance_daily(self):
        ''' Test that only moves in the given day are returned when performing a daily filtering. '''
        partner_balance = self.env['account.account'].spreadsheet_fetch_partner_balance([
            {
                'partner_ids': [self.move_23.partner_id.id],
                'date_range': {
                    'range_type': 'day',
                    'year': 2022,
                    'month': 2,
                    'day': 1,
                },
                'codes': [],
                'company_id': None,
                'include_unposted': True,
            },
            {
                'partner_ids': [self.move_23.partner_id.id],
                'date_range': {
                    'range_type': 'day',
                    'year': 2022,
                    'month': 2,
                    'day': 2,
                },
                'codes': [],
                'company_id': None,
                'include_unposted': True,
            }
        ])
        self.assertEqual(partner_balance, [{'balance': 0.0}, {'balance': 1500}])

    def test_partner_balance_posted_filter(self):
        partner_balance = self.env['account.account'].spreadsheet_fetch_partner_balance([
            {
                'partner_ids': [self.move_23.partner_id.id],
                'date_range': {
                    'range_type': 'year',
                    'year': 2023,
                },
                'codes': [],
                'company_id': None,
                'include_unposted': False,
            }
        ])
        self.assertEqual(partner_balance, [{'balance': 0.0}])

        self.move_23.action_post()

        partner_balance = self.env['account.account'].spreadsheet_fetch_partner_balance([
            {
                'partner_ids': [self.move_23.partner_id.id],
                'date_range': {
                    'range_type': 'year',
                    'year': 2023,
                },
                'codes': [],
                'company_id': None,
                'include_unposted': False,
            }
        ])
        self.assertNotEqual(partner_balance, [{'balance': 2500}])

    def test_partner_filter(self):
        partner_balance = self.env['account.account'].spreadsheet_fetch_partner_balance([
            {
                'partner_ids': [self.move_23.partner_id.id],
                'date_range': {
                    'range_type': 'year',
                    'year': 2023,
                },
                'codes': [],
                'company_id': None,
                'include_unposted': True,
            },
            {
                'partner_ids': [self.move_23_partner_b.partner_id.id],
                'date_range': {
                    'range_type': 'year',
                    'year': 2023,
                },
                'codes': [],
                'company_id': None,
                'include_unposted': True,
            },
        ])
        self.assertNotEqual(partner_balance, [{'balance': 1500 + 2500}, {'balance': 2500}])
