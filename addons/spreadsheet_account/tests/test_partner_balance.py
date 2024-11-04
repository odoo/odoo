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
                'move_type': 'out_invoice',
                'partner_id': cls.partner_a.id,
                'invoice_date': '2022-10-02',
                'invoice_line_ids': [
                    Command.create(
                        {
                            'product_id': cls.product_a.id,
                            'quantity': 1,
                            'price_unit': cls.product_a.standard_price,
                            'tax_ids': None,
                        }
                    ),
                ],
            }
        )
        cls.move_23 = cls.env['account.move'].create(
            {
                'company_id': cls.company_data['company'].id,
                'move_type': 'out_invoice',
                'partner_id': cls.partner_a.id,
                'invoice_date': '2023-07-05',
                'invoice_line_ids': [
                    Command.create(
                        {
                            'product_id': cls.product_a.id,
                            'quantity': 1,
                            'price_unit': cls.product_a.standard_price,
                            'tax_ids': None,
                        }
                    ),
                    Command.create(
                        {
                            'product_id': cls.product_b.id,
                            'quantity': 1,
                            'price_unit': cls.product_b.standard_price,
                            'tax_ids': None,
                        }
                    ),
                ],
            },
        )
        cls.move_23_partner_b = cls.move_23.copy({'partner_id': cls.partner_b.id})

    def test_partner_balance_empty_params(self):
        self.assertEqual(self.env['account.account'].spreadsheet_fetch_partner_balance([]), [])

    def test_partner_balance_no_account_codes(self):
        ''' Tests that when no account codes are provided, we are returned the residual
            amount for the receivable and payable accounts.
        '''
        self.move_23.action_post()
        partner_balance = self.env['account.account'].spreadsheet_fetch_partner_balance([
            {
                'partner_ids': [self.move_23.partner_id.id],
                'date_from': {
                    'range_type': 'year',
                    'year': 2023,
                },
                'date_to': {
                    'range_type': 'year',
                    'year': 2023,
                },
                'codes': [],
                'company_id': None,
                'include_unposted': False,
            }
        ])
        self.assertEqual(partner_balance, [{'balance': self.product_a.standard_price + self.product_b.standard_price}])

    def test_partner_balance_yearly(self):
        ''' Test that only moves in the given year are returned when performing a yearly filtering. '''
        partner_balance = self.env['account.account'].spreadsheet_fetch_partner_balance([
            {
                'partner_ids': [self.move_23.partner_id.id],
                'date_from': {
                    'range_type': 'year',
                    'year': 2022,
                },
                'date_to': {
                    'range_type': 'year',
                    'year': 2022,
                },
                'codes': [self.company_data['default_account_receivable'].code],
                'company_id': None,
                'include_unposted': True,
            }
        ])
        self.assertEqual(partner_balance, [{'balance': self.product_a.standard_price}])

    def test_partner_balance_quarterly(self):
        ''' Test that only moves in the given quarter are returned when performing a quarterly filtering. '''
        self.move_23.action_post()
        partner_balance = self.env['account.account'].spreadsheet_fetch_partner_balance([
            {
                'partner_ids': [self.move_23.partner_id.id],
                'date_from': {
                    'range_type': 'quarter',
                    'year': 2023,
                    'quarter': 1,
                },
                'date_to': {
                    'range_type': 'quarter',
                    'year': 2023,
                    'quarter': 1,
                },
                'codes': [self.company_data['default_account_receivable'].code],
                'company_id': None,
                'include_unposted': False,
            }
        ])
        self.assertEqual(partner_balance, [{'balance': 0.0}])

        partner_balance = self.env['account.account'].spreadsheet_fetch_partner_balance([
            {
                'partner_ids': [self.move_23.partner_id.id],
                'date_from': {
                    'range_type': 'quarter',
                    'year': 2023,
                    'quarter': 3,
                },
                'date_to': {
                    'range_type': 'quarter',
                    'year': 2023,
                    'quarter': 3,
                },
                'codes': [self.company_data['default_account_receivable'].code],
                'company_id': None,
                'include_unposted': False,
            }
        ])
        self.assertEqual(partner_balance, [{'balance': self.product_a.standard_price + self.product_b.standard_price}])

    def test_partner_balance_daily(self):
        ''' Test that only moves in the given day are returned when performing a daily filtering. '''
        partner_balance = self.env['account.account'].spreadsheet_fetch_partner_balance([
            {
                'partner_ids': [self.move_22.partner_id.id],
                'date_from': {
                    'range_type': 'day',
                    'year': 2022,
                    'month': 10,
                    'day': 2,
                },
                'date_to': {
                    'range_type': 'day',
                    'year': 2022,
                    'month': 10,
                    'day': 2,
                },
                'codes': [self.company_data['default_account_receivable'].code],
                'company_id': None,
                'include_unposted': True,
            }
        ])
        self.assertEqual(partner_balance, [{'balance': self.product_a.standard_price}])

    def test_partner_balance_posted_filter(self):
        partner_balance = self.env['account.account'].spreadsheet_fetch_partner_balance([
            {
                'partner_ids': [self.move_23.partner_id.id],
                'date_from': {
                    'range_type': 'year',
                    'year': 2023,
                },
                'date_to': {
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
                'date_from': {
                    'range_type': 'year',
                    'year': 2023,
                },
                'date_to': {
                    'range_type': 'year',
                    'year': 2023,
                },
                'codes': [],
                'company_id': None,
                'include_unposted': False,
            }
        ])
        self.assertNotEqual(partner_balance, [{'balance': self.product_a.standard_price}])

    def test_partner_filter(self):
        partner_balance = self.env['account.account'].spreadsheet_fetch_partner_balance([
            {
                'partner_ids': [self.move_23.partner_id.id],
                'date_from': {
                    'range_type': 'year',
                    'year': 2023,
                },
                'date_to': {
                    'range_type': 'year',
                    'year': 2023,
                },
                'codes': [],
                'company_id': None,
                'include_unposted': False,
            }
        ])
        self.assertNotEqual(partner_balance, [{'balance': self.product_a.standard_price}])

        partner_balance = self.env['account.account'].spreadsheet_fetch_partner_balance([
            {
                'partner_ids': [self.move_23.partner_id.id, self.move_23_partner_b.partner_id.id],
                'date_from': {
                    'range_type': 'year',
                    'year': 2023,
                },
                'date_to': {
                    'range_type': 'year',
                    'year': 2023,
                },
                'codes': [],
                'company_id': None,
                'include_unposted': False,
            }
        ])
        self.assertNotEqual(partner_balance, [{'balance': 2 * self.product_a.standard_price}])
