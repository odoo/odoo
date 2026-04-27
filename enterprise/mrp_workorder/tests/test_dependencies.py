# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.mrp_workorder.tests.common import TestMrpWorkorderCommon
from odoo.tests import Form


class TestWorkOrderDependencies(TestMrpWorkorderCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.wkct1 = cls.env['mrp.workcenter'].create({
            'name': 'Workcenter#1',
        })
        cls.wkct2 = cls.env['mrp.workcenter'].create({
            'name': 'Workcenter#2',
        })
        cls.wkct3 = cls.env['mrp.workcenter'].create({
            'name': 'Workcenter#3',
        })
        cls.finished = cls.env['product.product'].create({
            'name': 'Finished Product',
            'is_storable': True,
        })
        cls.component1 = cls.env['product.product'].create({
            'name': 'Component#1',
            'is_storable': True,
        })
        cls.component2 = cls.env['product.product'].create({
            'name': 'Component#2',
            'is_storable': True,
        })
        cls.bom = cls.env['mrp.bom'].create({
            'product_id': cls.finished.id,
            'product_tmpl_id': cls.finished.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [
                Command.create({'product_id': cls.component1.id, 'product_qty': 1}),
                Command.create({'product_id': cls.component2.id, 'product_qty': 2})
            ],
            'operation_ids': [
                Command.create({'name': 'Operation#A', 'workcenter_id': cls.wkct1.id}),
                Command.create({'name': 'Operation#B', 'workcenter_id': cls.wkct2.id}),
                Command.create({'name': 'Operation#C', 'workcenter_id': cls.wkct3.id}),
            ],
            'allow_operation_dependencies': True,
        })
        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        cls.env['stock.quant']._update_available_quantity(cls.component1, cls.stock_location, 100)
        cls.env['stock.quant']._update_available_quantity(cls.component2, cls.stock_location, 100)

    def test_parallel_workorders(self):
        """ Test parallel workorders: bom allowing operation dependencies without any dependency."""

        # Make MO
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.finished
        mo_form.product_qty = 2.0
        mo = mo_form.save()
        mo.action_confirm()

        # Check workorders initial state
        self.assertEqual(mo.workorder_ids[0].state, 'ready', "All workorders should be ready.")
        self.assertEqual(mo.workorder_ids[1].state, 'ready', "All workorders should be ready.")
        self.assertEqual(mo.workorder_ids[2].state, 'ready', "All workorders should be ready.")

    def test_stepped_workorders(self):
        """ Test step-by-step workorders: bom operations are interdependent."""

        # Make 1st workorder depend on 3rd
        self.bom.operation_ids[0].blocked_by_operation_ids = [Command.link(self.bom.operation_ids[2].id)]

        # Make MO
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.finished
        mo_form.product_qty = 2.0
        mo = mo_form.save()
        mo.action_confirm()
        wo1, wo2, wo3 = mo.workorder_ids
        # Check workorders initial state
        self.assertEqual(wo1.state, 'pending', "Workorder for Operation-A should be Waiting for another WO (the 3rd).")
        self.assertEqual(wo2.state, 'ready', "Workorder for Operation-B should be ready.")
        self.assertEqual(wo3.state, 'ready', "Workorder for Operation-C should be ready.")
        mo.button_plan()
        # Mark 1st initial WO as done
        wo2.button_start()
        wo2.qty_producing = 2
        wo2.record_production()
        # Check 3rd WO (not dependent on 1st)
        self.assertEqual(wo1.state, 'pending', "Workorder for Operation-A should STILL be Waiting for another WO (the 3rd).")
        # Mark 2nd initial WO as done
        wo3.button_start()
        wo3.qty_producing = 2
        wo3.record_production()
        # Check dependent WO
        self.assertEqual(wo1.state, 'ready', "Workorder for Operation-A can be started, as its predecessors are now done.")

    def test_propagate_quantity_on_backorders_with_stepped_workorders(self):
        """Create a MO for a product with several work orders.
        Produce different quantities to test quantity propagation and workorder cancellation.
        -> Reproduce test_propagate_quantity_on_backorders on stepped workorders
        """

        # Make 1st workorder depend on 3rd
        self.bom.operation_ids[0].blocked_by_operation_ids = [Command.link(self.bom.operation_ids[2].id)]

        # Make MO for 20 products

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.finished
        mo_form.product_qty = 20
        mo = mo_form.save()

        self.assertEqual(mo.state, 'draft')
        mo.action_confirm()

        wo_1, wo_2, wo_3 = mo.workorder_ids
        self.assertEqual(mo.state, 'confirmed')
        self.assertEqual(wo_1.state, 'pending')
        self.assertEqual(wo_2.state, 'ready')
        self.assertEqual(wo_3.state, 'ready')

        # produce 20 / 10 / 5 on workorders 2 / 3 / 1, mark as done & create backorder
        # mo closed with 5 produced
        # backorder for 15 created with
        # - wo5 'cancel' (fully processed)
        # - wo6 'ready' for 10
        # - wo4 'pending' for 15

        wo_2.button_start()
        wo_2.qty_producing = 20
        self.assertEqual(mo.state, 'progress')
        wo_2.button_finish()

        wo_3.button_start()
        wo_3.qty_producing = 10
        wo_3.button_finish()

        wo_1.button_start()
        wo_1.qty_producing = 5
        wo_1.button_finish()

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

        self.assertEqual(wo_4.state, 'pending')
        self.assertEqual(wo_5.state, 'cancel')
        self.assertEqual(wo_6.state, 'ready')

        # produce 10 / 5 on workorders 6 / 4, mark as done & create backorder
        # mo closed with 5 produced
        # backorder for 10 created with
        # - wo8 'cancel' (already fully processed)
        # - wo9 'cancel' (fully processed)
        # - wo7 'ready' for 10

        wo_6.button_start()
        wo_6.qty_producing = 10
        self.assertEqual(mo_2.state, 'progress')
        wo_6.button_finish()

        wo_4.button_start()
        wo_4.qty_producing = 5
        wo_4.button_finish()

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

        self.assertEqual(wo_7.state, 'ready')
        self.assertEqual(wo_8.state, 'cancel')
        self.assertEqual(wo_9.state, 'cancel')

        # produce 10 on workorder 7 and finish work

        wo_7.button_start()
        wo_7.qty_producing = 10
        self.assertEqual(mo_3.state, 'progress')
        wo_7.button_finish()

        self.assertEqual(mo_3.state, 'to_close')
        mo_3.button_mark_done()
        self.assertEqual(mo_3.state, 'done')

    def test_allow_operation_dependency_with_deleted_workorder(self):
        """
        BoM with dependencies between operations to ensure an order: OP01, OP02
        and OP03. The user creates a MO based on that BoM and removes WO02. He
        should still be able to confirm and process the MO.
        """
        self.bom.operation_ids[1].blocked_by_operation_ids = [Command.link(self.bom.operation_ids[0].id)]
        self.bom.operation_ids[2].blocked_by_operation_ids = [Command.link(self.bom.operation_ids[1].id)]

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.finished
        mo_form.product_qty = 20
        mo = mo_form.save()

        self.assertEqual(mo.state, 'draft')

        wo_1, wo_2, wo_3 = mo.workorder_ids

        wo_2.unlink()
        mo.action_confirm()

        self.assertEqual(wo_1.state, 'ready')
        self.assertEqual(wo_3.state, 'ready')

        wo_1.button_start()
        wo_1.button_finish()

        wo_3.button_start()
        wo_3.button_finish()

        self.assertEqual(mo.state, 'to_close')
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')
        self.assertEqual(mo.workorder_ids.operation_id, self.bom.operation_ids[0] | self.bom.operation_ids[2])
