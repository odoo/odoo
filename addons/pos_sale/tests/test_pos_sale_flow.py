# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.tests.common import Form

@odoo.tests.tagged('post_install', '-at_install')
class TestPoSSale(TestPointOfSaleHttpCommon):
    def test_settle_order_with_kit(self):
        if not self.env["ir.module.module"].search([("name", "=", "mrp"), ("state", "=", "installed")]):
            self.skipTest("mrp module is required for this test")

        self.kit = self.env['product.product'].create({
            'name': 'Pizza Chicken',
            'available_in_pos': True,
            'type': 'product',
            'lst_price': 10.0,
        })

        self.component_a = self.env['product.product'].create({
            'name': 'Chicken',
            'type': 'product',
            'available_in_pos': True,
            'uom_id': self.env.ref('uom.product_uom_gram').id,
            'uom_po_id': self.env.ref('uom.product_uom_gram').id,
            'lst_price': 10.0,
        })
        self.location = self.env['stock.location'].create({
            'name': 'Test location',
            'usage': 'internal',
        })

        self.env['stock.quant']._update_available_quantity(self.component_a, self.location, 100000)

        bom_product_form = Form(self.env['mrp.bom'])
        bom_product_form.product_id = self.kit
        bom_product_form.product_tmpl_id = self.kit.product_tmpl_id
        bom_product_form.product_qty = 1.0
        bom_product_form.type = 'phantom'
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.component_a
            bom_line.product_qty = 300.0
        self.bom_a = bom_product_form.save()

        sale_order = self.env['sale.order'].create({
            'partner_id': self.env.ref('base.res_partner_2').id,
            'order_line': [(0, 0, {
                'product_id': self.kit.id,
                'name': self.kit.name,
                'product_uom_qty': 10,
                'product_uom': self.kit.uom_id.id,
                'price_unit': self.kit.lst_price,
            })],
        })
        sale_order.action_confirm()
        picking = sale_order.picking_ids
        picking.move_ids.quantity_done = 300
        action = picking.button_validate()
        wizard = Form(self.env[action['res_model']].with_context(action['context']))
        wizard.save().process()

        self.assertEqual(sale_order.order_line.qty_delivered, 1)

        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PosSettleOrder', login="accountman")

        #assert that sales order qty are correctly updated
        self.assertEqual(sale_order.order_line.qty_delivered, 3)
        self.assertEqual(sale_order.picking_ids[0].move_ids.product_qty, 2100) # 7 left to deliver => 300 * 7 = 2100
        self.assertEqual(sale_order.picking_ids[0].move_ids.quantity_done, 0)
        self.assertEqual(sale_order.picking_ids[1].move_ids.product_qty, 300)
        self.assertEqual(sale_order.picking_ids[1].move_ids.quantity_done, 300) # 1 delivered => 300 * 2 = 600
