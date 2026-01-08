# -*- coding: utf-8 -*-

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

    def test_time_format_attendance(self):
        self.env.user.tz = 'UTC'
        self.env['res.lang']._activate_lang('en_US')
        lang = self.env['res.lang']._lang_get(self.env.user.lang)
        lang.time_format = "%I:%M %p"  # here "%I:%M %p" represents AM:PM format
        attendance_id = self.attendance.create({
            'employee_id': self.test_employee.id,
            'check_in': time.strftime('%Y-%m-28 08:00'),
            'check_out': time.strftime('%Y-%m-28 09:00'),
        })
        self.assertEqual(attendance_id.display_name, "01:00 : (08:00 AM-09:00 AM)")
        lang.time_format = "%H:%M:%S"
        attendance_id._compute_display_name()
        self.assertEqual(attendance_id.display_name, "01:00 : (08:00:00-09:00:00)")
