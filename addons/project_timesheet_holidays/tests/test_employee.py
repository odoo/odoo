# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestEmployee(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({
            'name': 'Test Company',
        })
        cls.global_leave = cls.env['resource.calendar.leaves'].create({
            'name': 'Test Global Leave',
            'date_from': '2020-01-01 00:00:00',
            'date_to': '2020-01-01 23:59:59',
            'calendar_id': cls.company.resource_calendar_id.id,
            'company_id': cls.company.id,
        })

    @freeze_time('2020-01-01')
    def test_create_employee(self):
        """ Test the timesheets representing the time off of this new employee
            is correctly generated once the employee is created

            Test Case:
            =========
            1) Create a new employee
            2) Check the timesheets representing the time off of this new employee
               is correctly generated
        """
        existing_employee = self.env['hr.employee'].create({
            'name': 'Test Employee',
            'company_id': self.company.id,
            'resource_calendar_id': self.company.resource_calendar_id.id,
        })
        resource_leave = self.env['resource.calendar.leaves'].with_company(self.company).create({
            'name': 'Future resource specific leave without a calendar',
            'date_from': '2020-01-02 00:00:00',
            'date_to': '2020-01-02 23:59:59',
            'calendar_id': False,
            'resource_id': existing_employee.resource_id.id,
            'company_id': self.company.id,
        })

        employee = self.env['hr.employee'].create({
            'name': 'Test Employee',
            'company_id': self.company.id,
            'resource_calendar_id': self.company.resource_calendar_id.id,
        })
        # Check resource-specific leave does not create a timesheet
        resource_timesheet = self.env['account.analytic.line'].search([
            ('employee_id', '=', employee.id),
            ('global_leave_id', '=', resource_leave.id),
        ])
        self.assertFalse(resource_timesheet, 'No timesheet should be created for resource-specific leaves')

        timesheet = self.env['account.analytic.line'].search([
            ('employee_id', '=', employee.id),
            ('global_leave_id', '=', self.global_leave.id),
        ])
        self.assertEqual(len(timesheet), 1, 'A timesheet should have been created for the global leave of the employee')
        self.assertEqual(str(timesheet.date), '2020-01-01', 'The timesheet should be created for the correct date')
        self.assertEqual(timesheet.unit_amount, 8, 'The timesheet should be created for the correct duration')

        # simulate the company of the employee updated is not in the allowed_company_ids of the current user
        employee2 = self.env['hr.employee'].with_company(self.env.company).create({
            'name': 'Test Employee',
            'company_id': self.company.id,
            'resource_calendar_id': self.company.resource_calendar_id.id,
        })
        timesheet = self.env['account.analytic.line'].search([
            ('employee_id', '=', employee2.id),
            ('global_leave_id', '=', self.global_leave.id),
        ])
        self.assertEqual(len(timesheet), 1, 'A timesheet should have been created for the global leave of the employee')
        self.assertEqual(str(timesheet.date), '2020-01-01', 'The timesheet should be created for the correct date')
        self.assertEqual(timesheet.unit_amount, 8, 'The timesheet should be created for the correct duration')

    @freeze_time('2020-01-01')
    def test_write_employee(self):
        """ Test the timesheets representing the time off of this employee
            is correctly generated once the employee is updated

            Test Case:
            =========
            1) Create a new employee
            2) Check the timesheets representing the time off of this new employee
               is correctly generated
            3) Update the employee
            4) Check the timesheets representing the time off of this employee
               is correctly updated
        """
        employee = self.env['hr.employee'].create({
            'name': 'Test Employee',
            'company_id': self.company.id,
        })
        employee.write({'resource_calendar_id': self.company.resource_calendar_id.id})
        timesheet = self.env['account.analytic.line'].search([
            ('employee_id', '=', employee.id),
            ('global_leave_id', '=', self.global_leave.id),
        ])
        self.assertEqual(len(timesheet), 1, 'A timesheet should have been created for the global leave of the employee')
        self.assertEqual(str(timesheet.date), '2020-01-01', 'The timesheet should be created for the correct date')
        self.assertEqual(timesheet.unit_amount, 8, 'The timesheet should be created for the correct duration')

        employee.write({'active': False})
        timesheet = self.env['account.analytic.line'].search([
            ('employee_id', '=', employee.id),
            ('global_leave_id', '=', self.global_leave.id),
        ])
        self.assertFalse(timesheet, 'The timesheet should have been deleted when the employee was archived')

        employee.write({'active': True})
        timesheet = self.env['account.analytic.line'].search([
            ('employee_id', '=', employee.id),
            ('global_leave_id', '=', self.global_leave.id),
        ])
        self.assertEqual(len(timesheet), 1, 'A timesheet should have been created for the global leave of the employee')
        self.assertEqual(str(timesheet.date), '2020-01-01', 'The timesheet should be created for the correct date')
        self.assertEqual(timesheet.unit_amount, 8, 'The timesheet should be created for the correct duration')

        # test unarchiving on an already active employee does not create duplicate public leaves
        employee.write({'active': True})
        timesheet = self.env['account.analytic.line'].search([
            ('employee_id', '=', employee.id),
            ('global_leave_id', '=', self.global_leave.id),
        ])
        self.assertEqual(len(timesheet), 1, 'We should not have created duplicate public holiday leaves')

        # simulate the company of the employee updated is not in the allowed_company_ids of the current user
        employee.with_company(self.env.company).write({'resource_calendar_id': self.company.resource_calendar_id.id})
        timesheet = self.env['account.analytic.line'].search([
            ('employee_id', '=', employee.id),
            ('global_leave_id', '=', self.global_leave.id),
        ])
        self.assertEqual(len(timesheet), 1, 'A timesheet should have been created for the global leave of the employee')
        self.assertEqual(str(timesheet.date), '2020-01-01', 'The timesheet should be created for the correct date')
        self.assertEqual(timesheet.unit_amount, 8, 'The timesheet should be created for the correct duration')
