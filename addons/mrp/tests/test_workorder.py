# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime

from odoo import Command
from odoo.addons.mrp.tests.common import TestMrpCommon
from odoo.tests import Form


class TestWorkorder(TestMrpCommon):

    def test_workorder_move_start_preserves_duration(self):
        """Moving only the start date of a planned work order (e.g. through the
        gantt edit dialog) must keep its expected duration and shift the end date,
        rather than recomputing - and drifting - the duration from the new dates.

        Changing the start date triggers _onchange_date_start, which recomputes the
        end date from start + duration. That cascades into _onchange_date_finished,
        which used to recompute the duration from the dates. plan_hours and
        get_work_duration_data are not exact inverses when the stored (UTC) dates do
        not line up with the calendar working hours, so the duration drifted (e.g.
        180 -> 270 minutes). A non-UTC timezone is required to expose the drift: at
        UTC the round trip is exact and the bug does not reproduce.
        """
        self.env.company.tz = 'Europe/Brussels'
        self.env.user.tz = 'Europe/Brussels'
        # Continuous 8:00-16:00 calendar with no overhead.
        calendar = self.env['resource.calendar'].create({
            'name': 'Continuous 8-16',
            'attendance_ids': [Command.create({
                'dayofweek': str(day), 'hour_from': 8.0, 'hour_to': 16.0,
                'day_period': 'morning',
            }) for day in range(5)],
        })
        self.workcenter_1.write({
            'time_efficiency': 100, 'time_start': 0, 'time_stop': 0,
            'resource_calendar_id': calendar.id,
        })
        self.workcenter_1.capacity_ids.write({'time_start': 0, 'time_stop': 0})
        mo = self.env['mrp.production'].create({
            'product_id': self.bom_2.product_id.id,
            'bom_id': self.bom_2.id,
            'product_qty': 1,
        })
        mo.action_confirm()
        wo = mo.workorder_ids[0]
        wo.duration_expected = 180.0
        wo.with_context(bypass_duration_calculation=True).write({
            'date_start': datetime(2025, 6, 2, 8, 0, 0),
            'date_finished': datetime(2025, 6, 2, 11, 0, 0),
        })
        # Move the start to a time that is not on the opening hour through the form.
        with Form(wo, view='mrp.mrp_production_workorder_form_view_inherit') as wo_form:
            wo_form.date_start = datetime(2025, 6, 2, 11, 30, 0)
        self.assertEqual(wo.duration_expected, 180.0,
                         "Moving the start date should not change the work order duration")
        self.assertEqual(wo.date_finished, wo._calculate_date_finished(),
                         "End date should follow the start date for the same duration")

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
