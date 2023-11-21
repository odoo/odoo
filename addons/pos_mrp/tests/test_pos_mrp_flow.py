# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo

from odoo.addons.point_of_sale.tests.common import TestPointOfSaleCommon
from odoo import fields
from odoo.tests.common import Form

@odoo.tests.tagged('post_install', '-at_install')
class TestPosMrp(TestPointOfSaleCommon):
    def test_bom_kit_order_total_cost(self):
        #create a product category that use fifo
        category = self.env['product.category'].create({
            'name': 'Category for kit',
            'property_cost_method': 'fifo',
        })

        self.kit = self.env['product.product'].create({
            'name': 'Kit Product',
            'available_in_pos': True,
            'type': 'product',
            'lst_price': 10.0,
            'categ_id': category.id,
        })

        self.component_a = self.env['product.product'].create({
            'name': 'Comp A',
            'type': 'product',
            'available_in_pos': True,
            'lst_price': 10.0,
            'standard_price': 5.0,
        })

        self.component_b = self.env['product.product'].create({
            'name': 'Comp B',
            'type': 'product',
            'available_in_pos': True,
            'lst_price': 10.0,
            'standard_price': 10.0,
        })

        bom_product_form = Form(self.env['mrp.bom'])
        bom_product_form.product_id = self.kit
        bom_product_form.product_tmpl_id = self.kit.product_tmpl_id
        bom_product_form.product_qty = 1.0
        bom_product_form.type = 'phantom'
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.component_a
            bom_line.product_qty = 1.0
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.component_b
            bom_line.product_qty = 1.0
        self.bom_a = bom_product_form.save()

        self.pos_config.open_ui()
        order = self.env['pos.order'].create({
            'session_id': self.pos_config.current_session_id.id,
            'lines': [(0, 0, {
                'name': self.kit.name,
                'product_id': self.kit.id,
                'price_unit': self.kit.lst_price,
                'qty': 1,
                'tax_ids': [[6, False, []]],
                'price_subtotal': self.kit.lst_price,
                'price_subtotal_incl': self.kit.lst_price,
            })],
            'pricelist_id': self.pos_config.pricelist_id.id,
            'amount_paid': self.kit.lst_price,
            'amount_total': self.kit.lst_price,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'to_invoice': False,
        })
        payment_context = {"active_ids": order.ids, "active_id": order.id}
        order_payment = self.PosMakePayment.with_context(**payment_context).create({
            'amount': order.amount_total,
            'payment_method_id': self.cash_payment_method.id
        })
        order_payment.with_context(**payment_context).check()

        self.pos_config.current_session_id.action_pos_session_closing_control()
        pos_order = self.env['pos.order'].search([], order='id desc', limit=1)
        self.assertEqual(pos_order.lines[0].total_cost, 15.0)

    def test_bom_kit_with_kit_invoice_valuation(self):
        # create a product category that use fifo
        category = self.env['product.category'].create({
            'name': 'Category for kit',
            'property_cost_method': 'fifo',
            'property_valuation': 'real_time',
        })

        self.kit = self.env['product.product'].create({
            'name': 'Final Kit',
            'available_in_pos': True,
            'categ_id': category.id,
            'taxes_id': False,
            'type': 'product',
        })

        self.subkit1 = self.env['product.product'].create({
            'name': 'Subkit 1',
            'available_in_pos': True,
            'categ_id': category.id,
            'taxes_id': False,
        })

        self.subkit2 = self.env['product.product'].create({
            'name': 'Subkit 2',
            'available_in_pos': True,
            'categ_id': category.id,
            'taxes_id': False,
        })

        self.component_a = self.env['product.product'].create({
            'name': 'Comp A',
            'available_in_pos': True,
            'standard_price': 5.0,
            'categ_id': category.id,
            'taxes_id': False,
        })

        self.component_b = self.env['product.product'].create({
            'name': 'Comp B',
            'available_in_pos': True,
            'standard_price': 10.0,
            'categ_id': category.id,
            'taxes_id': False,
        })

        bom_product_form = Form(self.env['mrp.bom'])
        bom_product_form.product_id = self.subkit1
        bom_product_form.product_tmpl_id = self.subkit1.product_tmpl_id
        bom_product_form.product_qty = 1.0
        bom_product_form.type = 'phantom'
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.component_a
            bom_line.product_qty = 1.0
        self.bom_a = bom_product_form.save()

        bom_product_form = Form(self.env['mrp.bom'])
        bom_product_form.product_id = self.subkit2
        bom_product_form.product_tmpl_id = self.subkit2.product_tmpl_id
        bom_product_form.product_qty = 1.0
        bom_product_form.type = 'phantom'
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.component_b
            bom_line.product_qty = 1.0
        self.bom_b = bom_product_form.save()

        bom_product_form = Form(self.env['mrp.bom'])
        bom_product_form.product_id = self.kit
        bom_product_form.product_tmpl_id = self.kit.product_tmpl_id
        bom_product_form.product_qty = 1.0
        bom_product_form.type = 'phantom'
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.subkit1
            bom_line.product_qty = 1.0
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.subkit2
            bom_line.product_qty = 1.0
        self.final_bom = bom_product_form.save()

        self.pos_config.open_ui()
        order_data = {'data':
        {'to_invoice': True,
        'amount_paid': 2.0,
        'amount_return': 0,
        'amount_tax': 0,
        'amount_total': 2.0,
        'creation_date': fields.Datetime.to_string(fields.Datetime.now()),
        'fiscal_position_id': False,
        'pricelist_id': self.pos_config.available_pricelist_ids[0].id,
        'lines': [[0,
                    0,
                    {'discount': 0,
                    'pack_lot_ids': [],
                    'price_unit': 2,
                    'product_id': self.kit.id,
                    'price_subtotal': 2,
                    'price_subtotal_incl': 2,
                    'qty': 1,
                    'tax_ids': [(6, 0, self.kit.taxes_id.ids)]}]],
            'name': 'Order 00042-003-0014',
            'partner_id': self.partner1.id,
            'pos_session_id': self.pos_config.current_session_id.id,
            'sequence_number': 2,
            'statement_ids': [[0,
                                0,
                                {'amount': 2.0,
                                'name': fields.Datetime.now(),
                                'payment_method_id': self.cash_payment_method.id}]],
            'uid': '00042-003-0014',
            'user_id': self.env.uid},
        }
        order = self.env['pos.order'].create_from_ui([order_data])
        order = self.env['pos.order'].browse(order[0]['id'])
        accounts = self.kit.product_tmpl_id.get_product_accounts()
        debit_interim_account = accounts['stock_output']
        credit_expense_account = accounts['expense']
        invoice_accounts = order.account_move.line_ids.mapped('account_id.id')
        self.assertTrue(debit_interim_account.id in invoice_accounts)
        self.assertTrue(credit_expense_account.id in invoice_accounts)
        expense_line = order.account_move.line_ids.filtered(lambda l: l.account_id.id == credit_expense_account.id)
        self.assertEqual(expense_line.credit, 0.0)
        self.assertEqual(expense_line.debit, 15.0)
        interim_line = order.account_move.line_ids.filtered(lambda l: l.account_id.id == debit_interim_account.id)
        self.assertEqual(interim_line.credit, 15.0)
        self.assertEqual(interim_line.debit, 0.0)
        self.pos_config.current_session_id.action_pos_session_closing_control()
