# -*- coding: utf-8 -*-

from datetime import datetime, UTC
from unittest.mock import patch
from zoneinfo import ZoneInfo

from odoo import fields
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
        cls.company = cls.env.company
        cls.employee = cls.env['hr.employee'].create({'name': 'Employee', 'tz': 'UTC'})
        cls.other_employee = cls.env['hr.employee'].create({'name': 'Other Employee', 'tz': 'UTC'})
        cls.jpn_employee = cls.env['hr.employee'].create({'name': 'Japan Employee', 'tz': 'Asia/Tokyo'})
        cls.honolulu_employee = cls.env['hr.employee'].create({'name': 'Honolulu Employee', 'tz': 'Pacific/Honolulu'})
        cls.no_contract_employee = cls.env['hr.employee'].create({'name': 'No Contract Employee', 'tz': 'UTC'})
        cls.future_contract_employee = cls.env['hr.employee'].create({'name': 'Future Contract Employee', 'tz': 'UTC'})
        cls.flexible_employee = cls.env['hr.employee'].create({'name': 'Flexible Employee', 'tz': 'UTC'})

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

    @freeze_time("2026-02-26 07:00:00")
    def test_auto_check_out_specific_time(self):
        """Test various check-in times with 06:00 cutoff"""
        self.company.write({
            'auto_check_out': True,
            'auto_check_out_mode': 'specific_time',
            'auto_check_out_specific_time': 6.0,
        })
        night_shift, before_cutoff, one_min_before, midnight, just_after_midnight, already_checked, flexible = self.env['hr.attendance'].create([
            {'employee_id': self.employee.id, 'check_in': datetime(2026, 2, 25, 22, 0)},
            {'employee_id': self.other_employee.id, 'check_in': datetime(2026, 2, 26, 1, 0)},
            {'employee_id': self.jpn_employee.id, 'check_in': datetime(2026, 2, 25, 15, 0)},
            {'employee_id': self.honolulu_employee.id, 'check_in': datetime(2026, 2, 25, 12, 0)},
            {'employee_id': self.no_contract_employee.id, 'check_in': datetime(2026, 2, 25, 23, 1)},
            {'employee_id': self.future_contract_employee.id, 'check_in': datetime(2026, 2, 26, 1, 0), 'check_out': datetime(2026, 2, 26, 4, 30)},
            {'employee_id': self.flexible_employee.id, 'check_in': datetime(2026, 2, 26, 1, 0)},
        ])
        initial_checkout = already_checked.check_out
        self.assertEqual(night_shift.check_out, False)
        self.env['hr.attendance']._cron_auto_check_out_specific_time()
        self.assertEqual(night_shift.check_out, datetime(2026, 2, 26, 6, 0))
        self.assertEqual(night_shift.out_mode, 'auto_check_out')
        self.assertEqual(before_cutoff.check_out, datetime(2026, 2, 26, 6, 0))
        # 06:00 JST = 21:00 UTC previous day (JST = UTC+09:00)
        self.assertEqual(one_min_before.check_out, datetime(2026, 2, 25, 21, 0))
        # 06:00 HST = 16:00 UTC (HST = UTC-10:00)
        self.assertEqual(midnight.check_out, datetime(2026, 2, 25, 16, 0))
        self.assertEqual(just_after_midnight.check_out, datetime(2026, 2, 26, 6, 0))
        self.assertEqual(already_checked.check_out, initial_checkout)
        self.assertEqual(flexible.check_out, datetime(2026, 2, 26, 6, 0))

    @freeze_time("2026-02-27 13:00:00")
    def test_auto_check_out_specific_time_old_attendances(self):
        """Test multiday forgotten and backdated attendances"""
        self.company.write({
            'auto_check_out': True,
            'auto_check_out_mode': 'specific_time',
            'auto_check_out_specific_time': 6.0,
        })
        multiday, backdated, very_old = self.env['hr.attendance'].create([
            {'employee_id': self.employee.id, 'check_in': datetime(2026, 2, 24, 1, 0)},
            {'employee_id': self.other_employee.id, 'check_in': datetime(2026, 2, 25, 2, 0)},
            {'employee_id': self.jpn_employee.id, 'check_in': datetime(2026, 2, 25, 16, 0)},
        ])
        self.env['hr.attendance']._cron_auto_check_out_specific_time()
        self.assertEqual(multiday.check_out, datetime(2026, 2, 24, 6, 0))
        self.assertEqual(backdated.check_out, datetime(2026, 2, 25, 6, 0))
        self.assertEqual(very_old.check_out, datetime(2026, 2, 25, 21, 0))

    @freeze_time("2026-02-27 00:30:00")
    def test_auto_check_out_specific_time_edge_times(self):
        """Test cutoff times at start and end of day"""
        self.company.write({
            'auto_check_out': True,
            'auto_check_out_mode': 'specific_time',
            'auto_check_out_specific_time': 23.98,
        })
        end_of_day = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2026, 2, 26, 4, 30),
        })
        self.env['hr.attendance']._cron_auto_check_out_specific_time()
        self.assertEqual(end_of_day.check_out, datetime(2026, 2, 26, 23, 59))
        with freeze_time("2026-02-26 07:00:00"):
            self.company.write({'auto_check_out_specific_time': 0.0})
            start_of_day = self.env['hr.attendance'].create({
                'employee_id': self.other_employee.id,
                'check_in': datetime(2026, 2, 25, 16, 30),
            })
            self.env['hr.attendance']._cron_auto_check_out_specific_time()
            self.assertEqual(start_of_day.check_out, datetime(2026, 2, 26, 0, 0))

    def test_auto_check_out_two_weeks_calendar(self):
        """Test case: two weeks calendar with different attendances depending on the week. No morning attendance on
        wednesday of the first week."""
        self.company.write({
            'auto_check_out': True,
            'auto_check_out_tolerance': 0
        })
        self.employee.resource_calendar_id.write({
            'calendar_type': 'variable',
            'attendance_ids': [(5, 0, 0),
                               (0, 0, {'date': datetime(2025, 3, 5), 'hour_from': 12, 'hour_to': 16}),
                               (0, 0, {'date': datetime(2025, 3, 12), 'hour_from': 8, 'hour_to': 16})],
        })

        with freeze_time("2025-03-05 22:00:00"):
            att = self.env['hr.attendance'].create({
                'employee_id': self.employee.id,
                'check_in': datetime(2025, 3, 5, 8, 0)
            })
            self.env['hr.attendance']._cron_auto_check_out()
            self.assertEqual(att.worked_hours, 4)
            self.assertEqual(att.check_out, datetime(2025, 3, 5, 12, 0))

        with freeze_time("2025-03-12 22:00:00"):
            att = self.env['hr.attendance'].create({
                'employee_id': self.employee.id,
                'check_in': datetime(2025, 3, 12, 8, 0),
            })
            self.env['hr.attendance']._cron_auto_check_out()
            self.assertEqual(att.worked_hours, 8)
            self.assertEqual(att.check_out, datetime(2025, 3, 12, 16, 0))


