# -*- coding: utf-8 -*-
import json

from odoo import fields, Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestAccruedPurchaseOrders(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.alt_exp_account = cls.company_data['default_account_expense'].copy()
        # set 'type' to 'service' to allow manualy set 'qty_delivered' even with purchase_stock installed
        cls.product_a.type = 'service'
        cls.product_b.type = 'service'
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
                }),
                Command.create({
                    'name': cls.product_b.name,
                    'product_id': cls.product_b.id,
                    'product_qty': 10.0,
                    'product_uom': cls.product_b.uom_id.id,
                    'price_unit': cls.product_b.list_price,
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
        self.purchase_order.currency_id = self.currency_data['currency']
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

    def test_accrued_order_account_with_fiscal_position(self):
        expense_account_copy = self.account_expense.copy()

        fiscal_position = self.env['account.fiscal.position'].create({
            'name': 'TEST FISCAL POSITION',
            'company_id': self.env.company.id,
        })

        self.env['account.fiscal.position.account'].create([
            {
                'account_src_id': self.account_expense.id,
                'account_dest_id': expense_account_copy.id,
                'position_id': fiscal_position.id,
            }
        ])

        partner = self.partner_a.copy({'property_account_position_id': fiscal_position.id})

        order = self.purchase_order.copy({
            'partner_id': partner.id,
            'fiscal_position_id': partner.property_account_position_id.id,
            'order_line': [
                Command.create({
                    'name': self.product_a.name,
                    'product_id': self.product_a.id,
                    'product_qty': 10.0,
                    'product_uom': self.product_a.uom_id.id,
                    'price_unit': self.product_a.list_price,
                    'taxes_id': False,
                    'qty_received': 10.0,
                })
            ]
        })

        order.button_confirm()

        wizard = self.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'purchase.order',
            'active_ids': order.ids
        }).create({
            'account_id': self.env['account.account'].create({
                'name': 'Accrued test account',
                'code': 'ATA',
                'user_type_id': self.env.ref('account.data_account_type_current_liabilities').id,
            }).id
        })

        wizard_lines = json.loads(wizard.preview_data)
        account_to_check = wizard_lines['groups_vals'][0]['items_vals'][0][2]['account_id']

        self.assertEqual(account_to_check, expense_account_copy.display_name)

        entries = self.env['account.move'].search(wizard.create_entries()['domain'])

        self.assertRecordValues(entries.filtered('reversed_entry_id').line_ids, [
            {
                'account_id': expense_account_copy.id,
                'debit': 0.0,
                'credit': order.amount_total,
            },
            {
                'account_id': wizard.account_id.id,
                'debit': order.amount_total,
                'credit': 0.0,
            }
        ])

        self.assertRecordValues(entries.filtered('reversal_move_id').line_ids, [
            {
                'account_id': expense_account_copy.id,
                'debit': order.amount_total,
                'credit': 0.0,
            },
            {
                'account_id': wizard.account_id.id,
                'debit': 0.0,
                'credit': order.amount_total,
            }
        ])
