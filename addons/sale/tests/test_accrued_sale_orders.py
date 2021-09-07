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
        uom_hour = cls.env.ref('uom.product_uom_hour')
        cls.alt_inc_account = cls.company_data['default_account_revenue'].copy()
        cls.currency_a = cls.env['res.currency'].create({
            'name': 'CUR',
            'symbol': 'c',
            'rounding': 0.01,
        })
        cls.env['res.currency.rate'].create({
            'currency_id': cls.currency_a.id,
            'rate': 1.5,
        })
        cls.product1 = cls.env['product.product'].create({
            'name': "Product",
            'list_price': 30.0,
            'type': 'service',
            'uom_id': uom_hour.id,
            'uom_po_id': uom_hour.id,
            'invoice_policy': 'delivery',
            'property_account_income_id': cls.alt_inc_account.id,
        })
        cls.product2 = cls.env['product.product'].create({
            'name': "Service",
            'list_price': 50.0,
            'type': 'service',
            'uom_id': uom_hour.id,
            'uom_po_id': uom_hour.id,
            'invoice_policy': 'delivery',
        })
        cls.sale_order = cls.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': cls.partner_a.id,
            'order_line': [
                Command.create({
                    'name': cls.product1.name,
                    'product_id': cls.product1.id,
                    'product_uom_qty': 10.0,
                    'product_uom': cls.product1.uom_id.id,
                    'price_unit': cls.product1.list_price,
                    'tax_id': False,
                }),
                Command.create({
                    'name': cls.product2.name,
                    'product_id': cls.product2.id,
                    'product_uom_qty': 10.0,
                    'product_uom': cls.product2.uom_id.id,
                    'price_unit': cls.product2.list_price,
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
            {'account_id': self.alt_inc_account.id, 'debit': 150, 'credit': 0},
            {'account_id': self.account_revenue.id, 'debit': 250, 'credit': 0},
            {'account_id': self.wizard.account_id.id, 'debit': 0, 'credit': 400},
            # move lines
            {'account_id': self.alt_inc_account.id, 'debit': 0, 'credit': 150},
            {'account_id': self.account_revenue.id, 'debit': 0, 'credit': 250},
            {'account_id': self.wizard.account_id.id, 'debit': 400, 'credit': 0},
        ])

        # delivered products invoiced, nothing to invoice left
        self.sale_order._create_invoices().action_post()
        self.wizard.create_entries()
        self.assertTrue(self.wizard.display_amount)

    def test_multi_currency_accrued_order(self):
        # 5 qty of each product billeable
        self.sale_order.order_line.qty_delivered = 5
        # set currency != company currency
        self.sale_order.currency_id = self.currency_a
        self.assertRecordValues(self.env['account.move'].search(self.wizard.create_entries()['domain']).line_ids, [
            # reverse move lines
            {'account_id': self.alt_inc_account.id, 'debit': 150 / 1.5, 'credit': 0, 'amount_currency': 150},
            {'account_id': self.account_revenue.id, 'debit': 250 / 1.5, 'credit': 0, 'amount_currency': 250},
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 400 / 1.5, 'amount_currency': 0.0},
            # move lines
            {'account_id': self.alt_inc_account.id, 'debit': 0, 'credit': 150 / 1.5, 'amount_currency': -150},
            {'account_id': self.account_revenue.id, 'debit': 0, 'credit': 250 / 1.5, 'amount_currency': -250},
            {'account_id': self.account_expense.id, 'debit': 400 / 1.5, 'credit': 0, 'amount_currency': 0.0},
        ])
