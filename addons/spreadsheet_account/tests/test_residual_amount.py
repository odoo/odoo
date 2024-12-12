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

    def test_residual_empty_params(self):
        self.assertEqual(self.env['account.account'].spreadsheet_fetch_residual_amount([]), [])

    def test_residual_no_account_codes(self):
        ''' Tests that when no account codes are provided, we are returned the residual
            amount for the receivable and payable accounts.
        '''
        self.move_23.action_post()
        residual_amount = self.env['account.account'].spreadsheet_fetch_residual_amount([
            {
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
        self.assertEqual(residual_amount, [{'amount_residual': self.product_a.standard_price + self.product_b.standard_price}])

    def test_residual_yearly(self):
        ''' Test that only moves in the given year are returned when performing a yearly filtering. '''
        residual_amount = self.env['account.account'].spreadsheet_fetch_residual_amount([
            {
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
        self.assertEqual(residual_amount, [{'amount_residual': self.product_a.standard_price}])

    def test_residual_with_payment(self):
        payment = self.env['account.payment'].create({
            'amount': 100.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
        })

        # Post the move and payment and reconcile them
        self.move_22.action_post()
        payment.action_post()
        (self.move_22 + payment.move_id).line_ids\
            .filtered(lambda line: line.account_type == 'asset_receivable')\
            .reconcile()

        residual_amount = self.env['account.account'].spreadsheet_fetch_residual_amount([
            {
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

        self.assertEqual(residual_amount, [{'amount_residual': self.product_a.standard_price - payment.amount}])

    def test_residual_quarterly(self):
        ''' Test that only moves in the given quarter are returned when performing a quarterly filtering. '''
        self.move_23.action_post()
        residual_amount = self.env['account.account'].spreadsheet_fetch_residual_amount([
            {
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
        self.assertEqual(residual_amount, [{'amount_residual': 0.0}])

        residual_amount = self.env['account.account'].spreadsheet_fetch_residual_amount([
            {
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
        self.assertEqual(residual_amount, [{'amount_residual': self.product_a.standard_price + self.product_b.standard_price}])

    def test_residual_daily(self):
        ''' Test that only moves in the given day are returned when performing a daily filtering. '''
        residual_amount = self.env['account.account'].spreadsheet_fetch_residual_amount([
            {
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
        self.assertEqual(residual_amount, [{'amount_residual': self.product_a.standard_price}])

    def test_residual_posted_filter(self):
        residual_amount = self.env['account.account'].spreadsheet_fetch_residual_amount([
            {
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
        self.assertEqual(residual_amount, [{'amount_residual': 0.0}])

        self.move_23.action_post()

        residual_amount = self.env['account.account'].spreadsheet_fetch_residual_amount([
            {
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
        self.assertNotEqual(residual_amount, [{'amount_residual': self.product_a.standard_price}])
