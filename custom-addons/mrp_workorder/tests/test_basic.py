# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from odoo import Command
from odoo.tests import Form
from odoo.tests.common import TransactionCase
from odoo.addons.mrp_workorder.tests.common import TestMrpWorkorderCommon
from odoo.exceptions import ValidationError, UserError
from freezegun import freeze_time


class TestWorkOrderProcessCommon(TestMrpWorkorderCommon):

    @classmethod
    def setUpClass(cls):
        super(TestWorkOrderProcessCommon, cls).setUpClass()
        cls.env.company.resource_calendar_id.tz = "Europe/Brussels"
        cls.source_location_id = cls.stock_location_14.id
        cls.warehouse = cls.env.ref('stock.warehouse0')
        # setting up alternative workcenters
        cls.wc_alt_1 = cls.env['mrp.workcenter'].create({
            'name': 'Nuclear Workcenter bis',
            'default_capacity': 3,
            'time_start': 9,
            'time_stop': 5,
            'time_efficiency': 80,
        })
        cls.wc_alt_2 = cls.env['mrp.workcenter'].create({
            'name': 'Nuclear Workcenter ter',
            'default_capacity': 1,
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
            'consumption': 'flexible',
            'operation_ids': [
                (0, 0, {'name': 'Gift Wrap Maching', 'workcenter_id': cls.workcenter_1.id, 'time_cycle': 15, 'sequence': 1}),
            ],
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': cls.product_2.id, 'product_qty': 2}),
                (0, 0, {'product_id': cls.product_1.id, 'product_qty': 4})
            ]})
        cls.dining_table = cls.env['product.product'].create({
            'name': 'Table (MTO)',
            'type': 'product',
            'tracking': 'serial',
        })
        cls.product_table_sheet = cls.env['product.product'].create({
            'name': 'Table Top',
            'type': 'product',
            'tracking': 'serial',
        })
        cls.product_table_leg = cls.env['product.product'].create({
            'name': 'Table Leg',
            'type': 'product',
            'tracking': 'lot',
        })
        cls.product_bolt = cls.env['product.product'].create({
            'name': 'Bolt',
            'type': 'product',
        })
        cls.product_screw = cls.env['product.product'].create({
            'name': 'Screw',
            'type': 'product',
        })

        cls.mrp_workcenter = cls.env['mrp.workcenter'].create({
            'name': 'Assembly Line 1',
            'resource_calendar_id': cls.env.ref('resource.resource_calendar_std').id,
        })
        cls.mrp_bom_desk = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.dining_table.product_tmpl_id.id,
            'product_uom_id': cls.env.ref('uom.product_uom_unit').id,
            'sequence': 3,
            'ready_to_produce': 'asap',
            'consumption': 'flexible',
            'operation_ids': [
                (0, 0, {'workcenter_id': cls.mrp_workcenter.id, 'name': 'Manual Assembly'}),
            ],
        })
        cls.mrp_bom_desk.write({
            'bom_line_ids': [
                (0, 0, {
                    'product_id': cls.product_table_sheet.id,
                    'product_qty': 1,
                    'product_uom_id': cls.env.ref('uom.product_uom_unit').id,
                    'sequence': 1,
                    'operation_id': cls.mrp_bom_desk.operation_ids.id}),
                (0, 0, {
                    'product_id': cls.product_table_leg.id,
                    'product_qty': 4,
                    'product_uom_id': cls.env.ref('uom.product_uom_unit').id,
                    'sequence': 2,
                    'operation_id': cls.mrp_bom_desk.operation_ids.id}),
                (0, 0, {
                    'product_id': cls.product_bolt.id,
                    'product_qty': 4,
                    'product_uom_id': cls.env.ref('uom.product_uom_unit').id,
                    'sequence': 3,
                    'operation_id': cls.mrp_bom_desk.operation_ids.id}),
                (0, 0, {
                    'product_id': cls.product_screw.id,
                    'product_qty': 10,
                    'product_uom_id': cls.env.ref('uom.product_uom_unit').id,
                    'sequence': 4,
                    'operation_id': cls.mrp_bom_desk.operation_ids.id}),
            ]
        })
        cls.mrp_workcenter_1 = cls.env['mrp.workcenter'].create({
            'name': 'Drill Station 1',
            'resource_calendar_id': cls.env.ref('resource.resource_calendar_std').id,
        })
        cls.mrp_workcenter_3 = cls.env['mrp.workcenter'].create({
            'name': 'Assembly Line 1',
            'resource_calendar_id': cls.env.ref('resource.resource_calendar_std').id,
        })
        cls.bom_laptop = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.laptop.product_tmpl_id.id,
            'product_qty': 1,
            'product_uom_id': cls.uom_unit.id,
            'consumption': 'flexible',
            'bom_line_ids': [(0, 0, {
                'product_id': cls.graphics_card.id,
                'product_qty': 1,
                'product_uom_id': cls.uom_unit.id,
            })],
            'operation_ids': [
                (0, 0, {'name': 'Cutting Machine', 'workcenter_id': cls.mrp_workcenter_1.id, 'time_cycle': 12, 'sequence': 1}),
            ],
        })
        # remove leaves that may affect our tests
        cls.env.ref('resource.resource_calendar_std').leave_ids.unlink()

    def test_cancel_mo_with_routing(self):
        """ Cancel a Manufacturing Order with routing (so generate a Work Order)
        and produce some quantities. When cancelled, the MO must be marked as
        done and the WO must be cancelled.
        """
        # Create MO
        product_to_build = self.env['product.product'].create({
            'name': 'Young Tom',
            'type': 'product',
        })
        product_to_use_1 = self.env['product.product'].create({
            'name': 'Botox',
            'type': 'product',
        })
        product_to_use_2 = self.env['product.product'].create({
            'name': 'Old Tom',
            'type': 'product',
        })
        bom = self.env['mrp.bom'].create({
            'product_id': product_to_build.id,
            'product_tmpl_id': product_to_build.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'consumption': 'strict',
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': product_to_use_2.id, 'product_qty': 4}),
                (0, 0, {'product_id': product_to_use_1.id, 'product_qty': 1})
            ],
            'operation_ids': [
                (0, 0, {'name': 'Gift Wrap Maching', 'workcenter_id': self.workcenter_1.id, 'time_cycle': 15, 'sequence': 1}),
            ]
        })
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product_to_build
        mo_form.bom_id = bom
        mo_form.product_qty = 5.0
        manufacturing_order = mo_form.save()
        manufacturing_order.action_confirm()

        manufacturing_order.button_plan()
        workorder = manufacturing_order.workorder_ids
        # Produce some quantity
        workorder.button_start()
        workorder.qty_producing = 2
        workorder.record_production()
        # Post Inventory
        manufacturing_order._post_inventory()
        backorder = manufacturing_order.procurement_group_id.mrp_production_ids[-1]
        # Cancel it
        backorder.action_cancel()
        # Check MO is done, WO is cancelled and its SML are done or cancelled
        self.assertEqual(manufacturing_order.state, 'done', "MO should be in done state.")
        self.assertEqual(workorder.state, 'done', "WO should be one.")
        self.assertEqual(manufacturing_order.move_raw_ids[0].state, 'done',
            "Due to 'post_inventory', some move raw must stay in done state")
        self.assertEqual(manufacturing_order.move_raw_ids[1].state, 'done',
            "Due to 'post_inventory', some move raw must stay in done state")
        self.assertEqual(backorder.move_raw_ids[0].state, 'cancel',
            "The other move raw are cancelled like their MO.")
        self.assertEqual(backorder.move_raw_ids[1].state, 'cancel',
            "The other move raw are cancelled like their MO.")
        self.assertEqual(manufacturing_order.move_finished_ids[0].state, 'done',
            "Due to 'post_inventory', a move finished must stay in done state")
        self.assertEqual(backorder.move_finished_ids[0].state, 'cancel',
            "The other move finished is cancelled like its MO.")

    def test_putaway_after_manufacturing_1(self):
        """ This test checks a manufactured product without tracking will go to
        location defined in putaway strategy.
        """
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.depot_location = self.env['stock.location'].create({
            'name': 'Depot',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        self.env["stock.putaway.rule"].create({
            "location_in_id": self.stock_location.id,
            "location_out_id": self.depot_location.id,
            'category_id': self.env.ref('product.product_category_all').id,
        })

        self.env['stock.quant']._update_available_quantity(self.graphics_card, self.stock_location, 20)
        form = Form(self.env['mrp.production'])
        form.product_id = self.laptop
        form.product_qty = 1
        form.bom_id = self.bom_laptop
        mo_laptop = form.save()
        mo_laptop.action_confirm()
        # <field name="qty_producing" invisible="state == 'draft'"/>
        form = Form(mo_laptop)
        form.qty_producing = 2.0
        mo_laptop = form.save()
        mo_laptop.action_assign()

        mo_laptop.button_plan()
        workorder = mo_laptop.workorder_ids[0]

        workorder.button_start()
        workorder.record_production()
        mo_laptop.move_raw_ids.quantity = 2.0
        mo_laptop.move_raw_ids.picked = True
        mo_laptop.button_mark_done()

        # We check if the laptop go in the depot and not in the stock
        move = mo_laptop.move_finished_ids
        location_dest = move.move_line_ids.location_dest_id
        self.assertEqual(location_dest.id, self.depot_location.id)
        self.assertNotEqual(location_dest.id, self.stock_location.id)

    def test_putaway_after_manufacturing_2(self):
        """ This test checks a tracked manufactured product will go to location
        defined in putaway strategy.
        """
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.depot_location = self.env['stock.location'].create({
            'name': 'Depot',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        self.env["stock.putaway.rule"].create({
            "location_in_id": self.stock_location.id,
            "location_out_id": self.depot_location.id,
            'category_id': self.env.ref('product.product_category_all').id,
        })
        self.env['stock.quant']._update_available_quantity(self.graphics_card, self.stock_location, 20)
        self.laptop.tracking = 'serial'
        form = Form(self.env['mrp.production'])
        form.product_id = self.laptop
        form.product_qty = 1
        form.bom_id = self.bom_laptop
        mo_laptop = form.save()
        mo_laptop.action_confirm()
        mo_laptop.action_assign()

        mo_laptop.button_plan()
        workorder = mo_laptop.workorder_ids[0]

        workorder.button_start()
        serial = self.env['stock.lot'].create({'product_id': self.laptop.id, 'company_id': self.env.company.id})
        workorder.finished_lot_id = serial
        workorder.record_production()
        mo_laptop.button_mark_done()

        # We check if the laptop go in the depot and not in the stock
        move = mo_laptop.move_finished_ids
        location_dest = move.move_line_ids.location_dest_id
        self.assertEqual(location_dest.id, self.depot_location.id)
        self.assertNotEqual(location_dest.id, self.stock_location.id)

    def test_backorder_1(self):
        """Operations are set on `self.bom_kit1` but none on `self.bom_finished1`."""
        # TODO: This test name + description don't match the test (there are no backorders
        # or kits). Test should either be rewritten or renamed if someone can figure out
        # what its intended purpose is.
        self.finished1 = self.env['product.product'].create({
            'name': 'finished1',
            'type': 'product',
        })
        self.compfinished1 = self.env['product.product'].create({
            'name': 'compfinished1',
            'type': 'product',
        })
        self.compfinished2 = self.env['product.product'].create({
            'name': 'compfinished2',
            'type': 'product',
        })
        self.workcenter1 = self.env['mrp.workcenter'].create({
            'name': 'workcenter1',
        })
        self.workcenter2 = self.env['mrp.workcenter'].create({
            'name': 'workcenter2',
        })

        self.bom_finished1 = self.env['mrp.bom'].create({
            'product_id': self.finished1.id,
            'product_tmpl_id': self.finished1.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1,
            'consumption': 'flexible',
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': self.compfinished1.id, 'product_qty': 1}),
                (0, 0, {'product_id': self.compfinished2.id, 'product_qty': 1}),
            ],
            'operation_ids': [
                (0, 0, {'sequence': 1, 'name': 'finished operation 1', 'workcenter_id': self.workcenter1.id}),
                (0, 0, {'sequence': 2, 'name': 'finished operation 2', 'workcenter_id': self.workcenter2.id}),
            ],
        })
        self.bom_finished1.bom_line_ids[0].operation_id = self.bom_finished1.operation_ids[0].id
        self.bom_finished1.bom_line_ids[1].operation_id = self.bom_finished1.operation_ids[1].id

        self.env['quality.point'].create({
            'product_ids': [(4, self.finished1.id)],
            'picking_type_ids': [(4, self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')], limit=1).id)],
            'operation_id': self.bom_finished1.operation_ids[0].id,
            'test_type_id': self.env.ref('mrp_workorder.test_type_register_consumed_materials').id,
            'component_id': self.compfinished1.id,
        })
        self.env['quality.point'].create({
            'product_ids': [(4, self.finished1.id)],
            'picking_type_ids': [(4, self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')], limit=1).id)],
            'operation_id': self.bom_finished1.operation_ids[1].id,
            'test_type_id': self.env.ref('mrp_workorder.test_type_register_consumed_materials').id,
            'component_id': self.compfinished2.id,
        })

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.finished1
        mo_form.bom_id = self.bom_finished1
        mo_form.product_qty = 2.0
        mo = mo_form.save()

        mo.action_confirm()
        mo.button_plan()

        self.assertEqual(len(mo.workorder_ids), 2)

        workorder1 = mo.workorder_ids[0]
        workorder2 = mo.workorder_ids[1]
        self.assertEqual(workorder1.check_ids.component_id, self.compfinished1)
        self.assertEqual(workorder1.qty_remaining, 2)

        self.assertEqual(workorder2.check_ids.component_id, self.compfinished2)
        self.assertEqual(workorder2.qty_remaining, 2)

        mo.workorder_ids.check_ids.quality_state = 'pass'
        mo.move_raw_ids.quantity = 2.0
        mo.move_raw_ids.picked = True
        mo.qty_producing = 2.0
        mo.with_context(debug=True).button_mark_done()

        self.assertEqual(workorder1.state, 'done')
        self.assertEqual(workorder2.state, 'done')

    def test_backorder_2(self):
        """Test if all the quality checks are retained when a backorder is created from the tablet view"""

        finished_product = self.env['product.product'].create({
            'name': 'finished_product',
            'type': 'product',
            'tracking': 'serial',
        })
        component = self.env['product.product'].create({
            'name': 'component',
            'type': 'product',
        })
        workcenter = self.env['mrp.workcenter'].create({
            'name': 'workcenter',
        })
        bom = self.env['mrp.bom'].create({
            'product_id': finished_product.id,
            'product_tmpl_id': finished_product.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1,
            'consumption': 'flexible',
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': component.id, 'product_qty': 1}),
            ],
            'operation_ids': [
                (0, 0, {'sequence': 1, 'name': 'finished operation 1', 'workcenter_id': workcenter.id}),
            ],
        })
        bom.bom_line_ids[0].operation_id = bom.operation_ids[0].id

        self.env['quality.point'].create({
            'product_ids': [(4, finished_product.id)],
            'picking_type_ids': [
                (4, self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')], limit=1).id)],
            'operation_id': bom.operation_ids[0].id,
            'test_type_id': self.env.ref('quality.test_type_instructions').id,
            'note': 'Installing VIM (pcs xi ipzth adi du ixbt)',
        })

        self.env['stock.quant']._update_available_quantity(component, self.stock_location_14, 10)

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = finished_product
        mo_form.bom_id = bom
        mo_form.product_qty = 2.0
        mo = mo_form.save()
        mo.action_confirm()
        mo.button_plan()

        wo = mo.workorder_ids[0]
        wo.button_start()
        wo.action_generate_serial()
        result = wo.do_finish()
        wo_backorder = self.env['mrp.workorder'].browse(result['res_id'])
        self.assertEqual(len(wo_backorder.check_ids), len(wo.check_ids))


class TestWorkOrderProcess(TestWorkOrderProcessCommon):
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

    def test_00_workorder_process(self):
        """ Testing consume quants and produced quants with workorder """
        dining_table = self.dining_table
        product_table_sheet = self.product_table_sheet
        product_table_leg = self.product_table_leg
        product_bolt = self.product_bolt
        product_screw = self.product_screw
        mrp_bom_desk = self.mrp_bom_desk
        mrp_bom_desk.bom_line_ids.operation_id = False
        mrp_bom_desk.bom_line_ids.manual_consumption = False

        self.env['stock.move'].search([('product_id', 'in', [product_bolt.id, product_screw.id])])._do_unreserve()

        # Set tracking lot on finish and consume products.
        dining_table.tracking = 'lot'
        product_table_sheet.tracking = 'lot'
        product_table_leg.tracking = 'lot'
        product_bolt.tracking = "lot"

        production_table_form = Form(self.env['mrp.production'])
        production_table_form.product_id = dining_table
        production_table_form.bom_id = mrp_bom_desk
        production_table_form.product_qty = 1.0
        production_table_form.product_uom_id = dining_table.uom_id
        production_table = production_table_form.save()
        production_table.action_confirm()

        # Initial inventory of product sheet, lags and bolt
        lot_sheet = self.env['stock.lot'].create({'product_id': product_table_sheet.id, 'company_id': self.env.company.id})
        lot_leg = self.env['stock.lot'].create({'product_id': product_table_leg.id, 'company_id': self.env.company.id})
        lot_bolt = self.env['stock.lot'].create({'product_id': product_bolt.id, 'company_id': self.env.company.id})

        # Initialize inventory
        # --------------------
        quants = self.env['stock.quant'].create({
            'product_id': product_table_sheet.id,
            'inventory_quantity': 20,
            'lot_id': lot_sheet.id,
            'location_id': self.source_location_id
        })
        quants |= self.env['stock.quant'].create({
            'product_id': product_table_leg.id,
            'inventory_quantity': 20,
            'lot_id': lot_leg.id,
            'location_id': self.source_location_id
        })
        quants |= self.env['stock.quant'].create({
            'product_id': product_bolt.id,
            'inventory_quantity': 20,
            'lot_id': lot_bolt.id,
            'location_id': self.source_location_id
        })
        quants |= self.env['stock.quant'].create({
            'product_id': product_screw.id,
            'inventory_quantity': 20,
            'location_id': self.source_location_id
        })
        quants.action_apply_inventory()

        # Check Work order created or not
        self.assertEqual(len(production_table.workorder_ids), 1)

        # ---------------------------------------------------------
        # Process all workorder and check it state.
        # ----------------------------------------------------------

        workorder = production_table.workorder_ids[0]
        self.assertEqual(workorder.state, 'waiting', "workorder state should be waiting.")
        production_table.action_assign()

        # --------------------------------------------------------------
        # Process assembly line
        # ---------------------------------------------------------
        finished_lot = self.env['stock.lot'].create({'product_id': production_table.product_id.id, 'company_id': self.env.company.id})
        workorder.write({'finished_lot_id': finished_lot.id})
        workorder.button_start()
        workorder.qty_producing = 1.0
        for stock_move in workorder.move_raw_ids:
            if stock_move.product_id.id == product_bolt.id:
                stock_move.move_line_ids.write({'lot_id': lot_bolt.id, 'quantity': 1, 'picked': True})
            if stock_move.product_id.id == product_table_sheet.id:
                stock_move.move_line_ids.write({'lot_id': lot_sheet.id, 'quantity': 1, 'picked': True})
            if stock_move.product_id.id == product_table_leg.id:
                stock_move.move_line_ids.write({'lot_id': lot_leg.id, 'quantity': 1, 'picked': True})
        self.assertEqual(workorder.state, 'progress')

        workorder.record_production()
        self.assertEqual(workorder.state, 'done')
        move_table_sheet = production_table.move_raw_ids.filtered(lambda x: x.product_id == product_table_sheet)
        self.assertEqual(move_table_sheet.quantity, 1)

        # ---------------------------------------------------------------
        # Check consume quants and produce quants after posting inventory
        # ---------------------------------------------------------------
        production_table.move_raw_ids.picked = True
        production_table.button_mark_done()

        self.assertEqual(product_screw.qty_available, 10)
        self.assertEqual(product_bolt.qty_available, 19)
        self.assertEqual(product_table_leg.qty_available, 19)
        self.assertEqual(product_table_sheet.qty_available, 19)

    def test_00b_workorder_process(self):
        """ Testing consume quants and produced quants with workorder """
        dining_table = self.dining_table
        product_table_sheet = self.product_table_sheet
        product_table_leg = self.product_table_leg
        product_bolt = self.product_bolt

        # Set tracking lot on finish and consume products.
        dining_table.tracking = 'lot'
        product_table_sheet.tracking = 'lot'
        product_table_leg.tracking = 'lot'
        product_bolt.tracking = "lot"

        bom = self.mrp_bom_desk

        self.env['stock.move'].search([('product_id', '=', product_bolt.id)])._do_unreserve()

        bom.operation_ids = False
        bom.write({
            'operation_ids': [
                (0, 0, {
                    'workcenter_id': self.mrp_workcenter_1.id,
                    'name': 'Packing',
                    'time_cycle': 30,
                    'sequence': 5}),
                (0, 0, {
                    'workcenter_id': self.mrp_workcenter_3.id,
                    'name': 'Testing',
                    'time_cycle': 60,
                    'sequence': 10}),
                (0, 0, {
                    'workcenter_id': self.mrp_workcenter_3.id,
                    'name': 'Long time assembly',
                    'time_cycle': 180,
                    'sequence': 15}),
            ]
        })

        bom.bom_line_ids.filtered(lambda p: p.product_id == product_table_sheet).operation_id = bom.operation_ids[0]
        bom.bom_line_ids.filtered(lambda p: p.product_id == product_table_leg).operation_id = bom.operation_ids[1]
        bom.bom_line_ids.filtered(lambda p: p.product_id == product_bolt).operation_id = bom.operation_ids[2]

        production_table_form = Form(self.env['mrp.production'])
        production_table_form.product_id = dining_table
        production_table_form.bom_id = bom
        production_table_form.product_qty = 2.0
        production_table_form.product_uom_id = dining_table.uom_id
        production_table = production_table_form.save()
        production_table.action_confirm()
        # Initial inventory of product sheet, lags and bolt
        lot_sheet = self.env['stock.lot'].create({'product_id': product_table_sheet.id, 'company_id': self.env.company.id})
        lot_leg = self.env['stock.lot'].create({'product_id': product_table_leg.id, 'company_id': self.env.company.id})
        lot_bolt = self.env['stock.lot'].create({'product_id': product_bolt.id, 'company_id': self.env.company.id})

        # Initialize inventory
        # --------------------
        self.env['stock.quant'].create({
            'product_id': product_table_sheet.id,
            'inventory_quantity': 20,
            'lot_id': lot_sheet.id,
            'location_id': self.source_location_id
        }).action_apply_inventory()
        self.env['stock.quant'].create({
            'product_id': product_table_leg.id,
            'inventory_quantity': 20,
            'lot_id': lot_leg.id,
            'location_id': self.source_location_id
        }).action_apply_inventory()
        self.env['stock.quant'].create({
            'product_id': product_bolt.id,
            'inventory_quantity': 20,
            'lot_id': lot_bolt.id,
            'location_id': self.source_location_id
        }).action_apply_inventory()

        # Create work order
        production_table.button_plan()
        # Check Work order created or not
        self.assertEqual(len(production_table.workorder_ids), 3)

        # ---------------------------------------------------------
        # Process all workorder and check it state.
        # ----------------------------------------------------------

        workorders = production_table.workorder_ids
        self.assertEqual(workorders[0].state, 'waiting', "First workorder state should be waiting.")
        self.assertEqual(workorders[1].state, 'pending')
        self.assertEqual(workorders[2].state, 'pending')

        # --------------------------------------------------------------
        # Process cutting operation...
        # ---------------------------------------------------------
        production_table.action_assign()

        finished_lot = self.env['stock.lot'].create({'product_id': production_table.product_id.id, 'company_id': self.env.company.id})
        workorders[0].write({'finished_lot_id': finished_lot.id, 'qty_producing': 1.0})
        workorders[0].button_start()
        move_table_sheet = production_table.move_raw_ids.filtered(lambda p: p.product_id == product_table_sheet)
        move_table_sheet.move_line_ids.write({'lot_id': lot_sheet.id, 'quantity': 1, 'picked': True})
        self.assertEqual(workorders[0].state, 'progress')

        workorders[0].record_production()

        self.assertEqual(move_table_sheet.quantity, 1)

        # --------------------------------------------------------------
        # Process drilling operation ...
        # ---------------------------------------------------------
        workorders[1].button_start()
        move_leg = production_table.move_raw_ids.filtered(lambda p: p.product_id == product_table_leg)
        move_leg.move_line_ids.write({'lot_id': lot_leg.id, 'quantity': 4, 'picked': True})
        workorders[1].record_production()
        self.assertEqual(workorders[1].state, 'done')
        self.assertEqual(move_leg.quantity, 4)

        # --------------------------------------------------------------
        # Process fitting operation ...
        # ---------------------------------------------------------
        workorders[2].button_start()
        workorders[2].qty_producing = 1.0
        move_table_bolt = production_table.move_raw_ids.filtered(lambda p: p.product_id.id == product_bolt.id)
        move_table_bolt.move_line_ids.write({'lot_id': lot_bolt.id, 'quantity': 4, 'picked': True})
        workorders[2].record_production()
        self.assertEqual(move_table_bolt.quantity, 4)

        # Change the quantity of the production order to 1
        wiz = self.env['change.production.qty'].create({
            'mo_id': production_table.id,
            'product_qty': 1.0
        })
        wiz.change_prod_qty()
        # ---------------------------------------------------------------
        # Check consume quants and produce quants after posting inventory
        # ---------------------------------------------------------------
        production_table.move_raw_ids.picked = True
        production_table._post_inventory()
        self.assertEqual(sum(move_table_sheet.mapped('quantity')), 1, "Wrong quantity of consumed product %s" % move_table_sheet.product_id.name)
        self.assertEqual(sum(move_leg.mapped('quantity')), 4, "Wrong quantity of consumed product %s" % move_leg.product_id.name)
        self.assertEqual(sum(move_table_bolt.mapped('quantity')), 4, "Wrong quantity of consumed product %s" % move_table_bolt.product_id.name)

    def test_explode_from_order(self):
        # bom3 produces 2 Dozen of Doors (p6), aka 24
        # To produce 24 Units of Doors (p6)
        # - 2 Units of Tools (p5) -> need 4
        # - 8 Dozen of Sticks (p4) -> need 16
        # - 12 Units of Wood (p2) -> need 24
        # bom2 produces 1 Unit of Tools (p5)
        # To produce 1 Unit of Tools (p5)
        # - 2 Dozen of Sticks (p4) -> need 8
        # - 3 Dozen of Stones (p3) -> need 12

        # Update capacity, start time, stop time, and time efficiency.
        # ------------------------------------------------------------
        self.workcenter_1.write({'default_capacity': 1, 'time_start': 0, 'time_stop': 0, 'time_efficiency': 100})

        # Set manual time cycle 20 and 10.
        # --------------------------------
        self.bom_3.operation_ids[0].time_cycle_manual = 10
        self.bom_3.operation_ids[1].time_cycle_manual = 10
        self.bom_2.operation_ids.time_cycle_manual = 20
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
        self.assertEqual(len(man_order.move_raw_ids), 4, "Consume material lines are not generated properly.")
        product_2_consume_moves = man_order.move_raw_ids.filtered(lambda x: x.product_id == self.product_2)
        product_3_consume_moves = man_order.move_raw_ids.filtered(lambda x: x.product_id == self.product_3)
        product_4_consume_moves = man_order.move_raw_ids.filtered(lambda x: x.product_id == self.product_4)
        product_5_consume_moves = man_order.move_raw_ids.filtered(lambda x: x.product_id == self.product_5)
        consume_qty_2 = product_2_consume_moves.product_uom_qty
        self.assertEqual(consume_qty_2, 24.0, "Consume material quantity of Wood should be 24 instead of %s" % str(consume_qty_2))
        consume_qty_3 = product_3_consume_moves.product_uom_qty
        self.assertEqual(consume_qty_3, 12.0, "Consume material quantity of Stone should be 12 instead of %s" % str(consume_qty_3))
        self.assertEqual(len(product_4_consume_moves), 2, "Consume move are not generated properly.")
        self.assertEqual(sum(product_4_consume_moves.mapped('product_uom_qty')), 24, "Consume material quantity of Stick should be 24.")
        self.assertFalse(product_5_consume_moves, "Move should not create for phantom bom")

        # create required lots
        lot_product_2 = self.env['stock.lot'].create({'product_id': self.product_2.id, 'company_id': self.env.company.id})
        lot_product_4 = self.env['stock.lot'].create({'product_id': self.product_4.id, 'company_id': self.env.company.id})

        # refuel stock
        self.env['stock.quant'].create({
            'product_id': self.product_2.id,
            'inventory_quantity': 30,
            'lot_id': lot_product_2.id,
            'location_id': self.stock_location_14.id
        }).action_apply_inventory()
        self.env['stock.quant'].create({
            'product_id': self.product_3.id,
            'inventory_quantity': 60,
            'location_id': self.stock_location_14.id
        }).action_apply_inventory()
        self.env['stock.quant'].create({
            'product_id': self.product_4.id,
            'inventory_quantity': 60,
            'lot_id': lot_product_4.id,
            'location_id': self.stock_location_14.id
        }).action_apply_inventory()

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
        kit_wo = man_order.workorder_ids.filtered(lambda wo: wo.operation_id.name == "Gift Wrap Maching")
        door_wo_1 = man_order.workorder_ids.filtered(lambda wo: wo.operation_id.name == "Cutting Machine")
        door_wo_2 = man_order.workorder_ids.filtered(lambda wo: wo.operation_id.name == "Weld Machine")
        workorders._compute_state()
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
        finished_lot = self.env['stock.lot'].create({'product_id': man_order.product_id.id, 'company_id': self.env.company.id})
        kit_wo.write({
            'finished_lot_id': finished_lot.id,
            'qty_producing': 48
        })

        kit_wo.record_production()

        self.assertEqual(kit_wo.state, 'done', "Workorder should be in done state.")

        # first operation of main bom
        finished_lot = self.env['stock.lot'].create({'product_id': man_order.product_id.id, 'company_id': self.env.company.id})
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
        custom_laptop = self.env['product.product'].create({
            'name': 'Drawer',
            'type': 'product',
            'tracking': 'lot',
        })

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
            'consumption': 'flexible',
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

        lot_charger = self.env['stock.lot'].create({'product_id': product_charger.id, 'company_id': self.env.company.id})
        lot_keybord = self.env['stock.lot'].create({'product_id': product_keybord.id, 'company_id': self.env.company.id})

        # Initialize Inventory
        # --------------------
        self.env['stock.quant'].create({
            'product_id': product_charger.id,
            'inventory_quantity': 20,
            'lot_id': lot_charger.id,
            'location_id': self.source_location_id
        }).action_apply_inventory()
        self.env['stock.quant'].create({
            'product_id': product_keybord.id,
            'inventory_quantity': 20,
            'lot_id': lot_keybord.id,
            'location_id': self.source_location_id
        }).action_apply_inventory()

        # Check consumed move status
        mo_custom_laptop.action_assign()
        self.assertEqual(mo_custom_laptop.reservation_state, 'assigned')

        # Check current status of raw materials.
        for move in mo_custom_laptop.move_raw_ids:
            self.assertEqual(move.product_uom_qty, 20, "Wrong consume quantity of raw material %s: %s instead of %s" % (move.product_id.name, move.product_uom_qty, 20))
            self.assertEqual(move.quantity, 20, "Wrong produced quantity on raw material %s: %s instead of 20" % (move.product_id.name, move.quantity))
            self.assertFalse(move.picked)

        # -----------------
        # Start production
        # -----------------

        # Produce 6 Unit of custom laptop will consume ( 12 Unit of keybord and 12 Unit of charger)
        laptop_lot_001 = self.env['stock.lot'].create({'product_id': custom_laptop.id, 'company_id': self.env.company.id})
        mo_form = Form(mo_custom_laptop)
        mo_form.qty_producing = 6
        mo_form.lot_producing_id = laptop_lot_001
        mo_custom_laptop = mo_form.save()
        details_operation_form = Form(mo_custom_laptop.move_raw_ids[0], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.quantity = 12
        details_operation_form.save()
        details_operation_form = Form(mo_custom_laptop.move_raw_ids[1], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.quantity = 12
        details_operation_form.save()

        mo_custom_laptop.move_raw_ids.picked = True
        action = mo_custom_laptop.button_mark_done()
        backorder = Form(self.env[action['res_model']].with_context(**action['context']))
        backorder.save().action_backorder()

        # Check consumed move after produce 6 quantity of customized laptop.
        for move in mo_custom_laptop.move_raw_ids:
            self.assertEqual(move.quantity, 12, "Wrong produced quantity on raw material %s" % (move.product_id.name))
        self.assertEqual(len(mo_custom_laptop.move_raw_ids), 2)

        # Check done move and confirmed move quantity.
        charger_done_move = mo_custom_laptop.move_raw_ids.filtered(lambda x: x.product_id.id == product_charger.id and x.state == 'done')
        keybord_done_move = mo_custom_laptop.move_raw_ids.filtered(lambda x: x.product_id.id == product_keybord.id and x.state == 'done')
        self.assertEqual(charger_done_move.product_uom_qty, 12)
        self.assertEqual(keybord_done_move.product_uom_qty, 12)

        # Produce remaining 4 quantity
        # ----------------------------

        # Produce 4 Unit of custom laptop will consume ( 8 Unit of keybord and 8 Unit of charger).
        laptop_lot_002 = self.env['stock.lot'].create({'product_id': custom_laptop.id, 'company_id': self.env.company.id})
        mo_custom_laptop = mo_custom_laptop.procurement_group_id.mrp_production_ids[1]
        mo_form = Form(mo_custom_laptop)
        mo_form.qty_producing = 4
        mo_form.lot_producing_id = laptop_lot_002
        mo_custom_laptop = mo_form.save()
        details_operation_form = Form(mo_custom_laptop.move_raw_ids[0], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.quantity = 8
        details_operation_form.save()
        details_operation_form = Form(mo_custom_laptop.move_raw_ids[1], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.quantity = 8
        details_operation_form.save()

        charger_move = mo_custom_laptop.move_raw_ids.filtered(lambda x: x.product_id.id == product_charger.id and x.state != 'done')
        keybord_move = mo_custom_laptop.move_raw_ids.filtered(lambda x: x.product_id.id == product_keybord.id and x.state !='done')
        self.assertEqual(charger_move.quantity, 8, "Wrong consumed quantity of %s" % charger_move.product_id.name)
        self.assertEqual(keybord_move.quantity, 8, "Wrong consumed quantity of %s" % keybord_move.product_id.name)

    def test_03_test_serial_number_defaults(self):
        """ Test that the correct serial number is suggested on consecutive work orders. """
        laptop = self.laptop
        graphics_card = self.graphics_card
        unit = self.env.ref("uom.product_uom_unit")
        stock_location = self.env.ref('stock.stock_location_stock')
        self.env['stock.quant']._update_available_quantity(graphics_card, stock_location, 20)

        laptop.tracking = 'serial'

        bom_laptop = self.env['mrp.bom'].create({
            'product_tmpl_id': laptop.product_tmpl_id.id,
            'product_qty': 1,
            'product_uom_id': unit.id,
            'consumption': 'flexible',
            'bom_line_ids': [(0, 0, {
                'product_id': graphics_card.id,
                'product_qty': 1,
                'product_uom_id': unit.id
            })],
            'operation_ids': [
                (0, 0, {
                    'workcenter_id': self.mrp_workcenter_1.id,
                    'name': 'Packing',
                    'time_cycle': 30,
                    'sequence': 5}),
                (0, 0, {
                    'workcenter_id': self.mrp_workcenter_3.id,
                    'name': 'Testing',
                    'time_cycle': 60,
                    'sequence': 10}),
                (0, 0, {
                    'workcenter_id': self.mrp_workcenter_3.id,
                    'name': 'Long time assembly',
                    'time_cycle': 180,
                    'sequence': 15}),
            ],
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

        workorders[0].open_tablet_view()
        workorder = workorders[0]
        serial_a = self.env['stock.lot'].create({'product_id': laptop.id, 'company_id': self.env.company.id})
        workorder.finished_lot_id = serial_a
        workorder = self.env['mrp.workorder'].browse(workorder.record_production()['res_id'])
        self.assertTrue(workorder)
        serial_b = self.env['stock.lot'].create({'product_id': laptop.id, 'company_id': self.env.company.id})
        workorder.finished_lot_id = serial_b
        workorder = self.env['mrp.workorder'].browse(workorder.record_production()['res_id'])
        serial_c = self.env['stock.lot'].create({'product_id': laptop.id, 'company_id': self.env.company.id})
        workorder.finished_lot_id = serial_c
        workorder.record_production()
        self.assertEqual(workorders[0].state, 'done')

        for workorder in workorders - workorders[0]:
            workorder.button_start()
            self.assertEqual(workorder.finished_lot_id, serial_a)
            workorder = self.env['mrp.workorder'].browse(workorder.record_production()['res_id'])
            self.assertEqual(workorder.finished_lot_id, serial_b)
            workorder = self.env['mrp.workorder'].browse(workorder.record_production()['res_id'])
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
        drawer = self.env['product.product'].create({
            'name': 'Drawer',
            'type': 'product',
            'tracking': 'lot',
        })
        drawer_drawer = self.env['product.product'].create({
            'name': 'Drawer Black',
            'type': 'product',
            'tracking': 'lot',
        })
        drawer_case = self.env['product.product'].create({
            'name': 'Drawer Case Black',
            'type': 'product',
            'tracking': 'lot',
        })
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': drawer.product_tmpl_id.id,
            'product_uom_id': self.env.ref('uom.product_uom_unit').id,
            'consumption': 'flexible',
            'sequence': 2,
            'operation_ids': [
                (0, 0, {
                    'workcenter_id': self.mrp_workcenter_1.id,
                    'name': 'Packing',
                    'time_cycle': 30,
                    'sequence': 5}),
                (0, 0, {
                    'workcenter_id': self.mrp_workcenter_3.id,
                    'name': 'Testing',
                    'time_cycle': 60,
                    'sequence': 10}),
                (0, 0, {
                    'workcenter_id': self.mrp_workcenter_3.id,
                    'name': 'Long time assembly',
                    'time_cycle': 180,
                    'sequence': 15}),
            ],
            'bom_line_ids': [(0, 0, {
                'product_id': drawer_drawer.id,
                'product_qty': 1,
                'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                'sequence': 1,
            }), (0, 0, {
                'product_id': drawer_case.id,
                'product_qty': 1,
                'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                'sequence': 2,
            })]
        })
        drawer_drawer_lot = self.env['stock.lot'].create({
            'product_id': drawer_drawer.id,
            'name': 'dd0001',
            'company_id': self.env.company.id,
        })

        drawer_case_lot = self.env['stock.lot'].create({
            'product_id': drawer_case.id,
            'name': 'dc0001',
            'company_id': self.env.company.id,
        })
        self.env['stock.quant'].create({
            'product_id': drawer_drawer.id,
            'inventory_quantity': 50.0,
            'location_id': self.stock_location_14.id,
            'lot_id': drawer_drawer_lot.id,
        }).action_apply_inventory()
        self.env['stock.quant'].create({
            'product_id': drawer_case.id,
            'inventory_quantity': 50.0,
            'location_id': self.stock_location_14.id,
            'lot_id': drawer_case_lot.id,
        }).action_apply_inventory()

        product = bom.product_tmpl_id.product_variant_id
        product.tracking = 'serial'

        lot_1 = self.env['stock.lot'].create({
            'product_id': product.id,
            'name': 'LOT000001',
            'company_id': self.env.company.id,
        })

        lot_2 = self.env['stock.lot'].create({
            'product_id': product.id,
            'name': 'LOT000002',
            'company_id': self.env.company.id,
        })
        self.env['stock.lot'].create({
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
        workorder_0.open_tablet_view()
        workorder_0 = self.env['mrp.workorder'].browse(workorder_0.record_production()['res_id'])
        workorder_0.record_production()

        workorder_1 = mo.workorder_ids[1]
        workorder_1.button_start()
        # `finished_lot_id` is invisible in the view
        # however, it's a computed field
        # `workorder.finished_lot_id = workorder.production_id.lot_producing_id`
        with Form(workorder_1.production_id) as wo_production:
            wo_production.lot_producing_id = lot_1
        workorder_1 = self.env['mrp.workorder'].browse(workorder_1.record_production()['res_id'])

        with Form(workorder_1.production_id) as wo_production:
            wo_production.lot_producing_id = lot_2
        workorder_1.record_production()

        workorder_2 = mo.workorder_ids[2]
        self.assertEqual(workorder_2.finished_lot_id, lot_1)

        productions = workorder_1.production_id.procurement_group_id.mrp_production_ids
        self.assertEqual(sum(productions.mapped('qty_producing')), 2)
        self.assertEqual(productions.lot_producing_id, lot_1 | lot_2)
        for production in productions:
            production._post_inventory()
        self.assertEqual(sum(productions.move_finished_ids.move_line_ids.mapped('quantity')), 2)
        self.assertEqual(productions.move_finished_ids.move_line_ids.mapped('lot_id'), lot_1 | lot_2)

    def test_04_test_planning_date(self):
        """ Test that workorder are planned at the correct time. """
        # The workcenter is working 24/7
        self.full_availability()

        dining_table = self.dining_table

        production_table_form = Form(self.env['mrp.production'])
        production_table_form.product_id = dining_table
        production_table_form.bom_id = self.mrp_bom_desk
        production_table_form.product_qty = 1.0
        production_table_form.product_uom_id = dining_table.uom_id
        production_table = production_table_form.save()
        production_table.action_confirm()

        # Create work order
        production_table.button_plan()
        workorder = production_table.workorder_ids[0]

        # Check that the workorder is planned now and that it lasts one hour
        self.assertAlmostEqual(workorder.date_start, datetime.now(), delta=timedelta(seconds=10), msg="Workorder should be planned now.")
        self.assertAlmostEqual(workorder.date_finished, datetime.now() + timedelta(hours=1), delta=timedelta(seconds=10), msg="Workorder should be done in an hour.")

    def test_04b_test_planning_date(self):
        """ Test that workorder are planned at the correct time when setting a start date """
        # The workcenter is working 24/7
        self.full_availability()

        dining_table = self.dining_table

        date_start = datetime.now() + timedelta(days=1)

        production_table_form = Form(self.env['mrp.production'])
        production_table_form.product_id = dining_table
        production_table_form.bom_id = self.mrp_bom_desk
        production_table_form.product_qty = 1.0
        production_table_form.product_uom_id = dining_table.uom_id
        production_table_form.date_start = date_start
        production_table = production_table_form.save()
        production_table.action_confirm()

        # Create work order
        production_table.button_plan()

        workorder = production_table.workorder_ids[0]

        # Check that the workorder is planned now and that it lasts one hour
        self.assertAlmostEqual(workorder.date_start, date_start, delta=timedelta(seconds=1), msg="Workorder should be planned tomorrow.")
        self.assertAlmostEqual(workorder.date_finished, date_start + timedelta(hours=1), delta=timedelta(seconds=1), msg="Workorder should be done one hour later.")

    def test_unlink_workorder(self):
        drawer = self.env['product.product'].create({
            'name': 'Drawer',
            'type': 'product',
            'tracking': 'lot',
        })
        drawer_drawer = self.env['product.product'].create({
            'name': 'Drawer Black',
            'type': 'product',
            'tracking': 'lot',
        })
        drawer_case = self.env['product.product'].create({
            'name': 'Drawer Case Black',
            'type': 'product',
            'tracking': 'lot',
        })
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': drawer.product_tmpl_id.id,
            'product_uom_id': self.env.ref('uom.product_uom_unit').id,
            'consumption': 'flexible',
            'sequence': 2,
            'operation_ids': [
                (0, 0, {
                    'workcenter_id': self.mrp_workcenter_1.id,
                    'name': 'Packing',
                    'time_cycle': 30,
                    'sequence': 5}),
                (0, 0, {
                    'workcenter_id': self.mrp_workcenter_3.id,
                    'name': 'Testing',
                    'time_cycle': 60,
                    'sequence': 10}),
                (0, 0, {
                    'workcenter_id': self.mrp_workcenter_3.id,
                    'name': 'Long time assembly',
                    'time_cycle': 180,
                    'sequence': 15}),
            ],
            'bom_line_ids': [(0, 0, {
                'product_id': drawer_drawer.id,
                'product_qty': 1,
                'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                'sequence': 1,
            }), (0, 0, {
                'product_id': drawer_case.id,
                'product_qty': 1,
                'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                'sequence': 2,
            })]
        })

        production_table_form = Form(self.env['mrp.production'])
        production_table_form.product_id = drawer
        production_table_form.bom_id = bom
        production_table_form.product_qty = 2.0
        production_table_form.product_uom_id = drawer.uom_id
        production_table = production_table_form.save()
        production_table.action_confirm()

        production_table.button_plan()

        self.assertEqual(len(production_table.workorder_ids), 3)

        workorders = production_table.workorder_ids

        for i in range(len(workorders) - 1):
            self.assertEqual(workorders[i].needed_by_workorder_ids, workorders[i + 1])

        production_table.workorder_ids[1].unlink()

        self.assertEqual(len(production_table.workorder_ids), 2)

        workorders = production_table.workorder_ids
        for i in range(len(workorders) - 1):
            self.assertEqual(workorders[i].needed_by_workorder_ids, workorders[i + 1])

    def test_planning_overlaps_wo(self):
        """ Test that workorder doesn't overlaps between then when plan the MO """
        self.full_availability()

        dining_table = self.dining_table

        # Take between +30min -> +90min
        date_start = datetime.now() + timedelta(minutes=30)

        production_table_form = Form(self.env['mrp.production'])
        production_table_form.product_id = dining_table
        production_table_form.bom_id = self.mrp_bom_desk
        production_table_form.product_qty = 1.0
        production_table_form.product_uom_id = dining_table.uom_id
        production_table_form.date_start = date_start
        production_table = production_table_form.save()
        production_table.action_confirm()

        # Create work order
        production_table.button_plan()
        workorder_prev = production_table.workorder_ids[0]

        # Check that the workorder is planned now and that it lasts one hour
        self.assertAlmostEqual(workorder_prev.date_start, date_start, delta=timedelta(seconds=10), msg="Workorder should be planned in +30min")
        self.assertAlmostEqual(workorder_prev.date_finished, date_start + timedelta(hours=1), delta=timedelta(seconds=10), msg="Workorder should be done in +90min")

        # As soon as possible, but because of the first one, it will planned only after +90 min
        date_start = datetime.now()

        production_table_form = Form(self.env['mrp.production'])
        production_table_form.product_id = dining_table
        production_table_form.bom_id = self.mrp_bom_desk
        production_table_form.product_qty = 1.0
        production_table_form.product_uom_id = dining_table.uom_id
        production_table_form.date_start = date_start
        production_table = production_table_form.save()
        production_table.action_confirm()

        # Create work order
        production_table.button_plan()
        workorder = production_table.workorder_ids[0]

        # Check that the workorder is planned now and that it lasts one hour
        self.assertAlmostEqual(workorder.date_start, workorder_prev.date_finished, delta=timedelta(seconds=10), msg="Workorder should be planned after the first one")
        self.assertAlmostEqual(workorder.date_finished, workorder_prev.date_finished + timedelta(hours=1), delta=timedelta(seconds=10), msg="Workorder should be done one hour later.")

    @freeze_time('2021-12-01')
    def test_planning_overlaps_wo_02(self):
        """ Test that workorder doesn't overlaps between then when plan the MO

            here is the expected result:
                MO1 : 01/dec/2021 00:00 → 01/dec/2021 00:24
                MO2 : 01/dec/2021 00:24 → 01/dec/2021 00:48
                MO3 : 02/dec/2021 00:00 → 02/dec/2021 00:24
                MO4 : 02/dec/2021 00:24 → 02/dec/2021 00:48
                MO5 : 02/dec/2021 00:48 → 03/dec/2021 00:12
        """
        self.full_availability()
        calendar = self.env['resource.calendar'].search([])
        # Possible working hours: every day from 00:00 to 01:00 (UTC)
        calendar.attendance_ids.hour_to = 1
        calendar.tz = 'UTC'

        dining_table = self.dining_table
        # Set the work order duration to 24 minutes
        dining_table.bom_ids.operation_ids[0].time_cycle_manual = 24

        # Set the date_start to 01/12/2021 00:00
        date_start = datetime.today()

        # Create 5 MO. one of them has a different date from the others
        all_production = self.env['mrp.production']
        for date in [date_start, date_start, (date_start + timedelta(days=1)), date_start, date_start]:
            production_table_form = Form(self.env['mrp.production'])
            production_table_form.product_id = dining_table
            production_table_form.bom_id = self.mrp_bom_desk
            production_table_form.product_qty = 1.0
            production_table_form.product_uom_id = dining_table.uom_id
            production_table_form.date_start = date
            all_production += production_table_form.save()

        all_production.action_confirm()
        all_production.button_plan()

        workorder_a = all_production[3].workorder_ids[0]
        workorder_b = all_production[4].workorder_ids[0]

        # Check that the workorders are planned correctly and that it lasts 24 minutes
        self.assertAlmostEqual(workorder_a.date_start, (date_start + timedelta(days=1, minutes=24)), delta=timedelta(seconds=10), msg="The workorder should be planned for the first available interval")
        self.assertAlmostEqual(workorder_a.date_finished, (date_start + timedelta(days=1, minutes=48)), delta=timedelta(seconds=10), msg="Workorder should be done in 24 minutes")
        self.assertAlmostEqual(workorder_b.date_start, (date_start + timedelta(days=1, minutes=48)), delta=timedelta(seconds=10), msg="The workorder should be planned for the first available interval")
        self.assertAlmostEqual(workorder_b.date_finished, (date_start + timedelta(days=2, minutes=12)), delta=timedelta(seconds=10), msg="Workorder should be done in 24 minutes")

    def test_change_production_1(self):
        """Change the quantity to produce on the MO while workorders are already planned."""
        dining_table = self.dining_table
        dining_table.tracking = 'lot'
        production_table_form = Form(self.env['mrp.production'])
        production_table_form.product_id = dining_table
        production_table_form.bom_id = self.mrp_bom_desk
        production_table_form.product_qty = 1.0
        production_table_form.product_uom_id = dining_table.uom_id
        production_table = production_table_form.save()
        production_table.action_confirm()
        mo_form = Form(production_table)
        mo_form.qty_producing = 1
        production_table = mo_form.save()

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
        Plan 6 times the same MO, the workorders should be split across workcenters
        The 3 workcenters are free, this test plans 3 workorder in a row then three next.
        The workcenters have not exactly the same parameters (efficiency, start time) so the
        the last 3 workorder are not dispatched like the 3 first.
        At the end of the test, the calendars will look like:
            - calendar wc1 :[mo1][mo4]
            - calendar wc2 :[mo2 ][mo5 ]
            - calendar wc3 :[mo3  ][mo6  ]"""
        self.full_availability()
        date = datetime.now() + timedelta(minutes=30)
        self.workcenter_1.alternative_workcenter_ids = self.wc_alt_1 | self.wc_alt_2
        workcenters = [self.wc_alt_2, self.wc_alt_1, self.workcenter_1]
        for i in range(3):
            # Create an MO for product4
            mo_form = Form(self.env['mrp.production'])
            mo_form.product_id = self.product_4
            mo_form.bom_id = self.planning_bom
            mo_form.product_qty = 1
            mo_form.date_start = date
            mo = mo_form.save()
            mo.action_confirm()
            mo.button_plan()
            # Check that workcenters change
            self.assertEqual(mo.workorder_ids.workcenter_id, workcenters[i], "wrong workcenter %d" % i)
            self.assertAlmostEqual(mo.date_start, date, delta=timedelta(seconds=10))
            self.assertAlmostEqual(mo.date_start, mo.workorder_ids.date_start, delta=timedelta(seconds=10))

        for i in range(3):
            # Planning 3 more should choose workcenters in opposite order as
            # - wc_alt_2 as the best efficiency
            # - wc_alt_1 take a little less start time
            # - workcenter_1 is the worst
            mo_form = Form(self.env['mrp.production'])
            mo_form.product_id = self.product_4
            mo_form.bom_id = self.planning_bom
            mo_form.product_qty = 1
            mo_form.date_start = date
            mo = mo_form.save()
            mo.action_confirm()
            mo.button_plan()
            # Check that workcenters change
            self.assertEqual(mo.workorder_ids.workcenter_id, workcenters[i], "wrong workcenter %d" % i)
            self.assertNotEqual(mo.date_start, date)
            self.assertAlmostEqual(mo.date_start, mo.workorder_ids.date_start, delta=timedelta(seconds=10))

    def test_planning_3(self):
        """ Plan some manufacturing orders with 1 workorder on 1 workcenter
        the first workorder will be hard set in the future to see if the second
        one take the free slot before on the calendar
        calendar after first mo : [   ][mo1]
        calendar after second mo: [mo2][mo1] """

        self.full_availability()
        self.workcenter_1.alternative_workcenter_ids = self.wc_alt_1 | self.wc_alt_2
        self.env['mrp.workcenter'].search([]).resource_calendar_id.write({'tz': 'UTC'})  # compute all date in UTC

        date = datetime.now() + timedelta(days=2)
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_4
        mo_form.bom_id = self.planning_bom
        mo_form.product_qty = 1
        mo_form.date_start = date
        mo = mo_form.save()
        start = mo.date_start
        mo.action_confirm()
        mo.button_plan()
        self.assertEqual(mo.workorder_ids[0].workcenter_id, self.wc_alt_2, "wrong workcenter")
        wo1_start = mo.workorder_ids[0].date_start
        wo1_finished = mo.workorder_ids[0].date_finished
        self.assertAlmostEqual(wo1_start, start, delta=timedelta(seconds=10), msg="Wrong plannification")
        self.assertAlmostEqual(wo1_finished, start + timedelta(minutes=85.58), delta=timedelta(seconds=10), msg="Wrong plannification")

        # second MO should be plan before as there is a free slot before
        date = date - timedelta(days=1)
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_4
        mo_form.bom_id = self.planning_bom
        mo_form.product_qty = 1
        mo_form.date_start = date
        mo = mo_form.save()
        mo.action_confirm()
        mo.button_plan()
        self.assertEqual(mo.workorder_ids[0].workcenter_id, self.wc_alt_2, "wrong workcenter")
        wo1_start = mo.workorder_ids[0].date_start
        wo1_finished = mo.workorder_ids[0].date_finished
        self.assertAlmostEqual(wo1_start, date, delta=timedelta(seconds=10), msg="Wrong plannification")
        self.assertAlmostEqual(wo1_finished, date + timedelta(minutes=85.59), delta=timedelta(seconds=10), msg="Wrong plannification")

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
        self.assertEqual(len(mo.workorder_ids.mapped('leave_id')), 0)

    def test_planning_6(self):
        """ Marking a workorder as done before the theoretical date should update
        the reservation slot in the calendar the be able to reserve the next
        production sooner """
        self.env['mrp.workcenter'].search([]).write({'tz': 'UTC'})  # compute all date in UTC
        self.full_availability()
        mrp_workcenter_3 = self.env['mrp.workcenter'].create({
            'name': 'assembly line 1',
            'resource_calendar_id': self.env.ref('resource.resource_calendar_std').id,
        })
        self.planning_bom.operation_ids = False
        self.planning_bom.write({
            'operation_ids': [(0, 0, {
                'workcenter_id': mrp_workcenter_3.id,
                'name': 'Manual Assembly',
                'time_cycle': 60,
            })]
        })
        self.planning_bom.operation_ids = False
        self.planning_bom.write({
            'operation_ids': [(0, 0, {
                'workcenter_id': mrp_workcenter_3.id,
                'name': 'Manual Assembly',
                'time_cycle': 60,
            })]
        })
        date = datetime.now() + timedelta(days=2)
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_4
        mo_form.bom_id = self.planning_bom
        mo_form.product_qty = 1
        mo_form.date_start = date
        mo = mo_form.save()
        mo.action_confirm()
        mo.button_plan()
        wo = mo.workorder_ids
        self.assertAlmostEqual(wo.date_start, date, delta=timedelta(seconds=10))
        self.assertAlmostEqual(wo.date_finished, date + timedelta(minutes=60), delta=timedelta(seconds=10))
        wo.button_start()
        wo.qty_producing = 1.0
        wo.record_production()
        # Marking workorder as done should change the finished date
        self.assertAlmostEqual(wo.date_finished, datetime.now(), delta=timedelta(seconds=10))

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_4
        mo_form.bom_id = self.planning_bom
        mo_form.product_qty = 1
        mo_form.date_start = date
        mo = mo_form.save()
        mo.action_confirm()
        mo.button_plan()
        wo = mo.workorder_ids
        wo.button_start()
        self.assertAlmostEqual(wo.date_start, datetime.now(), delta=timedelta(seconds=10))

    def test_planning_7(self):
        """ set the workcenter capacity to 10. Produce a dozen of product tracked by
        SN. The production should be done in two batches"""
        self.workcenter_1.default_capacity = 10
        self.workcenter_1.time_efficiency = 100
        self.workcenter_1.time_start = 0
        self.workcenter_1.time_stop = 0
        self.planning_bom.operation_ids.time_cycle = 60
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

    def test_planning_7_with_product_capacity(self):
        """ Set the workcenter capacity to 10 by default and 12 on product.
        Produce a dozen of product tracked by SN.
        The production should be done in only 1 batch
        -> Reproduce test_planning_7 with specific product capacity
        """
        self.workcenter_1.default_capacity = 10
        self.workcenter_1.capacity_ids = [Command.create({'product_id': self.product_4.id, 'capacity': 12})]
        self.workcenter_1.time_efficiency = 100
        self.workcenter_1.time_start = 0
        self.workcenter_1.time_stop = 0
        self.planning_bom.operation_ids.time_cycle = 60
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_4
        mo_form.bom_id = self.planning_bom
        mo_form.product_uom_id = self.uom_dozen
        mo_form.product_qty = 1
        mo = mo_form.save()
        mo.action_confirm()
        mo.button_plan()
        wo = mo.workorder_ids
        self.assertEqual(wo.duration_expected, 60)

    @freeze_time('2022-8-08')
    def test_planning_8(self):
        """ Plan a workorder and move it on the planning, the workorder duration
        should always be consistent with the planned start and finish date"""
        self.env['mrp.workcenter'].search([]).write({'tz': 'UTC'})
        self.env['resource.calendar'].search([]).write({'tz': 'UTC'})
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_4
        self.planning_bom.operation_ids.time_cycle_manual = 120.0
        mo_form.bom_id = self.planning_bom
        mo_form.product_qty = 1
        mo_form.date_start = datetime(2022, 8, 8, 11, 0, 0, 0)
        mo = mo_form.save()
        mo.action_confirm()
        mo.button_plan()
        wo = mo.workorder_ids
        wc = wo.workcenter_id
        self.assertEqual(wo.date_start, datetime(2022, 8, 8, 11, 0, 0, 0),
                         "Date start should not have changed")
        self.assertEqual(wo.duration_expected, (120.0 * 100 / wc.time_efficiency) + wc.time_start + wc.time_stop,
                         "Duration expected should be the sum of the time_cycle (taking the workcenter efficiency into account), the time_start and time_stop")
        self.assertEqual(wo.date_finished, wo.date_start + timedelta(minutes=wo.duration_expected + 60),
                         "Date finished should take into consideration the midday break")
        duration_expected = wo.duration_expected

        # Move the workorder in the planning so that it doesn't span across the midday break
        wo.write({'date_start': datetime(2022, 8, 8, 9, 0, 0, 0), 'date_finished': datetime(2022, 8, 8, 12, 45, 0, 0)})
        self.assertEqual(wo.date_start, datetime(2022, 8, 8, 9, 0, 0, 0),
                         "Date start should have changed")
        self.assertEqual(wo.duration_expected, duration_expected,
                         "Duration expected should not have changed")
        self.assertEqual(wo.date_finished, wo.date_start + timedelta(minutes=duration_expected),
                         "Date finished should have been recomputed to be consistent with the workorder duration")
        date_finished = wo.date_finished

        # Extend workorder one hour to the left
        wo.write({'date_start': datetime(2022, 8, 8, 8, 0, 0, 0)})
        self.assertEqual(wo.date_start, datetime(2022, 8, 8, 8, 0, 0, 0),
                         "Date start should have changed")
        self.assertEqual(wo.duration_expected, duration_expected + 60,
                         "Duration expected should have been extended by one hour")
        self.assertEqual(wo.date_finished, date_finished,
                         "Date finished should not have changed")
        self.assertEqual(wo.date_finished, wo.date_start + timedelta(minutes=wo.duration_expected),
                         "Date finished should be consistent with the workorder duration")
        duration_expected = wo.duration_expected

        # Extend workorder 2 hours to the right (span across the midday break)
        wo.write({'date_finished': datetime(2022, 8, 8, 13, 45, 0, 0)})
        self.assertEqual(wo.date_start, datetime(2022, 8, 8, 8, 0, 0, 0),
                         "Date start should not have changed")
        self.assertEqual(wo.duration_expected, duration_expected + 60,
                         "Duration expected should have been extended by one hour")
        self.assertEqual(wo.date_finished, datetime(2022, 8, 8, 13, 45, 0, 0),
                         "Date finished should have changed")
        self.assertEqual(wo.date_finished, wo.date_start + timedelta(minutes=wo.duration_expected + 60),
                         "Date finished should be consistent with the workorder duration")

    @freeze_time('2022-10-10 07:45')
    def test_planning_9(self):
        """ Plan a workorder and edit the scheduled start date, when we start
        the workorder, the scheduled finish date should be updated"""
        self.env.ref('base.group_user').write({'implied_ids': [(4, self.env.ref('mrp.group_mrp_routings').id)]})
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_4
        mo_form.bom_id = self.planning_bom
        mo_form.product_qty = 1
        mo_form.date_start = datetime(2022, 10, 10, 8, 0, 0, 0)
        mo = mo_form.save()
        mo.action_confirm()
        mo.button_plan()
        wo = mo.workorder_ids
        wc = wo.workcenter_id
        self.assertEqual(wo.date_start, datetime(2022, 10, 10, 8, 0, 0, 0),
                         "Date start should not have changed")
        self.assertEqual(wo.duration_expected, (60.0 * 100 / wc.time_efficiency) + wc.time_start + wc.time_stop,
                         "Duration expected should be the sum of the time_cycle (taking the workcenter efficiency into account), the time_start and time_stop")
        self.assertEqual(wo.date_finished, wo.date_start + timedelta(minutes=wo.duration_expected),
                         "Date finished should take into consideration the midday break")
        duration_expected = wo.duration_expected

        # Edit the workorder's scheduled start date to the next day
        with Form(mo) as mo_form:
            with mo_form.workorder_ids.edit(0) as wo_line:
                wo_line.date_start = datetime(2022, 10, 11, 8, 0, 0, 0)
        self.assertEqual(wo.date_start, datetime(2022, 10, 11, 8, 0, 0, 0),
                         "Date start should have changed")
        self.assertEqual(wo.duration_expected, duration_expected,
                         "Duration expected should not have changed")
        self.assertEqual(wo.date_finished, wo.date_start + timedelta(minutes=duration_expected),
                         "Date finished should have been recomputed to be consistent with the workorder duration")

        # Start the workorder
        wo.button_start()
        self.assertEqual(wo.date_start, datetime(2022, 10, 10, 7, 45, 0, 0),
                         "Date start should have changed")
        self.assertEqual(wo.duration_expected, duration_expected,
                         "Duration expected should have changed")
        self.assertEqual(wo.date_finished, wo.date_start + timedelta(minutes=duration_expected),
                         "Date finished should have been recomputed to be consistent with the workorder duration")

    def test_plan_unplan_date(self):
        """ Testing planning a workorder then cancel it and then plan it again.
        The planned date must be the same the first time and the second time the
        workorder is planned."""
        self.full_availability()
        date = datetime.now() + timedelta(days=2)
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_4
        mo_form.bom_id = self.planning_bom
        mo_form.product_qty = 1
        mo_form.date_start = date
        mo = mo_form.save()
        mo.action_confirm()
        # Plans the MO and checks the date.
        mo.button_plan()
        self.assertAlmostEqual(mo.date_start, date, delta=timedelta(seconds=10))
        self.assertEqual(bool(mo.workorder_ids.exists()), True)
        leave = mo.workorder_ids.leave_id
        self.assertEqual(bool(leave.exists()), True)
        # Unplans the MO and checks the workorder and its leave no more exist.
        mo.button_unplan()
        self.assertEqual(bool(mo.workorder_ids.exists()), True)
        self.assertEqual(bool(leave.exists()), False)
        # Plans (again) the MO and checks the date is still the same.
        mo.button_plan()
        self.assertAlmostEqual(mo.date_start, date, delta=timedelta(seconds=10))
        self.assertAlmostEqual(mo.date_start, mo.workorder_ids.date_start, delta=timedelta(seconds=10))

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
        # avoid having reservation issues by making all components consu
        self.product_2.type = 'consu'
        # Kit bom
        self.env['mrp.bom'].create({
            'product_id': self.product_4.id,
            'product_tmpl_id': self.product_4.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'consumption': 'flexible',
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
            'consumption': 'flexible',
            'operation_ids': [
                (0, 0, {
                    'workcenter_id': self.mrp_workcenter_1.id,
                    'name': 'Packing',
                    'time_cycle': 30,
                    'sequence': 5}),
                (0, 0, {
                    'workcenter_id': self.mrp_workcenter_3.id,
                    'name': 'Testing',
                    'time_cycle': 60,
                    'sequence': 10}),
                (0, 0, {
                    'workcenter_id': self.mrp_workcenter_3.id,
                    'name': 'Long time assembly',
                    'time_cycle': 180,
                    'sequence': 15}),
            ],
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': self.product_1.id, 'product_qty': 1}),
                (0, 0, {'product_id': self.product_4.id, 'product_qty': 1})
            ]})

        self.env['quality.point'].create({
            'product_ids': [(4, self.product_5.id)],
            'picking_type_ids': [(4, self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')], limit=1).id)],
            'operation_id': main_bom.operation_ids[2].id,
            'test_type_id': self.env.ref('mrp_workorder.test_type_register_consumed_materials').id,
            'component_id': self.product_1.id,
        })
        self.env['quality.point'].create({
            'product_ids': [(4, self.product_5.id)],
            'picking_type_ids': [(4, self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')], limit=1).id)],
            'operation_id': main_bom.operation_ids[2].id,
            'test_type_id': self.env.ref('mrp_workorder.test_type_register_consumed_materials').id,
            'component_id': self.product_2.id,
        })

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_5
        mo_form.bom_id = main_bom
        mo_form.product_qty = 1
        mo = mo_form.save()
        mo.action_confirm()
        mo.action_assign()
        mo.button_plan()
        self.assertEqual(len(mo.workorder_ids), 3)
        long_time_assembly = mo.workorder_ids[2]

        # same component merged in one line
        self.assertEqual(len(long_time_assembly.check_ids), 3)
        line1 = long_time_assembly.check_ids[0]
        line2 = long_time_assembly.check_ids[1]
        line3 = long_time_assembly.check_ids[2]
        self.assertEqual(line1.component_id, self.product_1)
        self.assertEqual(line1.qty_done, 1)
        self.assertEqual(line2.component_id, self.product_1)
        self.assertEqual(line2.qty_done, 4)
        self.assertEqual(line3.component_id, self.product_2)
        self.assertEqual(line3.qty_done, 1)

    def test_conflict_and_replan(self):
        """ TEST Json data conflicted and the replan button of a workorder """
        dining_table = self.dining_table
        bom = self.mrp_bom_desk
        bom.operation_ids = False
        bom.write({
            'operation_ids': [
                (0, 0, {
                    'workcenter_id': self.mrp_workcenter_3.id,
                    'name': 'Packing',
                    'time_cycle': 30,
                    'sequence': 5}),
                (0, 0, {
                    'workcenter_id': self.mrp_workcenter_3.id,
                    'name': 'Testing',
                    'time_cycle': 60,
                    'sequence': 10}),
                (0, 0, {
                    'workcenter_id': self.mrp_workcenter_3.id,
                    'name': 'Long time assembly',
                    'time_cycle': 180,
                    'sequence': 15}),
            ]})


        bom.bom_line_ids.filtered(lambda p: p.product_id == self.product_table_sheet).operation_id = bom.operation_ids[0].id
        bom.bom_line_ids.filtered(lambda p: p.product_id == self.product_table_leg).operation_id = bom.operation_ids[1].id
        bom.bom_line_ids.filtered(lambda p: p.product_id == self.product_bolt).operation_id = bom.operation_ids[2].id

        production_table_form = Form(self.env['mrp.production'])
        production_table_form.product_id = dining_table
        production_table_form.bom_id = bom
        production_table_form.product_qty = 1.0
        production_table_form.product_uom_id = dining_table.uom_id
        production_table = production_table_form.save()

        production_table.action_confirm()
        # Create work order
        production_table.button_plan()
        # Check Work order created or not
        self.assertEqual(len(production_table.workorder_ids), 3)

        workorders = production_table.workorder_ids
        wo1, wo2, wo3 = workorders[0], workorders[1], workorders[2]

        self.assertEqual(wo1.state, 'waiting', "First workorder state should be ready.")
        self.assertEqual(wo1.workcenter_id.id, self.mrp_workcenter_3.id)
        self.assertEqual(wo2.state, 'pending')
        self.assertEqual(wo3.state, 'pending')

        self.assertFalse(wo1.id in wo1._get_conflicted_workorder_ids(), "Shouldn't conflict")
        self.assertFalse(wo2.id in wo2._get_conflicted_workorder_ids(), "Shouldn't conflict")
        self.assertFalse(wo3.id in wo3._get_conflicted_workorder_ids(), "Shouldn't conflict")

        # Conflicted with wo1
        wo2.write({'date_start': wo1.date_start, 'date_finished': wo1.date_finished})
        # Bad order of workorders (wo3-wo1-wo2) + Late
        wo3.write({'date_start': wo1.date_start - timedelta(weeks=1), 'date_finished': wo1.date_finished - timedelta(weeks=1)})

        self.assertTrue(wo2.id in wo2._get_conflicted_workorder_ids(), "Should conflict with wo1")
        self.assertTrue(wo1.id in wo1._get_conflicted_workorder_ids(), "Should conflict with wo2")

        self.assertTrue('text-danger' in wo2.json_popover, "Popover should in be in red (due to conflict)")
        self.assertTrue('text-danger' in wo3.json_popover, "Popover should in be in red (due to bad order of wo)")
        self.assertTrue('text-warning' in wo3.json_popover, "Popover contains of warning (late)")

        wo1.button_start()
        self.assertEqual(wo1.state, 'progress')
        self.assertEqual(wo2.id in wo2._get_conflicted_workorder_ids(), False, "Shouldn't have a conflict because wo1 is in progress")

        wo1_date_start = wo1.date_start
        wo2_date_start = wo2.date_start
        wo3_date_start = wo3.date_start

        wo2.action_replan()  # Replan all MO of WO

        self.assertEqual(wo1.date_start, wo1_date_start, "Date of Workorder 1 shouldn't change (because it is in progress)")
        self.assertNotEqual(wo2.date_start, wo2_date_start, "Date of Workorder 2 should be updated")
        self.assertNotEqual(wo3.date_start, wo3_date_start, "Date of Workorder 3 should be updated")
        self.assertTrue(wo3.date_start > wo2.date_start, "Workorder 2 should be before the 3")


class TestRoutingAndKits(TransactionCase):
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

        grp_workorder = cls.env.ref('mrp.group_mrp_routings')
        cls.env.user.write({'groups_id': [(4, grp_workorder.id)]})

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
        cls.bom_finished1 = cls.env['mrp.bom'].create({
            'product_id': cls.finished1.id,
            'product_tmpl_id': cls.finished1.product_tmpl_id.id,
            'product_uom_id': cls.uom_unit.id,
            'consumption': 'flexible',
            'product_qty': 1,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': cls.compfinished1.id, 'product_qty': 1}),
                (0, 0, {'product_id': cls.kit1.id, 'product_qty': 1}),
            ],
            'operation_ids': [
                (0, 0, {'sequence': 1, 'name': 'finished operation 1', 'workcenter_id': cls.workcenter_finished1.id}),
                (0, 0, {'sequence': 2, 'name': 'finished operation 2', 'workcenter_id': cls.workcenter_finished1.id}),
            ],
        })
        cls.bom_kit1 = cls.env['mrp.bom'].create({
            'product_id': cls.kit1.id,
            'product_tmpl_id': cls.kit1.product_tmpl_id.id,
            'product_uom_id': cls.uom_unit.id,
            'product_qty': 1,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': cls.compkit1.id, 'product_qty': 1}),
            ],
            'operation_ids': [
                (0, 0, {'name': 'Kit operation', 'workcenter_id': cls.workcenter_kit1.id})
            ]
        })

    def test_1(self):
        """Operations are set on `self.bom_kit1` but none on `self.bom_finished1`."""
        self.bom_kit1.bom_line_ids.operation_id = self.bom_kit1.operation_ids[0]

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.finished1
        mo_form.bom_id = self.bom_finished1
        mo_form.product_qty = 1.0
        mo = mo_form.save()

        mo.action_confirm()
        mo.button_plan()

        self.assertEqual(len(mo.workorder_ids), 3)
        self.assertEqual(len(mo.workorder_ids[0].move_raw_ids.move_line_ids), 0)
        self.assertEqual(mo.workorder_ids[1].move_raw_ids.product_id, self.compfinished1)
        self.assertEqual(mo.workorder_ids[2].move_raw_ids.product_id, self.compkit1)

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
        self.assertEqual(len(mo.workorder_ids[0].move_raw_ids.move_line_ids), 0)
        self.assertEqual(mo.workorder_ids[1].move_raw_ids.product_id, self.compfinished1)
        self.assertEqual(mo.workorder_ids[2].move_raw_ids.product_id, self.compkit1)

    def test_3(self):
        """Operations are set both `self.bom_kit1` and `self.bom_finished1`."""
        self.bom_kit1.bom_line_ids.operation_id = self.bom_kit1.operation_ids
        self.bom_finished1.bom_line_ids[0].operation_id = self.bom_finished1.operation_ids[0]
        self.bom_finished1.bom_line_ids[1].operation_id = self.bom_finished1.operation_ids[1]

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.finished1
        mo_form.bom_id = self.bom_finished1
        mo_form.product_qty = 1.0
        mo = mo_form.save()

        mo.action_confirm()
        mo.button_plan()

        self.assertEqual(len(mo.workorder_ids), 3)
        self.assertEqual(mo.workorder_ids[0].move_raw_ids.product_id, self.compfinished1)
        self.assertFalse(mo.workorder_ids[1].move_raw_ids.product_id.id)
        self.assertEqual(mo.workorder_ids[2].move_raw_ids.product_id, self.compkit1)

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

        self.assertEqual(len(mo.workorder_ids[0].move_raw_ids), 0)
        self.assertEqual(set(mo.workorder_ids[1].move_raw_ids.product_id.ids), set([self.compfinished1.id, compkit2.id]))
        self.assertEqual(mo.workorder_ids[2].move_raw_ids.product_id, self.compkit1)

    def test_5(self):
        # Main bom: set the normal component to the first of the two operations of the routing.
        bomline_compfinished = self.bom_finished1.bom_line_ids.filtered(lambda bl: bl.product_id == self.compfinished1)
        bomline_compfinished.operation_id = self.bom_finished1.operation_ids[0]

        # Main bom: the kit do not have an operation set but there's one on its bom
        bomline_kit1 = self.bom_finished1.bom_line_ids - bomline_compfinished
        self.assertFalse(bomline_kit1.operation_id.id)
        self.bom_kit1.bom_line_ids.operation_id = self.bom_kit1.operation_ids

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
        self.assertEqual(mo.workorder_ids[0].move_raw_ids.product_id, self.compfinished1)
        self.assertEqual(mo.workorder_ids[1].move_raw_ids.product_id, compkit2)
        self.assertEqual(mo.workorder_ids[2].move_raw_ids.product_id, self.compkit1)

    # -------------------------------------------------------------------------
    # Those 2 next tests aren't related to routing and kit but to flexible
    # consumption.
    # -------------------------------------------------------------------------
    def test_merge_lot(self):
        """ Produce 10 units of product tracked by lot on two workorder. On the
        first one, produce 4 onto lot1 then 6 onto lot1 as well. The second
        workorder should be prefilled with 10 units and lot1"""
        self.finished1.tracking = 'lot'
        lot1 = self.env['stock.lot'].create({
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
        wo1 = mo.workorder_ids.filtered(lambda wo: wo.state == 'waiting')[0]
        wo1.button_start()
        wo1.qty_producing = 4
        wo1.finished_lot_id = lot1
        wo1.record_production()
        backorder = mo.procurement_group_id.mrp_production_ids[-1]
        ba_wo1 = backorder.workorder_ids[0]
        self.assertEqual(ba_wo1.qty_producing, 6)
        self.assertEqual(ba_wo1.qty_produced, 0)
        self.assertEqual(ba_wo1.qty_remaining, 6)
        ba_wo1.finished_lot_id = lot1
        ba_wo1.record_production()
        wo2 = mo.workorder_ids[2]
        wo2.button_start()
        ba_wo2 = backorder.workorder_ids[2]
        ba_wo2.button_start()
        self.assertEqual(wo2.qty_producing, 4)
        self.assertEqual(wo2.finished_lot_id, lot1)
        self.assertEqual(ba_wo2.qty_producing, 6)
        self.assertEqual(ba_wo2.finished_lot_id, lot1)

    def test_add_move(self):
        """ Make a production using multi step routing. Add an additional move
        on a specific operation and check that the produce is consumed into the
        right workorder. """
        # Required for `product_uom` to be visible in the view
        self.env.user.groups_id += self.env.ref('uom.group_uom')
        self.bom_finished1.consumption = 'flexible'
        add_product = self.env['product.product'].create({
            'name': 'Additional',
            'type': 'product',
        })
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.finished1
        mo_form.bom_id = self.bom_finished1
        mo_form.product_qty = 10.0
        mo = mo_form.save()

        mo_form = Form(mo)
        with mo_form.move_raw_ids.new() as move:
            move.name = mo.name
            move.product_id = add_product
            move.product_uom = add_product.uom_id
            move.location_dest_id = mo.production_location_id
            move.product_uom_qty = 2
            move.operation_id = mo.bom_id.operation_ids[0]
        mo = mo_form.save()
        self.assertEqual(len(mo.move_raw_ids), 3)
        mo.action_confirm()
        self.assertEqual(mo.move_raw_ids.mapped('state'), ['confirmed'] * 3)
        mo.button_plan()
        self.assertEqual(len(mo.workorder_ids), 3)
        wo1 = mo.workorder_ids[0]
        lines = wo1.move_raw_ids
        self.assertEqual(lines.product_id, add_product)

    def test_add_move_2(self):
        """ Make a production using multi step routing. Add an additional move
        on a specific operation and check that the produce is consumed into the
        right workorder. """
        # Required for `product_uom` to be visible in the view
        self.env.user.groups_id += self.env.ref('uom.group_uom')
        self.bom_finished1.consumption = 'flexible'
        add_product = self.env['product.product'].create({
            'name': 'Additional',
            'type': 'product',
        })
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.finished1
        mo_form.bom_id = self.bom_finished1
        mo_form.product_qty = 10.0
        mo = mo_form.save()
        mo.action_confirm()
        mo.is_locked = False
        mo_form = Form(mo)
        with mo_form.move_raw_ids.new() as move:
            move.name = mo.name
            move.product_id = add_product
            move.product_uom = add_product.uom_id
            move.location_dest_id = mo.production_location_id
            move.product_uom_qty = 2
            move.operation_id = mo.bom_id.operation_ids[0]
        mo = mo_form.save()
        new_move = mo.move_raw_ids.filtered(lambda move: move.product_id == add_product)
        self.assertEqual(len(mo.move_raw_ids), 3)
        self.assertEqual(len(new_move), 1)
        self.assertEqual(mo.move_raw_ids.mapped('state'), ['confirmed'] * 3)
        mo.button_plan()
        self.assertEqual(len(mo.workorder_ids), 3)
        wo1 = mo.workorder_ids[0]
        lines = wo1.move_raw_ids
        self.assertEqual(lines.product_id, add_product)
