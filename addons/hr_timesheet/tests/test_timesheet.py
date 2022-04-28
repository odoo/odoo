# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError, UserError, ValidationError


class TestCommonTimesheet(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestCommonTimesheet, cls).setUpClass()

        # Crappy hack to disable the rule from timesheet grid, if it exists
        # The registry doesn't contain the field timesheet_manager_id.
        # but there is an ir.rule about it, crashing during its evaluation
        rule = cls.env.ref('timesheet_grid.hr_timesheet_rule_approver_update', raise_if_not_found=False)
        if rule:
            rule.active = False

        # customer partner
        cls.partner = cls.env['res.partner'].create({
            'name': 'Customer Task',
            'email': 'customer@task.com',
            'phone': '42',
        })

        cls.analytic_plan = cls.env['account.analytic.plan'].create({
            'name': 'Plan Test',
            'company_id': False,
        })
        cls.analytic_account = cls.env['account.analytic.account'].create({
            'name': 'Analytic Account for Test Customer',
            'partner_id': cls.partner.id,
            'plan_id': cls.analytic_plan.id,
            'code': 'TEST'
        })

        # project and tasks
        cls.project_customer = cls.env['project.project'].create({
            'name': 'Project X',
            'allow_timesheets': True,
            'partner_id': cls.partner.id,
            'analytic_account_id': cls.analytic_account.id,
        })
        cls.task1 = cls.env['project.task'].create({
            'name': 'Task One',
            'priority': '0',
            'kanban_state': 'normal',
            'project_id': cls.project_customer.id,
            'partner_id': cls.partner.id,
        })
        cls.task2 = cls.env['project.task'].create({
            'name': 'Task Two',
            'priority': '1',
            'kanban_state': 'done',
            'project_id': cls.project_customer.id,
        })
        # users
        cls.user_employee = cls.env['res.users'].create({
            'name': 'User Employee',
            'login': 'user_employee',
            'email': 'useremployee@test.com',
            'groups_id': [(6, 0, [cls.env.ref('hr_timesheet.group_hr_timesheet_user').id])],
        })
        cls.user_employee2 = cls.env['res.users'].create({
            'name': 'User Employee 2',
            'login': 'user_employee2',
            'email': 'useremployee2@test.com',
            'groups_id': [(6, 0, [cls.env.ref('hr_timesheet.group_hr_timesheet_user').id])],
        })
        cls.user_manager = cls.env['res.users'].create({
            'name': 'User Officer',
            'login': 'user_manager',
            'email': 'usermanager@test.com',
            'groups_id': [(6, 0, [cls.env.ref('hr_timesheet.group_timesheet_manager').id])],
        })
        # employees
        cls.empl_employee = cls.env['hr.employee'].create({
            'name': 'User Empl Employee',
            'user_id': cls.user_employee.id,
        })
        cls.empl_employee2 = cls.env['hr.employee'].create({
            'name': 'User Empl Employee 2',
            'user_id': cls.user_employee2.id,
        })
        cls.empl_manager = cls.env['hr.employee'].create({
            'name': 'User Empl Officer',
            'user_id': cls.user_manager.id,
        })

