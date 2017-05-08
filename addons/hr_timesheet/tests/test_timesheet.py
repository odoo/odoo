# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError


class TestTimesheet(TransactionCase):

    def setUp(self):
        super(TestTimesheet, self).setUp()

        self.project_customer = self.env['project.project'].create({
            'name': 'Project X',
            'allow_timesheets': True,
            'use_tasks': True,
        })
        self.task1 = self.env['project.task'].create({
            'name': 'Task One',
            'priority': '0',
            'kanban_state': 'normal',
            'project_id': self.project_customer.id,
        })
        self.task2 = self.env['project.task'].create({
            'name': 'Task Two',
            'priority': '1',
            'kanban_state': 'done',
            'project_id': self.project_customer.id,
        })
        # users
        self.user_employee = self.env['res.users'].create({
            'name': 'User Employee',
            'login': 'user_employee',
            'email': 'useremployee@test.com',
            'groups_id': [(4, self.ref('hr_timesheet.group_hr_timesheet_user'))],
        })
        self.user_employee2 = self.env['res.users'].create({
            'name': 'User Employee 2',
            'login': 'user_employee2',
            'email': 'useremployee2@test.com',
            'groups_id': [(4, self.ref('hr_timesheet.group_hr_timesheet_user'))],
        })
        self.user_manager = self.env['res.users'].create({
            'name': 'User Officer',
            'login': 'user_manager',
            'email': 'usermanager@test.com',
            'groups_id': [(4, self.ref('hr_timesheet.group_timesheet_manager'))],
        })
        # employees
        self.empl_employee = self.env['hr.employee'].create({
            'name': 'User Empl Employee',
            'user_id': self.user_employee.id,
        })
        self.empl_employee2 = self.env['hr.employee'].create({
            'name': 'User Empl Employee 2',
            'user_id': self.user_employee2.id,
        })
        self.empl_manager = self.env['hr.employee'].create({
            'name': 'User Empl Officer',
            'user_id': self.user_manager.id,
        })

    def test_log_timesheet(self):
        """ Test when log timesheet : check analytic account, user and employee are correctly set. """
        Timesheet = self.env['account.analytic.line']
        # employee 1 log some timesheet on task 1
        timesheet1 = Timesheet.sudo(self.user_employee.id).create({
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'name': 'my first timesheet',
            'unit_amount': 4,
        })
        self.assertEquals(timesheet1.account_id, self.project_customer.analytic_account_id, 'Analytic account should be the same as the project')
        self.assertEquals(timesheet1.employee_id, self.empl_employee, 'Employee should be the one of the current user')

        # employee 1 cannot log timesheet for employee 2
        with self.assertRaises(AccessError):
            timesheet2 = Timesheet.sudo(self.user_employee.id).create({
                'project_id': self.project_customer.id,
                'task_id': self.task1.id,
                'name': 'a second timesheet but for employee 2',
                'unit_amount': 3,
                'employee_id': self.empl_employee2.id,
            })

        # manager log timesheet for employee 2
        timesheet3 = Timesheet.sudo(self.user_manager.id).create({
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'name': 'a second timesheet but for employee 2',
            'unit_amount': 7,
            'employee_id': self.empl_employee2.id,
        })
        timesheet3._onchange_employee_id()
        self.assertEquals(timesheet3.user_id, self.user_employee2, 'Timesheet user should be the one linked to the given employee')

    def test_log_access_rights(self):
        """ Test access rights : user can update its own timesheets only, and manager can change all """
        # employee 1 log some timesheet on task 1
        Timesheet = self.env['account.analytic.line']
        timesheet1 = Timesheet.sudo(self.user_employee.id).create({
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'name': 'my first timesheet',
            'unit_amount': 4,
        })
        # then employee 2 try to modify it
        with self.assertRaises(AccessError):
            timesheet1.sudo(self.user_employee2.id).write({
                'name': 'i try to update this timesheet',
                'unit_amount': 2,
            })
        # manager can modify all timesheet
        timesheet1.sudo(self.user_manager.id).write({
            'unit_amount': 8,
            'employee_id': self.empl_employee2.id,
        })
        self.assertEquals(timesheet1.user_id, self.user_employee2, 'Changing timesheet employee should change the related user')
