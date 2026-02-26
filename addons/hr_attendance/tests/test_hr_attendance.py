from datetime import datetime

from odoo.tests.common import tagged, TransactionCase


@tagged('hr_attendance')
class TestHrAttendanceCommon(TransactionCase):
    """Tests for attendances"""

    @classmethod
    def setUpClass(cls):
        super(TestHrAttendanceCommon, cls).setUpClass()
        cls.attendance = cls.env['hr.attendance']
        cls.employee = cls.env['hr.employee'].create({'name': "Jacky", 'ruleset_id': False})

    def test_get_overtimes_to_update_domain(self):
        attendance = self.attendance.create({
            'employee_id': self.employee.id,
            'check_in': datetime(2026, 1, 7, 8, 0),
            'check_out': datetime(2026, 1, 7, 20, 0)
        })

        expected_domain = f"['&', '&', ('employee_id', '=', {self.employee.id}), ('date', '<=', datetime.date(2026, 1, 11)), ('date', '>=', datetime.date(2026, 1, 5))]"
        self.assertEqual(expected_domain, str(attendance._get_overtimes_to_update_domain()))


    def test_get_overtimes_to_update_domain_same_week(self):
        attendance = self.attendance.create([{
            'employee_id': self.employee.id,
            'check_in': datetime(2026, 1, 7, 8, 0),
            'check_out': datetime(2026, 1, 7, 20, 0)
        },
        {
            'employee_id': self.employee.id,
            'check_in': datetime(2026, 1, 8, 8, 0),
            'check_out': datetime(2026, 1, 8, 20, 0)
        },
        ])

        expected_domain = f"['&', '&', ('employee_id', '=', {self.employee.id}), ('date', '<=', datetime.date(2026, 1, 11)), ('date', '>=', datetime.date(2026, 1, 5))]"
        self.assertEqual(expected_domain, str(attendance._get_overtimes_to_update_domain()))


    def test_get_overtimes_to_update_domain_double_week(self):
        attendance = self.attendance.create([{
            'employee_id': self.employee.id,
            'check_in': datetime(2026, 1, 3, 8, 0),
            'check_out': datetime(2026, 1, 3, 20, 0)
        },
        {
            'employee_id': self.employee.id,
            'check_in': datetime(2026, 1, 8, 8, 0),
            'check_out': datetime(2026, 1, 8, 20, 0)
        },
        ])

        expected_domain = f"['&', '&', ('employee_id', '=', {self.employee.id}), ('date', '<=', datetime.date(2026, 1, 11)), ('date', '>=', datetime.date(2025, 12, 29))]"
        self.assertEqual(expected_domain, str(attendance._get_overtimes_to_update_domain()))
