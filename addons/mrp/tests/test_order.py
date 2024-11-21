# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from freezegun import freeze_time

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import Form, users
from odoo.tools.misc import format_date
from odoo.tests.common import HttpCase, tagged

from odoo.addons.mrp.tests.common import TestMrpCommon


class TestMrpOrder(TestMrpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref('base.group_user').write({'implied_ids': [(4, cls.env.ref('stock.group_production_lot').id)]})

    def test_access_rights_manager(self):
        """ Checks an MRP manager can create, confirm and cancel a manufacturing order. """
        man_order_form = Form(self.env['mrp.production'].with_user(self.user_mrp_manager))
        man_order_form.product_id = self.product_4
        man_order_form.product_qty = 5.0
        man_order_form.bom_id = self.bom_1
        man_order_form.location_src_id = self.location_1
        man_order_form.location_dest_id = self.warehouse_1.wh_output_stock_loc_id
        man_order = man_order_form.save()
        man_order.action_confirm()
        man_order.action_cancel()
        self.assertEqual(man_order.state, 'cancel', "Production order should be in cancel state.")
        man_order.unlink()

    def test_access_rights_user(self):
        """ Checks an MRP user can create, confirm and cancel a manufacturing order. """
        man_order_form = Form(self.env['mrp.production'].with_user(self.user_mrp_user))
        man_order_form.product_id = self.product_4
        man_order_form.product_qty = 5.0
        man_order_form.bom_id = self.bom_1
        man_order_form.location_src_id = self.location_1
        man_order_form.location_dest_id = self.warehouse_1.wh_output_stock_loc_id
        man_order = man_order_form.save()
        man_order.action_confirm()
        man_order.action_cancel()
        self.assertEqual(man_order.state, 'cancel', "Production order should be in cancel state.")
        man_order.unlink()

    def test_basic(self):
        """ Checks a basic manufacturing order: no routing (thus no workorders), no lot and
        consume strictly what's needed. """
        self.product_1.is_storable = True
        self.product_2.is_storable = True
        self.env['stock.quant'].create({
            'location_id': self.warehouse_1.lot_stock_id.id,
            'product_id': self.product_1.id,
            'inventory_quantity': 500
        }).action_apply_inventory()
        self.env['stock.quant'].create({
            'location_id': self.warehouse_1.lot_stock_id.id,
            'product_id': self.product_2.id,
            'inventory_quantity': 500
        }).action_apply_inventory()

        date_start = fields.Datetime.now() - timedelta(days=1)
        test_quantity = 3.0
        man_order_form = Form(self.env['mrp.production'].with_user(self.user_mrp_user))
        man_order_form.product_id = self.product_4
        man_order_form.bom_id = self.bom_1
        man_order_form.product_uom_id = self.product_4.uom_id
        man_order_form.product_qty = test_quantity
        man_order_form.date_start = date_start
        man_order_form.location_src_id = self.location_1
        man_order_form.location_dest_id = self.warehouse_1.wh_output_stock_loc_id
        man_order = man_order_form.save()

        self.assertEqual(man_order.state, 'draft', "Production order should be in draft state.")
        man_order.action_confirm()
        self.assertEqual(man_order.state, 'confirmed', "Production order should be in confirmed state.")

        # check production move
        production_move = man_order.move_finished_ids
        self.assertAlmostEqual(production_move.date, date_start + timedelta(hours=1), delta=timedelta(seconds=10))
        self.assertEqual(production_move.product_id, self.product_4)
        self.assertEqual(production_move.product_uom, man_order.product_uom_id)
        self.assertEqual(production_move.product_qty, man_order.product_qty)
        self.assertEqual(production_move.location_id, self.product_4.property_stock_production)
        self.assertEqual(production_move.location_dest_id, man_order.location_dest_id)

        # check consumption moves
        for move in man_order.move_raw_ids:
            self.assertEqual(move.date, date_start)
        first_move = man_order.move_raw_ids.filtered(lambda move: move.product_id == self.product_2)
        self.assertEqual(first_move.product_qty, test_quantity / self.bom_1.product_qty * self.product_4.uom_id.factor_inv * 2)
        first_move = man_order.move_raw_ids.filtered(lambda move: move.product_id == self.product_1)
        self.assertEqual(first_move.product_qty, test_quantity / self.bom_1.product_qty * self.product_4.uom_id.factor_inv * 4)

        # produce product
        mo_form = Form(man_order)
        mo_form.qty_producing = 2.0
        man_order = mo_form.save()

        action = man_order.button_mark_done()
        self.assertEqual(man_order.state, 'progress', "Production order should be open a backorder wizard, then not done yet.")

        quantity_issues = man_order._get_consumption_issues()
        action = man_order._action_generate_consumption_wizard(quantity_issues)
        backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder.save().action_close_mo()
        self.assertEqual(man_order.state, 'done', "Production order should be done.")

        # check that copy handles moves correctly
        mo_copy = man_order.copy()
        self.assertEqual(mo_copy.state, 'draft', "Copied production order should be draft.")
        self.assertEqual(len(mo_copy.move_raw_ids), 2,
                         "Incorrect number of component moves [i.e. all non-0 (even cancelled) moves should be copied].")
        self.assertEqual(len(mo_copy.move_finished_ids), 1, "Incorrect number of moves for products to produce [i.e. cancelled moves should not be copied")
        self.assertEqual(mo_copy.move_finished_ids.product_uom_qty, 3, "Incorrect qty of products to produce")

        # check that a cancelled MO is copied correctly
        mo_copy.action_cancel()
        self.assertEqual(mo_copy.state, 'cancel')
        mo_copy_2 = mo_copy.copy()
        self.assertEqual(mo_copy_2.state, 'draft', "Copied production order should be draft.")
        self.assertEqual(len(mo_copy_2.move_raw_ids), 2, "Incorrect number of component moves.")
        self.assertEqual(len(mo_copy_2.move_finished_ids), 1, "Incorrect number of moves for products to produce [i.e. copying a cancelled MO should copy its cancelled moves]")
        self.assertEqual(mo_copy_2.move_finished_ids.product_uom_qty, 3, "Incorrect qty of products to produce")

    def test_production_availability(self):
        """ Checks the availability of a production order through mutliple calls to `action_assign`.
        """
        self.bom_3.bom_line_ids.filtered(lambda x: x.product_id == self.product_5).unlink()
        self.bom_3.bom_line_ids.filtered(lambda x: x.product_id == self.product_4).unlink()
        self.bom_3.ready_to_produce = 'all_available'

        production_form = Form(self.env['mrp.production'])
        production_form.product_id = self.product_6
        production_form.bom_id = self.bom_3
        production_form.product_qty = 5.0
        production_form.product_uom_id = self.product_6.uom_id
        production_2 = production_form.save()

        production_2.action_confirm()
        production_2.action_assign()

        # check sub product availability state is waiting
        self.assertEqual(production_2.reservation_state, 'confirmed', 'Production order should be availability for waiting state')

        # Update Inventory
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product_2.id,
            'inventory_quantity': 2.0,
            'location_id': self.stock_location_14.id
        }).action_apply_inventory()

        production_2.action_assign()
        # check sub product availability state is partially available
        self.assertEqual(production_2.reservation_state, 'confirmed', 'Production order should be availability for partially available state')

        # Update Inventory
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product_2.id,
            'inventory_quantity': 5.0,
            'location_id': self.stock_location_14.id
        }).action_apply_inventory()

        production_2.action_assign()
        # check sub product availability state is assigned
        self.assertEqual(production_2.reservation_state, 'assigned', 'Production order should be availability for assigned state')

    def test_workorder_sequence(self):
        """ Test that workorders are correctly sequenced after creation and confirmation. """
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom_3
        mo = mo_form.save()
        self.assertEqual(len(mo.workorder_ids), 3)
        self.assertListEqual(mo.workorder_ids.mapped('sequence'), [0, 1, 2])
        self.assertEqual(mo.workorder_ids[0].operation_id.bom_id.type, 'phantom')    # Kit operations should go first
        with Form(mo) as mo_form_2:
            with mo_form_2.workorder_ids.new() as wo:
                wo.name = 'Do important stuff'
                wo.workcenter_id = self.workcenter_2
        mo.action_confirm()
        self.assertEqual(mo.workorder_ids.mapped('sequence'), [0, 1, 2, 100])


    @freeze_time('2022-06-28 08:00')
    def test_end_date(self):
        """ End date must be the day the MO is done (regardless of lead times)"""
        mo, bom_id, _p_final, _p1, _p2 = self.generate_mo(qty_base_1=10, qty_final=1, qty_base_2=1)
        bom_id.produce_delay = 5
        mo.button_mark_done()
        self.assertEqual(mo.date_finished.day, 28)

    def test_over_consumption(self):
        """ Consume more component quantity than the initial demand. No split on moves.
        """
        mo, _bom, _p_final, _p1, _p2 = self.generate_mo(qty_base_1=10, qty_final=1, qty_base_2=1)
        mo.action_assign()
        # check is_quantity_done_editable
        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo = mo_form.save()
        details_operation_form = Form(mo.move_raw_ids[0], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.quantity = 2
        details_operation_form.save()
        details_operation_form = Form(mo.move_raw_ids[1], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.quantity = 11
        details_operation_form.save()

        self.assertEqual(len(mo.move_raw_ids), 2)
        self.assertEqual(len(mo.move_raw_ids.mapped('move_line_ids')), 2)
        self.assertEqual(mo.move_raw_ids[0].move_line_ids.mapped('quantity'), [2])
        self.assertEqual(mo.move_raw_ids[1].move_line_ids.mapped('quantity'), [11])
        self.assertEqual(mo.move_raw_ids[0].quantity, 2)
        self.assertEqual(mo.move_raw_ids[1].quantity, 11)
        mo.button_mark_done()
        self.assertEqual(len(mo.move_raw_ids), 2)
        self.assertEqual(len(mo.move_raw_ids.mapped('move_line_ids')), 2)
        self.assertEqual(mo.move_raw_ids.mapped('quantity'), [2, 11])
        self.assertEqual(mo.move_raw_ids.mapped('move_line_ids.quantity'), [2, 11])

    def test_under_consumption(self):
        """ Consume less component quantity than the initial demand.
            Before done:
                p1, to consume = 1, consumed = 0
                p2, to consume = 10, consumed = 5
            After done:
                p1, to consume = 1, consumed = 0, state = cancel
                p2, to consume = 10, consumed = 5, state = done
        """
        mo, _bom, _p_final, _p1, _p2 = self.generate_mo(qty_base_1=10, qty_final=1, qty_base_2=1)
        mo.action_assign()
        # check is_quantity_done_editable
        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo = mo_form.save()
        details_operation_form = Form(mo.move_raw_ids[0], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.quantity = 0
        details_operation_form.save()
        details_operation_form = Form(mo.move_raw_ids[1], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.quantity = 5
        details_operation_form.save()

        self.assertEqual(len(mo.move_raw_ids), 2)
        self.assertEqual(len(mo.move_raw_ids.mapped('move_line_ids')), 2)
        self.assertEqual(mo.move_raw_ids[0].move_line_ids.mapped('quantity'), [0])
        self.assertEqual(mo.move_raw_ids[1].move_line_ids.mapped('quantity'), [5])
        self.assertEqual(mo.move_raw_ids[0].quantity, 0)
        self.assertEqual(mo.move_raw_ids[1].quantity, 5)
        mo.button_mark_done()
        self.assertEqual(len(mo.move_raw_ids), 2)
        self.assertEqual(len(mo.move_raw_ids.mapped('move_line_ids')), 1)
        self.assertEqual(mo.move_raw_ids.mapped('quantity'), [0, 5])
        self.assertEqual(mo.move_raw_ids.mapped('product_uom_qty'), [1, 10])
        self.assertEqual(mo.move_raw_ids.mapped('state'), ['cancel', 'done'])
        self.assertEqual(mo.move_raw_ids.mapped('move_line_ids.quantity'), [5])

    def test_update_quantity_1(self):
        """ Build 5 final products with different consumed lots,
        then edit the finished quantity and update the Manufacturing
        order quantity. Then check if the produced quantity do not
        change and it is possible to close the MO.
        """
        self.stock_location = self.env.ref('stock.stock_location_stock')
        mo, bom, p_final, p1, p2 = self.generate_mo(tracking_base_1='lot')
        self.assertEqual(len(mo), 1, 'MO should have been created')

        lot_1 = self.env['stock.lot'].create({
            'name': 'lot1',
            'product_id': p1.id,
        })
        lot_2 = self.env['stock.lot'].create({
            'name': 'lot2',
            'product_id': p1.id,
        })

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 10, lot_id=lot_1)
        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 10, lot_id=lot_2)

        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 5)
        mo.action_assign()

        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo = mo_form.save()

        details_operation_form = Form(mo.move_raw_ids[1], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.lot_id = lot_1
            ml.quantity = 20
        details_operation_form.save()
        mo.move_raw_ids[1].picked = True
        update_quantity_wizard = self.env['change.production.qty'].create({
            'mo_id': mo.id,
            'product_qty': 4,
        })
        update_quantity_wizard.change_prod_qty()

        self.assertEqual(mo.move_raw_ids.filtered(lambda m: m.product_id == p1).quantity, 20, 'Update the produce quantity should not impact already produced quantity.')
        self.assertEqual(mo.move_finished_ids.product_uom_qty, 4)
        mo.button_mark_done()

    def test_update_quantity_2(self):
        """ Build 5 final products with different consumed lots,
        then edit the finished quantity and update the Manufacturing
        order quantity. Then check if the produced quantity do not
        change and it is possible to close the MO.
        """
        self.stock_location = self.env.ref('stock.stock_location_stock')
        mo, bom, p_final, p1, p2 = self.generate_mo(qty_final=3)
        self.assertEqual(len(mo), 1, 'MO should have been created')

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 20)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 5)
        mo.action_assign()

        mo_form = Form(mo)
        mo_form.qty_producing = 2
        mo = mo_form.save()

        # Produce & backorder
        action = mo.button_mark_done()
        backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder.save().action_backorder()
        mo_backorder = mo.procurement_group_id.mrp_production_ids[-1]
        self.assertEqual(mo_backorder.product_qty, 1)

        update_quantity_wizard = self.env['change.production.qty'].create({
            'mo_id': mo_backorder.id,
            'product_qty': 3,
        })
        update_quantity_wizard.change_prod_qty()
        mo_back_form = Form(mo_backorder)
        mo_back_form.qty_producing = 3
        mo_backorder = mo_back_form.save()
        mo_backorder.button_mark_done()

        productions = mo | mo_backorder
        self.assertEqual(sum(productions.move_raw_ids.filtered(lambda m: m.product_id == p1).mapped('quantity')), 20)
        self.assertEqual(sum(productions.move_finished_ids.mapped('quantity')), 5)

    def test_update_quantity_3(self):
        bom = self.env['mrp.bom'].create({
            'product_id': self.product_6.id,
            'product_tmpl_id': self.product_6.product_tmpl_id.id,
            'product_qty': 1,
            'product_uom_id': self.product_6.uom_id.id,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': self.product_2.id, 'product_qty': 2.03}),
                (0, 0, {'product_id': self.product_8.id, 'product_qty': 4.16})
            ],
            'operation_ids': [
                (0, 0, {'name': 'Gift Wrap Maching', 'workcenter_id': self.workcenter_1.id, 'time_cycle': 15, 'sequence': 1}),
            ]
        })
        production_form = Form(self.env['mrp.production'])
        production_form.product_id = self.product_6
        production_form.bom_id = bom
        production_form.product_qty = 1
        production_form.product_uom_id = self.product_6.uom_id
        production = production_form.save()
        self.assertEqual(production.workorder_ids.duration_expected, 90)
        self.assertEqual([production.date_finished], production.move_finished_ids.mapped('date'))
        mo_form = Form(production)
        mo_form.product_qty = 3
        production = mo_form.save()
        self.assertEqual(production.workorder_ids.duration_expected, 165)

        # The same test than above but without form
        production = self.env['mrp.production'].create({
            'product_id': self.product_6.id,
            'bom_id': bom.id,
            'product_qty': 1,
            'product_uom_id': self.product_6.uom_id.id,
        })
        self.assertEqual(production.workorder_ids.duration_expected, 90)
        production.product_qty = 3
        self.assertEqual(production.workorder_ids.duration_expected, 165)

    def test_update_quantity_4(self):
        """ Workcenter 1 has 10' start time and 5' stop time """
        # Required for `workerorder_ids` to be visible in the view
        self.env.user.groups_id += self.env.ref('mrp.group_mrp_routings')
        bom = self.env['mrp.bom'].create({
            'product_id': self.product_6.id,
            'product_tmpl_id': self.product_6.product_tmpl_id.id,
            'product_qty': 1,
            'product_uom_id': self.product_6.uom_id.id,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': self.product_2.id, 'product_qty': 2.03}),
                (0, 0, {'product_id': self.product_8.id, 'product_qty': 4.16})
            ],
        })
        production_form = Form(self.env['mrp.production'])
        production_form.product_id = self.product_6
        production_form.bom_id = bom
        production_form.product_qty = 1
        production_form.product_uom_id = self.product_6.uom_id
        production = production_form.save()
        production_form = Form(production)
        with production_form.workorder_ids.new() as wo:
            wo.name = 'OP1'
            wo.workcenter_id = self.workcenter_1
            wo.duration_expected = 40
        production = production_form.save()
        self.assertEqual(production.workorder_ids.duration_expected, 40)
        mo_form = Form(production)
        mo_form.product_qty = 3
        production = mo_form.save()
        self.assertEqual(production.workorder_ids.duration_expected, 40)

        production.action_confirm()
        update_quantity_wizard = self.env['change.production.qty'].create({
            'mo_id': production.id,
            'product_qty': 9,
        })
        update_quantity_wizard.change_prod_qty()
        self.assertEqual(production.workorder_ids.duration_expected, 90)

        # The same test than above but without form
        production = self.env['mrp.production'].create({
            'product_id': self.product_6.id,
            'bom_id': bom.id,
            'product_qty': 1,
            'product_uom_id': self.product_6.uom_id.id,
            'workorder_ids': [Command.create({
                'name': 'OP1',
                'product_uom_id': self.product_6.uom_id.id,
                'workcenter_id': self.workcenter_1.id,
                'duration_expected': 40,
            })],
        })
        self.assertEqual(production.workorder_ids.duration_expected, 40)
        production.product_qty = 3
        self.assertEqual(production.workorder_ids.duration_expected, 40)

        production.action_confirm()
        update_quantity_wizard = self.env['change.production.qty'].create({
            'mo_id': production.id,
            'product_qty': 9,
        })
        update_quantity_wizard.change_prod_qty()
        self.assertEqual(production.workorder_ids.duration_expected, 90)

    def test_qty_producing(self):
        """Qty producing should be the qty remain to produce, instead of 0"""
        # Required for `workerorder_ids` to be visible in the view
        self.env.user.groups_id += self.env.ref('mrp.group_mrp_routings')
        bom = self.env['mrp.bom'].create({
            'product_id': self.product_6.id,
            'product_tmpl_id': self.product_6.product_tmpl_id.id,
            'product_qty': 1,
            'product_uom_id': self.product_6.uom_id.id,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': self.product_2.id, 'product_qty': 2.00}),
            ],
        })
        production_form = Form(self.env['mrp.production'])
        production_form.product_id = self.product_6
        production_form.bom_id = bom
        production_form.product_qty = 5
        production_form.product_uom_id = self.product_6.uom_id
        production = production_form.save()
        production_form = Form(production)
        with production_form.workorder_ids.new() as wo:
            wo.name = 'OP1'
            wo.workcenter_id = self.workcenter_1
            wo.duration_expected = 40
        production = production_form.save()
        production.action_confirm()
        production.button_plan()

        wo = production.workorder_ids[0]
        wo.button_start()
        self.assertEqual(wo.qty_producing, 5, "Wrong quantity is suggested to produce.")

        # Simulate changing the qty_producing in the frontend
        wo.qty_producing = 4
        wo.button_pending()
        wo.button_start()
        self.assertEqual(wo.qty_producing, 4, "Changing the qty_producing in the frontend is not persisted")

    def test_recursive_work_orders(self):
        """ When planning more than 322 work orders,
            there is a recursion error
            (with the default getrecursionlimit of 1000)
        """
        product_uom_id = self.env.ref('uom.product_uom_unit').id
        mo_no_company = self.env['mrp.production'].create({
            'product_id': self.product.id,
            'product_uom_id': product_uom_id,
        })
        values = [
            {
                'name': f'Work order {n}',
                'workcenter_id': self.workcenter_1.id,
                'product_uom_id': product_uom_id,
                'production_id': mo_no_company.id,
                'duration': 60,
            } for n in range(300)
        ]
        self.env['mrp.workorder'].create(values)
        mo_no_company.action_confirm()
        mo_no_company.button_plan()

    def test_update_quantity_5(self):
        bom = self.env['mrp.bom'].create({
            'product_id': self.product_6.id,
            'product_tmpl_id': self.product_6.product_tmpl_id.id,
            'product_qty': 1,
            'product_uom_id': self.product_6.uom_id.id,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': self.product_2.id, 'product_qty': 3}),
            ],
        })
        production_form = Form(self.env['mrp.production'])
        production_form.product_id = self.product_6
        production_form.bom_id = bom
        production_form.product_qty = 1
        production_form.product_uom_id = self.product_6.uom_id
        production = production_form.save()
        production.action_confirm()
        production.action_assign()
        production.is_locked = False
        production_form = Form(production)
        # change the quantity producing and the initial demand
        # in the same transaction
        production_form.qty_producing = 10
        with production_form.move_raw_ids.edit(0) as move:
            move.product_uom_qty = 2
        production = production_form.save()
        production.button_mark_done()

    def test_update_plan_date(self):
        """Editing the scheduled date after planning the MO should unplan the MO, and adjust the date on the stock moves"""
        date_start = datetime(2023, 5, 15, 9, 0)
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_4
        mo_form.bom_id = self.bom_1
        mo_form.product_qty = 1
        mo_form.date_start = date_start
        mo = mo_form.save()
        self.assertEqual(mo.move_finished_ids[0].date, datetime(2023, 5, 15, 10, 0))
        mo.action_confirm()
        mo.button_plan()
        self.assertTrue(mo.is_planned)
        mo.date_start = datetime(2024, 5, 15, 9, 0)
        self.assertFalse(mo.is_planned)
        self.assertEqual(mo.move_finished_ids[0].date, datetime(2024, 5, 15, 10, 0))

    def test_rounding(self):
        """ Checks we round up when bringing goods to produce and round half-up when producing.
        This implementation allows to implement an efficiency notion (see rev 347f140fe63612ee05e).
        """
        self.product_6.uom_id.rounding = 1.0
        bom_eff = self.env['mrp.bom'].create({
            'product_id': self.product_6.id,
            'product_tmpl_id': self.product_6.product_tmpl_id.id,
            'product_qty': 1,
            'product_uom_id': self.product_6.uom_id.id,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': self.product_2.id, 'product_qty': 2.03}),
                (0, 0, {'product_id': self.product_8.id, 'product_qty': 4.16})
            ]
        })
        production_form = Form(self.env['mrp.production'])
        production_form.product_id = self.product_6
        production_form.bom_id = bom_eff
        production_form.product_qty = 20
        production_form.product_uom_id = self.product_6.uom_id
        production = production_form.save()
        production.action_confirm()
        #Check the production order has the right quantities
        self.assertEqual(production.move_raw_ids[0].product_qty, 41, 'The quantity should be rounded up')
        self.assertEqual(production.move_raw_ids[1].product_qty, 84, 'The quantity should be rounded up')

        # produce product
        mo_form = Form(production)
        mo_form.qty_producing = 8
        production = mo_form.save()
        self.assertEqual(production.move_raw_ids[0].quantity, 16, 'Should use half-up rounding when producing')
        self.assertEqual(production.move_raw_ids[1].quantity, 34, 'Should use half-up rounding when producing')

    def test_product_produce_1(self):
        """ Checks the production wizard contains lines even for untracked products. """
        self.stock_location = self.env.ref('stock.stock_location_stock')
        mo, bom, p_final, p1, p2 = self.generate_mo()
        self.assertEqual(len(mo), 1, 'MO should have been created')

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 100)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 5)

        mo.action_assign()

        # change the quantity done in one line
        details_operation_form = Form(mo.move_raw_ids[0], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.quantity = 1
        details_operation_form.save()

        # change the quantity producing
        mo_form = Form(mo)
        mo_form.qty_producing = 3

        # check than all quantities are update correctly
        self.assertEqual(mo_form.move_raw_ids._records[0]['product_uom_qty'], 5, "Wrong quantity to consume")
        self.assertEqual(mo_form.move_raw_ids._records[0]['quantity'], 3, "Wrong quantity done")
        self.assertEqual(mo_form.move_raw_ids._records[1]['product_uom_qty'], 20, "Wrong quantity to consume")
        self.assertEqual(mo_form.move_raw_ids._records[1]['quantity'], 12, "Wrong quantity done")

    def test_product_produce_2(self):
        """ Checks that, for a BOM where one of the components is tracked by serial number and the
        other is not tracked, when creating a manufacturing order for two finished products and
        reserving, the produce wizards proposes the corrects lines when producing one at a time.
        """
        self.stock_location = self.env.ref('stock.stock_location_stock')
        mo, bom, p_final, p1, p2 = self.generate_mo(tracking_base_1='serial', qty_base_1=1, qty_final=2)
        self.assertEqual(len(mo), 1, 'MO should have been created')

        lot_p1_1 = self.env['stock.lot'].create({
            'name': 'lot1',
            'product_id': p1.id,
        })
        lot_p1_2 = self.env['stock.lot'].create({
            'name': 'lot2',
            'product_id': p1.id,
        })

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 1, lot_id=lot_p1_1)
        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 1, lot_id=lot_p1_2)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 5)

        mo.action_assign()

        self.assertEqual(len(mo.move_raw_ids.move_line_ids), 3, 'You should have 3 stock move lines. One for each serial to consume and for the untracked product.')
        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo = mo_form.save()

        # get the proposed lot
        details_operation_form = Form(mo.move_raw_ids.filtered(lambda move: move.product_id == p1), view=self.env.ref('stock.view_stock_move_operations'))
        self.assertEqual(len(details_operation_form.move_line_ids), 1)
        with details_operation_form.move_line_ids.edit(0) as ml:
            consumed_lots = ml.lot_id
            ml.quantity = 1
        details_operation_form.save()

        remaining_lot = (lot_p1_1 | lot_p1_2) - consumed_lots
        remaining_lot.ensure_one()
        action = mo.button_mark_done()
        backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder.save().action_backorder()

        # Check MO backorder
        mo_backorder = mo.procurement_group_id.mrp_production_ids[-1]

        mo_form = Form(mo_backorder)
        mo_form.qty_producing = 1
        mo_backorder = mo_form.save()
        details_operation_form = Form(mo_backorder.move_raw_ids.filtered(lambda move: move.product_id == p1), view=self.env.ref('stock.view_stock_move_operations'))
        self.assertEqual(len(details_operation_form.move_line_ids), 1)
        with details_operation_form.move_line_ids.edit(0) as ml:
            self.assertEqual(ml.lot_id, remaining_lot)

    def test_product_produce_3(self):
        """ Checks that, for a BOM where one of the components is tracked by lot and the other is
        not tracked, when creating a manufacturing order for 1 finished product and reserving, the
        reserved lines are displayed. Then, over-consume by creating new line.
        """
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.stock_shelf_1 = self.stock_location_components

        self.stock_shelf_2 = self.stock_location_14
        mo, _, p_final, p1, p2 = self.generate_mo(tracking_base_1='lot', qty_base_1=10, qty_final=1)

        # Required for `lot_producing_id` to be visible in the view
        # <field name="lot_producing_id" invisible="product_tracking in ('none', False)"/>
        p_final.tracking = 'lot'

        self.assertEqual(len(mo), 1, 'MO should have been created')

        first_lot_for_p1 = self.env['stock.lot'].create({
            'name': 'lot1',
            'product_id': p1.id,
        })
        second_lot_for_p1 = self.env['stock.lot'].create({
            'name': 'lot2',
            'product_id': p1.id,
        })

        final_product_lot = self.env['stock.lot'].create({
            'name': 'lot1',
            'product_id': p_final.id,
        })

        self.env['stock.quant']._update_available_quantity(p1, self.stock_shelf_1, 3, lot_id=first_lot_for_p1)
        self.env['stock.quant']._update_available_quantity(p1, self.stock_shelf_2, 3, lot_id=first_lot_for_p1)
        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 8, lot_id=second_lot_for_p1)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 5)

        mo.action_assign()
        mo_form = Form(mo)
        mo_form.qty_producing = 1.0
        mo_form.lot_producing_id = final_product_lot
        mo = mo_form.save()
        # p2
        details_operation_form = Form(mo.move_raw_ids[0], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.new() as line:
            line.quantity = 1
        details_operation_form.save()

        # p1
        details_operation_form = Form(mo.move_raw_ids[1], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.new() as line:
            line.quantity = 2
            line.lot_id = first_lot_for_p1
        with details_operation_form.move_line_ids.new() as line:
            line.quantity = 1
            line.lot_id = second_lot_for_p1
        details_operation_form.save()

        move_1 = mo.move_raw_ids.filtered(lambda m: m.product_id == p1)
        # quantity/reserved_uom_qty lot
        # 3/3 lot 1 shelf 1
        # 1/1 lot 1 shelf 2
        # 2/2 lot 1 shelf 2
        # 2/0 lot 1 other
        # 5/4 lot 2
        ml_to_shelf_1 = move_1.move_line_ids.filtered(lambda ml: ml.lot_id == first_lot_for_p1 and ml.location_id == self.stock_shelf_1)
        ml_to_shelf_2 = move_1.move_line_ids.filtered(lambda ml: ml.lot_id == first_lot_for_p1 and ml.location_id == self.stock_shelf_2)

        self.assertEqual(sum(ml_to_shelf_1.mapped('quantity')), 3.0, '3 units should be took from shelf1 as reserved.')
        self.assertEqual(sum(ml_to_shelf_2.mapped('quantity')), 3.0, '3 units should be took from shelf2 as reserved.')
        self.assertEqual(move_1.quantity, 13, 'You should have used the tem units.')

        mo.button_mark_done()
        self.assertEqual(mo.state, 'done', "Production order should be in done state.")

    def test_product_produce_4(self):
        """ Possibility to produce with a given raw material in multiple locations. """
        # FIXME sle: how is it possible to consume before producing in the interface?
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.stock_shelf_1 = self.stock_location_components
        self.stock_shelf_2 = self.stock_location_14
        mo, _, p_final, p1, p2 = self.generate_mo(qty_final=1, qty_base_1=5)

        self.env['stock.quant']._update_available_quantity(p1, self.stock_shelf_1, 2)
        self.env['stock.quant']._update_available_quantity(p1, self.stock_shelf_2, 3)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 1)

        mo.action_assign()
        ml_p1 = mo.move_raw_ids.filtered(lambda x: x.product_id == p1).mapped('move_line_ids')
        ml_p2 = mo.move_raw_ids.filtered(lambda x: x.product_id == p2).mapped('move_line_ids')
        self.assertEqual(len(ml_p1), 2)
        self.assertEqual(len(ml_p2), 1)

        # Produce baby!
        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo = mo_form.save()

        m_p1 = mo.move_raw_ids.filtered(lambda x: x.product_id == p1)
        ml_p1 = m_p1.mapped('move_line_ids')
        self.assertEqual(len(ml_p1), 2)
        self.assertEqual(sorted(ml_p1.mapped('quantity')), [2.0, 3.0], 'Quantity should be 2.0 and 3.0')
        self.assertEqual(m_p1.quantity, 5.0, 'Total qty done should be 5.0')

        mo.button_mark_done()
        self.assertEqual(mo.state, 'done', "Production order should be in done state.")

    def test_product_produce_6(self):
        """ Plan 5 finished products, reserve and produce 3. Post the current production.
        Simulate an unlock and edit and, on the opened moves, set the consumed quantity
        to 3. Now, try to update the quantity to mo2 to 3. It should fail since there
        are consumed quantities. Unlock and edit, remove the consumed quantities and
        update the quantity to produce to 3."""
        self.stock_location = self.env.ref('stock.stock_location_stock')
        mo, bom, p_final, p1, p2 = self.generate_mo()
        self.assertEqual(len(mo), 1, 'MO should have been created')

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 20)

        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 5)
        mo.action_assign()

        mo_form = Form(mo)
        mo_form.qty_producing = 3
        mo = mo_form.save()

        mo._post_inventory()
        self.assertEqual(len(mo.move_raw_ids), 4)

        mo.move_raw_ids.filtered(lambda m: m.state != 'done')[0].quantity = 3

        update_quantity_wizard = self.env['change.production.qty'].create({
            'mo_id': mo.id,
            'product_qty': 3,
        })

        mo.move_raw_ids.filtered(lambda m: m.state != 'done')[0].quantity = 0
        update_quantity_wizard.change_prod_qty()

        self.assertEqual(len(mo.move_raw_ids), 4)

        mo.move_raw_ids.picked = True
        mo.button_mark_done()
        self.assertTrue(all(s in ['done', 'cancel'] for s in mo.move_raw_ids.mapped('state')))

    def test_product_produce_7(self):
        """ Plan 2 finished products, reserve and produce 3. Post the current production.
        Simulate an unlock and edit and, on the opened moves, set the consumed quantity
        to 5, and to 4. Check the component quantity removed from inventory is correct."""
        self.stock_location = self.env.ref('stock.stock_location_stock')
        mo, _, _, p1, p2 = self.generate_mo(qty_final=1)
        self.assertEqual(len(mo), 1, 'MO should have been created')

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 20)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 5)
        mo.action_assign()

        mo_form = Form(mo)
        mo_form.qty_producing = 2
        mo = mo_form.save()
        mo.button_mark_done()
        self.assertEqual(sum(mo.move_finished_ids.move_line_ids.mapped('quantity')), 2)
        self.assertTrue(mo.is_locked)

        mo.action_toggle_is_locked()
        self.assertFalse(mo.is_locked)
        mo_form = Form(mo)
        mo_form.qty_producing = 5
        mo = mo_form.save()
        self.assertAlmostEqual(sum(mo.move_finished_ids.move_line_ids.mapped('quantity')), 5)

        mo_form = Form(mo)
        mo_form.qty_producing = 4
        mo = mo_form.save()
        self.assertAlmostEqual(sum(mo.move_finished_ids.move_line_ids.mapped('quantity')), 4)

    def test_consumption_strict_1(self):
        """ Checks the constraints of a strict BOM without tracking when playing around
        quantities to consume."""
        self.stock_location = self.env.ref('stock.stock_location_stock')
        mo, bom, p_final, p1, p2 = self.generate_mo(consumption='strict', qty_final=1)
        self.assertEqual(len(mo), 1, 'MO should have been created')

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 100)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 5)

        mo.action_assign()

        mo_form = Form(mo)

        # try adding another line for a bom product to increase the quantity
        mo_form.qty_producing = 1
        with mo_form.move_raw_ids.new() as line:
            line.product_id = p1
        mo = mo_form.save()
        details_operation_form = Form(mo.move_raw_ids[-1], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.new() as ml:
            ml.quantity = 1
        details_operation_form.save()
        # Won't accept to be done, instead return a wizard
        mo.button_mark_done()
        self.assertEqual(mo.state, 'to_close')
        consumption_issues = mo._get_consumption_issues()
        action = mo._action_generate_consumption_wizard(consumption_issues)
        warning = Form(self.env['mrp.consumption.warning'].with_context(**action['context']))
        warning = warning.save()

        self.assertEqual(len(warning.mrp_consumption_warning_line_ids), 1)
        self.assertEqual(warning.mrp_consumption_warning_line_ids[0].product_consumed_qty_uom, 5)
        self.assertEqual(warning.mrp_consumption_warning_line_ids[0].product_expected_qty_uom, 4)
        # Force the warning (as a manager)
        warning.action_confirm()
        self.assertEqual(mo.state, 'done')

    def test_consumption_warning_1(self):
        """ Checks the constraints of a strict BOM without tracking when playing around
        quantities to consume."""
        self.stock_location = self.env.ref('stock.stock_location_stock')
        mo, bom, p_final, p1, p2 = self.generate_mo(consumption='warning', qty_final=1)
        self.assertEqual(len(mo), 1, 'MO should have been created')

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 100)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 5)

        mo.action_assign()

        mo_form = Form(mo)

        # try adding another line for a bom product to increase the quantity
        mo_form.qty_producing = 1
        with mo_form.move_raw_ids.new() as line:
            line.product_id = p1
        mo = mo_form.save()
        details_operation_form = Form(mo.move_raw_ids[-1], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.new() as ml:
            ml.quantity = 1
        details_operation_form.save()

        # Won't accept to be done, instead return a wizard
        mo.button_mark_done()
        self.assertEqual(mo.state, 'to_close')

        consumption_issues = mo._get_consumption_issues()
        action = mo._action_generate_consumption_wizard(consumption_issues)
        warning = Form(self.env['mrp.consumption.warning'].with_context(**action['context']))
        warning = warning.save()

        self.assertEqual(len(warning.mrp_consumption_warning_line_ids), 1)
        self.assertEqual(warning.mrp_consumption_warning_line_ids[0].product_consumed_qty_uom, 5)
        self.assertEqual(warning.mrp_consumption_warning_line_ids[0].product_expected_qty_uom, 4)
        # Force the warning (as a manager or employee)
        warning.action_confirm()
        self.assertEqual(mo.state, 'done')

    def test_consumption_flexible_1(self):
        """ Checks the constraints of a strict BOM without tracking when playing around
        quantities to consume."""
        self.stock_location = self.env.ref('stock.stock_location_stock')
        mo, bom, p_final, p1, p2 = self.generate_mo(consumption='flexible', qty_final=1)
        self.assertEqual(len(mo), 1, 'MO should have been created')

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 100)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 5)

        mo.action_assign()

        mo_form = Form(mo)

        # try adding another line for a bom product to increase the quantity
        mo_form.qty_producing = 1
        with mo_form.move_raw_ids.new() as line:
            line.product_id = p1
        mo = mo_form.save()
        details_operation_form = Form(mo.move_raw_ids[-1], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.new() as ml:
            ml.quantity = 1
        details_operation_form.save()

        # Won't accept to be done, instead return a wizard
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')

    def test_consumption_flexible_2(self):
        """ Checks the constraints of a strict BOM only apply to the product of the BoM. """
        self.stock_location = self.env.ref('stock.stock_location_stock')
        mo, bom, p_final, p1, p2 = self.generate_mo(consumption='flexible', qty_final=1)
        self.assertEqual(len(mo), 1, 'MO should have been created')

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 100)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 5)
        add_product = self.env['product.product'].create({
            'name': 'additional',
            'is_storable': True,
        })
        mo.action_assign()

        mo_form = Form(mo)

        # try adding another line for a bom product to increase the quantity
        mo_form.qty_producing = 1
        with mo_form.move_raw_ids.new() as line:
            line.product_id = p1
        with mo_form.move_raw_ids.new() as line:
            line.product_id = add_product
        mo = mo_form.save()
        details_operation_form = Form(mo.move_raw_ids[-1], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.new() as ml:
            ml.quantity = 1
        details_operation_form.save()

        # Won't accept to be done, instead return a wizard
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')

    def test_product_produce_9(self):
        """ Checks the production wizard contains lines even for untracked products. """
        serial = self.env['product.product'].create({
            'name': 'S1',
            'tracking': 'serial',
        })
        self.stock_location = self.env.ref('stock.stock_location_stock')
        mo, bom, p_final, p1, p2 = self.generate_mo()
        self.assertEqual(len(mo), 1, 'MO should have been created')

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 100)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 5)

        mo.action_assign()
        mo_form = Form(mo)

        # change the quantity done in one line
        with self.assertRaises(AssertionError):
            with mo_form.move_raw_ids.new() as move:
                move.product_id = serial
                move.quantity = 2
            mo_form.save()

    def test_product_produce_10(self):
        """ Produce byproduct with serial, lot and not tracked.
        byproduct1 serial 1.0
        byproduct2 lot    2.0
        byproduct3 none   1.0 dozen
        Check qty producing update and moves finished values.
        """
        # Required for `byproduct_ids` to be visible in the view
        self.env.user.groups_id += self.env.ref('mrp.group_mrp_byproducts')
        dozen = self.env.ref('uom.product_uom_dozen')
        self.byproduct1 = self.env['product.product'].create({
            'name': 'Byproduct 1',
            'is_storable': True,
            'tracking': 'serial'
        })
        self.serial_1 = self.env['stock.lot'].create({
            'product_id': self.byproduct1.id,
            'name': 'serial 1',
        })
        self.serial_2 = self.env['stock.lot'].create({
            'product_id': self.byproduct1.id,
            'name': 'serial 2',
        })

        self.byproduct2 = self.env['product.product'].create({
            'name': 'Byproduct 2',
            'is_storable': True,
            'tracking': 'lot',
        })
        self.lot_1 = self.env['stock.lot'].create({
            'product_id': self.byproduct2.id,
            'name': 'Lot 1',
        })
        self.lot_2 = self.env['stock.lot'].create({
            'product_id': self.byproduct2.id,
            'name': 'Lot 2',
        })

        self.byproduct3 = self.env['product.product'].create({
            'name': 'Byproduct 3',
            'is_storable': True,
            'tracking': 'none',
        })

        with Form(self.bom_1) as bom:
            bom.product_qty = 1.0
            with bom.byproduct_ids.new() as bp:
                bp.product_id = self.byproduct1
                bp.product_qty = 1.0
            with bom.byproduct_ids.new() as bp:
                bp.product_id = self.byproduct2
                bp.product_qty = 2.0
            with bom.byproduct_ids.new() as bp:
                bp.product_id = self.byproduct3
                bp.product_qty = 2.0
                bp.product_uom_id = dozen

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_4
        mo_form.bom_id = self.bom_1
        mo_form.product_qty = 2
        mo = mo_form.save()

        mo.action_confirm()
        move_byproduct_1 = mo.move_finished_ids.filtered(lambda l: l.product_id == self.byproduct1)
        self.assertEqual(len(move_byproduct_1), 1)
        self.assertEqual(move_byproduct_1.product_uom_qty, 2.0)
        self.assertEqual(move_byproduct_1.quantity, 2)
        self.assertEqual(len(move_byproduct_1.move_line_ids), 2)

        move_byproduct_2 = mo.move_finished_ids.filtered(lambda l: l.product_id == self.byproduct2)
        self.assertEqual(len(move_byproduct_2), 1)
        self.assertEqual(move_byproduct_2.product_uom_qty, 4.0)
        self.assertEqual(move_byproduct_2.quantity, 4)
        self.assertEqual(len(move_byproduct_2.move_line_ids), 1)

        move_byproduct_3 = mo.move_finished_ids.filtered(lambda l: l.product_id == self.byproduct3)
        self.assertEqual(move_byproduct_3.product_uom_qty, 4.0)
        self.assertEqual(move_byproduct_3.quantity, 4)
        self.assertEqual(move_byproduct_3.product_uom, dozen)
        self.assertEqual(len(move_byproduct_3.move_line_ids), 1)

        mo_form = Form(mo)
        mo_form.qty_producing = 1.0
        mo = mo_form.save()
        move_byproduct_1 = mo.move_finished_ids.filtered(lambda l: l.product_id == self.byproduct1)
        self.assertEqual(len(move_byproduct_1), 1)
        self.assertEqual(move_byproduct_1.product_uom_qty, 2.0)
        self.assertEqual(move_byproduct_1.quantity, 1)
        self.assertTrue(move_byproduct_1.picked)

        move_byproduct_2 = mo.move_finished_ids.filtered(lambda l: l.product_id == self.byproduct2)
        self.assertEqual(len(move_byproduct_2), 1)
        self.assertEqual(move_byproduct_2.product_uom_qty, 4.0)
        self.assertEqual(move_byproduct_2.quantity, 2)
        self.assertTrue(move_byproduct_2.picked)

        move_byproduct_3 = mo.move_finished_ids.filtered(lambda l: l.product_id == self.byproduct3)
        self.assertEqual(move_byproduct_3.product_uom_qty, 4.0)
        self.assertEqual(move_byproduct_3.quantity, 2.0)
        self.assertTrue(move_byproduct_3.picked)
        self.assertEqual(move_byproduct_3.product_uom, dozen)

        details_operation_form = Form(move_byproduct_1, view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.lot_id = self.serial_1
        details_operation_form.save()
        details_operation_form = Form(move_byproduct_2, view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.lot_id = self.lot_1
        details_operation_form.save()
        action = mo.button_mark_done()
        backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder.save().action_backorder()
        mo2 = mo.procurement_group_id.mrp_production_ids[-1]

        mo_form = Form(mo2)
        mo_form.qty_producing = 1
        mo2 = mo_form.save()

        move_byproduct_1 = mo2.move_finished_ids.filtered(lambda l: l.product_id == self.byproduct1)
        self.assertEqual(len(move_byproduct_1), 1)
        self.assertEqual(move_byproduct_1.product_uom_qty, 1.0)
        self.assertEqual(move_byproduct_1.quantity, 1)
        self.assertTrue(move_byproduct_1.picked)

        move_byproduct_2 = mo2.move_finished_ids.filtered(lambda l: l.product_id == self.byproduct2)
        self.assertEqual(len(move_byproduct_2), 1)
        self.assertEqual(move_byproduct_2.product_uom_qty, 2.0)
        self.assertEqual(move_byproduct_2.quantity, 2)
        self.assertTrue(move_byproduct_2.picked)

        move_byproduct_3 = mo2.move_finished_ids.filtered(lambda l: l.product_id == self.byproduct3)
        self.assertEqual(move_byproduct_3.product_uom_qty, 2.0)
        self.assertEqual(move_byproduct_3.quantity, 2.0)
        self.assertTrue(move_byproduct_3.picked)
        self.assertEqual(move_byproduct_3.product_uom, dozen)

        details_operation_form = Form(move_byproduct_1, view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.lot_id = self.serial_2
            ml.quantity = 1
        details_operation_form.save()
        details_operation_form = Form(move_byproduct_2, view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.lot_id = self.lot_2
        details_operation_form.save()
        details_operation_form = Form(move_byproduct_3, view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.quantity = 3
        details_operation_form.save()

        mo2.button_mark_done()
        move_lines_byproduct_1 = (mo | mo2).move_finished_ids.filtered(lambda l: l.product_id == self.byproduct1).mapped('move_line_ids')
        move_lines_byproduct_2 = (mo | mo2).move_finished_ids.filtered(lambda l: l.product_id == self.byproduct2).mapped('move_line_ids')
        move_lines_byproduct_3 = (mo | mo2).move_finished_ids.filtered(lambda l: l.product_id == self.byproduct3).mapped('move_line_ids')
        self.assertEqual(move_lines_byproduct_1.filtered(lambda ml: ml.lot_id == self.serial_1).quantity, 1.0)
        self.assertEqual(move_lines_byproduct_1.filtered(lambda ml: ml.lot_id == self.serial_2).quantity, 1.0)
        self.assertEqual(move_lines_byproduct_2.filtered(lambda ml: ml.lot_id == self.lot_1).quantity, 2.0)
        self.assertEqual(move_lines_byproduct_2.filtered(lambda ml: ml.lot_id == self.lot_2).quantity, 2.0)
        self.assertEqual(sum(move_lines_byproduct_3.mapped('quantity')), 5.0)
        self.assertEqual(move_lines_byproduct_3.mapped('product_uom_id'), dozen)

    def test_product_produce_11(self):
        """ Checks that, for a BOM with two components, when creating a manufacturing order for one
        finished products and without reserving, the produce wizards proposes the corrects lines
        even if we change the quantity to produce multiple times.
        """
        self.stock_location = self.env.ref('stock.stock_location_stock')
        mo, bom, p_final, p1, p2 = self.generate_mo(qty_final=1)
        self.assertEqual(len(mo), 1, 'MO should have been created')

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 4)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 1)

        mo.bom_id.consumption = 'flexible'  # Because we'll over-consume with a product not defined in the BOM
        mo.action_assign()
        mo.is_locked = False

        mo_form = Form(mo)
        mo_form.qty_producing = 3
        self.assertEqual(sum([x['quantity'] for x in mo_form.move_raw_ids._records]), 15, 'Update the produce quantity should change the components quantity.')
        mo = mo_form.save()
        mo_form = Form(mo)
        mo_form.qty_producing = 4
        self.assertEqual(sum([x['quantity'] for x in mo_form.move_raw_ids._records]), 20, 'Update the produce quantity should change the components quantity.')
        mo = mo_form.save()
        mo_form = Form(mo)
        mo_form.qty_producing = 1
        self.assertEqual(sum([x['quantity'] for x in mo_form.move_raw_ids._records]), 5, 'Update the produce quantity should change the components quantity.')
        mo = mo_form.save()
        # try adding another product that doesn't belong to the BoM
        with mo_form.move_raw_ids.new() as move:
            move.product_id = self.product_4
        mo = mo_form.save()
        details_operation_form = Form(mo.move_raw_ids[-1], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.new() as ml:
            ml.quantity = 10
        details_operation_form.save()
        # Check that this new product is not updated by qty_producing
        mo_form = Form(mo)
        mo_form.qty_producing = 2
        for move in mo_form.move_raw_ids._records:
            if move['product_id'] == self.product_4.id:
                self.assertEqual(move['quantity'], 10)
                break
        mo = mo_form.save()
        mo.button_mark_done()

    def test_product_produce_duplicate_1(self):
        """ produce a finished product tracked by serial number 2 times with the
        same SN. Check that an error is raised the second time"""
        mo1, bom, p_final, p1, p2 = self.generate_mo(tracking_final='serial', qty_final=1, qty_base_1=1,)

        mo_form = Form(mo1)
        mo_form.qty_producing = 1
        mo1 = mo_form.save()
        mo1.action_generate_serial()
        sn = mo1.lot_producing_id
        mo1.button_mark_done()

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = p_final
        mo_form.bom_id = bom
        mo_form.product_qty = 1
        mo2 = mo_form.save()
        mo2.action_confirm()

        mo_form = Form(mo2)
        with self.assertLogs(level="WARNING"):
            mo_form.lot_producing_id = sn
        mo2 = mo_form.save()
        with self.assertRaises(UserError):
            mo2.button_mark_done()

    def test_product_produce_duplicate_2(self):
        """ produce a finished product with component tracked by serial number 2
        times with the same SN. Check that an error is raised the second time"""
        mo1, bom, p_final, p1, p2 = self.generate_mo(tracking_base_2='serial', qty_final=1, qty_base_1=1,)
        sn = self.env['stock.lot'].create({
            'name': 'sn used twice',
            'product_id': p2.id,
        })
        mo_form = Form(mo1)
        mo_form.qty_producing = 1
        mo1 = mo_form.save()
        details_operation_form = Form(mo1.move_raw_ids[0], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.lot_id = sn
        details_operation_form.save()
        mo1.move_raw_ids.picked = True
        mo1.button_mark_done()

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = p_final
        mo_form.bom_id = bom
        mo_form.product_qty = 1
        mo2 = mo_form.save()
        mo2.action_confirm()

        mo_form = Form(mo2)
        mo_form.qty_producing = 1
        mo2 = mo_form.save()
        details_operation_form = Form(mo2.move_raw_ids[0], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.lot_id = sn
        details_operation_form.save()
        mo2.move_raw_ids.picked = True
        with self.assertRaises(UserError):
            mo2.button_mark_done()

    def test_product_produce_duplicate_3(self):
        """ produce a finished product with by-product tracked by serial number 2
        times with the same SN. Check that an error is raised the second time"""
        finished_product = self.env['product.product'].create({'name': 'finished product'})
        byproduct = self.env['product.product'].create({'name': 'byproduct', 'tracking': 'serial'})
        component = self.env['product.product'].create({'name': 'component'})
        bom = self.env['mrp.bom'].create({
            'product_id': finished_product.id,
            'product_tmpl_id': finished_product.product_tmpl_id.id,
            'product_uom_id': finished_product.uom_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': component.id, 'product_qty': 1}),
            ],
            'byproduct_ids': [
                (0, 0, {'product_id': byproduct.id, 'product_qty': 1, 'product_uom_id': byproduct.uom_id.id})
            ]})
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = finished_product
        mo_form.bom_id = bom
        mo_form.product_qty = 1
        mo = mo_form.save()
        mo.action_confirm()

        sn = self.env['stock.lot'].create({
            'name': 'sn used twice',
            'product_id': byproduct.id,
        })

        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo = mo_form.save()
        move_byproduct = mo.move_finished_ids.filtered(lambda m: m.product_id != mo.product_id)
        details_operation_form = Form(move_byproduct, view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.lot_id = sn
        details_operation_form.save()
        mo.button_mark_done()

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = finished_product
        mo_form.bom_id = bom
        mo_form.product_qty = 1
        mo2 = mo_form.save()
        mo2.action_confirm()

        mo_form = Form(mo2)
        mo_form.qty_producing = 1
        mo2 = mo_form.save()
        move_byproduct = mo2.move_finished_ids.filtered(lambda m: m.product_id != mo.product_id)
        details_operation_form = Form(move_byproduct, view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.new() as ml:
            ml.lot_id = sn
        details_operation_form.save()
        with self.assertRaises(UserError):
            mo2.button_mark_done()

    def test_product_produce_duplicate_4(self):
        """ Consuming the same serial number two times should not give an error if
        a repair order of the first production has been made before the second one"""
        mo1, bom, p_final, p1, p2 = self.generate_mo(tracking_base_2='serial', qty_final=1, qty_base_1=1,)
        sn = self.env['stock.lot'].create({
            'name': 'sn used twice',
            'product_id': p2.id,
        })
        mo_form = Form(mo1)
        mo_form.qty_producing = 1
        mo1 = mo_form.save()
        details_operation_form = Form(mo1.move_raw_ids[0], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.lot_id = sn
        details_operation_form.save()
        mo1.move_raw_ids.picked = True
        mo1.button_mark_done()

        unbuild_form = Form(self.env['mrp.unbuild'])
        unbuild_form.product_id = p_final
        unbuild_form.bom_id = bom
        unbuild_form.product_qty = 1
        unbuild_form.mo_id = mo1
        unbuild_order = unbuild_form.save()
        unbuild_order.action_unbuild()

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = p_final
        mo_form.bom_id = bom
        mo_form.product_qty = 1
        mo2 = mo_form.save()
        mo2.action_confirm()

        mo_form = Form(mo2)
        mo_form.qty_producing = 1
        mo2 = mo_form.save()
        details_operation_form = Form(mo2.move_raw_ids[0], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.lot_id = sn
        details_operation_form.save()
        mo2.move_raw_ids.picked = True
        mo2.button_mark_done()

    def test_product_produce_duplicate_5(self):
        """Produce a subassembly for the second time with the same serial
        after having unbuilt both the subassembly and finished good it was part of"""
        subassembly_product = self.env["product.product"].create(
            {
                "name": "Subassembly",
                "is_storable": True,
                "tracking": "serial",
            }
        )

        subassembly_sn = self.env["stock.lot"].create(
            {
                "name": "SN",
                "product_id": subassembly_product.id,
            }
        )

        subassembly_mo1_form = Form(self.env["mrp.production"])
        subassembly_mo1_form.product_id = subassembly_product
        subassembly_mo1 = subassembly_mo1_form.save()
        subassembly_mo1.action_confirm()
        with Form(subassembly_mo1) as mo:
            mo.qty_producing = 1
        subassembly_mo1.lot_producing_id = subassembly_sn
        subassembly_mo1.button_mark_done()

        finished_good_product = self.env["product.product"].create(
            {
                "name": "Finished Good",
                "is_storable": True,
                "tracking": "serial",
            }
        )
        finished_good_product_bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished_good_product.product_tmpl_id.id,
                "product_qty": 1,
                "type": "normal",
                "bom_line_ids": [
                    (0, 0, {"product_id": subassembly_product.id, "product_qty": 1}),
                ],
            }
        )
        finished_good_mo_form = Form(self.env["mrp.production"])
        finished_good_mo_form.product_id = finished_good_product
        finished_good_mo_form.bom_id = finished_good_product_bom
        finished_good_mo = finished_good_mo_form.save()
        finished_good_mo.action_confirm()
        with Form(finished_good_mo) as mo:
            mo.qty_producing = 1
        finished_good_mo.action_generate_serial()
        finished_good_detailed_operations_form = Form(
            finished_good_mo.move_raw_ids[0],
            view=self.env.ref("stock.view_stock_move_operations"),
        )
        with finished_good_detailed_operations_form.move_line_ids.edit(0) as ml:
            ml.quantity = 1
            ml.lot_id = subassembly_sn
        finished_good_detailed_operations_form.save()
        finished_good_mo.move_raw_ids.picked = True
        finished_good_mo.button_mark_done()

        finished_good_ub_form = Form(self.env["mrp.unbuild"])
        finished_good_ub_form.mo_id = finished_good_mo
        finished_good_ub = finished_good_ub_form.save()
        finished_good_ub.action_unbuild()

        subassembly_ub_form = Form(self.env["mrp.unbuild"])
        subassembly_ub_form.mo_id = subassembly_mo1
        subassembly_ub = subassembly_ub_form.save()
        subassembly_ub.action_unbuild()

        subassembly_mo2_form = Form(self.env["mrp.production"])
        subassembly_mo2_form.product_id = subassembly_product
        subassembly_mo2 = subassembly_mo2_form.save()
        subassembly_mo2.action_confirm()
        with Form(subassembly_mo2) as mo:
            mo.qty_producing = 1
        subassembly_mo2.lot_producing_id = subassembly_sn
        subassembly_mo2.button_mark_done()

    def test_product_produce_duplicate_6(self):
        """Produce a product for the second time with the same serial
        after having unbuilt, scrapped and unscrapped the product"""
        product = self.env["product.product"].create(
            {
                "name": "Product",
                "is_storable": True,
                "tracking": "serial",
            }
        )

        sn = self.env["stock.lot"].create(
            {
                "name": "SN",
                "product_id": product.id,
            }
        )

        mo1_form = Form(self.env["mrp.production"])
        mo1_form.product_id = product
        mo1 = mo1_form.save()
        mo1.action_confirm()
        with Form(mo1) as mo:
            mo.qty_producing = 1
        mo1.lot_producing_id = sn
        mo1.button_mark_done()

        ub_form = Form(self.env["mrp.unbuild"])
        ub_form.mo_id = mo1
        ub = ub_form.save()
        ub.action_unbuild()

        scrap = self.env['stock.scrap'].create({
            'product_id': product.id,
            'product_uom_id': product.uom_id.id,
            'lot_id': sn.id,
        })
        scrap.do_scrap()

        unscrap_picking = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_internal').id,
            'location_id': scrap.scrap_location_id.id,
            'location_dest_id': scrap.location_id.id,
        })
        unscrap_move = self.env['stock.move'].create({
            'name': 'unscrap',
            'location_id': scrap.scrap_location_id.id,
            'location_dest_id': scrap.location_id.id,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'picking_id': unscrap_picking.id,
        })
        unscrap_picking.action_confirm()
        self.env['stock.move.line'].create({
            'move_id': unscrap_move.id,
            'product_id': unscrap_move.product_id.id,
            'lot_id': sn.id,
            'quantity': 1,
            'product_uom_id': unscrap_move.product_uom.id,
            'picking_id': unscrap_move.picking_id.id,
        })
        unscrap_picking.button_validate()

        mo2_form = Form(self.env["mrp.production"])
        mo2_form.product_id = product
        mo2 = mo2_form.save()
        mo2.action_confirm()
        with Form(mo2) as mo:
            mo.qty_producing = 1
        mo2.lot_producing_id = sn
        mo2.button_mark_done()

    def test_product_produce_12(self):
        """ Checks that, the production is robust against deletion of finished move."""

        self.stock_location = self.env.ref('stock.stock_location_stock')
        mo, bom, p_final, p1, p2 = self.generate_mo(qty_final=1)
        self.assertEqual(len(mo), 1, 'MO should have been created')

        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo = mo_form.save()
        # remove the finished move from the available to be updated
        mo.move_finished_ids._action_done()
        mo.button_mark_done()

    def test_product_produce_13(self):
        """ Check that the production can be completed without any consumption."""
        product = self.env['product.product'].create({
            'name': 'Product no BoM',
            'is_storable': True,
        })
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product
        mo = mo_form.save()
        move = self.env['stock.move'].create({
            'product_id': self.product_2.id,
            'product_uom': self.ref('uom.product_uom_unit'),
            'production_id': mo.id,
            'location_dest_id': self.ref('stock.stock_location_output'),
        })

        self.assertEqual(move.name, mo.name)
        self.assertEqual(move.origin, mo._get_origin())
        self.assertEqual(move.group_id, mo.procurement_group_id)
        self.assertEqual(move.propagate_cancel, mo.propagate_cancel)
        self.assertFalse(move.raw_material_production_id)
        self.assertEqual(move.location_id, mo.production_location_id)
        self.assertEqual(move.date, mo.date_finished)
        self.assertEqual(move.date_deadline, mo.date_deadline)

        mo.move_raw_ids |= move
        mo.action_confirm()

        mo.qty_producing = 1
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')
        self.assertEqual(mo.qty_produced, 1)
        self.assertEqual(mo.move_raw_ids.state, 'cancel')

    def test_product_produce_14(self):
        """ Check two component move with the same product are not merged."""
        product = self.env['product.product'].create({
            'name': 'Product no BoM',
            'is_storable': True,
        })
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product
        mo = mo_form.save()
        for i in range(2):
            move = self.env['stock.move'].create({
                'name': 'mrp_move_' + str(i),
                'product_id': self.product_2.id,
                'product_uom': self.ref('uom.product_uom_unit'),
                'production_id': mo.id,
                'location_id': self.ref('stock.stock_location_stock'),
                'location_dest_id': self.ref('stock.stock_location_output'),
            })
            mo.move_raw_ids |= move
        mo.action_confirm()
        self.assertEqual(len(mo.move_raw_ids), 2)

    def test_change_sn_tracked_qty_produced(self):
        """ Checks if qty_producing can be set to 0 after being set to non-zero value """
        mo_with_serial, _, _, _, _ = self.generate_mo(tracking_final='serial')
        mo_without_serial, _, _, _, _ = self.generate_mo()

        self.assertEqual(mo_with_serial.qty_producing, 0)
        self.assertEqual(mo_without_serial.qty_producing, 0)

        mo_form_with_serial = Form(mo_with_serial)
        mo_form_without_serial = Form(mo_without_serial)

        mo_form_with_serial.qty_producing = 3
        mo_form_without_serial.qty_producing = 3
        mo_with_serial = mo_form_with_serial.save()
        mo_without_serial = mo_form_without_serial.save()
        self.assertEqual(mo_with_serial.qty_producing, 1)
        self.assertEqual(mo_without_serial.qty_producing, 3)

        mo_form_with_serial = Form(mo_with_serial)
        mo_form_without_serial = Form(mo_without_serial)
        mo_form_with_serial.qty_producing = 0
        mo_form_without_serial.qty_producing = 0
        mo_with_serial = mo_form_with_serial.save()
        mo_without_serial = mo_form_without_serial.save()
        self.assertEqual(mo_with_serial.qty_producing, 0)
        self.assertEqual(mo_without_serial.qty_producing, 0)

    def test_consumed_and_produced_in_operation(self):
        """
            Check if component and byproduct quantities correctly changes when we
            update the qty_producing and mark their respective operations from Consume
            In Operation as done directly through the WO record
        """
        self.env.user.groups_id += self.env.ref('mrp.group_mrp_byproducts')
        demo = self.env['product.product'].create({
            'name': 'DEMO'
        })
        comp1 = self.env['product.product'].create({
            'name': 'COMP1'
        })
        comp2 = self.env['product.product'].create({
            'name': 'COMP2'
        })
        comp3 = self.env['product.product'].create({
            'name': 'COMP3'
        })
        bprod1 = self.env['product.product'].create({
            'name': 'BPROD1'
        })
        bprod2 = self.env['product.product'].create({
            'name': 'BPROD2'
        })
        bprod3 = self.env['product.product'].create({
            'name': 'BPROD3'
        })
        work_center_1 = self.env['mrp.workcenter'].create({"name": "WorkCenter 1", "time_start": 11})
        work_center_2 = self.env['mrp.workcenter'].create({"name": "WorkCenter 2", "time_start": 12})
        work_center_3 = self.env['mrp.workcenter'].create({"name": "WorkCenter 3", "time_start": 13})
        bom = self.env['mrp.bom'].create({
            'product_id': demo.id,
            'product_tmpl_id': demo.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'type': 'normal',
            'operation_ids': [
                Command.create({'name': 'OP1', 'workcenter_id': work_center_1.id, 'time_cycle': 12, 'sequence': 1}),
                Command.create({'name': 'OP2', 'workcenter_id': work_center_2.id, 'time_cycle': 18, 'sequence': 2}),
                Command.create({'name': 'OP3', 'workcenter_id': work_center_3.id, 'time_cycle': 24, 'sequence': 3})
            ]
        })
        self.env['mrp.bom.line'].create([
            {
                'product_id': comp.id,
                'product_qty': qty,
                'bom_id': bom.id,
                'operation_id': operation.id,
            } for (comp, qty, operation) in zip([comp1, comp2, comp3], [1.0, 2.0, 3.0], bom.operation_ids)
        ])
        self.env['mrp.bom.byproduct'].create([
            {
                'product_id': bprod.id,
                'product_qty': qty,
                'bom_id': bom.id,
                'operation_id': operation.id,
            } for (bprod, qty, operation) in zip([bprod1, bprod2, bprod3], [1.0, 2.0, 3.0], bom.operation_ids)
        ])

        def _change_qty_producing_and_finish_wo(mo, new_qty, wo_index):
            mo.qty_producing = new_qty
            self.assertEqual(mo.qty_producing, new_qty)
            wo = mo.workorder_ids.sorted()[wo_index]
            wo.button_start()
            wo.button_finish()

        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = bom
        mo_form.product_qty = 5
        mo = mo_form.save()
        mo.action_confirm()
        self.assertRecordValues(mo.move_raw_ids + mo.move_byproduct_ids, [
            {'picked': False, 'quantity': 5},
            {'picked': False, 'quantity': 10},
            {'picked': False, 'quantity': 15},
            {'picked': False, 'quantity': 5},
            {'picked': False, 'quantity': 10},
            {'picked': False, 'quantity': 15},
        ])

        self.assertEqual(mo.qty_producing, 0)
        mo.qty_producing = 5
        self.assertEqual(mo.qty_producing, 5)
        self.assertRecordValues(mo.move_raw_ids + mo.move_byproduct_ids, [
            {'picked': False, 'quantity': 5},
            {'picked': False, 'quantity': 10},
            {'picked': False, 'quantity': 15},
            {'picked': False, 'quantity': 5},
            {'picked': False, 'quantity': 10},
            {'picked': False, 'quantity': 15},
        ])

        _change_qty_producing_and_finish_wo(mo, 4, 0)
        self.assertRecordValues(mo.move_raw_ids + mo.move_byproduct_ids, [
            {'picked': True, 'quantity': 4},
            {'picked': False, 'quantity': 10},
            {'picked': False, 'quantity': 15},
            {'picked': True, 'quantity': 4},
            {'picked': False, 'quantity': 10},
            {'picked': False, 'quantity': 15},
        ])

        _change_qty_producing_and_finish_wo(mo, 3, 1)
        self.assertRecordValues(mo.move_raw_ids + mo.move_byproduct_ids, [
            {'picked': True, 'quantity': 4},
            {'picked': True, 'quantity': 6},
            {'picked': False, 'quantity': 15},
            {'picked': True, 'quantity': 4},
            {'picked': True, 'quantity': 6},
            {'picked': False, 'quantity': 15},
        ])

        _change_qty_producing_and_finish_wo(mo, 2, 2)
        self.assertRecordValues(mo.move_raw_ids + mo.move_byproduct_ids, [
            {'picked': True, 'quantity': 4},
            {'picked': True, 'quantity': 6},
            {'picked': True, 'quantity': 6},
            {'picked': True, 'quantity': 4},
            {'picked': True, 'quantity': 6},
            {'picked': True, 'quantity': 6},
        ])

    def test_product_produce_uom(self):
        """ Produce a finished product tracked by serial number. Set another
        UoM on the bom. The produce wizard should keep the UoM of the product (unit)
        and quantity = 1."""
        dozen = self.env.ref('uom.product_uom_dozen')
        unit = self.env.ref('uom.product_uom_unit')
        plastic_laminate = self.env['product.product'].create({
            'name': 'Plastic Laminate',
            'is_storable': True,
            'uom_id': unit.id,
            'uom_po_id': unit.id,
            'tracking': 'serial',
        })
        ply_veneer = self.env['product.product'].create({
            'name': 'Ply Veneer',
            'is_storable': True,
            'uom_id': unit.id,
            'uom_po_id': unit.id,
        })
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': plastic_laminate.product_tmpl_id.id,
            'product_uom_id': unit.id,
            'sequence': 1,
            'bom_line_ids': [(0, 0, {
                'product_id': ply_veneer.id,
                'product_qty': 1,
                'product_uom_id': unit.id,
                'sequence': 1,
            })]
        })

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = plastic_laminate
        mo_form.bom_id = bom
        mo_form.product_uom_id = dozen
        mo_form.product_qty = 1
        mo = mo_form.save()

        final_product_lot = self.env['stock.lot'].create({
            'name': 'lot1',
            'product_id': plastic_laminate.id,
        })

        mo.action_confirm()
        mo.action_assign()
        self.assertEqual(mo.move_raw_ids.product_qty, 12, '12 units should be reserved.')

        # produce product
        mo_form = Form(mo)
        mo_form.qty_producing = 1/12.0
        mo_form.lot_producing_id = final_product_lot
        mo = mo_form.save()

        move_line_raw = mo.move_raw_ids.mapped('move_line_ids').filtered(lambda m: m.quantity)
        self.assertEqual(move_line_raw.quantity, 1)
        self.assertEqual(move_line_raw.product_uom_id, unit, 'Should be 1 unit since the tracking is serial.')

        mo._post_inventory()
        move_line_finished = mo.move_finished_ids.move_line_ids.filtered(lambda m: m.state == 'done' and m.quantity)
        self.assertEqual(move_line_finished.quantity, 1)
        self.assertEqual(move_line_finished.product_uom_id, unit, 'Should be 1 unit since the tracking is serial.')

    def test_product_type_service_1(self):
        # Create finished product
        finished_product = self.env['product.product'].create({
            'name': 'Geyser',
            'is_storable': True,
        })

        # Create service type product
        product_raw = self.env['product.product'].create({
            'name': 'raw Geyser',
            'type': 'service',
        })

        # Create bom for finish product
        bom = self.env['mrp.bom'].create({
            'product_id': finished_product.id,
            'product_tmpl_id': finished_product.product_tmpl_id.id,
            'product_uom_id': self.env.ref('uom.product_uom_unit').id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [(5, 0), (0, 0, {'product_id': product_raw.id})]
        })

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = finished_product
        mo_form.bom_id = bom
        mo_form.product_uom_id = self.env.ref('uom.product_uom_unit')
        mo_form.product_qty = 1
        mo = mo_form.save()

        # Check Mo is created or not
        self.assertTrue(mo, "Mo is created")

    def test_immediate_validate_1(self):
        """ In a production with a single available move raw, clicking on mark as done without filling any
        quantities should open a wizard asking to process all the reservation (so, the whole move).
        """
        mo, bom, p_final, p1, p2 = self.generate_mo(qty_final=1, qty_base_1=1, qty_base_2=1)
        self.env['stock.quant']._update_available_quantity(p1, self.stock_location_components, 5.0)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location_components, 5.0)
        mo.action_assign()
        res_dict = mo.button_mark_done()
        self.assertEqual(mo.move_raw_ids.mapped('state'), ['done', 'done'])
        self.assertEqual(mo.move_raw_ids.mapped('quantity'), [1, 1])
        self.assertEqual(mo.move_finished_ids.state, 'done')
        self.assertEqual(mo.move_finished_ids.quantity, 1)

    def test_immediate_validate_3(self):
        """ In a production with a serial number tracked product. Check that the immediate production only creates
        one unit of finished product. Test with reservation."""
        mo, bom, p_final, p1, p2 = self.generate_mo(tracking_final='serial', qty_final=2, qty_base_1=1, qty_base_2=1)
        self.env['stock.quant']._update_available_quantity(p1, self.stock_location_components, 5.0)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location_components, 5.0)
        mo.action_assign()
        mo.action_generate_serial()
        action = mo.button_mark_done()
        self.assertEqual(action.get('res_model'), 'mrp.production.backorder')
        Form.from_action(self.env, action).save().action_backorder()
        self.assertEqual(mo.qty_producing, 1)
        self.assertEqual(mo.move_raw_ids.mapped('quantity'), [1, 1])
        self.assertEqual(len(mo.procurement_group_id.mrp_production_ids), 2)
        mo_backorder = mo.procurement_group_id.mrp_production_ids[-1]
        self.assertEqual(mo_backorder.product_qty, 1)
        self.assertEqual(mo_backorder.move_raw_ids.mapped('product_uom_qty'), [1, 1])

    def test_immediate_validate_4(self):
        """ In a production with a serial number tracked product. Check that the immediate production only creates
        one unit of finished product. Test without reservation."""
        mo, bom, p_final, p1, p2 = self.generate_mo(tracking_final='serial', qty_final=2, qty_base_1=1, qty_base_2=1)
        self.env['stock.quant']._update_available_quantity(p1, self.stock_location_components, 5.0)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location_components, 5.0)
        mo.action_generate_serial()
        action = mo.button_mark_done()
        self.assertEqual(action.get('res_model'), 'mrp.production.backorder')
        Form.from_action(self.env, action).save().action_backorder()
        self.assertEqual(mo.qty_producing, 1)
        self.assertEqual(mo.move_raw_ids.mapped('quantity'), [1, 1])
        self.assertEqual(len(mo.procurement_group_id.mrp_production_ids), 2)
        mo_backorder = mo.procurement_group_id.mrp_production_ids[-1]
        self.assertEqual(mo_backorder.product_qty, 1)
        self.assertEqual(mo_backorder.move_raw_ids.mapped('product_uom_qty'), [1, 1])

    def test_immediate_validate_5(self):
        """Validate three productions at once."""
        mo1, bom, p_final, p1, p2 = self.generate_mo(qty_final=1, qty_base_1=1, qty_base_2=1)
        self.env['stock.quant']._update_available_quantity(p1, self.stock_location_components, 5.0)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location_components, 5.0)
        mo1.action_assign()
        mo2_form = Form(self.env['mrp.production'])
        mo2_form.product_id = p_final
        mo2_form.bom_id = bom
        mo2_form.product_qty = 1
        mo2 = mo2_form.save()
        mo2.action_confirm()
        mo2.action_assign()
        mo3_form = Form(self.env['mrp.production'])
        mo3_form.product_id = p_final
        mo3_form.bom_id = bom
        mo3_form.product_qty = 1
        mo3 = mo3_form.save()
        mo3.action_confirm()
        mo3.action_assign()
        mos = mo1 | mo2 | mo3
        mos.button_mark_done()
        self.assertEqual(mos.move_raw_ids.mapped('state'), ['done'] * 6)
        self.assertEqual(mos.move_raw_ids.mapped('quantity'), [1] * 6)
        self.assertEqual(mos.move_finished_ids.mapped('state'), ['done'] * 3)
        self.assertEqual(mos.move_finished_ids.mapped('quantity'), [1] * 3)

    def test_components_availability(self):
        def check_availability_state(state):
            self.assertEqual(mo.components_availability_state, state)
            MO = self.env['mrp.production']
            self.assertIn(mo, MO.search([('components_availability_state', '=', state)]))
            self.assertNotIn(mo, MO.search([('components_availability_state', '!=', state)]))

        self.bom_2.unlink()  # remove the kit bom of product_5
        now = fields.Datetime.now()
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom_3  # product_5 (2), product_4 (8), product_2 (12)
        mo_form.date_start = now
        mo = mo_form.save()
        self.assertEqual(mo.components_availability, False)  # no compute for draft
        mo.action_confirm()
        self.assertEqual(mo.components_availability, 'Not Available')

        tommorrow = fields.Datetime.now() + timedelta(days=1)
        after_tommorrow = fields.Datetime.now() + timedelta(days=2)
        warehouse = self.env.ref('stock.warehouse0')
        move1 = self._create_move(
            self.product_5, self.env.ref('stock.stock_location_suppliers'), warehouse.lot_stock_id,
            product_uom_qty=2, date=tommorrow
        )
        move2 = self._create_move(
            self.product_4, self.env.ref('stock.stock_location_suppliers'), warehouse.lot_stock_id,
            product_uom_qty=8, date=tommorrow
        )
        move3 = self._create_move(
            self.product_2, self.env.ref('stock.stock_location_suppliers'), warehouse.lot_stock_id,
            product_uom_qty=12, date=tommorrow
        )
        (move1 | move2 | move3)._action_confirm()

        mo.invalidate_recordset(['components_availability', 'components_availability_state'])
        self.assertEqual(mo.components_availability, f'Exp {format_date(self.env, tommorrow)}')
        check_availability_state('late')

        mo.date_start = after_tommorrow

        self.assertEqual(mo.components_availability, f'Exp {format_date(self.env, tommorrow)}')
        self.assertEqual(mo.components_availability_state, 'expected')
        check_availability_state('expected')

        (move1 | move2).picked = True
        (move1 | move2)._action_done()

        # Still expected because move3 not yet done
        self.assertEqual(mo.components_availability, f'Exp {format_date(self.env, tommorrow)}')
        self.assertEqual(mo.components_availability_state, 'expected')
        check_availability_state('expected')

        move3.picked = True
        move3._action_done()

        mo.invalidate_recordset(['components_availability', 'components_availability_state'])
        self.assertEqual(mo.components_availability, 'Available')
        check_availability_state('available')

        mo.action_assign()

        self.assertEqual(mo.reservation_state, 'assigned')
        self.assertEqual(mo.components_availability, 'Available')
        check_availability_state('available')


    def test_immediate_validate_6(self):
        """In a production for a tracked product, clicking on mark as done without filling any quantities should
        pop up the immediate transfer wizard. Processing should choose a new lot for the finished product. """
        mo, bom, p_final, p1, p2 = self.generate_mo(qty_final=1, qty_base_1=1, qty_base_2=1, tracking_final='lot')
        self.env['stock.quant']._update_available_quantity(p1, self.stock_location_components, 5.0)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location_components, 5.0)
        mo.action_assign()
        mo.button_mark_done()
        self.assertEqual(mo.move_raw_ids.mapped('state'), ['done'] * 2)
        self.assertEqual(mo.move_raw_ids.mapped('quantity'), [1] * 2)
        self.assertEqual(mo.move_finished_ids.state, 'done')
        self.assertEqual(mo.move_finished_ids.quantity, 1)
        self.assertTrue(mo.move_finished_ids.move_line_ids.lot_id != False)

    def test_immediate_validate_uom(self):
        """In a production with a different uom than the finished product one, the
        immediate production wizard should fill the correct quantities. """
        p_final = self.env['product.product'].create({
            'name': 'final',
            'is_storable': True,
        })
        component = self.env['product.product'].create({
            'name': 'component',
            'is_storable': True,
        })
        bom = self.env['mrp.bom'].create({
            'product_id': p_final.id,
            'product_tmpl_id': p_final.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'type': 'normal',
            'consumption': 'flexible',
            'bom_line_ids': [(0, 0, {'product_id': component.id, 'product_qty': 1})]
        })
        self.env['stock.quant']._update_available_quantity(component, self.stock_location_components, 25.0)
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = bom
        mo_form.product_uom_id = self.uom_dozen
        mo_form.product_qty = 1
        mo = mo_form.save()
        mo.action_confirm()
        mo.action_assign()
        mo.button_mark_done()
        self.assertEqual(mo.move_raw_ids.state, 'done')
        self.assertEqual(mo.move_raw_ids.quantity, 12)
        self.assertEqual(mo.move_finished_ids.state, 'done')
        self.assertEqual(mo.move_finished_ids.quantity, 1)
        self.assertEqual(component.qty_available, 13)

    def test_immediate_validate_uom_2(self):
        """The rounding precision of a component should be based on the UoM used in the MO for this component,
        not on the produced product's UoM nor the default UoM of the component"""
        uom_units = self.env.ref('uom.product_uom_unit')
        uom_L = self.env.ref('uom.product_uom_litre')
        uom_cL = self.env['uom.uom'].create({
            'name': 'cL',
            'category_id': uom_L.category_id.id,
            'uom_type': 'smaller',
            'factor': 100,
            'rounding': 1,
        })
        uom_units.rounding = 1
        uom_L.rounding = 0.01

        product = self.env['product.product'].create({
            'name': 'SuperProduct',
            'uom_id': uom_units.id,
        })
        consumable_component = self.env['product.product'].create({
            'name': 'Consumable Component',
            'type': 'consu',
            'uom_id': uom_cL.id,
            'uom_po_id': uom_cL.id,
        })
        storable_component = self.env['product.product'].create({
            'name': 'Storable Component',
            'is_storable': True,
            'uom_id': uom_cL.id,
            'uom_po_id': uom_cL.id,
        })
        self.env['stock.quant']._update_available_quantity(storable_component, self.env.ref('stock.stock_location_stock'), 100)

        # Despite the purpose of this test is to use multi uom
        # tests the production choose the right uoms on all models without
        # having the uom fields in the interface views
        self.env.user.groups_id -= self.env.ref('uom.group_uom')
        for component in [consumable_component, storable_component]:
            bom = self.env['mrp.bom'].create({
                'product_tmpl_id': product.product_tmpl_id.id,
                'bom_line_ids': [(0, 0, {
                    'product_id': component.id,
                    'product_qty': 0.2,
                    'product_uom_id': uom_L.id,
                })],
            })

            mo_form = Form(self.env['mrp.production'])
            mo_form.bom_id = bom
            mo = mo_form.save()
            mo.action_confirm()
            mo.button_mark_done()

            self.assertEqual(mo.move_raw_ids.product_uom_qty, 0.2)
            self.assertEqual(mo.move_raw_ids.quantity, 0.2)

    def test_copy(self):
        """ Check that copying a done production, create all the stock moves"""
        mo, bom, p_final, p1, p2 = self.generate_mo(qty_final=1, qty_base_1=1, qty_base_2=1)
        mo.action_confirm()
        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo = mo_form.save()
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')
        mo_copy = mo.copy()
        self.assertTrue(mo_copy.move_raw_ids)
        self.assertTrue(mo_copy.move_finished_ids)
        mo_copy.action_confirm()
        mo_form = Form(mo_copy)
        mo_form.qty_producing = 1
        mo_copy = mo_form.save()
        mo_copy.button_mark_done()
        self.assertEqual(mo_copy.state, 'done')

    def test_product_produce_different_uom(self):
        """ Check that for products tracked by lots,
        with component product UOM different from UOM used in the BOM,
        we do not create a new move line due to extra reserved quantity
        caused by decimal rounding conversions.
        """

        picking_type = self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')])[0]

        # the overall decimal accuracy is set to 3 digits
        precision = self.env.ref('product.decimal_product_uom')
        precision.digits = 3

        # define L and ml, L has rounding .001 but ml has rounding .01
        # when producing e.g. 187.5ml, it will be rounded to .188L
        categ_test = self.env['uom.category'].create({'name': 'Volume Test'})

        uom_L = self.env['uom.uom'].create({
            'name': 'Test Liters',
            'category_id': categ_test.id,
            'uom_type': 'reference',
            'rounding': 0.001
        })

        uom_ml = self.env['uom.uom'].create({
            'name': 'Test ml',
            'category_id': categ_test.id,
            'uom_type': 'smaller',
            'rounding': 0.01,
            'factor_inv': 0.001,
        })

        # create a product component and the final product using the component
        product_comp = self.env['product.product'].create({
            'name': 'Product Component',
            'is_storable': True,
            'tracking': 'lot',
            'categ_id': self.env.ref('product.product_category_all').id,
            'uom_id': uom_L.id,
            'uom_po_id': uom_L.id,
        })

        product_final = self.env['product.product'].create({
            'name': 'Product Final',
            'is_storable': True,
            'tracking': 'lot',
            'categ_id': self.env.ref('product.product_category_all').id,
            'uom_id': uom_L.id,
            'uom_po_id': uom_L.id,
        })

        # the products are tracked by lot, so we go through _generate_consumed_move_line
        self.env['stock.lot'].create({
            'name': 'Lot Final',
            'product_id': product_final.id,
        })

        lot_comp = self.env['stock.lot'].create({
            'name': 'Lot Component',
            'product_id': product_comp.id,
        })

        # update the quantity on hand for Component, in a lot
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.env['stock.quant']._update_available_quantity(product_comp, self.stock_location, 1, lot_id=lot_comp)

        # create a BOM for Final, using Component
        test_bom = self.env['mrp.bom'].create({
            'product_id': product_final.id,
            'product_tmpl_id': product_final.product_tmpl_id.id,
            'product_uom_id': uom_L.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [(0, 0, {
                'product_id': product_comp.id,
                'product_qty': 375.00,
                'product_uom_id': uom_ml.id
            })],
        })

        # create a MO for this BOM
        mo_product_final_form = Form(self.env['mrp.production'])
        mo_product_final_form.product_id = product_final
        mo_product_final_form.product_uom_id = uom_L
        mo_product_final_form.bom_id = test_bom
        mo_product_final_form.product_qty = 0.5
        mo_product_final_form = mo_product_final_form.save()

        mo_product_final_form.action_confirm()
        mo_product_final_form.action_assign()
        self.assertEqual(mo_product_final_form.reservation_state, 'assigned')

        # produce
        mo_product_final_form.button_mark_done()

        # check that in _generate_consumed_move_line,
        # we do not create an extra move line because
        # of a conversion 187.5ml = 0.188L
        # thus creating an extra line with 'product_uom_qty': 0.5
        self.assertEqual(len(mo_product_final_form.move_raw_ids.move_line_ids), 1, 'One move line should exist for the MO.')

    def test_mo_sn_warning(self):
        """ Checks that when a MO where the final product is tracked by serial, a warning pops up if
        the `lot_producting_id` has previously been used already (i.e. dupe SN). Also checks if a
        scrap linked to a MO has its sn warning correctly pop up.
        """
        self.stock_location = self.env.ref('stock.stock_location_stock')
        mo, _, p_final, _, _ = self.generate_mo(tracking_final='serial', qty_base_1=1, qty_final=1)
        self.assertEqual(len(mo), 1, 'MO should have been created')

        sn1 = self.env['stock.lot'].create({
            'name': 'serial1',
            'product_id': p_final.id,
        })

        self.env['stock.quant']._update_available_quantity(p_final, self.stock_location, 1, lot_id=sn1)
        mo.lot_producing_id = sn1

        warning = False
        warning = mo._onchange_lot_producing()
        self.assertTrue(warning, 'Reuse of existing serial number not detected')
        self.assertEqual(list(warning.keys())[0], 'warning', 'Warning message was not returned')

        mo.action_generate_serial()
        sn2 = mo.lot_producing_id
        mo.button_mark_done()

        # scrap linked to MO but with wrong SN location
        scrap = self.env['stock.scrap'].create({
            'product_id': p_final.id,
            'product_uom_id': self.uom_unit.id,
            'production_id': mo.id,
            'location_id': self.stock_location_14.id,
            'lot_id': sn2.id
        })

        warning = False
        warning = scrap._onchange_serial_number()
        self.assertTrue(warning, 'Use of wrong serial number location not detected')
        self.assertEqual(list(warning.keys())[0], 'warning', 'Warning message was not returned')
        self.assertEqual(scrap.location_id, mo.location_dest_id, 'Location was not auto-corrected')

    def test_a_multi_button_plan(self):
        """ Test batch methods (confirm/validate) of the MO with the same bom """
        self.bom_2.type = "normal"  # avoid to get the operation of the kit bom

        mo_3 = Form(self.env['mrp.production'])
        mo_3.bom_id = self.bom_3
        mo_3 = mo_3.save()

        self.assertEqual(len(mo_3.workorder_ids), 2)

        mo_3.button_plan()
        self.assertEqual(mo_3.state, 'confirmed')
        self.assertEqual(mo_3.workorder_ids[0].state, 'waiting')

        mo_1 = Form(self.env['mrp.production'])
        mo_1.bom_id = self.bom_3
        mo_1 = mo_1.save()

        mo_2 = Form(self.env['mrp.production'])
        mo_2.bom_id = self.bom_3
        mo_2 = mo_2.save()

        self.assertEqual(mo_1.product_id, self.product_6)
        self.assertEqual(mo_2.product_id, self.product_6)
        self.assertEqual(len(self.bom_3.operation_ids), 2)
        self.assertEqual(len(mo_1.workorder_ids), 2)
        self.assertEqual(len(mo_2.workorder_ids), 2)

        (mo_1 | mo_2).button_plan()  # Confirm and plan in the same "request"
        self.assertEqual(mo_1.state, 'confirmed')
        self.assertEqual(mo_2.state, 'confirmed')
        self.assertEqual(mo_1.workorder_ids[0].state, 'waiting')
        self.assertEqual(mo_2.workorder_ids[0].state, 'waiting')

        # produce
        (mo_1 | mo_2).button_mark_done()
        self.assertEqual(mo_1.state, 'done')
        self.assertEqual(mo_2.state, 'done')

    def test_workcenter_timezone(self):
        # Workcenter is based in Bangkok
        # Possible working hours are Monday to Friday, from 8:00 to 12:00 and from 13:00 to 17:00 (UTC+7)
        workcenter = self.workcenter_1
        workcenter.resource_calendar_id.tz = 'Asia/Bangkok'
        # The test will try to plan some WO on next Monday. We need to unlink all
        # useless times off to ensure that nothing will disturb the slot reservation
        (workcenter.resource_calendar_id.global_leave_ids | workcenter.resource_calendar_id.leave_ids).unlink()

        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product_1.product_tmpl_id.id,
            'bom_line_ids': [(0, 0, {
                'product_id': self.product_2.id,
            })],
            'operation_ids': [(0, 0, {
                'name': 'SuperOperation01',
                'workcenter_id': workcenter.id,
            }), (0, 0, {
                'name': 'SuperOperation01',
                'workcenter_id': workcenter.id,
            })],
        })

        # Next Monday at 6:00 am UTC
        date_start = (fields.Datetime.now() + timedelta(days=7 - fields.Datetime.now().weekday())).replace(hour=6, minute=0, second=0)
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = bom
        mo_form.date_start = date_start
        mo = mo_form.save()

        mo.workorder_ids[0].duration_expected = 240
        mo.workorder_ids[1].duration_expected = 60

        mo.action_confirm()
        mo.button_plan()

        # Asia/Bangkok is UTC+7 and the start date is on Monday at 06:00 UTC (i.e., 13:00 UTC+7).
        # So, in Bangkok, the first workorder uses the entire Monday afternoon slot 13:00 - 17:00 UTC+7 (i.e., 06:00 - 10:00 UTC)
        # The second job uses the beginning of the Tuesday morning slot: 08:00 - 09:00 UTC+7 (i.e., 01:00 - 02:00 UTC)
        self.assertEqual(mo.workorder_ids[0].date_start, date_start)
        self.assertEqual(mo.workorder_ids[0].date_finished, date_start + timedelta(hours=4))
        tuesday = date_start + timedelta(days=1)
        self.assertEqual(mo.workorder_ids[1].date_start, tuesday.replace(hour=1))
        self.assertEqual(mo.workorder_ids[1].date_finished, tuesday.replace(hour=2))

    def test_backorder_with_overconsumption(self):
        """ Check that the components of the backorder have the correct quantities
        when there is overconsumption in the initial MO
        """
        mo, _, _, _, _ = self.generate_mo(qty_final=30, qty_base_1=2, qty_base_2=3)
        mo.action_confirm()
        mo_form = Form(mo)
        mo_form.qty_producing = 10
        mo = mo_form.save()
        mo.move_raw_ids[0].quantity = 90
        mo.move_raw_ids[1].quantity = 70
        action = mo.button_mark_done()
        backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder.save().action_backorder()
        mo_backorder = mo.procurement_group_id.mrp_production_ids[-1]

        # Check quantities of the original MO
        self.assertEqual(mo.product_uom_qty, 10.0)
        self.assertEqual(mo.qty_produced, 10.0)
        move_prod_1 = self.env['stock.move'].search([
            ('product_id', '=', mo.bom_id.bom_line_ids[0].product_id.id),
            ('raw_material_production_id', '=', mo.id)])
        move_prod_2 = self.env['stock.move'].search([
            ('product_id', '=', mo.bom_id.bom_line_ids[1].product_id.id),
            ('raw_material_production_id', '=', mo.id)])
        self.assertEqual(sum(move_prod_1.mapped('quantity')), 90.0)
        self.assertEqual(sum(move_prod_1.mapped('product_uom_qty')), 30.0)
        self.assertEqual(sum(move_prod_2.mapped('quantity')), 70.0)
        self.assertEqual(sum(move_prod_2.mapped('product_uom_qty')), 20.0)

        # Check quantities of the backorder MO
        self.assertEqual(mo_backorder.product_uom_qty, 20.0)
        move_prod_1_bo = self.env['stock.move'].search([
            ('product_id', '=', mo.bom_id.bom_line_ids[0].product_id.id),
            ('raw_material_production_id', '=', mo_backorder.id)])
        move_prod_2_bo = self.env['stock.move'].search([
            ('product_id', '=', mo.bom_id.bom_line_ids[1].product_id.id),
            ('raw_material_production_id', '=', mo_backorder.id)])
        self.assertEqual(sum(move_prod_1_bo.mapped('product_uom_qty')), 60.0)
        self.assertEqual(sum(move_prod_2_bo.mapped('product_uom_qty')), 40.0)

    def test_backorder_with_underconsumption(self):
        """ Check that the components of the backorder have the correct quantities
        when there is underconsumption in the initial MO
        """
        mo, _, _, p1, p2 = self.generate_mo(qty_final=20, qty_base_1=1, qty_base_2=1)
        mo.action_confirm()
        mo_form = Form(mo)
        mo_form.qty_producing = 10
        mo = mo_form.save()
        mo.move_raw_ids.filtered(lambda m: m.product_id == p1).quantity = 5
        mo.move_raw_ids.filtered(lambda m: m.product_id == p2).quantity = 10
        action = mo.button_mark_done()
        backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder.save().action_backorder()
        mo_backorder = mo.procurement_group_id.mrp_production_ids[-1]

        # Check quantities of the original MO
        self.assertEqual(mo.product_uom_qty, 10.0)
        self.assertEqual(mo.qty_produced, 10.0)
        move_prod_1_done = mo.move_raw_ids.filtered(lambda m: m.product_id == p1)
        self.assertEqual(sum(move_prod_1_done.mapped('quantity')), 5)
        self.assertEqual(sum(move_prod_1_done.mapped('product_uom_qty')), 10)
        move_prod_2 = mo.move_raw_ids.filtered(lambda m: m.product_id == p2)
        self.assertEqual(sum(move_prod_2.mapped('quantity')), 10)
        self.assertEqual(sum(move_prod_2.mapped('product_uom_qty')), 10)

        # Check quantities of the backorder MO
        self.assertEqual(mo_backorder.product_uom_qty, 10.0)
        move_prod_1_bo = mo_backorder.move_raw_ids.filtered(lambda m: m.product_id == p1)
        move_prod_2_bo = mo_backorder.move_raw_ids.filtered(lambda m: m.product_id == p2)
        self.assertEqual(sum(move_prod_1_bo.mapped('product_uom_qty')), 10.0)
        self.assertEqual(sum(move_prod_2_bo.mapped('product_uom_qty')), 10.0)

    def test_state_workorders(self):
        bom = self.env['mrp.bom'].create({
            'product_id': self.product_4.id,
            'product_tmpl_id': self.product_4.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'consumption': 'flexible',
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': self.product_2.id, 'product_qty': 1})
            ],
            'operation_ids': [
                (0, 0, {'name': 'amUgbidhaW1lIHBhcyBsZSBKUw==', 'workcenter_id': self.workcenter_1.id, 'time_cycle': 15, 'sequence': 1}),
                (0, 0, {'name': '137 Python', 'workcenter_id': self.workcenter_1.id, 'time_cycle': 1, 'sequence': 2}),
            ],
        })

        self.env['stock.quant'].create({
            'location_id': self.stock_location_components.id,
            'product_id': self.product_2.id,
            'inventory_quantity': 10
        }).action_apply_inventory()

        mo = Form(self.env['mrp.production'])
        mo.bom_id = bom
        mo = mo.save()

        self.assertEqual(list(mo.workorder_ids.mapped("state")), ["waiting", "waiting"])

        mo.action_confirm()
        mo.action_assign()
        self.assertEqual(mo.move_raw_ids.state, "assigned")
        self.assertEqual(list(mo.workorder_ids.mapped("state")), ["ready", "pending"])
        mo.do_unreserve()

        self.assertEqual(list(mo.workorder_ids.mapped("state")), ["waiting", "pending"])

        mo.workorder_ids[0].unlink()

        self.assertEqual(list(mo.workorder_ids.mapped("state")), ["waiting"])
        mo.action_assign()
        self.assertEqual(list(mo.workorder_ids.mapped("state")), ["ready"])

        mo.button_mark_done()
        self.assertEqual(list(mo.workorder_ids.mapped("state")), ["done"])

    def test_products_with_variants(self):
        """Check for product with different variants with same bom"""
        attribute = self.env['product.attribute'].create({
            'name': 'Test Attribute',
        })
        attribute_values = self.env['product.attribute.value'].create([{
            'name': 'Value 1',
            'attribute_id': attribute.id,
            'sequence': 1,
        }, {
            'name': 'Value 2',
            'attribute_id': attribute.id,
            'sequence': 2,
        }])
        product = self.env['product.template'].create({
            "attribute_line_ids": [
                [0, 0, {"attribute_id": attribute.id, "value_ids": [[6, 0, attribute_values.ids]]}]
            ],
            "name": "Product with variants",
        })

        variant_1 = product.product_variant_ids[0]
        variant_2 = product.product_variant_ids[1]

        component = self.env['product.template'].create({
            "name": "Component",
        })

        self.env['mrp.bom'].create({
            'product_id': False,
            'product_tmpl_id': product.id,
            'bom_line_ids': [
                (0, 0, {'product_id': component.product_variant_id.id, 'product_qty': 1})
            ]
        })

        # First behavior to check, is changing the product (same product but another variant) after saving the MO a first time.
        mo_form_1 = Form(self.env['mrp.production'])
        mo_form_1.product_id = variant_1
        mo_1 = mo_form_1.save()
        mo_form_1 = Form(self.env['mrp.production'].browse(mo_1.id))
        mo_form_1.product_id = variant_2
        mo_1 = mo_form_1.save()
        mo_1.action_confirm()
        mo_1.action_assign()
        mo_form_1 = Form(self.env['mrp.production'].browse(mo_1.id))
        mo_form_1.qty_producing = 1
        mo_1 = mo_form_1.save()
        mo_1.button_mark_done()

        move_lines_1 = self.env['stock.move.line'].search([("reference", "=", mo_1.name)])
        move_finished_ids_1 = self.env['stock.move'].search([("production_id", "=", mo_1.id)])
        self.assertEqual(len(move_lines_1), 2, "There should only be 2 move lines: the component line and produced product line")
        self.assertEqual(len(move_finished_ids_1), 1, "There should only be 1 produced product for this MO")
        self.assertEqual(move_finished_ids_1.product_id, variant_2, "Incorrect variant produced")

        # Second behavior is changing the product before saving the MO
        mo_form_2 = Form(self.env['mrp.production'])
        mo_form_2.product_id = variant_1
        mo_form_2.product_id = variant_2
        mo_2 = mo_form_2.save()
        mo_2.action_confirm()
        mo_2.action_assign()
        mo_form_2 = Form(self.env['mrp.production'].browse(mo_2.id))
        mo_form_2.qty_producing = 1
        mo_2 = mo_form_2.save()
        mo_2.button_mark_done()

        move_lines_2 = self.env['stock.move.line'].search([("reference", "=", mo_2.name)])
        move_finished_ids_2 = self.env['stock.move'].search([("production_id", "=", mo_2.id)])
        self.assertEqual(len(move_lines_2), 2, "There should only be 2 move lines: the component line and produced product line")
        self.assertEqual(len(move_finished_ids_2), 1, "There should only be 1 produced product for this MO")
        self.assertEqual(move_finished_ids_2.product_id, variant_2, "Incorrect variant produced")

        # Third behavior is changing the product before saving the MO, then another time after
        mo_form_3 = Form(self.env['mrp.production'])
        mo_form_3.product_id = variant_1
        mo_form_3.product_id = variant_2
        mo_3 = mo_form_3.save()
        mo_form_3 = Form(self.env['mrp.production'].browse(mo_3.id))
        mo_form_3.product_id = variant_1
        mo_3 = mo_form_3.save()
        mo_3.action_confirm()
        mo_3.action_assign()
        mo_form_3 = Form(self.env['mrp.production'].browse(mo_3.id))
        mo_form_3.qty_producing = 1
        mo_3 = mo_form_3.save()
        mo_3.button_mark_done()

        move_lines_3 = self.env['stock.move.line'].search([("reference", "=", mo_3.name)])
        move_finished_ids_3 = self.env['stock.move'].search([("production_id", "=", mo_3.id)])
        self.assertEqual(len(move_lines_3), 2, "There should only be 2 move lines: the component line and produced product line")
        self.assertEqual(len(move_finished_ids_3), 1, "There should only be 1 produced product for this MO")
        self.assertEqual(move_finished_ids_3.product_id, variant_1, "Incorrect variant produced")

    def test_move_finished_onchanges(self):
        """ Test that move_finished_ids (i.e. produced products) are still correct even after
        multiple onchanges have changed the moves
        """

        product1 = self.env['product.product'].create({
            'name': 'Oatmeal Cookie',
        })
        product2 = self.env['product.product'].create({
            'name': 'Chocolate Chip Cookie',
        })

        # ===== product_id onchange checks ===== #
        # check product_id onchange without saving
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product1
        mo_form.product_id = product2
        mo = mo_form.save()
        self.assertEqual(len(mo.move_finished_ids), 1, 'Wrong number of finished product moves created')
        self.assertEqual(mo.move_finished_ids.product_id, product2, 'Wrong product to produce in finished product move')
        # check product_id onchange after saving
        mo_form = Form(self.env['mrp.production'].browse(mo.id))
        mo_form.product_id = product1
        mo = mo_form.save()
        self.assertEqual(len(mo.move_finished_ids), 1, 'Wrong number of finish product moves created')
        self.assertEqual(mo.move_finished_ids.product_id, product1, 'Wrong product to produce in finished product move')
        # check product_id onchange when mo._origin.product_id is unchanged
        mo_form = Form(self.env['mrp.production'].browse(mo.id))
        mo_form.product_id = product2
        mo_form.product_id = product1
        mo = mo_form.save()
        self.assertEqual(len(mo.move_finished_ids), 1, 'Wrong number of finish product moves created')
        self.assertEqual(mo.move_finished_ids.product_id, product1, 'Wrong product to produce in finished product move')

        # ===== product_qty onchange checks ===== #
        # check product_qty onchange without saving
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product1
        mo_form.product_qty = 5
        mo_form.product_qty = 10
        mo2 = mo_form.save()
        self.assertEqual(len(mo2.move_finished_ids), 1, 'Wrong number of finished product moves created')
        self.assertEqual(mo2.move_finished_ids.product_qty, 10, 'Wrong qty to produce for the finished product move')

        # check product_qty onchange after saving
        mo_form = Form(self.env['mrp.production'].browse(mo2.id))
        mo_form.product_qty = 5
        mo2 = mo_form.save()
        self.assertEqual(len(mo2.move_finished_ids), 1, 'Wrong number of finish product moves created')
        self.assertEqual(mo2.move_finished_ids.product_qty, 5, 'Wrong qty to produce for the finished product move')

        # check product_qty onchange when mo._origin.product_id is unchanged
        mo_form = Form(self.env['mrp.production'].browse(mo2.id))
        mo_form.product_qty = 10
        mo_form.product_qty = 5
        mo2 = mo_form.save()
        self.assertEqual(len(mo2.move_finished_ids), 1, 'Wrong number of finish product moves created')
        self.assertEqual(mo2.move_finished_ids.product_qty, 5, 'Wrong qty to produce for the finished product move')

        # ===== product_uom_id onchange checks ===== #
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product1
        mo_form.product_qty = 1
        mo_form.product_uom_id = self.env['uom.uom'].browse(self.ref('uom.product_uom_dozen'))
        mo3 = mo_form.save()
        self.assertEqual(len(mo3.move_finished_ids), 1, 'Wrong number of finish product moves created')
        self.assertEqual(mo3.move_finished_ids.product_qty, 12, 'Wrong qty to produce for the finished product move')

        # ===== bom_id onchange checks ===== #
        component = self.env['product.product'].create({
            "name": "Sugar",
        })

        bom1 = self.env['mrp.bom'].create({
            'product_id': False,
            'product_tmpl_id': product1.product_tmpl_id.id,
            'bom_line_ids': [
                (0, 0, {'product_id': component.id, 'product_qty': 1})
            ]
        })

        bom2 = self.env['mrp.bom'].create({
            'product_id': False,
            'product_tmpl_id': product1.product_tmpl_id.id,
            'bom_line_ids': [
                (0, 0, {'product_id': component.id, 'product_qty': 10})
            ]
        })
        # check bom_id onchange before product change
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = bom1
        mo_form.bom_id = bom2
        mo_form.product_id = product2
        mo4 = mo_form.save()
        self.assertFalse(mo4.bom_id, 'BoM should have been removed')
        self.assertEqual(len(mo4.move_finished_ids), 1, 'Wrong number of finished product moves created')
        self.assertEqual(mo4.move_finished_ids.product_id, product2, 'Wrong product to produce in finished product move')
        # check bom_id onchange after product change
        mo_form = Form(self.env['mrp.production'].browse(mo4.id))
        mo_form.product_id = product1
        mo_form.bom_id = bom1
        mo_form.bom_id = bom2
        mo4 = mo_form.save()
        self.assertEqual(len(mo4.move_finished_ids), 1, 'Wrong number of finish product moves created')
        self.assertEqual(mo4.move_finished_ids.product_id, product1, 'Wrong product to produce in finished product move')
        # check product_id onchange when mo._origin.product_id is unchanged
        mo_form = Form(self.env['mrp.production'].browse(mo4.id))
        mo_form.bom_id = bom2
        mo_form.bom_id = bom1
        mo4 = mo_form.save()
        self.assertEqual(len(mo4.move_finished_ids), 1, 'Wrong number of finish product moves created')
        self.assertEqual(mo4.move_finished_ids.product_id, product1, 'Wrong product to produce in finished product move')

    def test_compute_tracked_time_1(self):
        """
        Checks that the Duration Computation (`time_mode` of mrp.routing.workcenter) with value `auto` with Based On
        (`time_mode_batch`) set to 1 actually compute the time based on the last 1 operation, and not more.
        Create a first production in 15 minutes (expected should go from 60 to 15
        Create a second one in 10 minutes (expected should NOT go from 15 to 12.5, it should go from 15 to 10)
        """
        # First production, the default is 60 and there is 0 productions of that operation
        # Required for `workorder_ids` to be visible in the view
        self.env.user.groups_id += self.env.ref('mrp.group_mrp_routings')
        production_form = Form(self.env['mrp.production'])
        production_form.bom_id = self.bom_4
        production = production_form.save()
        self.assertEqual(production.workorder_ids[0].duration_expected, 60.0, "Default duration is 0+0+1*60.0")
        production.action_confirm()
        production.button_plan()
        # Production planned, time to start, I produce all the 1 product
        # 'invisible': [('state', '=', 'draft')]
        production_form = Form(production)
        production_form.qty_producing = 1
        with production_form.workorder_ids.edit(0) as wo:
            wo.duration = 15 # in 15 minutes
        production = production_form.save()
        production.button_mark_done()
        # It is saved and done, registered in the db. There are now 1 productions of that operation

        # Same production, let's see what the duration_expected is, last prod was 15 minutes for 1 item
        production_form = Form(self.env['mrp.production'])
        production_form.bom_id = self.bom_4
        production = production_form.save()
        self.assertEqual(production.workorder_ids[0].duration_expected, 15.0, "Duration is now 0+0+1*15")
        production.action_confirm()
        production.button_plan()
        # Production planned, time to start, I produce all the 1 product
        # 'invisible': [('state', '=', 'draft')]
        production_form = Form(production)
        production_form.qty_producing = 1
        with production_form.workorder_ids.edit(0) as wo:
            wo.duration = 10  # In 10 minutes this time
        production = production_form.save()
        production.button_mark_done()
        # It is saved and done, registered in the db. There are now 2 productions of that operation

        # Same production, let's see what the duration_expected is, last prod was 10 minutes for 1 item
        # Total average time would be 12.5 but we compute the duration based on the last 1 item
        production_form = Form(self.env['mrp.production'])
        production_form.bom_id = self.bom_4
        production = production_form.save()
        self.assertNotEqual(production.workorder_ids[0].duration_expected, 12.5, "Duration expected is based on the last 1 production, not last 2")
        self.assertEqual(production.workorder_ids[0].duration_expected, 10.0, "Duration is now 0+0+1*10")

    def test_compute_tracked_time_2_under_capacity(self):
        """
        Test that when tracking the 2 last production, if we make one with under capacity, and one with normal capacity,
        the two are equivalent (1 done with capacity 2 in 10mn = 2 done with capacity 2 in 10mn)
        """
        # Required for `workorder_ids` to be visible in the view
        self.env.user.groups_id += self.env.ref('mrp.group_mrp_routings')
        production_form = Form(self.env['mrp.production'])
        production_form.bom_id = self.bom_5
        production = production_form.save()
        production.action_confirm()
        production.button_plan()

        # Production planned, time to start, I produce all the 1 product
        # 'invisible': [('state', '=', 'draft')]
        production_form = Form(production)
        production_form.qty_producing = 1
        with production_form.workorder_ids.edit(0) as wo:
            wo.duration = 10  # in 10 minutes
        production = production_form.save()
        production.button_mark_done()
        # It is saved and done, registered in the db. There are now 1 productions of that operation

        # Same production, let's see what the duration_expected is, last prod was 10 minutes for 1 item
        production_form = Form(self.env['mrp.production'])
        production_form.bom_id = self.bom_5
        production_form.product_qty = 2  # We want to produce 2 items (the capacity) now
        production = production_form.save()
        self.assertNotEqual(production.workorder_ids[0].duration_expected, 20.0, "We made 1 item with capacity 2 in 10mn -> so 2 items shouldn't be double that")
        self.assertEqual(production.workorder_ids[0].duration_expected, 10.0, "Producing 1 or 2 items with capacity 2 is the same duration")
        production.action_confirm()
        production.button_plan()
        # Production planned, time to start, I produce all the 2 product
        # 'invisible': [('state', '=', 'draft')]
        production_form = Form(production)
        production_form.qty_producing = 2
        with production_form.workorder_ids.edit(0) as wo:
            wo.duration = 10  # In 10 minutes this time
        production = production_form.save()
        production.button_mark_done()
        # It is saved and done, registered in the db. There are now 2 productions of that operation but they have the same duration

        production_form = Form(self.env['mrp.production'])
        production_form.bom_id = self.bom_5
        production = production_form.save()
        self.assertNotEqual(production.workorder_ids[0].duration_expected, 15, "Producing 1 or 2 in 10mn with capacity 2 take the same amount of time : 10mn")
        self.assertEqual(production.workorder_ids[0].duration_expected, 10.0, "Duration is indeed (10+10)/2")

    def test_capacity_duration_expected(self):
        """
        Test that the duration expected is correctly computed when dealing with below or above capacity
        1 -> 10mn
        2 -> 10mn
        3 -> 20mn
        4 -> 20mn
        5 -> 30mn
        ...
        """
        # Required for `workorder_ids` to be visible in the view
        self.env.user.groups_id += self.env.ref('mrp.group_mrp_routings')
        production_form = Form(self.env['mrp.production'])
        production_form.bom_id = self.bom_6
        production = production_form.save()
        production.action_confirm()
        production.button_plan()

        # Production planned, time to start, I produce all the 1 product
        # 'invisible': [('state', '=', 'draft')]
        production_form = Form(production)
        production_form.qty_producing = 1
        with production_form.workorder_ids.edit(0) as wo:
            wo.duration = 10  # in 10 minutes
        production = production_form.save()
        production.button_mark_done()

        production_form = Form(self.env['mrp.production'])
        production_form.bom_id = self.bom_6
        production = production_form.save()
        # production_form.product_qty = 1 [BY DEFAULT]
        self.assertEqual(production.workorder_ids[0].duration_expected, 10.0, "Produce 1 with capacity 2, expected is 10mn for each run -> 10mn")
        production_form.product_qty = 2
        production = production_form.save()
        self.assertEqual(production.workorder_ids[0].duration_expected, 10.0, "Produce 2 with capacity 2, expected is 10mn for each run -> 10mn")

        production_form.product_qty = 3
        production = production_form.save()
        self.assertEqual(production.workorder_ids[0].duration_expected, 20.0, "Produce 3 with capacity 2, expected is 10mn for each run -> 20mn")

        production_form.product_qty = 4
        production = production_form.save()
        self.assertEqual(production.workorder_ids[0].duration_expected, 20.0, "Produce 4 with capacity 2, expected is 10mn for each run -> 20mn")

        production_form.product_qty = 5
        production = production_form.save()
        self.assertEqual(production.workorder_ids[0].duration_expected, 30.0, "Produce 5 with capacity 2, expected is 10mn for each run -> 30mn")

    def test_workorder_set_duration(self):
        """ Test that manually setting duration correctly creates/updates time_ids """
        mo = Form(self.env['mrp.production'])
        mo.bom_id = self.bom_4
        mo = mo.save()
        mo.action_confirm()

        workorder = mo.workorder_ids[0]
        expected_duration = workorder.duration_expected
        real_duration_under_expected = expected_duration / 2  # first value
        real_duration_increased_above_expected = 2 * expected_duration  # to create next 2 values
        real_duration_decreased = expected_duration * .75  # reduced amount that overlaps the last 2 values

        # update real duration to amount under expected duration
        workorder.duration = real_duration_under_expected
        self.assertEqual(len(workorder.time_ids), 1, "A time tracking value should have been created")
        self.assertEqual(workorder.time_ids[0].loss_type, 'productive', "Total duration < Expected duration => should be productive time")
        self.assertEqual(workorder.time_ids[0].duration, real_duration_under_expected, "Incorrect duration for time tracking value")

        # update real duration to amount above expected duration
        workorder.duration = real_duration_increased_above_expected
        self.assertEqual(len(workorder.time_ids), 3, "Two more time tracking values should have been created")
        self.assertEqual(workorder.time_ids[1].loss_type, 'productive', "Duration amount added under the expected duration should be productive time")
        self.assertEqual(workorder.time_ids[2].loss_type, 'performance', "Duration amount added above expected duration should be performance (i.e. reduced) time")
        self.assertEqual(workorder.time_ids[1].duration, expected_duration - real_duration_under_expected, "Added (productive) time should be expected duration - already existing duration")
        self.assertEqual(workorder.time_ids[2].duration, real_duration_increased_above_expected - expected_duration, "Added (reduced) time should be total duration - expected duration")

        # update real duration to amount below expected duration
        workorder.duration = real_duration_decreased
        # reducing time reverses the time_id order... so we reverse the check
        self.assertEqual(len(workorder.time_ids), 2, "One time tracking values should have been deleted")
        self.assertEqual(workorder.time_ids[1].loss_type, 'productive', "Original time tracking should be unchanged")
        self.assertEqual(workorder.time_ids[1].duration, real_duration_under_expected, "Original time tracking should be unchanged")
        self.assertEqual(workorder.time_ids[0].loss_type, 'productive', "Remaining time tracking should be productive")
        self.assertEqual(workorder.time_ids[0].duration, real_duration_decreased - real_duration_under_expected, "Time tracking duration should have been reduced to reflect new shorter duration")

    def test_propagate_quantity_on_backorders(self):
        """Create a MO for a product with several work orders.
        Produce different quantities to test quantity propagation and workorder cancellation.
        """

        # setup test

        work_center_1 = self.env['mrp.workcenter'].create({"name": "WorkCenter 1", "time_start": 11})
        work_center_2 = self.env['mrp.workcenter'].create({"name": "WorkCenter 2", "time_start": 12})
        work_center_3 = self.env['mrp.workcenter'].create({"name": "WorkCenter 3", "time_start": 13})

        product = self.env['product.template'].create({"name": "Finished Product"})
        component_1 = self.env['product.template'].create({"name": "Component 1", "is_storable": True})
        component_2 = self.env['product.template'].create({"name": "Component 2", "is_storable": True})
        component_3 = self.env['product.template'].create({"name": "Component 3", "is_storable": True})

        self.env['stock.quant'].create({
            "product_id": component_1.product_variant_id.id,
            "location_id": 8,
            "quantity": 100
        })
        self.env['stock.quant'].create({
            "product_id": component_2.product_variant_id.id,
            "location_id": 8,
            "quantity": 100
        })
        self.env['stock.quant'].create({
            "product_id": component_3.product_variant_id.id,
            "location_id": 8,
            "quantity": 100
        })

        self.env['mrp.bom'].create({
            "product_tmpl_id": product.id,
            "product_id": False,
            "product_qty": 1,
            "bom_line_ids": [
                [0, 0, {"product_id": component_1.product_variant_id.id, "product_qty": 1}],
                [0, 0, {"product_id": component_2.product_variant_id.id, "product_qty": 1}],
                [0, 0, {"product_id": component_3.product_variant_id.id, "product_qty": 1}]
            ],
            "operation_ids": [
                [0, 0, {"name": "Operation 1", "workcenter_id": work_center_1.id}],
                [0, 0, {"name": "Operation 2", "workcenter_id": work_center_2.id}],
                [0, 0, {"name": "Operation 3", "workcenter_id": work_center_3.id}]
            ]
        })

        # create a manufacturing order for 20 products

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product.product_variant_id
        mo_form.product_qty = 20
        mo = mo_form.save()

        self.assertEqual(mo.state, 'draft')
        mo.action_confirm()

        wo_1, wo_2, wo_3 = mo.workorder_ids
        self.assertEqual(mo.state, 'confirmed')
        self.assertEqual(wo_1.state, 'ready')
        self.assertEqual(wo_1.duration_expected, 11 + 20 * 60)

        # produce 20 / 10 / 5 on workorders, create backorder

        duration_expected = wo_1.duration_expected
        wo_1.button_start()
        wo_1.qty_producing = 20
        self.assertEqual(mo.state, 'progress')
        wo_1.button_finish()
        self.assertEqual(duration_expected, wo_1.duration_expected)

        wo_2.button_start()
        wo_2.qty_producing = 10
        wo_2.button_finish()
        self.assertEqual(wo_2.duration_expected, 12 + 10 * 60)

        wo_3.button_start()
        wo_3.qty_producing = 5
        wo_3.button_finish()
        self.assertEqual(wo_3.duration_expected, 13 + 5 * 60)

        self.assertEqual(mo.state, 'to_close')
        mo.button_mark_done()

        bo = self.env['mrp.production.backorder'].create({
            "mrp_production_backorder_line_ids": [
                [0, 0, {"mrp_production_id": mo.id, "to_backorder": True}]
            ]
        })
        bo.action_backorder()

        self.assertEqual(mo.state, 'done')

        mo_2 = mo.procurement_group_id.mrp_production_ids - mo
        wo_4, wo_5, wo_6 = mo_2.workorder_ids

        self.assertEqual(wo_4.state, 'cancel')
        self.assertEqual(wo_5.duration_expected, 12 + 15 * 60)

        # produce 10 / 5, create backorder

        wo_5.button_start()
        wo_5.qty_producing = 10
        self.assertEqual(mo_2.state, 'progress')
        wo_5.button_finish()

        wo_6.button_start()
        wo_6.qty_producing = 5
        wo_6.button_finish()

        self.assertEqual(mo_2.state, 'to_close')
        mo_2.button_mark_done()

        bo = self.env['mrp.production.backorder'].create({
            "mrp_production_backorder_line_ids": [
                [0, 0, {"mrp_production_id": mo_2.id, "to_backorder": True}]
            ]
        })
        bo.action_backorder()

        self.assertEqual(mo_2.state, 'done')

        mo_3 = mo.procurement_group_id.mrp_production_ids - (mo | mo_2)
        wo_7, wo_8, wo_9 = mo_3.workorder_ids

        self.assertEqual(wo_7.state, 'cancel')
        self.assertEqual(wo_8.state, 'cancel')
        self.assertEqual(wo_9.duration_expected, 13 + 10 * 60)

        # produce 10 and finish work

        wo_9.button_start()
        wo_9.qty_producing = 10
        self.assertEqual(mo_3.state, 'progress')
        wo_9.button_finish()

        self.assertEqual(mo_3.state, 'to_close')
        mo_3.button_mark_done()
        self.assertEqual(mo_3.state, 'done')

    def test_planning_workorder(self):
        """
            Check that the fastest work center is used when planning the workorder.
            - create two work centers with similar production capacity
                but the work_center_2 with a longer start and stop time.
            1:/ produce 2 units > work_center_1 faster because
                it does not need much time to start and to finish the production.
            2/ - update the production capacity of the work_center_2 to 4
                - produce 4 units > work_center_2 faster because
                it must do a single cycle while the work_center_1 have to do two cycles.
        """
        workcenter_1 = self.env['mrp.workcenter'].create({
            'name': 'wc1',
            'default_capacity': 2,
            'time_start': 1,
            'time_stop': 1,
            'time_efficiency': 100,
        })

        workcenter_2 = self.env['mrp.workcenter'].create({
            'name': 'wc2',
            'default_capacity': 2,
            'time_start': 10,
            'time_stop': 5,
            'time_efficiency': 100,
            'alternative_workcenter_ids': [workcenter_1.id]
        })

        product_to_build = self.env['product.product'].create({
            'name': 'final product',
            'is_storable': True,
        })

        product_to_use = self.env['product.product'].create({
            'name': 'component',
            'is_storable': True,
        })

        bom = self.env['mrp.bom'].create({
            'product_id': product_to_build.id,
            'product_tmpl_id': product_to_build.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'type': 'normal',
            'consumption': 'flexible',
            'operation_ids': [
                (0, 0, {'name': 'Test', 'workcenter_id': workcenter_2.id, 'time_cycle': 60, 'sequence': 1}),
            ],
            'bom_line_ids': [
                (0, 0, {'product_id': product_to_use.id, 'product_qty': 1}),
            ]})

        #MO_1
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product_to_build
        mo_form.bom_id = bom
        mo_form.product_qty = 2
        mo = mo_form.save()
        mo.action_confirm()
        mo.button_plan()
        self.assertEqual(mo.workorder_ids[0].workcenter_id.id, workcenter_1.id, 'workcenter_1 is faster than workcenter_2 to manufacture 2 units')
        # Unplan the mo to prevent the first workcenter from being busy
        mo.button_unplan()

        # Update the production capcity
        workcenter_2.default_capacity = 4

        #MO_2
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product_to_build
        mo_form.bom_id = bom
        mo_form.product_qty = 4
        mo_2 = mo_form.save()
        mo_2.action_confirm()
        mo_2.button_plan()
        self.assertEqual(mo_2.workorder_ids[0].workcenter_id.id, workcenter_2.id, 'workcenter_2 is faster than workcenter_1 to manufacture 4 units')

    def test_timers_after_cancelling_mo(self):
        """
            Check that the timers in the workorders are stopped after the cancellation of the MO
        """
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom_2
        mo_form.product_qty = 1
        mo = mo_form.save()
        mo.action_confirm()
        mo.button_plan()

        wo = mo.workorder_ids
        wo.button_start()
        mo.action_cancel()
        self.assertEqual(mo.state, 'cancel', 'Manufacturing order should be cancelled.')
        self.assertEqual(wo.state, 'cancel', 'Workorders should be cancelled.')
        self.assertTrue(mo.workorder_ids.time_ids.date_end, 'The timers must stop after the cancellation of the MO')

    def test_manual_duration(self):
        production_form = Form(self.env['mrp.production'])
        production_form.product_id = self.bom_4.product_id
        production_form.bom_id = self.bom_4
        production_form.product_qty = 1
        production_form.product_uom_id = self.bom_4.product_id.uom_id

        production = production_form.save()
        production.action_confirm()

        production_form = Form(production)
        production_form.qty_producing = 1
        production = production_form.save()
        production.button_mark_done()

        self.assertEqual(production.duration, production.workorder_ids.duration_expected)

    def test_starting_wo_twice(self):
        """
            Check that the work order is started only once when clicking the start button several times.
        """
        # Required for `workorder_ids` to be visible in the view
        self.env.user.groups_id += self.env.ref('mrp.group_mrp_routings')
        production_form = Form(self.env['mrp.production'])
        production_form.bom_id = self.bom_2
        production_form.product_qty = 1
        production = production_form.save()
        production_form = Form(production)
        with production_form.workorder_ids.new() as wo:
            wo.name = 'OP1'
            wo.workcenter_id = self.workcenter_1
            wo.duration_expected = 40
        production = production_form.save()
        production.action_confirm()
        production.button_plan()
        production.workorder_ids[0].button_start()
        production.workorder_ids[0].button_start()
        self.assertEqual(len(production.workorder_ids[0].time_ids.filtered(lambda t: t.date_start and not t.date_end)), 1)

    def test_qty_update_and_method_reservation(self):
        """
        When the reservation method of Manufacturing is 'manual', updating the
        quantity of a confirmed MO shouldn't trigger the reservation of the
        components
        """
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], order='id', limit=1)
        warehouse.manu_type_id.reservation_method = 'manual'

        for product in self.product_1 + self.product_2:
            product.is_storable = True
            self.env['stock.quant']._update_available_quantity(product, warehouse.lot_stock_id, 10)

        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom_1
        mo = mo_form.save()
        mo.action_confirm()

        self.assertFalse(mo.move_raw_ids.move_line_ids)

        wizard = self.env['change.production.qty'].create({
            'mo_id': mo.id,
            'product_qty': 5,
        })
        wizard.change_prod_qty()

        self.assertFalse(mo.move_raw_ids.move_line_ids)

    def test_source_and_child_mo(self):
        """
        Suppose three manufactured products A, B and C. C is a component of B
        and B is a component of A. If B and C have the routes MTO + Manufacture,
        when producing one A, it should generate a MO for B and C. Moreover,
        starting from one of the MOs, we should be able to find the source/child
        MO.
        (The test checks the flow in 1-step, 2-steps and 3-steps manufacturing)
        """
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        mto_route = warehouse.mto_pull_id.route_id
        manufacture_route = warehouse.manufacture_pull_id.route_id
        mto_route.active = True

        grandparent, parent, child = self.env['product.product'].create([{
            'name': n,
            'is_storable': True,
            'route_ids': [(6, 0, mto_route.ids + manufacture_route.ids)],
        } for n in ['grandparent', 'parent', 'child']])
        component = self.env['product.product'].create({
            'name': 'component',
            'type': 'consu',
        })

        self.env['mrp.bom'].create([{
            'product_tmpl_id': finished_product.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': compo.id, 'product_qty': 1}),
            ],
        } for finished_product, compo in [(grandparent, parent), (parent, child), (child, component)]])
        none_production = self.env['mrp.production']
        for steps, case_description, in [('mrp_one_step', '1-step Manufacturing'), ('pbm', '2-steps Manufacturing'), ('pbm_sam', '3-steps Manufacturing')]:
            warehouse.manufacture_steps = steps
            warehouse.manufacture_mto_pull_id.procure_method = "make_to_order"
            grandparent_production_form = Form(self.env['mrp.production'])
            grandparent_production_form.product_id = grandparent
            grandparent_production = grandparent_production_form.save()
            grandparent_production.action_confirm()

            child_production, parent_production = self.env['mrp.production'].search([('product_id', 'in', (parent + child).ids)], order='id desc', limit=2)

            for source_mo, mo, product, child_mo in [(none_production, grandparent_production, grandparent, parent_production),
                                                     (grandparent_production, parent_production, parent, child_production),
                                                     (parent_production, child_production, child, none_production)]:

                self.assertEqual(mo.product_id, product, '[%s] There should be a MO for product %s' % (case_description, product.display_name))
                self.assertEqual(mo.mrp_production_source_count, len(source_mo), '[%s] Incorrect value for product %s' % (case_description, product.display_name))
                self.assertEqual(mo.mrp_production_child_count, len(child_mo), '[%s] Incorrect value for product %s' % (case_description, product.display_name))

                source_action = mo.action_view_mrp_production_sources()
                child_action = mo.action_view_mrp_production_childs()
                self.assertEqual(source_action.get('res_id', False), source_mo.id, '[%s] Incorrect value for product %s' % (case_description, product.display_name))
                self.assertEqual(child_action.get('res_id', False), child_mo.id, '[%s] Incorrect value for product %s' % (case_description, product.display_name))

    @freeze_time('2022-06-28 08:00')
    def test_replan_workorders01(self):
        """
        Create two MO, each one with one WO. Set the same scheduled start date
        to each WO during the creation of the MO. A warning will be displayed.
        -> The user replans one of the WO: the warnings should disappear and the
        WO should be postponed.
        """
        # Required for `workorder_ids` to be visible in the view
        self.env.user.groups_id += self.env.ref('mrp.group_mrp_routings')
        mos = self.env['mrp.production']
        for _ in range(2):
            mo_form = Form(self.env['mrp.production'])
            mo_form.bom_id = self.bom_4
            with mo_form.workorder_ids.edit(0) as wo_line:
                wo_line.date_start = datetime.now()
            mos += mo_form.save()
        mos.action_confirm()

        mo_01, mo_02 = mos
        wo_01 = mo_01.workorder_ids
        wo_02 = mo_02.workorder_ids

        self.assertTrue(wo_01.show_json_popover)
        self.assertTrue(wo_02.show_json_popover)

        wo_02.action_replan()

        self.assertFalse(wo_01.show_json_popover)
        self.assertFalse(wo_02.show_json_popover)
        self.assertEqual(wo_01.date_finished, wo_02.date_start)

    @freeze_time('2022-06-28 08:00')
    def test_replan_workorders02(self):
        """
        Create two MO, each one with one WO. Set the same scheduled start date
        to each WO after the creation of the MO. A warning will be displayed.
        -> The user replans one of the WO: the warnings should disappear and the
        WO should be postponed.
        """
        # Required for `workorder_ids` to be visible in the view
        self.env.user.groups_id += self.env.ref('mrp.group_mrp_routings')
        mos = self.env['mrp.production']
        for _ in range(2):
            mo_form = Form(self.env['mrp.production'])
            mo_form.bom_id = self.bom_4
            mos += mo_form.save()
        mos.action_confirm()
        mo_01, mo_02 = mos

        for mo in mos:
            with Form(mo) as mo_form:
                with mo_form.workorder_ids.edit(0) as wo_line:
                    wo_line.date_start = datetime.now()

        wo_01 = mo_01.workorder_ids
        wo_02 = mo_02.workorder_ids
        self.assertTrue(wo_01.show_json_popover)
        self.assertTrue(wo_02.show_json_popover)

        wo_02.action_replan()

        self.assertFalse(wo_01.show_json_popover)
        self.assertFalse(wo_02.show_json_popover)
        self.assertEqual(wo_01.date_finished, wo_02.date_start)

    @freeze_time('2022-10-05 12:00')
    def test_replan_mo_without_bom(self):
        """
            Create 2 MOs without BoM
                just set the product and a component

            For first MO :
                Add 2 WO (with different WC)
                Don't schedule first WO
                Schedule second WO
                Confirm => MO is Confirmed and Planned
                Schedule first WO before second WO
                Confirm => MO should Replan without Error

            For second MO :
                Add 1 Scheduled WO
                Confirm => MO is Confirmed and Planned
                Add a second WO scheduled before the other one (with different WC)
                Confirm => MO should Replan without Error
        """

        # Required for `workorder_ids` to be visible in the view
        self.env.user.groups_id += self.env.ref('mrp.group_mrp_routings')

        mos = self.env['mrp.production']
        for _ in range(2):
            mo_form = Form(self.env['mrp.production'])
            mo_form.product_id = self.product_8
            with mo_form.move_raw_ids.new() as component:
                component.product_id = self.product_6
            mos += mo_form.save()
        mo_01, mo_02 = mos

        #First MO
        with Form(mo_01) as mo_01_form:
            with mo_01_form.workorder_ids.new() as workorder:
                workorder.name = "OP1"
                workorder.workcenter_id = self.workcenter_2
            with mo_01_form.workorder_ids.new() as workorder:
                workorder.name = "OP2"
                workorder.workcenter_id = self.workcenter_3
                workorder.date_start = datetime(2022, 10, 23, 12)
            mo_01 = mo_01_form.save()
        mo_01.action_confirm()

        op_1, op_2 = mo_01.workorder_ids.sorted('id')
        self.assertEqual(op_2.date_start, datetime(2022, 10, 23, 12))

        with Form(mo_01) as mo_01_form:
            with mo_01_form.workorder_ids.edit(0) as workorder:
                workorder.date_start = datetime(2022, 10, 18, 12)
            mo_01 = mo_01_form.save()

        self.assertEqual(op_1.date_start, datetime(2022, 10, 18, 12))
        # no auto replan
        self.assertEqual(op_2.date_start, datetime(2022, 10, 23, 12))
        self.assertNotEqual(op_1.date_finished, op_2.date_start)

        #Second MO
        with Form(mo_02) as mo_02_form:
            with mo_02_form.workorder_ids.new() as workorder:
                workorder.name = "OP1"
                workorder.workcenter_id = self.workcenter_2
                workorder.date_start = datetime(2022, 10, 20, 12)
            mo_02 = mo_02_form.save()
        mo_02.action_confirm()
        self.assertFalse(op_1.show_json_popover)

        with Form(mo_02) as mo_02_form:
            with mo_02_form.workorder_ids.new() as workorder:
                workorder.name = "OP2"
                workorder.workcenter_id = self.workcenter_3
                workorder.date_start = datetime(2022, 10, 18, 12)
            mo_02 = mo_02_form.save()

        op_1, op_2 = mo_02.workorder_ids.sorted('id')
        self.assertEqual(op_1.date_start, datetime(2022, 10, 20, 12))
        self.assertTrue(op_2.show_json_popover)

    @freeze_time('2023-03-01 12:00')
    def test_planning_cancelled_workorder(self):
        """Test when plan start time for workorders, cancelled workorders won't be taken into account.
        """
        self.env.company.resource_calendar_id.tz = 'Europe/Brussels'
        workcenter_1 = self.env['mrp.workcenter'].create({
            'name': 'wc1',
            'default_capacity': 1,
            'time_start': 10,
            'time_stop': 5,
            'time_efficiency': 100,
        })
        workcenter_2 = self.env['mrp.workcenter'].create({
            'name': 'wc2',
            'default_capacity': 1,
            'time_start': 10,
            'time_stop': 5,
            'time_efficiency': 100,
        })
        workcenter_3 = self.env['mrp.workcenter'].create({
            'name': 'wc3',
            'default_capacity': 1,
            'time_start': 10,
            'time_stop': 5,
            'time_efficiency': 100,
        })
        bom = self.env['mrp.bom'].create({
            'product_id': self.product_6.id,
            'product_tmpl_id': self.product_6.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'ready_to_produce': 'asap',
            'consumption': 'flexible',
            'product_qty': 1.0,
            'operation_ids': [
                (0, 0, {'name': 'Cutting Machine', 'workcenter_id': workcenter_1.id, 'time_cycle_manual': 30, 'sequence': 1}),
                (0, 0, {'name': 'Weld Machine', 'workcenter_id': workcenter_2.id, 'time_cycle_manual': 30, 'sequence': 2}),
                (0, 0, {'name': 'Gift Wrap Machine', 'workcenter_id': workcenter_3.id, 'time_cycle_manual': 30, 'sequence': 3}),
            ],
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': self.product_2.id, 'product_qty': 1})
            ]})

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_6
        mo_form.bom_id = bom
        mo_form.product_qty = 2
        mo = mo_form.save()
        mo.action_confirm()
        mo.button_plan()
        self.assertEqual(mo.workorder_ids[0].date_start, datetime(2023, 3, 1, 12, 0))
        self.assertEqual(mo.workorder_ids[1].date_start, datetime(2023, 3, 1, 13, 15))
        self.assertEqual(mo.workorder_ids[2].date_start, datetime(2023, 3, 1, 14, 30))

        # wo_1 completely finished
        mo_form = Form(mo)
        mo_form.qty_producing = 2
        mo = mo_form.save()
        mo.workorder_ids[0].button_start()
        mo.workorder_ids[0].button_finish()
        # wo_2, wo_3 partially finished
        mo_form.qty_producing = 1
        mo = mo_form.save()
        mo.workorder_ids[1].button_start()
        mo.workorder_ids[1].button_finish()
        mo.workorder_ids[2].button_start()
        mo.workorder_ids[2].button_finish()

        action = mo.button_mark_done()
        backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder.save().action_backorder()
        mo_backorder = mo.procurement_group_id.mrp_production_ids[-1]
        mo_backorder.button_plan()

        self.assertEqual(mo_backorder.workorder_ids[0].state, 'cancel')
        self.assertEqual(mo_backorder.workorder_ids[1].state, 'waiting')
        self.assertEqual(mo_backorder.workorder_ids[2].state, 'pending')
        self.assertFalse(mo_backorder.workorder_ids[0].date_start)
        self.assertEqual(mo_backorder.workorder_ids[1].date_start, datetime(2023, 3, 1, 12, 0))
        self.assertEqual(mo_backorder.workorder_ids[2].date_start, datetime(2023, 3, 1, 12, 45))

    def test_compute_product_id(self):
        """
            Tests the creation of a production order automatically sets the product when the bom is provided,
            without the need to put it in the vals of the create nor to call onchanges.
        """
        order = self.env['mrp.production'].create({
            'bom_id': self.bom_1.id,
        })
        self.assertEqual(order.product_id, self.bom_1.product_id)

    def test_compute_product_uom_id(self):
        """
            Tests the creation of a production order automatically sets the uom when the bom is provided,
            without the need to put it in the vals of the create nor to call onchanges.
        """
        order = self.env['mrp.production'].create({
            'bom_id': self.bom_1.id,
        })
        self.assertEqual(order.product_uom_id, self.bom_1.product_uom_id)

    def test_compute_bom_id(self):
        """
            Tests the creation of a production order automatically sets the bom when the product is provided,
            without the need to put it in the vals of the create nor to call onchanges.
        """
        order = self.env['mrp.production'].create({
            'product_id': self.bom_1.product_id.id,
        })
        self.assertEqual(order.bom_id, self.bom_1)

    def test_move_raw_uom_rounding(self):
        """Test that the correct rouding is applied on move_raw in
        manufacturing orders"""

        self.box250 = self.env['uom.uom'].create({
            'name': 'box250',
            'category_id': self.env.ref('uom.product_uom_categ_unit').id,
            'ratio': 250.0,
            'uom_type': 'bigger',
            'rounding': 1.0,
        })

        test_bom = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product_7_template.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 250.0,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': self.product_2.id, 'product_qty': 1.0, 'product_uom_id': self.box250.id}),
            ]
        })
        self.env['stock.quant'].create({
            'location_id':self.env.ref('stock.stock_location_stock').id,
            'product_id': self.product_2.id,
            'inventory_quantity': 500
        }).action_apply_inventory()

        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = test_bom
        mo = mo_form.save()
        mo.action_confirm()

        self.assertEqual(mo.move_raw_ids.product_uom_qty, 1)
        self.assertEqual(mo.move_raw_ids.move_line_ids.quantity, mo.move_raw_ids.product_uom_qty)
        self.assertEqual(mo.move_raw_ids.availability, 250)
        update_quantity_wizard = self.env['change.production.qty'].create({
            'mo_id': mo.id,
            'product_qty': 300,
        })
        update_quantity_wizard.change_prod_qty()

        self.assertEqual(mo.move_raw_ids.product_uom_qty, 2)
        self.assertEqual(mo.move_raw_ids.move_line_ids.quantity, mo.move_raw_ids.product_uom_qty)
        self.assertEqual(mo.move_raw_ids.availability, 0)

    def test_update_qty_to_consume_of_component(self):
        """
        The UoM of the finished product has a rounding precision equal to 1.0
        and the UoM of the component has a decimal one. When the producing qty
        is set, an onchange autocomplete the consumed quantity of the component.
        Then, when updating the 'to consume' quantity of the components, their
        consumed quantity is updated again. The test ensures that this update
        respects the rounding precisions
        """
        self.uom_dozen.rounding = 1
        self.bom_4.product_uom_id = self.uom_dozen

        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom_4
        mo = mo_form.save()
        mo.action_confirm()

        mo.action_toggle_is_locked()
        with Form(mo) as mo_form:
            mo_form.qty_producing = 1
            with mo_form.move_raw_ids.edit(0) as raw:
                raw.product_uom_qty = 1.25

        self.assertEqual(mo.move_raw_ids.quantity, 1.25)

    def test_clear_finished_move(self):
        """ Test that the finished moves created by the compute are correctly
        erased after changing the finished product"""
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_1
        mo = mo_form.save()
        self.assertEqual(len(mo.move_finished_ids), 1)
        mo.product_id = self.product_2
        self.assertEqual(len(mo.move_finished_ids), 1)
        self.assertFalse(self.env['stock.move'].search([
            ('product_id', '=', self.product_1.id),
            ('state', '=', 'draft'),
        ]))

    def test_compute_picking_type_id(self):
        """
        Test that the operation type set on the bom is set in the manufacturing order
        when selecting the BoM"""
        self.env.user.groups_id += self.env.ref("stock.group_adv_location")
        picking_type = self.env['stock.picking.type'].create({
            'name': 'new_picking_type',
            'code': 'internal',
            'sequence_code': 'NPT',
            'default_location_src_id': self.env.ref('stock.stock_location_stock').id,
            'default_location_dest_id': self.stock_location_components.id,
            'warehouse_id': self.warehouse_1.id,
        })
        self.bom_1.picking_type_id = picking_type
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom_1
        mo = mo_form.save()
        self.assertEqual(mo.picking_type_id.id, picking_type.id)
        # MO_2
        self.assertFalse(self.bom_2.picking_type_id)
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom_2
        mo_2 = mo_form.save()
        picking_type_company = self.env['stock.picking.type'].search_read([
            ('code', '=', 'mrp_operation'),
            ('warehouse_id.company_id', 'in', mo_2.company_id.ids),
        ], ['company_id'], load=False, limit=1)
        self.assertEqual(mo_2.picking_type_id.id, picking_type_company[0]['id'])

    def test_onchange_picking_type_id_and_name(self):
        """
        Test that when changing the operation type, the name of the MO should be changed too
        """
        picking_type_1 = self.env['stock.picking.type'].create({
            'name': 'new_picking_type_1',
            'code': 'mrp_operation',
            'sequence_code': 'PT1',
            'default_location_src_id': self.stock_location_components.id,
            'default_location_dest_id': self.env.ref('stock.stock_location_stock').id,
            'warehouse_id': self.warehouse_1.id,
        })
        picking_type_2 = picking_type_1.copy({
            'name': 'new_picking_type_2',
            'sequence_code': 'PT2'
        })
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_1
        mo_form.picking_type_id = picking_type_1
        mo = mo_form.save()
        self.assertEqual(mo.name, "BWH/PT1/00001")
        mo.picking_type_id = picking_type_2
        self.assertEqual(mo.name, "BWH/PT2/00001")
        mo.picking_type_id = picking_type_1
        self.assertEqual(mo.name, "BWH/PT1/00002")
        mo.picking_type_id = picking_type_1
        self.assertEqual(mo.name, "BWH/PT1/00002")

    def test_onchange_bom_ids_and_picking_type(self):
        warehouse01 = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        warehouse02, warehouse03 = self.env['stock.warehouse'].create([
            {'name': 'Second Warehouse', 'code': 'WH02'},
            {'name': 'Third Warehouse', 'code': 'WH03'},
        ])

        finished_product = self.env['product.product'].create({'name': 'finished product'})
        bom_wh01, bom_wh02 = self.env['mrp.bom'].create([{
            'product_id': finished_product.id,
            'product_tmpl_id': finished_product.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'bom_line_ids': [(0, 0, {'product_id': self.product.id, 'product_qty': 1})],
            'picking_type_id': wh.manu_type_id.id,
            'sequence': wh.id,
        } for wh in [warehouse01, warehouse02]])

        # Prioritize BoM of WH02
        bom_wh01.sequence = bom_wh02.sequence + 1

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = finished_product
        self.assertEqual(mo_form.bom_id, bom_wh02, 'Should select the first BoM in the list, whatever the picking type is')
        self.assertEqual(mo_form.picking_type_id, warehouse02.manu_type_id)

        mo_form.bom_id = bom_wh01
        self.assertEqual(mo_form.picking_type_id, warehouse01.manu_type_id, 'Should be adapted because of the found BoM')

        mo_form.bom_id = bom_wh02
        self.assertEqual(mo_form.picking_type_id, warehouse02.manu_type_id, 'Should be adapted because of the found BoM')

        mo_form.picking_type_id = warehouse01.manu_type_id
        self.assertEqual(mo_form.bom_id, bom_wh02, 'Should not change')
        self.assertEqual(mo_form.picking_type_id, warehouse01.manu_type_id, 'Should not change')

        mo_form.picking_type_id = warehouse03.manu_type_id
        mo_form.bom_id = bom_wh01
        self.assertEqual(mo_form.picking_type_id, warehouse01.manu_type_id, 'Should be adapted because of the found BoM '
                                                                            '(the selected picking type should be ignored)')

        mo_form = Form(self.env['mrp.production'].with_context(default_picking_type_id=warehouse03.manu_type_id.id))
        mo_form.product_id = finished_product
        self.assertFalse(mo_form.bom_id, 'Should not find any BoM, because of the defined picking type')
        self.assertEqual(mo_form.picking_type_id, warehouse03.manu_type_id)

        mo_form = Form(self.env['mrp.production'].with_context(default_picking_type_id=warehouse01.manu_type_id.id))
        mo_form.product_id = finished_product
        self.assertEqual(mo_form.bom_id, bom_wh01, 'Should select the BoM that matches the default picking type')
        self.assertEqual(mo_form.picking_type_id, warehouse01.manu_type_id, 'Should be the default one')

        mo_form.bom_id = bom_wh02
        self.assertEqual(mo_form.picking_type_id, warehouse01.manu_type_id, 'Should not change, because of default value')

        mo_form.picking_type_id = warehouse02.manu_type_id
        self.assertEqual(mo_form.bom_id, bom_wh02, 'Should not change')
        self.assertEqual(mo_form.picking_type_id, warehouse02.manu_type_id, 'Should not change')

        mo_form.picking_type_id = warehouse02.manu_type_id
        mo_form.bom_id = bom_wh02
        self.assertEqual(mo_form.picking_type_id, warehouse01.manu_type_id, 'Should be adapted because of the default value')

    def test_workcenter_specific_capacities(self):
        """ Test that the duraction expected is correctly computed when specific capacities are defined on the workcenter.
        """
        # Required for `workorder_ids` to be visible in the view
        self.env.user.groups_id += self.env.ref('mrp.group_mrp_routings')
        self.workcenter_2.update({
            'time_start': 10,
            'time_stop': 20,
        })
        self.env['mrp.workcenter.capacity'].create({
            'product_id': self.product_4.id,
            'workcenter_id': self.workcenter_2.id,
            'time_start': 5,
            'time_stop': 10,
        })

        production_form = Form(self.env['mrp.production'])
        production_form.product_id = self.product_5
        production = production_form.save()

        with Form(production) as mo_form:
            with mo_form.workorder_ids.new() as wo:
                wo.name = "OP1"
                wo.workcenter_id = self.workcenter_2

        # Since no duration was given, only duration from the workcenter setup/cleanup time should be added in : 10 + 20 = 30
        self.assertEqual(production.workorder_ids[0].duration_expected, 30.0, "Workcenter setup time (10) + workcenter cleanup time (20)")

        # Change the product so that it uses a specific capacity of that workcenter
        with Form(production) as mo_form:
            mo_form.product_id = self.product_4
            with mo_form.workorder_ids.new() as wo:
                wo.name = "OP1"
                wo.workcenter_id = self.workcenter_2

        # Only duration from the workcenter specific capacity setup/cleanup times since there is one defined for this product.
        self.assertEqual(production.workorder_ids[0].duration_expected, 15.0, "Capacity setup time (5) + capacity cleanup time (10)")

    def test_unlink_workorder_with_consumed_operations(self):
        self.bom_3.bom_line_ids[0].operation_id = self.bom_3.operation_ids[0].id
        self.bom_3.bom_line_ids[1].operation_id = self.bom_3.operation_ids[1].id
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom_3
        mo = mo_form.save()
        mo.workorder_ids[1].unlink()
        mo.action_confirm()
        self.assertEqual(mo.state, 'confirmed')
        self.assertEqual(len(mo.workorder_ids), 2)

    def test_consumption_action_set_qty_and_validate(self):
        """
        Check `To Consume` and `Consumed` qty are correctly updated to match the consumption warning values
        under 5 use cases:
        scenario 1:
        - bom is changed after MO is created => action_set_qty = match BoM
        scenario 2 (combined 3 use cases since they shouldn't affect each other):
        - a component move is deleted before MO is confirmed => action_set_qty = add missing BoM component
        - a component's UoM is changed after MO is created => action_set_qty = match BoM qty, but leave UoM unchanged (i.e. correctly convert)
        - add a new component not part of the BOM
        scenario 3:
        - a component has 2 moves in a MO => action_set_qty = set the 1st move to the correct qty, set 2nd move to 0
          (i.e. no way to know how to distribute quantity across these moves since warning aggregates qty by product)
        """
        mo, bom, p_final, p1, p2 = self.generate_mo(consumption='warning', qty_final=10, qty_base_1=12, qty_base_2=20)

        #### scenario 1 - change BoM after MO created ####
        mo_form = Form(mo)
        mo_form.qty_producing = 4
        mo = mo_form.save()
        # mo.move_raw_ids[0] = p2 => 20 qty_base, mo.move_raw_ids[1] = p1 => 12 qty_base
        self.assertEqual(mo.move_raw_ids[0].product_uom_qty, 200, "current MO To Consume qty should match expected qty to produce")
        self.assertEqual(mo.move_raw_ids[0].quantity, 80, "current MO Consumed qty should match expected qty to produce")
        self.assertEqual(mo.move_raw_ids[1].product_uom_qty, 120, "current MO To Consume qty should match expected qty produced")
        self.assertEqual(mo.move_raw_ids[1].quantity, 48, "current MO Consumed qty should match expected qty produced")
        # bom changes won't auto-update MO, it will only show diff in consumption warning
        bom.bom_line_ids[0].product_qty = 10
        self.assertEqual(mo.move_raw_ids[0].product_uom_qty, 200)
        self.assertEqual(mo.move_raw_ids[0].quantity, 80)
        action = mo.button_mark_done()
        warning = Form(self.env['mrp.consumption.warning'].with_context(**action['context']))
        consumption = warning.save()
        self.assertEqual(consumption.mrp_consumption_warning_line_ids.product_consumed_qty_uom, 80, "qty consumed incorrectly passed to wizard")
        self.assertEqual(consumption.mrp_consumption_warning_line_ids.product_expected_qty_uom, 40, "expected qty should match current BoM qty for qty being produced")
        action = consumption.action_set_qty()
        backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder.save().action_backorder()
        self.assertEqual(mo.move_raw_ids[0].product_uom_qty, 80, "current bom expected qty should remain unchanged")
        self.assertEqual(mo.move_raw_ids[0].quantity, 40, "current bom expected qty was not applied as qty to be done")
        self.assertEqual(mo.move_raw_ids[1].product_uom_qty, 48, "line without consumption issue was incorrectly changed")
        self.assertEqual(mo.move_raw_ids[1].quantity, 48, "line without consumption issue was incorrectly changed")
        self.assertEqual(mo.state, 'done')
        # double check that backorder qtys are also correct
        mo_backorder = mo.procurement_group_id.mrp_production_ids[-1]
        self.assertEqual(mo_backorder.move_raw_ids[0].product_uom_qty, 120, "backorder values are based on original MO, not current bom")
        self.assertEqual(mo_backorder.move_raw_ids[1].product_uom_qty, 72, "backorder values incorrectly calculated")

        #### scenario 2 - that removing a line in the MO + changing the uom of a line + adding a component not on the BOM ####
        mo2_form = Form(self.env['mrp.production'])
        mo2_form.product_id = p_final
        mo2_form.bom_id = bom
        mo2_form.product_qty = 5.0
        with mo2_form.move_raw_ids.new() as move:
            move.product_id = self.product_1
            move.product_uom_qty = 50
        mo2 = mo2_form.save()
        for move in mo2.move_raw_ids:
            if move.product_id == p2:
                move.unlink()
            elif move.product_id == p1:
                # p1 = qty_base_1 = 12 => now 12 dozens instead of units
                move.product_uom = self.env.ref('uom.product_uom_dozen')
        mo2.action_confirm()
        mo2_form = Form(mo2)
        mo2_form.qty_producing = 4
        mo2 = mo2_form.save()
        self.assertEqual(len(mo2.move_raw_ids), 2, "current MO should still have 1 component from its BoM deleted + 1 additional component")
        self.assertEqual(mo2.move_raw_ids[0].product_uom_qty, 60, "current MO To Consume qty should match manually set expected qty produced")
        self.assertEqual(mo2.move_raw_ids[0].quantity, 48, "current MO Consumed qty should match expected qty to produce based on manually set value")
        self.assertEqual(mo2.move_raw_ids[1].product_uom_qty, 50, "current MO To Consume qty should match manually set expected qty produced")
        self.assertEqual(mo2.move_raw_ids[1].quantity, 40, "current MO Consumed qty should match expected qty to produce based on manually set value")

        action = mo2.button_mark_done()
        warning = Form(self.env['mrp.consumption.warning'].with_context(**action['context']))
        consumption = warning.save()
        self.assertEqual(len(consumption.mrp_consumption_warning_line_ids), 3, "deleted move should also show as an consumption line diff from BoM")
        # mrp_consumption_warning_line_ids[2] = p1 => 12 unit qty_base
        # mrp_consumption_warning_line_ids[1] = p2 => 10 unit qty_base
        # mrp_consumption_warning_line_ids[0] = self.product_1 => 10 unit qty_base
        self.assertEqual(consumption.mrp_consumption_warning_line_ids[0].product_consumed_qty_uom, 40, "additional component was not correctly passed to wizard")
        self.assertEqual(consumption.mrp_consumption_warning_line_ids[0].product_expected_qty_uom, 0, "additional component should have no expected qty")
        self.assertEqual(consumption.mrp_consumption_warning_line_ids[1].product_consumed_qty_uom, 0, "missing line was not correctly passed to wizard")
        self.assertEqual(consumption.mrp_consumption_warning_line_ids[1].product_expected_qty_uom, 40, "expected qty should match current BoM qty for qty being produced")
        self.assertEqual(consumption.mrp_consumption_warning_line_ids[2].product_consumed_qty_uom, 576, "qty consumed was not correctly converted to product's uom before passing to wizard")
        self.assertEqual(consumption.mrp_consumption_warning_line_ids[2].product_expected_qty_uom, 48, "expected qty should match current BoM qty for qty being produced")
        action = consumption.action_set_qty()
        backorder2 = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder2.save().action_backorder()
        # expect 3 moves: 1 for the originally missing product p2 with qty demand/done = 40
        #                 1 for the overused product p1 one with qty demand/done = 48/12 = 4 dozens
        #                 1 for the additional product self.product_1 with demand/done = 40/0
        self.assertEqual(len(mo2.move_raw_ids), 3, "missing line was not correctly added")
        for move in mo2.move_raw_ids:
            if move.product_id == p2:
                self.assertEqual(move.product_uom_qty, 40, "missing line values were not correctly added")
                self.assertEqual(move.quantity, 40, "missing line values were not correctly added")
            elif move.product_id == p1:
                self.assertEqual(move.product_uom_qty, 48, "expected qty should be unchanged")
                self.assertEqual(move.quantity, 4, "expected qty was not applied as qty to be done (UoM was possibly not correctly converted)")
            else:
                self.assertEqual(move.product_uom_qty, 40, "additional component's demand should have carried over")
                self.assertEqual(move.quantity, 0, "additional component should have nothing reserved")
        self.assertEqual(mo2.state, 'done')
        # double check that backorder qtys are also correct
        mo2_backorder = mo2.procurement_group_id.mrp_production_ids[-1]
        self.assertEqual(len(mo2_backorder.move_raw_ids), 2, "missing line should NOT have been added in but additional line should")
        self.assertEqual(mo2_backorder.move_raw_ids.product_id.ids, [p1.id, self.product_1.id])
        self.assertEqual(mo2_backorder.move_raw_ids[0].product_uom_qty, 12, "backorder values are based on original MO, not current bom")

        #### scenario 3 - repeated comp move ####
        # bom.bom_line_ids[0]/product_id = p2
        bom.bom_line_ids[0].unlink()
        mo3 = self.env['mrp.production'].create({
            'product_id': p_final.id,
            'bom_id': bom.id,
            'product_qty': 1,
            'product_uom_id': p_final.uom_id.id,
        })
        mo3_form = Form(mo3)
        with mo3_form.move_raw_ids.new() as line:
            line.product_id = p1
            line.product_uom_qty = 5
        mo3 = mo3_form.save()
        mo3.action_confirm()
        self.assertEqual(len(mo3.move_raw_ids), 2, "there should be 2 comp lines")
        self.assertEqual(len(mo3.move_raw_ids.product_id), 1, "comp lines should have same product")
        mo3_form = Form(mo3)
        mo3_form.qty_producing = 1
        mo3 = mo3_form.save()
        self.assertEqual(mo3.move_raw_ids[0].product_uom_qty, 12, "BoM created comp move does not match expected To Consume qty")
        self.assertEqual(mo3.move_raw_ids[0].quantity, 12, "BoM created comp move does not match expected Consumed qty")
        self.assertEqual(mo3.move_raw_ids[1].product_uom_qty, 5, "Manually added comp move does not match original To Consume qty")
        self.assertEqual(mo3.move_raw_ids[1].quantity, 5, "Manually added comp move was not Consumed")
        action = mo3.button_mark_done()
        warning = Form(self.env['mrp.consumption.warning'].with_context(**action['context']))
        consumption = warning.save()
        self.assertEqual(len(consumption.mrp_consumption_warning_line_ids), 1, "warning lines should be grouped by product")
        self.assertEqual(consumption.mrp_consumption_warning_line_ids[0].product_expected_qty_uom, 12, "BoM expected qty not correctly passed to wizard")
        self.assertEqual(consumption.mrp_consumption_warning_line_ids[0].product_consumed_qty_uom, 17, "total Consumed qty not correctly passed to wizard")
        action = consumption.action_set_qty()
        self.assertEqual(mo3.move_raw_ids[0].product_uom_qty, 12, "BoM created comp move does not match expected To Consume qty")
        self.assertEqual(mo3.move_raw_ids[0].quantity, 12, "BoM created comp move does not match expected Consumed qty")
        self.assertEqual(mo3.move_raw_ids[1].product_uom_qty, 5, "Manually added comp move To Consume qty should be unchanged")
        self.assertEqual(mo3.move_raw_ids[1].quantity, 0, "Extra line Consumed qty not correctly zero-ed")
        self.assertEqual(mo3.state, 'done')

    def test_exceeded_consumed_qty_and_duplicated_lines(self):
        """
        Two components C01, C02. C01 has the MTO route.
        MO with 1 x C01, 1 x C02, 1 x C02.
        Process the MO and set a high consumed qty for C01.
        Ensure that the MO can still be processed and that the consumed quantities
        are correct.
        """
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        mto_route = warehouse.mto_pull_id.route_id
        manufacture_route = warehouse.manufacture_pull_id.route_id
        mto_route.active = True

        product01, product02, product03 = self.env['product.product'].create([{
            'name': 'Product %s' % (i + 1),
            'is_storable': True,
        } for i in range(3)])

        product02.route_ids = [(6, 0, (mto_route | manufacture_route).ids)]

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product01
        mo_form.product_qty = 1
        for component in (product02, product03, product03):
            with mo_form.move_raw_ids.new() as line:
                line.product_id = component
                line.product_uom_qty = 1
        mo = mo_form.save()
        mo.action_confirm()

        mo_form = Form(mo)
        mo_form.qty_producing = 1.0
        mo = mo_form.save()

        mo.move_raw_ids[0].move_line_ids.quantity = 1.5
        mo.button_mark_done()

        self.assertEqual(mo.state, 'done')

        p02_raws = mo.move_raw_ids.filtered(lambda m: m.product_id == product02)
        p03_raws = mo.move_raw_ids.filtered(lambda m: m.product_id == product03)
        self.assertEqual(sum(p02_raws.mapped('quantity')), 1.5)
        self.assertEqual(sum(p03_raws.mapped('quantity')), 2)

    def test_validation_mo_with_tracked_component(self):
        """ check that the verification of SN for tracked component is ignored when the quantity to consume is 0.
        """
        self.product_2.tracking = 'serial'
        bom = self.env["mrp.bom"].create({
            'product_tmpl_id': self.product_6.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [(0, 0, {
                'product_id': self.product_2.id,
                'product_qty': 1.0,
            }), (0, 0, {
                'product_id': self.product_3.id,
                'product_qty': 1.0,
            })]
        })
        # create the MO and confirm it
        mo = self.env['mrp.production'].create({
            'product_id': self.product_6.id,
            'bom_id': bom.id,
            'product_uom_qty': 1.0,
        })
        mo.action_confirm()
        self.assertEqual(mo.state, 'confirmed')
        # set the qty to consume of the tracked product to 0
        mo.move_raw_ids[0].product_uom_qty = 0
        mo.move_raw_ids[0].quantity = 0
        # Set MO Done and create backorder
        action = mo.button_mark_done()
        consumption_warning = Form(self.env['mrp.consumption.warning'].with_context(**action['context'])).save()

        self.assertEqual(len(consumption_warning.mrp_consumption_warning_line_ids), 1)
        self.assertEqual(consumption_warning.mrp_consumption_warning_line_ids[0].product_consumed_qty_uom, 0)
        self.assertEqual(consumption_warning.mrp_consumption_warning_line_ids[0].product_expected_qty_uom, 1)
        # Force the warning
        consumption_warning.action_confirm()
        self.assertEqual(mo.state, 'done')

    def test_cancel_return(self):
        """
        check that the return picking is not created on done state transfer when reducing MO quantity.
        """
        self.stock_location = self.env.ref('stock.stock_location_stock')
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        warehouse.manufacture_steps = 'pbm'

        mo, _bom, _p_final, p1, p2 = self.generate_mo(qty_final=5.0, qty_base_1=1.0, qty_base_2=1.0)
        mo.action_confirm()

        self.env['stock.quant']._update_available_quantity(p1, self.stock_location, 5.0)
        self.env['stock.quant']._update_available_quantity(p2, self.stock_location, 5.0)

        mo.picking_ids.move_ids[0].quantity = 5.0
        mo.picking_ids.move_ids[1].quantity = 5.0
        mo.picking_ids.button_validate()

        update_quantity_wizard = self.env['change.production.qty'].create({
            'mo_id': mo.id,
            'product_qty': 4.0,
        })
        update_quantity_wizard.change_prod_qty()
        new_picking = mo.picking_ids
        self.assertEqual(len(new_picking), 1, "Return picking should not be created in done Transfer")

    def test_manufacture_lead_days(self):
        """Test the lead days computation for manufacturing route.
        """
        rule = self.env['stock.rule'].search([('action', '=', 'manufacture')], limit=1)

        self.env.company.manufacturing_lead = 1
        self.bom_1.days_to_prepare_mo = 2
        self.bom_1.produce_delay = 3
        delays, _ = rule._get_lead_days(self.bom_1.product_id, bom=self.bom_1)
        self.assertEqual(delays['total_delay'], self.env.company.manufacturing_lead + self.bom_1.days_to_prepare_mo + self.bom_1.produce_delay)

        # switch to the 3 steps, only pre-production rules delays will be taken into account
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        warehouse.manufacture_steps = 'pbm_sam'
        warehouse.pbm_route_id.rule_ids.delay = 100
        delays, _ = rule._get_lead_days(self.bom_1.product_id, bom=self.bom_1)
        self.assertEqual(delays['total_delay'], self.env.company.manufacturing_lead + self.bom_1.days_to_prepare_mo + self.bom_1.produce_delay + 100 * 2)

    def test_use_kit_as_component_in_production_without_bom(self):
        """
        Test that a MO is not cancelled when a kit is added in a MO without a BoM.
        """
        finished, component, kit = self.env['product.product'].create([{
            'name': 'Product %s' % (i + 1),
            'is_storable': True,
        } for i in range(3)])
        self.env['mrp.bom'].create({
            'product_id': kit.id,
            'product_tmpl_id': kit.product_tmpl_id.id,
            'type': 'phantom',
            'bom_line_ids': [(0, 0, {
                'product_id': component.id,
                'product_qty': 1,
            })],
        })

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = finished
        mo_form.product_qty = 1
        with mo_form.move_raw_ids.new() as line:
            line.product_id = kit
        mo = mo_form.save()
        mo.action_confirm()
        self.assertEqual(mo.state, 'confirmed')
        self.assertEqual(mo.move_raw_ids.product_id, component)

    def test_product_variants_in_mo(self):
        """
        Test that the moves are corrltly removed when the poduct variant is changed
        """
        # Add another attribute line to test efficiency the function bom_line check
        size_attribute_line = self.env['product.template.attribute.line'].create([{
                'product_tmpl_id': self.product_7_template.id,
                 'attribute_id': self.size_attribute.id,
                 'value_ids': [(6, 0, self.size_attribute.value_ids.ids)]
             }])
        c1, c2, c3 = self.env['product.product'].create([{
            'name': i,
            'is_storable': True,
        } for i in range(3)])

        self.env['mrp.bom'].create({
            'product_tmpl_id': self.product_7_template.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 4.0,
            'type': 'normal',
            'bom_line_ids': [
                Command.create({
                    'product_id': c1.id,
                    'product_qty': 1,
                    'bom_product_template_attribute_value_ids': [(4, self.product_7_attr1_v2.id)]}), # Blue color
                Command.create({
                    'product_id': c2.id,
                    'product_qty': 1,
                    'bom_product_template_attribute_value_ids': [
                        (4, self.product_7_attr1_v1.id), # Red color
                        (4, size_attribute_line.product_template_value_ids[2].id) # size L
                    ]}),
                Command.create({
                    'product_id': c3.id,
                    'product_qty': 1,
                    'bom_product_template_attribute_value_ids': [(4, self.product_7_attr1_v1.id)]}), # Red color
            ]
        })

        mo_form = Form(self.env['mrp.production'])
        # select a product with a blue and s size attribute
        mo_form.product_id = self.product_7_template.product_variant_ids[1]
        mo_form.product_qty = 1
        mo = mo_form.save()
        self.assertEqual(mo.move_raw_ids.product_id, c1)
        # select a product with a red and L attribute (the compoent C1 should be removed and C2, C3 added)
        mo_form.product_id = self.product_7_template.product_variant_ids[6]
        mo = mo_form.save()
        self.assertEqual(mo.move_raw_ids.product_id, (c2 | c3))
        # select the product with red and s attribute (C2 and C3 should be removed and C1 added)
        mo_form.product_id = self.product_7_template.product_variant_ids[0]
        mo = mo_form.save()
        self.assertEqual(mo.move_raw_ids.product_id, c3)

    def test_mo_duration_expected(self):
        """
        Test to verify that the 'duration_expected' on a work order in a manufacturing order
        correctly remains as manually set after completion. This test involves creating a product
        with a Bill of Materials (BOM) and an operation with an initial expected duration.
        A manufacturing order is then created for this product, the expected duration of the
        work order is manually changed, and the order is completed. The test checks that
        the expected duration remains as manually set and does not revert to the original value.
        """
        production_form = Form(self.env['mrp.production'])
        production_form.product_id = self.product_6
        production_form.bom_id = self.bom_4
        production_form.product_qty = 5.0
        production = production_form.save()
        production.action_confirm()

        init_duration_expected = production.workorder_ids.duration_expected
        production.workorder_ids.duration_expected = init_duration_expected + 15

        # changing the qty producing should recompute the expected duration
        production_form = Form(production)
        production_form.qty_producing = 3.0
        production = production_form.save()

        current_duration_expected = production.workorder_ids.duration_expected
        self.assertNotEqual(current_duration_expected, init_duration_expected + 15)
        self.assertNotEqual(current_duration_expected, init_duration_expected)

        # one should not recompute the expected duration if the expected duration is changed
        # after the qty_producing is set
        production.workorder_ids.duration_expected = current_duration_expected + 10

        backorder_wizard_dict = production.button_mark_done()
        Form.from_action(self.env, backorder_wizard_dict).save().action_backorder()

        self.assertEqual(production.workorder_ids.duration_expected, current_duration_expected + 10)

        # One should not recompute the expected duration of a full production
        production = production.procurement_group_id.mrp_production_ids[-1]

        init_duration_expected = production.workorder_ids.duration_expected

        production.workorder_ids.duration_expected = init_duration_expected + 5

        production_form = Form(production)
        production_form.qty_producing = 2.0
        production = production_form.save()

        production.button_mark_done()

        self.assertEqual(production.workorder_ids.duration_expected, init_duration_expected + 5)

    def test_batch_production_01(self):
        """ Test the wizard mrp.batch.produce without tracked components.
        """
        self.product_4.tracking = 'serial'
        self.product_4.uom_id = self.uom_unit
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom_1
        mo = mo_form.save()
        mo.action_confirm()
        mo.action_assign()

        batch_produce_action = mo.button_mark_done()
        batch_produce = Form(self.env['mrp.batch.produce'].with_context(**batch_produce_action['context']))
        batch_produce.lot_name = "00001"
        batch_produce = batch_produce.save()
        batch_produce.action_generate_production_text()
        batch_produce.action_prepare()

        productions = mo.procurement_group_id.mrp_production_ids
        self.assertEqual(len(productions), 4)
        self.assertRecordValues(productions.lot_producing_id, [
            {'name': "00001"},
            {'name': "00002"},
            {'name': "00003"},
            {'name': "00004"},
        ])
        self.assertEqual(productions.mapped('state'), ['to_close'] * 4)

    def test_batch_production_02(self):
        """ Test the wizard mrp.batch.produce with a single tracked serial.
        """
        self.product_1.tracking = 'serial'
        self.product_4.tracking = 'serial'
        self.product_4.uom_id = self.uom_unit

        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom_1
        mo = mo_form.save()
        mo.action_confirm()
        mo.action_assign()

        batch_produce_action = mo.button_mark_done()
        batch_produce = Form(self.env['mrp.batch.produce'].with_context(**batch_produce_action['context']))
        # The white space for PO3 is to test that it is correctly stripped
        # Extra \n are also part of the test
        batch_produce.production_text = """
            00001,P01
            00002,P02
            00003,   P03
            00004,P04
        """
        batch_produce = batch_produce.save()
        batch_produce.action_done()

        productions = mo.procurement_group_id.mrp_production_ids
        self.assertEqual(len(productions), 4)
        for i in range(1, 5):
            production = productions[i-1]
            self.assertEqual(production.lot_producing_id.name, f"0000{i}")
            self.assertEqual(production.move_raw_ids.move_line_ids.lot_id.name, f"P0{i}")
            move_product_2 = production.move_raw_ids.filtered(lambda m: m.product_id == self.product_2)
            self.assertEqual(move_product_2.move_line_ids.quantity, 0.5)
            self.assertEqual(move_product_2.state, 'done')
            self.assertTrue(move_product_2.picked)

        self.assertEqual(productions.mapped('state'), ['done'] * 4)

    def test_batch_production_03(self):
        """ Test the wizard mrp.batch.produce with a mix of lot and serial.
        """
        self.product_1.tracking = 'serial'
        self.product_2.tracking = 'lot'
        self.product_4.tracking = 'serial'
        self.product_4.uom_id = self.uom_unit

        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.env['mrp.bom'].create({
            'product_id': self.product_4.id,
            'product_tmpl_id': self.product_4.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 4.0,
            'consumption': 'flexible',
            'operation_ids': [
            ],
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': self.product_2.id, 'product_qty': 2, 'manual_consumption': True}),
                (0, 0, {'product_id': self.product_1.id, 'product_qty': 4, 'manual_consumption': True})
            ]})
        mo = mo_form.save()
        mo.action_confirm()
        mo.action_assign()

        batch_produce_action = mo.button_mark_done()
        batch_produce = Form(self.env['mrp.batch.produce'].with_context(**batch_produce_action['context']))
        batch_produce.production_text = """
            00001,LOT01;2|LOT02;3,P01|P02
            00002,LOT01;4,P03
            00003,LOT01,P04|P05
            00004
        """
        batch_produce = batch_produce.save()
        self.assertEqual(batch_produce.production_text_help.split('\n')[1],
                         self.product_4.display_name + ',' +
                         self.product_2.display_name + ',' +
                         self.product_1.display_name)
        batch_produce.action_prepare()

        productions = mo.procurement_group_id.mrp_production_ids
        production_1, production_2, production_3, production_4 = productions
        self.assertEqual(production_1.lot_producing_id.name, "00001")
        move_1 = production_1.move_raw_ids.filtered(lambda m: m.product_id == self.product_1)
        move_2 = production_1.move_raw_ids.filtered(lambda m: m.product_id == self.product_2)
        self.assertRecordValues(move_2.move_line_ids, [
            {'quantity': 2},
            {'quantity': 3},
        ])
        self.assertRecordValues(move_2.move_line_ids.lot_id, [
            {'name': 'LOT01'},
            {'name': 'LOT02'},
        ])
        self.assertRecordValues(move_1.move_line_ids, [
            {'quantity': 1},
            {'quantity': 1},
        ])
        self.assertRecordValues(move_1.move_line_ids.lot_id, [
            {'name': 'P01'},
            {'name': 'P02'},
        ])

        move_1 = production_2.move_raw_ids.filtered(lambda m: m.product_id == self.product_1)
        move_2 = production_2.move_raw_ids.filtered(lambda m: m.product_id == self.product_2)
        self.assertRecordValues(move_2.move_line_ids, [{'quantity': 4}])
        self.assertRecordValues(move_2.move_line_ids.lot_id, [{'name': 'LOT01'}])
        self.assertRecordValues(move_1.move_line_ids, [{'quantity': 1}])
        self.assertRecordValues(move_1.move_line_ids.lot_id, [{'name': 'P03'}])

        move_1 = production_3.move_raw_ids.filtered(lambda m: m.product_id == self.product_1)
        move_2 = production_3.move_raw_ids.filtered(lambda m: m.product_id == self.product_2)
        self.assertRecordValues(move_2.move_line_ids, [{'quantity': 0.5}])
        self.assertRecordValues(move_2.move_line_ids.lot_id, [{'name': 'LOT01'}])
        self.assertRecordValues(move_1.move_line_ids, [
            {'quantity': 1},
            {'quantity': 1},
        ])
        self.assertRecordValues(move_1.move_line_ids.lot_id, [
            {'name': 'P04'},
            {'name': 'P05'},
        ])

        move_1 = production_4.move_raw_ids.filtered(lambda m: m.product_id == self.product_1)
        move_2 = production_4.move_raw_ids.filtered(lambda m: m.product_id == self.product_2)
        self.assertRecordValues(move_2.move_line_ids, [{'quantity': 0.5, 'lot_id': False}])
        self.assertRecordValues(move_1.move_line_ids, [{'quantity': 1, 'lot_id': False}])

    def test_batch_production_04(self):
        """ Test that splitting a MO correctly computes the duration of the workorders. """
        self.product_5.tracking = 'serial'
        self.bom_2.bom_line_ids.unlink()
        self.bom_2.operation_ids.write({
            'workcenter_id': self.workcenter_2.id,
            'time_cycle_manual': 60,
        })
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom_2
        mo_form.product_qty = 2
        mo = mo_form.save()
        mo.action_confirm()
        mo.button_plan()
        self.assertEqual(mo.workorder_ids.duration_expected, 120)

        batch_produce_action = mo.button_mark_done()
        batch_produce = Form(self.env['mrp.batch.produce'].with_context(**batch_produce_action['context']))
        batch_produce.lot_name = "00001"
        batch_produce = batch_produce.save()
        batch_produce.action_generate_production_text()
        batch_produce.action_prepare()

        productions = mo.procurement_group_id.mrp_production_ids
        self.assertListEqual(productions.workorder_ids.mapped('duration_expected'), [60, 60])

    def test_multi_edit_start_date_wo(self):
        """
        Test setting the start date for multiple workorders, checking if the finish date
        will be set too. As if the finish date is not set the planned workorder will not
        be shown in planning gantt view
        """
        self.env.company.resource_calendar_id.tz = 'Europe/Brussels'
        mo = self.env['mrp.production'].create({
            'product_id': self.product.id,
            'product_uom_id': self.bom_1.product_uom_id.id,
        })

        wos = self.env['mrp.workorder'].create([
            {
                'name': 'Test order',
                'workcenter_id': self.workcenter_1.id,
                'product_uom_id': self.bom_1.product_uom_id.id,
                'production_id': mo.id,
                'duration_expected': 1.0
            },
            {
                'name': 'Test order2',
                'workcenter_id': self.workcenter_2.id,
                'product_uom_id': self.bom_1.product_uom_id.id,
                'production_id': mo.id,
                'duration_expected': 2.0
            }
        ])
        dt = datetime(2024, 1, 17, 11)
        wos.date_start = dt

        self.assertEqual(wos[0].date_start, dt)
        self.assertEqual(wos[1].date_start, dt)

        self.assertEqual(wos[0].date_finished, dt + timedelta(hours=1, minutes=1))
        self.assertEqual(wos[1].date_finished, dt + timedelta(hours=1, minutes=2))

    @users('hilda')
    def test_update_mo_with_mrp_user(self):
        """
        Create an MO with an MRP user, in Draft status, try to update its quantity.
        """
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product
        mo_form.product_qty = 5
        mo = mo_form.save()
        mo_form.product_qty = 10
        mo_form.save()
        self.assertEqual(mo.product_qty, 10)

    @freeze_time('2017-01-01')
    def test_expected_duration_alternative_wc(self):
        """
            Check that the fastest work center is used when planning the workorder.
            - create two work centers with similar production capacity (1)
                but the work_center_1 with a longer prepartion time for finished product.
            1:/ produce 1 units > work_center_2 faster because
                it does not need much time to start and to finish the production.
            2/ - Create a second mo to produce one unit of P1
                - work_center_1 faster because workcenter_2 is busy despite being faster
                in preparation but it will finish later than workcenter 1.
        """
        workcenter_1 = self.env['mrp.workcenter'].create({
            'name': 'wc1',
            'default_capacity': 1,
            'time_start': 2,
            'time_stop': 2,
            'time_efficiency': 100,
        })
        workcenter_2 = workcenter_1.copy({'name': 'wc2'})

        workcenter_1.alternative_workcenter_ids = workcenter_2
        workcenter_1.capacity_ids = [Command.create({'product_id': self.product_1.id, 'capacity': 1, 'time_start': 10})]
        workcenter_2.capacity_ids = [Command.create({'product_id': self.product_1.id, 'capacity': 1, 'time_start': 5})]

        self.product_1.uom_id = self.uom_unit.id
        bom = self.env['mrp.bom'].create({
            'product_id': self.product_1.id,
            'product_tmpl_id': self.product_1.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'type': 'normal',
            'operation_ids': [
                (0, 0, {'name': 'Test', 'workcenter_id': workcenter_1.id, 'time_cycle': 60, 'sequence': 1}),
            ],
        })

        # mo_1
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_1
        mo_form.bom_id = bom
        mo_form.product_qty = 1
        mo = mo_form.save()
        mo.action_confirm()
        mo.button_plan()
        self.assertEqual(mo.workorder_ids[0].workcenter_id.id, workcenter_2.id)
        self.assertEqual(mo.workorder_ids[0].duration_expected, 65)

        # mo_2
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_1
        mo_form.bom_id = bom
        mo_form.product_qty = 1
        mo_2 = mo_form.save()
        mo_2.action_confirm()
        mo_2.button_plan()
        self.assertEqual(mo_2.workorder_ids[0].workcenter_id.id, workcenter_1.id)
        self.assertEqual(mo_2.workorder_ids[0].duration_expected, 70)

    def test_duration_expected_when_done(self):
        """
        Checks that the expected durations of workorders are updated depending on the produced quantity.
        """
        bom = self.bom_2
        bom.type = 'normal'
        bom.operation_ids.time_mode = 'manual'
        bom.operation_ids.time_cycle_manual = 60.0
        product = bom.product_id
        component_1, component_2 = bom.bom_line_ids.mapped('product_id')
        stock_location = self.env.ref('stock.stock_location_stock')
        self.env['stock.quant']._update_available_quantity(component_1, stock_location, 50.0)
        self.env['stock.quant']._update_available_quantity(component_2, stock_location, 50.0)
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product
        mo_form.bom_id = bom
        mo_form.product_qty = 10.0
        mo = mo_form.save()
        mo.action_confirm()
        self.assertRecordValues(mo.workorder_ids, [
            {'qty_produced': 0.0, 'qty_remaining': 10.0, 'duration_expected': 390.0, 'duration': 0.0}
        ])

        # Dont set any duration and validate the mo for 3 units
        mo_form = Form(mo)
        mo_form.qty_producing = 3.0
        mo = mo_form.save()
        action = mo.button_mark_done()
        backorder_form = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder_form.save().action_backorder()
        self.assertRecordValues(mo.workorder_ids, [
            {'qty_produced': 3.0, 'qty_remaining': 0.0, 'duration_expected': 165.0, 'duration': 165.0, 'state': 'done'}
        ])

        bo = self.env['mrp.production'].search([('product_id', '=', product.id)]) - mo
        self.assertRecordValues(bo, [{'product_id': product.id, 'product_uom_qty': 7.0}])
        self.assertRecordValues(bo.workorder_ids, [
            {'qty_produced': 0.0, 'qty_remaining': 7.0, 'duration_expected': 315.0, 'duration': 0.0}
        ])

        # check that the duration expected is correctly updated when the
        # qty_producing is updated both to partial and full qty_production
        bo_form = Form(bo)
        bo_form.qty_producing = 3.0
        bo = bo_form.save()
        self.assertEqual(bo.workorder_ids.duration_expected, 165.0)
        bo_form.qty_producing = 7.0
        bo = bo_form.save()
        self.assertEqual(bo.workorder_ids.duration_expected, 315.0)
        bo_form.qty_producing = 3.0
        bo = bo_form.save()
        self.assertEqual(bo.workorder_ids.duration_expected, 165.0)
        # Set a different expected duration and validate the bo for 3 units
        bo.workorder_ids.duration_expected = 120.0
        action = bo.button_mark_done()
        backorder_form = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder_form.save().action_backorder()
        self.assertRecordValues(bo.workorder_ids, [
            {'qty_produced': 3.0, 'qty_remaining': 0.0, 'duration_expected': 120.0, 'duration': 120.0, 'state': 'done'}
        ])

        bo_2 = self.env['mrp.production'].search([('product_id', '=', product.id)]) - mo - bo
        self.assertRecordValues(bo_2, [{'product_id': product.id, 'product_uom_qty': 4.0}])
        self.assertRecordValues(bo_2.workorder_ids, [
            {'qty_produced': 0.0, 'qty_remaining': 4.0, 'duration_expected': 165.0, 'duration': 0.0}
        ])

        # Set a different duration, finish the wo and validate the second bo
        bo_2.workorder_ids.button_start()
        bo_2.workorder_ids.button_finish()
        bo_2.workorder_ids.duration = 100
        self.assertRecordValues(bo_2.workorder_ids, [
            {'qty_produced': 4.0, 'qty_remaining': 0.0, 'duration_expected': 165.0, 'duration': 100.0, 'state': 'done'}
        ])
        bo_2.button_mark_done()
        self.assertRecordValues(bo_2, [{'qty_produced': 4.0, 'state': 'done'}])

    def test_update_workcenter_adapt_finish_date(self):
        """
        Test that changing the workcenter of a workorder will adapt the end date to make
        sure the duration expected is respected
        """
        self.workcenter_4 = self.env['mrp.workcenter'].create({
            'name': 'Test workcenter',
        })

        self.workcenter_5 = self.env['mrp.workcenter'].create({
            'name': 'Test workcenter',
        })

        operation = self.env['mrp.routing.workcenter'].create({
            'name': 'Test order',
            'workcenter_id': self.workcenter_4.id,
            'bom_id': self.bom_1.id,
            'time_cycle_manual': 30,
        })

        mo = self.env['mrp.production'].create({
            'product_id': self.product.id,
            'product_uom_id': self.bom_1.product_uom_id.id,
        })

        dt = datetime(2024, 1, 17, 8)
        wo = self.env['mrp.workorder'].create([
            {
                'name': 'Test order',
                'workcenter_id': self.workcenter_4.id,
                'product_uom_id': self.bom_1.product_uom_id.id,
                'production_id': mo.id,
                'duration_expected': 30.0,
                'date_start': dt,
                'operation_id': operation.id,
            }
        ])
        self.assertEqual(wo.date_start, dt)
        self.assertEqual(wo.date_finished, dt + timedelta(hours=0, minutes=30))

        # We change the date finished and make sure the duration expected is adapted
        wo.write({
            'date_finished': dt + timedelta(hours=1),
        })
        self.assertEqual(wo.duration_expected, 60.0)

        # We change the workcenter and make sure the duration expected and the date finish
        # is adapted accordingly
        wo.write({
            'workcenter_id': self.workcenter_5.id,
        })
        self.assertEqual(wo.duration_expected, 30.0)
        self.assertEqual(wo.date_start, dt)
        self.assertEqual(wo.date_finished, dt + timedelta(hours=0, minutes=30))

    def test_update_qty_producing_done_MO_with_lot(self):
        """
        Test that increasing the qty producing of a done MO for a product tracked by lot
        will create an additional sml for the final product with the same producing lot
        """
        tracked_product = self.env['product.template'].create({
            'name': 'Super Product',
            'tracking': 'lot',
            'is_storable': True,
            'bom_ids': [Command.create({
                'product_qty': 2.0,
                'bom_line_ids': [Command.create({'product_id': self.product_1.id, 'product_qty': 2.0})],
            })],
        })
        mo = self.env['mrp.production'].create({
            'product_id': tracked_product.product_variant_ids.id,
            'product_uom_qty': 2.0,
        })
        mo.action_confirm()
        mo.action_generate_serial()
        producing_lot = mo.lot_producing_id
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')
        self.assertEqual(mo.move_finished_ids.lot_ids, producing_lot)
        self.assertEqual(mo.move_finished_ids.move_line_ids.mapped('lot_id'), producing_lot)
        mo.qty_producing = 3.0
        self.assertTrue(all(sml.lot_id == producing_lot for sml in mo.move_finished_ids.move_line_ids))
        self.assertEqual(sum(sml.quantity for sml in mo.move_finished_ids.move_line_ids), 3.0)

    def test_mrp_link_new_operations(self):
        """
        Checks that newly created operations are linked with the correct dependencies.
            - Create and confirm an MO with 2 operations: op1 > op2
            - Start op2 and create a new operation op3
            > The new dependency should be op1 > op2 > op3
        """
        mo = self.env['mrp.production'].create({
            'product_id': self.product_1.id,
            'product_qty': 1.0,
        })
        with Form(mo) as mo_form:
            with mo_form.workorder_ids.new() as line_op_1:
                line_op_1.name = "op1"
                line_op_1.workcenter_id = self.workcenter_1
            with mo_form.workorder_ids.new() as line_op_2:
                line_op_2.name = "op2"
                line_op_2.workcenter_id = self.workcenter_1
        op_1, op_2 = mo.workorder_ids
        mo.action_confirm()
        self.assertFalse(op_1.blocked_by_workorder_ids)
        self.assertEqual(op_2.blocked_by_workorder_ids, op_1)
        op_2.button_start()
        with Form(mo) as mo_form:
            with mo_form.workorder_ids.new() as line_op_3:
                line_op_3.name = "op3"
                line_op_3.workcenter_id = self.workcenter_1
        op_3 = mo.workorder_ids - (op_1 | op_2)
        self.assertFalse(op_1.blocked_by_workorder_ids)
        self.assertEqual(op_2.blocked_by_workorder_ids, op_1)
        self.assertEqual(op_3.blocked_by_workorder_ids, op_2)

    def _prepare_report_values(self, qty_final=5, qty_base_1=4, qty_base_2=1, mto=False, bom_2=False, extra_component=False, extra_operation=False):
        grp_multi_step_rule = self.env.ref('stock.group_adv_location')
        self.env.user.write({'groups_id': [(3, grp_multi_step_rule.id)]})
        manufacture_route = self.env.ref('mrp.route_warehouse0_manufacture')
        routes = [Command.link(manufacture_route.id)]
        if mto:
            mto_route = self.env.ref('stock.route_warehouse0_mto')
            mto_route.active = True
            routes.append(Command.link(mto_route.id))
        product_to_build = self.env['product.product'].create({
            'name': 'Young Tom',
            'type': 'consu',
            'is_storable': True,
            'standard_price': 10.0,
            'route_ids': routes
        })
        product_to_use_1 = self.env['product.product'].create({
            'name': 'Botox',
            'type': 'consu',
            'is_storable': True,
            'standard_price': 15.0,
            'route_ids': routes
        })
        product_to_use_2 = self.env['product.product'].create({
            'name': 'Old Tom',
            'type': 'consu',
            'is_storable': True,
            'standard_price': 20.0,
        })
        workcenter_1 = self.env['mrp.workcenter'].create({
            'name': 'wc1',
            'default_capacity': 1,
            'time_efficiency': 100,
            'costs_hour': 10,
        })
        bom_1 = self.env['mrp.bom'].create({
            'product_id': product_to_build.id,
            'product_tmpl_id': product_to_build.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': product_to_use_2.id, 'product_qty': qty_base_2}),
            ],
            'operation_ids': [
                (0, 0, {'name': 'Test', 'workcenter_id': workcenter_1.id, 'time_cycle': 60, 'sequence': 1}),
            ]})
        if bom_2:
            self.env['mrp.bom'].create({
                'product_id': product_to_use_2.id,
                'product_tmpl_id': product_to_use_2.product_tmpl_id.id,
                'product_uom_id': self.uom_unit.id,
                'product_qty': 1.0,
                'type': 'normal',
                'bom_line_ids': [
                    (0, 0, {'product_id': product_to_use_1.id, 'product_qty': 1}),
                ],
                'operation_ids': [
                    (0, 0, {'name': 'Component assembly', 'workcenter_id': workcenter_1.id, 'time_cycle': 60, 'sequence': 1}),
                ]})
        if mto:
            replenish_wizard = self.env['product.replenish'].with_context(default_product_tmpl_id=product_to_use_2.product_tmpl_id.id).create({
                'product_id': product_to_use_2.id,
                'product_tmpl_id': product_to_use_2.product_tmpl_id.id,
                'quantity': 1,
                'route_id': manufacture_route.id,
            })
            replenish_wizard.launch_replenishment()
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product_to_build
        mo_form.bom_id = bom_1
        mo_form.product_qty = qty_final
        if extra_component:
            with mo_form.move_raw_ids.new() as line:
                line.product_id = product_to_use_1
                line.product_uom_qty = 5
        if extra_operation:
            with mo_form.workorder_ids.new() as line:
                line.name = "drilling"
                line.workcenter_id = workcenter_1
                line.duration_expected = 60
        mo = mo_form.save()
        return mo

    def _verify_report_main_decorators(self, mo, sum_real_cost=False, sum_mo_cost=False, comp_real_cost=False,
                                       comp_mo_cost=False, op_real_cost=False, op_mo_cost=False, extra_component=False, add_comp_real_cost=False):
        data = self.env['report.mrp.report_mo_overview'].get_report_values(mo.id)
        summary = data['data']['summary']
        components = data['data']['components']
        operations = data['data']['operations']
        self.assertEqual(summary['mo_cost_decorator'], sum_mo_cost)
        self.assertEqual(summary['real_cost_decorator'], sum_real_cost)
        component = components[0]
        self.assertEqual(component['summary']['mo_cost_decorator'], comp_mo_cost)
        self.assertEqual(component['summary']['real_cost_decorator'], comp_real_cost)
        if extra_component:
            component = components[1]
            self.assertEqual(component['summary']['mo_cost_decorator'], add_comp_real_cost)
            self.assertEqual(component['summary']['real_cost_decorator'], comp_real_cost)
        self.assertEqual(operations['summary']['mo_cost_decorator'], op_mo_cost)
        self.assertEqual(operations['summary']['real_cost_decorator'], op_real_cost)

    def test_mo_overview_base_decorators(self):
        # Base test for decorators colors of the report
        # Here no colors are expected except when the mo is started. The components are not consumed yet so a few colors are expected.
        mo = self._prepare_report_values()
        self._verify_report_main_decorators(mo)
        mo.action_confirm()
        self._verify_report_main_decorators(mo)
        mo.action_start()
        self._verify_report_main_decorators(mo, sum_mo_cost='danger', comp_mo_cost='danger', op_real_cost='success')
        mo.button_mark_done()
        self._verify_report_main_decorators(mo)

    def test_mo_overview_component_bom(self):
        # Test for decorators colors of the report with a component having a bom (without MTO)
        # No changes expected with the base scenario
        # Here no colors are expected except when the mo is started. The components are not consumed yet so a few colors are expected.
        mo = self._prepare_report_values(bom_2=True)
        self._verify_report_main_decorators(mo)
        mo.action_confirm()
        self._verify_report_main_decorators(mo)
        mo.action_start()
        self._verify_report_main_decorators(mo, sum_mo_cost='danger', comp_mo_cost='danger', op_real_cost='success')
        mo.button_mark_done()
        self._verify_report_main_decorators(mo)

    def test_mo_overview_component_bom_mto(self):
        # Test for decorators colors of the report with a component having a bom (with MTO)
        # Colors are expected when the MO is confirmed as the BoM does not take the component MO cost into account
        mo = self._prepare_report_values(mto=True, bom_2=True)
        self._verify_report_main_decorators(mo)
        mo.action_confirm()
        self._verify_report_main_decorators(mo, sum_mo_cost='danger', comp_mo_cost='danger')
        mo.action_start()
        self._verify_report_main_decorators(mo, sum_mo_cost='danger', comp_mo_cost='danger', op_real_cost='success')
        mo.button_mark_done()
        self._verify_report_main_decorators(mo)

    def test_mo_overview_added_component(self):
        # Test for decorators colors of the report with an added component (not on the BoM)
        # Colors should be mostly red as the component add an extra cost to the MO
        mo = self._prepare_report_values(extra_component=True)
        self._verify_report_main_decorators(mo, sum_mo_cost='danger', extra_component=True, add_comp_real_cost='danger')
        mo.action_confirm()
        self._verify_report_main_decorators(mo, sum_mo_cost='danger', extra_component=True, add_comp_real_cost='danger')
        mo.action_start()
        self._verify_report_main_decorators(mo, sum_mo_cost='danger', comp_mo_cost='danger', op_real_cost='success', extra_component=True, add_comp_real_cost='danger')
        mo.button_mark_done()
        self._verify_report_main_decorators(mo, op_real_cost='success', sum_real_cost='success', extra_component=True)

    def test_mo_overview_added_operation(self):
        # Test for decorators colors of the report with an added operation (not on the BoM)
        # Colors should be mostly red as soon as time has been timesheeted
        mo = self._prepare_report_values(extra_operation=True)
        self._verify_report_main_decorators(mo, sum_mo_cost='danger', op_mo_cost='danger')
        mo.action_confirm()
        self._verify_report_main_decorators(mo, sum_mo_cost='danger', op_mo_cost='danger')
        mo.action_start()
        self._verify_report_main_decorators(mo, sum_mo_cost='danger', comp_mo_cost='danger', op_real_cost='success')
        mo.workorder_ids[0].duration = 500
        self._verify_report_main_decorators(mo, sum_mo_cost='danger', comp_mo_cost='danger', op_real_cost='danger')
        mo.button_mark_done()
        self._verify_report_main_decorators(mo, op_real_cost='danger', sum_real_cost='danger')

    def test_update_mo_from_bom_with_kit(self):
        """
        Test that an MO can be updated from BoM when the finished product has a kit as a component.
        """
        # Test that the finished product has a kit as a component
        kit_bom_line = self.bom_3.bom_line_ids.filtered(lambda line: line.product_id.is_kits)
        self.assertEqual(len(kit_bom_line), 1)
        kit_bom = kit_bom_line.product_id.bom_ids
        self.assertEqual(len(kit_bom.bom_line_ids), 2)
        # Check that other components are present in the BoM
        self.assertEqual(len(self.bom_3.bom_line_ids), 3)
        # Create a MO
        mo = self.env['mrp.production'].create({
            'bom_id': self.bom_3.id,
        })
        mo.action_confirm()
        self.assertEqual(mo.state, 'confirmed')
        self.assertEqual(len(mo.move_raw_ids), 4)
        # keep only the kit as component
        (self.bom_3.bom_line_ids - kit_bom_line).unlink()
        self.assertEqual(self.bom_3.bom_line_ids, kit_bom_line)
        mo.action_update_bom()
        self.assertRecordValues(mo.move_raw_ids, [
            {'product_id': kit_bom.bom_line_ids[0].product_id.id, 'product_uom_qty': 2, 'product_uom': kit_bom.bom_line_ids[0].product_id.uom_id.id},
            {'product_id': kit_bom.bom_line_ids[1].product_id.id, 'product_uom_qty': 3, 'product_uom': kit_bom.bom_line_ids[1].product_id.uom_id.id},
        ])


