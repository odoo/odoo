# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from odoo.tests import Form
from odoo.tests.common import SavepointCase
from odoo.addons.mrp.tests.common import TestMrpCommon
from odoo.exceptions import ValidationError, UserError


class TestWorkOrderProcess(TestMrpCommon):
    def full_availability(self):
        """set full availability for all calendars"""
        calendar = self.env['resource.calendar'].search([])
        calendar.write({'attendance_ids': [(5, 0, 0)]})
        calendar.write({'attendance_ids': [
            (0, 0, {'name': 'Monday', 'dayofweek': '0', 'hour_from': 0, 'hour_to': 24, 'day_period': 'morning'}),
            (0, 0, {'name': 'Tuesday', 'dayofweek': '1', 'hour_from': 0, 'hour_to': 24, 'day_period': 'morning'}),
            (0, 0, {'name': 'Wednesday', 'dayofweek': '2', 'hour_from': 0, 'hour_to': 24, 'day_period': 'morning'}),
            (0, 0, {'name': 'Thursday', 'dayofweek': '3', 'hour_from': 0, 'hour_to': 24, 'day_period': 'morning'}),
            (0, 0, {'name': 'Friday', 'dayofweek': '4', 'hour_from': 0, 'hour_to': 24, 'day_period': 'morning'}),
            (0, 0, {'name': 'Saturday', 'dayofweek': '5', 'hour_from': 0, 'hour_to': 24, 'day_period': 'morning'}),
            (0, 0, {'name': 'Sunday', 'dayofweek': '6', 'hour_from': 0, 'hour_to': 24, 'day_period': 'morning'}),
        ]})

    @classmethod
    def setUpClass(cls):
        super(TestWorkOrderProcess, cls).setUpClass()
        cls.source_location_id = cls.env.ref('stock.stock_location_14').id
        cls.warehouse = cls.env.ref('stock.warehouse0')
        # setting up alternative workcenters
        cls.wc_alt_1 = cls.env['mrp.workcenter'].create({
            'name': 'Nuclear Workcenter bis',
            'capacity': 3,
            'time_start': 9,
            'time_stop': 5,
            'time_efficiency': 80,
        })
        cls.wc_alt_2 = cls.env['mrp.workcenter'].create({
            'name': 'Nuclear Workcenter ter',
            'capacity': 1,
            'time_start': 10,
            'time_stop': 5,
            'time_efficiency': 85,
        })
        cls.product_4.uom_id = cls.uom_unit
        cls.planning_bom = cls.env['mrp.bom'].create({
            'product_id': cls.product_4.id,
            'product_tmpl_id': cls.product_4.product_tmpl_id.id,
            'product_uom_id': cls.uom_unit.id,
            'product_qty': 4.0,
            'routing_id': cls.routing_1.id,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': cls.product_2.id, 'product_qty': 2}),
                (0, 0, {'product_id': cls.product_1.id, 'product_qty': 4})
            ]})

    def test_00_workorder_process(self):
        """ Testing consume quants and produced quants with workorder """

        dining_table = self.env.ref("mrp.product_product_computer_desk")
        product_table_sheet = self.env.ref('mrp.product_product_computer_desk_head')
        product_table_leg = self.env.ref('mrp.product_product_computer_desk_leg')
        product_bolt = self.env.ref('mrp.product_product_computer_desk_bolt')
        product_screw = self.env.ref('mrp.product_product_computer_desk_screw')
        self.env['stock.move'].search([('product_id', 'in', [product_bolt.id, product_screw.id])])._do_unreserve()
        (product_bolt + product_screw).write({'type': 'product'})

        self.env.ref("mrp.mrp_bom_desk").consumption = 'flexible'
        production_table_form = Form(self.env['mrp.production'])
        production_table_form.product_id = dining_table
        production_table_form.bom_id = self.env.ref("mrp.mrp_bom_desk")
        production_table_form.product_qty = 1.0
        production_table_form.product_uom_id = dining_table.uom_id
        production_table = production_table_form.save()
        production_table.action_confirm()

        # Set tracking lot on finish and consume products.
        dining_table.tracking = 'lot'
        product_table_sheet.tracking = 'lot'
        product_table_leg.tracking = 'lot'
        product_bolt.tracking = "lot"

        # Initial inventory of product sheet, lags and bolt
        lot_sheet = self.env['stock.production.lot'].create({'product_id': product_table_sheet.id, 'company_id': self.env.company.id})
        lot_leg = self.env['stock.production.lot'].create({'product_id': product_table_leg.id, 'company_id': self.env.company.id})
        lot_bolt = self.env['stock.production.lot'].create({'product_id': product_bolt.id, 'company_id': self.env.company.id})

        # Initialize inventory
        # --------------------
        inventory = self.env['stock.inventory'].create({
            'name': 'Inventory Product Table',
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
            }), (0, 0, {
                'product_id': product_screw.id,
                'product_uom_id': product_screw.uom_id.id,
                'product_qty': 20,
                'location_id': self.source_location_id
            })]
        })
        inventory.action_start()
        inventory.action_validate()

        # Create work order
        production_table.button_plan()
        # Check Work order created or not
        self.assertEqual(len(production_table.workorder_ids), 1)

        # ---------------------------------------------------------
        # Process all workorder and check it state.
        # ----------------------------------------------------------

        workorder = production_table.workorder_ids[0]
        self.assertEqual(workorder.state, 'ready', "workorder state should be ready.")

        # --------------------------------------------------------------
        # Process assembly line
        # ---------------------------------------------------------
        finished_lot =self.env['stock.production.lot'].create({'product_id': production_table.product_id.id, 'company_id': self.env.company.id})
        workorder.write({'finished_lot_id': finished_lot.id})
        workorder.button_start()
        for workorder_line_id in workorder._workorder_line_ids():
            if workorder_line_id.product_id.id == product_bolt.id:
                workorder_line_id.write({'lot_id': lot_bolt.id, 'qty_done': 1})
            if workorder_line_id.product_id.id == product_table_sheet.id:
                workorder_line_id.write({'lot_id': lot_sheet.id, 'qty_done': 1})
            if workorder_line_id.product_id.id == product_table_leg.id:
                workorder_line_id.write({'lot_id': lot_leg.id, 'qty_done': 1})
        self.assertEqual(workorder.state, 'progress')
        workorder.record_production()
        self.assertEqual(workorder.state, 'done')
        move_table_sheet = production_table.move_raw_ids.filtered(lambda x : x.product_id == product_table_sheet)
        self.assertEqual(move_table_sheet.quantity_done, 1)

        # ---------------------------------------------------------------
        # Check consume quants and produce quants after posting inventory
        # ---------------------------------------------------------------
        production_table.button_mark_done()

        self.assertEqual(product_screw.qty_available, 10)
        self.assertEqual(product_bolt.qty_available, 19)
        self.assertEqual(product_table_leg.qty_available, 19)
        self.assertEqual(product_table_sheet.qty_available, 19)

    def test_00b_workorder_process(self):
        """ Testing consume quants and produced quants with workorder """
        dining_table = self.env.ref("mrp.product_product_computer_desk")
        product_table_sheet = self.env.ref('mrp.product_product_computer_desk_head')
        product_table_leg = self.env.ref('mrp.product_product_computer_desk_leg')
        product_bolt = self.env.ref('mrp.product_product_computer_desk_bolt')
        self.env['stock.move'].search([('product_id', '=', product_bolt.id)])._do_unreserve()
        product_bolt.type = 'product'

        bom = self.env['mrp.bom'].browse(self.ref("mrp.mrp_bom_desk"))
        bom.routing_id = self.ref('mrp.mrp_routing_1')
        bom.consumption = 'flexible'

        bom.bom_line_ids.filtered(lambda p: p.product_id == product_table_sheet).operation_id = bom.routing_id.operation_ids[0]
        bom.bom_line_ids.filtered(lambda p: p.product_id == product_table_leg).operation_id = bom.routing_id.operation_ids[1]
        bom.bom_line_ids.filtered(lambda p: p.product_id == product_bolt).operation_id = bom.routing_id.operation_ids[2]

        production_table_form = Form(self.env['mrp.production'])
        production_table_form.product_id = dining_table
        production_table_form.bom_id = bom
        production_table_form.product_qty = 2.0
        production_table_form.product_uom_id = dining_table.uom_id
        production_table = production_table_form.save()
        # Set tracking lot on finish and consume products.
        dining_table.tracking = 'lot'
        product_table_sheet.tracking = 'lot'
        product_table_leg.tracking = 'lot'
        product_bolt.tracking = "lot"
        production_table.action_confirm()
        # Initial inventory of product sheet, lags and bolt
        lot_sheet = self.env['stock.production.lot'].create({'product_id': product_table_sheet.id, 'company_id': self.env.company.id})
        lot_leg = self.env['stock.production.lot'].create({'product_id': product_table_leg.id, 'company_id': self.env.company.id})
        lot_bolt = self.env['stock.production.lot'].create({'product_id': product_bolt.id, 'company_id': self.env.company.id})

        # Initialize inventory
        # --------------------
        inventory = self.env['stock.inventory'].create({
            'name': 'Inventory Product Table',
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
        inventory.action_start()
        inventory.action_validate()

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
        finished_lot = self.env['stock.production.lot'].create({'product_id': production_table.product_id.id, 'company_id': self.env.company.id})
        workorders[0].write({'finished_lot_id': finished_lot.id, 'qty_producing': 1.0})
        workorders[0].button_start()
        workorders[0]._workorder_line_ids()[0].write({'lot_id': lot_sheet.id, 'qty_done': 1})
        self.assertEqual(workorders[0].state, 'progress')
        workorders[0].record_production()

        move_table_sheet = production_table.move_raw_ids.filtered(lambda p: p.product_id == product_table_sheet)
        self.assertEqual(move_table_sheet.quantity_done, 1)

        # --------------------------------------------------------------
        # Process drilling operation ...
        # ---------------------------------------------------------
        workorders[1].button_start()
        workorders[1].qty_producing = 1.0
        workorders[1]._workorder_line_ids()[0].write({'lot_id': lot_leg.id, 'qty_done': 4})
        workorders[1].record_production()
        move_leg = production_table.move_raw_ids.filtered(lambda p: p.product_id == product_table_leg)
        #self.assertEqual(workorders[1].state, 'done')
        self.assertEqual(move_leg.quantity_done, 4)

        # --------------------------------------------------------------
        # Process fitting operation ...
        # ---------------------------------------------------------
        workorders[2].button_start()
        workorders[2].qty_producing = 1.0
        move_lot = workorders[2]._workorder_line_ids()[0]
        move_lot.write({'lot_id': lot_bolt.id, 'qty_done': 4})
        move_table_bolt = production_table.move_raw_ids.filtered(lambda p: p.product_id.id == product_bolt.id)
        workorders[2].record_production()
        self.assertEqual(move_table_bolt.quantity_done, 4)

        # Change the quantity of the production order to 1
        wiz = self.env['change.production.qty'].create({'mo_id': production_table.id ,
                                                        'product_qty': 1.0})
        wiz.change_prod_qty()
        # ---------------------------------------------------------------
        # Check consume quants and produce quants after posting inventory
        # ---------------------------------------------------------------
        production_table.post_inventory()
        self.assertEqual(sum(move_table_sheet.mapped('quantity_done')), 1, "Wrong quantity of consumed product %s" % move_table_sheet.product_id.name)
        self.assertEqual(sum(move_leg.mapped('quantity_done')), 4, "Wrong quantity of consumed product %s" % move_leg.product_id.name)
        self.assertEqual(sum(move_table_bolt.mapped('quantity_done')), 4, "Wrong quantity of consumed product %s" % move_table_bolt.product_id.name)

    def test_explode_from_order(self):
        # bom3 produces 2 Dozen of Doors (p6), aka 24
        # To produce 24 Units of Doors (p6)
        # - 2 Units of Tools (p5) -> need 4
        # - 8 Dozen of Sticks (p4) -> need 16
        # - 12 Units of Wood (p2) -> need 24
        # bom2 produces 1 Unit of Sticks (p4)
        # To produce 1 Unit of Sticks (p4)
        # - 2 Dozen of Sticks (p4) -> need 8
        # - 3 Dozen of Stones (p3) -> need 12

        # Update capacity, start time, stop time, and time efficiency.
        # ------------------------------------------------------------
        self.workcenter_1.write({'capacity': 1, 'time_start': 0, 'time_stop': 0, 'time_efficiency': 100})

        # Set manual time cycle 20 and 10.
        # --------------------------------
        self.operation_1.write({'time_cycle_manual': 20})
        (self.operation_2 | self.operation_3).write({'time_cycle_manual': 10})

        man_order_form = Form(self.env['mrp.production'])
        man_order_form.product_id = self.product_6
        man_order_form.bom_id = self.bom_3
        man_order_form.product_qty = 48
        man_order_form.product_uom_id = self.product_6.uom_id
        man_order = man_order_form.save()
        # reset quantities
        self.product_1.type = "product"
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product_1.id,
            'inventory_quantity': 0.0,
            'location_id': self.warehouse_1.lot_stock_id.id,
        })

        (self.product_2 | self.product_4).write({
            'tracking': 'none',
        })
        # assign consume material
        man_order.action_confirm()
        man_order.action_assign()
        self.assertEqual(man_order.reservation_state, 'confirmed', "Production order should be in waiting state.")

        # check consume materials of manufacturing order
        self.assertEqual(len(man_order.move_raw_ids), 4, "Consume material lines are not generated proper.")
        product_2_consume_moves = man_order.move_raw_ids.filtered(lambda x: x.product_id == self.product_2)
        product_3_consume_moves = man_order.move_raw_ids.filtered(lambda x: x.product_id == self.product_3)
        product_4_consume_moves = man_order.move_raw_ids.filtered(lambda x: x.product_id == self.product_4)
        product_5_consume_moves = man_order.move_raw_ids.filtered(lambda x: x.product_id == self.product_5)
        consume_qty_2 = product_2_consume_moves.product_uom_qty
        self.assertEqual(consume_qty_2, 24.0, "Consume material quantity of Wood should be 24 instead of %s" % str(consume_qty_2))
        consume_qty_3 = product_3_consume_moves.product_uom_qty
        self.assertEqual(consume_qty_3, 12.0, "Consume material quantity of Stone should be 12 instead of %s" % str(consume_qty_3))
        self.assertEqual(len(product_4_consume_moves), 2, "Consume move are not generated proper.")
        for consume_moves in product_4_consume_moves:
            consume_qty_4 = consume_moves.product_uom_qty
            self.assertIn(consume_qty_4, [8.0, 16.0], "Consume material quantity of Stick should be 8 or 16 instead of %s" % str(consume_qty_4))
        self.assertFalse(product_5_consume_moves, "Move should not create for phantom bom")

        # create required lots
        lot_product_2 = self.env['stock.production.lot'].create({'product_id': self.product_2.id, 'company_id': self.env.company.id})
        lot_product_4 = self.env['stock.production.lot'].create({'product_id': self.product_4.id, 'company_id': self.env.company.id})

        # refuel stock
        inventory = self.env['stock.inventory'].create({
            'name': 'Inventory For Product C',
            'line_ids': [(0, 0, {
                'product_id': self.product_2.id,
                'product_uom_id': self.product_2.uom_id.id,
                'product_qty': 30,
                'prod_lot_id': lot_product_2.id,
                'location_id': self.ref('stock.stock_location_14')
            }), (0, 0, {
                'product_id': self.product_3.id,
                'product_uom_id': self.product_3.uom_id.id,
                'product_qty': 60,
                'location_id': self.ref('stock.stock_location_14')
            }), (0, 0, {
                'product_id': self.product_4.id,
                'product_uom_id': self.product_4.uom_id.id,
                'product_qty': 60,
                'prod_lot_id': lot_product_4.id,
                'location_id': self.ref('stock.stock_location_14')
            })]
        })
        inventory.action_start()
        inventory.action_validate()

        # re-assign consume material
        man_order.action_assign()

        # Check production order status after assign.
        self.assertEqual(man_order.reservation_state, 'assigned', "Production order should be in assigned state.")
        # Plan production order.
        man_order.button_plan()

        # check workorders
        # - main bom: Door: 2 operations
        #   operation 1: Cutting
        #   operation 2: Welding, waiting for the previous one
        # - kit bom: Stone Tool: 1 operation
        #   operation 1: Gift Wrapping
        workorders = man_order.workorder_ids
        kit_wo = man_order.workorder_ids.filtered(lambda wo: wo.operation_id == self.operation_1)
        door_wo_1 = man_order.workorder_ids.filtered(lambda wo: wo.operation_id == self.operation_2)
        door_wo_2 = man_order.workorder_ids.filtered(lambda wo: wo.operation_id == self.operation_3)
        for workorder in workorders:
            self.assertEqual(workorder.workcenter_id, self.workcenter_1, "Workcenter does not match.")
        self.assertEqual(kit_wo.state, 'ready', "Workorder should be in ready state.")
        self.assertEqual(door_wo_1.state, 'ready', "Workorder should be in ready state.")
        self.assertEqual(door_wo_2.state, 'pending', "Workorder should be in pending state.")
        self.assertEqual(kit_wo.duration_expected, 960, "Workorder duration should be 960 instead of %s." % str(kit_wo.duration_expected))
        self.assertEqual(door_wo_1.duration_expected, 480, "Workorder duration should be 480 instead of %s." % str(door_wo_1.duration_expected))
        self.assertEqual(door_wo_2.duration_expected, 480, "Workorder duration should be 480 instead of %s." % str(door_wo_2.duration_expected))

        # subbom: kit for stone tools
        kit_wo.button_start()
        finished_lot = self.env['stock.production.lot'].create({'product_id': man_order.product_id.id, 'company_id': self.env.company.id})
        kit_wo.write({
            'finished_lot_id': finished_lot.id,
            'qty_producing': 48
        })

        kit_wo.record_production()

        self.assertEqual(kit_wo.state, 'done', "Workorder should be in done state.")

        # first operation of main bom
        finished_lot = self.env['stock.production.lot'].create({'product_id': man_order.product_id.id, 'company_id': self.env.company.id})
        door_wo_1.button_start()
        door_wo_1.write({
            'finished_lot_id': finished_lot.id,
            'qty_producing': 48
        })
        door_wo_1.record_production()
        self.assertEqual(door_wo_1.state, 'done', "Workorder should be in done state.")

        # second operation of main bom
        self.assertEqual(door_wo_2.state, 'ready', "Workorder should be in ready state.")
        door_wo_2.button_start()
        door_wo_2.record_production()
        self.assertEqual(door_wo_2.state, 'done', "Workorder should be in done state.")


    def test_01_without_workorder(self):
        """ Testing consume quants and produced quants without workorder """
        unit = self.ref("uom.product_uom_unit")
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

        mo_custom_laptop_form = Form(self.env['mrp.production'])
        mo_custom_laptop_form.product_id = custom_laptop
        mo_custom_laptop_form.bom_id = bom_custom_laptop
        mo_custom_laptop_form.product_qty = 10.0
        mo_custom_laptop_form.product_uom_id = self.env.ref("uom.product_uom_unit")
        mo_custom_laptop = mo_custom_laptop_form.save()

        mo_custom_laptop.action_confirm()
        # Assign component to production order.
        mo_custom_laptop.action_assign()

        # Check production order status of availablity

        self.assertEqual(mo_custom_laptop.reservation_state, 'confirmed')

        # --------------------------------------------------
        # Set inventory for rawmaterial charger and keybord
        # --------------------------------------------------

        lot_charger = self.env['stock.production.lot'].create({'product_id': product_charger.id, 'company_id': self.env.company.id})
        lot_keybord = self.env['stock.production.lot'].create({'product_id': product_keybord.id, 'company_id': self.env.company.id})

        # Initialize Inventory
        # --------------------
        inventory = self.env['stock.inventory'].create({
            'name': 'Inventory Product Table',
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
        inventory.action_start()
        inventory.action_validate()

        # Check consumed move status
        mo_custom_laptop.action_assign()
        self.assertEqual(mo_custom_laptop.reservation_state, 'assigned')

        # Check current status of raw materials.
        for move in mo_custom_laptop.move_raw_ids:
            self.assertEqual(move.product_uom_qty, 20, "Wrong consume quantity of raw material %s: %s instead of %s" % (move.product_id.name, move.product_uom_qty, 20))
            self.assertEqual(move.quantity_done, 0, "Wrong produced quantity on raw material %s: %s instead of %s" % (move.product_id.name, move.quantity_done, 0))

        # -----------------
        # Start production
        # -----------------

        # Produce 6 Unit of custom laptop will consume ( 12 Unit of keybord and 12 Unit of charger)
        context = {"active_ids": [mo_custom_laptop.id], "active_id": mo_custom_laptop.id}
        product_form = Form(self.env['mrp.product.produce'].with_context(context))
        product_form.qty_producing = 6.00
        laptop_lot_001 = self.env['stock.production.lot'].create({'product_id': custom_laptop.id , 'company_id': self.env.company.id})
        product_form.finished_lot_id = laptop_lot_001
        product_consume = product_form.save()
        product_consume._workorder_line_ids()[0].qty_done = 12
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
        produce_form = Form(self.env['mrp.product.produce'].with_context(context))
        produce_form.qty_producing = 4.00
        laptop_lot_002 = self.env['stock.production.lot'].create({'product_id': custom_laptop.id, 'company_id': self.env.company.id})
        produce_form.finished_lot_id = laptop_lot_002
        product_consume = produce_form.save()
        self.assertEquals(len(product_consume._workorder_line_ids()), 2)
        product_consume._workorder_line_ids()[0].qty_done = 8
        product_consume.do_produce()
        charger_move = mo_custom_laptop.move_raw_ids.filtered(lambda x: x.product_id.id == product_charger.id and x.state != 'done')
        keybord_move = mo_custom_laptop.move_raw_ids.filtered(lambda x: x.product_id.id == product_keybord.id and x.state !='done')
        self.assertEquals(charger_move.quantity_done, 8, "Wrong consumed quantity of %s" % charger_move.product_id.name)
        self.assertEquals(keybord_move.quantity_done, 8, "Wrong consumed quantity of %s" % keybord_move.product_id.name)

        # Post Inventory of production order.
        mo_custom_laptop.post_inventory()

#         raw_moves_state = any(move.state != 'done' for move in mo_custom_laptop.move_raw_ids)
#         finsh_moves_state = any(move.state != 'done' for move in mo_custom_laptop.move_finished_ids)
#         self.assertFalse(raw_moves_state, "Wrong state in consumed moves of production order.")
#         self.assertFalse(finsh_moves_state, "Wrong state in consumed moves of production order.")
#
#         # Finished move quants of production order
#
#         finshed_quant_lot_001 = mo_custom_laptop.move_finished_ids.filtered(lambda x: x.product_id.id == custom_laptop.id and x.product_uom_qty==6).mapped('quant_ids')
#         finshed_quant_lot_002 = mo_custom_laptop.move_finished_ids.filtered(lambda x: x.product_id.id == custom_laptop.id and x.product_uom_qty==4).mapped('quant_ids')
#
#         # Check total quantity consumed of charger, keybord
#         # --------------------------------------------------
#         charger_quants = mo_custom_laptop.move_raw_ids.filtered(lambda x: x.product_id.id == product_charger.id and x.state == 'done').mapped('quant_ids')
#         keybord_moves = mo_custom_laptop.move_raw_ids.filtered(lambda x: x.product_id.id == product_keybord.id and x.state == 'done').mapped('quant_ids')
#         self.assertEqual(sum(charger_quants.mapped('qty')), 20)
#         self.assertEqual(sum(keybord_moves.mapped('qty')), 20)

    def test_02_different_uom_on_bomlines(self):
        """ Testing bill of material with different unit of measure."""
        route_manufacture = self.warehouse.manufacture_pull_id.route_id.id
        route_mto = self.warehouse.mto_pull_id.route_id.id
        unit = self.ref("uom.product_uom_unit")
        dozen = self.ref("uom.product_uom_dozen")
        kg = self.ref("uom.product_uom_kgm")
        gm = self.ref("uom.product_uom_gram")
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

        mo_custom_product_form = Form(self.env['mrp.production'])
        mo_custom_product_form.product_id = product_A
        mo_custom_product_form.bom_id = bom_a
        mo_custom_product_form.product_qty = 10.0
        mo_custom_product_form.product_uom_id = self.env.ref("uom.product_uom_unit")
        mo_custom_product = mo_custom_product_form.save()

        move_product_b = mo_custom_product.move_raw_ids.filtered(lambda x: x.product_id == product_B)
        move_product_c = mo_custom_product.move_raw_ids.filtered(lambda x: x.product_id == product_C)

        # Check move correctly created or not.
        self.assertEqual(move_product_b.product_uom_qty, 20)
        self.assertEqual(move_product_b.product_uom.id, unit)
        self.assertEqual(move_product_c.product_uom_qty, 3000)
        self.assertEqual(move_product_c.product_uom.id, gm)

        # Lot create for product B and product C
        # ---------------------------------------
        lot_a = self.env['stock.production.lot'].create({'product_id': product_A.id, 'company_id': self.env.company.id})
        lot_b = self.env['stock.production.lot'].create({'product_id': product_B.id, 'company_id': self.env.company.id})
        lot_c = self.env['stock.production.lot'].create({'product_id': product_C.id, 'company_id': self.env.company.id})

        # Inventory Update
        # ----------------
        inventory = self.env['stock.inventory'].create({
            'name': 'Inventory Product B and C',
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
        inventory.action_start()
        inventory.action_validate()

        # Start Production ...
        # --------------------

        mo_custom_product.action_confirm()
        mo_custom_product.action_assign()
        context = {"active_ids": [mo_custom_product.id], "active_id": mo_custom_product.id}
        produce_form = Form(self.env['mrp.product.produce'].with_context(context))
        produce_form.qty_producing = 10.00
        produce_form.finished_lot_id = lot_a
        product_consume = produce_form.save()
        # laptop_lot_002 = self.env['stock.production.lot'].create({'product_id': custom_laptop.id})
        self.assertEquals(len(product_consume._workorder_line_ids()), 2)
        product_consume._workorder_line_ids().filtered(lambda x: x.product_id == product_C).write({'qty_done': 3000})
        product_consume._workorder_line_ids().filtered(lambda x: x.product_id == product_B).write({'qty_done': 20})
        product_consume.do_produce()
        mo_custom_product.post_inventory()

        # Check correct quant linked with move or not
        # -------------------------------------------
        #TODO: check original quants qtys diminished
#         self.assertEqual(len(move_product_b.quant_ids), 1)
#         self.assertEqual(len(move_product_c.quant_ids), 1)
#         self.assertEqual(move_product_b.quant_ids.qty, move_product_b.product_qty)
#         self.assertEqual(move_product_c.quant_ids.qty, 3)
#         self.assertEqual(move_product_c.quant_ids.product_uom_id.id, kg)

    def test_03_test_serial_number_defaults(self):
        """ Test that the correct serial number is suggested on consecutive work orders. """
        laptop = self.env.ref("product.product_product_25")
        graphics_card = self.env.ref("product.product_product_24")
        unit = self.env.ref("uom.product_uom_unit")
        three_step_routing = self.env.ref("mrp.mrp_routing_1")

        laptop.tracking = 'serial'

        bom_laptop = self.env['mrp.bom'].create({
            'product_tmpl_id': laptop.product_tmpl_id.id,
            'product_qty': 1,
            'product_uom_id': unit.id,
            'bom_line_ids': [(0, 0, {
                'product_id': graphics_card.id,
                'product_qty': 1,
                'product_uom_id': unit.id
            })],
            'routing_id': three_step_routing.id
        })

        mo_laptop_form = Form(self.env['mrp.production'])
        mo_laptop_form.product_id = laptop
        mo_laptop_form.bom_id = bom_laptop
        mo_laptop_form.product_qty = 3
        mo_laptop = mo_laptop_form.save()

        mo_laptop.action_confirm()
        mo_laptop.button_plan()
        workorders = mo_laptop.workorder_ids.sorted()
        self.assertEqual(len(workorders), 3)

        workorders[0].button_start()
        serial_a = self.env['stock.production.lot'].create({'product_id': laptop.id, 'company_id': self.env.company.id})
        workorders[0].finished_lot_id = serial_a
        workorders[0].record_production()
        serial_b = self.env['stock.production.lot'].create({'product_id': laptop.id, 'company_id': self.env.company.id})
        workorders[0].finished_lot_id = serial_b
        workorders[0].record_production()
        serial_c = self.env['stock.production.lot'].create({'product_id': laptop.id, 'company_id': self.env.company.id})
        workorders[0].finished_lot_id = serial_c
        workorders[0].record_production()
        self.assertEqual(workorders[0].state, 'done')

        for workorder in workorders - workorders[0]:
            workorder.button_start()
            self.assertEqual(workorder.finished_lot_id, serial_a)
            workorder.record_production()
            self.assertEqual(workorder.finished_lot_id, serial_b)
            workorder.record_production()
            self.assertEqual(workorder.finished_lot_id, serial_c)
            workorder.record_production()
            self.assertEqual(workorder.state, 'done')

    def test_03b_test_serial_number_defaults(self):
        """ Check the constraint on the workorder final_lot. The first workorder
        produces 2/2 units without serial number (serial is only required when
        you register a component) then the second workorder try to register a
        serial number. It should be allowed since the first workorder did not
        specify a seiral number.
        """
        bom = self.env.ref('mrp.mrp_bom_laptop_cust_rout')
        product = bom.product_tmpl_id.product_variant_id
        product.tracking = 'serial'

        lot_1 = self.env['stock.production.lot'].create({
            'product_id': product.id,
            'name': 'LOT000001',
            'company_id': self.env.company.id,
        })

        lot_2 = self.env['stock.production.lot'].create({
            'product_id': product.id,
            'name': 'LOT000002',
            'company_id': self.env.company.id,
        })
        self.env['stock.production.lot'].create({
            'product_id': product.id,
            'name': 'LOT000003',
            'company_id': self.env.company.id,
        })

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product
        mo_form.bom_id = bom
        mo_form.product_qty = 2.0
        mo = mo_form.save()

        mo.action_confirm()
        mo.button_plan()

        workorder_0 = mo.workorder_ids[0]
        workorder_0.button_start()
        workorder_0.record_production()
        workorder_0.record_production()

        workorder_1 = mo.workorder_ids[1]
        workorder_1.button_start()
        with Form(workorder_1) as wo:
            wo.finished_lot_id = lot_1
        workorder_1.record_production()

        self.assertTrue(len(workorder_1.allowed_lots_domain) > 1)
        with Form(workorder_1) as wo:
            wo.finished_lot_id = lot_2
        workorder_1.record_production()

        workorder_2 = mo.workorder_ids[2]
        self.assertEqual(workorder_2.allowed_lots_domain, lot_1 | lot_2)

        self.assertEqual(workorder_0.finished_workorder_line_ids.qty_done, 2)
        self.assertFalse(workorder_0.finished_workorder_line_ids.lot_id)
        self.assertEqual(sum(workorder_1.finished_workorder_line_ids.mapped('qty_done')), 2)
        self.assertEqual(workorder_1.finished_workorder_line_ids.mapped('lot_id'), lot_1 | lot_2)

    def test_04_test_planning_date(self):
        """ Test that workorder are planned at the correct time. """
        # The workcenter is working 24/7
        self.full_availability()

        dining_table = self.env.ref("mrp.product_product_computer_desk")

        production_table_form = Form(self.env['mrp.production'])
        production_table_form.product_id = dining_table
        production_table_form.bom_id = self.env.ref("mrp.mrp_bom_desk")
        production_table_form.product_qty = 1.0
        production_table_form.product_uom_id = dining_table.uom_id
        production_table = production_table_form.save()
        production_table.action_confirm()

        # Create work order
        production_table.button_plan()
        workorder = production_table.workorder_ids[0]

        # Check that the workorder is planned now and that it lasts one hour
        self.assertAlmostEqual(workorder.date_planned_start, datetime.now(), delta=timedelta(seconds=10), msg="Workorder should be planned now.")
        self.assertAlmostEqual(workorder.date_planned_finished, datetime.now() + timedelta(hours=1), delta=timedelta(seconds=10), msg="Workorder should be done in an hour.")

    def test_04b_test_planning_date(self):
        """ Test that workorder are planned at the correct time when setting a start date """
        # The workcenter is working 24/7
        self.full_availability()

        dining_table = self.env.ref("mrp.product_product_computer_desk")

        date_start = datetime.now() + timedelta(days=1)

        production_table_form = Form(self.env['mrp.production'])
        production_table_form.product_id = dining_table
        production_table_form.bom_id = self.env.ref("mrp.mrp_bom_desk")
        production_table_form.product_qty = 1.0
        production_table_form.product_uom_id = dining_table.uom_id
        production_table_form.date_start_wo = date_start
        production_table = production_table_form.save()
        production_table.action_confirm()

        # Create work order
        production_table.button_plan()
        workorder = production_table.workorder_ids[0]

        # Check that the workorder is planned now and that it lasts one hour
        self.assertAlmostEqual(workorder.date_planned_start, date_start, delta=timedelta(seconds=1), msg="Workorder should be planned tomorrow.")
        self.assertAlmostEqual(workorder.date_planned_finished, date_start + timedelta(hours=1), delta=timedelta(seconds=1), msg="Workorder should be done one hour later.")

    def test_change_production_1(self):
        """Change the quantity to produce on the MO while workorders are already planned."""
        dining_table = self.env.ref("mrp.product_product_computer_desk")
        dining_table.tracking = 'lot'
        production_table_form = Form(self.env['mrp.production'])
        production_table_form.product_id = dining_table
        production_table_form.bom_id = self.env.ref("mrp.mrp_bom_desk")
        production_table_form.product_qty = 1.0
        production_table_form.product_uom_id = dining_table.uom_id
        production_table = production_table_form.save()
        production_table.action_confirm()

        # Create work order
        production_table.button_plan()

        context = {'active_id': production_table.id, 'active_model': 'mrp.production'}
        change_qty_form = Form(self.env['change.production.qty'].with_context(context))
        change_qty_form.product_qty = 2.00
        change_qty = change_qty_form.save()
        change_qty.change_prod_qty()

        self.assertEqual(production_table.workorder_ids[0].qty_producing, 2, "Quantity to produce not updated")

    def test_planning_0(self):
        """ Test alternative conditions
        1. alternative relation is directionnal
        2. a workcenter cannot be it's own alternative """
        self.workcenter_1.alternative_workcenter_ids = self.wc_alt_1 | self.wc_alt_2
        self.assertEqual(self.wc_alt_1.alternative_workcenter_ids, self.env['mrp.workcenter'], "Alternative workcenter is not reciprocal")
        self.assertEqual(self.wc_alt_2.alternative_workcenter_ids, self.env['mrp.workcenter'], "Alternative workcenter is not reciprocal")
        with self.assertRaises(ValidationError):
            self.workcenter_1.alternative_workcenter_ids |= self.workcenter_1

    def test_planning_1(self):
        """ Testing planning workorder with alternative workcenters
        Plan 6 times the same MO, the workorders should be split accross workcenters
        The 3 workcenters are free, this test plans 3 workorder in a row then three next.
        The workcenters have not exactly the same parameters (efficiency, start time) so the
        the last 3 workorder are not dispatched like the 3 first.
        At the end of the test, the calendars will look like:
            - calendar wc1 :[mo1][mo4]
            - calendar wc2 :[mo2 ][mo5 ]
            - calendar wc3 :[mo3  ][mo6  ]"""
        planned_date = datetime(2019, 5, 13, 9, 0)
        self.workcenter_1.alternative_workcenter_ids = self.wc_alt_1 | self.wc_alt_2
        workcenters = [self.wc_alt_2, self.wc_alt_1, self.workcenter_1]
        for i in range(3):
            # Create an MO for product4
            mo_form = Form(self.env['mrp.production'])
            mo_form.product_id = self.product_4
            mo_form.bom_id = self.planning_bom
            mo_form.product_qty = 1
            mo_form.date_start_wo = planned_date
            mo = mo_form.save()
            mo.action_confirm()
            mo.button_plan()
            # Check that workcenters change
            self.assertEqual(mo.workorder_ids.workcenter_id, workcenters[i], "wrong workcenter %d" % i)
            self.assertAlmostEqual(mo.date_planned_start, planned_date, delta=timedelta(seconds=10))
            self.assertAlmostEqual(mo.date_planned_start, mo.workorder_ids.date_planned_start, delta=timedelta(seconds=10))

        for i in range(3):
            # Planning 3 more should choose workcenters in opposite order as
            # - wc_alt_2 as the best efficiency
            # - wc_alt_1 take a little less start time
            # - workcenter_1 is the worst
            mo_form = Form(self.env['mrp.production'])
            mo_form.product_id = self.product_4
            mo_form.bom_id = self.planning_bom
            mo_form.product_qty = 1
            mo_form.date_start_wo = planned_date
            mo = mo_form.save()
            mo.action_confirm()
            mo.button_plan()
            # Check that workcenters change
            self.assertEqual(mo.workorder_ids.workcenter_id, workcenters[i], "wrong workcenter %d" % i)
            self.assertNotEqual(mo.date_planned_start, planned_date)
            self.assertAlmostEqual(mo.date_planned_start, mo.workorder_ids.date_planned_start, delta=timedelta(seconds=10))

    def test_planning_2(self):
        """ Plan some manufacturing orders with 2 workorders each
        Batch size of the operation will influence start dates of workorders
        The first unit to be produced can go the second workorder before finishing
        to produce the second unit.
        calendar wc1 : [q1][q2]
        calendar wc2 :     [q1][q2]"""
        self.workcenter_1.alternative_workcenter_ids = self.wc_alt_1 | self.wc_alt_2
        self.planning_bom.routing_id = self.routing_2
        # Allow second workorder to start once the first one is not ended yet
        self.operation_2.batch = 'yes'
        self.operation_2.batch_size = 1
        self.env['mrp.workcenter'].search([]).write({'capacity': 1})
        # workcenters work 24/7
        self.full_availability()

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_4
        mo_form.bom_id = self.planning_bom
        mo_form.product_qty = 2
        mo = mo_form.save()
        mo.action_confirm()
        plan = datetime.now()
        mo.button_plan()
        self.assertEqual(mo.workorder_ids[0].workcenter_id, self.wc_alt_2, "wrong workcenter")
        self.assertEqual(mo.workorder_ids[1].workcenter_id, self.wc_alt_1, "wrong workcenter")

        duration1 = self.operation_2.time_cycle * 100.0 / self.wc_alt_2.time_efficiency + self.wc_alt_2.time_start
        duration2 = 2.0 * self.operation_2.time_cycle * 100.0 / self.wc_alt_1.time_efficiency + self.wc_alt_1.time_start + self.wc_alt_1.time_stop
        wo2_start = mo.workorder_ids[1].date_planned_start
        wo2_stop = mo.workorder_ids[1].date_planned_finished

        wo2_start_theo = self.wc_alt_2.resource_calendar_id.plan_hours(duration1 / 60.0, plan, compute_leaves=False, resource=self.wc_alt_2.resource_id)
        wo2_stop_theo = self.wc_alt_1.resource_calendar_id.plan_hours(duration2 / 60.0, wo2_start, compute_leaves=False, resource=self.wc_alt_2.resource_id)

        self.assertAlmostEqual(wo2_start, wo2_start_theo, delta=timedelta(seconds=10), msg="Wrong plannification")
        self.assertAlmostEqual(wo2_stop, wo2_stop_theo, delta=timedelta(seconds=10), msg="Wrong plannification")

    def test_planning_3(self):
        """ Plan some manufacturing orders with 1 workorder on 1 workcenter
        the first workorder will be hard set in the future to see if the second
        one take the free slot before on the calendar
        calendar after first mo : [   ][mo1]
        calendar after second mo: [mo2][mo1] """

        self.workcenter_1.alternative_workcenter_ids = self.wc_alt_1 | self.wc_alt_2
        self.env['mrp.workcenter'].search([]).write({'tz': 'UTC'}) # compute all date in UTC

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_4
        mo_form.bom_id = self.planning_bom
        mo_form.product_qty = 1
        mo_form.date_start_wo = datetime(2019, 5, 13, 14, 0, 0, 0)
        mo = mo_form.save()
        start = mo.date_start_wo
        mo.action_confirm()
        mo.button_plan()
        self.assertEqual(mo.workorder_ids[0].workcenter_id, self.wc_alt_2, "wrong workcenter")
        wo1_start = mo.workorder_ids[0].date_planned_start
        wo1_stop = mo.workorder_ids[0].date_planned_finished
        self.assertAlmostEqual(wo1_start, start, delta=timedelta(seconds=10), msg="Wrong plannification")
        self.assertAlmostEqual(wo1_stop, start + timedelta(minutes=85.58), delta=timedelta(seconds=10), msg="Wrong plannification")

        # second MO should be plan before as there is a free slot before
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_4
        mo_form.bom_id = self.planning_bom
        mo_form.product_qty = 1
        mo_form.date_start_wo = datetime(2019, 5, 13, 9, 0, 0, 0)
        mo = mo_form.save()
        mo.action_confirm()
        mo.button_plan()
        self.assertEqual(mo.workorder_ids[0].workcenter_id, self.wc_alt_2, "wrong workcenter")
        wo1_start = mo.workorder_ids[0].date_planned_start
        wo1_stop = mo.workorder_ids[0].date_planned_finished
        self.assertAlmostEqual(wo1_start, datetime(2019, 5, 13, 9, 0, 0, 0), delta=timedelta(seconds=10), msg="Wrong plannification")
        self.assertAlmostEqual(wo1_stop, datetime(2019, 5, 13, 9, 0, 0, 0) + timedelta(minutes=85.59), delta=timedelta(seconds=10), msg="Wrong plannification")

    def test_planning_4(self):
        """ Plan a manufacturing orders with 1 workorder on 1 workcenter
        the workcenter calendar is empty. which means the workcenter is never
        available. Planning a workorder on it should raise an error"""

        self.workcenter_1.alternative_workcenter_ids = self.wc_alt_1 | self.wc_alt_2
        self.env['resource.calendar'].search([]).write({'attendance_ids': [(5, False, False)]})

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_4
        mo_form.bom_id = self.planning_bom
        mo_form.product_qty = 1
        mo = mo_form.save()
        mo.action_confirm()
        with self.assertRaises(UserError):
            mo.button_plan()

    def test_planning_5(self):
        """ Cancelling a production with workorders should free all reserved slot
        in the related workcenters calendars """
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_4
        mo_form.bom_id = self.planning_bom
        mo_form.product_qty = 1
        mo = mo_form.save()
        mo.action_confirm()
        mo.button_plan()

        mo.action_cancel()
        self.assertEqual(mo.workorder_ids.mapped('date_start'), [False])
        self.assertEqual(mo.workorder_ids.mapped('date_finished'), [False])

    def test_planning_6(self):
        """ Marking a workorder as done before the theoretical date should update
        the reservation slot in the calendar the be able to reserve the next
        production sooner """
        self.workcenter_1.alternative_workcenter_ids = self.wc_alt_1 | self.wc_alt_2
        self.env['mrp.workcenter'].search([]).write({'tz': 'UTC'}) # compute all date in UTC
        self.planning_bom.routing = self.env.ref("mrp.mrp_routing_0")
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_4
        mo_form.bom_id = self.planning_bom
        mo_form.product_qty = 1
        mo_form.date_start_wo = datetime(2019, 5, 13, 9, 0, 0, 0)
        mo = mo_form.save()
        mo.action_confirm()
        mo.button_plan()
        wo = mo.workorder_ids
        self.assertAlmostEqual(wo.date_planned_start, datetime(2019, 5, 13, 9, 0, 0, 0), delta=timedelta(seconds=10))
        self.assertAlmostEqual(wo.date_planned_finished, datetime(2019, 5, 13, 9, 0, 0, 0) + timedelta(minutes=85.58), delta=timedelta(seconds=10))
        wo.button_start()
        wo.record_production()
        # Marking workorder as done should change the finished date
        self.assertAlmostEqual(wo.date_finished, datetime.now(), delta=timedelta(seconds=10))
        self.assertAlmostEqual(wo.date_planned_finished, datetime.now(), delta=timedelta(seconds=10))

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_4
        mo_form.bom_id = self.planning_bom
        mo_form.product_qty = 1
        mo_form.date_start_wo = datetime(2019, 5, 13, 9, 0, 0, 0)
        mo = mo_form.save()
        mo.action_confirm()
        mo.button_plan()
        wo = mo.workorder_ids
        wo.button_start()
        self.assertAlmostEqual(wo.date_start, datetime.now(), delta=timedelta(seconds=10))
        self.assertAlmostEqual(wo.date_planned_start, datetime.now(), delta=timedelta(seconds=10))
        self.assertAlmostEqual(wo.date_planned_finished, datetime.now(), delta=timedelta(seconds=10))

    def test_planning_7(self):
        """ set the workcenter capacity to 10. Produce a dozen of product tracked by
        SN. The production should be done in two batches"""
        self.workcenter_1.capacity = 10
        self.workcenter_1.time_efficiency = 100
        self.workcenter_1.time_start = 0
        self.workcenter_1.time_stop = 0
        self.routing_1.operation_ids.time_cycle = 60
        self.product_4.tracking = 'serial'
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_4
        mo_form.bom_id = self.planning_bom
        mo_form.product_uom_id = self.uom_dozen
        mo_form.product_qty = 1
        mo = mo_form.save()
        mo.action_confirm()
        mo.button_plan()
        wo = mo.workorder_ids
        self.assertEqual(wo.duration_expected, 120)

    def test_plan_unplan_date(self):
        """ Testing planning a workorder then cancel it and then plan it again.
        The planned date must be the same the first time and the second time the
        workorder is planned."""
        planned_date = datetime(2019, 5, 13, 9, 0)
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_4
        mo_form.bom_id = self.planning_bom
        mo_form.product_qty = 1
        mo_form.date_start_wo = planned_date
        mo = mo_form.save()
        mo.action_confirm()
        # Plans the MO and checks the date.
        mo.button_plan()
        self.assertAlmostEqual(mo.date_planned_start, planned_date, delta=timedelta(seconds=10))
        self.assertEqual(bool(mo.workorder_ids.exists()), True)
        leave = mo.workorder_ids.leave_id
        self.assertEqual(bool(leave.exists()), True)
        # Unplans the MO and checks the workorder and its leave no more exist.
        mo.button_unplan()
        self.assertEqual(bool(mo.workorder_ids.exists()), False)
        self.assertEqual(bool(leave.exists()), False)
        # Plans (again) the MO and checks the date is still the same.
        mo.button_plan()
        self.assertAlmostEqual(mo.date_planned_start, planned_date, delta=timedelta(seconds=10))
        self.assertAlmostEqual(mo.date_planned_start, mo.workorder_ids.date_planned_start, delta=timedelta(seconds=10))

    def test_kit_planning(self):
        """ Bom made of component 1 and component 2 which is a kit made of
        component 1 too. Check the workorder lines are well created after reservation
        Main bom :
            - comp1 (qty=1)
            - kit (qty=1)
                - comp1 (qty=4)
                - comp2 (qty=1)
        should give :
            - wo line 1 (comp1, qty=1)
            - wo line 2 (comp1, qty=4)
            - wo line 3 (comp2, qty=1) """
        # Kit bom
        self.env['mrp.bom'].create({
            'product_id': self.product_4.id,
            'product_tmpl_id': self.product_4.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': self.product_2.id, 'product_qty': 1}),
                (0, 0, {'product_id': self.product_1.id, 'product_qty': 4})
            ]})

        # Main bom
        main_bom = self.env['mrp.bom'].create({
            'product_id': self.product_5.id,
            'product_tmpl_id': self.product_5.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'routing_id': self.routing_1.id,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': self.product_1.id, 'product_qty': 1}),
                (0, 0, {'product_id': self.product_4.id, 'product_qty': 1})
            ]})

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_5
        mo_form.bom_id = main_bom
        mo_form.product_qty = 1
        mo = mo_form.save()
        mo.action_confirm()
        mo.action_assign()
        mo.button_plan()

        self.assertEqual(len(mo.workorder_ids), 1)
        self.assertEqual(len(mo.workorder_ids.raw_workorder_line_ids), 3)
        line1 = mo.workorder_ids.raw_workorder_line_ids[0]
        line2 = mo.workorder_ids.raw_workorder_line_ids[1]
        line3 = mo.workorder_ids.raw_workorder_line_ids[2]
        self.assertEqual(line1.product_id, self.product_1)
        self.assertEqual(line1.qty_done, 1)
        self.assertEqual(line2.product_id, self.product_2)
        self.assertEqual(line2.qty_done, 1)
        self.assertEqual(line3.product_id, self.product_1)
        self.assertEqual(line3.qty_done, 4)


class TestRoutingAndKits(SavepointCase):
    @classmethod
    def setUpClass(cls):
        """
        kit1 (consu)
        compkit1
        finished1
        compfinished1

        Finished1 (Bom1)
            - compfinished1
            - kit1
        Kit1 (BomKit1)
            - compkit1

        Rounting1 (finished1)
            - operation 1
            - operation 2
        Rounting2 (kit1)
            - operation 1
        """
        super(TestRoutingAndKits, cls).setUpClass()
        cls.uom_unit = cls.env['uom.uom'].search([
            ('category_id', '=', cls.env.ref('uom.product_uom_categ_unit').id),
            ('uom_type', '=', 'reference')
        ], limit=1)
        cls.kit1 = cls.env['product.product'].create({
            'name': 'kit1',
            'type': 'consu',
        })
        cls.compkit1 = cls.env['product.product'].create({
            'name': 'compkit1',
            'type': 'product',
        })
        cls.finished1 = cls.env['product.product'].create({
            'name': 'finished1',
            'type': 'product',
        })
        cls.compfinished1 = cls.env['product.product'].create({
            'name': 'compfinished',
            'type': 'product',
        })
        cls.workcenter_finished1 = cls.env['mrp.workcenter'].create({
            'name': 'workcenter1',
        })
        cls.workcenter_kit1 = cls.env['mrp.workcenter'].create({
            'name': 'workcenter2',
        })
        cls.routing_finished1 = cls.env['mrp.routing'].create({
            'name': 'routing for finished1',
        })
        cls.operation_finished1 = cls.env['mrp.routing.workcenter'].create({
            'sequence': 1,
            'name': 'finished operation 1',
            'workcenter_id': cls.workcenter_finished1.id,
            'routing_id': cls.routing_finished1.id,
        })
        cls.operation_finished2 = cls.env['mrp.routing.workcenter'].create({
            'sequence': 1,
            'name': 'finished operation 2',
            'workcenter_id': cls.workcenter_finished1.id,
            'routing_id': cls.routing_finished1.id,
        })
        cls.routing_kit1 = cls.env['mrp.routing'].create({
            'name': 'routing for kit1',
        })
        cls.operation_kit1 = cls.env['mrp.routing.workcenter'].create({
            'name': 'Kit operation',
            'workcenter_id': cls.workcenter_kit1.id,
            'routing_id': cls.routing_kit1.id,
        })
        cls.bom_finished1 = cls.env['mrp.bom'].create({
            'product_id': cls.finished1.id,
            'product_tmpl_id': cls.finished1.product_tmpl_id.id,
            'product_uom_id': cls.uom_unit.id,
            'product_qty': 1,
            'type': 'normal',
            'routing_id': cls.routing_finished1.id,
            'bom_line_ids': [
                (0, 0, {'product_id': cls.compfinished1.id, 'product_qty': 1}),
                (0, 0, {'product_id': cls.kit1.id, 'product_qty': 1}),
            ]})
        cls.bom_kit1 = cls.env['mrp.bom'].create({
            'product_id': cls.kit1.id,
            'product_tmpl_id': cls.kit1.product_tmpl_id.id,
            'product_uom_id': cls.uom_unit.id,
            'product_qty': 1,
            'type': 'phantom',
            'routing_id': cls.routing_kit1.id,
            'bom_line_ids': [
                (0, 0, {'product_id': cls.compkit1.id, 'product_qty': 1}),
            ]})

    def test_1(self):
        """Operations are set on `self.bom_kit1` but none on `self.bom_finished1`."""
        self.bom_kit1.bom_line_ids.operation_id = self.operation_kit1

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.finished1
        mo_form.bom_id = self.bom_finished1
        mo_form.product_qty = 1.0
        mo = mo_form.save()

        mo.action_confirm()
        mo.button_plan()

        self.assertEqual(len(mo.workorder_ids), 3)
        self.assertEqual(len(mo.workorder_ids[0].raw_workorder_line_ids), 0)
        self.assertEqual(mo.workorder_ids[1].raw_workorder_line_ids.product_id, self.compfinished1)
        self.assertEqual(mo.workorder_ids[2].raw_workorder_line_ids.product_id, self.compkit1)

    def test_2(self):
        """Operations are not set on `self.bom_kit1` and `self.bom_finished1`."""
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.finished1
        mo_form.bom_id = self.bom_finished1
        mo_form.product_qty = 1.0
        mo = mo_form.save()

        mo.action_confirm()
        mo.button_plan()

        self.assertEqual(len(mo.workorder_ids), 3)
        self.assertEqual(len(mo.workorder_ids[0].raw_workorder_line_ids), 0)
        self.assertEqual(mo.workorder_ids[1].raw_workorder_line_ids.product_id, self.compfinished1)
        self.assertEqual(mo.workorder_ids[2].raw_workorder_line_ids.product_id, self.compkit1)

    def test_3(self):
        """Operations are set both `self.bom_kit1` and `self.bom_finished1`."""
        self.bom_kit1.bom_line_ids.operation_id = self.operation_kit1
        self.bom_finished1.bom_line_ids[0].operation_id = self.operation_finished1
        self.bom_finished1.bom_line_ids[1].operation_id = self.operation_finished2

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.finished1
        mo_form.bom_id = self.bom_finished1
        mo_form.product_qty = 1.0
        mo = mo_form.save()

        mo.action_confirm()
        mo.button_plan()

        self.assertEqual(len(mo.workorder_ids), 3)
        self.assertEqual(mo.workorder_ids[0].raw_workorder_line_ids.product_id, self.compfinished1)
        self.assertFalse(mo.workorder_ids[1].raw_workorder_line_ids.product_id.id)
        self.assertEqual(mo.workorder_ids[2].raw_workorder_line_ids.product_id, self.compkit1)

    def test_4(self):
        """Operations are set on `self.kit1`, none are set on `self.bom_finished1` and a kit
        without routing was added to `self.bom_finished1`. We expect the component of the kit
        without routing to be consumed at the last workorder of the main BoM.
        """
        kit2 = self.env['product.product'].create({
            'name': 'kit2',
            'type': 'consu',
        })
        compkit2 = self.env['product.product'].create({
            'name': 'compkit2',
            'type': 'product',
        })
        bom_kit2 = self.env['mrp.bom'].create({
            'product_id': kit2.id,
            'product_tmpl_id': kit2.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1,
            'type': 'phantom',
            'bom_line_ids': [(0, 0, {'product_id': compkit2.id, 'product_qty': 1})]
        })
        self.bom_finished1.write({'bom_line_ids': [(0, 0, {'product_id': kit2.id, 'product_qty': 1})]})

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.finished1
        mo_form.bom_id = self.bom_finished1
        mo_form.product_qty = 1.0
        mo = mo_form.save()

        mo.action_confirm()
        mo.button_plan()

        self.assertEqual(len(mo.workorder_ids), 3)

        self.assertEqual(len(mo.workorder_ids[0].raw_workorder_line_ids), 0)
        self.assertEqual(set(mo.workorder_ids[1].raw_workorder_line_ids.product_id.ids), set([self.compfinished1.id, compkit2.id]))
        self.assertEqual(mo.workorder_ids[2].raw_workorder_line_ids.product_id, self.compkit1)

    def test_5(self):
        # Main bom: set the normal component to the first of the two operations of the routing.
        bomline_compfinished = self.bom_finished1.bom_line_ids.filtered(lambda bl: bl.product_id == self.compfinished1)
        bomline_compfinished.operation_id = self.operation_finished1

        # Main bom: the kit do not have an operation set but there's one on its bom
        bomline_kit1 = self.bom_finished1.bom_line_ids - bomline_compfinished
        self.assertFalse(bomline_kit1.operation_id.id)
        self.bom_kit1.bom_line_ids.operation_id = self.bom_kit1.routing_id.operation_ids

        # Main bom: add a kit without routing
        kit2 = self.env['product.product'].create({
            'name': 'kit2',
            'type': 'consu',
        })
        compkit2 = self.env['product.product'].create({
            'name': 'compkit2',
            'type': 'product',
        })
        bom_kit2 = self.env['mrp.bom'].create({
            'product_id': kit2.id,
            'product_tmpl_id': kit2.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1,
            'type': 'phantom',
            'bom_line_ids': [(0, 0, {'product_id': compkit2.id, 'product_qty': 1})]
        })
        self.bom_finished1.write({'bom_line_ids': [(0, 0, {'product_id': kit2.id, 'product_qty': 1})]})

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.finished1
        mo_form.bom_id = self.bom_finished1
        mo_form.product_qty = 1.0
        mo = mo_form.save()

        mo.action_confirm()
        mo.button_plan()

        self.assertEqual(len(mo.workorder_ids), 3)
        self.assertEqual(mo.workorder_ids[0].raw_workorder_line_ids.product_id, self.compfinished1)
        self.assertEqual(mo.workorder_ids[1].raw_workorder_line_ids.product_id, compkit2)
        self.assertEqual(mo.workorder_ids[2].raw_workorder_line_ids.product_id, self.compkit1)

    def test_6(self):
        """ Use the same routing on `self.bom_fnished1` and `self.kit1`. The workorders should not
        be duplicated.
        """
        self.bom_finished1.bom_line_ids[0].operation_id = self.operation_finished1
        self.bom_finished1.bom_line_ids[1].operation_id = self.operation_finished2
        self.bom_kit1.routing_id = self.routing_finished1
        self.bom_kit1.bom_line_ids.operation_id = self.operation_finished1

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.finished1
        mo_form.bom_id = self.bom_finished1
        mo_form.product_qty = 1.0
        mo = mo_form.save()

        mo.action_confirm()
        mo.button_plan()

        self.assertEqual(len(mo.workorder_ids), 2)
        self.assertEqual(set(mo.workorder_ids[0].raw_workorder_line_ids.product_id.ids), set([self.compfinished1.id, self.compkit1.id]))
        self.assertFalse(mo.workorder_ids[1].raw_workorder_line_ids.product_id.id)

    def test_merge_lot(self):
        """ Produce 10 units of product tracked by lot on two workorder. On the
        first one, produce 4 onto lot1 then 6 onto lot1 as well. The second
        workorder should be prefilled with 10 units and lot1"""
        self.finished1.tracking = 'lot'
        lot1 = self.env['stock.production.lot'].create({
            'product_id': self.finished1.id,
            'company_id': self.env.company.id,
        })
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.finished1
        mo_form.bom_id = self.bom_finished1
        mo_form.product_qty = 10.0
        mo = mo_form.save()

        mo.action_confirm()
        mo.button_plan()
        wo1 = mo.workorder_ids.filtered(lambda wo: wo.state == 'ready')[0]
        wo1.button_start()
        wo1.qty_producing = 4
        wo1.finished_lot_id = lot1
        wo1.record_production()
        wo1.qty_producing = 6
        wo1.finished_lot_id = lot1
        wo1.record_production()
        wo2 = mo.workorder_ids.filtered(lambda wo: wo.state == 'ready')[0]
        wo2.button_start()
        self.assertEqual(wo2.qty_producing, 10)
        self.assertEqual(wo2.finished_lot_id, lot1)
