# -*- coding: utf-8 -*-
from odoo import fields, Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestAccruedPurchaseOrders(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_currency = cls.setup_other_currency('XAF')
        cls.alt_exp_account = cls.company_data['default_account_expense'].copy()
        # set 'type' to 'service' to allow manualy set 'qty_delivered' even with purchase_stock installed
        cls.product_a.update({'type': 'service', 'purchase_method': 'receive'})
        cls.product_b.update({'type': 'service', 'purchase_method': 'receive'})
        #analytic distribution
        cls.default_plan = cls.env['account.analytic.plan'].create({'name': 'Default'})
        cls.analytic_account_a = cls.env['account.analytic.account'].create({
            'name': 'analytic_account_a',
            'plan_id': cls.default_plan.id,
            'company_id': False,
        })
        cls.analytic_account_b = cls.env['account.analytic.account'].create({
            'name': 'analytic_account_b',
            'plan_id': cls.default_plan.id,
            'company_id': False,
        })
        cls.product_b.property_account_expense_id = cls.alt_exp_account
        cls.purchase_order = cls.env['purchase.order'].with_context(tracking_disable=True).create({
            'partner_id': cls.partner_a.id,
            'order_line': [
                Command.create({
                    'name': cls.product_a.name,
                    'product_id': cls.product_a.id,
                    'product_qty': 10.0,
                    'product_uom': cls.product_a.uom_id.id,
                    'price_unit': cls.product_a.list_price,
                    'taxes_id': False,
                    'analytic_distribution': {
                        cls.analytic_account_a.id : 80.0,
                        cls.analytic_account_b.id : 20.0,
                    },
                }),
                Command.create({
                    'name': cls.product_b.name,
                    'product_id': cls.product_b.id,
                    'product_qty': 10.0,
                    'product_uom': cls.product_b.uom_id.id,
                    'price_unit': cls.product_b.list_price,
                    'taxes_id': False,
                    'analytic_distribution': {
                        cls.analytic_account_b.id : 100.0,
                    },
                }),
            ],
        })
        cls.purchase_order.button_confirm()
        cls.account_revenue = cls.company_data['default_account_revenue']
        cls.account_expense = cls.company_data['default_account_expense']
        cls.wizard = cls.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'purchase.order',
            'active_ids': cls.purchase_order.ids
        }).create({
            'account_id': cls.account_revenue.id,
        })

    def test_accrued_order(self):
        # nothing to bill : no entries to be created
        with self.assertRaises(UserError):
            self.wizard.create_entries()

        # 5 qty of each product billeable
        self.purchase_order.order_line.qty_received = 5
        self.assertRecordValues(self.env['account.move'].search(self.wizard.create_entries()['domain']).line_ids, [
            # reverse move lines
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 5000},
            {'account_id': self.alt_exp_account.id, 'debit': 0, 'credit': 1000},
            {'account_id': self.account_revenue.id, 'debit': 6000, 'credit': 0},
            # move lines
            {'account_id': self.account_expense.id, 'debit': 5000, 'credit': 0},
            {'account_id': self.alt_exp_account.id, 'debit': 1000, 'credit': 0},
            {'account_id': self.account_revenue.id, 'debit': 0, 'credit': 6000},
        ])

        # received products billed, nothing to bill left
        move = self.env['account.move'].browse(self.purchase_order.action_create_invoice()['res_id'])
        move.invoice_date = '2020-01-01'
        move.action_post()

        with self.assertRaises(UserError):
            self.wizard.create_entries()

    def test_multi_currency_accrued_order(self):
        # 5 qty of each product billeable
        self.purchase_order.order_line.qty_received = 5
        # set currency != company currency
        self.purchase_order.currency_id = self.other_currency
        self.assertRecordValues(self.env['account.move'].search(self.wizard.create_entries()['domain']).line_ids, [
            # reverse move lines
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 5000 / 2, 'amount_currency': -5000},
            {'account_id': self.alt_exp_account.id, 'debit': 0, 'credit': 1000 / 2, 'amount_currency': -1000},
            {'account_id': self.account_revenue.id, 'debit': 6000 / 2, 'credit': 0, 'amount_currency': 0.0},
            # move lines
            {'account_id': self.account_expense.id, 'debit': 5000 / 2, 'credit': 0, 'amount_currency': 5000},
            {'account_id': self.alt_exp_account.id, 'debit': 1000 / 2, 'credit': 0, 'amount_currency': 1000},
            {'account_id': self.account_revenue.id, 'debit': 0, 'credit': 6000 / 2, 'amount_currency': 0.0},
        ])

    def test_analytic_account_accrued_order(self):
        self.purchase_order.order_line.qty_received = 10

        self.assertRecordValues(self.env['account.move'].search(self.wizard.create_entries()['domain']).line_ids, [
            # reverse move lines
            {'account_id': self.account_expense.id, 'debit': 0.0, 'credit': 10000.0, 'analytic_distribution': {str(self.analytic_account_a.id): 80.0, str(self.analytic_account_b.id): 20.0}},
            {'account_id': self.alt_exp_account.id, 'debit': 0.0, 'credit': 2000.0, 'analytic_distribution': {str(self.analytic_account_b.id): 100.0}},
            {'account_id': self.account_revenue.id, 'debit': 12000.0, 'credit': 0.0, 'analytic_distribution': {str(self.analytic_account_a.id): 66.67, str(self.analytic_account_b.id): 33.33}},
            # move lines
            {'account_id': self.account_expense.id, 'debit': 10000.0, 'credit': 0.0, 'analytic_distribution': {str(self.analytic_account_a.id): 80.0, str(self.analytic_account_b.id): 20.0}},
            {'account_id': self.alt_exp_account.id, 'debit': 2000.0, 'credit': 0.0, 'analytic_distribution': {str(self.analytic_account_b.id): 100.0}},
            {'account_id': self.account_revenue.id, 'debit': 0.0, 'credit': 12000.0, 'analytic_distribution': {str(self.analytic_account_a.id): 66.67, str(self.analytic_account_b.id): 33.33}},
        ])

    def test_accrued_order_with_tax_included(self):
        tax_10_included = self.env['account.tax'].create({
            'name': 'Tax 10% included',
            'amount': 10.0,
            'type_tax_use': 'purchase',
            'price_include_override': 'tax_included',
        })
        self.purchase_order.order_line.taxes_id = tax_10_included
        self.purchase_order.order_line.qty_received = 5
        self.assertRecordValues(self.env['account.move'].search(self.wizard.create_entries()['domain']).line_ids, [
            # reverse move lines
            {'account_id': self.account_expense.id, 'debit': 0.0, 'credit': 4545.45},
            {'account_id': self.alt_exp_account.id, 'debit': 0.0, 'credit': 909.09},
            {'account_id': self.account_revenue.id, 'debit': 5454.54, 'credit': 0.0},
            # move lines
            {'account_id': self.account_expense.id, 'debit': 4545.45, 'credit': 0.0},
            {'account_id': self.alt_exp_account.id, 'debit': 909.09, 'credit': 0.0},
            {'account_id': self.account_revenue.id, 'debit': 0.0, 'credit': 5454.54},
        ])

    def test_accrued_order_returned(self):
        self.purchase_order.order_line.qty_received = 10
        # received products billed, nothing to bill left
        move = self.env['account.move'].browse(self.purchase_order.action_create_invoice()['res_id'])
        move.invoice_date = '2020-01-01'
        move.action_post()

        with self.assertRaises(UserError):
            self.wizard.create_entries()

        self.purchase_order.order_line.qty_received = 5
        res = self.env['account.move'].search(self.wizard.create_entries()['domain']).line_ids
        self.assertRecordValues(res, [
            # reverse move lines
            {'account_id': self.account_expense.id, 'debit': 5000.0, 'credit': 0.0},
            {'account_id': self.alt_exp_account.id, 'debit': 1000.0, 'credit': 0.0},
            {'account_id': self.account_revenue.id, 'debit': 0.0, 'credit': 6000.0},
            # move lines
            {'account_id': self.account_expense.id, 'debit': 0.0, 'credit': 5000.0},
            {'account_id': self.alt_exp_account.id, 'debit': 0.0, 'credit': 1000.0},
            {'account_id': self.account_revenue.id, 'debit': 6000.0, 'credit': 0.0},
        ])

        self.purchase_order.order_line.qty_received = 0
        res = self.env['account.move'].search(self.wizard.create_entries()['domain']).line_ids
        self.assertRecordValues(res, [
            # reverse move lines
            {'account_id': self.account_expense.id, 'debit': 5000.0, 'credit': 0.0},
            {'account_id': self.alt_exp_account.id, 'debit': 1000.0, 'credit': 0.0},
            {'account_id': self.account_revenue.id, 'debit': 0.0, 'credit': 6000.0},
            # move lines
            {'account_id': self.account_expense.id, 'debit': 0.0, 'credit': 5000.0},
            {'account_id': self.alt_exp_account.id, 'debit': 0.0, 'credit': 1000.0},
            {'account_id': self.account_revenue.id, 'debit': 6000.0, 'credit': 0.0},
        ])
