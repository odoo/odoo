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
        picking_receipt._action_done()

        mo = picking_receipt._get_subcontracted_productions()
        # Finished is made of 1 comp1 and 1 comp2.
        # Cost of comp1 = 10
        # Cost of comp2 = 20
        # --> Cost of finished = 10 + 20 = 30
        # Additionnal cost = 30 (from the purchase order line or directly set on the stock move here)
        # Total cost of subcontracting 1 unit of finished = 30 + 30 = 60
        self.assertEqual(mo.move_finished_ids.stock_valuation_layer_ids.value, 60)
        self.assertEqual(picking_receipt.move_lines.stock_valuation_layer_ids.value, 0)
        self.assertEqual(picking_receipt.move_lines.product_id.value_svl, 60)

        # Do the same without any additionnal cost
        picking_receipt = picking_receipt.copy()
        picking_receipt.move_lines.price_unit = 0

        picking_receipt.action_confirm()
        picking_receipt.move_lines.quantity_done = 1.0
        picking_receipt._action_done()

        mo = picking_receipt._get_subcontracted_productions()
        # In this case, since there isn't any additionnal cost, the total cost of the subcontracting
        # is the sum of the components' costs: 10 + 20 = 30
        self.assertEqual(mo.move_finished_ids.stock_valuation_layer_ids.value, 30)
        self.assertEqual(picking_receipt.move_lines.product_id.value_svl, 90)

    def test_subcontracting_account_backorder(self):
        """ This test uses tracked (serial and lot) component and tracked (serial) finished product
        The original subcontracting production order will be split into 4 backorders. This test
        ensure the extra cost asked from the subcontractor is added correctly on all the finished
        product valuation layer. Not only the first one. """
        todo_nb = 4
        self.comp2.tracking = 'lot'
        self.comp1.tracking = 'serial'
        self.comp2.standard_price = 100
        self.finished.tracking = 'serial'
        self.env.ref('product.product_category_all').property_cost_method = 'fifo'

        # Create a receipt picking from the subcontractor
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = self.subcontractor_partner1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.finished
            move.product_uom_qty = todo_nb
        picking_receipt = picking_form.save()
        # Mimic the extra cost on the po line
        picking_receipt.move_lines.price_unit = 50
        picking_receipt.action_confirm()

        # We should be able to call the 'record_components' button
        self.assertTrue(picking_receipt.display_action_record_components)

        # Check the created manufacturing order
        mo = self.env['mrp.production'].search([('bom_id', '=', self.bom.id)])
        wh = picking_receipt.picking_type_id.warehouse_id

        lot_comp2 = self.env['stock.production.lot'].create({
            'name': 'lot_comp2',
            'product_id': self.comp2.id,
            'company_id': self.env.company.id,
        })
        serials_finished = []
        serials_comp1 = []
        for i in range(todo_nb):
            serials_finished.append(self.env['stock.production.lot'].create({
                'name': 'serial_fin_%s' % i,
                'product_id': self.finished.id,
                'company_id': self.env.company.id,
            }))
            serials_comp1.append(self.env['stock.production.lot'].create({
                'name': 'serials_comp1_%s' % i,
                'product_id': self.comp1.id,
                'company_id': self.env.company.id,
            }))

        for i in range(todo_nb):
            action = picking_receipt.action_record_components()
            mo = self.env['mrp.production'].browse(action['res_id'])
            mo_form = Form(mo.with_context(**action['context']), view=action['view_id'])
            mo_form.lot_producing_id = serials_finished[i]
            with mo_form.move_line_raw_ids.edit(0) as ml:
                self.assertEqual(ml.product_id, self.comp1)
                ml.lot_id = serials_comp1[i]
            with mo_form.move_line_raw_ids.edit(1) as ml:
                self.assertEqual(ml.product_id, self.comp2)
                ml.lot_id = lot_comp2
            mo = mo_form.save()
            mo.subcontracting_record_component()

        # We should not be able to call the 'record_components' button

        picking_receipt.button_validate()

        f_layers = self.finished.stock_valuation_layer_ids
        self.assertEqual(len(f_layers), 4)
        for layer in f_layers:
            self.assertEqual(layer.value, 100 + 50)
