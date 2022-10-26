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
        report_data = self.env['hr.timesheet.attendance.report']._read_group(
            [('user_id', '=', self.user_employee.id),
            ('date', '>=', datetime(2022, 2, 9, 8, 0)), ('date', '<=', datetime(2022, 2, 9, 16, 0))],
            ['total_timesheet', 'total_attendance', 'total_difference'],
            ['user_id'],
        )[0]
        self.assertEqual(report_data['total_timesheet'], 6.0, "Total timesheet in report should be 4.0")
        self.assertEqual(report_data['total_attendance'], 8.0, "Total attendance in report should be 8.0")
        self.assertEqual(report_data['total_attendance'] - report_data['total_timesheet'], 2)
