from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from odoo import fields
from odoo.addons.hr_attendance.controllers.main import HrAttendance
from odoo.exceptions import AccessError, ValidationError
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
        employee_now = tz_datetime(2019, 3, 2, 14, 0).astimezone(UTC).replace(tzinfo=None)
        with self.mock_datetime_and_now(employee_now):
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
        with self.mock_datetime_and_now(datetime(2024, 1, 1, 18, 0, 0)):
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

        with self.mock_datetime_and_now(datetime(2024, 1, 2, 3)):
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

        with self.mock_datetime_and_now(datetime(2024, 1, 1, 23)):
            employee.invalidate_recordset(['hours_today'])
            self.assertAlmostEqual(employee.hours_today, 0, places=6)

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
        self.assertNotIn('in_location', public_payload['today_attendance_ids'][0])
        self.assertNotIn('can_edit', public_payload['today_attendance_ids'][0])
        self.assertEqual(public_payload['hours_today'], 1.5)
        self.assertEqual(public_payload['hours_previously_today'], 0)

        user_payload = HrAttendance._get_user_attendance_data(
            self.test_employee,
            include_attendance_details=True,
        )
        self.assertNotIn('last_attendance', user_payload)
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

        other_company = self.add_company('base.test_company', {
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

    def test_auto_check_out_gives_no_extra_hours(self):
        """An automatic check-out gives the employee exactly the hours of their schedule.

        The tolerance only waits longer before checking out: the check-out is set where the scheduled hours end.
        """
        self.company.write({'auto_check_out': True, 'auto_check_out_tolerance': 2})
        self.employee.resource_calendar_id.write({
            'calendar_type': 'variable',
            'attendance_ids': [(5, 0, 0), (0, 0, {'date': datetime(2025, 3, 5), 'hour_from': 8, 'hour_to': 16})],
        })
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2025, 3, 5, 8, 0),
            'check_out': datetime(2025, 3, 5, 12, 0),
        })
        att = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2025, 3, 5, 13, 0),
        })
        # 8:00 + 8 hours of schedule + 1 hour of lunch = 17:00, then 2 hours of tolerance
        with freeze_time("2025-03-05 18:59:00"):
            self.env['hr.attendance']._cron_auto_check_out()
        self.assertFalse(att.check_out, "The employee is still within the tolerance")
        with freeze_time("2025-03-05 19:01:00"):
            self.env['hr.attendance']._cron_auto_check_out()
        self.assertRecordValues(att, [{
            'check_out': datetime(2025, 3, 5, 17, 0),
            'worked_hours': 4,
            'out_mode': 'auto_check_out',
        }])


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
            ('time_rule_id', '!=', False),
        ])
        self.assertAlmostEqual(
            sum(a.worked_hours for a in output_atts), 8.0, places=2,
            msg="Full 8h schedule missed → 8h undertime output attendance",
        )

    @freeze_time('2024-01-02 06:00:00')  # yesterday = 2024-01-01 (Monday)
    def test_undertime_output_ignores_refused_attendance(self):
        """A refused attendance does not prevent the undertime output from covering its span."""
        undertime_wet = self.env['hr.work.entry.type'].create({
            'name': 'Undertime', 'code': 'UT_REFUSED_TEST',
        })
        rule = self.env['hr.time.rule'].create({
            'name': 'Daily Undertime',
            'threshold_operator': 'less_than',
            'calendar_source': 'employee',
            'quantity_period': 'day',
            'work_entry_type_id': undertime_wet.id,
            'condition_work_entry_type_ids': [(4, self.att_type.id)],
        })
        self.env['hr.attendance'].create({
            'employee_id': self.absent_employee.id,
            'check_in': datetime(2024, 1, 1, 8, 0),
            'check_out': datetime(2024, 1, 1, 12, 0),
            'state': 'refused',
        })
        self.env['hr.attendance'].create({
            'employee_id': self.absent_employee.id,
            'check_in': datetime(2024, 1, 1, 13, 0),
            'check_out': datetime(2024, 1, 1, 14, 0),
        })
        outputs = self.env['hr.attendance'].search([
            ('employee_id', '=', self.absent_employee.id),
            ('time_rule_id', '=', rule.id),
        ], order='check_in')
        self.assertEqual(
            [(a.check_in, a.check_out) for a in outputs],
            [(datetime(2024, 1, 1, 8, 0), datetime(2024, 1, 1, 12, 0)),
             (datetime(2024, 1, 1, 14, 0), datetime(2024, 1, 1, 17, 0))],
        )

    @freeze_time('2024-01-02 06:00:00')  # yesterday = 2024-01-01 (Monday)
    def test_absence_undertime_rule_timezones(self):
        """The absence is detected on the local day of the employee, whatever their timezone."""
        undertime_wet = self.env['hr.work.entry.type'].create({
            'name': 'Undertime', 'code': 'UT_CRON_TZ_TEST',
        })
        rule = self.env['hr.time.rule'].create({
            'name': 'Daily Undertime',
            'threshold_operator': 'less_than',
            'calendar_source': 'employee',
            'quantity_period': 'day',
            'work_entry_type_id': undertime_wet.id,
            'condition_work_entry_type_ids': [(4, self.att_type.id)],
        })
        self.absent_employee.contract_date_end = '2023-12-31'
        for tz in ('Europe/Brussels', 'Asia/Tokyo', 'Pacific/Honolulu', 'UTC'):
            employee = self.env['hr.employee'].create({
                'name': f'Absent Employee {tz}',
                'tz': tz,
                'date_version': '2020-01-01',
                'contract_date_start': '2020-01-01',
                'wage': 3000,
            })
            self.env['hr.attendance']._cron_absence_detection()
            outputs = self.env['hr.attendance'].search([
                ('employee_id', '=', employee.id),
                ('time_rule_id', '=', rule.id),
            ])
            self.assertAlmostEqual(sum(outputs.mapped('worked_hours')), 8.0, places=2, msg=tz)
            self.assertEqual(set(outputs.mapped('date')), {date(2024, 1, 1)}, tz)
            employee.contract_date_end = '2023-12-31'

    @freeze_time('2024-01-02 06:00:00')  # yesterday = 2024-01-01 (Monday)
    def test_absence_after_contract_end(self):
        """Employee whose contract ended before yesterday is not targeted by the cron."""
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
        self.absent_employee.contract_date_end = '2023-12-31'

        self.env['hr.attendance']._cron_absence_detection()

        atts = self.env['hr.attendance'].search([('employee_id', '=', self.absent_employee.id)])
        self.assertFalse(atts, "No technical attendance must be created after the end of the contract")

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


