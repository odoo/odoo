# -*- coding: utf-8 -*-

import pytz
from datetime import datetime
from freezegun import freeze_time
from unittest.mock import patch

from odoo import fields
from odoo.tests import new_test_user
from odoo.tests.common import tagged, TransactionCase


@tagged('attendance_process')
class TestHrAttendance(TransactionCase):
    """Test for presence validity"""

    @classmethod
    def setUpClass(cls):
        super(TestHrAttendance, cls).setUpClass()
        cls.user = new_test_user(cls.env, login='fru', groups='base.group_user')
        cls.user_no_pin = new_test_user(cls.env, login='gru', groups='base.group_user')
        cls.test_employee = cls.env['hr.employee'].create({
            'name': "François Russie",
            'user_id': cls.user.id,
            'pin': '1234',
        })
        cls.employee_kiosk = cls.env['hr.employee'].create({
            'name': "Machiavel",
            'pin': '5678',
        })

    def setUp(self):
        super().setUp()
        # Cache error if not done during setup
        (self.test_employee | self.employee_kiosk).last_attendance_id.unlink()

    def test_employee_state(self):
        # Make sure the attendance of the employee will display correctly
        assert self.test_employee.attendance_state == 'checked_out'
        self.test_employee._attendance_action_change()
        assert self.test_employee.attendance_state == 'checked_in'
        self.test_employee._attendance_action_change()
        assert self.test_employee.attendance_state == 'checked_out'

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

    def test_attendance_checkout_while_employee_archived(self):
        """An employee should be checked out by the system, if employee is getting archive."""
        test_attendance = self.env['hr.attendance'].create({
            'check_in': datetime(2024, 1, 1, 8, 0),
            'employee_id': self.test_employee.id,
        })

        with freeze_time("2024-01-01 17:00:00"):
            self.test_employee.action_archive()
            self.assertEqual(test_attendance.check_out, fields.Datetime.now())
            self.assertEqual(test_attendance.worked_hours, 8.0)
