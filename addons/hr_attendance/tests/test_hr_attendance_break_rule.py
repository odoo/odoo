# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAttendanceBreakRule(TransactionCase):
    """The break of an attendance is raised to the minimum break of the employee's break rule line, by the hours of
    the attendance."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].create({'name': 'Employee', 'tz': 'UTC'})
        cls.other_employee = cls.env['hr.employee'].create({'name': 'Other Employee', 'tz': 'UTC'})
        cls.rule = cls.env['hr.attendance.break.rule'].create({
            'name': 'Legal Breaks',
            'employee_domain': str([('id', '=', cls.employee.id)]),
            'line_ids': [
                Command.create({'work_hours': 6, 'break_hours': 0.5}),
                Command.create({'work_hours': 9, 'break_hours': 0.75}),
            ],
        })

    def _create(self, check_in, check_out, employee=None, **vals):
        return self.env['hr.attendance'].create({
            'employee_id': (employee or self.employee).id,
            'check_in': check_in,
            'check_out': check_out,
            **vals,
        })

    def test_break_by_attendance_hours(self):
        """The line with the highest hours that the attendance exceeds gives the break."""
        cases = [
            (datetime(2026, 6, 8, 8), datetime(2026, 6, 8, 14), 0.0),
            (datetime(2026, 6, 9, 8), datetime(2026, 6, 9, 14, 30), 0.5),
            (datetime(2026, 6, 10, 8), datetime(2026, 6, 10, 17), 0.5),
            (datetime(2026, 6, 11, 8), datetime(2026, 6, 11, 18), 0.75),
        ]
        for check_in, check_out, break_duration in cases:
            with self.subTest(check_in=check_in, check_out=check_out):
                attendance = self._create(check_in, check_out)
                self.assertAlmostEqual(attendance.break_duration, break_duration, places=4)

    def test_longer_break_kept(self):
        attendance = self._create(datetime(2026, 6, 8, 8), datetime(2026, 6, 8, 15), break_duration=1.0)
        self.assertAlmostEqual(attendance.break_duration, 1.0, places=4)

    def test_each_attendance_counts_alone(self):
        """8h of the day in two attendances of 4h: no attendance exceeds 6h, no break."""
        attendances = self._create(datetime(2026, 6, 8, 8), datetime(2026, 6, 8, 12)) | self._create(
            datetime(2026, 6, 8, 13), datetime(2026, 6, 8, 17))
        self.assertEqual(attendances.mapped('break_duration'), [0.0, 0.0])

    def test_break_raised_at_check_out_and_on_write(self):
        attendance = self._create(datetime(2026, 6, 8, 8), False)
        self.assertFalse(attendance.break_duration)
        attendance.check_out = datetime(2026, 6, 8, 15)
        self.assertAlmostEqual(attendance.break_duration, 0.5, places=4)
        self.assertAlmostEqual(attendance.worked_hours, 6.5, places=4)
        attendance.break_duration = 0.25
        self.assertAlmostEqual(attendance.break_duration, 0.5, places=4)
        attendance.check_out = datetime(2026, 6, 8, 18)
        self.assertAlmostEqual(attendance.break_duration, 0.75, places=4)

    def test_rule_of_the_employee(self):
        """Only the employees matching the domain get the rule, and the first rule by sequence applies."""
        attendance = self._create(datetime(2026, 6, 8, 8), datetime(2026, 6, 8, 15), employee=self.other_employee)
        self.assertFalse(attendance.break_duration)

        self.env['hr.attendance.break.rule'].create({
            'name': 'Everyone',
            'sequence': self.rule.sequence - 1,
            'line_ids': [Command.create({'work_hours': 4, 'break_hours': 1})],
        })
        attendances = self._create(datetime(2026, 6, 9, 8), datetime(2026, 6, 9, 15)) | self._create(
            datetime(2026, 6, 9, 8), datetime(2026, 6, 9, 15), employee=self.other_employee)
        self.assertEqual(attendances.mapped('break_duration'), [1.0, 1.0])

    def test_rule_of_the_company(self):
        """A rule with a company only applies to the employees of that company."""
        other_company = self.env['res.company'].create({'name': 'Other Company'})
        other_company_employee = self.env['hr.employee'].create({
            'name': 'Other Company Employee',
            'tz': 'UTC',
            'company_id': other_company.id,
        })
        self.env['hr.attendance.break.rule'].create({
            'name': 'Other Company Breaks',
            'company_id': other_company.id,
            'line_ids': [Command.create({'work_hours': 4, 'break_hours': 1})],
        })
        attendances = self._create(
            datetime(2026, 6, 8, 8), datetime(2026, 6, 8, 15), employee=self.other_employee,
        ) | self._create(datetime(2026, 6, 8, 8), datetime(2026, 6, 8, 15), employee=other_company_employee)
        self.assertEqual(attendances.mapped('break_duration'), [0.0, 1.0])

    def test_archived_rule(self):
        self.rule.active = False
        attendance = self._create(datetime(2026, 6, 8, 8), datetime(2026, 6, 8, 15))
        self.assertFalse(attendance.break_duration)
