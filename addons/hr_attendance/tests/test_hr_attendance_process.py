# -*- coding: utf-8 -*-

import pytz
from datetime import datetime
from unittest.mock import patch

from odoo import fields
from odoo.tests import new_test_user
from odoo.tests.common import TransactionCase


class TestHrAttendance(TransactionCase):
    """Test for presence validity"""

    def setUp(self):
        super(TestHrAttendance, self).setUp()
        self.user = new_test_user(self.env, login='fru', groups='base.group_user,hr_attendance.group_hr_attendance_use_pin')
        self.user_no_pin = new_test_user(self.env, login='gru', groups='base.group_user')
        self.test_employee = self.env['hr.employee'].create({
            'name': "François Russie",
            'user_id': self.user.id,
            'pin': '1234',
        })
        self.employee_kiosk = self.env['hr.employee'].create({
            'name': "Machiavel",
            'pin': '5678',
        })

    def test_employee_state(self):
        # Make sure the attendance of the employee will display correctly
        assert self.test_employee.attendance_state == 'checked_out'
        self.test_employee._attendance_action_change()
        assert self.test_employee.attendance_state == 'checked_in'
        self.test_employee._attendance_action_change()
        assert self.test_employee.attendance_state == 'checked_out'

    def test_checkin_self_without_pin(self):
        """ Employee can check in/out without pin with his own account """
        employee = self.test_employee.with_user(self.user)
        employee.with_user(self.user).attendance_manual({}, entered_pin=None)
        self.assertEqual(employee.attendance_state, 'checked_in', "He should be able to check in without pin")
        employee.attendance_manual({}, entered_pin=None)
        self.assertEqual(employee.attendance_state, 'checked_out', "He should be able to check out without pin")

    def test_checkin_self_with_pin(self):
        """ Employee can check in/out with pin with his own account """
        employee = self.test_employee.with_user(self.user)
        employee.attendance_manual({}, entered_pin='1234')
        self.assertEqual(employee.attendance_state, 'checked_in', "He should be able to check in with his pin")
        employee.attendance_manual({}, entered_pin='1234')
        self.assertEqual(employee.attendance_state, 'checked_out', "He should be able to check out with his pin")

    def test_checkin_self_wrong_pin(self):
        """ Employee cannot check in/out with wrong pin with his own account """
        employee = self.test_employee.with_user(self.user)
        action = employee.attendance_manual({}, entered_pin='9999')
        self.assertNotEqual(employee.attendance_state, 'checked_in', "He should not be able to check in with a wrong pin")
        self.assertTrue(action.get('warning'))

    def test_checkin_kiosk_with_pin(self):
        """ Employee can check in/out with his pin in kiosk """
        employee = self.employee_kiosk.with_user(self.user)
        employee.attendance_manual({}, entered_pin='5678')
        self.assertEqual(employee.attendance_state, 'checked_in', "He should be able to check in with his pin")
        employee.attendance_manual({}, entered_pin='5678')
        self.assertEqual(employee.attendance_state, 'checked_out', "He should be able to check out with his pin")

    def test_checkin_kiosk_with_wrong_pin(self):
        """ Employee cannot check in/out with wrong pin in kiosk """
        employee = self.employee_kiosk.with_user(self.user)
        action = employee.attendance_manual({}, entered_pin='8888')
        self.assertNotEqual(employee.attendance_state, 'checked_in', "He should not be able to check in with a wrong pin")
        self.assertTrue(action.get('warning'))

    def test_checkin_kiosk_without_pin(self):
        """ Employee cannot check in/out without his pin in kiosk """
        employee = self.employee_kiosk.with_user(self.user)
        action = employee.attendance_manual({}, entered_pin=None)
        self.assertNotEqual(employee.attendance_state, 'checked_in', "He should not be able to check in with no pin")
        self.assertTrue(action.get('warning'))

    def test_checkin_kiosk_no_pin_mode(self):
        """ Employee cannot check in/out without pin in kiosk when user has not group `use_pin` """
        employee = self.employee_kiosk.with_user(self.user_no_pin)
        employee.attendance_manual({}, entered_pin=None)
        self.assertEqual(employee.attendance_state, 'checked_out', "He shouldn't be able to check in without")

    def test_hours_today(self):
        """ Test day start is correctly computed according to the employee's timezone """

        def tz_datetime(year, month, day, hour, minute):
            tz = pytz.timezone('Europe/Brussels')
            return tz.localize(datetime(year, month, day, hour, minute)).astimezone(pytz.utc).replace(tzinfo=None)

        employee = self.env['hr.employee'].create({'name': 'Cunégonde', 'tz': 'Europe/Brussels'})
        self.env['hr.attendance'].create({
            'employee_id': employee.id,
            'check_in': tz_datetime(2019, 3, 1, 22, 0),  # should count from midnight in the employee's timezone (=the previous day in utc!)
            'check_out': tz_datetime(2019, 3, 2, 2, 0),
        })
        self.env['hr.attendance'].create({
            'employee_id': employee.id,
            'check_in': tz_datetime(2019, 3, 2, 11, 0),
        })

        # now = 2019/3/2 14:00 in the employee's timezone
        with patch.object(fields.Datetime, 'now', lambda: tz_datetime(2019, 3, 2, 14, 0).astimezone(pytz.utc).replace(tzinfo=None)):
            self.assertEqual(employee.hours_today, 5, "It should have counted 5 hours")
