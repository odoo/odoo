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
        employee = self.env['hr.employee'].create({
            'name': 'Test Employee',
            'company_id': self.company.id,
            'resource_calendar_id': self.company.resource_calendar_id.id,
        })
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

    @freeze_time('2020-01-01')
    def test_timesheet_inactive_employee(self):
        """ Test if the timesheets representing the time off of this employee,
            are correctly generated once the employee is set to inactive
        """
        employee = self.env['hr.employee'].create({
            'name': 'Test Employee',
            'resource_calendar_id': self.company.resource_calendar_id.id,
            'company_id': self.company.id,
        })
        old_timesheet_count = len(self.env['account.analytic.line'].search([
            ('employee_id', '=', employee.id)]))
        generic_time_off_type = self.env['hr.leave.type'].create({
            'name': 'Generic Time Off',
            'requires_allocation': 'no',
            'leave_validation_type': 'both',
            'company_id': self.company.id,
        })
        leave = self.env['hr.leave'].create({
            'employee_id': employee.id,
            'state': 'confirm',
            'holiday_type': 'employee',
            'holiday_status_id': generic_time_off_type.id,
            'request_date_from': '2020-01-02 08:00:00',
            'request_date_to': '2020-01-07 17:00:00',
        })
        leave.action_validate()
        timesheets = self.env['account.analytic.line'].search([
            ('employee_id', '=', employee.id)])
        self.assertEqual(len(timesheets), old_timesheet_count + 4, "4 new Timesheets should be generated for timeoff that doesn't fall on a week-end")

        employee.write({'active': False})  # Archiveing an employee will delete the timesheet related to its future holidays, this will change the number of timesheets
        old_timesheet_count = len(self.env['account.analytic.line'].search([
            ('employee_id', '=', employee.id)]))

        leave._generate_timesheets()
        self.assertTrue(timesheets, "Timesheet should not have been regenerated and therefore old timesheet shouldn't be deleted")
        timesheets = self.env['account.analytic.line'].search([
            ('employee_id', '=', employee.id)])
        self.assertEqual(len(timesheets), old_timesheet_count, "New timesheets should not have been generated due to employee being inactive/archived")
