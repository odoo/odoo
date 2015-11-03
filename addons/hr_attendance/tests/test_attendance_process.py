# -*- coding: utf-8 -*-

import time

from odoo.exceptions import ValidationError
from odoo.tests import common


class TestAttendanceProcess(common.TransactionCase):

    def setUp(self):
        super(TestAttendanceProcess, self).setUp()

        self.Attendance = self.env['hr.attendance']
        self.hr_employee_niv = self.ref('hr.employee_niv')
        # Create a user as 'HR Attendance Officer.'
        self.res_users_attendance_officer = self.env['res.users'].create({
            'company_id': self.ref('base.main_company'),
            'name': 'HR Officer',
            'login': 'ao',
            'password': 'ao',
            'groups_id': [(6, 0, [self.ref('base.group_hr_user')])]})
        self.hr_employee_al = self.env.ref('hr.employee_al').with_context({'uid': self.res_users_attendance_officer.id})

    def test_hr_attendance_process(self):
        # Give the access rights of Hr Officer to test attendance process.
        # In order to test attendance process in Odoo, I entry of signin of employee.

        self.hr_employee_al.attendance_action_change()
        # we need to clear cache before next action
        self.hr_employee_al.invalidate_cache()
        # -------------------------------------
        # I check that employee is "present".
        # -------------------------------------
        self.assertEqual(self.hr_employee_al.state, 'present', 'Employee should be in present state.')
        # After few seconds, employee sign's out.
        time.sleep(2)
        self.hr_employee_al.attendance_action_change()
        # again we need to clear cache before next action
        self.hr_employee_al.invalidate_cache()
        # -------------------------------------
        # I check that employee is "absent".
        # -------------------------------------
        self.assertEqual(self.hr_employee_al.state, 'absent', 'Employee should be in absent state.')

        # In order to check that first attendance must be sign in.
        with self.assertRaises(ValidationError):
            self.attendance = self.Attendance.create({
                'employee_id': self.hr_employee_niv,
                'name': time.strftime('%Y-%m-%d 09:59:25'),
                'action': 'sign_out'
            })

        # First of all, employee sign's in.
        self.attendance = self.Attendance.create({
            'employee_id': self.hr_employee_niv,
            'name': time.strftime('%Y-%m-%d 09:59:26'),
            'action': 'sign_in'
        })

        # Now employee is going to sign in prior to first sign in.
        with self.assertRaises(ValidationError):
            self.attendance = self.Attendance.create({
                'employee_id': self.hr_employee_niv,
                'name': time.strftime('%Y-%m-%d 09:59:25'),
                'action': 'sign_in'
            })

        # After that employee is going to sign in after first sign in.
        with self.assertRaises(ValidationError):
            self.attendance = self.Attendance.create({
                'employee_id': self.hr_employee_niv,
                'name': time.strftime('%Y-%m-%d 10:59:25'),
                'action': 'sign_in'
            })

        # After two hours, employee sign's out.
        self.attendance = self.Attendance.create({
            'employee_id': self.hr_employee_niv,
            'name': time.strftime('%Y-%m-%d 11:59:25'),
            'action': 'sign_out'
        })

        # Now employee is going to sign out prior to sirst sign out.
        with self.assertRaises(ValidationError):
            self.attendance = self.Attendance.create({
                'employee_id': self.hr_employee_niv,
                'name': time.strftime('%Y-%m-%d 10:59:25'),
                'action': 'sign_out'
            })

        # After that employee is going to sign out after first sign out.
        with self.assertRaises(ValidationError):
            self.attendance = self.Attendance.create({
                'employee_id': self.hr_employee_niv,
                'name': time.strftime('%Y-%m-%d 12:59:25'),
                'action': 'sign_out'
            })
