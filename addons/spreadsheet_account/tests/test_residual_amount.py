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

        cls.payment_move_22 = cls.env['account.payment'].create({
            'amount': 150.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': cls.partner_a.id,
            'date': '2022-02-10',
        })

        cls.payment_move_23 = cls.env['account.payment'].create({
            'amount': 250.0,
            'payment_type': 'outbound',
            'partner_type': 'customer',
            'partner_id': cls.partner_a.id,
            'date': '2023-02-10',
        })

        # Post the move and payment and reconcile them
        (cls.move_22 + cls.move_23).action_post()
        (cls.payment_move_22 + cls.payment_move_23).action_post()
        (cls.move_22 + cls.payment_move_22.move_id).line_ids\
            .filtered(lambda line: line.account_type == 'asset_receivable')\
            .reconcile()
        (cls.move_23 + cls.payment_move_23.move_id).line_ids\
            .filtered(lambda line: line.account_type == 'asset_receivable')\
            .reconcile()

    def test_residual_empty_params(self):
        self.assertEqual(self.env['account.account'].spreadsheet_fetch_residual_amount([]), [])

    def test_residual_no_account_codes(self):
        ''' Tests that when no account codes are provided, we are returned the residual
            amount for the receivable and payable accounts.
        '''
        residual_amount = self.env['account.account'].spreadsheet_fetch_residual_amount([
            {
                'date_range': {
                    'range_type': 'year',
                    'year': 2023,
                },
                'codes': [],
                'company_id': None,
                'include_unposted': False,
            },
            {
                'date_range': {
                    'range_type': 'year',
                    'year': 2023,
                },
                'codes': [self.company_data['default_account_receivable'].code],
                'company_id': None,
                'include_unposted': False,
            }
        ])
        self.assertEqual(residual_amount, [
            {'amount_residual': 1500 - 2500 + 250 - 150},
            {'amount_residual': 1500 + 250 - 150}
        ])

    def test_residual_yearly(self):
        ''' Test that only moves in the given year are returned when performing a yearly filtering. '''
        residual_amount = self.env['account.account'].spreadsheet_fetch_residual_amount([
            {
                'date_range': {
                    'range_type': 'year',
                    'year': 2022,
                },
                'codes': [],
                'company_id': None,
                'include_unposted': True,
            }
        ])
        self.assertEqual(residual_amount, [{'amount_residual': 1500 - 150}])

    def test_residual_quarterly(self):
        ''' Test that only moves in the given quarter are returned when performing a quarterly filtering. '''
        residual_amount = self.env['account.account'].spreadsheet_fetch_residual_amount([
            {
                'date_range': {
                    'range_type': 'quarter',
                    'year': 2022,
                    'quarter': 4,
                },
                'codes': [],
                'company_id': None,
                'include_unposted': False,
            },
            {
                'date_range': {
                    'range_type': 'quarter',
                    'year': 2023,
                    'quarter': 1,
                },
                'codes': [],
                'company_id': None,
                'include_unposted': False,
            }
        ])
        self.assertEqual(residual_amount, [
            {'amount_residual': 1500 - 150},
            {'amount_residual': 1500 - 2500 - 150 + 250},
        ])

    def test_residual_daily(self):
        ''' Test that only moves in the given day are returned when performing a daily filtering. '''
        residual_amount = self.env['account.account'].spreadsheet_fetch_residual_amount([
            {
                'date_range': {
                    'range_type': 'day',
                    'year': 2022,
                    'month': 2,
                    'day': 1,
                },
                'codes': [],
                'company_id': None,
                'include_unposted': False,
            },
            {
                'date_range': {
                    'range_type': 'day',
                    'year': 2022,
                    'month': 2,
                    'day': 2,
                },
                'codes': [],
                'company_id': None,
                'include_unposted': False,
            }
        ])
        self.assertEqual(residual_amount, [
            {'amount_residual': 0.0},
            {'amount_residual': 1500 - 150},
        ])
