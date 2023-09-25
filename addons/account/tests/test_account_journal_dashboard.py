# -*- coding: utf-8 -*-
from freezegun import freeze_time

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tools.misc import format_amount

@tagged('post_install', '-at_install')
class TestAccountJournalDashboard(AccountTestInvoicingCommon):

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

        # Check waiting payment
        refund.action_post()

        dashboard_data = journal._get_journal_dashboard_data_batched()[journal.id]
        self.assertEqual(dashboard_data['number_draft'], 0)
        self.assertIn('0.00', dashboard_data['sum_draft'])

        self.assertEqual(dashboard_data['number_waiting'], 2)
        self.assertIn('68.42', dashboard_data['sum_waiting'])

        # Check partial
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
        self.assertIn('78.42', dashboard_data['sum_waiting'])

        dashboard_data = journal._get_journal_dashboard_data_batched()[journal.id]
        self.assertEqual(dashboard_data['number_late'], 2)
        self.assertIn('78.42', dashboard_data['sum_late'])

    def test_sale_purchase_journal_for_multi_currency_purchase(self):
        currency = self.currency_data['currency']
        company_currency = self.company_data['currency']

        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
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
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': self.partner_a.id,
            'currency_id': currency.id,
        })
        payment.action_post()

        (invoice + payment.move_id).line_ids.filtered_domain([
            ('account_id', '=', self.company_data['default_account_payable'].id)
        ]).reconcile()

        default_journal_purchase = self.company_data['default_journal_purchase']
        dashboard_data = default_journal_purchase._get_journal_dashboard_data_batched()[default_journal_purchase.id]
        self.assertEqual(format_amount(self.env, 55, company_currency), dashboard_data['sum_waiting'])
        self.assertEqual(format_amount(self.env, 55, company_currency), dashboard_data['sum_late'])

    def test_sale_purchase_journal_for_multi_currency_sale(self):
        currency = self.currency_data['currency']
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
    def test_purchase_journal_numbers_and_sums(self):
        company_currency = self.company_data['currency']
        journal = self.company_data['default_journal_purchase']

        #Setup multiple payments term
        twentyfive_now_term = self.env['account.payment.term'].create({
            'name': '25% now, rest in 30 days',
            'note': 'Pay 25% on invoice date and 75% 30 days later',
            'line_ids': [
                (0, 0, {
                    'value': 'percent',
                    'value_amount': 25.00,
                    'delay_type': 'days_after',
                    'nb_days': 0,
                }),
                (0, 0, {
                    'value': 'percent',
                    'value_amount': 75.00,
                    'delay_type': 'days_after',
                    'nb_days': 30,
                }),
            ],
        })

        self.env['account.move'].create({
            'move_type': 'in_invoice',
            'journal_id': journal.id,
            'partner_id': self.partner_a.id,
            'invoice_date': '2023-04-01',
            'date': '2023-03-15',
            'invoice_payment_term_id': twentyfive_now_term.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'quantity': 1,
                'name': 'product test 1',
                'price_unit': 4000,
                'tax_ids': [],
            })]
        }).action_post()
        # This bill has two amls of 10$. Both are waiting for payment and due in 16 and 46 days.
        # number_waiting += 2, sum_waiting += -4000$, number_late += 0, sum_late += 0$

        self.env['account.move'].create({
            'move_type': 'in_invoice',
            'journal_id': journal.id,
            'partner_id': self.partner_a.id,
            'invoice_date': '2023-03-01',
            'date': '2023-03-15',
            'invoice_payment_term_id': twentyfive_now_term.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'quantity': 1,
                'name': 'product test 1',
                'price_unit': 400,
                'tax_ids': [],
            })]
        }).action_post()
        # This bill has two amls of 100$. One which is late and due 14 days prior and one which is waiting for payment and due in 15 days.
        # number_waiting += 2, sum_waiting += -400$, number_late += 1, sum_late += -100$

        self.env['account.move'].create({
            'move_type': 'in_invoice',
            'journal_id': journal.id,
            'partner_id': self.partner_a.id,
            'invoice_date': '2023-02-01',
            'date': '2023-03-15',
            'invoice_payment_term_id': twentyfive_now_term.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'quantity': 1,
                'name': 'product test 1',
                'price_unit': 40,
                'tax_ids': [],
            })]
        }).action_post()
        # This bill has two amls of 1000$. Both of them are late and due 45 and 15 days prior.
        # number_waiting += 2, sum_waiting += -40$, number_late += 2, sum_late += -40$

        dashboard_data = journal._get_journal_dashboard_data_batched()[journal.id]
        # Expected behavior is to have six amls waiting for payment for a total amount of 4440$
        # three of which would be late for a total amount of 140$
        self.assertEqual(6, dashboard_data['number_waiting'])
        self.assertEqual(format_amount(self.env, 4440, company_currency), dashboard_data['sum_waiting'])
        self.assertEqual(3, dashboard_data['number_late'])
        self.assertEqual(format_amount(self.env, 140, company_currency), dashboard_data['sum_late'])
