# -*- coding: utf-8 -*-
from odoo import fields, Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestAccruedPurchaseOrders(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        uom_unit = cls.env.ref('uom.product_uom_unit')
        uom_hour = cls.env.ref('uom.product_uom_hour')
        cls.alt_exp_account = cls.company_data['default_account_expense'].copy()
        cls.currency_a = cls.env['res.currency'].create({
            'name': 'CUR',
            'symbol': 'c',
            'rounding': 0.01,
        })
        cls.env['res.currency.rate'].create({
            'currency_id': cls.currency_a.id,
            'rate': 1.5,
        })
        product_order = cls.env['product.product'].create({
            'name': "Product",
            'list_price': 30.0,
            'type': 'consu',
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
            'purchase_method': 'receive',
            'property_account_expense_id': cls.alt_exp_account.id,
        })
        service_order = cls.env['product.product'].create({
            'name': "Service",
            'list_price': 50.0,
            'type': 'service',
            'uom_id': uom_hour.id,
            'uom_po_id': uom_hour.id,
            'purchase_method': 'receive',
        })
        cls.purchase_order = cls.env['purchase.order'].with_context(tracking_disable=True).create({
            'partner_id': cls.partner_a.id,
            'order_line': [
                Command.create({
                    'name': product_order.name,
                    'product_id': product_order.id,
                    'product_qty': 10.0,
                    'product_uom': product_order.uom_id.id,
                    'price_unit': product_order.list_price,
                    'taxes_id': False,
                }),
                Command.create({
                    'name': service_order.name,
                    'product_id': service_order.id,
                    'product_qty': 10.0,
                    'product_uom': service_order.uom_id.id,
                    'price_unit': service_order.list_price,
                    'taxes_id': False,
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
            {'account_id': self.alt_exp_account.id, 'debit': 0, 'credit': 150},
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 250},
            {'account_id': self.account_revenue.id, 'debit': 400, 'credit': 0},
            # move lines
            {'account_id': self.alt_exp_account.id, 'debit': 150, 'credit': 0},
            {'account_id': self.account_expense.id, 'debit': 250, 'credit': 0},
            {'account_id': self.account_revenue.id, 'debit': 0, 'credit': 400},
        ])

        # received products billed, nothing to bill left
        move = self.env['account.move'].browse(self.purchase_order.action_create_invoice()['res_id'])
        move.invoice_date = fields.Date.today()
        move.action_post()
        with self.assertRaises(UserError):
            self.wizard.create_entries()

    def test_multi_currency_accrued_order(self):
        # 5 qty of each product billeable
        self.purchase_order.order_line.qty_received = 5
        # set currency != company currency
        self.purchase_order.currency_id = self.currency_a
        self.assertRecordValues(self.env['account.move'].search(self.wizard.create_entries()['domain']).line_ids, [
            # reverse move lines
            {'account_id': self.alt_exp_account.id, 'debit': 0, 'credit': 150 / 1.5, 'amount_currency': -150},
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 250 / 1.5, 'amount_currency': -250},
            {'account_id': self.account_revenue.id, 'debit': 400 / 1.5, 'credit': 0, 'amount_currency': 400},
            # move lines
            {'account_id': self.alt_exp_account.id, 'debit': 150 / 1.5, 'credit': 0, 'amount_currency': 150},
            {'account_id': self.account_expense.id, 'debit': 250 / 1.5, 'credit': 0, 'amount_currency': 250},
            {'account_id': self.account_revenue.id, 'debit': 0, 'credit': 400 / 1.5, 'amount_currency': -400},
        ])
