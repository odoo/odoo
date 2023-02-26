# -*- coding: utf-8 -*-
from freezegun import freeze_time

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged

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
            })]
        })

        # Check Draft
        dashboard_data = journal.get_journal_dashboard_datas()

        self.assertEqual(dashboard_data['number_draft'], 2)
        self.assertIn('68.42', dashboard_data['sum_draft'])

        self.assertEqual(dashboard_data['number_waiting'], 0)
        self.assertIn('0.00', dashboard_data['sum_waiting'])

        # Check Both
        invoice.action_post()

        dashboard_data = journal.get_journal_dashboard_datas()
        self.assertEqual(dashboard_data['number_draft'], 1)
        self.assertIn('-13.30', dashboard_data['sum_draft'])

        self.assertEqual(dashboard_data['number_waiting'], 1)
        self.assertIn('81.72', dashboard_data['sum_waiting'])

        # Check waiting payment
        refund.action_post()

        dashboard_data = journal.get_journal_dashboard_datas()
        self.assertEqual(dashboard_data['number_draft'], 0)
        self.assertIn('0.00', dashboard_data['sum_draft'])

        self.assertEqual(dashboard_data['number_waiting'], 2)
        self.assertIn('68.42', dashboard_data['sum_waiting'])

        # Check partial
        receivable_account = refund.line_ids.mapped('account_id').filtered(lambda a: a.internal_type == 'receivable')
        payment = self.env['account.payment'].create({
            'amount': 10.0,
            'payment_type': 'outbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
        })
        payment.action_post()

        (refund + payment.move_id).line_ids\
            .filtered(lambda line: line.account_internal_type == 'receivable')\
            .reconcile()

        dashboard_data = journal.get_journal_dashboard_datas()
        self.assertEqual(dashboard_data['number_draft'], 0)
        self.assertIn('0.00', dashboard_data['sum_draft'])

        self.assertEqual(dashboard_data['number_waiting'], 2)
        self.assertIn('78.42', dashboard_data['sum_waiting'])

        dashboard_data = journal.get_journal_dashboard_datas()
        self.assertEqual(dashboard_data['number_late'], 2)
        self.assertIn('78.42', dashboard_data['sum_late'])

    def test_last_statement(self):
        bank_journal = self.company_data['default_journal_bank']

        invoices = self.env['account.move'].create([
            {
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2022-05-17',
            'date': '2022-05-17',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'quantity': 1.0,
                'name': 'product test 1',
                'price_unit': 500.0,
            })]
            },
            {
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2022-05-18',
            'date': '2022-05-18',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'quantity': 1.0,
                'name': 'product test 1',
                'price_unit': 700.0,
            })]
            },
            {
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2022-05-17',
            'date': '2022-05-17',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'quantity': 1.0,
                'name': 'product test 1',
                'price_unit': 900.0,
            })]
            },
        ])

        invoices.action_post()

        payments = self.env['account.payment'].create([
            {
                'amount': 500.0,
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': self.partner_a.id,
                'journal_id': bank_journal.id,
                'date': '2022-05-17',
            },
            {
                'amount': 700.0,
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': self.partner_a.id,
                'journal_id': bank_journal.id,
                'date': '2022-05-18',
            },
            {
                'amount': 500.0,
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': self.partner_a.id,
                'journal_id': bank_journal.id,
                'date': '2022-05-17',
            },
        ])
        payments.action_post()

        for invoice, payment in zip(invoices, payments):
            (invoice + payment.move_id).line_ids\
                .filtered(lambda line: line.account_internal_type == 'receivable')\
                .reconcile()

        # Create statements in bank journal.
        statements = self.env['account.bank.statement'].create([
            {
            'name': 'BNK1_1',
            'date': '2022-05-17',
            'journal_id': bank_journal.id,
            'line_ids': [
                (0, 0, {'date': '2022-05-17', 'payment_ref': invoices[0].name, 'amount': 500.0}),
                (0, 0, {'date': '2022-05-18', 'payment_ref': invoices[1].name, 'amount': 700.0}),
            ],
            'balance_end_real': 1200.0,
            },
            {
            'name': 'BNK1_2',
            'date': '2022-05-17',
            'journal_id': bank_journal.id,
            'line_ids': [(0, 0, {'date': '2022-05-17', 'payment_ref': invoices[2].name, 'amount': 900.0})],
            'balance_end_real': 2100.0,
            }
        ])

        statements.button_post()

        dashboard = bank_journal.get_journal_dashboard_datas()
        self.assertTrue(dashboard['last_balance'] == dashboard['account_balance'])
