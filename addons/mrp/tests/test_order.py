# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.fields import Datetime as Dt
from odoo.addons.mrp.tests.common import TestMrpCommon


class TestMrpOrder(TestMrpCommon):

    def test_access_rights_manager(self):
        man_order = self.env['mrp.production'].sudo(self.user_mrp_manager).create({
            'name': 'Stick-0',
            'product_id': self.product_4.id,
            'product_uom_id': self.product_4.uom_id.id,
            'product_qty': 5.0,
            'bom_id': self.bom_1.id,
            'location_src_id': self.location_1.id,
            'location_dest_id': self.warehouse_1.wh_output_stock_loc_id.id,
        })
        man_order.action_cancel()
        self.assertEqual(man_order.state, 'cancel', "Production order should be in cancel state.")
        man_order.unlink()

    def test_access_rights_user(self):
        man_order = self.env['mrp.production'].sudo(self.user_mrp_user).create({
            'name': 'Stick-0',
            'product_id': self.product_4.id,
            'product_uom_id': self.product_4.uom_id.id,
            'product_qty': 5.0,
            'bom_id': self.bom_1.id,
            'location_src_id': self.location_1.id,
            'location_dest_id': self.warehouse_1.wh_output_stock_loc_id.id,
        })
        man_order.action_cancel()
        self.assertEqual(man_order.state, 'cancel', "Production order should be in cancel state.")
        man_order.unlink()

    def test_basic(self):
        """ Basic order test: no routing (thus no workorders), no lot """
        inventory = self.env['stock.inventory'].create({
            'name': 'Initial inventory',
            'filter': 'partial',
            'line_ids': [(0, 0, {
                'product_id': self.product_1.id,
                'product_uom_id': self.product_1.uom_id.id,
                'product_qty': 500,
                'location_id': self.warehouse_1.lot_stock_id.id
            }), (0, 0, {
                'product_id': self.product_2.id,
                'product_uom_id': self.product_2.uom_id.id,
                'product_qty': 500,
                'location_id': self.warehouse_1.lot_stock_id.id
            })]
        })
        inventory.action_done()

        test_date_planned = datetime.now() - timedelta(days=1)
        test_quantity = 2.0
        self.bom_1.routing_id = False
        man_order = self.env['mrp.production'].sudo(self.user_mrp_user).create({
            'name': 'Stick-0',
            'product_id': self.product_4.id,
            'product_uom_id': self.product_4.uom_id.id,
            'product_qty': test_quantity,
            'bom_id': self.bom_1.id,
            'date_planned_start': test_date_planned,
            'location_src_id': self.location_1.id,
            'location_dest_id': self.warehouse_1.wh_output_stock_loc_id.id,
        })
        self.assertEqual(man_order.state, 'confirmed', "Production order should be in confirmed state.")

        # check production move
        production_move = man_order.move_finished_ids
        self.assertEqual(production_move.date, Dt.to_string(test_date_planned))
        self.assertEqual(production_move.product_id, self.product_4)
        self.assertEqual(production_move.product_uom, man_order.product_uom_id)
        self.assertEqual(production_move.product_qty, man_order.product_qty)
        self.assertEqual(production_move.location_id, self.product_4.property_stock_production)
        self.assertEqual(production_move.location_dest_id, man_order.location_dest_id)

        # check consumption moves
        for move in man_order.move_raw_ids:
            self.assertEqual(move.date, Dt.to_string(test_date_planned))
        first_move = man_order.move_raw_ids.filtered(lambda move: move.product_id == self.product_2)
        self.assertEqual(first_move.product_qty, test_quantity / self.bom_1.product_qty * self.product_4.uom_id.factor_inv * 2)
        first_move = man_order.move_raw_ids.filtered(lambda move: move.product_id == self.product_1)
        self.assertEqual(first_move.product_qty, test_quantity / self.bom_1.product_qty * self.product_4.uom_id.factor_inv * 4)

        # waste some material, create a scrap
        # scrap = self.env['stock.scrap'].with_context(
        #     active_model='mrp.production', active_id=man_order.id
        # ).create({})
        # scrap = self.env['stock.scrap'].create({
        #     'production_id': man_order.id,
        #     'product_id': first_move.product_id.id,
        #     'product_uom_id': first_move.product_uom.id,
        #     'scrap_qty': 5.0,
        # })
        # check created scrap


        # procurements = self.env['procurement.order'].search([('move_dest_id', 'in', man_order.move_raw_ids.ids)])
        # print procurements
        # procurements = self.env['procurement.order'].search([('production_id', '=', man_order.id)])
        # print procurements
        # for proc in self.env['procurement.order'].browse(procurements):
        #     date_planned = self.mrp_production_test1.date_planned
        #     if proc.product_id.type not in ('product', 'consu'):
        #         continue
        #     if proc.product_id.id == order_line.product_id.id:
        #         self.assertEqual(proc.date_planned, date_planned, "Planned date does not correspond")
        #       # procurement state should be `confirmed` at this stage, except if procurement_jit is installed, in which
        #       # case it could already be in `running` or `exception` state (not enough stock)
        #         expected_states = ('confirmed', 'running', 'exception')
        #         self.assertEqual(proc.state in expected_states, 'Procurement state is `%s` for %s, expected one of %s' % (proc.state, proc.product_id.name, expected_states))

        # Change production quantity
        qty_wizard = self.env['change.production.qty'].create({
            'mo_id': man_order.id,
            'product_qty': 3.0,
        })
        # qty_wizard.change_prod_qty()

        # # I check qty after changed in production order.
        # #self.assertEqual(self.mrp_production_test1.product_qty, 3, "Qty is not changed in order.")
        # move = self.mrp_production_test1.move_finished_ids[0]
        # self.assertEqual(move.product_qty, self.mrp_production_test1.product_qty, "Qty is not changed in move line.")

        # # I run scheduler.
        # self.env['procurement.order'].run_scheduler()

        # # The production order is Waiting Goods, will force production which should set consume lines as available
        # self.mrp_production_test1.button_plan()
        # # I check that production order in ready state after forcing production.

        # #self.assertEqual(self.mrp_production_test1.availability, 'assigned', 'Production order availability should be set as available')

        # produce product
        produce_wizard = self.env['mrp.product.produce'].sudo(self.user_mrp_user).with_context({
            'active_id': man_order.id,
            'active_ids': [man_order.id],
        }).create({
            'product_qty': 1.0,
        })
        produce_wizard.do_produce()

        # man_order.button_mark_done()
        man_order.button_mark_done()
        self.assertEqual(man_order.state, 'done', "Production order should be in done state.")

    def test_explode_from_order(self):
        #
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

        man_order = self.env['mrp.production'].create({
            'name': 'MO-Test',
            'product_id': self.product_6.id,
            'product_uom_id': self.product_6.uom_id.id,
            'product_qty': 48,
            'bom_id': self.bom_3.id,
        })

        # reset quantities
        self.env['stock.change.product.qty'].create({
            'product_id': self.product_1.id,
            'new_quantity': 0.0,
            'location_id': self.warehouse_1.lot_stock_id.id,
        }).change_product_qty()

        (self.product_2 | self.product_4).write({
            'tracking': 'none',
        })
        # assign consume material
        man_order.action_assign()
        self.assertEqual(man_order.availability, 'waiting', "Production order should be in waiting state.")

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
        lot_product_2 = self.env['stock.production.lot'].create({'product_id': self.product_2.id})
        lot_product_4 = self.env['stock.production.lot'].create({'product_id': self.product_4.id})

        # refuel stock
        inventory = self.env['stock.inventory'].create({
            'name': 'Inventory For Product C',
            'filter': 'partial',
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
        inventory.prepare_inventory()
        inventory.action_done()

        # re-assign consume material
        man_order.action_assign()

        # Check production order status after assign.
        self.assertEqual(man_order.availability, 'assigned', "Production order should be in assigned state.")
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
        self.assertEqual(kit_wo.duration_expected, 80, "Workorder duration should be 80 instead of %s." % str(kit_wo.duration_expected))
        self.assertEqual(door_wo_1.duration_expected, 20, "Workorder duration should be 20 instead of %s." % str(door_wo_1.duration_expected))
        self.assertEqual(door_wo_2.duration_expected, 20, "Workorder duration should be 20 instead of %s." % str(door_wo_2.duration_expected))

        # subbom: kit for stone tools
        kit_wo.button_start()
        finished_lot = self.env['stock.production.lot'].create({'product_id': man_order.product_id.id})
        kit_wo.write({
            'final_lot_id': finished_lot.id,
            'qty_producing': 48
        })
        
        kit_wo.record_production()

        self.assertEqual(kit_wo.state, 'done', "Workorder should be in done state.")

        # first operation of main bom
        finished_lot = self.env['stock.production.lot'].create({'product_id': man_order.product_id.id})
        door_wo_1.write({
            'final_lot_id': finished_lot.id,
            'qty_producing': 48
        })
        door_wo_1.record_production()
        self.assertEqual(door_wo_1.state, 'done', "Workorder should be in done state.")

        # second operation of main bom
        self.assertEqual(door_wo_2.state, 'ready', "Workorder should be in ready state.")
        door_wo_2.record_production()
        self.assertEqual(door_wo_2.state, 'done', "Workorder should be in done state.")

    def test_production_avialability(self):
        """
            Test availability of production order.
        """
        self.bom_3.bom_line_ids.filtered(lambda x: x.product_id == self.product_5).unlink()
        self.bom_3.bom_line_ids.filtered(lambda x: x.product_id == self.product_4).unlink()

        production_2 = self.env['mrp.production'].create({
            'name': 'MO-Test001',
            'product_id': self.product_6.id,
            'product_qty': 5.0,
            'bom_id': self.bom_3.id,
            'product_uom_id': self.product_6.uom_id.id,
        })
        production_2.action_assign()

        # check sub product availability state is waiting
        self.assertEqual(production_2.availability, 'waiting', 'Production order should be availability for waiting state')

        # Update Inventory
        inventory_wizard = self.env['stock.change.product.qty'].create({
            'product_id': self.product_2.id,
            'new_quantity': 2.0,
        })
        inventory_wizard.change_product_qty()

        production_2.action_assign()
        # check sub product availability state is partially available
        self.assertEqual(production_2.availability, 'partially_available', 'Production order should be availability for partially available state')

        # Update Inventory
        inventory_wizard = self.env['stock.change.product.qty'].create({
            'product_id': self.product_2.id,
            'new_quantity': 5.0,
        })
        inventory_wizard.change_product_qty()

        production_2.action_assign()
        # check sub product availability state is assigned
        self.assertEqual(production_2.availability, 'assigned', 'Production order should be availability for assigned state')

    def test_empty_routing(self):
        """ Check what happens when you work with an empty routing"""
        routing = self.env['mrp.routing'].create({'name': 'Routing without operations',
                                        'location_id': self.warehouse_1.wh_input_stock_loc_id.id,})
        self.bom_3.routing_id = routing.id
        production = self.env['mrp.production'].create({'name': 'MO test',
                                           'product_id': self.product_6.id,
                                           'product_qty': 3,
                                           'bom_id': self.bom_3.id,
                                           'product_uom_id': self.product_6.uom_id.id,})
        self.assertEqual(production.routing_id.id, False, 'The routing field should be empty on the mo')
        self.assertEqual(production.move_raw_ids[0].location_id.id, self.warehouse_1.wh_input_stock_loc_id.id, 'Raw moves start location should have altered.')