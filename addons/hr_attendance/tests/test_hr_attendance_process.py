# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase


class TestHrAttendance(TransactionCase):
    """Test for presence validity"""

    def setUp(self):
        super(TestHrAttendance, self).setUp()
        self.test_employee = self.browse_ref('hr.employee_al')

    def test_employee_state(self):
        # Make sure the attendance of the employee will display correctly
        assert self.test_employee.attendance_state == 'checked_out'
        self.test_employee.attendance_action_change()
        assert self.test_employee.attendance_state == 'checked_in'
        self.test_employee.attendance_action_change()
        assert self.test_employee.attendance_state == 'checked_out'
