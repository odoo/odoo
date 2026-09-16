from datetime import datetime, timedelta

from freezegun import freeze_time

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import Form, users
from odoo.tests.common import HttpCase, tagged
from odoo.tools.misc import format_date

from odoo.addons.mrp.tests.common import TestMrpCommon


class TestMrpOrder(TestMrpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref("mrp.route_warehouse0_manufacture").write(
            {
                "product_selectable": True,
            }
        )
        cls.env.ref("base.group_user").write(
            {"implied_ids": [(4, cls.env.ref("stock.group_production_lot").id)]}
        )

    def test_access_rights_manager(self):
        man_order_form = Form(
            self.env["mrp.production"].with_user(self.user_mrp_manager)
        )
        man_order_form.product_id = self.product_4
        man_order_form.product_qty = 5.0
        man_order_form.bom_id = self.bom_1
        man_order_form.location_src_id = self.shelf_1
        man_order_form.location_dest_id = self.output_location
        man_order = man_order_form.save()
        man_order.action_confirm()
        man_order.action_cancel()
        self.assertEqual(
            man_order.state, "cancel", "Production order should be in cancel state."
        )
        man_order.unlink()

    def test_access_rights_user(self):
        man_order_form = Form(self.env["mrp.production"].with_user(self.user_mrp_user))
        man_order_form.product_id = self.product_4
        man_order_form.product_qty = 5.0
        man_order_form.bom_id = self.bom_1
        man_order_form.location_src_id = self.shelf_1
        man_order_form.location_dest_id = self.output_location
        man_order = man_order_form.save()
        man_order.action_confirm()
        man_order.action_cancel()
        self.assertEqual(
            man_order.state, "cancel", "Production order should be in cancel state."
        )
        man_order.unlink()

    def test_basic(self):
        self.product_1.is_storable = True
        self.product_2.is_storable = True
        self.env["stock.quant"].create(
            {
                "location_id": self.warehouse_1.lot_stock_id.id,
                "product_id": self.product_1.id,
                "inventory_quantity": 500,
            }
        ).action_apply_inventory()
        self.env["stock.quant"].create(
            {
                "location_id": self.warehouse_1.lot_stock_id.id,
                "product_id": self.product_2.id,
                "inventory_quantity": 500,
            }
        ).action_apply_inventory()

        date_start = fields.Datetime.now() - timedelta(days=1)
        test_quantity = 3.0
        man_order_form = Form(self.env["mrp.production"].with_user(self.user_mrp_user))
        man_order_form.product_id = self.product_4
        man_order_form.bom_id = self.bom_1
        man_order_form.product_uom_id = self.product_4.uom_id
        man_order_form.product_qty = test_quantity
        man_order_form.date_start = date_start
        man_order_form.location_src_id = self.shelf_1
        man_order_form.location_dest_id = self.output_location
        man_order = man_order_form.save()

        self.assertEqual(
            man_order.state, "draft", "Production order should be in draft state."
        )
        man_order.action_confirm()
        self.assertEqual(
            man_order.state,
            "confirmed",
            "Production order should be in confirmed state.",
        )

        production_move = man_order.move_finished_ids
        self.assertAlmostEqual(
            production_move.date,
            date_start + timedelta(hours=1),
            delta=timedelta(seconds=10),
        )
        self.assertEqual(production_move.product_id, self.product_4)
        self.assertEqual(production_move.product_uom_id, man_order.product_uom_id)
        self.assertEqual(production_move.product_qty, man_order.product_qty)
        self.assertEqual(
            production_move.location_id, self.product_4.property_stock_production
        )
        self.assertEqual(production_move.location_dest_id, man_order.location_dest_id)

        for move in man_order.move_raw_ids:
            self.assertEqual(move.date, date_start)
        first_move = man_order.move_raw_ids.filtered(
            lambda move: move.product_id == self.product_2
        )
        self.assertEqual(
            first_move.product_qty,
            test_quantity / self.bom_1.product_qty * self.product_4.uom_id.factor * 2,
        )
        first_move = man_order.move_raw_ids.filtered(
            lambda move: move.product_id == self.product_1
        )
        self.assertEqual(
            first_move.product_qty,
            test_quantity / self.bom_1.product_qty * self.product_4.uom_id.factor * 4,
        )

        mo_form = Form(man_order)
        mo_form.qty_producing = 2.0
        man_order = mo_form.save()

        action = man_order.button_mark_done()
        self.assertEqual(
            man_order.state,
            "progress",
            "Production order should be open a backorder wizard, then not done yet.",
        )

        quantity_issues = man_order._get_consumption_issues()
        action = man_order._prepare_action_consumption_wizard(quantity_issues)
        backorder = Form(
            self.env["mrp.production.backorder"].with_context(**action["context"])
        )
        backorder.save().action_close_mo()
        self.assertEqual(man_order.state, "done", "Production order should be done.")

        mo_copy = man_order.copy()
        self.assertEqual(
            mo_copy.state, "draft", "Copied production order should be draft."
        )
        self.assertEqual(
            len(mo_copy.move_raw_ids),
            2,
            "Incorrect number of component moves [i.e. all non-0 (even cancelled) moves should be copied].",
        )
        self.assertEqual(
            len(mo_copy.move_finished_ids),
            1,
            "Incorrect number of moves for products to produce [i.e. cancelled moves should not be copied",
        )
        self.assertEqual(
            mo_copy.move_finished_ids.product_uom_qty,
            3,
            "Incorrect qty of products to produce",
        )

        mo_copy.action_cancel()
        self.assertEqual(mo_copy.state, "cancel")
        mo_copy_2 = mo_copy.copy()
        self.assertEqual(
            mo_copy_2.state, "draft", "Copied production order should be draft."
        )
        self.assertEqual(
            len(mo_copy_2.move_raw_ids), 2, "Incorrect number of component moves."
        )
        self.assertEqual(
            len(mo_copy_2.move_finished_ids),
            1,
            "Incorrect number of moves for products to produce [i.e. copying a cancelled MO should copy its cancelled moves]",
        )
        self.assertEqual(
            mo_copy_2.move_finished_ids.product_uom_qty,
            3,
            "Incorrect qty of products to produce",
        )

    def test_production_availability(self):
        self.bom_3.bom_line_ids.filtered(
            lambda x: x.product_id == self.product_5
        ).unlink()
        self.bom_3.bom_line_ids.filtered(
            lambda x: x.product_id == self.product_4
        ).unlink()
        self.bom_3.ready_to_produce = "all_available"

        production_form = Form(self.env["mrp.production"])
        production_form.product_id = self.product_6
        production_form.bom_id = self.bom_3
        production_form.product_qty = 5.0
        production_form.product_uom_id = self.product_6.uom_id
        production_2 = production_form.save()

        production_2.action_confirm()
        production_2.action_assign()

        self.assertEqual(
            production_2.reservation_state,
            "confirmed",
            "Production order should be availability for waiting state",
        )

        self.env["stock.quant"].with_context(inventory_mode=True).create(
            {
                "product_id": self.product_2.id,
                "inventory_quantity": 2.0,
                "location_id": self.shelf_1.id,
            }
        ).action_apply_inventory()

        production_2.action_assign()
        self.assertEqual(
            production_2.reservation_state,
            "confirmed",
            "Production order should be availability for partially available state",
        )

        self.env["stock.quant"].with_context(inventory_mode=True).create(
            {
                "product_id": self.product_2.id,
                "inventory_quantity": 5.0,
                "location_id": self.shelf_1.id,
            }
        ).action_apply_inventory()

        production_2.action_assign()
        self.assertEqual(
            production_2.reservation_state,
            "assigned",
            "Production order should be availability for assigned state",
        )

    def test_workorder_sequence(self):
        mo_form = Form(self.env["mrp.production"])
        mo_form.bom_id = self.bom_3
        mo = mo_form.save()
        self.assertEqual(len(mo.workorder_ids), 3)
        self.assertListEqual(mo.workorder_ids.mapped("sequence"), [0, 1, 2])
        self.assertEqual(mo.workorder_ids[0].operation_id.bom_id.type, "phantom")
        with Form(mo) as mo_form_2:
            with mo_form_2.workorder_ids.new() as wo:
                wo.name = "Do important stuff"
                wo.workcenter_id = self.workcenter_2
        mo.action_confirm()
        self.assertEqual(mo.workorder_ids.mapped("sequence"), [0, 1, 2, 100])

    @freeze_time("2022-06-28 08:00")
    def test_end_date(self):
        mo, bom_id, _p_final, _p1, _p2 = self.generate_mo(
            qty_base_1=10, qty_final=1, qty_base_2=1
        )
        bom_id.produce_delay = 5
        mo.button_mark_done()
        self.assertEqual(mo.date_end.day, 28)

    def test_over_consumption(self):
        mo, _bom, _p_final, _p1, _p2 = self.generate_mo(
            qty_base_1=10, qty_final=1, qty_base_2=1
        )
        mo.action_assign()
        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo = mo_form.save()
        details_operation_form = Form(
            mo.move_raw_ids[0],
            view=self.env.ref("stock.view_stock_move_form_operations"),
        )
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.quantity = 2
        details_operation_form.save()
        details_operation_form = Form(
            mo.move_raw_ids[1],
            view=self.env.ref("stock.view_stock_move_form_operations"),
        )
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.quantity = 11
        details_operation_form.save()

        self.assertEqual(len(mo.move_raw_ids), 2)
        self.assertEqual(len(mo.move_raw_ids.mapped("move_line_ids")), 2)
        self.assertEqual(mo.move_raw_ids[0].move_line_ids.mapped("quantity"), [2])
        self.assertEqual(mo.move_raw_ids[1].move_line_ids.mapped("quantity"), [11])
        self.assertEqual(mo.move_raw_ids[0].quantity, 2)
        self.assertEqual(mo.move_raw_ids[1].quantity, 11)
        mo.button_mark_done()
        self.assertEqual(len(mo.move_raw_ids), 2)
        self.assertEqual(len(mo.move_raw_ids.mapped("move_line_ids")), 2)
        self.assertEqual(mo.move_raw_ids.mapped("quantity"), [2, 11])
        self.assertEqual(mo.move_raw_ids.mapped("move_line_ids.quantity"), [2, 11])

    def test_under_consumption(self):
        mo, _bom, _p_final, _p1, _p2 = self.generate_mo(
            qty_base_1=10, qty_final=1, qty_base_2=1
        )
        mo.action_assign()
        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo = mo_form.save()
        details_operation_form = Form(
            mo.move_raw_ids[0],
            view=self.env.ref("stock.view_stock_move_form_operations"),
        )
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.quantity = 0
        details_operation_form.save()
        details_operation_form = Form(
            mo.move_raw_ids[1],
            view=self.env.ref("stock.view_stock_move_form_operations"),
        )
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.quantity = 5
        details_operation_form.save()

        self.assertEqual(len(mo.move_raw_ids), 2)
        self.assertEqual(len(mo.move_raw_ids.mapped("move_line_ids")), 2)
        self.assertEqual(mo.move_raw_ids[0].move_line_ids.mapped("quantity"), [0])
        self.assertEqual(mo.move_raw_ids[1].move_line_ids.mapped("quantity"), [5])
        self.assertEqual(mo.move_raw_ids[0].quantity, 0)
        self.assertEqual(mo.move_raw_ids[1].quantity, 5)
        mo.button_mark_done()
        self.assertEqual(len(mo.move_raw_ids), 2)
        self.assertEqual(len(mo.move_raw_ids.mapped("move_line_ids")), 1)
        self.assertEqual(mo.move_raw_ids.mapped("quantity"), [0, 5])
        self.assertEqual(mo.move_raw_ids.mapped("product_uom_qty"), [1, 10])
        self.assertEqual(mo.move_raw_ids.mapped("state"), ["cancel", "done"])
        self.assertEqual(mo.move_raw_ids.mapped("move_line_ids.quantity"), [5])

    def test_update_quantity_1(self):
        mo, _bom, _p_final, p1, p2 = self.generate_mo(tracking_base_1="lot")
        self.assertEqual(len(mo), 1, "MO should have been created")

        lot_1 = self.env["stock.lot"].create(
            {
                "name": "lot1",
                "product_id": p1.id,
            }
        )
        lot_2 = self.env["stock.lot"].create(
            {
                "name": "lot2",
                "product_id": p1.id,
            }
        )

        self.env["stock.quant"]._update_available_quantity(
            p1, self.stock_location, 10, lot_id=lot_1
        )
        self.env["stock.quant"]._update_available_quantity(
            p1, self.stock_location, 10, lot_id=lot_2
        )

        self.env["stock.quant"]._update_available_quantity(p2, self.stock_location, 5)
        mo.action_assign()

        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo = mo_form.save()

        details_operation_form = Form(
            mo.move_raw_ids[1],
            view=self.env.ref("stock.view_stock_move_form_operations"),
        )
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.lot_id = lot_1
            ml.quantity = 21
        details_operation_form.save()
        mo.move_raw_ids[1].picked = True
        mo.move_raw_ids[1]._onchange_quantity()
        update_quantity_wizard = self.env["change.production.qty"].create(
            {
                "mo_id": mo.id,
                "product_qty": 4,
            }
        )
        update_quantity_wizard.change_prod_qty()

        self.assertEqual(
            mo.move_raw_ids.filtered(lambda m: m.product_id == p1).quantity,
            21,
            "Update the produce quantity should not impact already produced quantity.",
        )
        self.assertEqual(mo.move_finished_ids.product_uom_qty, 4)
        mo.button_mark_done()

    def test_update_quantity_2(self):
        mo, _bom, _p_final, p1, p2 = self.generate_mo(qty_final=3)
        self.assertEqual(len(mo), 1, "MO should have been created")

        self.env["stock.quant"]._update_available_quantity(p1, self.stock_location, 20)
        self.env["stock.quant"]._update_available_quantity(p2, self.stock_location, 5)
        mo.action_assign()

        mo_form = Form(mo)
        mo_form.qty_producing = 2
        mo = mo_form.save()

        action = mo.button_mark_done()
        backorder = Form(
            self.env["mrp.production.backorder"].with_context(**action["context"])
        )
        backorder.save().action_backorder()
        mo_backorder = mo.production_group_id.production_ids.sorted(
            "backorder_sequence"
        )[-1]
        self.assertEqual(mo_backorder.product_qty, 1)

        update_quantity_wizard = self.env["change.production.qty"].create(
            {
                "mo_id": mo_backorder.id,
                "product_qty": 3,
            }
        )
        update_quantity_wizard.change_prod_qty()
        mo_back_form = Form(mo_backorder)
        mo_back_form.qty_producing = 3
        mo_backorder = mo_back_form.save()
        mo_backorder.button_mark_done()

        productions = mo | mo_backorder
        self.assertEqual(
            sum(
                productions.move_raw_ids.filtered(lambda m: m.product_id == p1).mapped(
                    "quantity"
                )
            ),
            20,
        )
        self.assertEqual(sum(productions.move_finished_ids.mapped("quantity")), 5)

    def test_update_quantity_3(self):
        bom = self.env["mrp.bom"].create(
            {
                "product_id": self.product_6.id,
                "product_tmpl_id": self.product_6.product_tmpl_id.id,
                "product_qty": 1,
                "product_uom_id": self.product_6.uom_id.id,
                "type": "normal",
                "bom_line_ids": [
                    Command.create(
                        {"product_id": self.product_2.id, "product_qty": 2.03}
                    ),
                    Command.create(
                        {"product_id": self.product_8.id, "product_qty": 4.16}
                    ),
                ],
                "operation_ids": [
                    Command.create(
                        {
                            "name": "Gift Wrap Maching",
                            "workcenter_id": self.workcenter_1.id,
                            "time_cycle": 15,
                            "sequence": 1,
                        }
                    ),
                ],
            }
        )
        production_form = Form(self.env["mrp.production"])
        production_form.product_id = self.product_6
        production_form.bom_id = bom
        production_form.product_qty = 1
        production_form.product_uom_id = self.product_6.uom_id
        production = production_form.save()
        self.assertEqual(production.workorder_ids.duration_expected, 90)
        self.assertEqual(
            [production.date_end], production.move_finished_ids.mapped("date")
        )
        mo_form = Form(production)
        mo_form.product_qty = 3
        production = mo_form.save()
        self.assertEqual(production.workorder_ids.duration_expected, 165)

        production = self.env["mrp.production"].create(
            {
                "product_id": self.product_6.id,
                "bom_id": bom.id,
                "product_qty": 1,
                "product_uom_id": self.product_6.uom_id.id,
            }
        )
        self.assertEqual(production.workorder_ids.duration_expected, 90)
        production.product_qty = 3
        self.assertEqual(production.workorder_ids.duration_expected, 165)

    def test_update_quantity_4(self):
        self.env.user.group_ids += self.env.ref("mrp.group_mrp_routings")
        bom = self.env["mrp.bom"].create(
            {
                "product_id": self.product_6.id,
                "product_tmpl_id": self.product_6.product_tmpl_id.id,
                "product_qty": 1,
                "product_uom_id": self.product_6.uom_id.id,
                "type": "normal",
                "bom_line_ids": [
                    Command.create(
                        {"product_id": self.product_2.id, "product_qty": 2.03}
                    ),
                    Command.create(
                        {"product_id": self.product_8.id, "product_qty": 4.16}
                    ),
                ],
            }
        )
        production_form = Form(self.env["mrp.production"])
        production_form.product_id = self.product_6
        production_form.bom_id = bom
        production_form.product_qty = 1
        production_form.product_uom_id = self.product_6.uom_id
        production = production_form.save()
        production_form = Form(production)
        with production_form.workorder_ids.new() as wo:
            wo.name = "OP1"
            wo.workcenter_id = self.workcenter_1
            wo.duration_expected = 40
        production = production_form.save()
        self.assertEqual(production.workorder_ids.duration_expected, 40)
        mo_form = Form(production)
        mo_form.product_qty = 3
        production = mo_form.save()
        self.assertEqual(production.workorder_ids.duration_expected, 40)

        production.action_confirm()
        update_quantity_wizard = self.env["change.production.qty"].create(
            {
                "mo_id": production.id,
                "product_qty": 9,
            }
        )
        update_quantity_wizard.change_prod_qty()
        self.assertEqual(production.workorder_ids.duration_expected, 90)

        production = self.env["mrp.production"].create(
            {
                "product_id": self.product_6.id,
                "bom_id": bom.id,
                "product_qty": 1,
                "product_uom_id": self.product_6.uom_id.id,
                "workorder_ids": [
                    Command.create(
                        {
                            "name": "OP1",
                            "product_uom_id": self.product_6.uom_id.id,
                            "workcenter_id": self.workcenter_1.id,
                            "duration_expected": 40,
                        }
                    )
                ],
            }
        )
        self.assertEqual(production.workorder_ids.duration_expected, 40)
        production.product_qty = 3
        self.assertEqual(production.workorder_ids.duration_expected, 40)

        production.action_confirm()
        update_quantity_wizard = self.env["change.production.qty"].create(
            {
                "mo_id": production.id,
                "product_qty": 9,
            }
        )
        update_quantity_wizard.change_prod_qty()
        self.assertEqual(production.workorder_ids.duration_expected, 90)

    def test_qty_producing(self):
        self.env.user.group_ids += self.env.ref("mrp.group_mrp_routings")
        bom = self.env["mrp.bom"].create(
            {
                "product_id": self.product_6.id,
                "product_tmpl_id": self.product_6.product_tmpl_id.id,
                "product_qty": 1,
                "product_uom_id": self.product_6.uom_id.id,
                "type": "normal",
                "bom_line_ids": [
                    Command.create(
                        {"product_id": self.product_2.id, "product_qty": 2.00}
                    ),
                ],
            }
        )
        production_form = Form(self.env["mrp.production"])
        production_form.product_id = self.product_6
        production_form.bom_id = bom
        production_form.product_qty = 5
        production_form.product_uom_id = self.product_6.uom_id
        production = production_form.save()
        production_form = Form(production)
        with production_form.workorder_ids.new() as wo:
            wo.name = "OP1"
            wo.workcenter_id = self.workcenter_1
            wo.duration_expected = 40
        production = production_form.save()
        production.action_confirm()
        production.button_plan()

        wo = production.workorder_ids[0]
        wo.button_start()
        self.assertEqual(wo.qty_producing, 5, "Wrong quantity is suggested to produce.")

        wo.qty_producing = 4
        wo.button_pending()
        wo.button_start()
        self.assertEqual(
            wo.qty_producing,
            4,
            "Changing the qty_producing in the frontend is not persisted",
        )

    def test_recursive_work_orders(self):
        mo_no_company = self.env["mrp.production"].create(
            {
                "product_id": self.product.id,
                "product_uom_id": self.uom_unit.id,
            }
        )
        values = [
            {
                "name": f"Work order {n}",
                "workcenter_id": self.workcenter_1.id,
                "product_uom_id": self.uom_unit.id,
                "production_id": mo_no_company.id,
                "duration": 60,
            }
            for n in range(300)
        ]
        self.env["mrp.workorder"].create(values)
        mo_no_company.action_confirm()
        mo_no_company.button_plan()

    def test_update_quantity_5(self):
        bom = self.env["mrp.bom"].create(
            {
                "product_id": self.product_6.id,
                "product_tmpl_id": self.product_6.product_tmpl_id.id,
                "product_qty": 1,
                "product_uom_id": self.product_6.uom_id.id,
                "type": "normal",
                "bom_line_ids": [
                    Command.create({"product_id": self.product_2.id, "product_qty": 3}),
                ],
            }
        )
        production_form = Form(self.env["mrp.production"])
        production_form.product_id = self.product_6
        production_form.bom_id = bom
        production_form.product_qty = 1
        production_form.product_uom_id = self.product_6.uom_id
        production = production_form.save()
        production.action_confirm()
        production.action_assign()
        production.is_locked = False
        production_form = Form(production)
        production_form.qty_producing = 10
        with production_form.move_raw_ids.edit(0) as move:
            move.product_uom_qty = 2
        production = production_form.save()
        production.button_mark_done()

    def test_update_plan_date(self):
        date_start = datetime(2023, 5, 15, 9, 0)
        mo_form = Form(self.env["mrp.production"])
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
        bom_eff = self.env["mrp.bom"].create(
            {
                "product_id": self.product_6.id,
                "product_tmpl_id": self.product_6.product_tmpl_id.id,
                "product_qty": 1,
                "product_uom_id": self.product_6.uom_id.id,
                "type": "normal",
                "bom_line_ids": [
                    Command.create(
                        {"product_id": self.product_2.id, "product_qty": 2.03}
                    ),
                    Command.create(
                        {"product_id": self.product_8.id, "product_qty": 4.16}
                    ),
                ],
            }
        )
        self.env["decimal.precision"].search([("name", "=", "Product Unit")]).digits = 0
        production_form = Form(self.env["mrp.production"])
        production_form.product_id = self.product_6
        production_form.bom_id = bom_eff
        production_form.product_qty = 20
        production_form.product_uom_id = self.product_6.uom_id
        production = production_form.save()
        production.action_confirm()
        self.assertEqual(
            production.move_raw_ids[0].product_qty,
            41,
            "The quantity should be rounded up",
        )
        self.assertEqual(
            production.move_raw_ids[1].product_qty,
            84,
            "The quantity should be rounded up",
        )

        mo_form = Form(production)
        mo_form.qty_producing = 8
        production = mo_form.save()
        self.assertEqual(
            production.move_raw_ids[0].quantity,
            16,
            "Should use half-up rounding when producing",
        )
        self.assertEqual(
            production.move_raw_ids[1].quantity,
            34,
            "Should use half-up rounding when producing",
        )

    def test_product_produce_1(self):
        mo, _bom, _p_final, p1, p2 = self.generate_mo()
        self.assertEqual(len(mo), 1, "MO should have been created")

        self.env["stock.quant"]._update_available_quantity(p1, self.stock_location, 100)
        self.env["stock.quant"]._update_available_quantity(p2, self.stock_location, 5)

        mo.action_assign()

        details_operation_form = Form(
            mo.move_raw_ids[0],
            view=self.env.ref("stock.view_stock_move_form_operations"),
        )
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.quantity = 1
        details_operation_form.save()

        mo_form = Form(mo)
        mo_form.qty_producing = 3

        self.assertEqual(
            mo_form.move_raw_ids._records[0]["product_uom_qty"],
            5,
            "Wrong quantity to consume",
        )
        self.assertEqual(
            mo_form.move_raw_ids._records[0]["quantity"], 3, "Wrong quantity done"
        )
        self.assertEqual(
            mo_form.move_raw_ids._records[1]["product_uom_qty"],
            20,
            "Wrong quantity to consume",
        )
        self.assertEqual(
            mo_form.move_raw_ids._records[1]["quantity"], 12, "Wrong quantity done"
        )

    def test_product_produce_2(self):
        mo, _bom, _p_final, p1, p2 = self.generate_mo(
            tracking_base_1="serial", qty_base_1=1, qty_final=2
        )
        self.assertEqual(len(mo), 1, "MO should have been created")

        lot_p1_1 = self.env["stock.lot"].create(
            {
                "name": "lot1",
                "product_id": p1.id,
            }
        )
        lot_p1_2 = self.env["stock.lot"].create(
            {
                "name": "lot2",
                "product_id": p1.id,
            }
        )

        self.env["stock.quant"]._update_available_quantity(
            p1, self.stock_location, 1, lot_id=lot_p1_1
        )
        self.env["stock.quant"]._update_available_quantity(
            p1, self.stock_location, 1, lot_id=lot_p1_2
        )
        self.env["stock.quant"]._update_available_quantity(p2, self.stock_location, 5)

        mo.action_assign()

        self.assertEqual(
            len(mo.move_raw_ids.move_line_ids),
            3,
            "You should have 3 stock move lines. One for each serial to consume and for the untracked product.",
        )
        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo = mo_form.save()

        details_operation_form = Form(
            mo.move_raw_ids.filtered(lambda move: move.product_id == p1),
            view=self.env.ref("stock.view_stock_move_form_operations"),
        )
        self.assertEqual(len(details_operation_form.move_line_ids), 1)
        with details_operation_form.move_line_ids.edit(0) as ml:
            consumed_lots = ml.lot_id
            ml.quantity = 1
        details_operation_form.save()

        remaining_lot = (lot_p1_1 | lot_p1_2) - consumed_lots
        remaining_lot.check_singleton()
        action = mo.button_mark_done()
        backorder = Form(
            self.env["mrp.production.backorder"].with_context(**action["context"])
        )
        backorder.save().action_backorder()

        mo_backorder = mo.production_group_id.production_ids.sorted(
            "backorder_sequence"
        )[-1]

        mo_form = Form(mo_backorder)
        mo_form.qty_producing = 1
        mo_backorder = mo_form.save()
        details_operation_form = Form(
            mo_backorder.move_raw_ids.filtered(lambda move: move.product_id == p1),
            view=self.env.ref("stock.view_stock_move_form_operations"),
        )
        self.assertEqual(len(details_operation_form.move_line_ids), 1)
        with details_operation_form.move_line_ids.edit(0) as ml:
            self.assertEqual(ml.lot_id, remaining_lot)

    def test_product_produce_3(self):
        mo, _, p_final, p1, p2 = self.generate_mo(
            tracking_base_1="lot", qty_base_1=10, qty_final=1
        )

        p_final.tracking = "lot"

        self.assertEqual(len(mo), 1, "MO should have been created")

        first_lot_for_p1 = self.env["stock.lot"].create(
            {
                "name": "lot1",
                "product_id": p1.id,
            }
        )
        second_lot_for_p1 = self.env["stock.lot"].create(
            {
                "name": "lot2",
                "product_id": p1.id,
            }
        )

        final_product_lot = self.env["stock.lot"].create(
            {
                "name": "lot1",
                "product_id": p_final.id,
            }
        )

        self.env["stock.quant"]._update_available_quantity(
            p1, self.shelf_1, 3, lot_id=first_lot_for_p1
        )
        self.env["stock.quant"]._update_available_quantity(
            p1, self.shelf_2, 3, lot_id=first_lot_for_p1
        )
        self.env["stock.quant"]._update_available_quantity(
            p1, self.stock_location, 8, lot_id=second_lot_for_p1
        )
        self.env["stock.quant"]._update_available_quantity(p2, self.stock_location, 5)

        mo.action_assign()
        mo_form = Form(mo)
        mo_form.qty_producing = 1.0
        mo_form.lot_producing_ids.set(final_product_lot)
        mo = mo_form.save()
        details_operation_form = Form(
            mo.move_raw_ids[0],
            view=self.env.ref("stock.view_stock_move_form_operations"),
        )
        with details_operation_form.move_line_ids.new() as line:
            line.quantity = 1
        details_operation_form.save()

        details_operation_form = Form(
            mo.move_raw_ids[1],
            view=self.env.ref("stock.view_stock_move_form_operations"),
        )
        with details_operation_form.move_line_ids.new() as line:
            line.quantity = 2
            line.lot_id = first_lot_for_p1
        with details_operation_form.move_line_ids.new() as line:
            line.quantity = 1
            line.lot_id = second_lot_for_p1
        details_operation_form.save()

        move_1 = mo.move_raw_ids.filtered(lambda m: m.product_id == p1)
        ml_to_shelf_1 = move_1.move_line_ids.filtered(
            lambda ml: ml.lot_id == first_lot_for_p1 and ml.location_id == self.shelf_1
        )
        ml_to_shelf_2 = move_1.move_line_ids.filtered(
            lambda ml: ml.lot_id == first_lot_for_p1 and ml.location_id == self.shelf_2
        )

        self.assertEqual(
            sum(ml_to_shelf_1.mapped("quantity")),
            3.0,
            "3 units should be took from shelf1 as reserved.",
        )
        self.assertEqual(
            sum(ml_to_shelf_2.mapped("quantity")),
            3.0,
            "3 units should be took from shelf2 as reserved.",
        )
        self.assertEqual(move_1.quantity, 13, "You should have used the tem units.")

        mo.button_mark_done()
        self.assertEqual(mo.state, "done", "Production order should be in done state.")

    def test_product_produce_4(self):
        mo, _, _p_final, p1, p2 = self.generate_mo(qty_final=1, qty_base_1=5)

        self.env["stock.quant"]._update_available_quantity(p1, self.shelf_1, 2)
        self.env["stock.quant"]._update_available_quantity(p1, self.shelf_2, 3)
        self.env["stock.quant"]._update_available_quantity(p2, self.stock_location, 1)

        mo.action_assign()

        m_p1 = mo.move_raw_ids.filtered(lambda x: x.product_id == p1)
        ml_p1 = m_p1.move_line_ids
        ml_p2 = mo.move_raw_ids.filtered(lambda x: x.product_id == p2).move_line_ids

        self.assertEqual(len(ml_p1), 2)
        self.assertEqual(len(ml_p2), 1)

        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo = mo_form.save()

        self.assertEqual(
            sorted(ml_p1.mapped("quantity")),
            [2.0, 3.0],
            "Quantity should be 2.0 and 3.0",
        )
        self.assertEqual(m_p1.quantity, 5.0, "Total qty done should be 5.0")

        mo.button_mark_done()
        self.assertEqual(mo.state, "done", "Production order should be in done state.")

    def test_product_produce_6(self):
        mo, _bom, _p_final, p1, p2 = self.generate_mo()
        self.assertEqual(len(mo), 1, "MO should have been created")

        self.env["stock.quant"]._update_available_quantity(p1, self.stock_location, 20)

        self.env["stock.quant"]._update_available_quantity(p2, self.stock_location, 5)
        mo.action_assign()

        mo_form = Form(mo)
        mo_form.qty_producing = 3
        mo = mo_form.save()

        mo._post_inventory()
        self.assertEqual(len(mo.move_raw_ids), 4)

        mo.move_raw_ids.filtered(lambda m: m.state != "done")[0].quantity = 3

        update_quantity_wizard = self.env["change.production.qty"].create(
            {
                "mo_id": mo.id,
                "product_qty": 3,
            }
        )

        mo.move_raw_ids.filtered(lambda m: m.state != "done")[0].quantity = 0
        update_quantity_wizard.change_prod_qty()

        self.assertEqual(len(mo.move_raw_ids), 4)

        mo.move_raw_ids.picked = True
        mo.button_mark_done()
        self.assertTrue(
            all(s in ["done", "cancel"] for s in mo.move_raw_ids.mapped("state"))
        )

    def test_product_produce_7(self):
        mo, _, _, p1, p2 = self.generate_mo(qty_final=1)
        self.assertEqual(len(mo), 1, "MO should have been created")

        self.env["stock.quant"]._update_available_quantity(p1, self.stock_location, 20)
        self.env["stock.quant"]._update_available_quantity(p2, self.stock_location, 5)
        mo.action_assign()

        mo_form = Form(mo)
        mo_form.qty_producing = 2
        mo = mo_form.save()
        mo.button_mark_done()
        self.assertEqual(sum(mo.move_finished_ids.move_line_ids.mapped("quantity")), 2)
        self.assertTrue(mo.is_locked)

        mo.action_toggle_is_locked()
        self.assertFalse(mo.is_locked)
        mo_form = Form(mo)
        mo_form.qty_producing = 5
        mo = mo_form.save()
        self.assertAlmostEqual(
            sum(mo.move_finished_ids.move_line_ids.mapped("quantity")), 5
        )

        mo_form = Form(mo)
        mo_form.qty_producing = 4
        mo = mo_form.save()
        self.assertAlmostEqual(
            sum(mo.move_finished_ids.move_line_ids.mapped("quantity")), 4
        )

    def test_consumption_strict_1(self):
        mo, _bom, _p_final, p1, p2 = self.generate_mo(consumption="strict", qty_final=1)
        self.assertEqual(len(mo), 1, "MO should have been created")

        self.env["stock.quant"]._update_available_quantity(p1, self.stock_location, 100)
        self.env["stock.quant"]._update_available_quantity(p2, self.stock_location, 5)

        mo.action_assign()

        mo_form = Form(mo)

        mo_form.qty_producing = 1
        with mo_form.move_raw_ids.new() as line:
            line.product_id = p1
        mo = mo_form.save()
        details_operation_form = Form(
            mo.move_raw_ids[-1],
            view=self.env.ref("stock.view_stock_move_form_operations"),
        )
        with details_operation_form.move_line_ids.new() as ml:
            ml.quantity = 1
            ml.picked = True
        details_operation_form.save()
        mo.button_mark_done()
        self.assertEqual(mo.state, "to_close")
        consumption_issues = mo._get_consumption_issues()
        action = mo._prepare_action_consumption_wizard(consumption_issues)
        warning = Form(
            self.env["mrp.consumption.warning"].with_context(**action["context"])
        )
        warning = warning.save()

        self.assertEqual(len(warning.mrp_consumption_warning_line_ids), 1)
        self.assertEqual(
            warning.mrp_consumption_warning_line_ids[0].product_consumed_qty_uom, 5
        )
        self.assertEqual(
            warning.mrp_consumption_warning_line_ids[0].product_expected_qty_uom, 4
        )
        warning.action_confirm()
        self.assertEqual(mo.state, "done")

    def test_consumption_warning_1(self):
        mo, _bom, _p_final, p1, p2 = self.generate_mo(
            consumption="warning", qty_final=1
        )
        self.assertEqual(len(mo), 1, "MO should have been created")

        self.env["stock.quant"]._update_available_quantity(p1, self.stock_location, 100)
        self.env["stock.quant"]._update_available_quantity(p2, self.stock_location, 5)

        mo.action_assign()

        mo_form = Form(mo)

        mo_form.qty_producing = 1
        with mo_form.move_raw_ids.new() as line:
            line.product_id = p1
        mo = mo_form.save()
        details_operation_form = Form(
            mo.move_raw_ids[-1],
            view=self.env.ref("stock.view_stock_move_form_operations"),
        )
        with details_operation_form.move_line_ids.new() as ml:
            ml.quantity = 1
            ml.picked = True
        details_operation_form.save()

        mo.button_mark_done()
        self.assertEqual(mo.state, "to_close")

        consumption_issues = mo._get_consumption_issues()
        action = mo._prepare_action_consumption_wizard(consumption_issues)
        warning = Form(
            self.env["mrp.consumption.warning"].with_context(**action["context"])
        )
        warning = warning.save()

        self.assertEqual(len(warning.mrp_consumption_warning_line_ids), 1)
        self.assertEqual(
            warning.mrp_consumption_warning_line_ids[0].product_consumed_qty_uom, 5
        )
        self.assertEqual(
            warning.mrp_consumption_warning_line_ids[0].product_expected_qty_uom, 4
        )
        warning.action_confirm()
        self.assertEqual(mo.state, "done")

    def test_consumption_flexible_1(self):
        mo, _bom, _p_final, p1, p2 = self.generate_mo(
            consumption="flexible", qty_final=1
        )
        self.assertEqual(len(mo), 1, "MO should have been created")

        self.env["stock.quant"]._update_available_quantity(p1, self.stock_location, 100)
        self.env["stock.quant"]._update_available_quantity(p2, self.stock_location, 5)

        mo.action_assign()

        mo_form = Form(mo)

        mo_form.qty_producing = 1
        with mo_form.move_raw_ids.new() as line:
            line.product_id = p1
        mo = mo_form.save()
        details_operation_form = Form(
            mo.move_raw_ids[-1],
            view=self.env.ref("stock.view_stock_move_form_operations"),
        )
        with details_operation_form.move_line_ids.new() as ml:
            ml.quantity = 1
        details_operation_form.save()

        mo.button_mark_done()
        self.assertEqual(mo.state, "done")

    def test_consumption_flexible_2(self):
        mo, _bom, _p_final, p1, p2 = self.generate_mo(
            consumption="flexible", qty_final=1
        )
        self.assertEqual(len(mo), 1, "MO should have been created")

        self.env["stock.quant"]._update_available_quantity(p1, self.stock_location, 100)
        self.env["stock.quant"]._update_available_quantity(p2, self.stock_location, 5)
        add_product = self.env["product.product"].create(
            {
                "name": "additional",
                "is_storable": True,
            }
        )
        mo.action_assign()

        mo_form = Form(mo)

        mo_form.qty_producing = 1
        with mo_form.move_raw_ids.new() as line:
            line.product_id = p1
        with mo_form.move_raw_ids.new() as line:
            line.product_id = add_product
        mo = mo_form.save()
        details_operation_form = Form(
            mo.move_raw_ids[-1],
            view=self.env.ref("stock.view_stock_move_form_operations"),
        )
        with details_operation_form.move_line_ids.new() as ml:
            ml.quantity = 1
        details_operation_form.save()

        mo.button_mark_done()
        self.assertEqual(mo.state, "done")

    def test_product_produce_10(self):
        self.env.user.group_ids += self.env.ref("mrp.group_mrp_byproducts")
        self.byproduct1 = self.env["product.product"].create(
            {"name": "Byproduct 1", "is_storable": True, "tracking": "serial"}
        )
        self.serial_1 = self.env["stock.lot"].create(
            {
                "product_id": self.byproduct1.id,
                "name": "serial 1",
            }
        )
        self.serial_2 = self.env["stock.lot"].create(
            {
                "product_id": self.byproduct1.id,
                "name": "serial 2",
            }
        )

        self.byproduct2 = self.env["product.product"].create(
            {
                "name": "Byproduct 2",
                "is_storable": True,
                "tracking": "lot",
            }
        )
        self.lot_1 = self.env["stock.lot"].create(
            {
                "product_id": self.byproduct2.id,
                "name": "Lot 1",
            }
        )
        self.lot_2 = self.env["stock.lot"].create(
            {
                "product_id": self.byproduct2.id,
                "name": "Lot 2",
            }
        )

        self.byproduct3 = self.env["product.product"].create(
            {
                "name": "Byproduct 3",
                "is_storable": True,
                "tracking": "none",
            }
        )

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
                bp.product_uom_id = self.uom_dozen

        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = self.product_4
        mo_form.bom_id = self.bom_1
        mo_form.product_qty = 2
        mo = mo_form.save()

        mo.action_confirm()
        move_byproduct_1 = mo.move_finished_ids.filtered(
            lambda l: l.product_id == self.byproduct1
        )
        self.assertEqual(len(move_byproduct_1), 1)
        self.assertEqual(move_byproduct_1.product_uom_qty, 2.0)
        self.assertEqual(move_byproduct_1.quantity, 2)
        self.assertEqual(len(move_byproduct_1.move_line_ids), 2)

        move_byproduct_2 = mo.move_finished_ids.filtered(
            lambda l: l.product_id == self.byproduct2
        )
        self.assertEqual(len(move_byproduct_2), 1)
        self.assertEqual(move_byproduct_2.product_uom_qty, 4.0)
        self.assertEqual(move_byproduct_2.quantity, 4)
        self.assertEqual(len(move_byproduct_2.move_line_ids), 1)

        move_byproduct_3 = mo.move_finished_ids.filtered(
            lambda l: l.product_id == self.byproduct3
        )
        self.assertEqual(move_byproduct_3.product_uom_qty, 4.0)
        self.assertEqual(move_byproduct_3.quantity, 4)
        self.assertEqual(move_byproduct_3.product_uom_id, self.uom_dozen)
        self.assertEqual(len(move_byproduct_3.move_line_ids), 1)

        mo_form = Form(mo)
        mo_form.qty_producing = 1.0
        mo = mo_form.save()
        move_byproduct_1 = mo.move_finished_ids.filtered(
            lambda l: l.product_id == self.byproduct1
        )
        self.assertEqual(len(move_byproduct_1), 1)
        self.assertEqual(move_byproduct_1.product_uom_qty, 2.0)
        self.assertEqual(move_byproduct_1.quantity, 1)
        self.assertFalse(move_byproduct_1.picked)

        move_byproduct_2 = mo.move_finished_ids.filtered(
            lambda l: l.product_id == self.byproduct2
        )
        self.assertEqual(len(move_byproduct_2), 1)
        self.assertEqual(move_byproduct_2.product_uom_qty, 4.0)
        self.assertEqual(move_byproduct_2.quantity, 2)
        self.assertFalse(move_byproduct_2.picked)

        move_byproduct_3 = mo.move_finished_ids.filtered(
            lambda l: l.product_id == self.byproduct3
        )
        self.assertEqual(move_byproduct_3.product_uom_qty, 4.0)
        self.assertEqual(move_byproduct_3.quantity, 2.0)
        self.assertFalse(move_byproduct_3.picked)
        self.assertEqual(move_byproduct_3.product_uom_id, self.uom_dozen)

        details_operation_form = Form(
            move_byproduct_1, view=self.env.ref("stock.view_stock_move_form_operations")
        )
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.lot_id = self.serial_1
        details_operation_form.save()
        details_operation_form = Form(
            move_byproduct_2, view=self.env.ref("stock.view_stock_move_form_operations")
        )
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.lot_id = self.lot_1
        details_operation_form.save()
        action = mo.button_mark_done()
        backorder = Form(
            self.env["mrp.production.backorder"].with_context(**action["context"])
        )
        backorder.save().action_backorder()
        mo2 = mo.production_group_id.production_ids.sorted("backorder_sequence")[-1]

        mo_form = Form(mo2)
        mo_form.qty_producing = 1
        mo2 = mo_form.save()

        move_byproduct_1 = mo2.move_finished_ids.filtered(
            lambda l: l.product_id == self.byproduct1
        )
        self.assertEqual(len(move_byproduct_1), 1)
        self.assertEqual(move_byproduct_1.product_uom_qty, 1.0)
        self.assertEqual(move_byproduct_1.quantity, 1)
        self.assertFalse(move_byproduct_1.picked)

        move_byproduct_2 = mo2.move_finished_ids.filtered(
            lambda l: l.product_id == self.byproduct2
        )
        self.assertEqual(len(move_byproduct_2), 1)
        self.assertEqual(move_byproduct_2.product_uom_qty, 2.0)
        self.assertEqual(move_byproduct_2.quantity, 2)
        self.assertFalse(move_byproduct_2.picked)

        move_byproduct_3 = mo2.move_finished_ids.filtered(
            lambda l: l.product_id == self.byproduct3
        )
        self.assertEqual(move_byproduct_3.product_uom_qty, 2.0)
        self.assertEqual(move_byproduct_3.quantity, 2.0)
        self.assertFalse(move_byproduct_3.picked)
        self.assertEqual(move_byproduct_3.product_uom_id, self.uom_dozen)

        details_operation_form = Form(
            move_byproduct_1, view=self.env.ref("stock.view_stock_move_form_operations")
        )
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.lot_id = self.serial_2
            ml.quantity = 1
        details_operation_form.save()
        details_operation_form = Form(
            move_byproduct_2, view=self.env.ref("stock.view_stock_move_form_operations")
        )
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.lot_id = self.lot_2
        details_operation_form.save()
        details_operation_form = Form(
            move_byproduct_3, view=self.env.ref("stock.view_stock_move_form_operations")
        )
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.quantity = 3
        details_operation_form.save()

        mo2.button_mark_done()
        move_lines_byproduct_1 = (
            (mo | mo2)
            .move_finished_ids.filtered(lambda l: l.product_id == self.byproduct1)
            .mapped("move_line_ids")
        )
        move_lines_byproduct_2 = (
            (mo | mo2)
            .move_finished_ids.filtered(lambda l: l.product_id == self.byproduct2)
            .mapped("move_line_ids")
        )
        move_lines_byproduct_3 = (
            (mo | mo2)
            .move_finished_ids.filtered(lambda l: l.product_id == self.byproduct3)
            .mapped("move_line_ids")
        )
        self.assertEqual(
            move_lines_byproduct_1.filtered(
                lambda ml: ml.lot_id == self.serial_1
            ).quantity,
            1.0,
        )
        self.assertEqual(
            move_lines_byproduct_1.filtered(
                lambda ml: ml.lot_id == self.serial_2
            ).quantity,
            1.0,
        )
        self.assertEqual(
            move_lines_byproduct_2.filtered(
                lambda ml: ml.lot_id == self.lot_1
            ).quantity,
            2.0,
        )
        self.assertEqual(
            move_lines_byproduct_2.filtered(
                lambda ml: ml.lot_id == self.lot_2
            ).quantity,
            2.0,
        )
        self.assertEqual(sum(move_lines_byproduct_3.mapped("quantity")), 5.0)
        self.assertEqual(
            move_lines_byproduct_3.mapped("product_uom_id"), self.uom_dozen
        )

    def test_product_produce_11(self):
        mo, _bom, _p_final, p1, p2 = self.generate_mo(qty_final=1)
        self.assertEqual(len(mo), 1, "MO should have been created")

        self.env["stock.quant"]._update_available_quantity(p1, self.stock_location, 4)
        self.env["stock.quant"]._update_available_quantity(p2, self.stock_location, 1)

        mo.bom_id.consumption = "flexible"
        mo.action_assign()
        mo.is_locked = False

        mo_form = Form(mo)
        mo_form.qty_producing = 3
        self.assertEqual(
            sum(x["quantity"] for x in mo_form.move_raw_ids._records),
            15,
            "Update the produce quantity should change the components quantity.",
        )
        mo = mo_form.save()
        mo_form = Form(mo)
        mo_form.qty_producing = 4
        self.assertEqual(
            sum(x["quantity"] for x in mo_form.move_raw_ids._records),
            20,
            "Update the produce quantity should change the components quantity.",
        )
        mo = mo_form.save()
        mo_form = Form(mo)
        mo_form.qty_producing = 1
        self.assertEqual(
            sum(x["quantity"] for x in mo_form.move_raw_ids._records),
            5,
            "Update the produce quantity should change the components quantity.",
        )
        mo = mo_form.save()
        with mo_form.move_raw_ids.new() as move:
            move.product_id = self.product_4
        mo = mo_form.save()
        details_operation_form = Form(
            mo.move_raw_ids[-1],
            view=self.env.ref("stock.view_stock_move_form_operations"),
        )
        with details_operation_form.move_line_ids.new() as ml:
            ml.quantity = 10
        details_operation_form.save()
        mo_form = Form(mo)
        mo_form.qty_producing = 2
        for move in mo_form.move_raw_ids._records:
            if move["product_id"] == self.product_4.id:
                self.assertEqual(move["quantity"], 10)
                break
        mo = mo_form.save()
        mo.button_mark_done()

    def test_byproduct_update_produced(self):
        self.env.user.group_ids += self.env.ref("mrp.group_mrp_byproducts")
        byproduct1, byproduct2 = self.env["product.product"].create(
            [
                {
                    "name": f"byproduct{i}",
                    "is_storable": True,
                    "tracking": "none",
                }
                for i in [1, 2]
            ]
        )

        self.bom_1.product_qty = 1
        self.bom_1.byproduct_ids = [
            Command.create(
                {
                    "product_id": byproduct1.id,
                    "product_qty": 1.0,
                }
            ),
            Command.create(
                {
                    "product_id": byproduct2.id,
                    "product_qty": 1.0,
                }
            ),
        ]

        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = self.product_4
        mo_form.bom_id = self.bom_1
        mo_form.product_qty = 2
        mo = mo_form.save()
        mo.action_confirm()
        self.assertRecordValues(
            mo.move_byproduct_ids,
            [
                {"product_id": byproduct1.id, "quantity": 2, "picked": False},
                {"product_id": byproduct2.id, "quantity": 2, "picked": False},
            ],
        )

        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo = mo_form.save()
        self.assertRecordValues(
            mo.move_byproduct_ids,
            [
                {"product_id": byproduct1.id, "quantity": 1, "picked": False},
                {"product_id": byproduct2.id, "quantity": 1, "picked": False},
            ],
        )

        move_byproduct_1 = mo.move_finished_ids.filtered(
            lambda l: l.product_id == byproduct1
        )
        move_byproduct_1.picked = True
        mo_form = Form(mo)
        mo_form.qty_producing = 2
        mo = mo_form.save()
        self.assertRecordValues(
            mo.move_byproduct_ids,
            [
                {"product_id": byproduct1.id, "quantity": 1, "picked": True},
                {"product_id": byproduct2.id, "quantity": 2, "picked": False},
            ],
        )

    def test_product_produce_duplicate_1(self):
        mo1, bom, p_final, _p1, _p2 = self.generate_mo(
            tracking_final="serial",
            qty_final=1,
            qty_base_1=1,
        )

        mo1.action_generate_serial()
        sn = mo1.lot_producing_ids
        mo1.button_mark_done()

        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = p_final
        mo_form.bom_id = bom
        mo_form.product_qty = 1
        mo2 = mo_form.save()
        mo2.action_confirm()

        mo_form = Form(mo2)
        with self.assertLogs(level="WARNING"):
            mo_form.lot_producing_ids.set(sn)
        mo2 = mo_form.save()
        with self.assertRaises(UserError):
            mo2.button_mark_done()

    def test_product_produce_duplicate_2(self):
        mo1, bom, p_final, _p1, p2 = self.generate_mo(
            tracking_base_2="serial",
            qty_final=1,
            qty_base_1=1,
        )
        sn = self.env["stock.lot"].create(
            {
                "name": "sn used twice",
                "product_id": p2.id,
            }
        )
        mo_form = Form(mo1)
        mo_form.qty_producing = 1
        mo1 = mo_form.save()
        details_operation_form = Form(
            mo1.move_raw_ids[0],
            view=self.env.ref("stock.view_stock_move_form_operations"),
        )
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.lot_id = sn
        details_operation_form.save()
        mo1.move_raw_ids.picked = True
        mo1.button_mark_done()

        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = p_final
        mo_form.bom_id = bom
        mo_form.product_qty = 1
        mo2 = mo_form.save()
        mo2.action_confirm()

        mo_form = Form(mo2)
        mo_form.qty_producing = 1
        mo2 = mo_form.save()
        details_operation_form = Form(
            mo2.move_raw_ids[0],
            view=self.env.ref("stock.view_stock_move_form_operations"),
        )
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.lot_id = sn
        details_operation_form.save()
        mo2.move_raw_ids.picked = True
        with self.assertRaises(UserError):
            mo2.button_mark_done()

    def test_product_produce_duplicate_3(self):
        finished_product = self.env["product.product"].create(
            {"name": "finished product"}
        )
        byproduct = self.env["product.product"].create(
            {"name": "byproduct", "is_storable": True, "tracking": "serial"}
        )
        component = self.env["product.product"].create({"name": "component"})
        bom = self.env["mrp.bom"].create(
            {
                "product_id": finished_product.id,
                "product_tmpl_id": finished_product.product_tmpl_id.id,
                "product_uom_id": finished_product.uom_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    Command.create({"product_id": component.id, "product_qty": 1}),
                ],
                "byproduct_ids": [
                    Command.create(
                        {
                            "product_id": byproduct.id,
                            "product_qty": 1,
                            "product_uom_id": byproduct.uom_id.id,
                        }
                    ),
                ],
            }
        )
        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = finished_product
        mo_form.bom_id = bom
        mo_form.product_qty = 1
        mo = mo_form.save()
        mo.action_confirm()

        sn = self.env["stock.lot"].create(
            {
                "name": "sn used twice",
                "product_id": byproduct.id,
            }
        )

        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo = mo_form.save()
        move_byproduct = mo.move_finished_ids.filtered(
            lambda m: m.product_id != mo.product_id
        )
        details_operation_form = Form(
            move_byproduct, view=self.env.ref("stock.view_stock_move_form_operations")
        )
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.lot_id = sn
        details_operation_form.save()
        mo.button_mark_done()

        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = finished_product
        mo_form.bom_id = bom
        mo_form.product_qty = 1
        mo2 = mo_form.save()
        mo2.action_confirm()

        mo_form = Form(mo2)
        mo_form.qty_producing = 1
        mo2 = mo_form.save()
        move_byproduct = mo2.move_finished_ids.filtered(
            lambda m: m.product_id != mo.product_id
        )
        details_operation_form = Form(
            move_byproduct, view=self.env.ref("stock.view_stock_move_form_operations")
        )
        with details_operation_form.move_line_ids.new() as ml:
            ml.lot_id = sn
        details_operation_form.save()
        with self.assertRaises(UserError):
            mo2.button_mark_done()

    def test_product_produce_duplicate_4(self):
        mo1, bom, p_final, _p1, p2 = self.generate_mo(
            tracking_base_2="serial",
            qty_final=1,
            qty_base_1=1,
        )
        sn = self.env["stock.lot"].create(
            {
                "name": "sn used twice",
                "product_id": p2.id,
            }
        )
        mo_form = Form(mo1)
        mo_form.qty_producing = 1
        mo1 = mo_form.save()
        details_operation_form = Form(
            mo1.move_raw_ids[0],
            view=self.env.ref("stock.view_stock_move_form_operations"),
        )
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.lot_id = sn
        details_operation_form.save()
        mo1.move_raw_ids.picked = True
        mo1.button_mark_done()

        unbuild_form = Form(self.env["mrp.unbuild"])
        unbuild_form.product_id = p_final
        unbuild_form.bom_id = bom
        unbuild_form.product_qty = 1
        unbuild_form.mo_id = mo1
        unbuild_order = unbuild_form.save()
        unbuild_order.action_unbuild()

        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = p_final
        mo_form.bom_id = bom
        mo_form.product_qty = 1
        mo2 = mo_form.save()
        mo2.action_confirm()

        mo_form = Form(mo2)
        mo_form.qty_producing = 1
        mo2 = mo_form.save()
        details_operation_form = Form(
            mo2.move_raw_ids[0],
            view=self.env.ref("stock.view_stock_move_form_operations"),
        )
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.lot_id = sn
        details_operation_form.save()
        mo2.move_raw_ids.picked = True
        mo2.button_mark_done()

    def test_product_produce_duplicate_5(self):
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
        subassembly_mo1.lot_producing_ids = subassembly_sn
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
                    Command.create(
                        {"product_id": subassembly_product.id, "product_qty": 1}
                    ),
                ],
            }
        )
        finished_good_mo_form = Form(self.env["mrp.production"])
        finished_good_mo_form.product_id = finished_good_product
        finished_good_mo_form.bom_id = finished_good_product_bom
        finished_good_mo = finished_good_mo_form.save()
        finished_good_mo.action_confirm()
        finished_good_mo.qty_producing = 1
        finished_good_mo.action_generate_serial()
        finished_good_detailed_operations_form = Form(
            finished_good_mo.move_raw_ids[0],
            view=self.env.ref("stock.view_stock_move_form_operations"),
        )
        with finished_good_detailed_operations_form.move_line_ids.edit(0) as ml:
            ml.quantity = 1
            ml.lot_id = subassembly_sn
        finished_good_detailed_operations_form.save()
        finished_good_mo.move_raw_ids.picked = True
        finished_good_mo.button_mark_done()

        finished_good_ub_form = Form(self.env["mrp.unbuild"])
        finished_good_ub_form.mo_id = finished_good_mo
        finished_good_ub_form.lot_id = finished_good_mo.lot_producing_ids[:1]
        finished_good_ub = finished_good_ub_form.save()
        finished_good_ub.action_unbuild()

        subassembly_ub_form = Form(self.env["mrp.unbuild"])
        subassembly_ub_form.mo_id = subassembly_mo1
        subassembly_ub_form.lot_id = subassembly_mo1.lot_producing_ids[:1]
        subassembly_ub = subassembly_ub_form.save()
        subassembly_ub.action_unbuild()

        subassembly_mo2_form = Form(self.env["mrp.production"])
        subassembly_mo2_form.product_id = subassembly_product
        subassembly_mo2 = subassembly_mo2_form.save()
        subassembly_mo2.action_confirm()
        subassembly_mo2.lot_producing_ids = subassembly_sn
        subassembly_mo2.button_mark_done()

    def test_product_produce_duplicate_6(self):
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
        mo1.lot_producing_ids = sn
        mo1.button_mark_done()

        ub_form = Form(self.env["mrp.unbuild"])
        ub_form.mo_id = mo1
        ub_form.lot_id = sn
        ub = ub_form.save()
        ub.action_unbuild()

        scrap = self.env["stock.scrap"].create(
            {
                "product_id": product.id,
                "product_uom_id": product.uom_id.id,
                "lot_id": sn.id,
            }
        )
        scrap._action_done()

        unscrap_picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type_int.id,
                "location_id": scrap.scrap_location_id.id,
                "location_dest_id": scrap.location_id.id,
            }
        )
        unscrap_move = self.env["stock.move"].create(
            {
                "location_id": scrap.scrap_location_id.id,
                "location_dest_id": scrap.location_id.id,
                "product_id": product.id,
                "product_uom_id": product.uom_id.id,
                "picking_id": unscrap_picking.id,
            }
        )
        unscrap_picking.action_confirm()
        self.env["stock.move.line"].create(
            {
                "move_id": unscrap_move.id,
                "product_id": unscrap_move.product_id.id,
                "lot_id": sn.id,
                "quantity": 1,
                "product_uom_id": unscrap_move.product_uom_id.id,
                "picking_id": unscrap_move.picking_id.id,
            }
        )
        unscrap_picking.button_validate()

        mo2_form = Form(self.env["mrp.production"])
        mo2_form.product_id = product
        mo2 = mo2_form.save()
        mo2.action_confirm()
        mo2.lot_producing_ids = sn
        mo2.button_mark_done()

    def test_product_produce_12(self):
        mo, _bom, _p_final, _p1, _p2 = self.generate_mo(qty_final=1)
        self.assertEqual(len(mo), 1, "MO should have been created")

        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo = mo_form.save()
        mo.move_finished_ids._action_done()
        mo.button_mark_done()

    def test_product_produce_13(self):
        product = self.env["product.product"].create(
            {
                "name": "Product no BoM",
                "is_storable": True,
            }
        )
        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = product
        mo = mo_form.save()
        move = self.env["stock.move"].create(
            {
                "product_id": self.product_2.id,
                "product_uom_id": self.uom_unit.id,
                "production_id": mo.id,
                "location_dest_id": self.output_location.id,
            }
        )

        self.assertEqual(move.reference, mo.name)
        self.assertEqual(move.origin, mo._get_origin())
        self.assertEqual(move.production_group_id, mo.production_group_id)
        self.assertEqual(move.propagate_cancel, mo.propagate_cancel)
        self.assertFalse(move.raw_material_production_id)
        self.assertEqual(move.location_id, mo.production_location_id)
        self.assertEqual(move.date, mo.date_end)
        self.assertEqual(move.date_deadline, mo.date_deadline)

        mo.move_raw_ids |= move
        mo.action_confirm()

        mo.qty_producing = 1
        mo.button_mark_done()
        self.assertEqual(mo.state, "done")
        self.assertEqual(mo.qty_produced, 1)
        self.assertEqual(mo.move_raw_ids.state, "cancel")

    def test_product_produce_14(self):
        product = self.env["product.product"].create(
            {
                "name": "Product no BoM",
                "is_storable": True,
            }
        )
        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = product
        mo = mo_form.save()
        for _i in range(2):
            move = self.env["stock.move"].create(
                {
                    "product_id": self.product_2.id,
                    "product_uom_id": self.uom_unit.id,
                    "production_id": mo.id,
                    "location_id": self.stock_location.id,
                    "location_dest_id": self.output_location.id,
                }
            )
            mo.move_raw_ids |= move
        mo.action_confirm()
        self.assertEqual(len(mo.move_raw_ids), 2)

    def test_consumed_and_produced_in_operation(self):
        self.env.user.group_ids += self.env.ref("mrp.group_mrp_byproducts")
        demo = self.env["product.product"].create({"name": "DEMO"})
        comp1 = self.env["product.product"].create({"name": "COMP1"})
        comp2 = self.env["product.product"].create({"name": "COMP2"})
        comp3 = self.env["product.product"].create({"name": "COMP3"})
        bprod1 = self.env["product.product"].create({"name": "BPROD1"})
        bprod2 = self.env["product.product"].create({"name": "BPROD2"})
        bprod3 = self.env["product.product"].create({"name": "BPROD3"})
        work_center_1 = self.env["mrp.workcenter"].create(
            {"name": "WorkCenter 1", "time_start": 11}
        )
        work_center_2 = self.env["mrp.workcenter"].create(
            {"name": "WorkCenter 2", "time_start": 12}
        )
        work_center_3 = self.env["mrp.workcenter"].create(
            {"name": "WorkCenter 3", "time_start": 13}
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_id": demo.id,
                "product_tmpl_id": demo.product_tmpl_id.id,
                "product_uom_id": self.uom_unit.id,
                "product_qty": 1.0,
                "type": "normal",
                "operation_ids": [
                    Command.create(
                        {
                            "name": "OP1",
                            "workcenter_id": work_center_1.id,
                            "time_cycle": 12,
                            "sequence": 1,
                        }
                    ),
                    Command.create(
                        {
                            "name": "OP2",
                            "workcenter_id": work_center_2.id,
                            "time_cycle": 18,
                            "sequence": 2,
                        }
                    ),
                    Command.create(
                        {
                            "name": "OP3",
                            "workcenter_id": work_center_3.id,
                            "time_cycle": 24,
                            "sequence": 3,
                        }
                    ),
                ],
            }
        )
        self.env["mrp.bom.line"].create(
            [
                {
                    "product_id": comp.id,
                    "product_qty": qty,
                    "bom_id": bom.id,
                    "operation_id": operation.id,
                }
                for (comp, qty, operation) in zip(
                    [comp1, comp2, comp3],
                    [1.0, 2.0, 3.0],
                    bom.operation_ids,
                    strict=False,
                )
            ]
        )
        self.env["mrp.bom.byproduct"].create(
            [
                {
                    "product_id": bprod.id,
                    "product_qty": qty,
                    "bom_id": bom.id,
                    "operation_id": operation.id,
                }
                for (bprod, qty, operation) in zip(
                    [bprod1, bprod2, bprod3],
                    [1.0, 2.0, 3.0],
                    bom.operation_ids,
                    strict=False,
                )
            ]
        )

        def _change_qty_producing_and_finish_wo(mo, new_qty, wo_index):
            mo.qty_producing = new_qty
            self.assertEqual(mo.qty_producing, new_qty)
            wo = mo.workorder_ids.sorted()[wo_index]
            wo.button_start()
            wo.button_finish()

        mo_form = Form(self.env["mrp.production"])
        mo_form.bom_id = bom
        mo_form.product_qty = 5
        mo = mo_form.save()
        mo.action_confirm()
        self.assertRecordValues(
            mo.move_raw_ids + mo.move_byproduct_ids,
            [
                {"picked": False, "quantity": 5},
                {"picked": False, "quantity": 10},
                {"picked": False, "quantity": 15},
                {"picked": False, "quantity": 5},
                {"picked": False, "quantity": 10},
                {"picked": False, "quantity": 15},
            ],
        )

        self.assertEqual(mo.qty_producing, 0)
        mo.qty_producing = 5
        self.assertEqual(mo.qty_producing, 5)
        self.assertRecordValues(
            mo.move_raw_ids + mo.move_byproduct_ids,
            [
                {"picked": False, "quantity": 5},
                {"picked": False, "quantity": 10},
                {"picked": False, "quantity": 15},
                {"picked": False, "quantity": 5},
                {"picked": False, "quantity": 10},
                {"picked": False, "quantity": 15},
            ],
        )

        _change_qty_producing_and_finish_wo(mo, 4, 0)
        self.assertRecordValues(
            mo.move_raw_ids + mo.move_byproduct_ids,
            [
                {"picked": True, "quantity": 4},
                {"picked": False, "quantity": 10},
                {"picked": False, "quantity": 15},
                {"picked": True, "quantity": 4},
                {"picked": False, "quantity": 10},
                {"picked": False, "quantity": 15},
            ],
        )

        _change_qty_producing_and_finish_wo(mo, 3, 1)
        self.assertRecordValues(
            mo.move_raw_ids + mo.move_byproduct_ids,
            [
                {"picked": True, "quantity": 4},
                {"picked": True, "quantity": 6},
                {"picked": False, "quantity": 15},
                {"picked": True, "quantity": 4},
                {"picked": True, "quantity": 6},
                {"picked": False, "quantity": 15},
            ],
        )

        _change_qty_producing_and_finish_wo(mo, 2, 2)
        self.assertRecordValues(
            mo.move_raw_ids + mo.move_byproduct_ids,
            [
                {"picked": True, "quantity": 4},
                {"picked": True, "quantity": 6},
                {"picked": True, "quantity": 6},
                {"picked": True, "quantity": 4},
                {"picked": True, "quantity": 6},
                {"picked": True, "quantity": 6},
            ],
        )

    def test_product_produce_uom(self):
        plastic_laminate = self.env["product.product"].create(
            {
                "name": "Plastic Laminate",
                "is_storable": True,
                "uom_id": self.uom_unit.id,
                "tracking": "serial",
            }
        )
        ply_veneer = self.env["product.product"].create(
            {
                "name": "Ply Veneer",
                "is_storable": True,
                "uom_id": self.uom_unit.id,
            }
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": plastic_laminate.product_tmpl_id.id,
                "product_uom_id": self.uom_unit.id,
                "sequence": 1,
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": ply_veneer.id,
                            "product_qty": 1,
                            "product_uom_id": self.uom_unit.id,
                            "sequence": 1,
                        }
                    )
                ],
            }
        )

        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = plastic_laminate
        mo_form.bom_id = bom
        mo_form.product_uom_id = self.uom_dozen
        mo_form.product_qty = 1
        mo = mo_form.save()

        final_product_lot = self.env["stock.lot"].create(
            {
                "name": "lot1",
                "product_id": plastic_laminate.id,
            }
        )

        mo.action_confirm()
        mo.action_assign()
        self.assertEqual(
            mo.move_raw_ids.product_qty, 12, "12 units should be reserved."
        )

        mo.lot_producing_ids = final_product_lot
        mo.qty_producing = 1
        mo.set_qty_producing()

        move_line_raw = mo.move_raw_ids.mapped("move_line_ids").filtered(
            lambda m: m.quantity
        )
        self.assertEqual(move_line_raw.quantity, 1)
        self.assertEqual(
            move_line_raw.product_uom_id,
            self.uom_unit,
            "Should be 1 unit since the tracking is serial.",
        )

        mo._post_inventory()
        move_line_finished = mo.move_finished_ids.move_line_ids.filtered(
            lambda m: m.state == "done" and m.quantity
        )
        self.assertEqual(move_line_finished.quantity, 1)
        self.assertEqual(
            move_line_finished.product_uom_id,
            self.uom_unit,
            "Should be 1 unit since the tracking is serial.",
        )

    def test_product_type_service_1(self):
        finished_product = self.env["product.product"].create(
            {
                "name": "Geyser",
                "is_storable": True,
            }
        )

        product_raw = self.env["product.product"].create(
            {
                "name": "raw Geyser",
                "type": "service",
            }
        )

        bom = self.env["mrp.bom"].create(
            {
                "product_id": finished_product.id,
                "product_tmpl_id": finished_product.product_tmpl_id.id,
                "product_uom_id": self.uom_unit.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    Command.clear(),
                    Command.create({"product_id": product_raw.id}),
                ],
            }
        )

        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = finished_product
        mo_form.bom_id = bom
        mo_form.product_uom_id = self.uom_unit
        mo_form.product_qty = 1
        mo = mo_form.save()

        self.assertTrue(mo, "Mo is created")

    def test_immediate_validate_1(self):
        mo, _bom, _p_final, p1, p2 = self.generate_mo(
            qty_final=1, qty_base_1=1, qty_base_2=1
        )
        self.env["stock.quant"]._update_available_quantity(
            p1, self.stock_location_components, 5.0
        )
        self.env["stock.quant"]._update_available_quantity(
            p2, self.stock_location_components, 5.0
        )
        mo.action_assign()
        mo.button_mark_done()
        self.assertEqual(mo.move_raw_ids.mapped("state"), ["done", "done"])
        self.assertEqual(mo.move_raw_ids.mapped("quantity"), [1, 1])
        self.assertEqual(mo.move_finished_ids.state, "done")
        self.assertEqual(mo.move_finished_ids.quantity, 1)

    def test_immediate_validate_3(self):
        mo, _bom, _p_final, p1, p2 = self.generate_mo(
            tracking_final="serial", qty_final=2, qty_base_1=1, qty_base_2=1
        )
        self.env["stock.quant"]._update_available_quantity(
            p1, self.stock_location_components, 5.0
        )
        self.env["stock.quant"]._update_available_quantity(
            p2, self.stock_location_components, 5.0
        )
        mo.action_assign()
        res_dict = mo.action_generate_serial()
        self.assertEqual(res_dict.get("res_model"), "mrp.production.serials")
        serials_wizard = Form.from_action(self.env, res_dict)
        serials_wizard.lot_name = "sn#1"
        serials_wizard.lot_quantity = 1
        res_dict = serials_wizard.save().action_generate_serial_numbers()
        serials_wizard = Form.from_action(self.env, res_dict)
        serials_wizard.save().action_apply()
        action = mo.button_mark_done()
        self.assertEqual(action.get("res_model"), "mrp.production.backorder")
        Form.from_action(self.env, action).save().action_backorder()
        self.assertEqual(mo.qty_producing, 1)
        self.assertEqual(mo.move_raw_ids.mapped("quantity"), [1, 1])
        self.assertEqual(len(mo.production_group_id.production_ids), 2)
        mo_backorder = mo.production_group_id.production_ids.sorted(
            "backorder_sequence"
        )[-1]
        self.assertEqual(mo_backorder.product_qty, 1)
        self.assertEqual(mo_backorder.move_raw_ids.mapped("product_uom_qty"), [1, 1])

    def test_immediate_validate_4(self):
        mo, _bom, _p_final, p1, p2 = self.generate_mo(
            tracking_final="serial", qty_final=2, qty_base_1=1, qty_base_2=1
        )
        self.env["stock.quant"]._update_available_quantity(
            p1, self.stock_location_components, 5.0
        )
        self.env["stock.quant"]._update_available_quantity(
            p2, self.stock_location_components, 5.0
        )
        res_dict = mo.action_generate_serial()
        self.assertEqual(res_dict.get("res_model"), "mrp.production.serials")
        serials_wizard = Form.from_action(self.env, res_dict)
        serials_wizard.lot_name = "sn#1"
        serials_wizard.lot_quantity = 1
        res_dict = serials_wizard.save().action_generate_serial_numbers()
        serials_wizard = Form.from_action(self.env, res_dict)
        serials_wizard.save().action_apply()
        action = mo.button_mark_done()
        self.assertEqual(action.get("res_model"), "mrp.production.backorder")
        Form.from_action(self.env, action).save().action_backorder()
        self.assertEqual(mo.qty_producing, 1)
        self.assertEqual(mo.move_raw_ids.mapped("quantity"), [1, 1])
        self.assertEqual(len(mo.production_group_id.production_ids), 2)
        mo_backorder = mo.production_group_id.production_ids.sorted(
            "backorder_sequence"
        )[-1]
        self.assertEqual(mo_backorder.product_qty, 1)
        self.assertEqual(mo_backorder.move_raw_ids.mapped("product_uom_qty"), [1, 1])

    def test_immediate_validate_5(self):
        mo1, bom, p_final, p1, p2 = self.generate_mo(
            qty_final=1, qty_base_1=1, qty_base_2=1
        )
        self.env["stock.quant"]._update_available_quantity(
            p1, self.stock_location_components, 5.0
        )
        self.env["stock.quant"]._update_available_quantity(
            p2, self.stock_location_components, 5.0
        )
        mo1.action_assign()
        mo2_form = Form(self.env["mrp.production"])
        mo2_form.product_id = p_final
        mo2_form.bom_id = bom
        mo2_form.product_qty = 1
        mo2 = mo2_form.save()
        mo2.action_confirm()
        mo2.action_assign()
        mo3_form = Form(self.env["mrp.production"])
        mo3_form.product_id = p_final
        mo3_form.bom_id = bom
        mo3_form.product_qty = 1
        mo3 = mo3_form.save()
        mo3.action_confirm()
        mo3.action_assign()
        mos = mo1 | mo2 | mo3
        mos.button_mark_done()
        self.assertEqual(mos.move_raw_ids.mapped("state"), ["done"] * 6)
        self.assertEqual(mos.move_raw_ids.mapped("quantity"), [1] * 6)
        self.assertEqual(mos.move_finished_ids.mapped("state"), ["done"] * 3)
        self.assertEqual(mos.move_finished_ids.mapped("quantity"), [1] * 3)

    def test_components_availability(self):
        def check_availability_state(state):
            self.assertEqual(mo.components_availability_state, state)
            MO = self.env["mrp.production"]
            self.assertIn(
                mo, MO.search([("components_availability_state", "=", state)])
            )
            self.assertNotIn(
                mo, MO.search([("components_availability_state", "!=", state)])
            )

        self.bom_2.unlink()
        now = fields.Datetime.now()
        mo_form = Form(self.env["mrp.production"])
        mo_form.bom_id = self.bom_3
        mo_form.date_start = now
        mo = mo_form.save()
        self.assertEqual(mo.components_availability, False)
        mo.action_confirm()
        self.assertEqual(mo.components_availability, "Not Available")

        tommorrow = fields.Datetime.now() + timedelta(days=1)
        after_tommorrow = fields.Datetime.now() + timedelta(days=2)
        move1 = self._create_move(
            self.product_5,
            self.supplier_location,
            self.stock_location,
            product_uom_qty=2,
            date=tommorrow,
        )
        move2 = self._create_move(
            self.product_4,
            self.supplier_location,
            self.stock_location,
            product_uom_qty=8,
            date=tommorrow,
        )
        move3 = self._create_move(
            self.product_2,
            self.supplier_location,
            self.stock_location,
            product_uom_qty=12,
            date=tommorrow,
        )
        (move1 | move2 | move3)._action_confirm()

        mo.invalidate_recordset(
            ["components_availability", "components_availability_state"]
        )
        self.assertEqual(
            mo.components_availability, f"Exp {format_date(self.env, tommorrow)}"
        )
        check_availability_state("late")

        mo.date_start = after_tommorrow

        self.assertEqual(
            mo.components_availability, f"Exp {format_date(self.env, tommorrow)}"
        )
        self.assertEqual(mo.components_availability_state, "expected")
        check_availability_state("expected")

        (move1 | move2).picked = True
        (move1 | move2)._action_done()

        self.assertEqual(
            mo.components_availability, f"Exp {format_date(self.env, tommorrow)}"
        )
        self.assertEqual(mo.components_availability_state, "expected")
        check_availability_state("expected")

        move3.picked = True
        move3._action_done()

        mo.invalidate_recordset(
            ["components_availability", "components_availability_state"]
        )
        self.assertEqual(mo.components_availability, "Available")
        check_availability_state("available")

        mo.action_assign()

        self.assertEqual(mo.reservation_state, "assigned")
        self.assertEqual(mo.components_availability, "Available")
        check_availability_state("available")

    def test_immediate_validate_6(self):
        mo, _bom, _p_final, p1, p2 = self.generate_mo(
            qty_final=1, qty_base_1=1, qty_base_2=1, tracking_final="lot"
        )
        self.env["stock.quant"]._update_available_quantity(
            p1, self.stock_location_components, 5.0
        )
        self.env["stock.quant"]._update_available_quantity(
            p2, self.stock_location_components, 5.0
        )
        mo.action_assign()
        mo.button_mark_done()
        self.assertEqual(mo.move_raw_ids.mapped("state"), ["done"] * 2)
        self.assertEqual(mo.move_raw_ids.mapped("quantity"), [1] * 2)
        self.assertEqual(mo.move_finished_ids.state, "done")
        self.assertEqual(mo.move_finished_ids.quantity, 1)
        self.assertTrue(mo.move_finished_ids.move_line_ids.lot_id)

    def test_immediate_validate_uom(self):
        p_final = self.env["product.product"].create(
            {
                "name": "final",
                "is_storable": True,
            }
        )
        component = self.env["product.product"].create(
            {
                "name": "component",
                "is_storable": True,
            }
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_id": p_final.id,
                "product_tmpl_id": p_final.product_tmpl_id.id,
                "product_uom_id": self.uom_unit.id,
                "product_qty": 1.0,
                "type": "normal",
                "consumption": "flexible",
                "bom_line_ids": [
                    Command.create({"product_id": component.id, "product_qty": 1})
                ],
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            component, self.stock_location_components, 25.0
        )
        mo_form = Form(self.env["mrp.production"])
        mo_form.bom_id = bom
        mo_form.product_uom_id = self.uom_dozen
        mo_form.product_qty = 1
        mo = mo_form.save()
        mo.action_confirm()
        mo.action_assign()
        mo.button_mark_done()
        self.assertEqual(mo.move_raw_ids.state, "done")
        self.assertEqual(mo.move_raw_ids.quantity, 12)
        self.assertEqual(mo.move_finished_ids.state, "done")
        self.assertEqual(mo.move_finished_ids.quantity, 1)
        self.assertEqual(component.qty_available, 13)

    def test_immediate_validate_uom_2(self):
        uom_L = self.env.ref("uom.product_uom_litre")
        uom_cL = self.env["uom.uom"].create(
            {
                "name": "cL",
                "relative_factor": 0.01,
                "relative_uom_id": uom_L.id,
            }
        )

        product = self.env["product.product"].create(
            {
                "name": "SuperProduct",
                "uom_id": self.uom_unit.id,
            }
        )
        consumable_component = self.env["product.product"].create(
            {
                "name": "Consumable Component",
                "type": "consu",
                "uom_id": uom_cL.id,
            }
        )
        storable_component = self.env["product.product"].create(
            {
                "name": "Storable Component",
                "is_storable": True,
                "uom_id": uom_cL.id,
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            storable_component, self.stock_location, 100
        )

        self.env.user.group_ids -= self.env.ref("uom.group_uom")
        for component in [consumable_component, storable_component]:
            bom = self.env["mrp.bom"].create(
                {
                    "product_tmpl_id": product.product_tmpl_id.id,
                    "bom_line_ids": [
                        Command.create(
                            {
                                "product_id": component.id,
                                "product_qty": 0.2,
                                "product_uom_id": uom_L.id,
                            }
                        )
                    ],
                }
            )

            mo_form = Form(self.env["mrp.production"])
            mo_form.bom_id = bom
            mo = mo_form.save()
            mo.action_confirm()
            mo.button_mark_done()

            self.assertEqual(mo.move_raw_ids.product_uom_qty, 0.2)
            self.assertEqual(mo.move_raw_ids.quantity, 0.2)

    def test_copy(self):
        mo, _bom, _p_final, _p1, _p2 = self.generate_mo(
            qty_final=1, qty_base_1=1, qty_base_2=1
        )
        mo.action_confirm()
        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo = mo_form.save()
        mo.button_mark_done()
        self.assertEqual(mo.state, "done")
        mo_copy = mo.copy()
        self.assertTrue(mo_copy.move_raw_ids)
        self.assertTrue(mo_copy.move_finished_ids)
        mo_copy.action_confirm()
        mo_form = Form(mo_copy)
        mo_form.qty_producing = 1
        mo_copy = mo_form.save()
        mo_copy.button_mark_done()
        self.assertEqual(mo_copy.state, "done")

    def test_product_produce_different_uom(self):
        precision = self.env.ref("uom.decimal_product_uom")
        precision.digits = 3

        uom_ml = self.env["uom.uom"].create(
            {
                "name": "Test ml",
                "relative_factor": 1,
            }
        )
        uom_L = self.env["uom.uom"].create(
            {
                "name": "Test Liters",
                "relative_factor": 1000,
                "relative_uom_id": uom_ml.id,
            }
        )

        product_comp = self.env["product.product"].create(
            {
                "name": "Product Component",
                "is_storable": True,
                "tracking": "lot",
                "uom_id": uom_L.id,
            }
        )

        product_final = self.env["product.product"].create(
            {
                "name": "Product Final",
                "is_storable": True,
                "tracking": "lot",
                "uom_id": uom_L.id,
            }
        )

        self.env["stock.lot"].create(
            {
                "name": "Lot Final",
                "product_id": product_final.id,
            }
        )

        lot_comp = self.env["stock.lot"].create(
            {
                "name": "Lot Component",
                "product_id": product_comp.id,
            }
        )

        self.env["stock.quant"]._update_available_quantity(
            product_comp, self.stock_location, 1, lot_id=lot_comp
        )

        test_bom = self.env["mrp.bom"].create(
            {
                "product_id": product_final.id,
                "product_tmpl_id": product_final.product_tmpl_id.id,
                "product_uom_id": uom_L.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": product_comp.id,
                            "product_qty": 375.00,
                            "product_uom_id": uom_ml.id,
                        }
                    )
                ],
            }
        )

        mo_product_final_form = Form(self.env["mrp.production"])
        mo_product_final_form.product_id = product_final
        mo_product_final_form.product_uom_id = uom_L
        mo_product_final_form.bom_id = test_bom
        mo_product_final_form.product_qty = 0.5
        mo_product_final_form = mo_product_final_form.save()

        mo_product_final_form.action_confirm()
        mo_product_final_form.action_assign()
        self.assertEqual(mo_product_final_form.reservation_state, "assigned")

        mo_product_final_form.button_mark_done()

        self.assertEqual(
            len(mo_product_final_form.move_raw_ids.move_line_ids),
            1,
            "One move line should exist for the MO.",
        )

    def test_mo_sn_warning(self):
        mo, _, p_final, _, _ = self.generate_mo(
            tracking_final="serial", qty_base_1=1, qty_final=1
        )
        self.assertEqual(len(mo), 1, "MO should have been created")

        sn1 = self.env["stock.lot"].create(
            {
                "name": "serial1",
                "product_id": p_final.id,
            }
        )

        self.env["stock.quant"]._update_available_quantity(
            p_final, self.stock_location, 1, lot_id=sn1
        )
        mo.lot_producing_ids = sn1

        warning = False
        warning = mo._onchange_lot_producing()
        self.assertTrue(warning, "Reuse of existing serial number not detected")
        self.assertEqual(
            list(warning.keys())[0], "warning", "Warning message was not returned"
        )

        mo.lot_producing_ids = self.env["stock.lot"]
        mo.action_generate_serial()
        sn2 = mo.lot_producing_ids
        mo.button_mark_done()

        scrap = self.env["stock.scrap"].create(
            {
                "product_id": p_final.id,
                "product_uom_id": self.uom_unit.id,
                "production_id": mo.id,
                "location_id": self.shelf_1.id,
                "lot_id": sn2.id,
            }
        )

        warning = False
        warning = scrap._onchange_serial_number()
        self.assertTrue(warning, "Use of wrong serial number location not detected")
        self.assertEqual(
            list(warning.keys())[0], "warning", "Warning message was not returned"
        )
        self.assertEqual(
            scrap.location_id, mo.location_dest_id, "Location was not auto-corrected"
        )

    def test_mo_assign_producing_lot(self):
        mo, _, p_final, comp1, comp2 = self.generate_mo(
            tracking_final="lot",
            tracking_base_1="serial",
            qty_base_1=1,
            qty_final=1,
            picking_type_id=self.picking_type_manu,
        )
        self.assertEqual(len(mo), 1, "MO should have been created")
        lot1, sn1 = self.env["stock.lot"].create(
            [
                {
                    "name": "lot1",
                    "product_id": p_final.id,
                    "company_id": self.env.company.id,
                },
                {
                    "name": "sn1",
                    "product_id": comp1.id,
                    "company_id": self.env.company.id,
                },
            ]
        )
        self.env["stock.quant"]._update_available_quantity(
            comp1, self.stock_location, 1, lot_id=sn1
        )
        self.env["stock.quant"]._update_available_quantity(
            comp2, self.stock_location, 1
        )
        mo.action_assign()
        self.assertEqual(mo.qty_producing, 0.0)
        self.assertRecordValues(
            mo.move_raw_ids,
            [
                {"product_id": comp2.id, "quantity": 1, "picked": False, "lot_ids": []},
                {
                    "product_id": comp1.id,
                    "quantity": 1,
                    "picked": False,
                    "lot_ids": sn1.ids,
                },
            ],
        )
        with Form(mo) as mo_form:
            mo_form.lot_producing_ids.add(lot1)
        self.assertEqual(mo.qty_producing, 0.0)
        self.assertEqual(mo.lot_producing_ids, lot1)
        self.assertRecordValues(
            mo.move_raw_ids,
            [
                {"product_id": comp2.id, "quantity": 1, "picked": False, "lot_ids": []},
                {
                    "product_id": comp1.id,
                    "quantity": 1,
                    "picked": False,
                    "lot_ids": sn1.ids,
                },
            ],
        )

    def test_a_multi_button_plan(self):
        self.bom_2.type = "normal"

        mo_3 = Form(self.env["mrp.production"])
        mo_3.bom_id = self.bom_3
        mo_3 = mo_3.save()

        self.assertEqual(len(mo_3.workorder_ids), 2)

        mo_3.button_plan()
        self.assertEqual(mo_3.state, "confirmed")
        self.assertEqual(mo_3.workorder_ids[0].state, "ready")

        mo_1 = Form(self.env["mrp.production"])
        mo_1.bom_id = self.bom_3
        mo_1 = mo_1.save()

        mo_2 = Form(self.env["mrp.production"])
        mo_2.bom_id = self.bom_3
        mo_2 = mo_2.save()

        self.assertEqual(mo_1.product_id, self.product_6)
        self.assertEqual(mo_2.product_id, self.product_6)
        self.assertEqual(len(self.bom_3.operation_ids), 2)
        self.assertEqual(len(mo_1.workorder_ids), 2)
        self.assertEqual(len(mo_2.workorder_ids), 2)

        (mo_1 | mo_2).button_plan()
        self.assertEqual(mo_1.state, "confirmed")
        self.assertEqual(mo_2.state, "confirmed")
        self.assertEqual(mo_1.workorder_ids[0].state, "ready")
        self.assertEqual(mo_2.workorder_ids[0].state, "ready")

        (mo_1 | mo_2).button_mark_done()
        self.assertEqual(mo_1.state, "done")
        self.assertEqual(mo_2.state, "done")

    def test_workcenter_timezone(self):
        workcenter = self.workcenter_1
        # The work zone is the resource's, not the calendar's: a calendar
        # states hours, the resource states the zone those hours are read in.
        workcenter.tz = "Asia/Bangkok"
        (
            workcenter.resource_calendar_id.global_leave_ids
            | workcenter.resource_calendar_id.leave_ids
        ).unlink()

        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.product_1.product_tmpl_id.id,
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_2.id,
                        }
                    )
                ],
                "operation_ids": [
                    Command.create(
                        {
                            "name": "SuperOperation01",
                            "workcenter_id": workcenter.id,
                        }
                    ),
                    Command.create(
                        {
                            "name": "SuperOperation01",
                            "workcenter_id": workcenter.id,
                        }
                    ),
                ],
            }
        )

        date_start = (
            fields.Datetime.now() + timedelta(days=7 - fields.Datetime.now().weekday())
        ).replace(hour=6, minute=0, second=0)
        mo_form = Form(self.env["mrp.production"])
        mo_form.bom_id = bom
        mo_form.date_start = date_start
        mo = mo_form.save()

        mo.workorder_ids[0].duration_expected = 240
        mo.workorder_ids[1].duration_expected = 60

        mo.action_confirm()
        mo.button_plan()

        self.assertEqual(mo.workorder_ids[0].date_start, date_start)
        self.assertEqual(mo.workorder_ids[0].date_end, date_start + timedelta(hours=4))
        tuesday = date_start + timedelta(days=1)
        self.assertEqual(mo.workorder_ids[1].date_start, tuesday.replace(hour=1))
        self.assertEqual(mo.workorder_ids[1].date_end, tuesday.replace(hour=2))

    def test_backorder_with_overconsumption(self):
        mo, _, _, _, _ = self.generate_mo(qty_final=30, qty_base_1=2, qty_base_2=3)
        mo.action_confirm()
        mo_form = Form(mo)
        mo_form.qty_producing = 10
        mo = mo_form.save()
        mo.move_raw_ids[0].quantity = 90
        mo.move_raw_ids[1].quantity = 70
        action = mo.button_mark_done()
        backorder = Form(
            self.env["mrp.production.backorder"].with_context(**action["context"])
        )
        backorder.save().action_backorder()
        mo_backorder = mo.production_group_id.production_ids.sorted(
            "backorder_sequence"
        )[-1]

        self.assertEqual(mo.product_uom_qty, 10.0)
        self.assertEqual(mo.qty_produced, 10.0)
        move_prod_1 = self.env["stock.move"].search(
            [
                ("product_id", "=", mo.bom_id.bom_line_ids[0].product_id.id),
                ("raw_material_production_id", "=", mo.id),
            ]
        )
        move_prod_2 = self.env["stock.move"].search(
            [
                ("product_id", "=", mo.bom_id.bom_line_ids[1].product_id.id),
                ("raw_material_production_id", "=", mo.id),
            ]
        )
        self.assertEqual(sum(move_prod_1.mapped("quantity")), 90.0)
        self.assertEqual(sum(move_prod_1.mapped("product_uom_qty")), 30.0)
        self.assertEqual(sum(move_prod_2.mapped("quantity")), 70.0)
        self.assertEqual(sum(move_prod_2.mapped("product_uom_qty")), 20.0)

        self.assertEqual(mo_backorder.product_uom_qty, 20.0)
        move_prod_1_bo = self.env["stock.move"].search(
            [
                ("product_id", "=", mo.bom_id.bom_line_ids[0].product_id.id),
                ("raw_material_production_id", "=", mo_backorder.id),
            ]
        )
        move_prod_2_bo = self.env["stock.move"].search(
            [
                ("product_id", "=", mo.bom_id.bom_line_ids[1].product_id.id),
                ("raw_material_production_id", "=", mo_backorder.id),
            ]
        )
        self.assertEqual(sum(move_prod_1_bo.mapped("product_uom_qty")), 60.0)
        self.assertEqual(sum(move_prod_2_bo.mapped("product_uom_qty")), 40.0)

    def test_backorder_with_underconsumption(self):
        mo, _, _, p1, p2 = self.generate_mo(qty_final=20, qty_base_1=1, qty_base_2=1)
        mo.action_confirm()
        mo_form = Form(mo)
        mo_form.qty_producing = 10
        mo = mo_form.save()
        mo.move_raw_ids.filtered(lambda m: m.product_id == p1).quantity = 5
        mo.move_raw_ids.filtered(lambda m: m.product_id == p2).quantity = 10
        action = mo.button_mark_done()
        backorder = Form(
            self.env["mrp.production.backorder"].with_context(**action["context"])
        )
        backorder.save().action_backorder()
        mo_backorder = mo.production_group_id.production_ids.sorted(
            "backorder_sequence"
        )[-1]

        self.assertEqual(mo.product_uom_qty, 10.0)
        self.assertEqual(mo.qty_produced, 10.0)
        move_prod_1_done = mo.move_raw_ids.filtered(lambda m: m.product_id == p1)
        self.assertEqual(sum(move_prod_1_done.mapped("quantity")), 5)
        self.assertEqual(sum(move_prod_1_done.mapped("product_uom_qty")), 10)
        move_prod_2 = mo.move_raw_ids.filtered(lambda m: m.product_id == p2)
        self.assertEqual(sum(move_prod_2.mapped("quantity")), 10)
        self.assertEqual(sum(move_prod_2.mapped("product_uom_qty")), 10)

        self.assertEqual(mo_backorder.product_uom_qty, 10.0)
        move_prod_1_bo = mo_backorder.move_raw_ids.filtered(
            lambda m: m.product_id == p1
        )
        move_prod_2_bo = mo_backorder.move_raw_ids.filtered(
            lambda m: m.product_id == p2
        )
        self.assertEqual(sum(move_prod_1_bo.mapped("product_uom_qty")), 10.0)
        self.assertEqual(sum(move_prod_2_bo.mapped("product_uom_qty")), 10.0)

    def test_state_workorders(self):
        bom = self.env["mrp.bom"].create(
            {
                "product_id": self.product_4.id,
                "product_tmpl_id": self.product_4.product_tmpl_id.id,
                "product_uom_id": self.uom_unit.id,
                "product_qty": 1.0,
                "consumption": "flexible",
                "type": "normal",
                "bom_line_ids": [
                    Command.create({"product_id": self.product_2.id, "product_qty": 1}),
                ],
                "operation_ids": [
                    Command.create(
                        {
                            "name": "amUgbidhaW1lIHBhcyBsZSBKUw==",
                            "workcenter_id": self.workcenter_1.id,
                            "time_cycle": 15,
                            "sequence": 1,
                        }
                    ),
                    Command.create(
                        {
                            "name": "137 Python",
                            "workcenter_id": self.workcenter_1.id,
                            "time_cycle": 1,
                            "sequence": 2,
                        }
                    ),
                ],
            }
        )

        self.env["stock.quant"].create(
            {
                "location_id": self.stock_location_components.id,
                "product_id": self.product_2.id,
                "inventory_quantity": 10,
            }
        ).action_apply_inventory()

        mo = Form(self.env["mrp.production"])
        mo.bom_id = bom
        mo = mo.save()

        self.assertEqual(list(mo.workorder_ids.mapped("state")), ["ready", "ready"])

        mo.action_confirm()
        mo.action_assign()
        self.assertEqual(mo.move_raw_ids.state, "assigned")
        self.assertEqual(list(mo.workorder_ids.mapped("state")), ["ready", "blocked"])
        mo.action_unreserve()
        self.assertEqual(list(mo.workorder_ids.mapped("state")), ["ready", "blocked"])

        mo.workorder_ids[0].unlink()

        self.assertEqual(list(mo.workorder_ids.mapped("state")), ["ready"])
        mo.action_assign()
        self.assertEqual(list(mo.workorder_ids.mapped("state")), ["ready"])

        mo.button_mark_done()
        self.assertEqual(list(mo.workorder_ids.mapped("state")), ["done"])

    def test_products_with_variants(self):
        attribute = self.env["product.attribute"].create(
            {
                "name": "Test Attribute",
            }
        )
        attribute_values = self.env["product.attribute.value"].create(
            [
                {
                    "name": "Value 1",
                    "attribute_id": attribute.id,
                    "sequence": 1,
                },
                {
                    "name": "Value 2",
                    "attribute_id": attribute.id,
                    "sequence": 2,
                },
            ]
        )
        product = self.env["product.template"].create(
            {
                "attribute_line_ids": [
                    [
                        0,
                        0,
                        {
                            "attribute_id": attribute.id,
                            "value_ids": [[6, 0, attribute_values.ids]],
                        },
                    ]
                ],
                "name": "Product with variants",
            }
        )

        variant_1 = product.product_variant_ids[0]
        variant_2 = product.product_variant_ids[1]

        component = self.env["product.template"].create(
            {
                "name": "Component",
            }
        )

        self.env["mrp.bom"].create(
            {
                "product_id": False,
                "product_tmpl_id": product.id,
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": component.product_variant_id.id,
                            "product_qty": 1,
                        }
                    ),
                ],
            }
        )

        mo_form_1 = Form(self.env["mrp.production"])
        mo_form_1.product_id = variant_1
        mo_1 = mo_form_1.save()
        mo_form_1 = Form(self.env["mrp.production"].browse(mo_1.id))
        mo_form_1.product_id = variant_2
        mo_1 = mo_form_1.save()
        mo_1.action_confirm()
        mo_1.action_assign()
        mo_form_1 = Form(self.env["mrp.production"].browse(mo_1.id))
        mo_form_1.qty_producing = 1
        mo_1 = mo_form_1.save()
        mo_1.button_mark_done()

        move_lines_1 = self.env["stock.move.line"].search(
            [("reference", "=", mo_1.name)]
        )
        move_finished_ids_1 = self.env["stock.move"].search(
            [("production_id", "=", mo_1.id)]
        )
        self.assertEqual(
            len(move_lines_1),
            2,
            "There should only be 2 move lines: the component line and produced product line",
        )
        self.assertEqual(
            len(move_finished_ids_1),
            1,
            "There should only be 1 produced product for this MO",
        )
        self.assertEqual(
            move_finished_ids_1.product_id, variant_2, "Incorrect variant produced"
        )

        mo_form_2 = Form(self.env["mrp.production"])
        mo_form_2.product_id = variant_1
        mo_form_2.product_id = variant_2
        mo_2 = mo_form_2.save()
        mo_2.action_confirm()
        mo_2.action_assign()
        mo_form_2 = Form(self.env["mrp.production"].browse(mo_2.id))
        mo_form_2.qty_producing = 1
        mo_2 = mo_form_2.save()
        mo_2.button_mark_done()

        move_lines_2 = self.env["stock.move.line"].search(
            [("reference", "=", mo_2.name)]
        )
        move_finished_ids_2 = self.env["stock.move"].search(
            [("production_id", "=", mo_2.id)]
        )
        self.assertEqual(
            len(move_lines_2),
            2,
            "There should only be 2 move lines: the component line and produced product line",
        )
        self.assertEqual(
            len(move_finished_ids_2),
            1,
            "There should only be 1 produced product for this MO",
        )
        self.assertEqual(
            move_finished_ids_2.product_id, variant_2, "Incorrect variant produced"
        )

        mo_form_3 = Form(self.env["mrp.production"])
        mo_form_3.product_id = variant_1
        mo_form_3.product_id = variant_2
        mo_3 = mo_form_3.save()
        mo_form_3 = Form(self.env["mrp.production"].browse(mo_3.id))
        mo_form_3.product_id = variant_1
        mo_3 = mo_form_3.save()
        mo_3.action_confirm()
        mo_3.action_assign()
        mo_form_3 = Form(self.env["mrp.production"].browse(mo_3.id))
        mo_form_3.qty_producing = 1
        mo_3 = mo_form_3.save()
        mo_3.button_mark_done()

        move_lines_3 = self.env["stock.move.line"].search(
            [("reference", "=", mo_3.name)]
        )
        move_finished_ids_3 = self.env["stock.move"].search(
            [("production_id", "=", mo_3.id)]
        )
        self.assertEqual(
            len(move_lines_3),
            2,
            "There should only be 2 move lines: the component line and produced product line",
        )
        self.assertEqual(
            len(move_finished_ids_3),
            1,
            "There should only be 1 produced product for this MO",
        )
        self.assertEqual(
            move_finished_ids_3.product_id, variant_1, "Incorrect variant produced"
        )

    def test_move_finished_onchanges(self):
        product1 = self.env["product.product"].create(
            {
                "name": "Oatmeal Cookie",
            }
        )
        product2 = self.env["product.product"].create(
            {
                "name": "Chocolate Chip Cookie",
            }
        )

        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = product1
        mo_form.product_id = product2
        mo = mo_form.save()
        self.assertEqual(
            len(mo.move_finished_ids),
            1,
            "Wrong number of finished product moves created",
        )
        self.assertEqual(
            mo.move_finished_ids.product_id,
            product2,
            "Wrong product to produce in finished product move",
        )
        mo_form = Form(self.env["mrp.production"].browse(mo.id))
        mo_form.product_id = product1
        mo = mo_form.save()
        self.assertEqual(
            len(mo.move_finished_ids), 1, "Wrong number of finish product moves created"
        )
        self.assertEqual(
            mo.move_finished_ids.product_id,
            product1,
            "Wrong product to produce in finished product move",
        )
        mo_form = Form(self.env["mrp.production"].browse(mo.id))
        mo_form.product_id = product2
        mo_form.product_id = product1
        mo = mo_form.save()
        self.assertEqual(
            len(mo.move_finished_ids), 1, "Wrong number of finish product moves created"
        )
        self.assertEqual(
            mo.move_finished_ids.product_id,
            product1,
            "Wrong product to produce in finished product move",
        )

        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = product1
        mo_form.product_qty = 5
        mo_form.product_qty = 10
        mo2 = mo_form.save()
        self.assertEqual(
            len(mo2.move_finished_ids),
            1,
            "Wrong number of finished product moves created",
        )
        self.assertEqual(
            mo2.move_finished_ids.product_qty,
            10,
            "Wrong qty to produce for the finished product move",
        )

        mo_form = Form(self.env["mrp.production"].browse(mo2.id))
        mo_form.product_qty = 5
        mo2 = mo_form.save()
        self.assertEqual(
            len(mo2.move_finished_ids),
            1,
            "Wrong number of finish product moves created",
        )
        self.assertEqual(
            mo2.move_finished_ids.product_qty,
            5,
            "Wrong qty to produce for the finished product move",
        )

        mo_form = Form(self.env["mrp.production"].browse(mo2.id))
        mo_form.product_qty = 10
        mo_form.product_qty = 5
        mo2 = mo_form.save()
        self.assertEqual(
            len(mo2.move_finished_ids),
            1,
            "Wrong number of finish product moves created",
        )
        self.assertEqual(
            mo2.move_finished_ids.product_qty,
            5,
            "Wrong qty to produce for the finished product move",
        )

        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = product1
        mo_form.product_qty = 1
        mo_form.product_uom_id = self.env["uom.uom"].browse(
            self.ref("uom.product_uom_dozen")
        )
        mo3 = mo_form.save()
        self.assertEqual(
            len(mo3.move_finished_ids),
            1,
            "Wrong number of finish product moves created",
        )
        self.assertEqual(
            mo3.move_finished_ids.product_qty,
            12,
            "Wrong qty to produce for the finished product move",
        )

        component = self.env["product.product"].create(
            {
                "name": "Sugar",
            }
        )

        bom1 = self.env["mrp.bom"].create(
            {
                "product_id": False,
                "product_tmpl_id": product1.product_tmpl_id.id,
                "bom_line_ids": [
                    Command.create({"product_id": component.id, "product_qty": 1}),
                ],
            }
        )

        bom2 = self.env["mrp.bom"].create(
            {
                "product_id": False,
                "product_tmpl_id": product1.product_tmpl_id.id,
                "bom_line_ids": [
                    Command.create({"product_id": component.id, "product_qty": 10}),
                ],
            }
        )
        mo_form = Form(self.env["mrp.production"])
        mo_form.bom_id = bom1
        mo_form.bom_id = bom2
        mo_form.product_id = product2
        mo4 = mo_form.save()
        self.assertFalse(mo4.bom_id, "BoM should have been removed")
        self.assertEqual(
            len(mo4.move_finished_ids),
            1,
            "Wrong number of finished product moves created",
        )
        self.assertEqual(
            mo4.move_finished_ids.product_id,
            product2,
            "Wrong product to produce in finished product move",
        )
        mo_form = Form(self.env["mrp.production"].browse(mo4.id))
        mo_form.product_id = product1
        mo_form.bom_id = bom1
        mo_form.bom_id = bom2
        mo4 = mo_form.save()
        self.assertEqual(
            len(mo4.move_finished_ids),
            1,
            "Wrong number of finish product moves created",
        )
        self.assertEqual(
            mo4.move_finished_ids.product_id,
            product1,
            "Wrong product to produce in finished product move",
        )
        mo_form = Form(self.env["mrp.production"].browse(mo4.id))
        mo_form.bom_id = bom2
        mo_form.bom_id = bom1
        mo4 = mo_form.save()
        self.assertEqual(
            len(mo4.move_finished_ids),
            1,
            "Wrong number of finish product moves created",
        )
        self.assertEqual(
            mo4.move_finished_ids.product_id,
            product1,
            "Wrong product to produce in finished product move",
        )

    def test_compute_tracked_time_1(self):
        self.env.user.group_ids += self.env.ref("mrp.group_mrp_routings")
        production_form = Form(self.env["mrp.production"])
        production_form.bom_id = self.bom_4
        production = production_form.save()
        self.assertEqual(
            production.workorder_ids[0].duration_expected,
            60.0,
            "Default duration is 0+0+1*60.0",
        )
        production.action_confirm()
        production.button_plan()
        production_form = Form(production)
        production_form.qty_producing = 1
        production = production_form.save()
        production.workorder_ids[0].duration = 15
        production.button_mark_done()

        production_form = Form(self.env["mrp.production"])
        production_form.bom_id = self.bom_4
        production = production_form.save()
        self.assertEqual(
            production.workorder_ids[0].duration_expected,
            15.0,
            "Duration is now 0+0+1*15",
        )
        production.action_confirm()
        production.button_plan()
        production_form = Form(production)
        production_form.qty_producing = 1
        production = production_form.save()
        production.workorder_ids[0].duration = 10
        production.button_mark_done()

        production_form = Form(self.env["mrp.production"])
        production_form.bom_id = self.bom_4
        production = production_form.save()
        self.assertNotEqual(
            production.workorder_ids[0].duration_expected,
            12.5,
            "Duration expected is based on the last 1 production, not last 2",
        )
        self.assertEqual(
            production.workorder_ids[0].duration_expected,
            10.0,
            "Duration is now 0+0+1*10",
        )

    def test_compute_tracked_time_2_under_capacity(self):
        self.env.user.group_ids += self.env.ref("mrp.group_mrp_routings")
        production_form = Form(self.env["mrp.production"])
        production_form.bom_id = self.bom_5
        production = production_form.save()
        production.action_confirm()
        production.button_plan()

        production_form = Form(production)
        production_form.qty_producing = 1
        production = production_form.save()
        production.workorder_ids[0].duration = 10
        production.button_mark_done()

        production_form = Form(self.env["mrp.production"])
        production_form.bom_id = self.bom_5
        production_form.product_qty = 2
        production = production_form.save()
        self.assertNotEqual(
            production.workorder_ids[0].duration_expected,
            20.0,
            "We made 1 item with capacity 2 in 10mn -> so 2 items shouldn't be double that",
        )
        self.assertEqual(
            production.workorder_ids[0].duration_expected,
            10.0,
            "Producing 1 or 2 items with capacity 2 is the same duration",
        )
        production.action_confirm()
        production.button_plan()
        production_form = Form(production)
        production_form.qty_producing = 2
        production = production_form.save()
        production.workorder_ids[0].duration = 10
        production.button_mark_done()

        production_form = Form(self.env["mrp.production"])
        production_form.bom_id = self.bom_5
        production = production_form.save()
        self.assertNotEqual(
            production.workorder_ids[0].duration_expected,
            15,
            "Producing 1 or 2 in 10mn with capacity 2 take the same amount of time : 10mn",
        )
        self.assertEqual(
            production.workorder_ids[0].duration_expected,
            10.0,
            "Duration is indeed (10+10)/2",
        )

    def test_capacity_duration_expected(self):
        self.env.user.group_ids += self.env.ref("mrp.group_mrp_routings")
        production_form = Form(self.env["mrp.production"])
        production_form.bom_id = self.bom_6
        production = production_form.save()
        production.action_confirm()
        production.button_plan()

        production_form = Form(production)
        production_form.qty_producing = 1
        production = production_form.save()
        production.workorder_ids[0].duration = 10
        production.button_mark_done()

        production_form = Form(self.env["mrp.production"])
        production_form.bom_id = self.bom_6
        production = production_form.save()
        self.assertEqual(
            production.workorder_ids[0].duration_expected,
            10.0,
            "Produce 1 with capacity 2, expected is 10mn for each run -> 10mn",
        )
        production_form.product_qty = 2
        production = production_form.save()
        self.assertEqual(
            production.workorder_ids[0].duration_expected,
            10.0,
            "Produce 2 with capacity 2, expected is 10mn for each run -> 10mn",
        )

        production_form.product_qty = 3
        production = production_form.save()
        self.assertEqual(
            production.workorder_ids[0].duration_expected,
            20.0,
            "Produce 3 with capacity 2, expected is 10mn for each run -> 20mn",
        )

        production_form.product_qty = 4
        production = production_form.save()
        self.assertEqual(
            production.workorder_ids[0].duration_expected,
            20.0,
            "Produce 4 with capacity 2, expected is 10mn for each run -> 20mn",
        )

        production_form.product_qty = 5
        production = production_form.save()
        self.assertEqual(
            production.workorder_ids[0].duration_expected,
            30.0,
            "Produce 5 with capacity 2, expected is 10mn for each run -> 30mn",
        )

    def test_workorder_set_duration(self):
        mo = Form(self.env["mrp.production"])
        mo.bom_id = self.bom_4
        mo = mo.save()
        mo.action_confirm()

        workorder = mo.workorder_ids[0]
        expected_duration = workorder.duration_expected
        real_duration_under_expected = expected_duration / 2
        real_duration_increased_above_expected = 2 * expected_duration
        real_duration_decreased = expected_duration * 0.75

        workorder.duration = real_duration_under_expected
        self.assertEqual(
            len(workorder.time_ids), 1, "A time tracking value should have been created"
        )
        self.assertEqual(
            workorder.time_ids[0].loss_type,
            "productive",
            "Total duration < Expected duration => should be productive time",
        )
        self.assertEqual(
            workorder.time_ids[0].duration,
            real_duration_under_expected,
            "Incorrect duration for time tracking value",
        )

        workorder.duration = real_duration_increased_above_expected
        self.assertEqual(
            len(workorder.time_ids),
            3,
            "Two more time tracking values should have been created",
        )
        _first, added_productive, added_performance = workorder.time_ids.sorted("id")
        self.assertEqual(
            added_productive.loss_type,
            "productive",
            "Duration amount added under the expected duration should be productive time",
        )
        self.assertEqual(
            added_performance.loss_type,
            "performance",
            "Duration amount added above expected duration should be performance (i.e. reduced) time",
        )
        self.assertEqual(
            added_productive.duration,
            expected_duration - real_duration_under_expected,
            "Added (productive) time should be expected duration - already existing duration",
        )
        self.assertEqual(
            added_performance.duration,
            real_duration_increased_above_expected - expected_duration,
            "Added (reduced) time should be total duration - expected duration",
        )

        workorder.duration = real_duration_decreased
        self.assertEqual(
            len(workorder.time_ids),
            2,
            "One time tracking values should have been deleted",
        )
        self.assertEqual(
            workorder.time_ids[1].loss_type,
            "productive",
            "Original time tracking should be unchanged",
        )
        self.assertEqual(
            workorder.time_ids[1].duration,
            real_duration_under_expected,
            "Original time tracking should be unchanged",
        )
        self.assertEqual(
            workorder.time_ids[0].loss_type,
            "productive",
            "Remaining time tracking should be productive",
        )
        self.assertEqual(
            workorder.time_ids[0].duration,
            real_duration_decreased - real_duration_under_expected,
            "Time tracking duration should have been reduced to reflect new shorter duration",
        )

    def test_propagate_quantity_on_backorders(self):
        work_center_1 = self.env["mrp.workcenter"].create(
            {"name": "WorkCenter 1", "time_start": 11}
        )
        work_center_2 = self.env["mrp.workcenter"].create(
            {"name": "WorkCenter 2", "time_start": 12}
        )
        work_center_3 = self.env["mrp.workcenter"].create(
            {"name": "WorkCenter 3", "time_start": 13}
        )

        product = self.env["product.template"].create({"name": "Finished Product"})
        component_1 = self.env["product.template"].create(
            {"name": "Component 1", "is_storable": True}
        )
        component_2 = self.env["product.template"].create(
            {"name": "Component 2", "is_storable": True}
        )
        component_3 = self.env["product.template"].create(
            {"name": "Component 3", "is_storable": True}
        )

        self.env["stock.quant"].create(
            {
                "product_id": component_1.product_variant_id.id,
                "location_id": self.stock_location.id,
                "quantity": 100,
            }
        )
        self.env["stock.quant"].create(
            {
                "product_id": component_2.product_variant_id.id,
                "location_id": self.stock_location.id,
                "quantity": 100,
            }
        )
        self.env["stock.quant"].create(
            {
                "product_id": component_3.product_variant_id.id,
                "location_id": self.stock_location.id,
                "quantity": 100,
            }
        )

        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": product.id,
                "product_id": False,
                "product_qty": 1,
                "bom_line_ids": [
                    [
                        0,
                        0,
                        {
                            "product_id": component_1.product_variant_id.id,
                            "product_qty": 1,
                        },
                    ],
                    [
                        0,
                        0,
                        {
                            "product_id": component_2.product_variant_id.id,
                            "product_qty": 1,
                        },
                    ],
                    [
                        0,
                        0,
                        {
                            "product_id": component_3.product_variant_id.id,
                            "product_qty": 1,
                        },
                    ],
                ],
                "operation_ids": [
                    [0, 0, {"name": "Operation 1", "workcenter_id": work_center_1.id}],
                    [0, 0, {"name": "Operation 2", "workcenter_id": work_center_2.id}],
                    [0, 0, {"name": "Operation 3", "workcenter_id": work_center_3.id}],
                ],
            }
        )

        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = product.product_variant_id
        mo_form.product_qty = 20
        mo = mo_form.save()

        self.assertEqual(mo.state, "draft")
        mo.action_confirm()

        wo_1, wo_2, wo_3 = mo.workorder_ids
        self.assertEqual(mo.state, "confirmed")
        self.assertEqual(wo_1.state, "ready")
        self.assertEqual(wo_1.duration_expected, 11 + 20 * 60)

        duration_expected = wo_1.duration_expected
        wo_1.button_start()
        wo_1.qty_producing = 20
        self.assertEqual(mo.state, "progress")
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

        self.assertEqual(mo.state, "to_close")
        mo.button_mark_done()

        bo = self.env["mrp.production.backorder"].create(
            {
                "mrp_production_backorder_line_ids": [
                    [0, 0, {"mrp_production_id": mo.id, "to_backorder": True}]
                ]
            }
        )
        bo.action_backorder()

        self.assertEqual(mo.state, "done")

        mo_2 = mo.production_group_id.production_ids - mo
        wo_4, wo_5, wo_6 = (
            mo_2.workorder_ids.filtered(lambda wo, op=operation: wo.operation_id == op)
            for operation in bom.operation_ids
        )

        self.assertEqual(wo_4.state, "cancel")
        self.assertEqual(wo_5.duration_expected, 12 + 15 * 60)

        wo_5.button_start()
        wo_5.qty_producing = 10
        self.assertEqual(mo_2.state, "progress")
        wo_5.button_finish()

        wo_6.button_start()
        wo_6.qty_producing = 5
        wo_6.button_finish()

        self.assertEqual(mo_2.state, "to_close")
        mo_2.button_mark_done()

        bo = self.env["mrp.production.backorder"].create(
            {
                "mrp_production_backorder_line_ids": [
                    [0, 0, {"mrp_production_id": mo_2.id, "to_backorder": True}]
                ]
            }
        )
        bo.action_backorder()

        self.assertEqual(mo_2.state, "done")

        mo_3 = mo.production_group_id.production_ids - (mo | mo_2)
        wo_7, wo_8, wo_9 = (
            mo_3.workorder_ids.filtered(lambda wo, op=operation: wo.operation_id == op)
            for operation in bom.operation_ids
        )

        self.assertEqual(wo_7.state, "cancel")
        self.assertEqual(wo_8.state, "cancel")
        self.assertEqual(wo_9.duration_expected, 13 + 10 * 60)

        wo_9.button_start()
        wo_9.qty_producing = 10
        self.assertEqual(mo_3.state, "progress")
        wo_9.button_finish()

        self.assertEqual(mo_3.state, "to_close")
        mo_3.button_mark_done()
        self.assertEqual(mo_3.state, "done")

    def test_planning_workorder(self):
        workcenter_1 = self.env["mrp.workcenter"].create(
            {
                "name": "wc1",
                "time_start": 1,
                "time_stop": 1,
                "time_efficiency": 100,
            }
        )

        workcenter_2 = self.env["mrp.workcenter"].create(
            {
                "name": "wc2",
                "time_start": 10,
                "time_stop": 5,
                "time_efficiency": 100,
                "alternative_workcenter_ids": [workcenter_1.id],
            }
        )

        for workcenter in [workcenter_1, workcenter_2]:
            self.env["mrp.workcenter.capacity"].create(
                {
                    "workcenter_id": workcenter.id,
                    "product_uom_id": self.uom_unit.id,
                    "capacity": 2,
                    "time_start": workcenter.time_start,
                    "time_stop": workcenter.time_stop,
                }
            )

        product_to_build = self.env["product.product"].create(
            {
                "name": "final product",
                "is_storable": True,
            }
        )

        product_to_use = self.env["product.product"].create(
            {
                "name": "component",
                "is_storable": True,
            }
        )

        bom = self.env["mrp.bom"].create(
            {
                "product_id": product_to_build.id,
                "product_tmpl_id": product_to_build.product_tmpl_id.id,
                "product_uom_id": self.uom_unit.id,
                "product_qty": 1.0,
                "type": "normal",
                "consumption": "flexible",
                "operation_ids": [
                    Command.create(
                        {
                            "name": "Test",
                            "workcenter_id": workcenter_2.id,
                            "time_cycle": 60,
                            "sequence": 1,
                        }
                    ),
                ],
                "bom_line_ids": [
                    Command.create({"product_id": product_to_use.id, "product_qty": 1}),
                ],
            }
        )

        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = product_to_build
        mo_form.bom_id = bom
        mo_form.product_qty = 2
        mo = mo_form.save()
        mo.action_confirm()
        mo.button_plan()
        self.assertEqual(
            mo.workorder_ids[0].workcenter_id.id,
            workcenter_1.id,
            "workcenter_1 is faster than workcenter_2 to manufacture 2 units",
        )
        mo.button_unplan()

        self.env["mrp.workcenter.capacity"].search(
            [
                ("workcenter_id", "=", workcenter_2.id),
                ("product_id", "=", False),
                ("product_uom_id", "=", self.uom_unit.id),
            ]
        ).capacity = 4

        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = product_to_build
        mo_form.bom_id = bom
        mo_form.product_qty = 4
        mo_2 = mo_form.save()
        mo_2.action_confirm()
        mo_2.button_plan()
        self.assertEqual(
            mo_2.workorder_ids[0].workcenter_id.id,
            workcenter_2.id,
            "workcenter_2 is faster than workcenter_1 to manufacture 4 units",
        )

    def test_timers_after_cancelling_mo(self):
        mo_form = Form(self.env["mrp.production"])
        mo_form.bom_id = self.bom_2
        mo_form.product_qty = 1
        mo = mo_form.save()
        mo.action_confirm()
        mo.button_plan()

        wo = mo.workorder_ids
        wo.button_start()
        mo.action_cancel()
        self.assertEqual(mo.state, "cancel", "Manufacturing order should be cancelled.")
        self.assertEqual(wo.state, "cancel", "Workorders should be cancelled.")
        self.assertTrue(
            mo.workorder_ids.time_ids.date_end,
            "The timers must stop after the cancellation of the MO",
        )

    def test_manual_duration(self):
        production_form = Form(self.env["mrp.production"])
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

        self.assertEqual(
            production.duration, production.workorder_ids.duration_expected
        )

    def test_starting_wo_twice(self):
        self.env.user.group_ids += self.env.ref("mrp.group_mrp_routings")
        production_form = Form(self.env["mrp.production"])
        production_form.bom_id = self.bom_2
        production_form.product_qty = 1
        production = production_form.save()
        production_form = Form(production)
        with production_form.workorder_ids.new() as wo:
            wo.name = "OP1"
            wo.workcenter_id = self.workcenter_1
            wo.duration_expected = 40
        production = production_form.save()
        production.action_confirm()
        production.button_plan()
        production.workorder_ids[0].button_start()
        production.workorder_ids[0].button_start()
        self.assertEqual(
            len(
                production.workorder_ids[0].time_ids.filtered(
                    lambda t: t.date_start and not t.date_end
                )
            ),
            1,
        )

    def test_qty_update_and_method_reservation(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], order="id", limit=1
        )
        warehouse.manu_type_id.reservation_method = "manual"

        for product in self.product_1 + self.product_2:
            product.is_storable = True
            self.env["stock.quant"]._update_available_quantity(
                product, warehouse.lot_stock_id, 10
            )

        mo_form = Form(self.env["mrp.production"])
        mo_form.bom_id = self.bom_1
        mo = mo_form.save()
        mo.action_confirm()

        self.assertFalse(mo.move_raw_ids.move_line_ids)

        wizard = self.env["change.production.qty"].create(
            {
                "mo_id": mo.id,
                "product_qty": 5,
            }
        )
        wizard.change_prod_qty()

        self.assertFalse(mo.move_raw_ids.move_line_ids)

    def test_source_and_child_mo(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        mto_route = warehouse.mto_pull_id.route_id
        manufacture_route = warehouse.manufacture_pull_id.route_id
        mto_route.active = True

        grandparent, parent, child = self.env["product.product"].create(
            [
                {
                    "name": n,
                    "is_storable": True,
                    "route_ids": [(6, 0, mto_route.ids + manufacture_route.ids)],
                }
                for n in ["grandparent", "parent", "child"]
            ]
        )
        component = self.env["product.product"].create(
            {
                "name": "component",
                "type": "consu",
            }
        )

        self.env["mrp.bom"].create(
            [
                {
                    "product_tmpl_id": finished_product.product_tmpl_id.id,
                    "product_qty": 1,
                    "type": "normal",
                    "bom_line_ids": [
                        Command.create({"product_id": compo.id, "product_qty": 1}),
                    ],
                }
                for finished_product, compo in [
                    (grandparent, parent),
                    (parent, child),
                    (child, component),
                ]
            ]
        )
        none_production = self.env["mrp.production"]
        for (
            steps,
            case_description,
        ) in [
            ("mrp_one_step", "1-step Manufacturing"),
            ("pbm", "2-steps Manufacturing"),
            ("pbm_sam", "3-steps Manufacturing"),
        ]:
            warehouse.manufacture_steps = steps
            warehouse.manufacture_mto_pull_id.procure_method = "make_to_order"
            grandparent_production_form = Form(self.env["mrp.production"])
            grandparent_production_form.product_id = grandparent
            grandparent_production = grandparent_production_form.save()
            grandparent_production.action_confirm()

            child_production, parent_production = self.env["mrp.production"].search(
                [("product_id", "in", (parent + child).ids)], order="id desc", limit=2
            )

            for source_mo, mo, product, child_mo in [
                (
                    none_production,
                    grandparent_production,
                    grandparent,
                    parent_production,
                ),
                (grandparent_production, parent_production, parent, child_production),
                (parent_production, child_production, child, none_production),
            ]:
                self.assertEqual(
                    mo.product_id,
                    product,
                    "[%s] There should be a MO for product %s"
                    % (case_description, product.display_name),
                )
                self.assertEqual(
                    mo.mrp_production_source_count,
                    len(source_mo),
                    "[%s] Incorrect value for product %s"
                    % (case_description, product.display_name),
                )
                self.assertEqual(
                    mo.mrp_production_child_count,
                    len(child_mo),
                    "[%s] Incorrect value for product %s"
                    % (case_description, product.display_name),
                )

                source_action = mo.action_view_mrp_production_sources()
                child_action = mo.action_view_mrp_production_childs()
                self.assertEqual(
                    source_action.get("res_id", False),
                    source_mo.id,
                    "[%s] Incorrect value for product %s"
                    % (case_description, product.display_name),
                )
                self.assertEqual(
                    child_action.get("res_id", False),
                    child_mo.id,
                    "[%s] Incorrect value for product %s"
                    % (case_description, product.display_name),
                )

    @freeze_time("2022-06-28 08:00")
    def test_replan_workorders01(self):
        self.env.user.group_ids += self.env.ref("mrp.group_mrp_routings")
        mos = self.env["mrp.production"]
        for _ in range(2):
            mo_form = Form(self.env["mrp.production"])
            mo_form.bom_id = self.bom_4
            mo_form.save()
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
        self.assertEqual(wo_01.date_end, wo_02.date_start)

    @freeze_time("2022-06-28 08:00")
    def test_replan_workorders02(self):
        self.env.user.group_ids += self.env.ref("mrp.group_mrp_routings")
        mos = self.env["mrp.production"]
        for _ in range(2):
            mo_form = Form(self.env["mrp.production"])
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
        self.assertEqual(wo_01.date_end, wo_02.date_start)

    @freeze_time("2022-10-05 12:00")
    def test_replan_mo_without_bom(self):
        self.env.user.group_ids += self.env.ref("mrp.group_mrp_routings")

        mos = self.env["mrp.production"]
        for _ in range(2):
            mo_form = Form(self.env["mrp.production"])
            mo_form.product_id = self.product_8
            with mo_form.move_raw_ids.new() as component:
                component.product_id = self.product_6
            mos += mo_form.save()
        mo_01, mo_02 = mos

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

        op_1, op_2 = mo_01.workorder_ids.sorted("id")
        self.assertEqual(op_2.date_start, datetime(2022, 10, 23, 12))

        with Form(mo_01) as mo_01_form:
            with mo_01_form.workorder_ids.edit(0) as workorder:
                workorder.date_start = datetime(2022, 10, 18, 12)
            mo_01 = mo_01_form.save()

        self.assertEqual(op_1.date_start, datetime(2022, 10, 18, 12))
        self.assertEqual(op_2.date_start, datetime(2022, 10, 23, 12))
        self.assertNotEqual(op_1.date_end, op_2.date_start)

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

        op_1, op_2 = mo_02.workorder_ids.sorted("id")
        self.assertEqual(op_1.date_start, datetime(2022, 10, 20, 12))
        self.assertTrue(op_2.show_json_popover)

    @freeze_time("2023-03-01 12:00")
    def test_planning_cancelled_workorder(self):
        self.env.company.resource_calendar_id.tz = "Europe/Brussels"
        workcenter_1 = self.env["mrp.workcenter"].create(
            {
                "name": "wc1",
                "time_start": 10,
                "time_stop": 5,
                "time_efficiency": 100,
            }
        )
        workcenter_2 = self.env["mrp.workcenter"].create(
            {
                "name": "wc2",
                "time_start": 10,
                "time_stop": 5,
                "time_efficiency": 100,
            }
        )
        workcenter_3 = self.env["mrp.workcenter"].create(
            {
                "name": "wc3",
                "time_start": 10,
                "time_stop": 5,
                "time_efficiency": 100,
            }
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_id": self.product_6.id,
                "product_tmpl_id": self.product_6.product_tmpl_id.id,
                "product_uom_id": self.uom_unit.id,
                "ready_to_produce": "asap",
                "consumption": "flexible",
                "product_qty": 1.0,
                "operation_ids": [
                    Command.create(
                        {
                            "name": "Cutting Machine",
                            "workcenter_id": workcenter_1.id,
                            "time_cycle_manual": 30,
                            "sequence": 1,
                        }
                    ),
                    Command.create(
                        {
                            "name": "Weld Machine",
                            "workcenter_id": workcenter_2.id,
                            "time_cycle_manual": 30,
                            "sequence": 2,
                        }
                    ),
                    Command.create(
                        {
                            "name": "Gift Wrap Machine",
                            "workcenter_id": workcenter_3.id,
                            "time_cycle_manual": 30,
                            "sequence": 3,
                        }
                    ),
                ],
                "type": "normal",
                "bom_line_ids": [
                    Command.create({"product_id": self.product_2.id, "product_qty": 1}),
                ],
            }
        )

        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = self.product_6
        mo_form.bom_id = bom
        mo_form.product_qty = 2
        mo = mo_form.save()
        mo.action_confirm()
        mo.button_plan()
        self.assertEqual(mo.workorder_ids[0].date_start, datetime(2023, 3, 1, 12, 0))
        self.assertEqual(mo.workorder_ids[1].date_start, datetime(2023, 3, 1, 13, 15))
        self.assertEqual(mo.workorder_ids[2].date_start, datetime(2023, 3, 1, 14, 30))

        mo_form = Form(mo)
        mo_form.qty_producing = 2
        mo = mo_form.save()
        mo.workorder_ids[0].button_start()
        mo.workorder_ids[0].button_finish()
        mo_form.qty_producing = 1
        mo = mo_form.save()
        mo.workorder_ids[1].button_start()
        mo.workorder_ids[1].button_finish()
        mo.workorder_ids[2].button_start()
        mo.workorder_ids[2].button_finish()

        action = mo.button_mark_done()
        backorder = Form(
            self.env["mrp.production.backorder"].with_context(**action["context"])
        )
        backorder.save().action_backorder()
        mo_backorder = mo.production_group_id.production_ids.sorted(
            "backorder_sequence"
        )[-1]
        mo_backorder.button_plan()
        cutting, welding, wrapping = mo_backorder.workorder_ids.sorted(
            lambda wo: wo.operation_id.sequence
        )

        self.assertEqual(cutting.state, "cancel")
        self.assertEqual(welding.state, "ready")
        self.assertEqual(wrapping.state, "blocked")
        self.assertFalse(cutting.date_start)
        self.assertEqual(welding.date_start, datetime(2023, 3, 1, 12, 0))
        self.assertEqual(wrapping.date_start, datetime(2023, 3, 1, 12, 45))

    @freeze_time("2023-03-01 12:00")
    def test_all_workorders_planned(self):
        self.env.user.group_ids += self.env.ref("mrp.group_mrp_routings")

        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = self.product_8
        mo = mo_form.save()
        with mo_form.workorder_ids.new() as workorder:
            workorder.name = "OP1"
            workorder.workcenter_id = self.workcenter_2
        with mo_form.workorder_ids.new() as workorder:
            workorder.name = "OP2"
            workorder.workcenter_id = self.workcenter_2
        mo = mo_form.save()
        mo.action_confirm()

        mo.workorder_ids[1].button_start()
        mo.workorder_ids[1].button_finish()

        self.assertTrue(mo.workorder_ids[1].date_start)

        with Form(mo) as mo_form:
            with mo_form.workorder_ids.new() as workorder:
                workorder.name = "OP3"
                workorder.workcenter_id = self.workcenter_2
            mo = mo_form.save()

        self.assertTrue(mo.workorder_ids[0].date_start)
        self.assertTrue(mo.workorder_ids[2].date_start)

    def test_compute_product_id(self):
        order = self.env["mrp.production"].create(
            {
                "bom_id": self.bom_1.id,
            }
        )
        self.assertEqual(order.product_id, self.bom_1.product_id)

    def test_compute_product_uom_id(self):
        order = self.env["mrp.production"].create(
            {
                "bom_id": self.bom_1.id,
            }
        )
        self.assertEqual(order.product_uom_id, self.bom_1.product_uom_id)

    def test_compute_bom_id(self):
        order = self.env["mrp.production"].create(
            {
                "product_id": self.bom_1.product_id.id,
            }
        )
        self.assertEqual(order.bom_id, self.bom_1)

    def test_move_raw_uom_rounding(self):
        self.box250 = self.env["uom.uom"].create(
            {
                "name": "box250",
                "relative_factor": 250.0,
                "relative_uom_id": self.uom_unit.id,
            }
        )
        self.env["decimal.precision"].search([("name", "=", "Product Unit")]).digits = 0

        test_bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.product_7_template.id,
                "product_uom_id": self.uom_unit.id,
                "product_qty": 250.0,
                "type": "normal",
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_2.id,
                            "product_qty": 1.0,
                            "product_uom_id": self.box250.id,
                        }
                    ),
                ],
            }
        )
        self.env["stock.quant"].create(
            {
                "location_id": self.stock_location.id,
                "product_id": self.product_2.id,
                "inventory_quantity": 500,
            }
        ).action_apply_inventory()

        mo_form = Form(self.env["mrp.production"])
        mo_form.bom_id = test_bom
        mo = mo_form.save()
        mo.action_confirm()

        quant = self.env["stock.quant"]
        self.assertEqual(mo.move_raw_ids.product_uom_qty, 1)
        self.assertEqual(
            mo.move_raw_ids.move_line_ids.quantity, mo.move_raw_ids.product_uom_qty
        )
        self.assertEqual(
            quant._get_available_quantity(self.product_2, self.stock_location), 250
        )
        update_quantity_wizard = self.env["change.production.qty"].create(
            {
                "mo_id": mo.id,
                "product_qty": 300,
            }
        )
        update_quantity_wizard.change_prod_qty()

        self.assertEqual(mo.move_raw_ids.product_uom_qty, 2)
        self.assertEqual(
            mo.move_raw_ids.move_line_ids.quantity, mo.move_raw_ids.product_uom_qty
        )
        self.assertEqual(
            quant._get_available_quantity(self.product_2, self.stock_location), 0
        )

    def test_update_qty_to_consume_of_component(self):
        self.bom_4.product_uom_id = self.uom_dozen

        mo_form = Form(self.env["mrp.production"])
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
        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = self.product_1
        mo = mo_form.save()
        self.assertEqual(len(mo.move_finished_ids), 1)
        mo.product_id = self.product_2
        self.assertEqual(len(mo.move_finished_ids), 1)
        self.assertFalse(
            self.env["stock.move"].search(
                [
                    ("product_id", "=", self.product_1.id),
                    ("state", "=", "draft"),
                ]
            )
        )

    def test_compute_picking_type_id(self):
        self.env.user.group_ids += self.env.ref("stock.group_adv_location")
        picking_type = self.env["stock.picking.type"].create(
            {
                "name": "new_picking_type",
                "code": "internal",
                "sequence_code": "NPT",
                "default_location_src_id": self.stock_location.id,
                "default_location_dest_id": self.stock_location_components.id,
                "warehouse_id": self.warehouse_1.id,
            }
        )
        self.bom_1.picking_type_id = picking_type
        mo_form = Form(self.env["mrp.production"])
        mo_form.bom_id = self.bom_1
        mo = mo_form.save()
        self.assertEqual(mo.picking_type_id.id, picking_type.id)
        self.assertFalse(self.bom_2.picking_type_id)
        mo_form = Form(self.env["mrp.production"])
        mo_form.bom_id = self.bom_2
        mo_2 = mo_form.save()
        picking_type_company = self.env["stock.picking.type"].search_read(
            [
                ("code", "=", "mrp_operation"),
                ("warehouse_id.company_id", "in", mo_2.company_id.ids),
            ],
            ["company_id"],
            load=False,
            limit=1,
        )
        self.assertEqual(mo_2.picking_type_id.id, picking_type_company[0]["id"])

    def test_onchange_picking_type_id_and_name(self):
        stock_location_1 = self.stock_location
        stock_location_2 = stock_location_1.copy()
        picking_type_1 = self.env["stock.picking.type"].create(
            {
                "name": "new_picking_type_1",
                "code": "mrp_operation",
                "sequence_code": "PT1",
                "default_location_src_id": stock_location_1.id,
                "default_location_dest_id": stock_location_1.id,
                "warehouse_id": self.warehouse_1.id,
            }
        )
        picking_type_2 = picking_type_1.copy(
            {
                "name": "new_picking_type_2",
                "sequence_code": "PT2",
                "default_location_src_id": stock_location_2.id,
                "default_location_dest_id": stock_location_2.id,
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_2, stock_location_2, 1
        )
        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = self.product_4
        mo_form.picking_type_id = picking_type_1
        mo = mo_form.save()
        mo.action_confirm()
        move = mo.move_raw_ids[0]
        self.assertEqual(mo.name, "BWH/PT1/00001")
        self.assertEqual(move.location_id, stock_location_1)
        self.assertEqual(move.quantity, 0.0)
        mo.picking_type_id = picking_type_2
        self.assertEqual(mo.name, "BWH/PT2/00001")
        self.assertEqual(move.location_id, stock_location_2)
        self.assertEqual(move.quantity, 1.0)
        mo.picking_type_id = picking_type_1
        self.assertEqual(mo.name, "BWH/PT1/00002")
        mo.picking_type_id = picking_type_1
        self.assertEqual(mo.name, "BWH/PT1/00002")

    def test_onchange_bom_ids_and_picking_type(self):
        warehouse01 = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        warehouse02, warehouse03 = self.env["stock.warehouse"].create(
            [
                {"name": "Second Warehouse", "code": "WH02"},
                {"name": "Third Warehouse", "code": "WH03"},
            ]
        )

        finished_product = self.env["product.product"].create(
            {"name": "finished product"}
        )
        bom_wh01, bom_wh02 = self.env["mrp.bom"].create(
            [
                {
                    "product_id": finished_product.id,
                    "product_tmpl_id": finished_product.product_tmpl_id.id,
                    "product_uom_id": self.uom_unit.id,
                    "product_qty": 1.0,
                    "bom_line_ids": [
                        Command.create(
                            {"product_id": self.product.id, "product_qty": 1}
                        )
                    ],
                    "picking_type_id": wh.manu_type_id.id,
                    "sequence": wh.id,
                }
                for wh in [warehouse01, warehouse02]
            ]
        )

        bom_wh01.sequence = bom_wh02.sequence + 1

        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = finished_product
        self.assertEqual(
            mo_form.bom_id,
            bom_wh02,
            "Should select the first BoM in the list, whatever the picking type is",
        )
        self.assertEqual(mo_form.picking_type_id, warehouse02.manu_type_id)

        mo_form.bom_id = bom_wh01
        self.assertEqual(
            mo_form.picking_type_id,
            warehouse01.manu_type_id,
            "Should be adapted because of the found BoM",
        )

        mo_form.bom_id = bom_wh02
        self.assertEqual(
            mo_form.picking_type_id,
            warehouse02.manu_type_id,
            "Should be adapted because of the found BoM",
        )

        mo_form.picking_type_id = warehouse01.manu_type_id
        self.assertEqual(mo_form.bom_id, bom_wh02, "Should not change")
        self.assertEqual(
            mo_form.picking_type_id, warehouse01.manu_type_id, "Should not change"
        )

        mo_form.picking_type_id = warehouse03.manu_type_id
        mo_form.bom_id = bom_wh01
        self.assertEqual(
            mo_form.picking_type_id,
            warehouse01.manu_type_id,
            "Should be adapted because of the found BoM "
            "(the selected picking type should be ignored)",
        )

        mo_form = Form(
            self.env["mrp.production"].with_context(
                default_picking_type_id=warehouse03.manu_type_id.id
            )
        )
        mo_form.product_id = finished_product
        self.assertFalse(
            mo_form.bom_id,
            "Should not find any BoM, because of the defined picking type",
        )
        self.assertEqual(mo_form.picking_type_id, warehouse03.manu_type_id)

        mo_form = Form(
            self.env["mrp.production"].with_context(
                default_picking_type_id=warehouse01.manu_type_id.id
            )
        )
        mo_form.product_id = finished_product
        self.assertEqual(
            mo_form.bom_id,
            bom_wh01,
            "Should select the BoM that matches the default picking type",
        )
        self.assertEqual(
            mo_form.picking_type_id,
            warehouse01.manu_type_id,
            "Should be the default one",
        )

        mo_form.bom_id = bom_wh02
        self.assertEqual(
            mo_form.picking_type_id,
            warehouse01.manu_type_id,
            "Should not change, because of default value",
        )

        mo_form.picking_type_id = warehouse02.manu_type_id
        self.assertEqual(mo_form.bom_id, bom_wh02, "Should not change")
        self.assertEqual(
            mo_form.picking_type_id, warehouse02.manu_type_id, "Should not change"
        )

        mo_form.picking_type_id = warehouse02.manu_type_id
        mo_form.bom_id = bom_wh02
        self.assertEqual(
            mo_form.picking_type_id,
            warehouse01.manu_type_id,
            "Should be adapted because of the default value",
        )

    def test_workcenter_specific_capacities(self):
        self.env.user.group_ids += self.env.ref("mrp.group_mrp_routings")
        self.env["mrp.workcenter.capacity"].search(
            [
                ("workcenter_id", "=", self.workcenter_2.id),
                ("product_id", "=", False),
                ("product_uom_id", "=", self.product_5.uom_id.id),
            ]
        ).write(
            {
                "time_start": 10,
                "time_stop": 20,
            }
        )
        self.env["mrp.workcenter.capacity"].create(
            {
                "workcenter_id": self.workcenter_2.id,
                "product_id": self.product_4.id,
                "product_uom_id": self.product_4.uom_id.id,
                "time_start": 5,
                "time_stop": 10,
            }
        )

        production_form = Form(self.env["mrp.production"])
        production_form.product_id = self.product_5
        production = production_form.save()

        with Form(production) as mo_form:
            with mo_form.workorder_ids.new() as wo:
                wo.name = "OP1"
                wo.workcenter_id = self.workcenter_2

        self.assertEqual(
            production.workorder_ids[0].duration_expected,
            30.0,
            "Workcenter setup time (10) + workcenter cleanup time (20)",
        )

        with Form(production) as mo_form:
            mo_form.product_id = self.product_4
            with mo_form.workorder_ids.new() as wo:
                wo.name = "OP1"
                wo.workcenter_id = self.workcenter_2

        self.assertEqual(
            production.workorder_ids[0].duration_expected,
            15.0,
            "Capacity setup time (5) + capacity cleanup time (10)",
        )

    def test_unlink_workorder_with_consumed_operations(self):
        self.bom_3.bom_line_ids[0].operation_id = self.bom_3.operation_ids[0].id
        self.bom_3.bom_line_ids[1].operation_id = self.bom_3.operation_ids[1].id
        mo_form = Form(self.env["mrp.production"])
        mo_form.bom_id = self.bom_3
        mo = mo_form.save()
        mo.workorder_ids[1].unlink()
        mo.action_confirm()
        self.assertEqual(mo.state, "confirmed")
        self.assertEqual(len(mo.workorder_ids), 2)

    def test_unlink_update_workcenter_productivity(self):
        mo_form = Form(self.env["mrp.production"])
        mo_form.bom_id = self.bom_3
        mo = mo_form.save()
        mo.workorder_ids[0].button_start()
        time_log = mo.workorder_ids[0].time_ids[0]
        mo.workorder_ids[0].unlink()
        self.assertIsNot(time_log.date_end, False)

    def test_consumption_action_set_qty_and_validate(self):
        mo, bom, p_final, p1, p2 = self.generate_mo(
            consumption="warning", qty_final=10, qty_base_1=12, qty_base_2=20
        )

        mo_form = Form(mo)
        mo_form.qty_producing = 4
        mo = mo_form.save()
        self.assertEqual(
            mo.move_raw_ids[0].product_uom_qty,
            200,
            "current MO To Consume qty should match expected qty to produce",
        )
        self.assertEqual(
            mo.move_raw_ids[0].quantity,
            80,
            "current MO Consumed qty should match expected qty to produce",
        )
        self.assertEqual(
            mo.move_raw_ids[1].product_uom_qty,
            120,
            "current MO To Consume qty should match expected qty produced",
        )
        self.assertEqual(
            mo.move_raw_ids[1].quantity,
            48,
            "current MO Consumed qty should match expected qty produced",
        )
        bom.bom_line_ids[0].product_qty = 10
        self.assertEqual(mo.move_raw_ids[0].product_uom_qty, 200)
        self.assertEqual(mo.move_raw_ids[0].quantity, 80)
        action = mo.button_mark_done()
        warning = Form(
            self.env["mrp.consumption.warning"].with_context(**action["context"])
        )
        consumption = warning.save()
        self.assertEqual(
            consumption.mrp_consumption_warning_line_ids.product_consumed_qty_uom,
            80,
            "qty consumed incorrectly passed to wizard",
        )
        self.assertEqual(
            consumption.mrp_consumption_warning_line_ids.product_expected_qty_uom,
            40,
            "expected qty should match current BoM qty for qty being produced",
        )
        action = consumption.action_set_qty()
        backorder = Form(
            self.env["mrp.production.backorder"].with_context(**action["context"])
        )
        backorder.save().action_backorder()
        self.assertEqual(
            mo.move_raw_ids[0].product_uom_qty,
            80,
            "current bom expected qty should remain unchanged",
        )
        self.assertEqual(
            mo.move_raw_ids[0].quantity,
            40,
            "current bom expected qty was not applied as qty to be done",
        )
        self.assertEqual(
            mo.move_raw_ids[1].product_uom_qty,
            48,
            "line without consumption issue was incorrectly changed",
        )
        self.assertEqual(
            mo.move_raw_ids[1].quantity,
            48,
            "line without consumption issue was incorrectly changed",
        )
        self.assertEqual(mo.state, "done")
        mo_backorder = mo.production_group_id.production_ids.sorted(
            "backorder_sequence"
        )[-1]
        self.assertEqual(
            mo_backorder.move_raw_ids[0].product_uom_qty,
            120,
            "backorder values are based on original MO, not current bom",
        )
        self.assertEqual(
            mo_backorder.move_raw_ids[1].product_uom_qty,
            72,
            "backorder values incorrectly calculated",
        )

        mo2_form = Form(self.env["mrp.production"])
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
                move.product_uom_id = self.uom_dozen
        mo2.action_confirm()
        mo2_form = Form(mo2)
        mo2_form.qty_producing = 4
        mo2 = mo2_form.save()
        self.assertEqual(
            len(mo2.move_raw_ids),
            2,
            "current MO should still have 1 component from its BoM deleted + 1 additional component",
        )
        self.assertEqual(
            mo2.move_raw_ids[0].product_uom_qty,
            60,
            "current MO To Consume qty should match manually set expected qty produced",
        )
        self.assertEqual(
            mo2.move_raw_ids[0].quantity,
            48,
            "current MO Consumed qty should match expected qty to produce based on manually set value",
        )
        self.assertEqual(
            mo2.move_raw_ids[1].product_uom_qty,
            50,
            "current MO To Consume qty should match manually set expected qty produced",
        )
        self.assertEqual(
            mo2.move_raw_ids[1].quantity,
            40,
            "current MO Consumed qty should match expected qty to produce based on manually set value",
        )

        action = mo2.button_mark_done()
        warning = Form(
            self.env["mrp.consumption.warning"].with_context(**action["context"])
        )
        consumption = warning.save()
        self.assertEqual(
            len(consumption.mrp_consumption_warning_line_ids),
            3,
            "deleted move should also show as an consumption line diff from BoM",
        )
        self.assertEqual(
            consumption.mrp_consumption_warning_line_ids[0].product_consumed_qty_uom,
            40,
            "additional component was not correctly passed to wizard",
        )
        self.assertEqual(
            consumption.mrp_consumption_warning_line_ids[0].product_expected_qty_uom,
            0,
            "additional component should have no expected qty",
        )
        self.assertEqual(
            consumption.mrp_consumption_warning_line_ids[1].product_consumed_qty_uom,
            0,
            "missing line was not correctly passed to wizard",
        )
        self.assertEqual(
            consumption.mrp_consumption_warning_line_ids[1].product_expected_qty_uom,
            40,
            "expected qty should match current BoM qty for qty being produced",
        )
        self.assertEqual(
            consumption.mrp_consumption_warning_line_ids[2].product_consumed_qty_uom,
            576,
            "qty consumed was not correctly converted to product's uom before passing to wizard",
        )
        self.assertEqual(
            consumption.mrp_consumption_warning_line_ids[2].product_expected_qty_uom,
            48,
            "expected qty should match current BoM qty for qty being produced",
        )
        action = consumption.action_set_qty()
        backorder2 = Form(
            self.env["mrp.production.backorder"].with_context(**action["context"])
        )
        backorder2.save().action_backorder()
        self.assertEqual(
            len(mo2.move_raw_ids), 3, "missing line was not correctly added"
        )
        for move in mo2.move_raw_ids:
            if move.product_id == p2:
                self.assertEqual(
                    move.product_uom_qty,
                    40,
                    "missing line values were not correctly added",
                )
                self.assertEqual(
                    move.quantity, 40, "missing line values were not correctly added"
                )
            elif move.product_id == p1:
                self.assertEqual(
                    move.product_uom_qty, 48, "expected qty should be unchanged"
                )
                self.assertEqual(
                    move.quantity,
                    4,
                    "expected qty was not applied as qty to be done (UoM was possibly not correctly converted)",
                )
            else:
                self.assertEqual(
                    move.product_uom_qty,
                    40,
                    "additional component's demand should have carried over",
                )
                self.assertEqual(
                    move.quantity,
                    0,
                    "additional component should have nothing reserved",
                )
        self.assertEqual(mo2.state, "done")
        mo2_backorder = mo2.production_group_id.production_ids.sorted(
            "backorder_sequence"
        )[-1]
        self.assertEqual(
            len(mo2_backorder.move_raw_ids),
            2,
            "missing line should NOT have been added in but additional line should",
        )
        self.assertEqual(
            mo2_backorder.move_raw_ids.product_id.ids, [p1.id, self.product_1.id]
        )
        self.assertEqual(
            mo2_backorder.move_raw_ids[0].product_uom_qty,
            12,
            "backorder values are based on original MO, not current bom",
        )

        bom.bom_line_ids[0].unlink()
        mo3 = self.env["mrp.production"].create(
            {
                "product_id": p_final.id,
                "bom_id": bom.id,
                "product_qty": 1,
                "product_uom_id": p_final.uom_id.id,
            }
        )
        mo3_form = Form(mo3)
        with mo3_form.move_raw_ids.new() as line:
            line.product_id = p1
            line.product_uom_qty = 5
        mo3 = mo3_form.save()
        mo3.action_confirm()
        self.assertEqual(len(mo3.move_raw_ids), 2, "there should be 2 comp lines")
        self.assertEqual(
            len(mo3.move_raw_ids.product_id), 1, "comp lines should have same product"
        )
        mo3_form = Form(mo3)
        mo3_form.qty_producing = 1
        mo3 = mo3_form.save()
        self.assertEqual(
            mo3.move_raw_ids[0].product_uom_qty,
            12,
            "BoM created comp move does not match expected To Consume qty",
        )
        self.assertEqual(
            mo3.move_raw_ids[0].quantity,
            12,
            "BoM created comp move does not match expected Consumed qty",
        )
        self.assertEqual(
            mo3.move_raw_ids[1].product_uom_qty,
            5,
            "Manually added comp move does not match original To Consume qty",
        )
        self.assertEqual(
            mo3.move_raw_ids[1].quantity, 5, "Manually added comp move was not Consumed"
        )
        action = mo3.button_mark_done()
        warning = Form(
            self.env["mrp.consumption.warning"].with_context(**action["context"])
        )
        consumption = warning.save()
        self.assertEqual(
            len(consumption.mrp_consumption_warning_line_ids),
            1,
            "warning lines should be grouped by product",
        )
        self.assertEqual(
            consumption.mrp_consumption_warning_line_ids[0].product_expected_qty_uom,
            12,
            "BoM expected qty not correctly passed to wizard",
        )
        self.assertEqual(
            consumption.mrp_consumption_warning_line_ids[0].product_consumed_qty_uom,
            17,
            "total Consumed qty not correctly passed to wizard",
        )
        action = consumption.action_set_qty()
        self.assertEqual(
            mo3.move_raw_ids[0].product_uom_qty,
            12,
            "BoM created comp move does not match expected To Consume qty",
        )
        self.assertEqual(
            mo3.move_raw_ids[0].quantity,
            12,
            "BoM created comp move does not match expected Consumed qty",
        )
        self.assertEqual(
            mo3.move_raw_ids[1].product_uom_qty,
            5,
            "Manually added comp move To Consume qty should be unchanged",
        )
        self.assertEqual(
            mo3.move_raw_ids[1].quantity,
            0,
            "Extra line Consumed qty not correctly zero-ed",
        )
        self.assertEqual(mo3.state, "done")

    def test_exceeded_consumed_qty_and_duplicated_lines(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        mto_route = warehouse.mto_pull_id.route_id
        manufacture_route = warehouse.manufacture_pull_id.route_id
        mto_route.active = True

        product01, product02, product03 = self.env["product.product"].create(
            [
                {
                    "name": "Product %s" % (i + 1),
                    "is_storable": True,
                }
                for i in range(3)
            ]
        )

        product02.route_ids = [(6, 0, (mto_route | manufacture_route).ids)]

        mo_form = Form(self.env["mrp.production"])
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

        self.assertEqual(mo.state, "done")

        p02_raws = mo.move_raw_ids.filtered(lambda m: m.product_id == product02)
        p03_raws = mo.move_raw_ids.filtered(lambda m: m.product_id == product03)
        self.assertEqual(sum(p02_raws.mapped("quantity")), 1.5)
        self.assertEqual(sum(p03_raws.mapped("quantity")), 2)

    def test_validation_mo_with_tracked_component(self):
        self.product_2.tracking = "serial"
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.product_6.product_tmpl_id.id,
                "product_qty": 1.0,
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_2.id,
                            "product_qty": 1.0,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.product_3.id,
                            "product_qty": 1.0,
                        }
                    ),
                ],
            }
        )
        mo = self.env["mrp.production"].create(
            {
                "product_id": self.product_6.id,
                "bom_id": bom.id,
                "product_uom_qty": 1.0,
            }
        )
        mo.action_confirm()
        self.assertEqual(mo.state, "confirmed")
        mo.move_raw_ids[0].product_uom_qty = 0
        mo.move_raw_ids[0].quantity = 0
        action = mo.button_mark_done()
        consumption_warning = Form(
            self.env["mrp.consumption.warning"].with_context(**action["context"])
        ).save()

        self.assertEqual(len(consumption_warning.mrp_consumption_warning_line_ids), 1)
        self.assertEqual(
            consumption_warning.mrp_consumption_warning_line_ids[
                0
            ].product_consumed_qty_uom,
            0,
        )
        self.assertEqual(
            consumption_warning.mrp_consumption_warning_line_ids[
                0
            ].product_expected_qty_uom,
            1,
        )
        consumption_warning.action_confirm()
        self.assertEqual(mo.state, "done")

    def test_cancel_return(self):
        self.warehouse_1.manufacture_steps = "pbm"

        mo, _bom, _p_final, p1, p2 = self.generate_mo(
            qty_final=5.0, qty_base_1=1.0, qty_base_2=1.0
        )
        mo.action_confirm()

        self.env["stock.quant"]._update_available_quantity(p1, self.stock_location, 5.0)
        self.env["stock.quant"]._update_available_quantity(p2, self.stock_location, 5.0)

        mo.picking_ids.move_ids[0].quantity = 5.0
        mo.picking_ids.move_ids[1].quantity = 5.0
        mo.picking_ids.button_validate()

        update_quantity_wizard = self.env["change.production.qty"].create(
            {
                "mo_id": mo.id,
                "product_qty": 4.0,
            }
        )
        update_quantity_wizard.change_prod_qty()
        new_picking = mo.picking_ids
        self.assertEqual(
            len(new_picking), 1, "Return picking should not be created in done Transfer"
        )

    def test_manufacture_lead_days(self):
        self.env.company.horizon_days = 0
        warehouse = self.warehouse_1
        rule = warehouse.manufacture_pull_id

        self.bom_1.days_to_prepare_mo = 2
        self.bom_1.produce_delay = 3
        delays, _ = rule._get_lead_days(self.bom_1.product_id, bom=self.bom_1)
        self.assertEqual(
            delays["total_delay"],
            +self.bom_1.days_to_prepare_mo + self.bom_1.produce_delay,
        )

        warehouse.manufacture_steps = "pbm_sam"
        warehouse.pbm_route_id.rule_ids.delay = 100
        delays, _ = rule._get_lead_days(self.bom_1.product_id, bom=self.bom_1)
        self.assertEqual(
            delays["total_delay"],
            +self.bom_1.days_to_prepare_mo + self.bom_1.produce_delay + 100 * 2,
        )

    def test_use_kit_as_component_in_production_without_bom(self):
        finished, component, kit = self.env["product.product"].create(
            [
                {
                    "name": "Product %s" % (i + 1),
                    "is_storable": True,
                }
                for i in range(3)
            ]
        )
        self.env["mrp.bom"].create(
            {
                "product_id": kit.id,
                "product_tmpl_id": kit.product_tmpl_id.id,
                "type": "phantom",
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": component.id,
                            "product_qty": 1,
                        }
                    )
                ],
            }
        )

        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = finished
        mo_form.product_qty = 1
        with mo_form.move_raw_ids.new() as line:
            line.product_id = kit
        mo = mo_form.save()
        mo.action_confirm()
        self.assertEqual(mo.state, "confirmed")
        self.assertEqual(mo.move_raw_ids.product_id, component)

    def test_product_variants_in_mo(self):
        size_attribute_line = self.env["product.template.attribute.line"].create(
            [
                {
                    "product_tmpl_id": self.product_7_template.id,
                    "attribute_id": self.size_attribute.id,
                    "value_ids": [(6, 0, self.size_attribute.value_ids.ids)],
                }
            ]
        )
        c1, c2, c3 = self.env["product.product"].create(
            [
                {
                    "name": i,
                    "is_storable": True,
                }
                for i in range(3)
            ]
        )

        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.product_7_template.id,
                "product_uom_id": self.uom_unit.id,
                "product_qty": 4.0,
                "type": "normal",
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": c1.id,
                            "product_qty": 1,
                            "bom_product_template_attribute_value_ids": [
                                (4, self.product_7_attr1_v2.id)
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "product_id": c2.id,
                            "product_qty": 1,
                            "bom_product_template_attribute_value_ids": [
                                (4, self.product_7_attr1_v1.id),
                                (
                                    4,
                                    size_attribute_line.product_template_value_ids[
                                        2
                                    ].id,
                                ),
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "product_id": c3.id,
                            "product_qty": 1,
                            "bom_product_template_attribute_value_ids": [
                                (4, self.product_7_attr1_v1.id)
                            ],
                        }
                    ),
                ],
            }
        )

        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = self.product_7_template.product_variant_ids[1]
        mo_form.product_qty = 1
        mo = mo_form.save()
        self.assertEqual(mo.move_raw_ids.product_id, c1)
        mo_form.product_id = self.product_7_template.product_variant_ids[6]
        mo = mo_form.save()
        self.assertEqual(mo.move_raw_ids.product_id, (c2 | c3))
        mo_form.product_id = self.product_7_template.product_variant_ids[0]
        mo = mo_form.save()
        self.assertEqual(mo.move_raw_ids.product_id, c3)

    def test_mo_duration_expected(self):
        production_form = Form(self.env["mrp.production"])
        production_form.product_id = self.product_6
        production_form.bom_id = self.bom_4
        production_form.product_qty = 5.0
        production = production_form.save()
        production.action_confirm()

        init_duration_expected = production.workorder_ids.duration_expected
        production.workorder_ids.duration_expected = init_duration_expected + 15

        production_form = Form(production)
        production_form.qty_producing = 3.0
        production = production_form.save()

        current_duration_expected = production.workorder_ids.duration_expected
        self.assertNotEqual(current_duration_expected, init_duration_expected + 15)
        self.assertNotEqual(current_duration_expected, init_duration_expected)

        production.workorder_ids.duration_expected = current_duration_expected + 10

        backorder_wizard_dict = production.button_mark_done()
        Form.from_action(self.env, backorder_wizard_dict).save().action_backorder()

        self.assertEqual(
            production.workorder_ids.duration_expected, current_duration_expected + 10
        )

        production = production.production_group_id.production_ids.sorted(
            "backorder_sequence"
        )[-1]

        init_duration_expected = production.workorder_ids.duration_expected

        production.workorder_ids.duration_expected = init_duration_expected + 5

        production_form = Form(production)
        production_form.qty_producing = 2.0
        production = production_form.save()

        production.button_mark_done()

        self.assertEqual(
            production.workorder_ids.duration_expected, init_duration_expected + 5
        )

    def test_multi_edit_start_date_wo(self):
        self.env.company.resource_calendar_id.tz = "Europe/Brussels"
        mo = self.env["mrp.production"].create(
            {
                "product_id": self.product.id,
                "product_uom_id": self.bom_1.product_uom_id.id,
            }
        )

        wos = self.env["mrp.workorder"].create(
            [
                {
                    "name": "Test order",
                    "workcenter_id": self.workcenter_1.id,
                    "product_uom_id": self.bom_1.product_uom_id.id,
                    "production_id": mo.id,
                    "duration_expected": 1.0,
                },
                {
                    "name": "Test order2",
                    "workcenter_id": self.workcenter_2.id,
                    "product_uom_id": self.bom_1.product_uom_id.id,
                    "production_id": mo.id,
                    "duration_expected": 2.0,
                },
            ]
        )
        dt = datetime(2024, 1, 17, 11)
        wos.date_start = dt

        self.assertEqual(wos[0].date_start, dt)
        self.assertEqual(wos[1].date_start, dt)

        self.assertEqual(wos[0].date_end, dt + timedelta(hours=1, minutes=1))
        self.assertEqual(wos[1].date_end, dt + timedelta(hours=1, minutes=2))

    @users("hilda")
    def test_update_mo_with_mrp_user(self):
        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = self.product
        mo_form.product_qty = 5
        mo = mo_form.save()
        mo_form.product_qty = 10
        mo_form.save()
        self.assertEqual(mo.product_qty, 10)

    @freeze_time("2017-01-01")
    def test_expected_duration_alternative_wc(self):
        self.product_1.uom_id = self.uom_unit.id

        workcenter_1 = self.env["mrp.workcenter"].create(
            {
                "name": "wc1",
                "time_start": 2,
                "time_stop": 2,
                "time_efficiency": 100,
            }
        )
        workcenter_2 = workcenter_1.copy({"name": "wc2"})

        workcenter_1.alternative_workcenter_ids = workcenter_2
        workcenter_1.capacity_ids = [
            Command.create(
                {
                    "product_id": self.product_1.id,
                    "product_uom_id": self.product_1.uom_id.id,
                    "capacity": 1,
                    "time_start": 10,
                    "time_stop": 0,
                }
            )
        ]
        workcenter_2.capacity_ids = [
            Command.create(
                {
                    "product_id": self.product_1.id,
                    "product_uom_id": self.product_1.uom_id.id,
                    "capacity": 1,
                    "time_start": 5,
                    "time_stop": 0,
                }
            )
        ]

        bom = self.env["mrp.bom"].create(
            {
                "product_id": self.product_1.id,
                "product_tmpl_id": self.product_1.product_tmpl_id.id,
                "product_uom_id": self.uom_unit.id,
                "product_qty": 1.0,
                "type": "normal",
                "operation_ids": [
                    Command.create(
                        {
                            "name": "Test",
                            "workcenter_id": workcenter_1.id,
                            "time_cycle": 60,
                            "sequence": 1,
                        }
                    ),
                ],
            }
        )

        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = self.product_1
        mo_form.bom_id = bom
        mo_form.product_qty = 1
        mo = mo_form.save()
        mo.action_confirm()
        mo.button_plan()
        self.assertEqual(mo.workorder_ids[0].workcenter_id.id, workcenter_2.id)
        self.assertEqual(mo.workorder_ids[0].duration_expected, 65)

        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = self.product_1
        mo_form.bom_id = bom
        mo_form.product_qty = 1
        mo_2 = mo_form.save()
        mo_2.action_confirm()
        mo_2.button_plan()
        self.assertEqual(mo_2.workorder_ids[0].workcenter_id.id, workcenter_1.id)
        self.assertEqual(mo_2.workorder_ids[0].duration_expected, 70)

    def test_duration_expected_when_done(self):
        bom = self.bom_2
        bom.type = "normal"
        bom.operation_ids.time_mode = "manual"
        bom.operation_ids.time_cycle_manual = 60.0
        product = bom.product_id
        component_1, component_2 = bom.bom_line_ids.mapped("product_id")
        self.env["stock.quant"]._update_available_quantity(
            component_1, self.stock_location, 50.0
        )
        self.env["stock.quant"]._update_available_quantity(
            component_2, self.stock_location, 50.0
        )
        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = product
        mo_form.bom_id = bom
        mo_form.product_qty = 10.0
        mo = mo_form.save()
        mo.action_confirm()
        self.assertRecordValues(
            mo.workorder_ids,
            [
                {
                    "qty_produced": 0.0,
                    "qty_remaining": 10.0,
                    "duration_expected": 390.0,
                    "duration": 0.0,
                }
            ],
        )

        mo_form = Form(mo)
        mo_form.qty_producing = 3.0
        mo = mo_form.save()
        action = mo.button_mark_done()
        backorder_form = Form(
            self.env["mrp.production.backorder"].with_context(**action["context"])
        )
        backorder_form.save().action_backorder()
        self.assertRecordValues(
            mo.workorder_ids,
            [
                {
                    "qty_produced": 3.0,
                    "qty_remaining": 0.0,
                    "duration_expected": 165.0,
                    "duration": 165.0,
                    "state": "done",
                }
            ],
        )

        bo = self.env["mrp.production"].search([("product_id", "=", product.id)]) - mo
        self.assertRecordValues(
            bo, [{"product_id": product.id, "product_uom_qty": 7.0}]
        )
        self.assertRecordValues(
            bo.workorder_ids,
            [
                {
                    "qty_produced": 0.0,
                    "qty_remaining": 7.0,
                    "duration_expected": 315.0,
                    "duration": 0.0,
                }
            ],
        )

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
        bo.workorder_ids.duration_expected = 120.0
        action = bo.button_mark_done()
        backorder_form = Form(
            self.env["mrp.production.backorder"].with_context(**action["context"])
        )
        backorder_form.save().action_backorder()
        self.assertRecordValues(
            bo.workorder_ids,
            [
                {
                    "qty_produced": 3.0,
                    "qty_remaining": 0.0,
                    "duration_expected": 120.0,
                    "duration": 120.0,
                    "state": "done",
                }
            ],
        )

        bo_2 = (
            self.env["mrp.production"].search([("product_id", "=", product.id)])
            - mo
            - bo
        )
        self.assertRecordValues(
            bo_2, [{"product_id": product.id, "product_uom_qty": 4.0}]
        )
        self.assertRecordValues(
            bo_2.workorder_ids,
            [
                {
                    "qty_produced": 0.0,
                    "qty_remaining": 4.0,
                    "duration_expected": 165.0,
                    "duration": 0.0,
                }
            ],
        )

        bo_2.workorder_ids.button_start()
        bo_2.workorder_ids.button_finish()
        bo_2.workorder_ids.duration = 100
        self.assertRecordValues(
            bo_2.workorder_ids,
            [
                {
                    "qty_produced": 4.0,
                    "qty_remaining": 0.0,
                    "duration_expected": 165.0,
                    "duration": 100.0,
                    "state": "done",
                }
            ],
        )
        bo_2.button_mark_done()
        self.assertRecordValues(bo_2, [{"qty_produced": 4.0, "state": "done"}])

    def test_update_workcenter_adapt_finish_date(self):
        self.workcenter_4 = self.env["mrp.workcenter"].create(
            {
                "name": "Test workcenter",
            }
        )

        self.workcenter_5 = self.env["mrp.workcenter"].create(
            {
                "name": "Test workcenter",
            }
        )

        operation = self.env["mrp.routing.workcenter"].create(
            {
                "name": "Test order",
                "workcenter_id": self.workcenter_4.id,
                "bom_id": self.bom_1.id,
                "time_cycle_manual": 30,
            }
        )

        mo = self.env["mrp.production"].create(
            {
                "product_id": self.product.id,
                "product_uom_id": self.bom_1.product_uom_id.id,
            }
        )

        dt = datetime(2024, 1, 17, 8)
        wo = self.env["mrp.workorder"].create(
            [
                {
                    "name": "Test order",
                    "workcenter_id": self.workcenter_4.id,
                    "product_uom_id": self.bom_1.product_uom_id.id,
                    "production_id": mo.id,
                    "duration_expected": 30.0,
                    "date_start": dt,
                    "operation_id": operation.id,
                }
            ]
        )
        self.assertEqual(wo.date_start, dt)
        self.assertEqual(wo.date_end, dt + timedelta(hours=0, minutes=30))

        wo.write(
            {
                "date_end": dt + timedelta(hours=1),
            }
        )
        self.assertEqual(wo.duration_expected, 60.0)

        wo.write(
            {
                "workcenter_id": self.workcenter_5.id,
            }
        )
        self.assertEqual(wo.duration_expected, 30.0)
        self.assertEqual(wo.date_start, dt)
        self.assertEqual(wo.date_end, dt + timedelta(hours=0, minutes=30))

    def test_update_qty_producing_done_MO_with_lot(self):
        tracked_product = self.env["product.product"].create(
            {
                "name": "Super Product",
                "is_storable": True,
                "tracking": "lot",
                "bom_ids": [
                    Command.create(
                        {
                            "product_qty": 2.0,
                            "bom_line_ids": [
                                Command.create(
                                    {
                                        "product_id": self.product_1.id,
                                        "product_qty": 2.0,
                                    }
                                )
                            ],
                        }
                    )
                ],
            }
        )
        mo = self.env["mrp.production"].create(
            {
                "product_id": tracked_product.id,
                "product_uom_qty": 5.0,
            }
        )
        mo.action_confirm()
        mo.action_generate_serial()
        producing_lot = mo.lot_producing_ids[:1]
        mo.button_mark_done()
        self.assertEqual(mo.state, "done")
        self.assertEqual(mo.move_finished_ids.lot_ids, producing_lot)
        self.assertEqual(
            mo.move_finished_ids.move_line_ids.mapped("lot_id"), producing_lot
        )
        mo.qty_producing = 10.0
        self.assertTrue(
            all(
                sml.lot_id == producing_lot
                for sml in mo.move_finished_ids.move_line_ids
            )
        )
        self.assertEqual(
            sum(sml.quantity for sml in mo.move_finished_ids.move_line_ids), 10.0
        )

        self.env["stock.quant"]._update_available_quantity(
            tracked_product, self.stock_location, -3, lot_id=producing_lot
        )
        mo.qty_producing = 15.0
        quants = tracked_product.stock_quant_ids.filtered(
            lambda q: q.location_id == self.stock_location
        )
        self.assertRecordValues(
            quants,
            [
                {"quantity": 12.0, "lot_id": producing_lot.id},
            ],
        )

    def test_mrp_link_new_operations(self):
        mo = self.env["mrp.production"].create(
            {
                "product_id": self.product_1.id,
                "product_qty": 1.0,
            }
        )
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

    def _prepare_report_values(
        self,
        qty_final=5,
        qty_base_1=4,
        qty_base_2=1,
        mto=False,
        bom_2=False,
        extra_component=False,
        extra_operation=False,
    ):
        grp_multi_step_rule = self.env.ref("stock.group_adv_location")
        self.env.user.write({"group_ids": [(3, grp_multi_step_rule.id)]})
        routes = [Command.link(self.route_manufacture.id)]
        if mto:
            self.route_mto.active = True
            routes.append(Command.link(self.route_mto.id))
        product_to_build = self.env["product.product"].create(
            {
                "name": "Young Tom",
                "type": "consu",
                "is_storable": True,
                "standard_price": 10.0,
                "route_ids": routes,
            }
        )
        product_to_use_1 = self.env["product.product"].create(
            {
                "name": "Botox",
                "type": "consu",
                "is_storable": True,
                "standard_price": 15.0,
                "route_ids": routes,
            }
        )
        product_to_use_2 = self.env["product.product"].create(
            {
                "name": "Old Tom",
                "type": "consu",
                "is_storable": True,
                "standard_price": 20.0,
            }
        )
        workcenter_1 = self.env["mrp.workcenter"].create(
            {
                "name": "wc1",
                "time_efficiency": 100,
                "costs_hour": 10,
            }
        )
        bom_1 = self.env["mrp.bom"].create(
            {
                "product_id": product_to_build.id,
                "product_tmpl_id": product_to_build.product_tmpl_id.id,
                "product_uom_id": self.uom_unit.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    Command.create(
                        {"product_id": product_to_use_2.id, "product_qty": qty_base_2}
                    ),
                ],
                "operation_ids": [
                    Command.create(
                        {
                            "name": "Test",
                            "workcenter_id": workcenter_1.id,
                            "time_cycle": 60,
                            "sequence": 1,
                        }
                    ),
                ],
            }
        )
        if bom_2:
            self.env["mrp.bom"].create(
                {
                    "product_id": product_to_use_2.id,
                    "product_tmpl_id": product_to_use_2.product_tmpl_id.id,
                    "product_uom_id": self.uom_unit.id,
                    "product_qty": 1.0,
                    "type": "normal",
                    "bom_line_ids": [
                        Command.create(
                            {"product_id": product_to_use_1.id, "product_qty": 1}
                        ),
                    ],
                    "operation_ids": [
                        Command.create(
                            {
                                "name": "Component assembly",
                                "workcenter_id": workcenter_1.id,
                                "time_cycle": 60,
                                "sequence": 1,
                            }
                        )
                    ],
                }
            )
        if mto:
            replenish_wizard = (
                self.env["product.replenish"]
                .with_context(
                    default_product_tmpl_id=product_to_use_2.product_tmpl_id.id
                )
                .create(
                    {
                        "product_id": product_to_use_2.id,
                        "product_tmpl_id": product_to_use_2.product_tmpl_id.id,
                        "quantity": 1,
                        "route_id": self.route_manufacture.id,
                    }
                )
            )
            replenish_wizard.action_replenish()
        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = product_to_build
        mo_form.bom_id = bom_1
        mo_form.product_qty = qty_final
        mo_form.save()
        if extra_component:
            with mo_form.move_raw_ids.new() as line:
                line.product_id = product_to_use_1
                line.product_uom_qty = 5
        if extra_operation:
            with mo_form.workorder_ids.new() as line:
                line.name = "drilling"
                line.workcenter_id = workcenter_1
                line.duration_expected = 60
        return mo_form.save()

    def _verify_report_main_decorators(
        self,
        mo,
        sum_real_cost=False,
        sum_mo_cost=False,
        comp_real_cost=False,
        comp_mo_cost=False,
        op_real_cost=False,
        op_mo_cost=False,
        extra_component=False,
        add_comp_real_cost=False,
    ):
        data = self.env["report.mrp.report_mo_overview"].get_report_values(mo.id)
        summary = data["data"]["summary"]
        components = data["data"]["components"]
        operations = data["data"]["operations"]
        self.assertEqual(summary["mo_cost_decorator"], sum_mo_cost)
        self.assertEqual(summary["real_cost_decorator"], sum_real_cost)
        component = components[0]
        self.assertEqual(component["summary"]["mo_cost_decorator"], comp_mo_cost)
        self.assertEqual(component["summary"]["real_cost_decorator"], comp_real_cost)
        if extra_component:
            component = components[1]
            self.assertEqual(
                component["summary"]["mo_cost_decorator"], add_comp_real_cost
            )
            self.assertEqual(
                component["summary"]["real_cost_decorator"], comp_real_cost
            )
        self.assertEqual(operations["summary"]["mo_cost_decorator"], op_mo_cost)
        self.assertEqual(operations["summary"]["real_cost_decorator"], op_real_cost)

    def test_mo_overview_base_decorators(self):
        mo = self._prepare_report_values()
        self._verify_report_main_decorators(mo)
        mo.action_confirm()
        self._verify_report_main_decorators(mo)
        mo.action_start()
        self._verify_report_main_decorators(
            mo, sum_mo_cost="danger", comp_mo_cost="danger", op_real_cost="success"
        )
        mo.button_mark_done()
        self._verify_report_main_decorators(mo)

    def test_mo_overview_component_bom(self):
        mo = self._prepare_report_values(bom_2=True)
        self._verify_report_main_decorators(mo)
        mo.action_confirm()
        self._verify_report_main_decorators(mo)
        mo.action_start()
        self._verify_report_main_decorators(
            mo, sum_mo_cost="danger", comp_mo_cost="danger", op_real_cost="success"
        )
        mo.button_mark_done()
        self._verify_report_main_decorators(mo)

    def test_mo_overview_component_bom_mto(self):
        mo = self._prepare_report_values(mto=True, bom_2=True)
        self._verify_report_main_decorators(mo)
        mo.action_confirm()
        self._verify_report_main_decorators(
            mo, sum_mo_cost="danger", comp_mo_cost="danger"
        )
        mo.action_start()
        self._verify_report_main_decorators(
            mo, sum_mo_cost="danger", comp_mo_cost="danger", op_real_cost="success"
        )
        mo.button_mark_done()
        self._verify_report_main_decorators(mo)

    def test_mo_overview_added_component(self):
        mo = self._prepare_report_values(extra_component=True)
        self._verify_report_main_decorators(
            mo, sum_mo_cost="danger", extra_component=True, add_comp_real_cost="danger"
        )
        mo.action_confirm()
        self._verify_report_main_decorators(
            mo, sum_mo_cost="danger", extra_component=True, add_comp_real_cost="danger"
        )
        mo.action_start()
        self._verify_report_main_decorators(
            mo,
            sum_mo_cost="danger",
            comp_mo_cost="danger",
            op_real_cost="success",
            extra_component=True,
            add_comp_real_cost="danger",
        )
        mo.button_mark_done()
        self._verify_report_main_decorators(
            mo, op_real_cost="success", sum_real_cost="success", extra_component=True
        )

    def test_mo_overview_added_operation(self):
        mo = self._prepare_report_values(extra_operation=True)
        self._verify_report_main_decorators(
            mo, sum_mo_cost="danger", op_mo_cost="danger"
        )
        mo.action_confirm()
        self._verify_report_main_decorators(
            mo, sum_mo_cost="danger", op_mo_cost="danger"
        )
        mo.action_start()
        self._verify_report_main_decorators(
            mo, sum_mo_cost="danger", comp_mo_cost="danger", op_real_cost="success"
        )
        mo.workorder_ids[0].duration = 500
        self._verify_report_main_decorators(
            mo, sum_mo_cost="danger", comp_mo_cost="danger", op_real_cost="danger"
        )
        mo.button_mark_done()
        self._verify_report_main_decorators(
            mo, op_real_cost="danger", sum_real_cost="danger"
        )

    def test_update_mo_from_bom_with_kit(self):
        kit_bom_line = self.bom_3.bom_line_ids.filtered(
            lambda line: line.product_id.is_kit
        )
        self.assertEqual(len(kit_bom_line), 1)
        kit_bom = kit_bom_line.product_id.bom_ids
        self.assertEqual(len(kit_bom.bom_line_ids), 2)
        self.assertEqual(len(self.bom_3.bom_line_ids), 3)
        mo = self.env["mrp.production"].create(
            {
                "bom_id": self.bom_3.id,
            }
        )
        mo.action_confirm()
        self.assertEqual(mo.state, "confirmed")
        self.assertEqual(len(mo.move_raw_ids), 4)
        (self.bom_3.bom_line_ids - kit_bom_line).unlink()
        self.assertEqual(self.bom_3.bom_line_ids, kit_bom_line)
        mo.action_update_bom()
        self.assertRecordValues(
            mo.move_raw_ids,
            [
                {
                    "product_id": kit_bom.bom_line_ids[0].product_id.id,
                    "product_uom_qty": 4,
                    "product_uom_id": kit_bom.bom_line_ids[0].product_id.uom_id.id,
                },
                {
                    "product_id": kit_bom.bom_line_ids[1].product_id.id,
                    "product_uom_qty": 6,
                    "product_uom_id": kit_bom.bom_line_ids[1].product_id.uom_id.id,
                },
            ],
        )
        kit_bom_line.product_qty = 3
        kit_bom.bom_line_ids[0].product_qty = 4
        mo.action_update_bom()
        self.assertRecordValues(
            mo.move_raw_ids,
            [
                {
                    "product_id": kit_bom.bom_line_ids[0].product_id.id,
                    "product_uom_qty": 12,
                    "product_uom_id": kit_bom.bom_line_ids[0].product_id.uom_id.id,
                },
                {
                    "product_id": kit_bom.bom_line_ids[1].product_id.id,
                    "product_uom_qty": 9,
                    "product_uom_id": kit_bom.bom_line_ids[1].product_id.uom_id.id,
                },
            ],
        )
        with Form(self.bom_3) as main_bom:
            with main_bom.bom_line_ids.new() as bom_line:
                bom_line.product_id = self.product_5
                bom_line.product_qty = 1
                bom_line.product_uom_id = self.uom_dozen
        mo.action_update_bom()
        self.assertRecordValues(
            mo.move_raw_ids,
            [
                {
                    "product_id": kit_bom.bom_line_ids[0].product_id.id,
                    "product_uom_qty": 60,
                    "product_uom_id": kit_bom.bom_line_ids[0].product_id.uom_id.id,
                },
                {
                    "product_id": kit_bom.bom_line_ids[1].product_id.id,
                    "product_uom_qty": 45,
                    "product_uom_id": kit_bom.bom_line_ids[1].product_id.uom_id.id,
                },
            ],
        )

    def test_update_mo_from_bom_with_kit_variants(self):
        self.env.user.group_ids += self.env.ref("product.group_product_variant")
        color_attribute = self.env["product.attribute"].create(
            {
                "name": "Variant Color",
                "value_ids": [
                    Command.create({"name": "White"}),
                    Command.create({"name": "Black"}),
                ],
            }
        )
        colors = color_attribute.value_ids
        paint_products = [
            self.env["product.product"].create({"name": f"{color.name} paint"})
            for color in colors
        ]
        kit_product = self.env["product.template"].create(
            [
                {"name": "Painted Stick"},
            ]
        )
        with Form(kit_product) as prod:
            with prod.attribute_line_ids.new() as attr_line:
                attr_line.attribute_id = color_attribute
                attr_line.value_ids = colors
        self.assertEqual(kit_product.product_variant_count, 2)
        kit_product_bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": kit_product.id,
                "product_qty": 1.0,
                "type": "phantom",
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_4.product_variant_id.id,
                            "product_qty": 1,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": paint_products[0].product_variant_id.id,
                            "product_qty": 2,
                            "bom_product_template_attribute_value_ids": kit_product.product_variant_ids[
                                0
                            ].product_template_variant_value_ids.ids,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": paint_products[1].product_variant_id.id,
                            "product_qty": 1,
                            "bom_product_template_attribute_value_ids": kit_product.product_variant_ids[
                                1
                            ].product_template_variant_value_ids.ids,
                        }
                    ),
                ],
            }
        )
        self.assertEqual(len(kit_product_bom.bom_line_ids), 3)
        mo = self.env["mrp.production"].create(
            {
                "bom_id": self.bom_4.id,
            }
        )
        mo.action_confirm()
        self.assertEqual(mo.state, "confirmed")
        self.assertEqual(len(mo.move_raw_ids), 1)
        with Form(self.bom_4) as main_bom:
            with main_bom.bom_line_ids.new() as bom_line:
                bom_line.product_id = kit_product.product_variant_ids[0]
                bom_line.product_qty = 1
        mo.action_update_bom()
        self.assertEqual(len(mo.move_raw_ids), 3)
        self.assertRecordValues(
            mo.move_raw_ids,
            [
                {"product_id": self.product_1.id, "product_qty": 1},
                {"product_id": self.product_4.id, "product_qty": 1},
                {"product_id": paint_products[0].id, "product_qty": 2},
            ],
        )
        with Form(self.bom_4) as main_bom:
            with main_bom.bom_line_ids.new() as bom_line:
                bom_line.product_id = kit_product.product_variant_ids[1]
                bom_line.product_qty = 1
        mo.action_update_bom()
        self.assertEqual(len(mo.move_raw_ids), 4)
        self.assertRecordValues(
            mo.move_raw_ids,
            [
                {"product_id": self.product_1.id, "product_qty": 1},
                {"product_id": self.product_4.id, "product_qty": 2},
                {"product_id": paint_products[0].id, "product_qty": 2},
                {"product_id": paint_products[1].id, "product_qty": 1},
            ],
        )

    @freeze_time("2024-11-26 9:00")
    def test_workorder_planning_validity_with_workcenters(self):
        week_days = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        resource_calendar = self.env["resource.calendar"].create(
            {
                "name": "Default Calendar",
                "company_id": False,
                "hours_per_day": 24,
                "attendance_ids": [
                    Command.create(
                        {
                            "name": f"{day}",
                            "dayofweek": str(week_days.index(day)),
                            "hour_from": 0,
                            "hour_to": 24,
                        }
                    )
                    for day in week_days
                ],
            }
        )
        workcenter_5 = self.env["mrp.workcenter"].create(
            {
                "name": "Workcenter no pause",
                "time_start": 0,
                "time_stop": 0,
                "time_efficiency": 100,
                "resource_calendar_id": resource_calendar.id,
            }
        )

        bom = self.env["mrp.bom"].create(
            {
                "product_id": self.product_6.id,
                "product_tmpl_id": self.product_6.product_tmpl_id.id,
                "ready_to_produce": "asap",
                "consumption": "flexible",
                "product_qty": 1.0,
                "operation_ids": [
                    Command.create(
                        {
                            "name": "Cutting Machine",
                            "workcenter_id": self.workcenter_2.id,
                            "time_cycle": 1,
                            "sequence": 1,
                            "time_cycle_manual": 360,
                        }
                    )
                ],
                "type": "normal",
            }
        )

        production_form = Form(self.env["mrp.production"])
        production_form.bom_id = bom
        production = production_form.save()

        production.action_confirm()
        production.button_plan()

        self.assertEqual(fields.Datetime.now(), production.workorder_ids.date_start)
        self.assertEqual(
            fields.Datetime.now() + timedelta(hours=7),
            production.workorder_ids.date_end,
            "The time difference should be 7 hours: 6 for the shift and 1 for the lunch pause",
        )

        production.workorder_ids.workcenter_id = workcenter_5
        self.assertEqual(fields.Datetime.now(), production.workorder_ids.date_start)
        self.assertEqual(
            fields.Datetime.now() + timedelta(hours=6),
            production.workorder_ids.date_end,
            "The time difference should be 6 hours: 6 for the shift and 0 for the lunch pause",
        )

        production.workorder_ids.workcenter_id = self.workcenter_2.id
        workcenter_5.time_efficiency = 50
        self.assertEqual(
            production.workorder_ids.date_end,
            fields.Datetime.now() + timedelta(hours=7),
            "The time difference should be 7 hours: 6 for the shift and 1 for the lunch pause",
        )
        production.workorder_ids.workcenter_id = workcenter_5
        self.assertEqual(
            production.workorder_ids.date_end,
            fields.Datetime.now() + timedelta(hours=12),
            "The time difference should be 12 hours: 6 / 0.5 for the shift and 0 for the lunch pause",
        )
        production.workorder_ids.workcenter_id = self.workcenter_2.id
        self.assertEqual(
            production.workorder_ids.date_end,
            fields.Datetime.now() + timedelta(hours=7),
            "The time difference should be 7 hours: 6 for the shift and 1 for the lunch pause",
        )

    def test_compute_tracked_time_3(self):
        self.bom_4.product_uom_id = self.uom_dozen

        self.env.user.group_ids += self.env.ref("mrp.group_mrp_routings")
        production_form = Form(self.env["mrp.production"])
        production_form.bom_id = self.bom_4
        production = production_form.save()
        production.action_confirm()
        production.button_plan()
        production_form = Form(production)
        production_form.qty_producing = 1
        production = production_form.save()
        production.workorder_ids[0].duration = 15
        production.button_mark_done()

        production_form = Form(self.env["mrp.production"])
        production_form.bom_id = self.bom_4
        production = production_form.save()
        self.assertEqual(production.workorder_ids[0].duration_expected, 15)

    def test_mo_without_resource_calendar(self):
        self.workcenter_1.resource_calendar_id = False

        mo = self.env["mrp.production"].create(
            {
                "product_id": self.product_1.id,
                "workorder_ids": [
                    Command.create(
                        {
                            "name": "Test Workorder",
                            "product_uom_id": self.product_1.uom_id.id,
                            "workcenter_id": self.workcenter_1.id,
                        }
                    )
                ],
            }
        )

        dt_start = datetime(2024, 12, 12, 8, 30)
        dt_finished = datetime(2024, 12, 13, 8, 30)

        mo.workorder_ids[0].date_start = dt_start
        mo.workorder_ids[0].date_end = dt_finished
        mo.action_confirm()
        mo.button_mark_done()

        self.assertEqual(mo.state, "done")
        self.assertEqual(mo.workorder_ids[0].duration_expected, 1440.0)

    def test_additional_transfer_creation_in_progress_state(self):
        self.warehouse_1.manufacture_steps = "pbm"

        product = self.env["product.product"].create(
            {
                "name": "Product",
                "is_storable": True,
                "bom_ids": [
                    Command.create(
                        {
                            "product_qty": 2.0,
                            "bom_line_ids": [
                                Command.create(
                                    {
                                        "product_id": self.product_1.id,
                                        "product_qty": 2.0,
                                    }
                                )
                            ],
                        }
                    )
                ],
            }
        )

        mo = self.env["mrp.production"].create(
            {
                "product_id": product.id,
                "product_uom_qty": 1.0,
            }
        )
        mo.action_confirm()

        self.assertEqual(mo.count_transfer_outgoing, 1.0)
        mo.picking_ids.button_validate()

        mo.is_locked = False
        mo_form = Form(mo)
        with mo_form.move_raw_ids.edit(0) as move:
            move.product_uom_qty = 3
        mo = mo_form.save()

        self.assertEqual(mo.count_transfer_outgoing, 2.0)
        mo.picking_ids.filtered(
            lambda picking: picking.state != "done"
        ).button_validate()

        mo.action_start()

        mo_form = Form(mo)
        with mo_form.move_raw_ids.edit(0) as move:
            move.product_uom_qty += 2
        mo = mo_form.save()

        self.assertEqual(mo.count_transfer_outgoing, 3.0)

        mo_form = Form(mo)
        with mo_form.move_raw_ids.edit(0) as move:
            move.product_uom_qty += 3
        mo = mo_form.save()

        self.assertEqual(mo.count_transfer_outgoing, 3.0)

        not_done_picking = mo.picking_ids.filtered(
            lambda picking: picking.state != "done"
        )
        self.assertEqual(not_done_picking.move_ids.product_uom_qty, 5.0)
        not_done_picking.button_validate()

        mo_form = Form(mo)
        mo_form.qty_producing = 1.0
        mo = mo_form.save()

        mo_form = Form(mo)
        with mo_form.move_raw_ids.edit(0) as move:
            move.product_uom_qty += 3
        mo = mo_form.save()

        self.assertEqual(mo.count_transfer_outgoing, 4.0)
        not_done_picking = mo.picking_ids.filtered(
            lambda picking: picking.state != "done"
        )
        self.assertEqual(not_done_picking.move_ids.product_uom_qty, 3.0)

    def test_wo_date_finished_on_done_unplanned_mo(self):
        production_form = Form(self.env["mrp.production"])
        production_form.bom_id = self.bom_4
        production = production_form.save()

        production.action_confirm()

        self.assertFalse(production.workorder_ids[0].date_end)
        self.assertFalse(production.workorder_ids[0].reservation_id)

        production.button_mark_done()

        self.assertAlmostEqual(
            production.workorder_ids[0].date_end,
            production.date_end,
            delta=timedelta(seconds=2),
        )
        self.assertAlmostEqual(
            production.workorder_ids[0].reservation_id.date_end,
            production.date_end,
            delta=timedelta(seconds=2),
        )

    def test_child_mo_after_qty_parent_mo_update(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        mto_route = warehouse.mto_pull_id.route_id
        manufacture_route = warehouse.manufacture_pull_id.route_id
        mto_route.active = True

        grandparent, parent, child = self.env["product.product"].create(
            [
                {
                    "name": n,
                    "is_storable": True,
                    "route_ids": [(6, 0, mto_route.ids + manufacture_route.ids)],
                }
                for n in ["grandparent", "parent", "child"]
            ]
        )
        component = self.env["product.product"].create(
            {
                "name": "component",
            }
        )

        self.env["mrp.bom"].create(
            [
                {
                    "product_tmpl_id": finished_product.product_tmpl_id.id,
                    "product_qty": 1,
                    "type": "normal",
                    "bom_line_ids": [
                        Command.create({"product_id": compo.id, "product_qty": 1}),
                    ],
                }
                for finished_product, compo in [
                    (grandparent, parent),
                    (parent, child),
                    (child, component),
                ]
            ]
        )
        grandparent_production = self.env["mrp.production"].create(
            {
                "bom_id": grandparent.bom_ids.id,
            }
        )
        grandparent_production.action_confirm()
        child_production, parent_production = self.env["mrp.production"].search(
            [("product_id", "in", (parent + child).ids)], order="id desc", limit=2
        )
        self.assertTrue(grandparent_production._get_children(), parent_production)
        self.assertTrue(parent_production._get_children(), child_production)
        update_quantity_wizard = self.env["change.production.qty"].create(
            {
                "mo_id": grandparent_production.id,
                "product_qty": 2,
            }
        )
        update_quantity_wizard.change_prod_qty()
        self.assertEqual(grandparent_production.move_raw_ids.product_uom_qty, 2)
        self.assertEqual(parent_production.product_qty, 2)
        self.assertEqual(child_production.product_qty, 2)

    def test_workcenter_with_resource_calendar_from_another_company(self):
        new_company = self.env["res.company"].create({"name": "new company"})
        resource_calendar = self.env["resource.calendar"].create(
            {
                "name": "Default Calendar",
                "company_id": new_company.id,
                "hours_per_day": 24,
            }
        )
        with self.assertRaises(UserError):
            (self.workcenter_1.resource_calendar_id,) = resource_calendar

    def test_workorder_without_product(self):
        mo_form = Form(self.env["mrp.production"])
        with self.assertRaises(AssertionError):
            mo_form.save()

        mo_form.product_id = self.product_1
        mo_form.product_qty = 1.0
        mo = mo_form.save()

        self.assertFalse(mo.workorder_ids)

        with mo_form.workorder_ids.new() as wo:
            wo.name = "Cutting"
            wo.workcenter_id = self.workcenter_1
        mo = mo_form.save()

        self.assertTrue(mo.workorder_ids)
        self.assertEqual(len(mo.workorder_ids), 1)
        self.assertEqual(mo.product_id, wo.product_id)

    def test_mo_modify_date_with_manuf_lead_time(self):
        finished_product = self.env["product.product"].create(
            {"name": "finished product"}
        )
        finished_bom_id = self.env["mrp.bom"].create(
            {
                "produce_delay": 17,
                "product_id": finished_product.id,
                "product_tmpl_id": finished_product.product_tmpl_id.id,
                "product_uom_id": self.uom_unit.id,
                "product_qty": 1.0,
                "bom_line_ids": [
                    Command.create({"product_id": self.product.id, "product_qty": 1})
                ],
            }
        )
        mo = self.env["mrp.production"].create({"bom_id": finished_bom_id.id})
        mo.action_confirm()
        original_start_date = mo.date_start
        with Form(mo) as production_form:
            production_form.date_start = fields.Date.today() - timedelta(days=10)
        self.assertEqual(
            mo.date_start.date(), original_start_date.date() - timedelta(days=10)
        )
        with Form(mo) as production_form:
            production_form.date_start = original_start_date
        self.assertEqual(mo.date_start, original_start_date)

    def test_json_popover_with_workorder_dependence(self):
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.product.product_tmpl_id.id,
                "product_qty": 1,
                "type": "normal",
                "allow_operation_dependencies": True,
                "operation_ids": [
                    Command.create(
                        {
                            "name": "Super op 1",
                            "workcenter_id": self.workcenter_2.id,
                            "sequence": 1,
                        }
                    ),
                    Command.create(
                        {
                            "name": "Super op 2",
                            "workcenter_id": self.workcenter_2.id,
                            "sequence": 2,
                        }
                    ),
                    Command.create(
                        {
                            "name": "Super op 3",
                            "workcenter_id": self.workcenter_2.id,
                            "sequence": 2,
                        }
                    ),
                ],
            }
        )
        bom.operation_ids[-1].blocked_by_operation_ids = bom.operation_ids[:2]
        mo = self.env["mrp.production"].create({"bom_id": bom.id})
        mo.action_confirm()
        date_start = fields.Date.today()
        date_end = fields.Date.today() + timedelta(days=5)
        wos_to_set = mo.workorder_ids - mo.workorder_ids[1]
        wos_to_set.write({"date_start": date_start, "date_end": date_end})
        self.assertTrue(mo.workorder_ids[-1].show_json_popover)

    def test_final_product_as_component(self):
        self.productA.tracking = "serial"
        serial_number = self.env["stock.lot"].create(
            {
                "name": "SAME-SN",
                "product_id": self.productA.id,
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            self.productA, self.stock_location, 1, lot_id=serial_number
        )

        with Form(self.env["mrp.production"]) as mo_form:
            mo_form.product_id = self.productA
            mo_form.product_qty = 1
            with mo_form.move_raw_ids.new() as move:
                move.product_id = self.productB
                move.product_uom_qty = 1
            mo = mo_form.save()
        self.assertTrue(mo.show_generate_bom)

        with Form(mo) as mo_form:
            with mo_form.move_raw_ids.edit(0) as move:
                move.product_id = self.productA
        self.assertFalse(mo.show_generate_bom)

        mo.action_confirm()
        self.assertEqual(mo.move_raw_ids.lot_ids, serial_number)
        mo.lot_producing_ids = serial_number
        mo.move_raw_ids.picked = True

        mo.button_mark_done()
        self.assertEqual(mo.lot_producing_ids, mo.move_raw_ids.lot_ids)
        qty_final = self.env["stock.quant"]._get_available_quantity(
            self.productA, self.stock_location, lot_id=serial_number
        )
        self.assertEqual(
            qty_final, 1, "We consumed 1 product (-1) and we produced 1 product (+1)"
        )

        with Form(self.env["mrp.production"]) as mo_form:
            mo_form.product_id = self.productA
            mo_form.product_qty = 1
            with mo_form.move_raw_ids.new() as move:
                move.product_id = self.productA
                move.product_uom_qty = 1
            mo = mo_form.save()
        mo.action_confirm()
        mo.lot_producing_ids = serial_number
        mo.move_raw_ids.picked = True
        mo.button_mark_done()
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.productA, self.stock_location, lot_id=serial_number
            ),
            1,
        )

    def test_product_qty_digits_precision(self):
        self.env["decimal.precision"].search([("name", "=", "Product Unit")]).digits = 5
        self.bom_1.product_uom_id.rounding = 0.00001
        mo = self.env["mrp.production"].create(
            {
                "bom_id": self.bom_1.id,
                "product_qty": 1.23456,
            }
        )
        mo.action_confirm()
        self.assertEqual(mo.product_qty, 1.23456)
        mo.button_mark_done()
        self.assertEqual(mo.state, "done")
        unbuild_form = Form(self.env["mrp.unbuild"])
        unbuild_form.product_id = self.bom_1.product_id
        unbuild_form.product_qty = 1.23456
        unbuild_form.mo_id = mo
        unbuild_order = unbuild_form.save()
        unbuild_order.action_unbuild()
        self.assertEqual(unbuild_order.state, "done")
        self.assertEqual(unbuild_order.product_qty, 1.23456)

    def test_generate_serial_numbers_wizard(self):
        mo, _bom, p_final, _p1, _p2 = self.generate_mo(
            tracking_final="serial", qty_final=5
        )
        res_dict = mo.action_generate_serial()
        self.assertEqual(res_dict.get("res_model"), "mrp.production.serials")
        serials_wizard = Form.from_action(self.env, res_dict)
        self.assertEqual(serials_wizard.serial_numbers, "")
        serials_wizard.lot_name = "sn#01"
        serials_wizard.lot_quantity = mo.product_uom_qty
        res_dict = serials_wizard.save().action_generate_serial_numbers()
        serials_wizard = Form.from_action(self.env, res_dict)
        self.assertEqual(
            serials_wizard.serial_numbers, "sn#01\nsn#02\nsn#03\nsn#04\nsn#05"
        )
        serials_wizard.save().action_apply()
        self.assertEqual(
            mo.lot_producing_ids.mapped("name"),
            ["sn#01", "sn#02", "sn#03", "sn#04", "sn#05"],
        )
        mo.button_mark_done()
        mo_form = Form(self.env["mrp.production"])
        p_final.serial_prefix_format = "customMRPSerial"
        mo_form.product_id = p_final
        mo_form.product_qty = 3
        mo2 = mo_form.save()
        mo2.action_confirm()
        res_dict = mo2.action_generate_serial()
        serials_wizard = Form.from_action(self.env, res_dict)
        self.assertEqual(serials_wizard.lot_name, "customMRPSerial0000001")
        serials_wizard.lot_quantity = mo2.product_uom_qty
        res_dict = serials_wizard.save().action_generate_serial_numbers()
        serials_wizard = Form.from_action(self.env, res_dict)
        serials_wizard.save().action_apply()
        self.assertEqual(
            mo2.lot_producing_ids.mapped("name"),
            [
                "customMRPSerial0000001",
                "customMRPSerial0000002",
                "customMRPSerial0000003",
            ],
        )

    def test_mark_done_multi_mo_with_different_uom(self):
        mo1, mo2 = self.env["mrp.production"].create(
            [
                {"product_id": self.product_1.id},
                {"product_id": self.product_3.id},
            ]
        )
        wo1, wo2 = self.env["mrp.workorder"].create(
            [
                {
                    "name": "Test order1",
                    "workcenter_id": self.workcenter_1.id,
                    "product_uom_id": self.product_1.uom_id.id,
                    "production_id": mo1.id,
                },
                {
                    "name": "Test order2",
                    "workcenter_id": self.workcenter_1.id,
                    "product_uom_id": self.product_3.uom_id.id,
                    "production_id": mo2.id,
                },
            ]
        )

        mos = mo1 | mo2
        mos.action_confirm()
        mos.button_mark_done()

        self.assertEqual(mo1.state, "done")
        self.assertEqual(mo2.state, "done")
        self.assertNotEqual(
            mo1.workorder_ids.product_uom_id, mo2.workorder_ids.product_uom_id
        )
        self.assertEqual(mo1.product_qty, mo2.product_qty)
        self.assertEqual(wo1.qty_produced, wo2.qty_produced)

    def test_update_component_qty_consumption(self):
        group_unlock_mo = self.env.ref("mrp.group_unlocked_by_default")
        self.env.user.group_ids += group_unlock_mo
        self.bom_1.bom_line_ids.product_id.is_storable = True
        self.env["stock.quant"]._update_available_quantity(
            self.bom_1.bom_line_ids[0].product_id, self.stock_location, 10
        )
        self.env["stock.quant"]._update_available_quantity(
            self.bom_1.bom_line_ids[1].product_id, self.stock_location, 10
        )
        mo = self.env["mrp.production"].create(
            {
                "bom_id": self.bom_1.id,
            }
        )
        mo.action_confirm()
        self.assertEqual(mo.move_raw_ids.mapped("product_uom_qty"), [2.0, 4.0])
        self.assertEqual(mo.move_raw_ids.mapped("quantity"), [2.0, 4.0])
        self.assertEqual(mo.move_raw_ids.mapped("picked"), [False, False])
        mo_form = Form(mo)
        with mo_form.move_raw_ids.edit(1) as move:
            move.product_uom_qty = 5
        mo = mo_form.save()
        self.assertEqual(mo.move_raw_ids.mapped("quantity"), [2.0, 5.0])
        self.assertEqual(mo.move_raw_ids.mapped("picked"), [False, False])
        mo.button_mark_done()
        self.assertEqual(mo.state, "done")

    def test_change_bom_and_quantity_together(self):
        mo = self.env["mrp.production"].create({"product_id": self.bom_2.product_id.id})
        self.assertFalse(mo.workorder_ids)
        self.assertEqual(len(self.bom_2.operation_ids), 1)
        mo_form = Form(mo)
        mo_form.bom_id = self.bom_2
        mo_form.product_qty = 10
        mo = mo_form.save()
        self.assertEqual(len(mo.workorder_ids), 1)


