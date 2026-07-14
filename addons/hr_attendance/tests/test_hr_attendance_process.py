# -*- coding: utf-8 -*-

from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from odoo import fields
from odoo.addons.hr_attendance.controllers.main import HrAttendance
from odoo.exceptions import ValidationError
from odoo.tests import Form, new_test_user
from odoo.tests.common import HttpCase, tagged, TransactionCase, freeze_time


@tagged('attendance_process')
class TestHrAttendance(HttpCase, TransactionCase):
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
            'ruleset_id': False,
        })
        cls.employee_kiosk = cls.env['hr.employee'].create({
            'name': "Machiavel",
            'pin': '5678',
        })
        cls.hr_user = cls.env['res.users'].create({
            'name': 'HR Officer',
            'login': 'hr_officer',
            'group_ids': [(6, 0, [
                cls.env.ref('hr.group_hr_user').id,
                # Explicitly NOT adding: hr_attendance.group_hr_attendance_user
            ])]
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

    def test_employee_group_id(self):
        # Create attendance for one of them
        self.env['hr.attendance'].create({
            'employee_id': self.employee_kiosk.id,
            'check_in': '2025-08-01 08:00:00',
            'check_out': '2025-08-01 17:00:00',
        })
        context = self.env.context.copy()
        context['read_group_expand'] = True

        groups = self.env['hr.attendance'].with_context(**context).web_read_group(
            domain=[],
            groupby=['employee_id']
        )
        groups = groups['groups']

        grouped_employee_ids = [g['employee_id'][0] for g in groups]

        self.assertNotIn(self.test_employee.id, grouped_employee_ids)
        self.assertIn(self.employee_kiosk.id, grouped_employee_ids)

        # Specific to gantt view.
        context['gantt_start_date'] = fields.Datetime.now()
        context['allowed_company_ids'] = [self.env.company.id]

        groups = self.env['hr.attendance'].with_context(**context).web_read_group(
            domain=[],
            groupby=['employee_id']
        )
        groups = groups['groups']

        grouped_employee_ids = [g['employee_id'][0] for g in groups]

        # Result should still be the same - test_employee is only added in
        # overridden get_gantt_data()
        self.assertNotIn(self.test_employee.id, grouped_employee_ids)
        self.assertIn(self.employee_kiosk.id, grouped_employee_ids)

    def test_hours_today(self):
        """ Test day start is correctly computed according to the employee's timezone """

        def tz_datetime(year, month, day, hour, minute):
            tz = ZoneInfo('Europe/Brussels')
            return datetime(year, month, day, hour, minute).replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)

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
        with patch.object(fields.Datetime, 'now', lambda: tz_datetime(2019, 3, 2, 14, 0).astimezone(UTC).replace(tzinfo=None)):
            self.assertEqual(employee.hours_today, 5, "It should have counted 5 hours")

    def test_remove_check_in_value_from_attendance(self):
        attendance_form = Form(self.env['hr.attendance'])
        attendance_form.employee_id = self.test_employee
        attendance_form.check_in = False
        with self.assertRaises(AssertionError):
            attendance_form.save()

    def test_attendance_checkout_while_employee_archived(self):
        """An employee should be checked out by the system, if employee is getting archive."""
        test_attendance = self.env['hr.attendance'].create({
            'check_in': datetime(2024, 1, 1, 8, 0),
            'employee_id': self.test_employee.id,
        })

        with freeze_time("2024-01-01 16:00:00"):
            self.test_employee.action_archive()
            self.assertEqual(test_attendance.check_out, fields.Datetime.now())
            self.assertEqual(test_attendance.worked_hours, 8.0)

    def test_break_duration_updates_worked_hours(self):
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.test_employee.id,
            'check_in': '2024-01-01 08:00:00',
            'check_out': '2024-01-01 17:00:00',
        })
        initial_hours = attendance.worked_hours
        with patch.object(fields.Datetime, 'now', lambda: datetime(2024, 1, 1, 18, 0, 0)):
            self.test_employee.invalidate_recordset(['hours_today'])
            initial_hours_today = self.test_employee.hours_today
            attendance.break_duration = 1.0
            self.assertAlmostEqual(attendance.worked_hours, max(initial_hours - 1.0, 0.0))
            self.assertAlmostEqual(self.test_employee.hours_today, attendance.worked_hours)
            self.assertAlmostEqual(self.test_employee.hours_today, initial_hours_today - 1.0)
        with self.assertRaises(ValidationError):
            attendance.break_duration = -1
        with self.assertRaises(ValidationError):
            attendance.break_duration = 12

    def test_hours_today_splits_break_proportionally_across_cross_midnight_attendance(self):
        employee = self.env['hr.employee'].create({'name': 'Cross Midnight', 'tz': 'UTC'})
        self.env['hr.attendance'].create({
            'employee_id': employee.id,
            'check_in': datetime(2024, 1, 1, 20),
            'check_out': datetime(2024, 1, 2, 2),
            'break_duration': 3,
        })

        with patch.object(fields.Datetime, 'now', lambda: datetime(2024, 1, 2, 3)):
            employee.invalidate_recordset(['hours_today'])
            self.assertAlmostEqual(employee.hours_today, 1, places=6)

    def test_hours_today_keeps_full_break_before_midnight_checkout(self):
        employee = self.env['hr.employee'].create({'name': 'Midnight Checkout', 'tz': 'UTC'})
        self.env['hr.attendance'].create({
            'employee_id': employee.id,
            'check_in': datetime(2024, 1, 1, 22),
            'check_out': datetime(2024, 1, 2),
            'break_duration': 2,
        })

        with patch.object(fields.Datetime, 'now', lambda: datetime(2024, 1, 1, 23)):
            employee.invalidate_recordset(['hours_today'])
            self.assertAlmostEqual(employee.hours_today, 0, places=6)

    def test_break_duration_normalization(self):
        self.assertEqual(HrAttendance._normalize_break_duration(0), 0.0)
        self.assertEqual(HrAttendance._normalize_break_duration("0.5"), 0.5)
        for duration in (None, False, True, "", "invalid", -1, float("inf"), float("nan")):
            with self.subTest(duration=duration):
                self.assertIsNone(HrAttendance._normalize_break_duration(duration))

    @freeze_time("2024-01-02 12:00:00")
    def test_user_attendance_details_are_opt_in(self):
        now = fields.Datetime.now()
        self.env['hr.attendance'].create({
            'employee_id': self.test_employee.id,
            'check_in': datetime(2024, 1, 1, 22),
            'check_out': datetime(2024, 1, 2, 2),
            'break_duration': 1,
        })
        future_attendance = self.env['hr.attendance'].create({
            'employee_id': self.test_employee.id,
            'check_in': now + timedelta(hours=2),
            'check_out': now + timedelta(hours=3),
        })
        tomorrow_attendance = self.env['hr.attendance'].create({
            'employee_id': self.test_employee.id,
            'check_in': now + timedelta(days=1),
            'check_out': now + timedelta(days=1, hours=1),
        })
        future_open_attendance = self.env['hr.attendance'].create({
            'employee_id': self.test_employee.id,
            'check_in': now + timedelta(hours=4),
        })

        public_payload = HrAttendance._get_user_attendance_data(self.test_employee)
        self.assertNotIn('last_attendance', public_payload)
        self.assertNotIn('break_today', public_payload)
        self.assertNotIn('in_location', public_payload['today_attendance_ids'][0])
        self.assertNotIn('can_edit', public_payload['today_attendance_ids'][0])
        self.assertEqual(public_payload['hours_today'], 1.5)
        self.assertEqual(public_payload['hours_previously_today'], 0)

        user_payload = HrAttendance._get_user_attendance_data(
            self.test_employee,
            include_attendance_details=True,
        )
        self.assertNotIn('last_attendance', user_payload)
        self.assertAlmostEqual(user_payload['break_today'], 0.5, places=6)
        self.assertIn('in_location', user_payload['today_attendance_ids'][0])
        self.assertIn('can_edit', user_payload['today_attendance_ids'][0])
        attendance_ids = [attendance['id'] for attendance in user_payload['today_attendance_ids']]
        self.assertIn(future_attendance.id, attendance_ids)
        self.assertIn(future_open_attendance.id, attendance_ids)
        self.assertNotIn(tomorrow_attendance.id, attendance_ids)
    # @freeze_time("2024-02-1")
    # def test_change_in_out_mode_when_manual_modification(self):
    #     TODO naja: cron should work eventually when the adjustment feature is back
    #     company = self.env['res.company'].create({
    #         'name': 'Monsters, Inc.',
    #         'absence_management': True,
    #     })

    #     employee = self.env['hr.employee'].create({
    #         'name': "James P. Sullivan",
    #         'company_id': company.id,
    #         'date_version': date(2021, 1, 1),
    #         'contract_date_start': date(2021, 1, 1),
    #     })
    #     breakpoint()

    #     self.env['hr.attendance']._cron_absence_detection()

    #     attendance = self.env['hr.attendance'].search([('employee_id', '=', employee.id)])

    #     self.assertEqual(attendance.in_mode, 'technical')
    #     self.assertEqual(attendance.out_mode, 'technical')
    #     self.assertEqual(attendance.color, 1)

    #     attendance.write({
    #         'check_in': datetime(2021, 1, 4, 8, 0),
    #         'check_out': datetime(2021, 1, 4, 17, 0),
    #     })

    #     self.assertEqual(attendance.in_mode, 'manual')
    #     self.assertEqual(attendance.out_mode, 'manual')
    #     self.assertEqual(attendance.color, 0)

    def test_attendance_checkout_while_employee_archived_without_rights(self):
        """Test that archiving employee by HR user closes attendance even if lacks of attendance permissions"""

        test_attendance = self.env['hr.attendance'].create({
            'employee_id': self.test_employee.id,
            'check_in': '2024-01-15 08:00:00',
        })

        with freeze_time("2024-01-15 17:00:00"):
            self.test_employee.with_user(self.hr_user).action_archive()
            self.assertTrue(not self.test_employee.active, "Employee should be archived successfully with sudo()")
            self.assertEqual(test_attendance.check_out, fields.Datetime.now(), "Attendance should be checked out at the time of archiving")

    def test_attendance_multicompany(self):
        """Test that the attendance is for the currently selected company, not default company of user"""

        first_company = self.user.employee_id.company_id
        self.assertTrue(first_company)

        other_company = self.env["res.company"].create({
            "name": "Test"
        })
        other_employee = self.env["hr.employee"].create({
            "name": self.user.name,
            "company_id": other_company.id,
            "user_id": self.user.id
        })

        self.user.password = 'password'
        self.authenticate(self.user.login, 'password')

        # first case check when no cids sent, second case check when cids included
        test_cases = [
            ("", self.user.employee_id.id),
            (f"{other_company.id}-{first_company.id}", other_employee.id),
        ]

        for cids, expected_employee_id in test_cases:
            with self.subTest(expected_employee_id=expected_employee_id):
                self.opener.cookies.set('cids', cids)
                employee = self.make_jsonrpc_request("/hr_attendance/systray_check_in_out", {})
                self.assertEqual(employee["id"], expected_employee_id)
