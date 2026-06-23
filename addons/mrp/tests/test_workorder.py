# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.addons.mrp.tests.common import TestMrpCommon
from odoo.tests import Form


class TestWorkorder(TestMrpCommon):

    def test_workorder_operation_assignment(self):
        """Test that moves aren't automatically assigned to the last workorder
        when the quantity to produce (`product_qty`) is changed.
        """
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom_2
        mo = mo_form.save()
        mo.action_confirm()
        wiz = self.env['change.production.qty'].create({
            'mo_id': mo.id,
            'product_qty': 5
        })
        wiz.change_prod_qty()
        self.assertFalse(mo.workorder_ids[-1].move_raw_ids)

    def test_workorder_in_progress_expected_duration(self):
        """Test that in progress workorder duration are correctly adapted according to the
        quantity to produce (`product_qty`).
        """
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom_4
        mo = mo_form.save()
        mo.action_confirm()
        wo = mo.workorder_ids[0]
        initial_duration = wo.duration_expected
        wo.button_start()
        wiz = self.env['change.production.qty'].create({
            'mo_id': mo.id,
            'product_qty': 2
        })
        wiz.change_prod_qty()
        self.assertEqual(wo.duration_expected, wiz.product_qty * initial_duration)

    def test_planning_respects_operation_dependencies(self):
        """ Test that each workorder must start after all its blockers when button_plan is called.
            opA
            ├── opB  (leaf)
            └── opC
                └── opD  (leaf)
        """
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product_6.product_tmpl_id.id,
            'uom_id': self.product_6.uom_id.id,
            'product_qty': 1.0,
            'allow_operation_dependencies': True,
            'operation_ids': [
                Command.create({'name': 'opA', 'workcenter_id': self.workcenter_2.id, 'time_cycle': 60, 'sequence': 1}),
                Command.create({'name': 'opB', 'workcenter_id': self.workcenter_2.id, 'time_cycle': 60, 'sequence': 2}),
                Command.create({'name': 'opC', 'workcenter_id': self.workcenter_2.id, 'time_cycle': 60, 'sequence': 3}),
                Command.create({'name': 'opD', 'workcenter_id': self.workcenter_2.id, 'time_cycle': 60, 'sequence': 4}),
            ],
            'bom_line_ids': [Command.create({'product_id': self.product_1.id, 'product_qty': 1})],
        })
        opA, opB, opC, opD = bom.operation_ids.sorted('sequence')
        opB.blocked_by_operation_ids = [Command.link(opA.id)]
        opC.blocked_by_operation_ids = [Command.link(opA.id)]
        opD.blocked_by_operation_ids = [Command.link(opC.id)]

        mo = self.env['mrp.production'].create({
            'bom_id': bom.id,
        })
        mo.action_confirm()
        mo.button_plan()

        # Ensure workorders are scheduled respecting dependencies by checking
        # the order of workorders when sorted by `date_start`.
        wo_sorted = mo.workorder_ids.sorted('date_start')
        self.assertRecordValues(
            wo_sorted,
            [
                {'operation_id': opA.id},
                {'operation_id': opB.id},
                {'operation_id': opC.id},
                {'operation_id': opD.id},
            ],
            field_names=['operation_id'],
        )
