# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
import time


class TestHrAttendance(TransactionCase):
    """Tests for attendance date ranges validity"""

    def setUp(self):
        super(TestHrAttendance, self).setUp()
        self.attendance = self.env['hr.attendance']
        self.test_employee = self.browse_ref('hr.employee_qdp')
        # demo data contains set up for self.test_employee

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
        self.attendance.create({
            'employee_id': self.test_employee.id,
            'check_in': time.strftime('%Y-%m-10 10:00'),
        })
        with self.assertRaises(Exception):
            self.attendance.create({
                'employee_id': self.test_employee.id,
                'check_in': time.strftime('%Y-%m-10 11:00'),
            })

    # 5 next tests : Make sure that when attendances overlap an error is raised
    def test_attendance_1(self):
        with self.assertRaises(Exception):
            self.attendance.create({
                'employee_id': self.test_employee.id,
                'check_in': time.strftime('%Y-%m-10 08:30'),
                'check_out': time.strftime('%Y-%m-10 09:30'),
            })

    def test_attendance_2(self):
        with self.assertRaises(Exception):
            self.attendance.create({
                'employee_id': self.test_employee.id,
                'check_in': time.strftime('%Y-%m-10 07:30'),
                'check_out': time.strftime('%Y-%m-10 08:30'),
            })

    def test_attendance_3(self):
        with self.assertRaises(Exception):
            self.attendance.create({
                'employee_id': self.test_employee.id,
                'check_in': time.strftime('%Y-%m-10 07:30'),
                'check_out': time.strftime('%Y-%m-10 09:30'),
            })

    def test_attendance_4(self):
        with self.assertRaises(Exception):
            self.attendance.create({
                'employee_id': self.test_employee.id,
                'check_in': time.strftime('%Y-%m-10 08:15'),
                'check_out': time.strftime('%Y-%m-10 08:45'),
            })

    def test_attendance_5(self):
        self.attendance.create({
            'employee_id': self.test_employee.id,
            'check_in': time.strftime('%Y-%m-10 10:00'),
        })
        with self.assertRaises(Exception):
            self.attendance.create({
                'employee_id': self.test_employee.id,
                'check_in': time.strftime('%Y-%m-10 09:30'),
                'check_out': time.strftime('%Y-%m-10 10:30'),
            })

    def test_new_attendances(self):
        # Make sure attendance modification raises an error when it causes an overlap
        self.attendance.create({
            'employee_id': self.test_employee.id,
            'check_in': time.strftime('%Y-%m-10 11:00'),
            'check_out': time.strftime('%Y-%m-10 12:00'),
        })
        open_attendance = self.attendance.create({
            'employee_id': self.test_employee.id,
            'check_in': time.strftime('%Y-%m-10 10:00'),
        })
        with self.assertRaises(Exception):
            open_attendance.write({
                'check_out': time.strftime('%Y-%m-10 11:30'),
            })
