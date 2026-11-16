# -*- coding: utf-8 -*-

from freezegun import freeze_time
import time

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, new_test_user, tagged, users, warmup
from odoo.tools import format_datetime


@tagged('jesaispas')
class TestHrAttendance(TransactionCase):
    """Tests for attendance date ranges validity"""

    @classmethod
    def setUpClass(cls):
        super(TestHrAttendance, cls).setUpClass()
        cls.attendance = cls.env['hr.attendance']
        cls.test_employee = cls.env['hr.employee'].create({'name': "Jacky"})
        # demo data contains set up for cls.test_employee
        cls.open_attendance = cls.attendance.create({
            'employee_id': cls.test_employee.id,
            'check_in': time.strftime('%Y-%m-10 10:00'),
        })

    def test_attendance_in_before_out(self):
        # Make sure check_out is before check_in
        with self.assertRaises(Exception):
            self.my_attend = self.attendance.create({
                'employee_id': self.test_employee.id,
                'check_in': time.strftime('%Y-%m-10 12:00'),
                'check_out': time.strftime('%Y-%m-10 11:00'),
            })

    def test_attendance_no_check_out(self):
        # Make sure no second attandance without check_out can be created
        with self.assertRaises(Exception):
            self.attendance.create({
                'employee_id': self.test_employee.id,
                'check_in': time.strftime('%Y-%m-10 11:00'),
            })

    # 5 next tests : Make sure that when attendances overlap an error is raised
    def test_attendance_1(self):
        self.attendance.create({
            'employee_id': self.test_employee.id,
            'check_in': time.strftime('%Y-%m-10 07:30'),
            'check_out': time.strftime('%Y-%m-10 09:00'),
        })
        with self.assertRaises(Exception):
            self.attendance.create({
                'employee_id': self.test_employee.id,
                'check_in': time.strftime('%Y-%m-10 08:30'),
                'check_out': time.strftime('%Y-%m-10 09:30'),
            })

    def test_new_attendances(self):
        # Make sure attendance modification raises an error when it causes an overlap
        self.attendance.create({
            'employee_id': self.test_employee.id,
            'check_in': time.strftime('%Y-%m-10 11:00'),
            'check_out': time.strftime('%Y-%m-10 12:00'),
        })
        with self.assertRaises(Exception):
            self.open_attendance.write({
                'check_out': time.strftime('%Y-%m-10 11:30'),
            })

    def test_overlap_error_names_conflicting_check_in(self):
        employee = self.env['hr.employee'].create({'name': "Overlap"})
        existing = self.attendance.create({
            'employee_id': employee.id,
            'check_in': '2024-02-05 07:30:00',
            'check_out': '2024-02-05 12:00:00',
        })
        with self.assertRaises(ValidationError) as error:
            self.attendance.create({
                'employee_id': employee.id,
                'check_in': '2024-02-05 10:00:00',
                'check_out': '2024-02-05 13:00:00',
            })
        self.assertIn(format_datetime(self.env, existing.check_in, dt_format=False), str(error.exception))

    @freeze_time("2024-02-05 11:00:00")
    def test_attendance_in_the_future(self):
        employee = self.env['hr.employee'].create({'name': "Test"})
        self.attendance.create({
            'employee_id': employee.id,
            'check_in': time.strftime('2024-02-10 11:00'),
            'check_out': time.strftime('2024-02-10 12:00'),
        })
        open_attendance = self.env['hr.attendance'].create({
            'employee_id': employee.id,
            'check_in': time.strftime('2024-02-05 10:00'),
        })

        self.assertEqual(employee.attendance_state, 'checked_in')

        open_attendance.write({
            'check_out': time.strftime('2024-02-05 11:30'),
        })

        self.assertEqual(employee.attendance_state, 'checked_out')

    def test_time_format_attendance(self):
        # on a working day of the employee: a weekend day or a day before the first version
        # (created today) would be counted as overtime by the default time rule
        self.test_employee.version_id.date_version = '2024-01-01'
        attendance_id = self.attendance.create({
            'employee_id': self.test_employee.id,
            'check_in': '2024-02-05 08:00',  # a Monday
            'check_out': '2024-02-05 09:00',
        })
        self.assertEqual(attendance_id.display_name, "A - 1h")

    def test_overlap_same_check_in(self):
        """Two attendances of an employee starting at the same time overlap."""
        self.attendance.create({
            'employee_id': self.test_employee.id,
            'check_in': '2024-02-05 08:00:00',
            'check_out': '2024-02-05 12:00:00',
        })
        with self.assertRaises(ValidationError):
            self.attendance.create({
                'employee_id': self.test_employee.id,
                'check_in': '2024-02-05 08:00:00',
                'check_out': '2024-02-05 09:00:00',
            })

    def test_overlap_within_same_batch(self):
        """Attendances created together are checked against each other. The employee has no
        attendance yet, as the open one of ``test_employee`` would raise on its own."""
        employee = self.env['hr.employee'].create({'name': "Batch"})
        for vals_list in [
            [  # two closed attendances overlapping each other
                {'check_in': '2024-02-05 08:00:00', 'check_out': '2024-02-05 12:00:00'},
                {'check_in': '2024-02-05 11:00:00', 'check_out': '2024-02-05 13:00:00'},
            ],
            [  # two open attendances
                {'check_in': '2024-02-05 08:00:00'},
                {'check_in': '2024-02-06 08:00:00'},
            ],
        ]:
            with self.subTest(vals_list=vals_list), self.assertRaises(ValidationError):
                self.attendance.create([dict(vals, employee_id=employee.id) for vals in vals_list])

    def test_overlap_boundaries(self):
        """An attendance may start exactly when the previous one ends, but not a second before,
        and may last zero seconds. The employee has no attendance yet, as the open one of
        ``test_employee`` is always read by the check."""
        employee = self.env['hr.employee'].create({'name': "Boundaries"})
        self.attendance.create({
            'employee_id': employee.id,
            'check_in': '2024-02-05 08:00:00',
            'check_out': '2024-02-05 12:00:00',
        })
        with self.assertRaises(ValidationError):
            self.attendance.create({
                'employee_id': employee.id,
                'check_in': '2024-02-05 11:59:59',
                'check_out': '2024-02-05 13:00:00',
            })
        self.attendance.create({
            'employee_id': employee.id,
            'check_in': '2024-02-05 12:00:00',
            'check_out': '2024-02-05 13:00:00',
        })
        self.attendance.create({
            'employee_id': employee.id,
            'check_in': '2024-02-05 14:00:00',
            'check_out': '2024-02-05 14:00:00',
        })

    def test_overlap_in_distant_periods_of_batch(self):
        """The attendances of a batch far apart in time are each checked against their own period."""
        self.attendance.create({
            'employee_id': self.test_employee.id,
            'check_in': '2026-02-05 08:00:00',
            'check_out': '2026-02-05 12:00:00',
        })
        with self.assertRaises(ValidationError):
            self.attendance.create([{
                'employee_id': self.test_employee.id,
                'check_in': '2024-02-05 08:00:00',
                'check_out': '2024-02-05 12:00:00',
            }, {
                'employee_id': self.test_employee.id,
                'check_in': '2026-02-05 11:00:00',
                'check_out': '2026-02-05 13:00:00',
            }])


@tagged('post_install', '-at_install')
class TestHrAttendancePerformance(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        new_test_user(cls.env, login='hr_attendance_officer', groups='hr_attendance.group_hr_attendance_user')
        employees = cls.env['hr.employee'].create([{'name': f"Employee {i}"} for i in range(10)])
        cls.attendances = cls.env['hr.attendance'].create([{
            'employee_id': employee.id,
            'check_in': f'2024-02-0{day} 08:00:00',
            'check_out': f'2024-02-0{day} 12:00:00',
        } for employee in employees for day in range(1, 6)])

    @users('hr_attendance_officer')
    @warmup
    def test_check_validity_query_count(self):
        """The overlap check runs the same number of queries for one attendance as for a batch."""
        for size in (1, len(self.attendances)):
            attendances = self.env['hr.attendance'].browse(self.attendances.ids[:size])
            with self.subTest(size=size), self.assertQueryCount(hr_attendance_officer=2):  # fetch the batch + search the conflicts
                attendances._check_validity()
