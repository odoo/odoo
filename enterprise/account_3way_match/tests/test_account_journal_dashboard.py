from freezegun import freeze_time

from odoo.addons.account.tests.test_account_journal_dashboard_common import TestAccountJournalDashboardCommon

from odoo.tests import tagged
from odoo.tools.misc import format_amount


@tagged('post_install', '-at_install')
class AccountJournalDashboard3WayWatchTest(TestAccountJournalDashboardCommon):

    @classmethod
    def init_invoice(cls, move_type, partner=None, invoice_date=None, post=False, products=None, amounts=None, taxes=None, company=False, currency=None, journal=None, invoice_date_due=None, release_to_pay=None):
        move = super().init_invoice(move_type, partner, invoice_date, False, products, amounts, taxes, company, currency, journal)
        if invoice_date_due:
            move.invoice_date_due = invoice_date_due
        if release_to_pay:
            move.release_to_pay = release_to_pay
        if post:
            move.action_post()
        return move

    def test_sale_purchase_journal_for_purchase(self):
        """
        Test different purchase journal setups with or without multicurrency:
            1) Journal with no currency, bills in foreign currency -> dashboard data should be displayed in company currency
            2) Journal in foreign currency, bills in foreign currency -> dashboard data should be displayed in foreign currency
            3) Journal in foreign currency, bills in company currency -> dashboard data should be displayed in foreign currency
            4) Journal in company currency, bills in company currency -> dashboard data should be displayed in company currency
            5) Journal in company currency, bills in foreign currency -> dashboard data should be displayed in company currency
        """
        foreign_currency = self.other_currency
        company_currency = self.company_data['currency']

        setup_values = [
            [self.company_data['default_journal_purchase'], foreign_currency],
            [self.company_data['default_journal_purchase'].copy({'currency_id': foreign_currency.id, 'default_account_id': self.company_data['default_account_expense'].id}), foreign_currency],
            [self.company_data['default_journal_purchase'].copy({'currency_id': foreign_currency.id, 'default_account_id': self.company_data['default_account_expense'].id}), company_currency],
            [self.company_data['default_journal_purchase'].copy({'currency_id': company_currency.id, 'default_account_id': self.company_data['default_account_expense'].id}), company_currency],
            [self.company_data['default_journal_purchase'].copy({'currency_id': company_currency.id, 'default_account_id': self.company_data['default_account_expense'].id}), foreign_currency],
        ]

        expected_vals_list = [
            # number_draft, sum_draft, number_waiting, sum_waiting, number_late, sum_late, currency
            [            1,       100,              1,          55,           1,       55, company_currency],
            [            1,       200,              1,         110,           1,      110, foreign_currency],
            [            1,       400,              1,         220,           1,      220, foreign_currency],
            [            1,       200,              1,         110,           1,      110, company_currency],
            [            1,       100,              1,          55,           1,       55, company_currency],
        ]

        for (purchase_journal, bill_currency), expected_vals in zip(setup_values, expected_vals_list):
            with self.subTest(purchase_journal_currency=purchase_journal.currency_id, bill_currency=bill_currency, expected_vals=expected_vals):
                bill = self.init_invoice('in_invoice', invoice_date='2017-01-01', post=True, amounts=[200], currency=bill_currency, journal=purchase_journal)
                _draft_bill = self.init_invoice('in_invoice', invoice_date='2017-01-01', post=False, amounts=[200], currency=bill_currency, journal=purchase_journal)

                payment = self.init_payment(-90, post=True, date='2017-01-01', currency=bill_currency)
                (bill + payment.move_id).line_ids.filtered_domain([
                    ('account_id', '=', self.company_data['default_account_payable'].id)
                ]).reconcile()

                self.assertDashboardPurchaseSaleData(purchase_journal, *expected_vals)

    @freeze_time("2023-03-15")
    def test_purchase_journal_numbers_and_sums(self):
        company_currency = self.company_data['currency']
        journal = self.company_data['default_journal_purchase']

        self._create_test_vendor_bills(journal)

        dashboard_data = journal._get_journal_dashboard_data_batched()[journal.id]
        # Expected behavior is to have three moves waiting for payment for a total amount of 4440$ one of which would be late
        # for a total amount of 40$ (second move has one of three lines late but that's not enough to make the move late)
        self.assertEqual(3, dashboard_data['number_waiting'])
        self.assertEqual(format_amount(self.env, 4440, company_currency), dashboard_data['sum_waiting'])
        self.assertEqual(1, dashboard_data['number_late'])
        self.assertEqual(format_amount(self.env, 40, company_currency), dashboard_data['sum_late'])

    @freeze_time("2019-01-22")
    def test_customer_invoice_dashboard(self):
        journal = self.company_data['default_journal_sale']

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'journal_id': journal.id,
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-21',
            'date': '2019-01-21',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'quantity': 40.0,
                'name': 'product test 1',
                'discount': 10.00,
                'price_unit': 2.27,
                'tax_ids': [],
            })]
        })
        refund = self.env['account.move'].create({
            'move_type': 'out_refund',
            'journal_id': journal.id,
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-21',
            'date': '2019-01-21',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'quantity': 1.0,
                'name': 'product test 1',
                'price_unit': 13.3,
                'tax_ids': [],
            })]
        })

        # Check Draft
        dashboard_data = journal._get_journal_dashboard_data_batched()[journal.id]

        self.assertEqual(dashboard_data['number_draft'], 2)
        self.assertIn('68.42', dashboard_data['sum_draft'])

        self.assertEqual(dashboard_data['number_waiting'], 0)
        self.assertIn('0.00', dashboard_data['sum_waiting'])

        # Check Both
        invoice.action_post()

        dashboard_data = journal._get_journal_dashboard_data_batched()[journal.id]
        self.assertEqual(dashboard_data['number_draft'], 1)
        self.assertIn('-\N{ZERO WIDTH NO-BREAK SPACE}13.30', dashboard_data['sum_draft'])

        self.assertEqual(dashboard_data['number_waiting'], 1)
        self.assertIn('81.72', dashboard_data['sum_waiting'])

        # Check partial on invoice
        partial_payment = self.env['account.payment'].create({
            'amount': 13.3,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
        })
        partial_payment.action_post()

        (invoice + partial_payment.move_id).line_ids.filtered(lambda line: line.account_type == 'asset_receivable').reconcile()

        dashboard_data = journal._get_journal_dashboard_data_batched()[journal.id]
        self.assertEqual(dashboard_data['number_draft'], 1)
        self.assertIn('13.3', dashboard_data['sum_draft'])

        self.assertEqual(dashboard_data['number_waiting'], 1)
        self.assertIn('68.42', dashboard_data['sum_waiting'])

        # Check waiting payment
        refund.action_post()

        dashboard_data = journal._get_journal_dashboard_data_batched()[journal.id]
        self.assertEqual(dashboard_data['number_draft'], 0)
        self.assertIn('0.00', dashboard_data['sum_draft'])

        self.assertEqual(dashboard_data['number_waiting'], 2)
        self.assertIn('55.12', dashboard_data['sum_waiting'])

        # Check partial on refund
        payment = self.env['account.payment'].create({
            'amount': 10.0,
            'payment_type': 'outbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
        })
        payment.action_post()

        (refund + payment.move_id).line_ids\
            .filtered(lambda line: line.account_type == 'asset_receivable')\
            .reconcile()

        dashboard_data = journal._get_journal_dashboard_data_batched()[journal.id]
        self.assertEqual(dashboard_data['number_draft'], 0)
        self.assertIn('0.00', dashboard_data['sum_draft'])

        self.assertEqual(dashboard_data['number_waiting'], 2)
        self.assertIn('65.12', dashboard_data['sum_waiting'])

        dashboard_data = journal._get_journal_dashboard_data_batched()[journal.id]
        self.assertEqual(dashboard_data['number_late'], 2)
        self.assertIn('65.12', dashboard_data['sum_late'])

    def test_sale_purchase_journal_for_multi_currency_sale(self):
        currency = self.other_currency
        company_currency = self.company_data['currency']

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': currency.id,
            'invoice_line_ids': [
                (0, 0, {'name': 'test', 'price_unit': 200})
            ],
        })
        invoice.action_post()

        payment = self.env['account.payment'].create({
            'amount': 90.0,
            'date': '2016-01-01',
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'currency_id': currency.id,
        })
        payment.action_post()

        (invoice + payment.move_id).line_ids.filtered_domain([
            ('account_id', '=', self.company_data['default_account_receivable'].id)
        ]).reconcile()

        default_journal_sale = self.company_data['default_journal_sale']
        dashboard_data = default_journal_sale._get_journal_dashboard_data_batched()[default_journal_sale.id]
        self.assertEqual(format_amount(self.env, 55, company_currency), dashboard_data['sum_waiting'])
        self.assertEqual(format_amount(self.env, 55, company_currency), dashboard_data['sum_late'])

    @freeze_time("2023-03-15")
    def test_purchase_journal_numbers_and_sums_to_validate(self):
        company_currency = self.company_data['currency']
        journal = self.company_data['default_journal_purchase']

        datas = [
            {'invoice_date_due': '2023-04-30'},
            {'invoice_date_due': '2023-04-30', 'release_to_pay': 'yes'},
            {'invoice_date_due': '2023-04-30', 'release_to_pay': 'no'},
            {'invoice_date_due': '2023-03-01'},
            {'invoice_date_due': '2023-03-01', 'release_to_pay': 'yes'},
            {'invoice_date_due': '2023-03-01', 'release_to_pay': 'no'},
        ]

        for data in datas:
            self.init_invoice('in_invoice', invoice_date='2023-03-01', post=False, amounts=[4000], journal=journal, invoice_date_due=data['invoice_date_due'], release_to_pay=data.get('release_to_pay'))

        dashboard_data = journal._get_journal_dashboard_data_batched()[journal.id]
        # Expected behavior is to have six amls waiting for payment for a total amount of 4440$
        # three of which would be late for a total amount of 140$
        self.assertEqual(4, dashboard_data['number_draft'])
        self.assertEqual(format_amount(self.env, 16000, company_currency), dashboard_data['sum_draft'])
