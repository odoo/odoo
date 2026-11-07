# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from .common import TestCommonSaleTimesheet


@tagged('-at_install', 'post_install')
class TestSoLineDeterminedInTimesheet(TestCommonSaleTimesheet):

    def test_sol_determined_when_project_is_task_rate(self):
        """ Test the sol give to the timesheet when the pricing type in the project is task rate

            Test Case:
            =========
            1) Create Task in project with pricing_type='task_rate',
            2) Compute the SOL for the task and check if we have the one containing the prepaid service product,
            3) Create timesheet and check if the SOL in this timesheet is the one in the task,
            4) Since the remaining hours of the prepaid service is equals to 0 hour,
                when we create a new task, the SOL in this one should be equal to False
            5) Change the SOL in the task and see if the SOL in the timesheet also changes.
        """
        # 1) Create Task in project with pricing_type='task_rate'
        task = self.env['project.task'].create({
            'name': 'Task',
            'project_id': self.project_task_rate.id,
        })

        # 2) Compute the SOL for the task and check if we have the one containing the prepaid service product
        # task._compute_sale_line()
        self.assertEqual(task.sale_line_id, self.so.order_line[-1], "The SOL in the task should be the one containing the prepaid service product.")
        self.assertTrue(all(sol.qty_delivered == 0 for sol in self.so.order_line), "The quantity delivered should be equal to 0 because we have no timesheet for each SOL containing in the SO.")

        # 3) Create timesheet and check if the SOL in this timesheet is the one in the task
        timesheet = self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'unit_amount': 2,
            'employee_id': self.employee_manager.id,
            'project_id': self.project_task_rate.id,
            'task_id': task.id,
        })
        self.assertEqual(timesheet.so_line, task.sale_line_id, "The SOL in the timesheet should be the same than the one in the task.")
        self.assertEqual(self.so.order_line[-1].qty_delivered, 2, "The quantity delivered should be equal to 2.")
        self.assertEqual(task.remaining_hours_so, 0, "The remaining hours on the SOL containing the prepaid service product should be equals to 0.")

        # 4) Since the remaining hours of the prepaid service product is equals to 0 hour, when we create a new task, the SOL in this one should be equals to False
        task2 = self.env['project.task'].create({
            'name': 'Task 2',
            'project_id': self.project_task_rate.id,
        })
        self.assertFalse(task2.sale_line_id, "The SOL in this task should be equal to False")

        # 5) Change the SOL in the task and see if the SOL in the timesheet also changes.
        task.update({'sale_line_id': self.so.order_line[0].id})
        self.assertEqual(timesheet.so_line, task.sale_line_id, "The SOL in the timesheet should also change and be the same than the one in the task.")

    def test_sol_determined_when_project_is_project_rate(self):
        """ Test the sol give to the timesheet when the pricing type in the project is project rate

            Test Case:
            =========
            1) Define a SO and SOL in the project,
            2) Create task and check if the SOL is the one defined in the project,
            3) Create timesheet in the task and check if the SOL in the timesheet is the one in the task,
            4) Change the SOL in the task and check if the SOL in the timesheet has also changed.
        """
        # 1) Define a SO and SOL in the project
        self.project_project_rate = self.project_task_rate.copy({
            'name': 'Project with pricing_type="project_rate"',
            'sale_line_id': self.so.order_line[0].id,
        })

        # 2) Create task and check if the SOL is the one defined in the project
        task = self.env['project.task'].create({
            'name': 'Task',
            'project_id': self.project_project_rate.id,
        })
        self.assertEqual(task.sale_line_id, self.so.order_line[0], "The SOL in the task should be the one containing the prepaid service product.")
        self.assertTrue(all(sol.qty_delivered == 0 for sol in self.so.order_line), "The quantity delivered should be equal to 0 because we have no timesheet for each SOL containing in the SO.")

        # 3) Create timesheet in the task and check if the SOL in the timesheet is the one in the task
        timesheet = self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'unit_amount': 1,
            'employee_id': self.employee_manager.id,
            'project_id': self.project_project_rate.id,
            'task_id': task.id,
        })
        self.assertTrue(timesheet.so_line == task.sale_line_id == self.so.order_line[0], "The SOL in the timesheet should be the same than the one in the task.")
        self.assertEqual(self.so.order_line[0].qty_delivered, 1, "The quantity delivered should be equal to 1.")

        # 4) Change the SOL in the task and check if the SOL in the timesheet has also changed
        task.update({'sale_line_id': self.so.order_line[1].id})
        self.assertTrue(timesheet.so_line == task.sale_line_id == self.so.order_line[1], "The SOL in the timesheet should also change and be the same than the one in the task.")

    def test_sol_determined_when_project_is_employee_rate(self):
        """ Test the sol give to the timesheet when the pricing type in the project is employee rate

            Test Case:
            =========
            1) Define a SO, SOL mapping for an employee in the project,
            2) Create task and check if the SOL is the one defined in the project,
            3) Create timesheet in the task and check if the SOL in the timesheet is the one in the task,
            4) Create timesheet in the task for the employee defined in the mapping and check if the SOL in this timesheet is the one defined in the mapping,
            5) Change the SOL in the task and check if only the SOL in the timesheet which does not concerne about the mapping changes,
            6) Change the SOL in the mapping and check if the timesheet conserne by the mapping has its SOL has been changed too.
        """
        # 1) Define a SO, SOL and mapping for an employee in the project,
        self.project_employee_rate = self.project_task_rate.copy({
            'name': 'Project with pricing_type="employee_rate"',
            'sale_line_id': self.so.order_line[0].id,
            'sale_line_employee_ids': [(0, 0, {
                'employee_id': self.employee_user.id,
                'sale_line_id': self.so.order_line[1].id,
            })]
        })
        mapping = self.project_employee_rate.sale_line_employee_ids

        # 2) Create task and check if the SOL is the one defined in the project,
        task = self.env['project.task'].create({
            'name': 'Task',
            'project_id': self.project_employee_rate.id,
        })
        self.assertEqual(task.sale_line_id, self.so.order_line[0], "The SOL in the task should be the one containing the prepaid service product.")
        self.assertTrue(all(sol.qty_delivered == 0 for sol in self.so.order_line), "The quantity delivered should be equal to 0 because we have no timesheet for each SOL containing in the SO.")

        # 3) Create timesheet in the task and check if the SOL in the timesheet is the one in the task,
        timesheet = self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'unit_amount': 1,
            'auto_account_id': self.analytic_account_sale.id,
            'employee_id': self.employee_manager.id,
            'project_id': self.project_employee_rate.id,
            'task_id': task.id,
        })
        self.assertTrue(timesheet.so_line == task.sale_line_id == self.so.order_line[0], "The SOL in the timesheet should be the same than the one in the task.")
        self.assertEqual(self.so.order_line[0].qty_delivered, 1, "The quantity delivered should be equal to 1 for all SOLs in the SO.")

        # 4) Create timesheet in the task for the employee defined in the mapping and check if the SOL in this timesheet is the one defined in the # mapping,
        employee_user_timesheet = timesheet.copy({
            'name': 'Test Line Employee User',
            'employee_id': self.employee_user.id,
            'unit_amount': 2,
        })
        employee_user_timesheet._compute_so_line()
        self.assertTrue(employee_user_timesheet.so_line == self.project_employee_rate.sale_line_employee_ids[0].sale_line_id == self.so.order_line[1], "The SOL in the timesheet should be the one defined in the mapping for the employee user.")
        self.assertEqual(self.so.order_line[1].qty_delivered, 2, "The quantity delivered for this SOL should be equal to 2 hours.")

        # 5) Change the SOL in the task and check if only the SOL in the timesheet which does not concerne about the mapping changes,
        task.update({'sale_line_id': self.so.order_line[2].id})
        self.assertTrue(timesheet.so_line == task.sale_line_id == self.so.order_line[2], "The SOL in the timesheet should also change and be the same than the one in the task.")
        self.assertNotEqual(timesheet.so_line, employee_user_timesheet.so_line, "The SOL in the timesheet done by the employee user should not be the same than the one in the other timesheet in the task.")

        # 6) Change the SOL in the mapping and check if the timesheet conserne by the mapping has its SOL has been changed too.
        mapping.update({'sale_line_id': self.so.order_line[-1].id})
        self.assertTrue(employee_user_timesheet.so_line == mapping.sale_line_id == self.so.order_line[-1], "The SOL in the timesheet done by the employee user should be the one defined in the mapping.")
        self.assertNotEqual(timesheet.so_line, employee_user_timesheet.so_line, "The other timesheet should not have the SOL defined in the mapping.")

    def test_no_so_line_if_project_non_billable(self):
        """ Test if the timesheet created in task in non billable project does not have a SOL

            Test Case:
            =========
            1) Create task in a non billable project,
            2) Check if there is no SOL in task,
            3) Create timesheet in the task and check if it does not contain any SOL.
            4) Create a timesheet in the project without any task set for this timesheet.
            5) Check the timesheet has no SOL too since the project is non billable.
        """
        # 1) Create task in a non billable project,
        task = self.env['project.task'].create({
            'name': 'Test Task',
            'project_id': self.project_non_billable.id,
            'partner_id': self.partner_a.id,
        })
        # 2) Check if there is no SOL in task,
        self.assertFalse(task.sale_line_id, 'No SOL should be linked in this task because the project is non billable.')

        # 3) Create timesheet in the task and check if it does not contain any SOL.
        timesheet = self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'unit_amount': 1,
            'employee_id': self.employee_manager.id,
            'project_id': task.project_id.id,
            'task_id': task.id,
        })
        self.assertFalse(timesheet.so_line, 'No SOL should be linked in this timesheet because the project is non billable.')

        # 4) Create a timesheet in the project without any task set for this timesheet.
        timesheet1 = self.env['account.analytic.line'].create({
            'name': 'Test Line 1',
            'unit_amount': 1,
            'project_id': task.project_id.id,
            'employee_id': self.employee_manager.id,
        })
        # 5) Check the timesheet has no SOL too since the project is non billable.
        self.assertFalse(timesheet1.so_line, 'This Timesheet is not billable since it has no task set and the project linked is not billable')

    def test_tranfer_project(self):
        """ Test if the SOL in timesheet is erased if the task of this timesheet changes the project
            from a billable project to a non billable project

            Test Case:
            =========
            1) Create task in project_task_rate,
            2) Check if the task has the SOL which contain the prepaid service product,
            3) Create timesheet in this task,
            4) Check if the timesheet contains the same SOL than the task,
            5) Move the task in a non billable project,
            6) Check if the task and timesheet has no SOL.
        """
        # 1) Create task in project_task_rate,
        task = self.env['project.task'].create({
            'name': 'Test Task',
            'project_id': self.project_task_rate.id,
        })

        # 2) Check if the task has the SOL which contain the prepaid service product,
        self.assertEqual(task.sale_line_id, self.so.order_line[-1], 'The SOL with prepaid service product should be linked to the task.')

        # 3) Create timesheet in this task,
        timesheet = self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'unit_amount': 1,
            'employee_id': self.employee_manager.id,
            'project_id': task.project_id.id,
            'task_id': task.id,
        })

        # 4) Check if the timesheet contains the same SOL than the task,
        self.assertEqual(timesheet.so_line, task.sale_line_id, 'The timesheet should have the same SOL than the task.')

        # 5) Move the task in a non billable project,
        task.write({'project_id': self.project_non_billable.id})

        # 6) Check if the task and timesheet has no SOL.
        self.assertFalse(timesheet.so_line, 'No SOL should be linked to the timesheet because the project is non billable')
