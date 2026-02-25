# -*- coding: utf-8 -*-

from datetime import date, datetime, UTC
from unittest.mock import patch
from zoneinfo import ZoneInfo

from odoo import Command, fields
from odoo.tests import Form, new_test_user
from odoo.tests.common import tagged, TransactionCase, freeze_time


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
            'ruleset_id': False,
        })
        cls.employee_kiosk = cls.env['hr.employee'].create({
            'name': "Machiavel",
            'pin': '5678',
        })
        cls.calendar_40h = cls.env['resource.calendar'].create({
            'attendance_ids': [
                Command.create({
                        'dayofweek': weekday,
                        'hour_from': 8.0,
                        'hour_to': 17.0,
                })
                for weekday in ['0', '1', '2', '3', '4']
            ],
            'name': 'calendar 40h/week',
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

    @freeze_time("2024-02-01 10:00:00")
    def test_attendance_checkout_while_employee_archived(self):
        """An employee should be checked out by the system, if employee is getting archive.
            additionally his presence_state should be in archive state.
        """

        self.jonathon_user = new_test_user(self.env, login='jonathan_user', groups='base.group_user')
        jonathon_employee = self.env['hr.employee'].create({
            'contract_date_start': date(2021, 1, 1),
            'date_version': date(2021, 1, 1),
            'email': 'jonathan.joestar@example.com',
            'name': 'jonathan joestar',
            'resource_calendar_id': self.calendar_40h.id,
            'user_id': self.jonathon_user.id,
        })
        self.assertEqual(jonathon_employee.hr_icon_display, 'presence_absent')

        jonathon_attendance = self.env['hr.attendance'].create({
            'check_in': datetime(2024, 1, 2, 8, 0),
            'employee_id': jonathon_employee.id,
        })
        self.assertEqual(jonathon_employee.hr_icon_display, 'presence_present')

        with freeze_time("2024-01-03 20:00:00"):
            jonathon_employee.action_archive()
            self.assertEqual(jonathon_employee.hr_icon_display, 'presence_archive')
            self.assertEqual(jonathon_attendance.check_out, fields.Datetime.now())

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