@tagged('attendance_process')
class TestAbsenceDetectionCron(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.absence_management = True
        cls.env.company.tz = 'UTC'
        cls.env.company.resource_calendar_id = cls.env['resource.calendar'].create({
            'name': '40h/week',
            'attendance_ids': [
                (0, 0, {'dayofweek': wd, 'hour_from': h, 'hour_to': h + 4})
                for wd in ['0', '1', '2', '3', '4']
                for h in [8, 13]
            ],
        })
        cls.att_type = cls.env.company._get_default_attendance_work_entry_type()
        cls.env.company.attendance_work_entry_type_id = cls.att_type

        cls.env['hr.time.rule'].search([]).write({'active': False})

        cls.absent_employee = cls.env['hr.employee'].create({
            'name': 'Absent Employee',
            'tz': 'UTC',
            'date_version': '2020-01-01',
            'contract_date_start': '2020-01-01',
            'wage': 3000,
        })

    @freeze_time('2024-01-02 06:00:00')  # yesterday = 2024-01-01 (Monday)
    def test_absence_no_rule_discards_technical(self):
        """Absent employee with no undertime rule: technical attendance is created then discarded."""
        self.env['hr.attendance']._cron_absence_detection()

        atts = self.env['hr.attendance'].search([('employee_id', '=', self.absent_employee.id)])
        self.assertFalse(atts,
                         "No undertime rule fired → technical attendance must be discarded")

    @freeze_time('2024-01-02 06:00:00')  # yesterday = 2024-01-01 (Monday)
    def test_absence_undertime_rule_creates_output(self):
        """Absent employee with an undertime rule: full scheduled day becomes an undertime output."""
        undertime_wet = self.env['hr.work.entry.type'].create({
            'name': 'Undertime', 'code': 'UT_CRON_TEST',
        })
        self.env['hr.time.rule'].create({
            'name': 'Daily Undertime',
            'threshold_operator': 'less_than',
            'calendar_source': 'employee',
            'quantity_period': 'day',
            'work_entry_type_id': undertime_wet.id,
            'condition_work_entry_type_ids': [(4, self.att_type.id)],
        })

        self.env['hr.attendance']._cron_absence_detection()

        tech_atts = self.env['hr.attendance'].search([
            ('employee_id', '=', self.absent_employee.id),
            ('in_mode', '=', 'technical'),
        ])
        self.assertEqual(len(tech_atts), 1,
                         "Technical attendance must be kept when it produced an output")

        output_atts = self.env['hr.attendance'].search([
            ('employee_id', '=', self.absent_employee.id),
            ('is_time_rule_output', '=', True),
        ])
        self.assertAlmostEqual(
            sum(a.worked_hours for a in output_atts), 8.0, places=2,
            msg="Full 8h schedule missed → 8h undertime output attendance",
        )

    @freeze_time('2024-01-02 06:00:00')  # yesterday = 2024-01-01 (Monday)
    def test_checked_in_employee_not_targeted(self):
        """Employee who already checked in yesterday is not touched by the cron."""
        self.env['hr.attendance'].create({
            'employee_id': self.absent_employee.id,
            'check_in': datetime(2024, 1, 1, 8, 0),
            'check_out': datetime(2024, 1, 1, 16, 0),
        })
        before = self.env['hr.attendance'].search([('employee_id', '=', self.absent_employee.id)])

        self.env['hr.attendance']._cron_absence_detection()

        after = self.env['hr.attendance'].search([('employee_id', '=', self.absent_employee.id)])
        self.assertEqual(
            before.ids, after.ids,
            "Cron must not create technical attendances for employees who already checked in",
        )
