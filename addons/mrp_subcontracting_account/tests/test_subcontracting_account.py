# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mrp_subcontracting.tests.common import TestMrpSubcontractingCommon
from odoo.tests.common import Form

class TestAccountSubcontractingFlows(TestMrpSubcontractingCommon):
    def test_subcontracting_account_flow_1(self):
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.customer_location = self.env.ref('stock.stock_location_customers')
        self.supplier_location = self.env.ref('stock.stock_location_suppliers')
        self.uom_unit = self.env.ref('uom.product_uom_unit')
        self.env.ref('product.product_category_all').property_cost_method = 'fifo'

        # IN 10@10 comp1 10@20 comp2
        move1 = self.env['stock.move'].create({
            'name': 'IN 10 units @ 10.00 per unit',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.env.company.subcontracting_location_id.id,
            'product_id': self.comp1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 10.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 10.0
        move1._action_done()
        move2 = self.env['stock.move'].create({
            'name': 'IN 10 units @ 20.00 per unit',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.env.company.subcontracting_location_id.id,
            'product_id': self.comp2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 20.0,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.qty_done = 10.0
        move2._action_done()

        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = self.subcontractor_partner1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.finished
            move.product_uom_qty = 1
        picking_receipt = picking_form.save()
        picking_receipt.move_lines.price_unit = 30.0

        picking_receipt.action_confirm()
        picking_receipt.move_lines.quantity_done = 1.0
        picking_receipt.action_done()

        mo = picking_receipt._get_subcontracted_productions()
        self.assertEqual(mo.move_finished_ids.stock_valuation_layer_ids.value, 60)
        self.assertEqual(mo.move_finished_ids.product_id.value_svl, 60)
