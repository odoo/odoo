# -*- coding: utf-8 -*-

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
        employee = self.test_employee.sudo(self.user)
        employee.sudo(self.user).attendance_manual({}, entered_pin=None)
        self.assertEqual(employee.attendance_state, 'checked_in', "He should be able to check in without pin")
        employee.attendance_manual({}, entered_pin=None)
        self.assertEqual(employee.attendance_state, 'checked_out', "He should be able to check out without pin")

    def test_checkin_self_with_pin(self):
        """ Employee can check in/out with pin with his own account """
        employee = self.test_employee.sudo(self.user)
        employee.attendance_manual({}, entered_pin='1234')
        self.assertEqual(employee.attendance_state, 'checked_in', "He should be able to check in with his pin")
        employee.attendance_manual({}, entered_pin='1234')
        self.assertEqual(employee.attendance_state, 'checked_out', "He should be able to check out with his pin")

    def test_checkin_self_wrong_pin(self):
        """ Employee cannot check in/out with wrong pin with his own account """
        employee = self.test_employee.sudo(self.user)
        action = employee.attendance_manual({}, entered_pin='9999')
        self.assertNotEqual(employee.attendance_state, 'checked_in', "He should not be able to check in with a wrong pin")
        self.assertTrue(action.get('warning'))

    def test_checkin_kiosk_with_pin(self):
        """ Employee can check in/out with his pin in kiosk """
        employee = self.employee_kiosk.sudo(self.user)
        employee.attendance_manual({}, entered_pin='5678')
        self.assertEqual(employee.attendance_state, 'checked_in', "He should be able to check in with his pin")
        employee.attendance_manual({}, entered_pin='5678')
        self.assertEqual(employee.attendance_state, 'checked_out', "He should be able to check out with his pin")

    def test_checkin_kiosk_with_wrong_pin(self):
        """ Employee cannot check in/out with wrong pin in kiosk """
        employee = self.employee_kiosk.sudo(self.user)
        action = employee.attendance_manual({}, entered_pin='8888')
        self.assertNotEqual(employee.attendance_state, 'checked_in', "He should not be able to check in with a wrong pin")
        self.assertTrue(action.get('warning'))

    def test_checkin_kiosk_without_pin(self):
        """ Employee cannot check in/out without his pin in kiosk """
        employee = self.employee_kiosk.sudo(self.user)
        action = employee.attendance_manual({}, entered_pin=None)
        self.assertNotEqual(employee.attendance_state, 'checked_in', "He should not be able to check in with no pin")
        self.assertTrue(action.get('warning'))

    def test_checkin_kiosk_no_pin_mode(self):
        """ Employee can check in/out without pin in kiosk when user has not group `use_pin` """
        employee = self.employee_kiosk.sudo(self.user_no_pin)
        employee.attendance_manual({}, entered_pin=None)
        self.assertEqual(employee.attendance_state, 'checked_in', "He should be able to check in with his pin")
        employee.attendance_manual({}, entered_pin=None)
        self.assertEqual(employee.attendance_state, 'checked_out', "He should be able to check out with his pin")
