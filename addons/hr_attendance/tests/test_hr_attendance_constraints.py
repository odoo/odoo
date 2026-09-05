# -*- coding: utf-8 -*-

from freezegun import freeze_time
import time

from odoo.tests.common import tagged, TransactionCase


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
        # display_name now shows duration only (no time range); WET display_code prefixed when set
        self.assertEqual(attendance_id.display_name, "1h")