class TestTimesheet(TestCommonTimesheet):

    def setUp(self):
        super(TestTimesheet, self).setUp()

        # Crappy hack to disable the rule from timesheet grid, if it exists
        # The registry doesn't contain the field timesheet_manager_id.
        # but there is an ir.rule about it, crashing during its evaluation
        rule = self.env.ref('timesheet_grid.timesheet_line_rule_user_update-unlink', raise_if_not_found=False)
        if rule:
            rule.active = False

    def test_log_timesheet(self):
        """ Test when log timesheet : check analytic account, user and employee are correctly set. """
        Timesheet = self.env['account.analytic.line']
        timesheet_uom = self.project_customer.analytic_account_id.company_id.project_time_mode_id
        # employee 1 log some timesheet on task 1
        timesheet1 = Timesheet.with_user(self.user_employee).create({
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'name': 'my first timesheet',
            'unit_amount': 4,
        })
        self.assertEqual(timesheet1.account_id, self.project_customer.analytic_account_id, 'Analytic account should be the same as the project')
        self.assertEqual(timesheet1.employee_id, self.empl_employee, 'Employee should be the one of the current user')
        self.assertEqual(timesheet1.partner_id, self.task1.partner_id, 'Customer of task should be the same of the one set on new timesheet')
        self.assertEqual(timesheet1.product_uom_id, timesheet_uom, "The UoM of the timesheet should be the one set on the company of the analytic account.")

        # employee 1 cannot log timesheet for employee 2
        with self.assertRaises(AccessError):
            timesheet2 = Timesheet.with_user(self.user_employee).create({
                'project_id': self.project_customer.id,
                'task_id': self.task1.id,
                'name': 'a second timesheet but for employee 2',
                'unit_amount': 3,
                'employee_id': self.empl_employee2.id,
            })

        # manager log timesheet for employee 2
        timesheet3 = Timesheet.with_user(self.user_manager).create({
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'name': 'a second timesheet but for employee 2',
            'unit_amount': 7,
            'employee_id': self.empl_employee2.id,
        })
        self.assertEqual(timesheet3.user_id, self.user_employee2, 'Timesheet user should be the one linked to the given employee')
        self.assertEqual(timesheet3.product_uom_id, timesheet_uom, "The UoM of the timesheet 3 should be the one set on the company of the analytic account.")

        # employee 1 log some timesheet on project (no task)
        timesheet4 = Timesheet.with_user(self.user_employee).create({
            'project_id': self.project_customer.id,
            'name': 'my first timesheet',
            'unit_amount': 4,
        })
        self.assertEqual(timesheet4.partner_id, self.project_customer.partner_id, 'Customer of new timesheet should be the same of the one set project (since no task on timesheet)')

    def test_log_access_rights(self):
        """ Test access rights : user can update its own timesheets only, and manager can change all """
        # employee 1 log some timesheet on task 1
        Timesheet = self.env['account.analytic.line']
        timesheet1 = Timesheet.with_user(self.user_employee).create({
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'name': 'my first timesheet',
            'unit_amount': 4,
        })
        # then employee 2 try to modify it
        with self.assertRaises(AccessError):
            timesheet1.with_user(self.user_employee2).write({
                'name': 'i try to update this timesheet',
                'unit_amount': 2,
            })
        # manager can modify all timesheet
        timesheet1.with_user(self.user_manager).write({
            'unit_amount': 8,
            'employee_id': self.empl_employee2.id,
        })
        self.assertEqual(timesheet1.user_id, self.user_employee2, 'Changing timesheet employee should change the related user')

    def test_create_unlink_project(self):
        """ Check project creation, and if necessary the analytic account generated when project should track time. """
        # create project wihtout tracking time, nor provide AA
        non_tracked_project = self.env['project.project'].create({
            'name': 'Project without timesheet',
            'allow_timesheets': False,
            'partner_id': self.partner.id,
        })
        self.assertFalse(non_tracked_project.analytic_account_id, "A non time-tracked project shouldn't generate an analytic account")

        # create a project tracking time
        tracked_project = self.env['project.project'].create({
            'name': 'Project with timesheet',
            'allow_timesheets': True,
            'partner_id': self.partner.id,
        })
        self.assertTrue(tracked_project.analytic_account_id, "A time-tracked project should generate an analytic account")
        self.assertTrue(tracked_project.analytic_account_id.active, "A time-tracked project should generate an active analytic account")
        self.assertEqual(tracked_project.partner_id, tracked_project.analytic_account_id.partner_id, "The generated AA should have the same partner as the project")
        self.assertEqual(tracked_project.name, tracked_project.analytic_account_id.name, "The generated AA should have the same name as the project")
        self.assertEqual(tracked_project.analytic_account_id.project_count, 1, "The generated AA should be linked to the project")

        # create a project without tracking time, but with analytic account
        analytic_project = self.env['project.project'].create({
            'name': 'Project without timesheet but with AA',
            'allow_timesheets': True,
            'partner_id': self.partner.id,
            'analytic_account_id': tracked_project.analytic_account_id.id,
        })
        self.assertNotEqual(analytic_project.name, tracked_project.analytic_account_id.name, "The name of the associated AA can be different from the project")
        self.assertEqual(tracked_project.analytic_account_id.project_count, 2, "The AA should be linked to 2 project")

        # analytic linked to projects containing tasks can not be removed
        task = self.env['project.task'].create({
            'name': 'task in tracked project',
            'project_id': tracked_project.id,
        })
        with self.assertRaises(UserError):
            tracked_project.analytic_account_id.unlink()

        # task can be removed, as there is no timesheet
        task.unlink()

        # since both projects linked to the same analytic account are empty (no task), it can be removed
        tracked_project.analytic_account_id.unlink()

    def test_transfert_project(self):
        """ Transfert task with timesheet to another project. """
        Timesheet = self.env['account.analytic.line']
        # create a second project
        self.project_customer2 = self.env['project.project'].create({
            'name': 'Project NUMBER DEUX',
            'allow_timesheets': True,
        })
        # employee 1 log some timesheet on task 1
        Timesheet.create({
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'name': 'my first timesheet',
            'unit_amount': 4,
            'user_id': self.user_employee.id,
        })

        timesheet_count1 = Timesheet.search_count([('project_id', '=', self.project_customer.id)])
        timesheet_count2 = Timesheet.search_count([('project_id', '=', self.project_customer2.id)])
        self.assertEqual(timesheet_count1, 1, "One timesheet in project 1")
        self.assertEqual(timesheet_count2, 0, "No timesheet in project 2")
        self.assertEqual(len(self.task1.timesheet_ids), 1, "The timesheet should be linked to task 1")

        # change project of task 1
        self.task1.write({
            'project_id': self.project_customer2.id
        })

        timesheet_count1 = Timesheet.search_count([('project_id', '=', self.project_customer.id)])
        timesheet_count2 = Timesheet.search_count([('project_id', '=', self.project_customer2.id)])
        self.assertEqual(timesheet_count1, 0, "No timesheet in project 1")
        self.assertEqual(timesheet_count2, 1, "Still one timesheet in project 2")
        self.assertEqual(len(self.task1.timesheet_ids), 1, "The timesheet still should be linked to task 1")

        # it is forbidden to set a task with timesheet without project
        with self.assertRaises(UserError):
            self.task1.write({
                'project_id': False
            })

    def test_recompute_amount_for_multiple_timesheets(self):
        """ Check that amount is recomputed correctly when setting unit_amount for multiple timesheets at once. """
        Timesheet = self.env['account.analytic.line']
        self.empl_employee.hourly_cost = 5.0
        self.empl_employee2.hourly_cost = 6.0
        # create a timesheet for each employee
        timesheet_1 = Timesheet.with_user(self.user_employee).create({
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'name': '/',
            'unit_amount': 1,
        })
        timesheet_2 = Timesheet.with_user(self.user_employee2).create({
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'name': '/',
            'unit_amount': 1,
        })
        timesheets = timesheet_1 + timesheet_2

        with self.assertRaises(AccessError):
            # should raise since employee 1 doesn't have the access rights to update employee's 2 timesheet
            timesheets.with_user(self.empl_employee.user_id).write({
                'unit_amount': 2,
            })

        timesheets.with_user(self.user_manager).write({
            'unit_amount': 2,
        })

        # since timesheet costs are different for both employees, we should get different amounts
        self.assertRecordValues(timesheets.with_user(self.user_manager), [{
            'amount': -10.0,
        }, {
            'amount': -12.0,
        }])

    def test_recompute_partner_from_task_customer_change(self):
        partner2 = self.env['res.partner'].create({
            'name': 'Customer Task 2',
            'email': 'customer2@task.com',
            'phone': '43',
        })

        timesheet_entry = self.env['account.analytic.line'].create({
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'name': 'my only timesheet',
            'unit_amount': 4,
            'user_id': self.user_employee.id,
        })

        self.assertEqual(timesheet_entry.partner_id, self.partner, "The timesheet entry's partner should be equal to the task's partner/customer")

        self.task1.write({'partner_id': partner2})

        self.assertEqual(timesheet_entry.partner_id, partner2, "The timesheet entry's partner should still be equal to the task's partner/customer, after the change")

    def test_task_with_timesheet_project_change(self):
        '''This test checks that no error is raised when moving a task that contains timesheet to another project.
           This move implying writing on the account.analytic.line.
        '''

        project_manager = self.env['res.users'].create({
            'name': 'user_project_manager',
            'login': 'user_project_manager',
            'groups_id': [(6, 0, [self.ref('project.group_project_manager')])],
        })

        project = self.env['project.project'].create({
            'name': 'Project With Timesheets',
            'privacy_visibility': 'employees',
            'allow_timesheets': True,
            'user_id': project_manager.id,
        })
        second_project = self.env['project.project'].create({
            'name': 'Project w/ timesheets',
            'privacy_visibility': 'employees',
            'allow_timesheets': True,
            'user_id': project_manager.id,
        })

        task_1 = self.env['project.task'].create({
            'name': 'First task',
            'user_ids': self.user_employee2,
            'project_id': project.id
        })

        timesheet = self.env['account.analytic.line'].create({
            'name': 'FirstTimeSheet',
            'project_id': project.id,
            'task_id': task_1.id,
            'unit_amount': 2,
            'employee_id': self.empl_employee2.id
        })

        task_1.with_user(project_manager).write({
            'project_id': second_project.id
        })

        self.assertEqual(timesheet.project_id, second_project, 'The project_id of timesheet should be second_project')

    def test_create_timesheet_employee_not_in_company(self):
        ''' ts.employee_id only if the user has an employee in the company or one employee for all companies.
        '''
        company_2 = self.env['res.company'].create({'name': 'Company 2'})
        company_3 = self.env['res.company'].create({'name': 'Company 3'})

        analytic_plan = self.env['account.analytic.plan'].create({
            'name': 'Plan Test',
            'company_id': company_3.id
        })
        analytic_account = self.env['account.analytic.account'].create({
            'name': 'Aa Aa',
            'plan_id': analytic_plan.id,
            'company_id': company_3.id,
        })
        project = self.env['project.project'].create({
            'name': 'Aa Project',
            'company_id': company_3.id,
            'analytic_account_id': analytic_account.id,
        })
        task = self.env['project.task'].create({
            'name': 'Aa Task',
            'project_id': project.id,
        })

        Timesheet = self.env['account.analytic.line'].with_context(allowed_company_ids=[company_3.id, company_2.id, self.env.company.id])
        timesheet = Timesheet.create({
            'name': 'Timesheet',
            'project_id': project.id,
            'task_id': task.id,
            'unit_amount': 2,
            'user_id': self.user_manager.id,
            'company_id': company_3.id,
        })
        self.assertEqual(timesheet.employee_id, self.user_manager.employee_id, 'As there is a unique employee for this user, it must be found')

        self.env['hr.employee'].with_company(company_2).create({
            'name': 'Employee 2',
            'user_id': self.user_manager.id,
        })
        with self.assertRaises(ValidationError):
            # As there are several employees for this user, but none of them in this company, none must be found
            Timesheet.create({
                'name': 'Timesheet',
                'project_id': project.id,
                'task_id': task.id,
                'unit_amount': 2,
                'user_id': self.user_manager.id,
                'company_id': company_3.id,
            })

    def test_create_timesheet_with_multi_company(self):
        """ Always set the current company in the timesheet, not the employee company """
        company_4 = self.env['res.company'].create({'name': 'Company 4'})
        empl_employee = self.env['hr.employee'].with_company(company_4).create({
            'name': 'Employee 3',
        })

        Timesheet = self.env['account.analytic.line'].with_context(allowed_company_ids=[company_4.id, self.env.company.id])

        timesheet = Timesheet.create({
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'name': 'my first timesheet',
            'unit_amount': 4,
            'employee_id': empl_employee.id,
        })

        self.assertEqual(timesheet.company_id.id, self.env.company.id)

    def test_subtask_log_timesheet(self):
        """ Test parent task takes into account the timesheets of its sub-tasks.
            Test Case:
            ----------
            1) Create parent task
            2) Create child/subtask task
            3) Enter the 8 hour timesheet in the child task
            4) Check subtask Effective hours in parent task
        """
        self.task1.child_ids = [Command.set([self.task2.id])]
        self.env['account.analytic.line'].create({
            'name': 'FirstTimeSheet',
            'project_id': self.project_customer.id,
            'task_id': self.task2.id,
            'unit_amount': 8.0,
            'employee_id': self.empl_employee2.id,
        })
        self.assertEqual(self.task1.subtask_effective_hours, 8, 'Hours Spent on Sub-tasks should be 8 hours in Parent Task')
        self.task1.child_ids = [Command.clear()]

    def test_ensure_product_uom_set_in_timesheet(self):
        self.assertFalse(self.project_customer.timesheet_ids, 'No timesheet should be recorded in this project')
        self.assertFalse(self.project_customer.total_timesheet_time, 'The total time recorded should be equal to 0 since no timesheet is recorded.')

        timesheet1, timesheet2 = self.env['account.analytic.line'].with_user(self.user_employee).create([
            {'unit_amount': 1.0, 'project_id': self.project_customer.id},
            {'unit_amount': 3.0, 'project_id': self.project_customer.id, 'product_uom_id': False},
        ])
        self.assertEqual(
            timesheet1.product_uom_id,
            self.project_customer.analytic_account_id.company_id.timesheet_encode_uom_id,
            'The default UoM set on the timesheet should be the one set on the company of AA.'
        )
        self.assertEqual(
            timesheet2.product_uom_id,
            self.project_customer.analytic_account_id.company_id.timesheet_encode_uom_id,
            'Even if the product_uom_id field is empty in the vals, the product_uom_id should have a UoM by default,'
            ' otherwise the `total_timesheet_time` in project should not included the timesheet.'
        )
        self.assertEqual(self.project_customer.timesheet_ids, timesheet1 + timesheet2)
        self.assertEqual(
            self.project_customer.total_timesheet_time,
            timesheet1.unit_amount + timesheet2.unit_amount,
            'The total timesheet time of this project should be equal to 4.'
        )
    def test_create_timesheet_with_archived_employee(self):
        ''' the timesheet can be created or edited only with an active employee
        '''
        self.empl_employee2.active = False
        batch_vals = {
            'project_id': self.project_customer.id,
            'task_id': self.task1.id,
            'name': 'archived employee timesheet',
            'unit_amount': 3,
            'employee_id': self.empl_employee2.id
        }

        self.assertRaises(UserError, self.env['account.analytic.line'].create, batch_vals)

        batch_vals["employee_id"] = self.empl_employee.id
        timesheet = self.env['account.analytic.line'].create(batch_vals)

        with self.assertRaises(UserError):
            timesheet.employee_id = self.empl_employee2