@tagged("-at_install", "post_install")
class TestTourMrpOrder(HttpCase):
    def test_mrp_order_product_catalog(self):
        product = self.env["product.product"].create(
            {
                "name": "test1",
                "is_storable": True,
            }
        )
        mo = self.env["mrp.production"].create(
            {
                "product_id": product.id,
                "product_uom_qty": 1.0,
            }
        )
        self.env["product.product"].create(
            {
                "name": "Component",
                "is_storable": True,
            }
        )
        self.assertEqual(len(mo.move_raw_ids), 0)
        url = f"/odoo/action-mrp.mrp_production_action/{mo.id}"

        self.start_tour(url, "test_mrp_production_product_catalog", login="admin")
        self.assertEqual(len(mo.move_raw_ids), 1)

    def test_manufacturing_and_byproduct_sm_to_sml_synchronization(self):
        self.env["res.config.settings"].create(
            {"group_stock_multi_locations": True}
        ).execute()
        self.env["res.config.settings"].create({"group_mrp_byproducts": True}).execute()

        location = self.env.ref("stock.stock_location_stock")
        product = self.env["product.product"]
        product_finish = product.create(
            {
                "name": "product1",
                "is_storable": True,
                "tracking": "none",
            }
        )
        component = product.create(
            {
                "name": "product2",
                "is_storable": True,
                "tracking": "none",
            }
        )
        by_product = product.create(
            {
                "name": "product2",
                "is_storable": True,
                "tracking": "none",
            }
        )

        self.env["stock.quant"]._update_available_quantity(component, location, 50)

        bom = self.env["mrp.bom"].create(
            {
                "product_id": product_finish.id,
                "product_tmpl_id": product_finish.product_tmpl_id.id,
                "product_qty": 1,
                "type": "normal",
                "bom_line_ids": [
                    Command.create({"product_id": component.id, "product_qty": 5}),
                ],
                "byproduct_ids": [
                    Command.create(
                        {
                            "product_id": by_product.id,
                            "product_qty": 2,
                            "product_uom_id": by_product.uom_id.id,
                        }
                    ),
                ],
            }
        )

        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = product_finish
        mo_form.product_qty = 1
        mo_form.bom_id = bom
        mo = mo_form.save()

        action_id = self.env.ref("mrp.menu_mrp_production_action").action
        url = f"/odoo/action-{action_id.id}/{mo.id}"
        self.start_tour(
            url,
            "test_manufacturing_and_byproduct_sm_to_sml_synchronization",
            login="admin",
            timeout=100,
        )
        self.assertEqual(mo.move_raw_ids.quantity, 7)
        self.assertEqual(mo.move_raw_ids.move_line_ids.quantity, 7)
        self.assertEqual(mo.move_byproduct_ids.quantity, 7)
        self.assertEqual(len(mo.move_byproduct_ids.move_line_ids), 1)

    def test_mrp_multi_step_draft_mo_creates_component_transfer(self):
        self.env.user.group_ids += self.env.ref("stock.group_stock_multi_locations")
        warehouse = self.env.ref("stock.warehouse0")
        warehouse.manufacture_steps = "pbm"
        component, final_product = self.env["product.product"].create(
            [
                {
                    "name": name,
                    "is_storable": True,
                }
                for name in ["Wooden Leg", "Table"]
            ]
        )
        mo = self.env["mrp.production"].create(
            {
                "product_id": final_product.id,
                "product_uom_qty": 1.0,
                "warehouse_id": warehouse.id,
            }
        )
        self.assertEqual(len(mo.move_raw_ids), 0)
        self.assertEqual(mo.state, "draft")

        self.authenticate("admin", "admin")
        self.opener.post(
            url=self.base_url() + "/product/catalog/update_order_line_info",
            json={
                "params": {
                    "res_model": "mrp.production",
                    "order_id": mo.id,
                    "product_id": component.id,
                    "quantity": 2,
                    "child_field": "move_raw_ids",
                },
            },
        )

        self.assertEqual(len(mo.move_raw_ids), 1)

        mo.action_confirm()
        component_transfer = self.env["stock.move"].search(
            [
                ("product_id", "=", component.id),
                ("location_dest_id", "=", warehouse.pbm_loc_id.id),
            ]
        )
        self.assertEqual(component_transfer.product_uom_qty, 2)
