# -*- coding: utf-8 -*-
from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestAccruedSaleOrders(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.alt_inc_account = cls.company_data['default_account_revenue'].copy()
        # set 'invoice_policy' to 'delivery' to take 'qty_delivered' into account when computing 'untaxed_amount_to_invoice'
        # set 'type' to 'service' to allow manualy set 'qty_delivered' even with sale_stock installed
        cls.product_a.update({
            'type': 'service',
            'invoice_policy': 'delivery',
        })
        cls.product_b.update({
            'type': 'service',
            'invoice_policy': 'delivery',
            'property_account_income_id': cls.alt_inc_account.id,
        })
        cls.sale_order = cls.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': cls.partner_a.id,
            'order_line': [
                Command.create({
                    'name': cls.product_a.name,
                    'product_id': cls.product_a.id,
                    'product_uom_qty': 10.0,
                    'product_uom': cls.product_a.uom_id.id,
                    'price_unit': cls.product_a.list_price,
                    'tax_id': False,
                }),
                Command.create({
                    'name': cls.product_b.name,
                    'product_id': cls.product_b.id,
                    'product_uom_qty': 10.0,
                    'product_uom': cls.product_b.uom_id.id,
                    'price_unit': cls.product_b.list_price,
                    'tax_id': False,
                })
            ]
        })
        cls.sale_order.action_confirm()
        cls.account_expense = cls.company_data['default_account_expense']
        cls.account_revenue = cls.company_data['default_account_revenue']
        cls.wizard = cls.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'sale.order',
            'active_ids': cls.sale_order.ids,
        }).create({
            'account_id': cls.account_expense.id,
        })

    def test_accrued_order(self):
        # nothing to invoice : no entries to be created
        with self.assertRaises(UserError):
            self.wizard.create_entries()

        # 5 qty of each product invoiceable
        self.sale_order.order_line.qty_delivered = 5
        self.assertRecordValues(self.env['account.move'].search(self.wizard.create_entries()['domain']).line_ids, [
            # reverse move lines
            {'account_id': self.account_revenue.id, 'debit': 5000, 'credit': 0},
            {'account_id': self.alt_inc_account.id, 'debit': 1000, 'credit': 0},
            {'account_id': self.wizard.account_id.id, 'debit': 0, 'credit': 6000},
            # move lines
            {'account_id': self.account_revenue.id, 'debit': 0, 'credit': 5000},
            {'account_id': self.alt_inc_account.id, 'debit': 0, 'credit': 1000},
            {'account_id': self.wizard.account_id.id, 'debit': 6000, 'credit': 0},
        ])

        # delivered products invoiced, nothing to invoice left
        self.sale_order._create_invoices().action_post()
        self.wizard.create_entries()
        self.assertTrue(self.wizard.display_amount)

    def test_multi_currency_accrued_order(self):
        # 5 qty of each product billeable
        self.sale_order.order_line.qty_delivered = 5
        # self.sale_order.order_line.product_uom_qty = 5
        # set currency != company currency
        self.sale_order.currency_id = self.currency_data['currency']
        self.assertRecordValues(self.env['account.move'].search(self.wizard.create_entries()['domain']).line_ids, [
            # reverse move lines
            {'account_id': self.account_revenue.id, 'debit': 5000 / 2, 'credit': 0, 'amount_currency': 5000},
            {'account_id': self.alt_inc_account.id, 'debit': 1000 / 2, 'credit': 0, 'amount_currency': 1000},
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 6000 / 2, 'amount_currency': 0.0},
            # move lines
            {'account_id': self.account_revenue.id, 'debit': 0, 'credit': 5000 / 2, 'amount_currency': -5000},
            {'account_id': self.alt_inc_account.id, 'debit': 0, 'credit': 1000 / 2, 'amount_currency': -1000},
            {'account_id': self.account_expense.id, 'debit': 6000 / 2, 'credit': 0, 'amount_currency': 0.0},
        ])
