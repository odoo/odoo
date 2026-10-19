# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.tests import tagged
from odoo.addons.hr_timesheet.tests.test_timesheet import TestCommonTimesheet

@tagged('post_install', '-at_install')
class TestTimesheetAttendance(TestCommonTimesheet):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['hr.attendance'].create({
            'employee_id': cls.empl_employee.id,
            'check_in': datetime(2022, 2, 9, 8, 0), # Wednesday
            'check_out': datetime(2022, 2, 9, 16, 0),
        })

    def test_timesheet_attendance_report(self):
        self.env['account.analytic.line'].with_user(self.user_employee).create({
            'name': 'Test timesheet 1',
            'project_id': self.project_customer.id,
            'unit_amount': 6.0,
            'date': datetime(2022, 2, 9),
        })
        total_timesheet, total_attendance = self.env['hr.timesheet.attendance.report']._read_group(
            [('employee_id', '=', self.empl_employee.id),
            ('date', '>=', datetime(2022, 2, 9, 8, 0)), ('date', '<=', datetime(2022, 2, 9, 16, 0))],
            aggregates=['total_timesheet:sum', 'total_attendance:sum'],
        )[0]
        self.assertEqual(total_timesheet, 6.0, "Total timesheet in report should be 4.0")
        self.assertEqual(total_attendance, 8.0, "Total attendance in report should be 8.0")
        self.assertEqual(total_attendance - total_timesheet, 2)

    def test_timesheet_attendance_report_costs(self):
        """ The costs of the report are the time (timesheeted, attended, and the
            difference between both) multiplied by the hourly cost of the employee.
        """
        self.empl_employee.hourly_cost = 10.0
        self.env['account.analytic.line'].with_user(self.user_employee).create({
            'name': 'Test timesheet 1',
            'project_id': self.project_customer.id,
            'unit_amount': 6.0,
            'date': datetime(2022, 2, 9),
        })
        self.env.flush_all()
        timesheets_cost, attendance_cost, cost_difference = self.env['hr.timesheet.attendance.report']._read_group(
            [('employee_id', '=', self.empl_employee.id),
             ('date', '>=', datetime(2022, 2, 9, 8, 0)), ('date', '<=', datetime(2022, 2, 9, 16, 0))],
            aggregates=['timesheets_cost:sum', 'attendance_cost:sum', 'cost_difference:sum'],
        )[0]
        self.assertEqual(timesheets_cost, 60.0, "6 timesheeted hours at a cost of 10/hour")
        self.assertEqual(attendance_cost, 80.0, "8 attended hours at a cost of 10/hour")
        self.assertEqual(cost_difference, 20.0, "The 2 hours of difference at a cost of 10/hour")
        self.assertEqual(attendance_cost - timesheets_cost, cost_difference)
