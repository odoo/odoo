# -*- coding: utf-8 -*-
from odoo import fields, Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged, Form
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestAccruedPurchaseStock(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        uom_unit = cls.env.ref('uom.product_uom_unit')
        product = cls.env['product.product'].create({
            'name': "Product",
            'list_price': 30.0,
            'type': 'consu',
            'uom_id': uom_unit.id,
        })

        cls.purchase_order = cls.env['purchase.order'].create({
            'partner_id': cls.partner_a.id,
            'order_line': [
                Command.create({
                    'name': product.name,
                    'product_id': product.id,
                    'product_qty': 10.0,
                    'product_uom_id': product.uom_id.id,
                    'price_unit': product.list_price,
                    'taxes_id': False,
                }),
            ]
        })
        cls.purchase_order.button_confirm()
        cls.account_expense = cls.company_data['default_account_expense']
        cls.account_revenue = cls.company_data['default_account_revenue']

    def test_purchase_stock_accruals(self):
        # receive 2 on 2020-01-02
        pick = self.purchase_order.picking_ids
        pick.move_ids.write({
            'quantity': 2,
            'picked': True,
        })
        pick.button_validate()
        Form.from_action(self.env, pick.button_validate()).save().process()
        pick.move_ids.write({'date': fields.Date.to_date('2020-01-02')})

        # receive 3 on 2020-01-06
        pick = pick.copy()
        pick.move_ids.write({'quantity': 3, 'picked': True})
        pick.button_validate()
        pick.move_ids.write({'date': fields.Date.to_date('2020-01-06')})

        wizard = self.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'purchase.order',
            'active_ids': self.purchase_order.ids,
        }).create({
            'account_id': self.account_expense.id,
            'date': '2020-01-01',
        })
        # nothing to invoice on 2020-01-01
        with self.assertRaises(UserError):
            wizard.create_entries()

        # 2 to invoice on 2020-01-04
        wizard.date = fields.Date.to_date('2020-01-04')
        self.assertRecordValues(self.env['account.move'].search(wizard.create_entries()['domain']).line_ids, [
            # reverse move lines
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 60},
            {'account_id': wizard.account_id.id, 'debit': 60, 'credit': 0},
            # move lines
            {'account_id': self.account_expense.id, 'debit': 60, 'credit': 0},
            {'account_id': wizard.account_id.id, 'debit': 0, 'credit': 60},
        ])

        # 5 to invoice on 2020-01-07
        wizard.date = fields.Date.to_date('2020-01-07')
        self.assertRecordValues(self.env['account.move'].search(wizard.create_entries()['domain']).line_ids, [
            # reverse move lines
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 150},
            {'account_id': wizard.account_id.id, 'debit': 150, 'credit': 0},
            # move lines
            {'account_id': self.account_expense.id, 'debit': 150, 'credit': 0},
            {'account_id': wizard.account_id.id, 'debit': 0, 'credit': 150},
        ])

    def test_purchase_stock_invoiced_accrued_entries(self):
        # deliver 2 on 2020-01-02
        pick = self.purchase_order.picking_ids
        pick.move_ids.write({'quantity': 2, 'picked': True})
        pick.button_validate()
        Form.from_action(self.env, pick.button_validate()).save().process()
        pick.move_ids.write({'date': fields.Date.to_date('2020-01-02')})

        # invoice on 2020-01-04
        move = self.env['account.move'].browse(self.purchase_order.action_create_invoice()['res_id'])
        move.invoice_date = fields.Date.to_date('2020-01-04')
        move.action_post()

        # deliver 3 on 2020-01-06
        pick = pick.copy()
        pick.move_ids.write({'quantity': 3, 'picked': True})
        pick.button_validate()
        pick.move_ids.write({'date': fields.Date.to_date('2020-01-06')})

        # invoice on 2020-01-08
        move = self.env['account.move'].browse(self.purchase_order.action_create_invoice()['res_id'])
        move.invoice_date = fields.Date.to_date('2020-01-08')
        move.action_post()

        wizard = self.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'purchase.order',
            'active_ids': self.purchase_order.ids,
        }).create({
            'account_id': self.company_data['default_account_expense'].id,
            'date': '2020-01-02',
        })

        # 2 to invoice on 2020-01-07
        self.assertRecordValues(self.env['account.move'].search(wizard.create_entries()['domain']).line_ids, [
            # reverse move lines
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 60},
            {'account_id': wizard.account_id.id, 'debit': 60, 'credit': 0},
            # move lines
            {'account_id': self.account_expense.id, 'debit': 60, 'credit': 0},
            {'account_id': wizard.account_id.id, 'debit': 0, 'credit': 60},
        ])

        # nothing to invoice on 2020-01-05
        wizard.date = fields.Date.to_date('2020-01-05')
        with self.assertRaises(UserError):
            wizard.create_entries()

        # 3 to invoice on 2020-01-07
        wizard.date = fields.Date.to_date('2020-01-07')
        self.assertRecordValues(self.env['account.move'].search(wizard.create_entries()['domain']).line_ids, [
            # reverse move lines
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 90},
            {'account_id': wizard.account_id.id, 'debit': 90, 'credit': 0},
            # move lines
            {'account_id': self.account_expense.id, 'debit': 90, 'credit': 0},
            {'account_id': wizard.account_id.id, 'debit': 0, 'credit': 90},
        ])

        # nothing to invoice on 2020-01-09
        wizard.date = fields.Date.to_date('2020-01-09')
        with self.assertRaises(UserError):
            wizard.create_entries()
