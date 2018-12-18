# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from odoo.addons.stock.tests.common import TestStockCommon


class TestSplitMove(TestStockCommon):

    def test_mo_split_moves(self):
        """ Manufacturing Order of Semifinished product:

        - Create a MO for 10 units of a finished product -> Product A.
        - It creates an MO for 10 units of a semi finished product -> Product B.
        - Decrease quantity to produce from 10 to 5 on the semi finished product (Product B).
        - On the MO for the finished products (Product A), for the component "semi finished product (Product B)",
          split into two moves, one of 5 in MTO and one of 5 in MTS.

        This test ensure that when quantity to produce is decreased in semi finished product,
        the quantity to produce in destination move should be splitted into two -> one in MTO and one in MTS.
        """
        warehouse = self.env.ref('stock.warehouse0')
        mrp_bom = self.env['mrp.bom']
        mrp_production = self.env['mrp.production']
        route_manufacture = warehouse.manufacture_pull_id.route_id.id
        route_mto = warehouse.mto_pull_id.route_id.id

        # Create finished product - Product A with route - Manufacture
        finished_product = self.ProductObj.create({
            'name': 'Product A',
            'type': 'product',
            'route_ids': [(6, 0, [route_manufacture])]
        })
        # Create semi finished product - Product B with route - Manufacture and MTO
        semifinished_product = self.ProductObj.create({
            'name': 'Product B',
            'type': 'product',
            'route_ids': [(6, 0, [route_manufacture, route_mto])]
        })
        # Create raw material for semi finished product
        raw_material = self.ProductObj.create({
            'name': 'Product C',
            'type': 'product',
        })
        # Create BOM for Product A having raw material as Product B
        bom_1 = mrp_bom.create({
            'product_id': finished_product.id,
            'product_tmpl_id': finished_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': semifinished_product.id, 'product_qty': 1})
            ]})
        # Create BOM for Product B
        mrp_bom.create({
            'product_id': semifinished_product.id,
            'product_tmpl_id': semifinished_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': raw_material.id, 'product_qty': 1})
            ]})
        # Create MO of Product A with Quantity = 10
        mo_form = Form(mrp_production)
        mo_form.product_id = finished_product
        mo_form.bom_id = bom_1
        mo_form.product_qty = 10
        mo = mo_form.save()
        mo.action_confirm()

        self.assertEqual(len(mo.move_raw_ids), 1, "Consume material lines are not generated properly.")
        self.assertEqual(mo.state, 'confirmed', "Production order should be in confirmed state.")

        # find MO for semifinished product
        mnf_product_b = mrp_production.search([('product_id', '=', semifinished_product.id)])

        self.assertTrue(mnf_product_b, 'Manufacturing order not created.')
        self.assertEqual(mnf_product_b.product_qty, 10, 'Wrong product quantity in manufacturing order.')

        # ----------------------------------------------------------------------
        # Decrease the Quantity to produce
        # ----------------------------------------------------------------------
        #   Product B ( 10 Unit ) --> Product B ( 5 Unit )
        # ----------------------------------------------------------------------

        qty_wizard = self.env['change.production.qty'].create({
            'mo_id': mnf_product_b.id,
            'product_qty': 5.0,
        })
        qty_wizard.change_prod_qty()

        self.assertEqual(mnf_product_b.product_qty, 5, 'Wrong product quantity in manufacturing order.')
        self.assertEqual(mnf_product_b.state, 'confirmed', "Production order should be in confirmed state.")

        self.assertEqual(len(mnf_product_b.move_raw_ids), 1, "Consume material lines are not generated properly.")
        move = self.MoveObj.search([('raw_material_production_id', '=', mnf_product_b.id), ('product_id', '=', raw_material.id)])

        # Create stock
        inventory = self.InvObj.create({
            'name': 'Inventory For Product C',
            'line_ids': [(0, 0, {
                'product_id': raw_material.id,
                'product_uom_id': raw_material.uom_id.id,
                'product_qty': 5.0,
                'location_id': warehouse.lot_stock_id.id
            })]
        })
        inventory.action_start()
        inventory.action_validate()
        # assign consume material
        mnf_product_b.action_assign()
        self.assertEqual(mnf_product_b.reservation_state, 'assigned', "Production order should be in assigned state.")
        self.assertEqual(move.state, 'assigned', "Wrong state in move line.")

        # produce semi finished product
        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mnf_product_b.id,
            'active_ids': [mnf_product_b.id],
        }))
        produce_wizard = produce_form.save()
        produce_wizard.do_produce()

        mnf_product_b.button_mark_done()
        self.assertEqual(mnf_product_b.state, 'done', "Production order should be in done state.")

        # ======================================================================
        # Before splitting move:
        # ----------------------
        #   Product A ( 10 Unit ) - MTO
        #
        # After splitting move:
        # ---------------------
        #   Product A (  5 unit ) - MTO
        #   ---------------------------
        #   Product A (  5 unit ) - MTS
        # ======================================================================

        # Check that new line of MTS is created for remaining product in MO of finished product and it should be MTS.
        self.assertEqual(len(mo.move_raw_ids), 2, "New move line of MTS must be created.")
        self.assertEqual(sum(qty for qty in mo.move_raw_ids.mapped('product_uom_qty')), 10, "wrong quantity in move lines.")
        self.assertEqual(mo.move_raw_ids[1].procure_method, 'make_to_stock', "New move line must be - Make to Stock.")
