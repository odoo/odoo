# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from .common import TestCommonSaleTimesheet


@tagged('-at_install', 'post_install')
class TestEditSoLineTimesheet(TestCommonSaleTimesheet):
    def setUp(self):
        super().setUp()
        self.task_rate_task = self.env['project.task'].create({
            'name': 'Task',
            'project_id': self.project_task_rate.id,
            'sale_line_id': self.so.order_line[0].id,
        })

    def test_sol_no_change_if_edited(self):
        """ Check if a sol manually edited, does not change with a change of sol in the task.

            Test Case:
            =========
            1) create some timesheets on this task,
            2) edit a SOL of a timesheet in this task,
            3) check if the edited SOL has the one selected and is not the one in the task,
            4) change the sol on the task,
            5) check if the timesheet in which the sol has manually edited, does not change but the another ones are the case.
        """
        # 1) create some timesheets on this task
        timesheet = self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': self.project_task_rate.id,
            'task_id': self.task_rate_task.id,
            'unit_amount': 5,
            'employee_id': self.employee_manager.id
        })
        timesheet._compute_so_line()
        edited_timesheet = timesheet.copy()
        self.assertTrue(timesheet.so_line == edited_timesheet.so_line == self.task_rate_task.sale_line_id, "SOL in timesheet should be the same than the one in the task.")
        self.assertEqual(timesheet.unit_amount + edited_timesheet.unit_amount, self.task_rate_task.sale_line_id.qty_delivered, "The quantity timesheeted should be increased the quantity delivered in the linked SOL.")

        # 2) edit a SOL of a timesheet in this task
        # Remark, we simulate the action done in the task form view
        edited_timesheet.write({
            "is_so_line_edited": True,
            "so_line": self.so.order_line[1].id,
        })
        self.so.order_line._compute_qty_delivered()

        # 3) check if the edited SOL has the one selected and is not the one in the task
        self.assertNotEqual(edited_timesheet.so_line, self.task_rate_task.sale_line_id, "SOL in timesheet should be different than the one in the task.")
        self.assertEqual(edited_timesheet.so_line, self.so.order_line[1], "SOL in timesheet is the one selected when we manually edit in the timesheet")
        self.assertEqual(self.task_rate_task.sale_line_id.qty_delivered, timesheet.unit_amount, "The quantity delivered should be the quantity defined in the first timesheet of the task since the so_line in the second timesheet has manually been changed.")

        # 4) change the sol on the task
        self.task_rate_task.update({
            'sale_line_id': self.so.order_line[-1].id,
        })
        timesheet._compute_so_line()
        edited_timesheet._compute_so_line()
        self.so.order_line._compute_qty_delivered()

        # 5) check if the timesheet in which the sol has manually edited, does not change but the another ones are the case.
        self.assertEqual(timesheet.so_line, self.task_rate_task.sale_line_id, "SOL in timesheet should be the same than the one in the task.")
        self.assertNotEqual(edited_timesheet.so_line, self.task_rate_task.sale_line_id, "SOL in timesheet which is manually edited should be different than the one in the task.")
        self.assertEqual(edited_timesheet.so_line, self.so.order_line[1], "SOL in timesheet should still be the same")
