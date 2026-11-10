# -*- coding: utf-8 -*-

from freezegun import freeze_time
import time

from odoo.exceptions import ValidationError
from odoo.tests.common import tagged, TransactionCase
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

    def test_batch_validity(self):
        """A batch of attendances is checked with a single query, against each other and the existing attendances."""
        employees = self.env['hr.employee'].create([{'name': "Batch 1"}, {'name': "Batch 2"}])
        attendances = self.attendance.create([{
            'employee_id': employee.id,
            'check_in': f'2024-03-{day:02} 08:00:00',
            'check_out': f'2024-03-{day:02} 12:00:00',
        } for employee in employees for day in range(1, 11)])
        attendances.invalidate_recordset()
        with self.assertQueryCount(2):  # the times of the attendances, then the attendances they are checked against
            attendances._check_validity()
        self.attendance._check_validity()  # nothing to check

        with self.assertRaisesRegex(ValidationError, "Batch 2, the employee was already checked in on"):
            self.attendance.create([{
                'employee_id': employees[0].id,
                'check_in': '2024-03-20 08:00:00',
                'check_out': '2024-03-20 12:00:00',
            }, {
                'employee_id': employees[1].id,
                'check_in': '2024-03-01 10:00:00',
                'check_out': '2024-03-01 13:00:00',
            }])
        with self.assertRaisesRegex(ValidationError, "Batch 1, the employee hasn't checked out since"):
            self.attendance.create([{
                'employee_id': employees[0].id,
                'check_in': f'2024-03-2{day} 08:00:00',
            } for day in (1, 2)])

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
        attendance_id = self.attendance.create({
            'employee_id': self.test_employee.id,
            'check_in': time.strftime('%Y-%m-28 08:00'),
            'check_out': time.strftime('%Y-%m-28 09:00'),
        })
        self.assertEqual(attendance_id.display_name, "A 1h")
