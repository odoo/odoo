# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestWorkOrderProcess(common.TransactionCase):

    def setUp(self):
        super(TestWorkOrderProcess, self).setUp()
        self.source_location_id = self.ref('stock.stock_location_14')
        self.warehouse = self.env.ref('stock.warehouse0')

    def test_00_workorder_process(self):
        """ Testing consume quants and produced quants with workorder """
        dining_table = self.env.ref("mrp.product_product_computer_desk")
        product_table_sheet = self.env.ref('mrp.product_product_computer_desk_head')
        product_table_leg = self.env.ref('mrp.product_product_computer_desk_leg')
        product_bolt = self.env.ref('mrp.product_product_computer_desk_bolt')

        production_table = self.env['mrp.production'].create({
            'product_id': dining_table.id,
            'product_qty': 1.0,
            'product_uom_id': dining_table.uom_id.id,
            'bom_id': self.ref("mrp.mrp_bom_desk")
        })

        # Set tracking lot on finish and consume products.
        dining_table.tracking = 'lot'
        product_table_sheet.tracking = 'lot'
        product_table_leg.tracking = 'lot'
        product_bolt.tracking = "lot"

        # Initial inventory of product sheet, lags and bolt
        lot_sheet = self.env['stock.production.lot'].create({'product_id': product_table_sheet.id})
        lot_leg = self.env['stock.production.lot'].create({'product_id': product_table_leg.id})
        lot_bolt = self.env['stock.production.lot'].create({'product_id': product_bolt.id})

        # Initialize inventory
        # --------------------
        inventory = self.env['stock.inventory'].create({
            'name': 'Inventory Product Table',
            'filter': 'partial',
            'line_ids': [(0, 0, {
                'product_id': product_table_sheet.id,
                'product_uom_id': product_table_sheet.uom_id.id,
                'product_qty': 20,
                'prod_lot_id': lot_sheet.id,
                'location_id': self.source_location_id
            }), (0, 0, {
                'product_id': product_table_leg.id,
                'product_uom_id': product_table_leg.uom_id.id,
                'product_qty': 20,
                'prod_lot_id': lot_leg.id,
                'location_id': self.source_location_id
            }), (0, 0, {
                'product_id': product_bolt.id,
                'product_uom_id': product_bolt.uom_id.id,
                'product_qty': 20,
                'prod_lot_id': lot_bolt.id,
                'location_id': self.source_location_id
            })]
        })
        inventory.action_done()

        # Create work order
        production_table.button_plan()
        # Check Work order created or not
        self.assertEqual(len(production_table.workorder_ids), 3)

        # ---------------------------------------------------------
        # Process all workorder and check it state.
        # ----------------------------------------------------------

        workorders = production_table.workorder_ids
        self.assertEqual(workorders[0].state, 'ready', "First workorder state should be ready.")
        self.assertEqual(workorders[1].state, 'pending')
        self.assertEqual(workorders[2].state, 'pending')

        # --------------------------------------------------------------
        # Process cutting operation...
        # ---------------------------------------------------------

        finished_lot =self.env['stock.production.lot'].create({'product_id': production_table.product_id.id})
        workorders[0].write({'final_lot_id': finished_lot.id})
        workorders[0].button_start()
        workorders[0].active_move_lot_ids[0].write({'lot_id': lot_sheet.id, 'quantity_done': 1})
        self.assertEqual(workorders[0].state, 'progress')
        workorders[0].record_production()
        self.assertEqual(workorders[0].state, 'done')
        move_table_sheet = production_table.move_raw_ids.filtered(lambda x : x.product_id == product_table_sheet)
        self.assertEqual(move_table_sheet.quantity_done, 1)

        # --------------------------------------------------------------
        # Process drilling operation ...
        # ---------------------------------------------------------

        workorders[1].button_start()
        workorders[1].active_move_lot_ids[0].write({'lot_id': lot_leg.id, 'quantity_done': 4})
        workorders[1].record_production()
        move_leg = production_table.move_raw_ids.filtered(lambda x : x.product_id == product_table_leg)
        self.assertEqual(workorders[1].state, 'done')
        self.assertEqual(move_leg.quantity_done, 4)

        # --------------------------------------------------------------
        # Process fitting operation ...
        # ---------------------------------------------------------

        finish_move = production_table.move_finished_ids.filtered(lambda x : x.product_id.id == dining_table.id)

        workorders[2].button_start()
        move_lot = workorders[2].active_move_lot_ids[0]
        move_lot.write({'lot_id': lot_bolt.id, 'quantity_done': 4})
        move_table_bolt = production_table.move_raw_ids.filtered(lambda x : x.product_id.id == product_bolt.id)
        workorders[2].record_production()
        self.assertEqual(workorders[2].state, 'done')
        self.assertEqual(move_table_bolt.quantity_done, 4)

        # -----------------------------------------
        # Post inventory of manufacturing order
        # -----------------------------------------

        # This behaviour was changed
        #self.assertEqual(production_table.state, 'done', "Production order should be in done state.")

        # ----------------------------------------
        # Check consume quants and produce quants.
        # ----------------------------------------
        self.assertEqual(sum(move_table_sheet.quant_ids.mapped('qty')), 1, "Wrong quantity of consumed product %s" % move_table_sheet.product_id.name)
        self.assertEqual(sum(move_leg.quant_ids.mapped('qty')), 4, "Wrong quantity of consumed product %s" % move_leg.product_id.name)
        self.assertEqual(sum(move_table_bolt.quant_ids.mapped('qty')), 4, "Wrong quantity of consumed product %s" % move_table_bolt.product_id.name)

        consume_quants = move_table_sheet.quant_ids + move_leg.quant_ids + move_table_bolt.quant_ids

        # Check for produced quant correctly linked with consumed quants or not.

        finish_move = production_table.move_finished_ids.filtered(lambda x: x.product_id.id == dining_table.id)
        finished_quant = finish_move.quant_ids[0]
        for quant in consume_quants:
            self.assertEqual(len(quant.produced_quant_ids), 1)
            self.assertEqual(quant.produced_quant_ids[0].lot_id.id, finished_lot.id)
            self.assertEqual(quant.produced_quant_ids[0].id, finished_quant.id)

        # ------------------------------------------
        # Check finished quants with consumed quant.
        # ------------------------------------------

        self.assertEqual(finished_quant.consumed_quant_ids, consume_quants)

    def test_01_without_workorder(self):
        """ Testing consume quants and produced quants without workorder """
        unit = self.ref("product.product_uom_unit")
        custom_laptop = self.env.ref("product.product_product_27")
        custom_laptop.tracking = 'lot'

        # Create new product charger and keybord
        # --------------------------------------
        product_charger = self.env['product.product'].create({
            'name': 'Charger',
            'type': 'product',
            'tracking': 'lot',
            'uom_id': unit,
            'uom_po_id': unit})
        product_keybord = self.env['product.product'].create({
            'name': 'Usb Keybord',
            'type': 'product',
            'tracking': 'lot',
            'uom_id': unit,
            'uom_po_id': unit})

        # Create bill of material for customized laptop.

        bom_custom_laptop = self.env['mrp.bom'].create({
            'product_tmpl_id': custom_laptop.product_tmpl_id.id,
            'product_qty': 10,
            'product_uom_id': unit,
            'bom_line_ids': [(0, 0, {
                'product_id': product_charger.id,
                'product_qty': 20,
                'product_uom_id': unit
            }), (0, 0, {
                'product_id': product_keybord.id,
                'product_qty': 20,
                'product_uom_id': unit
            })]
        })

        # Create production order for customize laptop.

        mo_custom_laptop = self.env['mrp.production'].create({
            'product_id': custom_laptop.id,
            'product_qty': 10,
            'product_uom_id': unit,
            'bom_id': bom_custom_laptop.id})

        # Assign component to production order.
        mo_custom_laptop.action_assign()

        # Check production order status of availablity

        self.assertEqual(mo_custom_laptop.availability, 'waiting')

        # --------------------------------------------------
        # Set inventory for rawmaterial charger and keybord
        # --------------------------------------------------

        lot_charger = self.env['stock.production.lot'].create({'product_id': product_charger.id})
        lot_keybord = self.env['stock.production.lot'].create({'product_id': product_keybord.id})

        # Initialize Inventory
        # --------------------
        inventory = self.env['stock.inventory'].create({
            'name': 'Inventory Product Table',
            'filter': 'partial',
            'line_ids': [(0, 0, {
                'product_id': product_charger.id,
                'product_uom_id': product_charger.uom_id.id,
                'product_qty': 20,
                'prod_lot_id': lot_charger.id,
                'location_id': self.source_location_id
            }), (0, 0, {
                'product_id': product_keybord.id,
                'product_uom_id': product_keybord.uom_id.id,
                'product_qty': 20,
                'prod_lot_id': lot_keybord.id,
                'location_id': self.source_location_id
            })]
        })
        # inventory.prepare_inventory()
        inventory.action_done()

        # Check consumed move status
        mo_custom_laptop.action_assign()
        self.assertEqual( mo_custom_laptop.availability, 'assigned')

        # Check current status of raw materials.
        for move in mo_custom_laptop.move_raw_ids:
            self.assertEqual(move.product_uom_qty, 20, "Wrong consume quantity of raw material %s: %s instead of %s" % (move.product_id.name, move.product_uom_qty, 20))
            self.assertEqual(move.quantity_done, 0, "Wrong produced quantity on raw material %s: %s instead of %s" % (move.product_id.name, move.quantity_done, 0))

        # -----------------
        # Start production
        # -----------------

        # Produce 6 Unit of custom laptop will consume ( 12 Unit of keybord and 12 Unit of charger)

        context = {"active_ids": [mo_custom_laptop.id], "active_id": mo_custom_laptop.id}
        product_consume = self.env['mrp.product.produce'].with_context(context).create({'product_qty': 6.00})
        laptop_lot_001 = self.env['stock.production.lot'].create({'product_id': custom_laptop.id})
        product_consume.lot_id = laptop_lot_001.id
        product_consume.consume_line_ids.write({'quantity_done': 12})
        product_consume.do_produce()

        # Check consumed move after produce 6 quantity of customized laptop.
        for move in mo_custom_laptop.move_raw_ids:
            self.assertEqual(move.quantity_done, 12, "Wrong produced quantity on raw material %s" % (move.product_id.name))
        self.assertEqual(len(mo_custom_laptop.move_raw_ids), 2)
        mo_custom_laptop.post_inventory()
        self.assertEqual(len(mo_custom_laptop.move_raw_ids), 4)

        # Check done move and confirmed move quantity.

        charger_done_move = mo_custom_laptop.move_raw_ids.filtered(lambda x: x.product_id.id == product_charger.id and x.state == 'done')
        keybord_done_move = mo_custom_laptop.move_raw_ids.filtered(lambda x: x.product_id.id == product_keybord.id and x.state == 'done')
        self.assertEquals(charger_done_move.product_uom_qty, 12)
        self.assertEquals(keybord_done_move.product_uom_qty, 12)

        # Produce remaining 4 quantity
        # ----------------------------

        # Produce 4 Unit of custom laptop will consume ( 8 Unit of keybord and 8 Unit of charger).
        context = {"active_ids": [mo_custom_laptop.id], "active_id": mo_custom_laptop.id}
        product_consume = self.env['mrp.product.produce'].with_context(context).create({'product_qty': 4.00})
        laptop_lot_002 = self.env['stock.production.lot'].create({'product_id': custom_laptop.id})
        product_consume.lot_id = laptop_lot_002.id
        self.assertEquals(len(product_consume.consume_line_ids), 2)
        product_consume.consume_line_ids.write({'quantity_done': 8})
        product_consume.do_produce()
        charger_move = mo_custom_laptop.move_raw_ids.filtered(lambda x: x.product_id.id == product_charger.id and x.state != 'done')
        keybord_move = mo_custom_laptop.move_raw_ids.filtered(lambda x: x.product_id.id == product_keybord.id and x.state !='done')
        self.assertEquals(charger_move.quantity_done, 8, "Wrong consumed quantity of %s" % charger_move.product_id.name)
        self.assertEquals(keybord_move.quantity_done, 8, "Wrong consumed quantity of %s" % keybord_move.product_id.name)

        # Post Inventory of production order.
        mo_custom_laptop.post_inventory()

        raw_moves_state = any(move.state != 'done' for move in mo_custom_laptop.move_raw_ids)
        finsh_moves_state = any(move.state != 'done' for move in mo_custom_laptop.move_finished_ids)
        self.assertFalse(raw_moves_state, "Wrong state in consumed moves of production order.")
        self.assertFalse(finsh_moves_state, "Wrong state in consumed moves of production order.")

        # Finished move quants of production order

        finshed_quant_lot_001 = mo_custom_laptop.move_finished_ids.filtered(lambda x: x.product_id.id == custom_laptop.id and x.product_uom_qty==6).mapped('quant_ids')
        finshed_quant_lot_002 = mo_custom_laptop.move_finished_ids.filtered(lambda x: x.product_id.id == custom_laptop.id and x.product_uom_qty==4).mapped('quant_ids')

        # --------------------------------
        # Check consume and produce quants
        # --------------------------------

        # Check consumed quants of lot1
        for consume_quant in finshed_quant_lot_001[0].consumed_quant_ids:
            self.assertEqual(consume_quant.qty, 12)
            self.assertEqual(consume_quant.produced_quant_ids[0].lot_id.id, finshed_quant_lot_001[0].lot_id.id)
            self.assertEqual(consume_quant.produced_quant_ids[0].id, finshed_quant_lot_001[0].id)

        self.assertEqual(len(finshed_quant_lot_001[0].consumed_quant_ids), 2, "Wrong consumed quant linked with produced quant for lot %s " % laptop_lot_001.name)


        # Check total no of quants linked with produced quants.
        self.assertEqual(len(finshed_quant_lot_002[0].consumed_quant_ids), 2, "Wrong consumed quant linked with produced quant for lot %s " % laptop_lot_002.name)

        # Check consumed quants of lot2
        for consume_quant in finshed_quant_lot_002[0].consumed_quant_ids:
            self.assertEqual(consume_quant.qty, 8)
            self.assertEqual(consume_quant.produced_quant_ids[0].lot_id.id, finshed_quant_lot_002[0].lot_id.id)
            self.assertEqual(consume_quant.produced_quant_ids[0].id, finshed_quant_lot_002[0].id)

        # Check total quantity consumed of charger, keybord
        # --------------------------------------------------
        charger_quants = mo_custom_laptop.move_raw_ids.filtered(lambda x: x.product_id.id == product_charger.id and x.state == 'done').mapped('quant_ids')
        keybord_moves = mo_custom_laptop.move_raw_ids.filtered(lambda x: x.product_id.id == product_keybord.id and x.state == 'done').mapped('quant_ids')
        self.assertEqual(sum(charger_quants.mapped('qty')), 20)
        self.assertEqual(sum(keybord_moves.mapped('qty')), 20)

    def test_02_different_uom_on_bomlines(self):
        """ Testing bill of material with diffrent unit of measure."""
        route_manufacture = self.warehouse.manufacture_pull_id.route_id.id
        route_mto = self.warehouse.mto_pull_id.route_id.id
        unit = self.ref("product.product_uom_unit")
        dozen = self.ref("product.product_uom_dozen")
        kg = self.ref("product.product_uom_kgm")
        gm = self.ref("product.product_uom_gram")
        # Create Product A, B, C
        product_A = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'tracking': 'lot',
            'uom_id': dozen,
            'uom_po_id': dozen,
            'route_ids': [(6, 0, [route_manufacture, route_mto])]})
        product_B = self.env['product.product'].create({
            'name': 'Product B',
            'type': 'product',
            'tracking': 'lot',
            'uom_id': dozen,
            'uom_po_id': dozen})
        product_C = self.env['product.product'].create({
            'name': 'Product C',
            'type': 'product',
            'tracking': 'lot',
            'uom_id': kg,
            'uom_po_id': kg})

        # Bill of materials
        # -----------------

        #===================================
        # Product A 1 Unit
        #     Product B 4 Unit
        #     Product C 600 gram
        # -----------------------------------

        bom_a = self.env['mrp.bom'].create({
            'product_tmpl_id': product_A.product_tmpl_id.id,
            'product_qty': 2,
            'product_uom_id': unit,
            'bom_line_ids': [(0, 0, {
                'product_id': product_B.id,
                'product_qty': 4,
                'product_uom_id': unit
            }), (0, 0, {
                'product_id': product_C.id,
                'product_qty': 600,
                'product_uom_id': gm
            })]
        })

        # Create production order with product A 10 Unit.
        # -----------------------------------------------

        mo_custom_product = self.env['mrp.production'].create({
            'product_id': product_A.id,
            'product_qty': 10,
            'product_uom_id': unit,
            'bom_id': bom_a.id})

        move_product_b = mo_custom_product.move_raw_ids.filtered(lambda x: x.product_id == product_B)
        move_product_c = mo_custom_product.move_raw_ids.filtered(lambda x: x.product_id == product_C)

        # Check move correctly created or not.
        self.assertEqual(move_product_b.product_uom_qty, 20)
        self.assertEqual(move_product_b.product_uom.id, unit)
        self.assertEqual(move_product_c.product_uom_qty, 3000)
        self.assertEqual(move_product_c.product_uom.id, gm)

        # Lot create for product B and product C
        # ---------------------------------------
        lot_a = self.env['stock.production.lot'].create({'product_id': product_A.id})
        lot_b = self.env['stock.production.lot'].create({'product_id': product_B.id})
        lot_c = self.env['stock.production.lot'].create({'product_id': product_C.id})

        # Inventory Update
        # ----------------
        inventory = self.env['stock.inventory'].create({
            'name': 'Inventory Product B and C',
            'filter': 'partial',
            'line_ids': [(0, 0, {
                'product_id': product_B.id,
                'product_uom_id': product_B.uom_id.id,
                'product_qty': 3,
                'prod_lot_id': lot_b.id,
                'location_id': self.source_location_id
            }), (0, 0, {
                'product_id': product_C.id,
                'product_uom_id': product_C.uom_id.id,
                'product_qty': 3,
                'prod_lot_id': lot_c.id,
                'location_id': self.source_location_id
            })]
        })
        # inventory.prepare_inventory()
        inventory.action_done()

        # Start Production ...
        # --------------------

        mo_custom_product.action_assign()
        context = {"active_ids": [mo_custom_product.id], "active_id": mo_custom_product.id}
        product_consume = self.env['mrp.product.produce'].with_context(context).create({'product_qty': 10})
        # laptop_lot_002 = self.env['stock.production.lot'].create({'product_id': custom_laptop.id})
        product_consume.lot_id = lot_a.id
        self.assertEquals(len(product_consume.consume_line_ids), 2)
        product_consume.consume_line_ids.filtered(lambda x : x.product_id == product_C).write({'quantity_done': 3000})
        product_consume.consume_line_ids.filtered(lambda x : x.product_id == product_B).write({'quantity_done': 20})
        product_consume.do_produce()
        mo_custom_product.post_inventory()

        # Check correct quant linked with move or not
        # -------------------------------------------
        self.assertEqual(len(move_product_b.quant_ids), 1)
        self.assertEqual(len(move_product_c.quant_ids), 1)
        self.assertEqual(move_product_b.quant_ids.qty, move_product_b.product_qty)
        self.assertEqual(move_product_c.quant_ids.qty, 3)
        self.assertEqual(move_product_c.quant_ids.product_uom_id.id, kg)
