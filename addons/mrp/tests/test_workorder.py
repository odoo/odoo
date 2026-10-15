# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime

from odoo import Command
from odoo.addons.mrp.tests.common import TestMrpCommon
from odoo.tests import Form, users
from odoo.exceptions import UserError


class TestWorkorder(TestMrpCommon):
    _test_user_groups = (
        'product.group_product_manager',  # FIXME: use base.group_user
        'mrp.group_mrp_manager',
        'mrp.group_mrp_routings',  # view visibility (duration/workorder fields) granted to cls.env.user in Common
        'mrp.group_mrp_byproducts',  # view visibility (byproducts) granted to mrp users in Common
        'stock.group_stock_manager',  # setup: warehouse/route/rule/orderpoint/location/picking_type config in test bodies
        'uom.group_uom',  # view visibility (uom_id) granted to cls.env.user in Common
    )

    _test_user_name = 'Test Product Manager'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        grp_workorder = cls.env.ref('mrp.group_mrp_routings')
        cls.env.user.write({'group_ids': [(4, grp_workorder.id)]})
        cls.workcenter = cls.env['mrp.workcenter'].create({
            'name': 'Nuclear Workcenter',
            'employee_ids': [
                Command.create({
                    'name': 'Qian Xuesen',
                    'pin': '1234'}),
                Command.create({
                    'name': 'Yu Min',
                    'pin': '5678'})]})
        cls.employee_1 = cls.workcenter.employee_ids[0]
        cls.employee_2 = cls.workcenter.employee_ids[1]
        cls.final_product = cls.env['product.product'].create({
            'name': 'DF-41',
            'is_storable': True,
        })
        cls.component = cls.env['product.product'].create({
            'name': 'RBCC engine',
            'is_storable': True,
        })
        cls.bom = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.final_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'operation_ids': [
                Command.create({
                    'name': 'fuel injection',
                    'workcenter_id': cls.workcenter.id,
                    'time_cycle': 12,
                    'sequence': 1})]})
        cls.env['mrp.bom.line'].create({
            'product_id': cls.component.id,
            'product_qty': 1.0,
            'bom_id': cls.bom.id})
        mo_form = Form(cls.env['mrp.production'])
        mo_form.product_id = cls.final_product
        mo_form.bom_id = cls.bom
        mo_form.product_qty = 1
        cls.mo = mo_form.save()

        cls.user_without_hr_right = cls.env['res.users'].create({
            'name': 'Test without hr right',
            'login': 'test_without_hr_right',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('mrp.group_mrp_manager').id,
                cls.env.ref('mrp.group_mrp_routings').id
            ])],
        })

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
        self.env.company.sudo().tz = 'Europe/Brussels'  # UTC+2
        # Continuous 8:00-16:00 calendar with no overhead.
        calendar = self.env['resource.calendar'].sudo().create({
            'name': 'Continuous 8-16',
            'attendance_ids': [Command.create({
                'dayofweek': str(day), 'hour_from': 8.0, 'hour_to': 16.0,
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
            'date_start': datetime(2025, 6, 2, 8, 0, 0),  # 10:00 local
            'date_finished': datetime(2025, 6, 2, 11, 0, 0),  # 13:00 local
        })
        # Move the start to a time that is not on the opening hour through the form.
        with Form(wo) as wo_form:
            wo_form.date_start = datetime(2025, 6, 2, 11, 30, 0)  # 13:30 local
        self.assertEqual(wo.duration_expected, 180.0,
                         "Moving the start date should not change the work order duration")
        self.assertEqual(wo.date_finished, datetime(2025, 6, 3, 6, 30, 0),  # 8:30 local
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

    def test_start_workorder_keeps_mo_planned(self):
        """Starting a work order on a planned MO with several work orders must not
        unplan the MO.
        """
        mo = self.env['mrp.production'].create({'bom_id': self.bom_3.id})
        mo.action_confirm()
        mo.button_plan()
        self.assertTrue(mo.is_planned)

        mo.workorder_ids.sorted('date_start')[0].button_start()
        self.assertTrue(mo.is_planned, "Starting a work order must not unplan the MO")

    def test_duplicate_mo_workorder_name_not_suffixed(self):
        """
        Duplicating a manufacturing order should keep its workorders' names
        as-is: the generic "(copy)" suffix applied by default to 'name'
        fields on copy should not apply to workorders.
        """
        self.bom_1.write({
            'operation_ids': [
                Command.create({'name': 'Cutting Machine', 'workcenter_id': self.workcenter_1.id, 'sequence': 1}),
                Command.create({'name': 'Weld Machine', 'workcenter_id': self.workcenter_1.id, 'sequence': 2}),
            ],
        })
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom_1
        mo_form.product_qty = 10
        mo = mo_form.save()
        mo.action_confirm()
        original_names = mo.workorder_ids.mapped('name')
        self.assertEqual(original_names, ['Cutting Machine', 'Weld Machine'])

        mo_copy = mo.copy()
        self.assertEqual(mo_copy.workorder_ids.mapped('name'), original_names)

    def test_allowed_employees_restriction(self):
        """
        Ensure that the employee linked to the current user cannot start a work order
        in a work center where this employee is not authorized to work.
        """
        self.workcenter.employee_ids = self.employee_1
        self.assertEqual(self.mo.workorder_ids.workcenter_id, self.workcenter)
        self.env.user.employee_id = self.employee_2
        with self.assertRaises(UserError):
            self.mo.workorder_ids.button_start()
        self.env.user.employee_id = self.employee_1
        self.mo.workorder_ids.button_start()
        self.assertEqual(self.mo.workorder_ids.state, 'progress')

    def test_assigned_employee_workorder_productivity(self):
        """Ensure that the employee assigned to the work order is the one
        linked to productivity when validating the MO.
        """
        self.env.user.employee_ids = [Command.link(self.employee_2.id)]
        self.mo.workorder_ids.employee_assigned_ids = self.employee_1
        self.mo.button_mark_done()
        self.assertTrue(self.mo.workorder_ids)
        self.assertEqual(self.mo.state, 'done')
        self.assertEqual(self.mo.workorder_ids.time_ids.employee_id, self.employee_1)

    def test_estimated_employee_cost_valuation(self):
        """ Test that operations with 'estimated' cost correctly compute the employee cost.
        The cost should be equal to workcenter.employee_costs_hour * workorder.duration_expected. """
        self.bom.operation_ids.cost_mode = 'estimated'
        self.workcenter.costs_hour = 33
        self.workcenter.employee_costs_hour = 60
        self.mo.action_confirm()

        self.mo.workorder_ids.duration = 10
        self.assertEqual(self.mo.workorder_ids._cal_cost(), 93.0)

        # Cost should stay the same for a done MO if nothing else is changed
        self.mo.button_mark_done()
        self.bom.operation_ids.cost_mode = 'actual'
        self.workcenter.employee_costs_hour = 99
        self.assertEqual(self.mo.workorder_ids._cal_cost(), 93.0)

    @users('test_without_hr_right')
    def test_create_workorder_without_hr_right(self):
        self.env['mrp.workorder'].create({
            'name': 'Test work order',
            'workcenter_id': self.workcenter.id,
            'production_id': self.mo.id,
            'employee_assigned_ids': self.employee_1.ids,
        })

    @users('test_without_hr_right')
    def test_create_manufacturing_order_without_hr_right(self):
        production = self.env['mrp.production'].create({
            'bom_id': self.bom.id,
            'product_qty': 1,
            'workorder_ids': [Command.create({
                'name': 'Test work order',
                'workcenter_id': self.workcenter.id,
                'production_id': self.mo.id,
                'employee_assigned_ids': self.employee_1.ids,
                'employee_ids': self.employee_1.ids,
            })],
        })
        # the access cache would otherwise keep the employee marked as readable
        self.env.transaction.invalidate_access_cache()
        self.assertEqual(production.employee_ids, self.employee_1)
        allowed_employees = (self.employee_1 | self.employee_2)
        self.assertRecordValues(production.workorder_ids, [{
            'employee_assigned_ids': self.employee_1.ids,
            'employee_ids': self.employee_1.ids,
            'allowed_employees': allowed_employees.ids,
            'all_employees_allowed': False,
        }])
        self.assertEqual(production.workorder_ids.workcenter_id.employee_ids, allowed_employees)

    @users('test_without_hr_right')
    def test_create_workcenter_without_hr_right(self):
        self.env['mrp.workcenter'].create({
            'name': 'Test Workcenter',
            'time_start': 10,
            'time_stop': 5,
            'employee_ids': self.employee_1.ids,
            'time_efficiency': 80,
        })

    def test_button_pending_only_current_employee(self):
        """
        Ensure that clicking on Pending stops only the current employee productivity
        and does not affect other employees working on the same workorder.
        """
        self.mo.action_confirm()
        wo = self.mo.workorder_ids

        # Create a second user linked to employee_2
        user_2 = self.env['res.users'].sudo().create({
            'name': 'Second User',
            'login': 'second_user',
            'email': 'second_user@test.com',
            'group_ids': [Command.set([self.env.ref('mrp.group_mrp_user').id])],
            'employee_id': self.employee_2.id,
        })
        # Start workorder with employee 1
        self.env.user.employee_id = self.employee_1
        wo.start_employee(self.employee_1.id)
        # Start workorder with employee 2 (second user)
        wo.with_user(user_2).start_employee(self.employee_2.id)
        # Ensure both employees are working
        self.assertEqual(len(wo.time_ids), 2)
        self.assertFalse(any(wo.time_ids.mapped('date_end')))
        # Employee 1 clicks on Pending
        wo.button_pending()

        time_emp_1 = wo.time_ids.filtered(lambda t: t.employee_id == self.employee_1)
        time_emp_2 = wo.time_ids.filtered(lambda t: t.employee_id == self.employee_2)
        # Employee 1 must be stopped
        self.assertTrue(time_emp_1.date_end)
        # Employee 2 must still be running
        self.assertFalse(time_emp_2.date_end)
