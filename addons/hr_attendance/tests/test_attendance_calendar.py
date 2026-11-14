# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAttendanceCalendar(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['hr.time.rule'].search([]).write({'active': False})
        cls.calendar = cls.env['resource.calendar'].create({
            'name': 'Attendance Based',
            'calendar_type': 'attendance',
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Attendance Employee',
            'tz': 'UTC',
            'resource_calendar_id': cls.calendar.id,
            'date_version': date(2024, 1, 1),
            'contract_date_start': date(2024, 1, 1),
        })
        cls.work_entry_type = cls.env['hr.work.entry.type'].create({
            'name': 'Attendance Type',
            'code': 'ATTCAL',
        })
        cls.attendance = cls.env['hr.attendance'].create({
            'employee_id': cls.employee.id,
            'check_in': datetime(2024, 3, 4, 8),
            'check_out': datetime(2024, 3, 4, 17),
            'break_duration': 1,
            'work_entry_type_id': cls.work_entry_type.id,
        })
        cls.attendance.state = 'validated'

    def test_calendar_has_no_attendance_lines(self):
        self.assertFalse(self.calendar.attendance_ids)

    def test_generate_work_entries_from_attendances(self):
        vals = self.employee.version_id.generate_work_entries(date(2024, 3, 4), date(2024, 3, 5))
        self.assertEqual(len(vals), 1)
        self.assertEqual(vals[0]['work_entry_type_id'], self.work_entry_type)
        self.assertEqual(vals[0]['date'], date(2024, 3, 4))
        self.assertAlmostEqual(vals[0]['duration'], 8)

    def test_draft_attendance_ignored(self):
        self.attendance.state = 'draft'
        vals = self.employee.version_id.generate_work_entries(date(2024, 3, 4), date(2024, 3, 5))
        self.assertFalse(vals)