@tagged('attendance_process')
class TestAttendanceValidationTimeRules(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
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
        cls.overtime_type = cls.env['hr.work.entry.type'].create({
            'name': 'Overtime', 'code': 'OT_VALIDATION_TEST',
        })
        cls.rule = cls.env['hr.time.rule'].create({
            'name': 'Daily Overtime',
            'calendar_source': 'employee',
            'quantity_period': 'day',
            'work_entry_type_id': cls.overtime_type.id,
            'condition_work_entry_type_ids': [(4, cls.att_type.id)],
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Validated Employee',
            'tz': 'UTC',
            'date_version': '2020-01-01',
            'contract_date_start': '2020-01-01',
            'wage': 3000,
        })
        cls.light_user = new_test_user(
            cls.env, login='light_att', groups='base.group_user,hr_attendance.group_hr_attendance_own',
        )
        cls.employee.user_id = cls.light_user

    def _get_overtime_hours(self):
        outputs = self.env['hr.attendance'].search([
            ('employee_id', '=', self.employee.id),
            ('time_rule_id', '=', self.rule.id),
            ('state', '=', 'validated'),
        ])
        return sum(outputs.mapped('worked_hours'))

    def _create_kiosk_attendances(self, *spans):
        return self.env['hr.attendance'].create([{
            'employee_id': self.employee.id,
            'check_in': datetime(2024, 1, 1, *start),  # Monday, 8-12 and 13-17 expected
            'check_out': datetime(2024, 1, 1, *stop),
            'in_mode': 'kiosk',
            'out_mode': 'kiosk',
        } for start, stop in spans])

    @freeze_time('2024-01-03 06:00:00')
    def test_manager_encoded_attendance_runs_time_rules(self):
        self.env.company.attendance_validation = 'manual_validation'
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2024, 1, 1, 8, 0),  # Monday, 8h expected
            'check_out': datetime(2024, 1, 1, 17, 0),
        })
        self.assertEqual(attendance.state, 'validated')
        self.assertAlmostEqual(self._get_overtime_hours(), 1.0)

    @freeze_time('2024-01-03 06:00:00')
    def test_exceptions_only_on_check_out_runs_time_rules(self):
        """A clock-out without exception is reviewed at once, overtime waits for a review."""
        self.env.company.attendance_validation = 'exception_validation'
        self.env.company.attendance_validation_tolerance = 15
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2024, 1, 1, 8, 0),
            'in_mode': 'kiosk',
        })
        self.assertEqual(attendance.state, 'draft')
        attendance.write({'check_out': datetime(2024, 1, 1, 17, 0), 'out_mode': 'kiosk'})
        self.assertRecordValues(attendance, [{'is_overtime': True, 'state': 'draft'}])
        self.assertFalse(self._get_overtime_hours())

        # the lunch break recorded at the kiosk after the check-out
        attendance.break_duration = 1.0
        self.assertRecordValues(attendance, [{'is_overtime': False, 'state': 'validated'}])
        self.assertFalse(self._get_overtime_hours())

    @freeze_time('2024-01-03 06:00:00')
    def test_issue_flags(self):
        self.env.company.attendance_validation = 'exception_validation'
        self.env.company.attendance_validation_tolerance = 15
        morning, afternoon = self._create_kiosk_attendances(((8, 30), (12, 0)), ((13, 0), (16, 30)))
        self.assertRecordValues(morning | afternoon, [
            {'is_late_check_in': True, 'is_early_check_out': False, 'is_overtime': False, 'has_issue': True, 'state': 'draft'},
            {'is_late_check_in': False, 'is_early_check_out': True, 'is_overtime': False, 'has_issue': True, 'state': 'draft'},
        ])
        self.assertEqual(
            self.env['hr.attendance'].search([('is_late_check_in', '=', True), ('employee_id', '=', self.employee.id)]),
            morning, "The flags are stored, so that the filters and counters can search them",
        )

        # within the tolerance, the day is reviewed
        afternoon.write({'check_out': datetime(2024, 1, 1, 17, 10), 'out_mode': 'kiosk'})
        morning.write({'check_in': datetime(2024, 1, 1, 8, 5), 'in_mode': 'kiosk'})
        self.assertRecordValues(morning | afternoon, [
            {'has_issue': False, 'state': 'validated'},
            {'has_issue': False, 'state': 'validated'},
        ])

    @freeze_time('2024-01-06 06:00:00')
    def test_undertime(self):
        """A day with fewer worked hours than expected is an undertime, flagged on its last attendance."""
        self.env.company.attendance_validation = 'exception_validation'
        self.env.company.attendance_validation_tolerance = 15
        Attendance = self.env['hr.attendance']
        kiosk = {'employee_id': self.employee.id, 'in_mode': 'kiosk', 'out_mode': 'kiosk'}
        morning, afternoon = Attendance.create([{
            **kiosk, 'check_in': datetime(2024, 1, 1, 8, 0), 'check_out': datetime(2024, 1, 1, 12, 0),
        }, {
            # Monday, 8-12 and 13-17 expected: on time, but a long break
            **kiosk, 'check_in': datetime(2024, 1, 1, 13, 0), 'check_out': datetime(2024, 1, 1, 17, 0), 'break_duration': 1,
        }])
        self.assertRecordValues(morning | afternoon, [
            {'is_undertime': False, 'is_early_check_out': False, 'has_issue': False, 'state': 'validated'},
            {'is_undertime': True, 'is_early_check_out': False, 'has_issue': True, 'state': 'draft'},
        ])
        self.assertEqual(
            Attendance.search([('is_undertime', '=', True), ('employee_id', '=', self.employee.id)]), afternoon,
        )
        # within the tolerance
        afternoon.break_duration = 0.1
        self.assertRecordValues(afternoon, [{'is_undertime': False, 'state': 'validated'}])

        open_day, auto_checked_out, day_off = Attendance.create([{
            # Tuesday, still at work
            'employee_id': self.employee.id, 'check_in': datetime(2024, 1, 2, 8, 0), 'in_mode': 'kiosk',
        }, {
            # Wednesday, checked out by the cron: no undertime, it goes to review as such
            **kiosk, 'check_in': datetime(2024, 1, 3, 8, 0), 'check_out': datetime(2024, 1, 3, 10, 0),
            'out_mode': 'auto_check_out',
        }, {
            # Saturday
            **kiosk, 'check_in': datetime(2024, 1, 6, 1, 0), 'check_out': datetime(2024, 1, 6, 2, 0),
        }])
        self.assertFalse(open_day.is_undertime)
        self.assertRecordValues(auto_checked_out, [{'is_undertime': False, 'state': 'draft'}])
        self.assertRecordValues(day_off, [{'is_undertime': False, 'is_overtime': True}])

    @freeze_time('2024-01-03 06:00:00')
    def test_issues_follow_time_off(self):
        """A morning off approved after the afternoon was worked: the afternoon is neither late nor short any more,
        and is reviewed, which runs the time rules. Taken back, the issues come back, but the attendance stays
        reviewed."""
        self.env.company.attendance_validation = 'exception_validation'
        self.env.company.attendance_validation_tolerance = 15
        afternoon = self._create_kiosk_attendances(((13, 0), (17, 10)))
        self.assertRecordValues(afternoon, [{'is_late_check_in': True, 'is_undertime': True, 'state': 'draft'}])
        # as the time off approval does
        morning_off = self.env['resource.calendar.leaves'].with_context(skip_time_rules=True).create({
            'name': 'Morning off',
            'resource_id': self.employee.resource_id.id,
            'calendar_id': self.employee.resource_calendar_id.id,
            'date_from': datetime(2024, 1, 1, 8, 0),
            'date_to': datetime(2024, 1, 1, 12, 0),
        })
        self.assertRecordValues(afternoon, [{'is_late_check_in': False, 'is_undertime': False, 'state': 'validated'}])
        self.assertAlmostEqual(self._get_overtime_hours(), 1 / 6, msg="The review ran the time rules")
        # the time rules moved the extra 10 minutes to an output, now the last attendance of the day
        day = afternoon | afternoon.overtime_attendance_ids
        morning_off.date_from = datetime(2024, 1, 1, 10, 0)
        self.assertRecordValues(afternoon, [{'is_late_check_in': True, 'state': 'validated'}])
        self.assertTrue(day.filtered('is_undertime'))
        morning_off.unlink()
        self.assertRecordValues(afternoon, [{'is_late_check_in': True, 'state': 'validated'}])
        self.assertTrue(day.filtered('is_undertime'))

        # a public holiday in the morning, for the employees of the company
        self.env['resource.calendar.leaves'].create({
            'name': 'Half holiday',
            'company_id': self.employee.company_id.id,
            'calendar_id': self.employee.resource_calendar_id.id,
            'date_from': datetime(2024, 1, 1, 8, 0),
            'date_to': datetime(2024, 1, 1, 12, 0),
        })
        self.assertRecordValues(afternoon, [{'is_late_check_in': False, 'is_undertime': False}])

    @freeze_time('2024-01-03 06:00:00')
    def test_manager_edit_is_manual(self):
        """A manager's edit of the times is manual, like the employee's, but keeps the review state. The devices, the
        automatic check-out and the time rules write as superuser and keep their mode."""
        self.env.company.attendance_validation = 'exception_validation'
        officer = new_test_user(
            self.env, login='att_officer_edit', groups='base.group_user,hr_attendance.group_hr_attendance_officer',
        )
        self.employee.attendance_manager_id = officer
        morning, afternoon = self._create_kiosk_attendances(((8, 0), (12, 0)), ((13, 0), (17, 0)))
        afternoon.with_user(officer).write({'check_out': datetime(2024, 1, 1, 17, 5)})
        self.assertRecordValues(afternoon, [{'state': 'validated', 'in_mode': 'kiosk', 'out_mode': 'manual'}])
        morning.with_user(officer).write({'check_in': datetime(2024, 1, 1, 7, 55), 'in_mode': 'kiosk'})
        self.assertRecordValues(morning, [{'in_mode': 'kiosk', 'out_mode': 'kiosk'}])
        morning.sudo().write({'check_out': datetime(2024, 1, 1, 12, 5)})
        self.assertRecordValues(morning, [{'in_mode': 'kiosk', 'out_mode': 'kiosk'}])

    @freeze_time('2024-01-03 06:00:00')
    def test_issues_follow_the_other_attendances_of_the_day(self):
        """Refusing, resetting or deleting an attendance moves the issues of the other attendances of its day."""
        morning, afternoon = self._create_kiosk_attendances(((8, 30), (12, 0)), ((13, 0), (16, 30)))
        morning.action_refuse()
        self.assertRecordValues(morning | afternoon, [
            {'is_late_check_in': False, 'is_early_check_out': False},
            {'is_late_check_in': True, 'is_early_check_out': True},
        ])
        morning.action_reset_to_draft()
        self.assertRecordValues(morning | afternoon, [
            {'is_late_check_in': True, 'is_early_check_out': False},
            {'is_late_check_in': False, 'is_early_check_out': True},
        ])
        morning.unlink()
        self.assertTrue(afternoon.is_late_check_in)

    @freeze_time('2024-01-03 06:00:00')
    def test_lunch_check_out_reviewed_once_back(self):
        """Checking out for lunch is an early check-out until the employee checks in again. Then the
        morning attendance has no issue left, and is reviewed like the afternoon one.
        """
        self.env.company.attendance_validation = 'exception_validation'
        morning = self._create_kiosk_attendances(((8, 0), (12, 0)))
        self.assertRecordValues(morning, [{'is_early_check_out': True, 'state': 'draft'}])

        afternoon = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2024, 1, 1, 13, 0),
            'in_mode': 'kiosk',
        })
        afternoon.write({'check_out': datetime(2024, 1, 1, 17, 0), 'out_mode': 'kiosk'})
        self.assertRecordValues(morning | afternoon, [
            {'is_early_check_out': False, 'has_issue': False, 'state': 'validated'},
            {'is_early_check_out': False, 'has_issue': False, 'state': 'validated'},
        ])

    @freeze_time('2024-01-10 06:00:00')
    def test_expected_attendances_before_contract(self):
        """The days before a contract follow the employee's schedule, also the last one, alone or with earlier days."""
        self.employee.version_id.write({'date_version': date(2024, 1, 2), 'contract_date_start': date(2024, 1, 2)})
        friday, monday, tuesday = date(2023, 12, 29), date(2024, 1, 1), date(2024, 1, 2)  # contract from Tuesday
        for days in ([monday], [friday, monday], [friday, monday, tuesday]):
            with self.subTest(days=days):
                expected = self.employee._get_expected_attendances_by_day(days)
                self.assertEqual({day: len(shifts) for day, shifts in expected.items()}, dict.fromkeys(days, 2))

    def test_issues_of_night_shift(self):
        """A shift over midnight belongs to the day it starts, like its attendance."""
        self.employee.resource_calendar_id = self.env['resource.calendar'].create({
            'name': 'Nights',
            'attendance_ids': [
                (0, 0, {'dayofweek': str(wd), 'hour_from': 22, 'hour_to': 24}) for wd in range(5)
            ] + [
                (0, 0, {'dayofweek': str(wd), 'hour_from': 0, 'hour_to': 6}) for wd in range(1, 6)
            ],
        })
        night, long_night = self.env['hr.attendance'].create([{
            'employee_id': self.employee.id,
            'check_in': datetime(2024, 1, day, 22, 0),  # Monday and Tuesday nights
            'check_out': datetime(2024, 1, day + 1, check_out_hour, 0),
            'in_mode': 'kiosk',
            'out_mode': 'kiosk',
        } for day, check_out_hour in ((1, 6), (2, 9))])
        self.assertRecordValues(night | long_night, [
            {'is_late_check_in': False, 'is_early_check_out': False, 'is_overtime': False},
            {'is_late_check_in': False, 'is_early_check_out': False, 'is_overtime': True},
        ])

    @freeze_time('2024-01-03 06:00:00')
    def test_light_user_edit_sends_back_to_review(self):
        self.env.company.attendance_validation = 'exception_validation'
        morning, afternoon = self._create_kiosk_attendances(((8, 0), (12, 0)), ((13, 0), (17, 0)))
        self.assertEqual(afternoon.state, 'validated')

        afternoon.with_user(self.light_user).write({'check_out': datetime(2024, 1, 1, 16, 55)})
        self.assertRecordValues(morning | afternoon, [
            {'state': 'validated', 'in_mode': 'kiosk', 'out_mode': 'kiosk'},
            {'state': 'draft', 'in_mode': 'kiosk', 'out_mode': 'manual'},
        ])

        morning.with_user(self.light_user).write({'break_duration': 0.25})
        self.assertRecordValues(morning, [{'state': 'draft', 'in_mode': 'kiosk', 'out_mode': 'kiosk'}])

        morning.action_validate()
        morning.with_user(self.light_user).write({'check_in': datetime(2024, 1, 1, 8, 5)})
        self.assertRecordValues(morning, [{'state': 'draft', 'in_mode': 'manual', 'out_mode': 'kiosk'}])

        afternoon.action_validate()
        afternoon.with_user(self.light_user).write({'check_in': datetime(2024, 1, 1, 13, 5), 'state': 'draft'})
        self.assertRecordValues(afternoon, [{'state': 'draft', 'in_mode': 'manual', 'out_mode': 'manual'}])

    @freeze_time('2024-01-03 06:00:00')
    def test_light_user_edit_overtime_waits_for_review(self):
        self.env.company.attendance_validation = 'exception_validation'
        _morning, afternoon = self._create_kiosk_attendances(((8, 0), (12, 0)), ((13, 0), (17, 0)))
        self.assertEqual(afternoon.state, 'validated')
        afternoon.with_user(self.light_user).write({'check_out': datetime(2024, 1, 1, 20, 0)})
        self.assertRecordValues(afternoon, [{'state': 'draft', 'out_mode': 'manual'}])
        self.assertFalse(self._get_overtime_hours(), "The overtime waits for a review")
        afternoon.action_validate()
        self.assertAlmostEqual(self._get_overtime_hours(), 3)  # 4h + 7h - 8h

    @freeze_time('2024-01-03 06:00:00')
    def test_light_user_cannot_set_trusted_values(self):
        """Only the managers review attendances, and only the devices and the time rules (in sudo) set the check in/out
        modes and create time rule outputs."""
        self.env.company.attendance_validation = 'exception_validation'
        self._create_kiosk_attendances(((8, 0), (12, 0)))
        attendances = self.env['hr.attendance'].with_user(self.light_user)
        afternoon = attendances.create({
            'employee_id': self.employee.id,
            'check_in': datetime(2024, 1, 1, 13, 0),
            'check_out': datetime(2024, 1, 1, 17, 0),
        })
        self.assertRecordValues(afternoon, [{'state': 'draft', 'in_mode': 'manual', 'out_mode': 'manual'}])
        for trusted_vals in (
            {'state': 'validated'},
            {'in_mode': 'systray'},
            {'out_mode': 'kiosk'},
            {'time_rule_id': self.rule.id},
            {'source_attendance_id': afternoon.id},
        ):
            with self.subTest(vals=trusted_vals):
                with self.assertRaises(AccessError):
                    attendances.create({
                        'employee_id': self.employee.id,
                        'check_in': datetime(2024, 1, 2, 8, 0),
                        **trusted_vals,
                    })
                with self.assertRaises(AccessError):
                    # without the times, the review policy would review it
                    afternoon.with_user(self.light_user).write({
                        'work_entry_type_id': afternoon.work_entry_type_id.id,
                        **trusted_vals,
                    })

    @freeze_time('2024-01-03 06:00:00')
    def test_review_exceptions_after_time_rules(self):
        """The excess hours that the time rules move to an output on review still count in the
        day: the reviewed day keeps its overtime and does not become an early check-out."""
        self.env.company.attendance_validation = 'exception_validation'
        self.env.company.attendance_validation_tolerance = 15
        morning, afternoon = self._create_kiosk_attendances(((7, 30), (12, 0)), ((13, 0), (17, 0)))
        self.assertTrue(afternoon.is_overtime)
        (morning | afternoon).action_validate()
        self.assertAlmostEqual(self._get_overtime_hours(), 0.5)
        day = self.env['hr.attendance'].search([('employee_id', '=', self.employee.id), ('date', '=', date(2024, 1, 1))])
        self.assertEqual(len(day), 3)
        self.assertFalse(day.filtered('is_early_check_out'))
        self.assertFalse(day.filtered('is_late_check_in'))
        self.assertEqual(len(day.filtered('is_overtime')), 1)

    def test_auto_check_out_is_reviewed(self):
        """An automatic check-out goes to review as such, not as an early check-out."""
        self.env.company.write({
            'attendance_validation': 'exception_validation',
            'attendance_validation_tolerance': 15,
            'auto_check_out': True,
            'auto_check_out_tolerance': 1,
        })
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2024, 1, 1, 8, 0),  # Monday, 8-12 and 13-17 expected
            'in_mode': 'kiosk',
        })
        with freeze_time('2024-01-01 18:00:00'):
            self.env['hr.attendance']._cron_auto_check_out()
        self.assertRecordValues(attendance, [{
            'check_out': datetime(2024, 1, 1, 16, 0),
            'out_mode': 'auto_check_out',
            'is_early_check_out': False,
            'state': 'draft',
        }])

    def test_check_in_out_log_gives_the_device(self):
        """The chatter message of a check-in or check-out gives the browser and the IP address on a second line."""
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2024, 1, 1, 8, 0),
            'in_mode': 'systray',
            'in_browser': 'chrome',
            'in_ip_address': '192.0.2.1',
        })
        self.assertIn(
            '<br><span class="text-muted">Browser: chrome · IP address: 192.0.2.1</span>',
            attendance.message_ids[-1].body,
        )
        attendance.write({'check_out': datetime(2024, 1, 1, 17, 0), 'out_mode': 'systray', 'out_browser': 'firefox'})
        self.assertEqual(
            attendance._get_check_in_out_log('out'),
            'Check out (Systray)<br/><span class="text-muted">Browser: firefox</span>',
        )
        manual = self._create_kiosk_attendances(((18, 0), (19, 0)))
        self.assertNotIn('text-muted', manual.message_ids[-1].body, "Nothing to add without the browser nor the IP address")

    def test_auto_check_out_counts_worked_time_only(self):
        """The automatic check-out completes the hours of the day: a refused attendance of the day does not count."""
        self.env.company.write({
            'auto_check_out': True,
            'auto_check_out_tolerance': 1,
        })
        morning = self._create_kiosk_attendances(((8, 0), (12, 0)))
        morning.action_refuse()
        afternoon = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2024, 1, 1, 13, 0),
            'in_mode': 'kiosk',
        })
        with freeze_time('2024-01-01 23:00:00'):
            self.env['hr.attendance']._cron_auto_check_out()
        self.assertRecordValues(afternoon, [{'check_out': datetime(2024, 1, 1, 21, 0), 'out_mode': 'auto_check_out'}])

    @freeze_time('2023-12-31 10:00:00')  # Sunday
    def test_home_action_and_dashboard(self):
        self.env.company.attendance_validation = 'exception_validation'
        officer = new_test_user(self.env, login='att_officer', groups='base.group_user,hr_attendance.group_hr_attendance_officer')
        light = new_test_user(self.env, login='att_light', groups='base.group_user,hr_attendance.group_hr_attendance_own')
        my_action_id = self.env.ref('hr_attendance.hr_attendance_my_action').id
        self.assertEqual(self.env['hr.attendance'].with_user(officer)._get_home_action()['id'], self.env.ref('hr_attendance.hr_attendance_action').id)
        self.assertEqual(self.env['hr.attendance'].with_user(light)._get_home_action()['id'], my_action_id, "No employee: no check in panel")
        self.env['hr.employee'].create({'name': 'Light', 'user_id': light.id})
        self.assertEqual(self.env['hr.attendance'].with_user(light)._get_home_action()['tag'], 'hr_attendance_my_attendance')
        self.env.company.attendance_from_systray = False
        self.assertEqual(self.env['hr.attendance'].with_user(light)._get_home_action()['id'], my_action_id, "Check in from the kiosk only")
        self.env.company.attendance_from_systray = True
        my_action = self.env['ir.actions.act_window'].with_user(light)._for_xml_id('hr_attendance.hr_attendance_my_action')
        self.assertIn(f'Welcome {light.name}! Log your attendances here.', my_action['help'], "The users are welcomed by name")

        self.employee.attendance_manager_id = officer
        self.env['hr.attendance'].create([{
            'employee_id': self.employee.id,
            'check_in': datetime(2023, 12, 29, 8, 30),  # Friday, late
            'check_out': datetime(2023, 12, 29, 17, 0),
            'in_mode': 'kiosk',
            'out_mode': 'kiosk',
        }, {
            'employee_id': self.employee.id,
            'check_in': datetime(2023, 12, 28, 8, 0),  # Thursday, checked out by the cron
            'check_out': datetime(2023, 12, 28, 12, 0),
            'in_mode': 'kiosk',
            'out_mode': 'auto_check_out',
        }, {
            'employee_id': self.employee.id,
            'check_in': datetime(2023, 12, 30, 9, 0),  # Saturday, never checked out
            'in_mode': 'kiosk',
        }])
        counts = self.env['hr.attendance'].with_user(officer).get_attendance_dashboard_data()
        self.assertEqual(counts['to_review'], 2)
        self.assertEqual(counts['late_check_in'], 1)
        self.assertEqual(counts['no_check_out'], 1)
        self.assertEqual(counts['at_work'], 1)
        counts = self.env['hr.attendance'].with_user(officer).get_attendance_dashboard_data([('check_in', '>=', datetime(2023, 12, 30))])
        self.assertEqual(counts, {
            'to_review': 0, 'late_check_in': 0, 'early_check_out': 0, 'no_check_out': 0, 'overtime': 0, 'undertime': 0,
            'at_work': 1,
        },
            "The counters only count the attendances of the action")

        # To Review opens the dashboard action, filtered, under its own URL
        to_review = self.env['hr.attendance'].with_user(officer)._get_to_review_action()
        self.assertEqual(to_review['id'], self.env.ref('hr_attendance.hr_attendance_action').id)
        self.assertEqual(to_review['name'], 'To Review')
        self.assertEqual(to_review['display_name'], 'To Review')
        self.assertEqual(to_review['context'], {'search_default_state_draft': 1})
        self.assertEqual(to_review['views'][0][1], 'list')
        self.assertNotIn('path', to_review)

    @freeze_time('2024-01-03 06:00:00')
    def test_overtime_rule_timezones(self):
        """The schedule of the local day is compared with the attendances of that day."""
        for tz in ('Asia/Tokyo', 'Pacific/Honolulu', 'Europe/Brussels'):
            employee = self.env['hr.employee'].create({
                'name': f'Employee {tz}',
                'tz': tz,
                'date_version': '2020-01-01',
                'contract_date_start': '2020-01-01',
                'wage': 3000,
            })

            def to_utc(hour, tz=tz):
                local = datetime(2024, 1, 1, hour, tzinfo=ZoneInfo(tz))  # Monday
                return local.astimezone(UTC).replace(tzinfo=None)

            self.env['hr.attendance'].create([{
                'employee_id': employee.id,
                'check_in': to_utc(start),
                'check_out': to_utc(stop),
            } for start, stop in ((8, 12), (13, 17))])
            outputs = self.env['hr.attendance'].search([
                ('employee_id', '=', employee.id),
                ('time_rule_id', '=', self.rule.id),
            ])
            self.assertFalse(outputs, tz)

            self.env['hr.attendance'].create({
                'employee_id': employee.id,
                'check_in': to_utc(17),
                'check_out': to_utc(18),
            })
            outputs = self.env['hr.attendance'].search([
                ('employee_id', '=', employee.id),
                ('time_rule_id', '=', self.rule.id),
            ])
            self.assertAlmostEqual(sum(outputs.mapped('worked_hours')), 1.0, places=2, msg=tz)