@tagged('-at_install', 'post_install')
class TestTourMrpOrder(HttpCase):
    def test_mrp_order_product_catalog(self):
        product = self.env['product.product'].create({
            'name': 'test1',
            'is_storable': True,
        })
        mo = self.env['mrp.production'].create({
            'product_id': product.id,
            'product_uom_qty': 1.0,
        })

        self.assertEqual(len(mo.move_raw_ids), 0)
        url = f'/odoo/action-mrp.mrp_production_action/{mo.id}'

        self.start_tour(url, 'test_mrp_production_product_catalog', login='admin')
        self.assertEqual(len(mo.move_raw_ids), 1)

    def test_manufacturing_and_byproduct_sm_to_sml_synchronization(self):
        """ Test the synchronization between stock moves and stock move lines within
            the detailed operation modal for manufacturings and by-products.
        """

        self.env['res.config.settings'].create({'group_stock_multi_locations': True}).execute()
        self.env['res.config.settings'].create({'group_mrp_byproducts': True}).execute()

        location = self.env.ref('stock.stock_location_stock')
        product = self.env['product.product']
        product_finish = product.create({
            'name': 'product1',
            'is_storable': True,
            'tracking': 'none',
        })
        component = product.create({
            'name': 'product2',
            'is_storable': True,
            'tracking': 'none',
        })
        by_product = product.create({
            'name': 'product2',
            'is_storable': True,
            'tracking': 'none',
        })

        self.env['stock.quant']._update_available_quantity(component, location, 50)

        bom = self.env['mrp.bom'].create({
            'product_id': product_finish.id,
            'product_tmpl_id': product_finish.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': component.id, 'product_qty': 5}),
            ],
            'byproduct_ids': [
                (0, 0, {'product_id': by_product.id, 'product_qty': 2, 'product_uom_id': by_product.uom_id.id})
            ],
        })

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product_finish
        mo_form.product_qty = 1
        mo_form.bom_id = bom
        mo = mo_form.save()

        action_id = self.env.ref('mrp.menu_mrp_production_action').action
        url = f'/odoo/action-{action_id.id}/{mo.id}'
        self.start_tour(url, "test_manufacturing_and_byproduct_sm_to_sml_synchronization", login="admin", timeout=100)
        self.assertEqual(mo.move_raw_ids.quantity, 7)
        self.assertEqual(mo.move_raw_ids.move_line_ids.quantity, 7)
        self.assertEqual(mo.move_byproduct_ids.quantity, 7)
        self.assertEqual(len(mo.move_byproduct_ids.move_line_ids), 1)
