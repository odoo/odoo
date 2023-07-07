# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo

from odoo.addons.point_of_sale.tests.common import TestPointOfSaleCommon
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
