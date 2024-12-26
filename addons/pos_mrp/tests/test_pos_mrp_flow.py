# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo

from odoo.addons.point_of_sale.tests.common import TestPointOfSaleCommon
from odoo import fields
from odoo.tests import Form

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
            'is_storable': True,
            'lst_price': 10.0,
            'categ_id': category.id,
        })

        self.component_a = self.env['product.product'].create({
            'name': 'Comp A',
            'is_storable': True,
            'available_in_pos': True,
            'lst_price': 10.0,
            'standard_price': 5.0,
        })

        self.component_b = self.env['product.product'].create({
            'name': 'Comp B',
            'is_storable': True,
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
            'last_order_preparation_change': '{}'
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
            'is_storable': True,
        })

        self.kit_2 = self.env['product.product'].create({
            'name': 'Final Kit 2',
            'available_in_pos': True,
            'categ_id': category.id,
            'taxes_id': False,
            'is_storable': True,
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
            'standard_price': 5.0,
            'categ_id': category.id,
            'taxes_id': False,
        })

        self.component_c = self.env['product.product'].create({
            'name': 'Comp C',
            'available_in_pos': True,
            'standard_price': 5.0,
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
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.component_c
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

        bom_product_form = Form(self.env['mrp.bom'])
        bom_product_form.product_id = self.kit_2
        bom_product_form.product_tmpl_id = self.kit_2.product_tmpl_id
        bom_product_form.product_qty = 1.0
        bom_product_form.type = 'phantom'
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.subkit1
            bom_line.product_qty = 2.0
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.subkit2
            bom_line.product_qty = 3.0
        self.final_bom = bom_product_form.save()

        self.pos_config.open_ui()
        order_data = {
            'to_invoice': True,
            'amount_paid': 2.0,
            'amount_return': 0,
            'amount_tax': 0,
            'amount_total': 2.0,
            'date_order': fields.Datetime.to_string(fields.Datetime.now()),
            'fiscal_position_id': False,
            'pricelist_id': self.pos_config.pricelist_id.id,
            'lines': [[0, 0, {
                'discount': 0,
                'pack_lot_ids': [],
                'price_unit': 2,
                'product_id': self.kit.id,
                'price_subtotal': 2,
                'price_subtotal_incl': 2,
                'qty': 1,
                'tax_ids': [(6, 0, self.kit.taxes_id.ids)]}], [0, 0, {
                    'discount': 0,
                    'pack_lot_ids': [],
                    'price_unit': 2,
                    'product_id': self.kit_2.id,
                    'price_subtotal': 2,
                    'price_subtotal_incl': 2,
                    'qty': 1,
                    'tax_ids': [(6, 0, self.kit_2.taxes_id.ids)]}
            ]],
            'name': 'Order 00042-003-0014',
            'partner_id': self.partner1.id,
            'session_id': self.pos_config.current_session_id.id,
            'sequence_number': 2,
            'payment_ids': [[0, 0, {
                'amount': 2.0,
                'name': fields.Datetime.now(),
                'payment_method_id': self.cash_payment_method.id}
            ]],
            'uuid': '00042-003-0014',
            'user_id': self.env.uid
        }
        order = self.env['pos.order'].sync_from_ui([order_data])
        order = self.env['pos.order'].browse(order['pos.order'][0]['id'])
        self.assertEqual(order.lines.filtered(lambda l: l.product_id == self.kit).total_cost, 15.0)
        accounts = self.kit.product_tmpl_id.get_product_accounts()
        debit_interim_account = accounts['stock_output']
        credit_expense_account = accounts['expense']
        invoice_accounts = order.account_move.line_ids.mapped('account_id.id')
        self.assertTrue(debit_interim_account.id in invoice_accounts)
        self.assertTrue(credit_expense_account.id in invoice_accounts)
        expense_line = order.account_move.line_ids.filtered(lambda l: l.account_id.id == credit_expense_account.id)
        self.assertEqual(expense_line.filtered(lambda l: l.product_id == self.kit).credit, 0.0)
        self.assertEqual(expense_line.filtered(lambda l: l.product_id == self.kit).debit, 15.0)
        interim_line = order.account_move.line_ids.filtered(lambda l: l.account_id.id == debit_interim_account.id)
        self.assertEqual(interim_line.filtered(lambda l: l.product_id == self.kit).credit, 15.0)
        self.assertEqual(interim_line.filtered(lambda l: l.product_id == self.kit).debit, 0.0)
        self.pos_config.current_session_id.action_pos_session_closing_control()

    def test_bom_kit_different_uom_invoice_valuation(self):
        """This test make sure that when a kit is made of product using UoM A but the bom line uses UoM B
           the price unit is correctly computed on the invoice lines.
        """
        self.env.user.groups_id += self.env.ref('uom.group_uom')
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
            'is_storable': True,
        })

        self.component_a = self.env['product.product'].create({
            'name': 'Comp A',
            'available_in_pos': True,
            'standard_price': 12000.0,
            'categ_id': category.id,
            'taxes_id': False,
            'uom_id': self.env.ref('uom.product_uom_dozen').id,
        })

        bom_product_form = Form(self.env['mrp.bom'])
        bom_product_form.product_id = self.kit
        bom_product_form.product_tmpl_id = self.kit.product_tmpl_id
        bom_product_form.product_qty = 2.0
        bom_product_form.type = 'phantom'
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.component_a
            bom_line.product_qty = 6.0
            bom_line.product_uom_id = self.env.ref('uom.product_uom_unit')
        self.bom_a = bom_product_form.save()

        self.pos_config.open_ui()
        order_data = {'to_invoice': True,
            'amount_paid': 2.0,
            'amount_return': 0,
            'amount_tax': 0,
            'amount_total': 2.0,
            'date_order': fields.Datetime.to_string(fields.Datetime.now()),
            'fiscal_position_id': False,
            'pricelist_id': self.pos_config.pricelist_id.id,
            'lines': [[0,
                        0,
                        {'discount': 0,
                        'pack_lot_ids': [],
                        'price_unit': 2,
                        'product_id': self.kit.id,
                        'price_subtotal': 2,
                        'price_subtotal_incl': 2,
                        'qty': 2,
                        'tax_ids': []}],
                        ],
                'name': 'Order 00042-003-0014',
                'partner_id': self.partner1.id,
                'session_id': self.pos_config.current_session_id.id,
                'sequence_number': 2,
                'payment_ids': [[0,
                                    0,
                                    {'amount': 2.0,
                                    'name': fields.Datetime.now(),
                                    'payment_method_id': self.cash_payment_method.id}]],
                'uuid': '00042-003-0014',
                'user_id': self.env.uid}
        order = self.env['pos.order'].sync_from_ui([order_data])
        order = self.env['pos.order'].browse(order['pos.order'][0]['id'])
        accounts = self.kit.product_tmpl_id.get_product_accounts()
        expense_line = order.account_move.line_ids.filtered(lambda l: l.account_id.id == accounts['expense'].id)
        self.assertEqual(expense_line.filtered(lambda l: l.product_id == self.kit).debit, 6000.0)
        interim_line = order.account_move.line_ids.filtered(lambda l: l.account_id.id == accounts['stock_output'].id)
        self.assertEqual(interim_line.filtered(lambda l: l.product_id == self.kit).credit, 6000.0)

    def test_bom_kit_order_total_cost_with_shared_component(self):
        category = self.env['product.category'].create({
            'name': 'Category for average cost',
            'property_cost_method': 'average',
        })

        kit_1 = self.env['product.product'].create({
            'name': 'Kit Product 1',
            'available_in_pos': True,
            'is_storable': True,
            'type': 'consu',
            'lst_price': 30.0,
            'categ_id': category.id,
        })

        kit_2 = self.env['product.product'].create({
            'name': 'Kit Product 2',
            'available_in_pos': True,
            'is_storable': True,
            'type': 'consu',
            'lst_price': 200.0,
            'categ_id': category.id,
        })

        shared_component_a = self.env['product.product'].create({
            'name': 'Shared Comp A',
            'is_storable': True,
            'type': 'consu',
            'available_in_pos': True,
            'lst_price': 10.0,
            'standard_price': 5.0,

        })

        other_component_a = self.env['product.product'].create({
            'name': 'Other Comp A',
            'is_storable': True,
            'type': 'consu',
            'available_in_pos': True,
            'lst_price': 20.0,
            'standard_price': 10.0,
        })

        other_component_b = self.env['product.product'].create({
            'name': 'Other Comp B',
            'is_storable': True,
            'type': 'consu',
            'available_in_pos': True,
            'lst_price': 30.0,
            'standard_price': 20.0,
        })

        bom_product_form = Form(self.env['mrp.bom'])
        bom_product_form.product_id = kit_1
        bom_product_form.product_tmpl_id = kit_1.product_tmpl_id
        bom_product_form.product_qty = 1.0
        bom_product_form.type = 'phantom'
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = shared_component_a
            bom_line.product_qty = 1.0
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = other_component_a
            bom_line.product_qty = 1.0
        self.bom_a = bom_product_form.save()

        bom_product_form = Form(self.env['mrp.bom'])
        bom_product_form.product_id = kit_2
        bom_product_form.product_tmpl_id = kit_2.product_tmpl_id
        bom_product_form.product_qty = 1.0
        bom_product_form.type = 'phantom'
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = shared_component_a
            bom_line.product_qty = 10.0
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = other_component_b
            bom_line.product_qty = 5.0
        self.bom_b = bom_product_form.save()

        self.pos_config.open_ui()
        order = self.env['pos.order'].create({
            'session_id': self.pos_config.current_session_id.id,
            'lines': [(0, 0, {
                'name': kit_1.name,
                'product_id': kit_1.id,
                'price_unit': kit_1.lst_price,
                'qty': 1,
                'tax_ids': [[6, False, []]],
                'price_subtotal': kit_1.lst_price,
                'price_subtotal_incl': kit_1.lst_price,
            }), (0, 0, {
                'name': kit_2.name,
                'product_id': kit_2.id,
                'price_unit': kit_2.lst_price,
                'qty': 1,
                'tax_ids': [[6, False, []]],
                'price_subtotal': kit_2.lst_price,
                'price_subtotal_incl': kit_2.lst_price,
            })],
            'pricelist_id': self.pos_config.pricelist_id.id,
            'amount_paid': kit_1.lst_price + kit_2.lst_price,
            'amount_total': kit_1.lst_price + kit_2.lst_price,
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
        self.assertRecordValues(pos_order.lines, [
            {'product_id': kit_1.id, 'total_cost': 15.0},
            {'product_id': kit_2.id, 'total_cost': 150.0},
        ])
