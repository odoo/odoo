# -*- coding: utf-8 -*-

import time

from odoo import fields
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

from dateutil.relativedelta import relativedelta


class TestHrAttendance(TransactionCase):
    """Tests for attendance date ranges validity"""

    def setUp(self):
        super(TestHrAttendance, self).setUp()
        self.attendance = self.env['hr.attendance']
        self.test_employee = self.env['hr.employee'].create({'name': "Jacky"})
        # demo data contains set up for self.test_employee
        self.open_attendance = self.attendance.create({
            'employee_id': self.test_employee.id,
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

    def test_updated_check_date_without_permissions(self):
        # Close open attendance
        self.open_attendance.unlink()
        # Make sure check_out can't be updated without proper permissions
        self.env.user.groups_id = self.env.ref('base.group_user')
        now = fields.Datetime.from_string(time.strftime('%Y-%m-10 11:30'))
        attendance = self.attendance.with_context(test_datetime_now=now).create({
            'employee_id': self.test_employee.id,
            'check_in': now,
        })
        attendance.write({'check_out': now})
        with self.assertRaises(ValidationError):
            attendance.write({
                'check_in': now - relativedelta(hours=1),
            })
        with self.assertRaises(ValidationError):
            attendance.write({
                'check_out': now + relativedelta(hours=1),
            })
        # Add permission to user to validate that check_out update is possible
        self.env.user.groups_id |= self.env.ref('hr_attendance.group_hr_attendance_user')
        attendance.write({
            'check_out': now + relativedelta(hours=1),
        })
