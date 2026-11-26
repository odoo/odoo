from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from odoo import Command, fields
from odoo.addons.hr_attendance.controllers.main import HrAttendance
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import Form, new_test_user
from odoo.tests.common import HttpCase, tagged, TransactionCase, freeze_time


USER_TZ = 'Europe/Brussels'


def utc(day, hour=0, minute=0, tz=USER_TZ):
    local = datetime.combine(day, time.min, ZoneInfo(tz)) + timedelta(hours=hour, minutes=minute)
    return local.astimezone(UTC).replace(tzinfo=None)


@tagged('attendance_process')
class TestHrAttendance(HttpCase, TransactionCase):
    """Test for presence validity"""

    @classmethod
    def setUpClass(cls):
        super(TestHrAttendance, cls).setUpClass()
        cls.env.company.country_id = cls.env.ref('base.us')
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
        # disable any time rules to run this test class in isolation
        cls.env['hr.time.rule'].search([]).write({'active': False})

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

    def test_employee_without_user_presence_state(self):
        # Employee without linked user should update presence state on check in / check out
        self.assertFalse(self.employee_kiosk.user_id)
        self.assertEqual(self.employee_kiosk.attendance_state, 'checked_out')
        self.assertNotEqual(self.employee_kiosk.hr_presence_state, 'present')
        self.employee_kiosk._attendance_action_change()
        self.assertEqual(self.employee_kiosk.attendance_state, 'checked_in')
        self.assertEqual(self.employee_kiosk.hr_presence_state, 'present')
        self.employee_kiosk._attendance_action_change()
        self.assertEqual(self.employee_kiosk.attendance_state, 'checked_out')
        self.assertNotEqual(self.employee_kiosk.hr_presence_state, 'present')

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

    def test_last_month_attendances_new_defaults_to_employee(self):
        """New from the Monthly Hours smart button defaults to that employee."""
        action = self.employee.action_open_last_month_attendances()
        attendance_form = Form(self.env['hr.attendance'].with_context(action['context']))
        self.assertEqual(attendance_form.employee_id, self.employee)

    def test_last_month_attendances_rights(self):
        """The Monthly Hours of an employee can only be changed with the rights to change them."""
        officer = new_test_user(self.env, login='att_officer', groups='base.group_user,hr_attendance.group_hr_attendance_officer')
        own_editor = new_test_user(self.env, login='att_own', groups='base.group_user,hr_attendance.group_hr_attendance_own')
        officer_employee = self.env['hr.employee'].create({'name': 'Officer Employee', 'user_id': officer.id})
        own_employee = self.env['hr.employee'].create({'name': 'Own Employee', 'user_id': own_editor.id})
        self.employee.attendance_manager_id = officer

        def rights(employee, user):
            context = employee.with_user(user).action_open_last_month_attendances()['context']
            return {key: context[key] for key in ('create', 'edit', 'delete')}

        # The attendance manager of the employee manages his attendances
        self.assertEqual(rights(self.employee, officer), {'create': True, 'edit': True, 'delete': True})
        # Without "Self Attendance Edit", an attendance officer only reads his own attendances
        self.assertEqual(rights(officer_employee, officer), {'create': False, 'edit': False, 'delete': False})
        self.assertEqual(rights(self.other_employee, officer), {'create': False, 'edit': False, 'delete': False})
        # "Self Attendance Edit" creates and edits the own attendances, but doesn't delete them
        self.assertEqual(rights(own_employee, own_editor), {'create': True, 'edit': True, 'delete': False})

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

    def test_archive_attendance_approver(self):
        """The attendance approver is emptied when their employee is archived, also by an HR officer without
        attendance rights, like the other approvers."""
        approver_user = new_test_user(self.env, login='archived_approver', groups='base.group_user,hr_attendance.group_hr_attendance_officer')
        approver = self.env['hr.employee'].create({'name': 'Approver', 'user_id': approver_user.id})
        self.test_employee.attendance_manager_id = approver_user

        approver.with_user(self.hr_user).action_archive()
        self.assertFalse(self.test_employee.attendance_manager_id)

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
        employee = self.env['hr.employee'].create({
            'name': 'Cross Midnight',
            'date_version': date(2023, 1, 1),
            'tz': 'UTC',
        })
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
        employee = self.env['hr.employee'].create({
            'name': 'Opt-in Employee',
            'date_version': date(2023, 1, 1),
            'tz': 'UTC',
        })
        now = fields.Datetime.now()
        self.env['hr.attendance'].create({
            'employee_id': employee.id,
            'check_in': datetime(2024, 1, 1, 22),
            'check_out': datetime(2024, 1, 2, 2),
            'break_duration': 1,
        })
        future_attendance = self.env['hr.attendance'].create({
            'employee_id': employee.id,
            'check_in': now + timedelta(hours=2),
            'check_out': now + timedelta(hours=3),
        })
        tomorrow_attendance = self.env['hr.attendance'].create({
            'employee_id': employee.id,
            'check_in': now + timedelta(days=1),
            'check_out': now + timedelta(days=1, hours=1),
        })
        future_open_attendance = self.env['hr.attendance'].create({
            'employee_id': employee.id,
            'check_in': now + timedelta(hours=4),
        })

        public_payload = HrAttendance._get_user_attendance_data(employee)
        self.assertNotIn('last_attendance', public_payload)
        self.assertNotIn('in_location', public_payload['today_attendance_ids'][0])
        self.assertNotIn('can_edit', public_payload['today_attendance_ids'][0])
        self.assertEqual(public_payload['hours_today'], 1.5)
        self.assertEqual(public_payload['hours_previously_today'], 0)

        user_payload = HrAttendance._get_user_attendance_data(
            employee,
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
            "name": "Test",
            "country_id": self.env.ref("base.us").id,
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

    def test_check_in_out_tolerance(self):
        """ Within the tolerance, a check-in or a check-out is recorded at the planned time, the time of the
        check-in stays the creation date of the attendance. Default tolerance: 15 minutes for an early arrival or
        an early departure, none when late. """
        self.company.attendance_tolerance = True
        employee = self.employee

        def last_attendance():
            return self.env['hr.attendance'].search([('employee_id', '=', employee.id)], order='check_in desc', limit=1)
        monday = datetime(2026, 11, 16, tzinfo=UTC)
        intervals = employee._get_attendance_tolerance_intervals(monday, monday + timedelta(days=1))
        self.assertTrue(intervals)
        start = intervals[0][0].astimezone(UTC).replace(tzinfo=None)
        stop = intervals[-1][1].astimezone(UTC).replace(tzinfo=None)

        # Early arrival and early departure within the tolerance
        with freeze_time(start - timedelta(minutes=10)):
            employee._attendance_action_change()
        attendance = last_attendance()
        # The attendance is open from the time of the check-in, then recorded from the planned time once closed
        self.assertEqual(attendance.check_in, start - timedelta(minutes=10))
        self.assertEqual(employee.attendance_state, 'checked_in')
        with freeze_time(stop - timedelta(minutes=5)):
            employee._attendance_action_change()
        self.assertEqual((attendance.check_in, attendance.check_out), (start, stop))

        # Late arrival and late departure are not tolerated by default, nor an early arrival beyond the tolerance
        tuesday_start, tuesday_stop = start + timedelta(days=1), stop + timedelta(days=1)
        with freeze_time(tuesday_start + timedelta(minutes=2)):
            employee._attendance_action_change()
        attendance = last_attendance()
        self.assertEqual(attendance.check_in, tuesday_start + timedelta(minutes=2))
        with freeze_time(tuesday_stop + timedelta(minutes=3)):
            employee._attendance_action_change()
        self.assertEqual(attendance.check_out, tuesday_stop + timedelta(minutes=3))
        wednesday_start = start + timedelta(days=2)
        with freeze_time(wednesday_start - timedelta(minutes=20)):
            employee._attendance_action_change()
        self.assertEqual(last_attendance().check_in, wednesday_start - timedelta(minutes=20))

        # A late arrival is tolerated once configured
        self.company.attendance_tolerance_late_check_in = 5
        with freeze_time(wednesday_start + timedelta(hours=2)):
            employee._attendance_action_change()
        thursday_start = start + timedelta(days=3)
        with freeze_time(thursday_start + timedelta(minutes=4)):
            employee._attendance_action_change()
        self.assertEqual(last_attendance().check_in, thursday_start)

        # Checked out before the planned time the check-in would be recorded at: the times are kept
        friday_start = start + timedelta(days=4)
        with freeze_time(thursday_start + timedelta(hours=2)):
            employee._attendance_action_change()
        with freeze_time(friday_start - timedelta(minutes=10)):
            employee._attendance_action_change()
        attendance = last_attendance()
        with freeze_time(friday_start - timedelta(minutes=5)):
            employee._attendance_action_change()
        self.assertEqual(
            (attendance.check_in, attendance.check_out),
            (friday_start - timedelta(minutes=10), friday_start - timedelta(minutes=5)))

        # Without the tolerance, the time of the check-in or the check-out is recorded
        self.company.attendance_tolerance = False
        self.assertEqual(employee._get_attendance_tolerance_time(friday_start - timedelta(minutes=5), 'in'), friday_start - timedelta(minutes=5))

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
        cls.env.company.country_id = cls.env.ref('base.us')
        cls.env.company.tz = 'UTC'
        cls.env.company.resource_calendar_id = cls.env['resource.calendar'].create({
            'name': '40h/week',
            'attendance_ids': [
                (0, 0, {'dayofweek': wd, 'hour_from': h, 'hour_to': h + 4})
                for wd in ['0', '1', '2', '3', '4']
                for h in [8, 13]
            ],
        })

        cls.env['hr.time.rule'].search([]).write({'active': False})

        cls.absent_employee = cls.env['hr.employee'].create({
            'name': 'Absent Employee',
            'tz': 'UTC',
            'date_version': '2020-01-01',
            'contract_date_start': '2020-01-01',
            'wage': 3000,
            'work_entry_source': 'attendance',
        })

    @freeze_time('2024-01-02 06:00:00')  # yesterday = 2024-01-01 (Monday)
    def test_absence_creates_technical_attendance(self):
        """Absent employee: a validated technical attendance without worked hours at the start of
        the first shift of the day, whose overtime is the missed day. The time rules are tested in
        hr_holidays_attendance."""
        self.env['hr.attendance']._cron_absence_detection()

        atts = self.env['hr.attendance'].search([('employee_id', '=', self.absent_employee.id)])
        self.assertRecordValues(atts, [{
            'check_in': datetime(2024, 1, 1, 8, 0),
            'check_out': datetime(2024, 1, 1, 8, 0),
            'in_mode': 'technical',
            'out_mode': 'technical',
            'state': 'validated',
            'worked_hours': 0.0,
            'overtime_hours': -8.0,
        }])

    @freeze_time('2024-01-02 06:00:00')  # yesterday = 2024-01-01 (Monday)
    def test_undertime_with_refused_attendance(self):
        """A refused attendance did not happen: it expects nothing and makes no overtime, the other
        attendances of the day share the expected hours. Taking back the refusal shares them again."""
        refused, worked = self.env['hr.attendance'].create([{
            'employee_id': self.absent_employee.id,
            'check_in': datetime(2024, 1, 1, 8, 0),
            'check_out': datetime(2024, 1, 1, 12, 0),
        }, {
            'employee_id': self.absent_employee.id,
            'check_in': datetime(2024, 1, 1, 13, 0),
            'check_out': datetime(2024, 1, 1, 14, 0),
        }])
        refused.action_refuse()
        self.assertEqual(refused.state, 'refused')
        self.assertRecordValues(refused | worked, [
            {'expected_hours': 0.0, 'overtime_hours': 0.0},
            {'expected_hours': 8.0, 'overtime_hours': -7.0},
        ])
        refused.action_validate()
        self.assertEqual(refused.state, 'validated')
        self.assertRecordValues(refused | worked, [
            {'expected_hours': 4.0, 'overtime_hours': 0.0},
            {'expected_hours': 4.0, 'overtime_hours': -3.0},
        ])

    @freeze_time('2024-01-02 06:00:00')  # yesterday = 2024-01-01 (Monday)
    def test_absence_with_refused_attendance(self):
        """A day with only refused attendances is an absence: the refused attendance did not happen."""
        refused = self.env['hr.attendance'].create({
            'employee_id': self.absent_employee.id,
            'check_in': datetime(2024, 1, 1, 9, 0),
            'check_out': datetime(2024, 1, 1, 12, 0),
        })
        refused.action_refuse()

        self.env['hr.attendance']._cron_absence_detection()

        technical = self.env['hr.attendance'].search([
            ('employee_id', '=', self.absent_employee.id), ('in_mode', '=', 'technical'),
        ])
        self.assertRecordValues(technical, [{
            'check_in': datetime(2024, 1, 1, 8, 0),
            'check_out': datetime(2024, 1, 1, 8, 0),
            'overtime_hours': -8.0,
        }])

    @freeze_time('2024-01-02 06:00:00')  # yesterday = 2024-01-01 (Monday)
    def test_absence_over_refused_attendance(self):
        """The absence can start during a refused attendance: it did not happen, so it does not
        overlap. Taking back the refusal then overlaps the absence."""
        refused = self.env['hr.attendance'].create({
            'employee_id': self.absent_employee.id,
            'check_in': datetime(2024, 1, 1, 7, 55),
            'check_out': datetime(2024, 1, 1, 12, 0),
        })
        refused.action_refuse()

        self.env['hr.attendance']._cron_absence_detection()

        technical = self.env['hr.attendance'].search([
            ('employee_id', '=', self.absent_employee.id), ('in_mode', '=', 'technical'),
        ])
        self.assertRecordValues(technical, [{
            'check_in': datetime(2024, 1, 1, 8, 0),
            'check_out': datetime(2024, 1, 1, 8, 0),
            'overtime_hours': -8.0,
        }])
        with self.assertRaises(ValidationError):
            refused.action_reset_to_draft()

    @freeze_time('2024-01-02 06:00:00')  # yesterday = 2024-01-01 (Monday)
    def test_absence_timezones(self):
        """The absence is detected on the local day of the employee, whatever their timezone."""
        self.absent_employee.contract_date_end = '2023-12-31'
        for tz in ('Europe/Brussels', 'Asia/Tokyo', 'Pacific/Honolulu', 'UTC'):
            employee = self.env['hr.employee'].create({
                'name': f'Absent Employee {tz}',
                'tz': tz,
                'date_version': '2020-01-01',
                'contract_date_start': '2020-01-01',
                'wage': 3000,
                'work_entry_source': 'attendance',
            })
            self.env['hr.attendance']._cron_absence_detection()
            atts = self.env['hr.attendance'].search([('employee_id', '=', employee.id)])
            self.assertRecordValues(atts, [{'date': date(2024, 1, 1), 'overtime_hours': -8.0}])
            employee.contract_date_end = '2023-12-31'

    @freeze_time('2026-11-23 06:00:00')  # yesterday = 2026-11-22 (Sunday)
    def test_absence_flexible_with_hours_target(self):
        """A flexible schedule with hours targets expects its average day on the first days of the
        week, until the hours per week are reached: Monday to Friday for 38h of 7.6h, whatever the
        days the cron checks."""
        self.absent_employee.resource_calendar_id = self.env['resource.calendar'].create({
            'name': 'Flexible 38h', 'calendar_type': 'undefined', 'hours_per_day': 7.6, 'hours_per_week': 38,
        })
        # last call on Sunday 15: the days from Sunday 15 to Sunday 22 are checked
        self.env['hr.attendance'].with_context(lastcall=datetime(2026, 11, 15, 6))._cron_absence_detection()

        atts = self.env['hr.attendance'].search([('employee_id', '=', self.absent_employee.id)], order='check_in')
        self.assertRecordValues(atts, [
            {'date': date(2026, 11, day), 'overtime_hours': -7.6} for day in range(16, 21)
        ])

    @freeze_time('2024-01-02 06:00:00')  # yesterday = 2024-01-01 (Monday)
    def test_absence_after_contract_end(self):
        """Employee whose contract ended before yesterday is not targeted by the cron."""
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
class TestAttendanceValidation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.country_id = cls.env.ref('base.us')
        cls.env.company.resource_calendar_id = cls.env['resource.calendar'].create({
            'name': '40h/week',
            'attendance_ids': [
                (0, 0, {'dayofweek': wd, 'hour_from': h, 'hour_to': h + 4})
                for wd in ['0', '1', '2', '3', '4']
                for h in [8, 13]
            ],
        })
        cls.env['hr.time.rule'].search([]).write({'active': False})
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
        """The overtime of the reviewed attendances of the employee."""
        return self.employee.total_overtime

    def _create_kiosk_attendances(self, *spans):
        return self.env['hr.attendance'].create([{
            'employee_id': self.employee.id,
            'check_in': datetime(2024, 1, 1, *start),  # Monday, 8-12 and 13-17 expected
            'check_out': datetime(2024, 1, 1, *stop),
            'in_mode': 'kiosk',
            'out_mode': 'kiosk',
        } for start, stop in spans])

    @freeze_time('2024-01-03 06:00:00')
    def test_manager_encoded_attendance_is_reviewed(self):
        self.env.company.attendance_validation = 'manual_validation'
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2024, 1, 1, 8, 0),  # Monday: 8 hours expected, so 1 hour of overtime
            'check_out': datetime(2024, 1, 1, 17, 0),
        })
        self.assertEqual(attendance.state, 'validated')
        self.assertAlmostEqual(self._get_overtime_hours(), 1.0)

    @freeze_time('2024-01-03 06:00:00')
    def test_exceptions_only_on_check_out(self):
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
        self.assertRecordValues(attendance, [{'state': 'draft', 'overtime_hours': 1.0}])
        self.assertFalse(self._get_overtime_hours())

        # the lunch break recorded at the kiosk after the check-out
        attendance.break_duration = 1.0
        self.assertRecordValues(attendance, [{'state': 'validated', 'overtime_hours': 0.0}])
        self.assertFalse(self._get_overtime_hours())

    @freeze_time('2024-01-03 06:00:00')
    def test_schedule_change_recomputes_issues(self):
        """A new schedule changes the issues of the attendances it covers, and the days left without issue are
        reviewed."""
        self.env.company.attendance_validation = 'exception_validation'
        self.env.company.attendance_validation_tolerance = 15
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2024, 1, 1, 8, 0),  # Monday: 8 hours expected, 9 worked
            'check_out': datetime(2024, 1, 1, 17, 0),
            'in_mode': 'kiosk',
            'out_mode': 'kiosk',
        })
        self.assertRecordValues(attendance, [{'overtime_hours': 1.0, 'state': 'draft'}])

        nine_hours = self.env['resource.calendar'].create({
            'name': '45h/week',
            'attendance_ids': [
                (0, 0, {'dayofweek': wd, 'hour_from': h_from, 'hour_to': h_to})
                for wd in ['0', '1', '2', '3', '4']
                for h_from, h_to in [(8, 12), (12, 17)]
            ],
        })
        self.employee.version_id.resource_calendar_id = nine_hours
        self.assertRecordValues(attendance, [{'overtime_hours': 0.0, 'state': 'validated'}])

        # a version of the old schedule from that Monday brings the overtime back on the next days
        attendance_tuesday = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2024, 1, 2, 8, 0),
            'check_out': datetime(2024, 1, 2, 17, 0),
            'in_mode': 'kiosk',
            'out_mode': 'kiosk',
        })
        self.assertRecordValues(attendance_tuesday, [{'overtime_hours': 0.0, 'state': 'validated'}])
        self.employee.create_version({
            'date_version': date(2024, 1, 2),
            'resource_calendar_id': self.env.company.resource_calendar_id.id,
        })
        self.assertRecordValues(attendance_tuesday, [{'overtime_hours': 1.0}])

    @freeze_time('2024-01-06 06:00:00')
    def test_issue_flags_hours_only_schedule(self):
        """A schedule of 8 hours per day, without times, has no late check-in nor early check-out, only overtime and
        undertime."""
        self.env.company.attendance_validation = 'exception_validation'
        self.env.company.attendance_validation_tolerance = 15
        self.employee.resource_calendar_id = self.env['resource.calendar'].create({
            'name': '8h/day',
            'attendance_ids': [
                (0, 0, {'dayofweek': str(day), 'duration_hours': 8, 'hour_from': 0, 'hour_to': 0}) for day in range(5)
            ],
        })
        # Monday to Wednesday. The schedule places its 8 hours from 8:00 to 16:00, so 10:00 would be late with times.
        attendances = self.env['hr.attendance'].create([{
            'employee_id': self.employee.id,
            'check_in': datetime(2024, 1, day, check_in),
            'check_out': datetime(2024, 1, day, check_out),
            'in_mode': 'kiosk',
            'out_mode': 'kiosk',
        } for day, check_in, check_out in [(1, 10, 18), (2, 10, 16), (3, 6, 17)]])
        self.assertRecordValues(attendances, [
            {'is_late_check_in': False, 'is_early_check_out': False, 'overtime_hours': 0.0},
            {'is_late_check_in': False, 'is_early_check_out': False, 'overtime_hours': -2.0},
            {'is_late_check_in': False, 'is_early_check_out': False, 'overtime_hours': 3.0},
        ])

    @freeze_time('2024-01-03 06:00:00')
    def test_issue_flags(self):
        self.env.company.attendance_validation = 'exception_validation'
        self.env.company.attendance_validation_tolerance = 15
        morning, afternoon = self._create_kiosk_attendances(((8, 30), (12, 0)), ((13, 0), (16, 30)))
        self.assertRecordValues(morning | afternoon, [
            {'is_late_check_in': True, 'is_early_check_out': False, 'overtime_hours': 0.0, 'has_issue': True, 'state': 'draft'},
            {'is_late_check_in': False, 'is_early_check_out': True, 'overtime_hours': -1.0, 'has_issue': True, 'state': 'draft'},
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
        kiosk = {'employee_id': self.employee.id, 'in_mode': 'kiosk', 'out_mode': 'kiosk'}
        morning, afternoon = self.env['hr.attendance'].create([{
            **kiosk, 'check_in': datetime(2024, 1, 1, 8, 0), 'check_out': datetime(2024, 1, 1, 12, 0),
        }, {
            # Monday, 8-12 and 13-17 expected: on time, but a long break
            **kiosk, 'check_in': datetime(2024, 1, 1, 13, 0), 'check_out': datetime(2024, 1, 1, 17, 0), 'break_duration': 1,
        }])
        self.assertRecordValues(morning | afternoon, [
            {'overtime_hours': 0.0, 'is_early_check_out': False, 'has_issue': False, 'state': 'validated'},
            {'overtime_hours': -1.0, 'is_early_check_out': False, 'has_issue': True, 'state': 'draft'},
        ])
        self.assertEqual(
            self.env['hr.attendance'].search([('overtime_hours', '<', 0), ('employee_id', '=', self.employee.id)]),
            afternoon,
        )
        # within the tolerance
        afternoon.break_duration = 0.1
        self.assertRecordValues(afternoon, [{'overtime_hours': 0.0, 'state': 'validated'}])

        open_day, auto_checked_out, day_off = self.env['hr.attendance'].create([{
            # Tuesday, still at work
            'employee_id': self.employee.id, 'check_in': datetime(2024, 1, 2, 8, 0), 'in_mode': 'kiosk',
        }, {
            # Wednesday, checked out by the cron: it goes to review
            **kiosk, 'check_in': datetime(2024, 1, 3, 8, 0), 'check_out': datetime(2024, 1, 3, 10, 0),
            'out_mode': 'auto_check_out',
        }, {
            # Saturday
            **kiosk, 'check_in': datetime(2024, 1, 6, 1, 0), 'check_out': datetime(2024, 1, 6, 2, 0),
        }])
        self.assertFalse(open_day.overtime_hours, "No overtime until the check-out")
        self.assertRecordValues(auto_checked_out, [{'overtime_hours': -6.0, 'state': 'draft'}])
        self.assertRecordValues(day_off, [{'overtime_hours': 1.0}])

    @freeze_time('2024-01-03 06:00:00')
    def test_issues_follow_public_holidays(self):
        """A public holiday in the morning, added after the afternoon was worked: the afternoon is neither late nor
        short any more, and is reviewed. When the holiday moves or is deleted, the issues come back, but the
        attendance stays reviewed. The time off are tested in hr_holidays_attendance."""
        self.env.company.attendance_validation = 'exception_validation'
        self.env.company.attendance_validation_tolerance = 15
        afternoon = self._create_kiosk_attendances(((13, 0), (17, 10)))
        self.assertRecordValues(afternoon, [{'is_late_check_in': True, 'state': 'draft'}])
        self.assertLess(afternoon.overtime_hours, 0)
        holiday = self.env['resource.calendar.leaves'].create({
            'name': 'Half holiday',
            'company_id': self.employee.company_id.id,
            'calendar_id': self.employee.resource_calendar_id.id,
            'date_from': datetime(2024, 1, 1, 8, 0),
            'date_to': datetime(2024, 1, 1, 12, 0),
        })
        self.assertRecordValues(afternoon, [{'is_late_check_in': False, 'overtime_hours': 0.0, 'state': 'validated'}])
        self.assertFalse(self._get_overtime_hours(), "The extra 10 minutes are within the tolerance")
        holiday.date_from = datetime(2024, 1, 1, 10, 0)
        self.assertRecordValues(afternoon, [{'is_late_check_in': True, 'state': 'validated'}])
        self.assertLess(afternoon.overtime_hours, 0)
        holiday.unlink()
        self.assertRecordValues(afternoon, [{'is_late_check_in': True, 'state': 'validated'}])
        self.assertLess(afternoon.overtime_hours, 0)

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
    def test_officer_reviews_closed_managed_attendances(self):
        """A check-in a manager encodes by hand waits for its check-out to be reviewed. Approving a selection skips the
        attendances the user may not review: the open ones and the user's own."""
        self.env.company.attendance_validation = 'exception_validation'
        officer = new_test_user(
            self.env, login='att_officer_review', groups='base.group_user,hr_attendance.group_hr_attendance_officer',
        )
        self.employee.attendance_manager_id = officer
        officer_employee = self.env['hr.employee'].create({'name': 'Officer', 'user_id': officer.id, 'tz': 'UTC'})
        forgotten_check_in = self.env['hr.attendance'].with_user(officer).create({
            'employee_id': self.employee.id,
            'check_in': datetime(2024, 1, 2, 9, 0),
        })
        self.assertEqual(forgotten_check_in.state, 'draft')
        forgotten_check_in.sudo().write({'check_out': datetime(2024, 1, 2, 22, 0), 'out_mode': 'kiosk'})
        self.assertEqual(forgotten_check_in.state, 'draft', "The day is reviewed once it is over")
        own = self.env['hr.attendance'].create({
            'employee_id': officer_employee.id,
            'check_in': datetime(2024, 1, 2, 9, 0),
            'check_out': datetime(2024, 1, 2, 17, 0),
            'state': 'draft',
        })
        at_work = self.env['hr.attendance'].create({'employee_id': self.employee.id, 'check_in': datetime(2024, 1, 3, 5, 0)})
        (forgotten_check_in | own | at_work).with_user(officer).action_validate()
        self.assertRecordValues(forgotten_check_in | own | at_work, [
            {'state': 'validated'},
            {'state': 'draft'},
            {'state': 'draft'},
        ])

    @freeze_time('2024-01-03 06:00:00')
    def test_officer_gives_kiosk_attendances_to_self(self):
        """Attendances an officer gives to themselves are their own edit: they go back to To Review, and their times
        become encoded by hand, so the review by exception does not review them once the day has no issue left."""
        self.env.company.attendance_validation = 'exception_validation'
        officer = new_test_user(
            self.env, login='att_officer_move',
            groups='base.group_user,hr_attendance.group_hr_attendance_own,hr_attendance.group_hr_attendance_officer',
        )
        self.employee.attendance_manager_id = officer
        officer_employee = self.env['hr.employee'].create({'name': 'Officer', 'user_id': officer.id, 'tz': 'UTC'})
        morning, afternoon = self._create_kiosk_attendances(((8, 0), (12, 0)), ((13, 0), (17, 0)))
        self.assertRecordValues(morning | afternoon, [{'state': 'validated'}, {'state': 'validated'}])
        morning.with_user(officer).write({'employee_id': officer_employee.id})
        afternoon.with_user(officer).write({'employee_id': officer_employee.id})
        self.assertRecordValues(morning | afternoon, [
            {'employee_id': officer_employee.id, 'state': 'draft', 'in_mode': 'manual', 'out_mode': 'manual'},
            {'employee_id': officer_employee.id, 'state': 'draft', 'in_mode': 'manual', 'out_mode': 'manual'},
        ])

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
        """Attendances can be logged before the contract starts, e.g. when the contract dates are filled in later than
        the first day of work. Those days get the shifts of the employee's schedule too, also when the other days
        asked for are in the contract."""
        self.employee.version_id.write({'date_version': date(2024, 1, 2), 'contract_date_start': date(2024, 1, 2)})
        friday, monday, tuesday = date(2023, 12, 29), date(2024, 1, 1), date(2024, 1, 2)  # contract from Tuesday
        for days in ([monday], [friday, monday], [friday, monday, tuesday]):
            with self.subTest(days=days):
                expected = self.employee._get_expected_attendances_by_day(days)
                self.assertEqual({day: len(shifts) for day, shifts in expected.items()}, dict.fromkeys(days, 2))

    def test_expected_hours_flexible_with_hours_target(self):
        """A flexible schedule with hours targets expects its average day from Monday to Friday for
        38h of 7.6h, whatever the attendances computed together."""
        self.employee.resource_calendar_id = self.env['resource.calendar'].create({
            'name': 'Flexible 38h', 'calendar_type': 'undefined', 'hours_per_day': 7.6, 'hours_per_week': 38,
        })
        # Wednesday 18, Saturday 21, then Monday 23 to Wednesday 25
        attendances = self.env['hr.attendance'].create([{
            'employee_id': self.employee.id,
            'check_in': datetime(2026, 11, day, 8, 0),
            'check_out': datetime(2026, 11, day, 12, 0),
        } for day in (18, 21, 23, 24, 25)])
        self.assertRecordValues(attendances, [
            {'expected_hours': 7.6}, {'expected_hours': 0.0},
            {'expected_hours': 7.6}, {'expected_hours': 7.6}, {'expected_hours': 7.6},
        ])

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
            {'is_late_check_in': False, 'is_early_check_out': False},
            {'is_late_check_in': False, 'is_early_check_out': False},
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
        """Only the managers review attendances, and only the devices (in sudo) set the check in/out modes."""
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
        ):
            with self.subTest(vals=trusted_vals):
                with self.assertRaises(AccessError):
                    attendances.create({
                        'employee_id': self.employee.id,
                        'check_in': datetime(2024, 1, 2, 8, 0),
                        **trusted_vals,
                    })
                with self.assertRaises(AccessError):
                    afternoon.with_user(self.light_user).write(trusted_vals)

    @freeze_time('2024-01-03 06:00:00')
    def test_review_exceptions_after_review(self):
        """The reviewed day keeps its overtime and does not become an early check-out."""
        self.env.company.attendance_validation = 'exception_validation'
        self.env.company.attendance_validation_tolerance = 15
        morning, afternoon = self._create_kiosk_attendances(((7, 30), (12, 0)), ((13, 0), (17, 0)))
        self.assertEqual(afternoon.overtime_hours, 0.5)
        (morning | afternoon).action_validate()
        self.assertAlmostEqual(self._get_overtime_hours(), 0.5)
        day = self.env['hr.attendance'].search([('employee_id', '=', self.employee.id), ('date', '=', date(2024, 1, 1))])
        self.assertEqual(day, morning | afternoon)
        self.assertFalse(day.filtered('is_early_check_out'))
        self.assertFalse(day.filtered('is_late_check_in'))
        self.assertEqual(day.filtered(lambda attendance: attendance.overtime_hours > 0), afternoon)

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

    @freeze_time("2026-02-27 13:00:00")
    def test_auto_check_out_specific_time_is_reviewed(self):
        """The overtime of an automatic check-out at a fixed hour goes to review: the employee did not leave at that
        time."""
        self.env.company.write({
            'attendance_validation': 'exception_validation',
            'auto_check_out': True,
            'auto_check_out_mode': 'specific_time',
            'auto_check_out_specific_time': 20.0,
        })
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2024, 1, 1, 8, 0),  # Monday, 8 hours expected
            'in_mode': 'kiosk',
        })
        with freeze_time('2024-01-01 23:00:00'):
            self.env['hr.attendance']._cron_auto_check_out_specific_time()
        self.assertRecordValues(attendance, [{
            'out_mode': 'auto_check_out',
            'state': 'draft',
        }])
        self.assertGreater(attendance.worked_hours, 10)

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

    def test_auto_check_out_ignores_refused_attendance(self):
        """The automatic check-out closes the attendance once it has worked its expected hours: a refused attendance
        of the day did not happen, it takes no share of the day's hours."""
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
        # 8h expected, none taken by the refused morning
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
        help_data = self.env['hr.attendance'].with_user(light).with_context(my_attendances=True).get_help_data([])
        self.assertEqual(help_data['welcome'], 'Welcome Light! Log your attendances here.', "The name of the employee, not of the user")

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

        # the attendances of the archived employees are not counted
        self.employee.active = False
        counts = self.env['hr.attendance'].with_user(officer).get_attendance_dashboard_data()
        self.assertEqual(counts['to_review'], 0)
        self.assertEqual(counts['at_work'], 0)
        self.employee.active = True

        # To Review opens the dashboard action, filtered, under its own URL
        to_review = self.env['hr.attendance'].with_user(officer)._get_to_review_action()
        self.assertEqual(to_review['id'], self.env.ref('hr_attendance.hr_attendance_action').id)
        self.assertEqual(to_review['name'], 'To Review')
        self.assertEqual(to_review['display_name'], 'To Review')
        self.assertEqual(to_review['context'], {'search_default_state_draft': 1})
        self.assertEqual(to_review['views'][0][1], 'list')
        self.assertNotIn('path', to_review)

    @freeze_time('2024-01-03 06:00:00')
    def test_overtime_timezones(self):
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
            self.assertAlmostEqual(employee.total_overtime, 0.0, places=2, msg=tz)

            self.env['hr.attendance'].create({
                'employee_id': employee.id,
                'check_in': to_utc(17),
                'check_out': to_utc(18),
            })
            self.assertAlmostEqual(employee.total_overtime, 1.0, places=2, msg=tz)


@tagged('post_install', '-at_install', 'attendance_process')
class TestAttendanceDefaultShift(TransactionCase):
    """Default check in / out proposed when a day cell is clicked in the calendar or gantt view."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Calendar = cls.env['resource.calendar']
        cls.calendar_8h = cls.env.ref('resource.resource_calendar_std')
        cls.calendar_two_slots = Calendar.create({
            'name': 'Two slots',
            'attendance_ids': [Command.clear()] + [
                Command.create({'dayofweek': str(day), 'hour_from': hour_from, 'hour_to': hour_to})
                for day in range(5) for hour_from, hour_to in ((8, 12), (13, 17))
            ],
        })
        cls.calendar_nine_to_five = Calendar.create({
            'name': '9-17',
            'attendance_ids': [Command.clear()] + [
                Command.create({'dayofweek': str(day), 'hour_from': 9, 'hour_to': 17}) for day in range(5)
            ],
        })
        cls.calendar_flexible = Calendar.create({
            'name': 'Flexible', 'calendar_type': 'undefined', 'hours_per_day': 7.6, 'hours_per_week': 38,
        })
        cls.calendar_fully_flexible = Calendar.create({
            'name': 'Fully flexible', 'calendar_type': 'undefined', 'hours_per_day': 0, 'hours_per_week': 0,
        })

        # A week outside the daylight saving time transitions
        cls.monday = date(2026, 11, 9)
        cls.wednesday = cls.monday + timedelta(days=2)
        cls.saturday = cls.monday + timedelta(days=5)

    def _employee(self, calendar, tz=USER_TZ):
        return self.env['hr.employee'].create({'name': calendar.name, 'tz': tz, 'resource_calendar_id': calendar.id})

    def _default_shift(self, employee, day, start_hour=0, stop_hour=24, all_day=True, tz=USER_TZ):
        """Open a new attendance form as a view does when a day cell is clicked.

        The gantt view sends the whole day (00:00 -> 24:00), the calendar view 07:00 -> 19:00,
        both in the browser's timezone ``tz``, and the clicked day.
        """
        context = {
            'tz': tz,
            'default_employee_id': employee.id,
            'default_check_in': str(utc(day, start_hour, tz=tz)),
            'default_check_out': str(utc(day, stop_hour, tz=tz)),
        }
        if all_day:
            context.update(isAllDay=True, allDayDate=str(day))
        form = Form(self.env['hr.attendance'].with_context(context))
        return form.check_in, form.check_out

    def test_first_planned_slot(self):
        """ If there are multiple slots in the employee's agenda for a specific day, we pick the first one. """
        employee = self._employee(self.calendar_8h)
        self.assertEqual(self._default_shift(employee, self.wednesday), (utc(self.wednesday, 8), utc(self.wednesday, 16)))

        employee = self._employee(self.calendar_two_slots)
        self.assertEqual(
            self._default_shift(employee, self.wednesday), (utc(self.wednesday, 8), utc(self.wednesday, 12)),
            "Only the first slot of the day is proposed")

    def test_gantt_and_calendar_ranges(self):
        """ Calendar view and gantt view should return the same default values """
        employee = self._employee(self.calendar_two_slots)
        self.assertEqual(
            self._default_shift(employee, self.wednesday, start_hour=7, stop_hour=19),
            self._default_shift(employee, self.wednesday),
            "The calendar (07:00 -> 19:00) and the gantt (whole day) give the same shift")

    def test_flexible_hours(self):
        """ If flexible hours, we use the average hours per day, centered around noon."""
        employee = self._employee(self.calendar_flexible)
        self.assertEqual(
            self._default_shift(employee, self.wednesday),
            (utc(self.wednesday, 8, 12), utc(self.wednesday, 15, 48)))

    def test_no_planned_slot(self):
        """ If no planned slot for that day, we use the average hours per day, centered around noon. """
        employee = self._employee(self.calendar_two_slots)
        self.assertEqual(
            self._default_shift(employee, self.saturday), (utc(self.saturday, 8), utc(self.saturday, 16)),
            "Without a planned slot, the average day is centered on noon")

        self.env['resource.calendar.leaves'].create({
            'name': 'Leave',
            'calendar_id': self.calendar_two_slots.id,
            'resource_id': employee.resource_id.id,
            'date_from': utc(self.wednesday, 0),
            'date_to': utc(self.wednesday, 24),
        })
        self.assertEqual(
            self._default_shift(employee, self.wednesday), (utc(self.wednesday, 8), utc(self.wednesday, 16)),
            "A day of absence has no planned slot")

    def test_no_average_hours(self):
        """ If no average hour, the default slot starts at 7am and has a duration of 0 """
        employee = self._employee(self.calendar_fully_flexible)
        check_in, check_out = self._default_shift(employee, self.wednesday)
        self.assertEqual((check_in, check_out), (utc(self.wednesday, 7), utc(self.wednesday, 7)))
        attendance = self.env['hr.attendance'].create({
            'employee_id': employee.id, 'check_in': check_in, 'check_out': check_out,
        })
        self.assertEqual(attendance.worked_hours, 0)

    def test_version_calendar(self):
        """ We use the version that is valid for the attendance date. """
        # Today is Monday 9 November 2026: the current version is the 8h one
        with freeze_time(self.monday):
            # From 1 January 2026: 8h calendar (08:00 -> 16:00)
            employee = self._employee(self.calendar_8h)
            employee.version_id.write({'date_version': date(2026, 1, 1), 'contract_date_start': date(2026, 1, 1)})
            # From Wednesday 11 November 2026: two slots calendar (08:00 -> 12:00, 13:00 -> 17:00)
            employee.create_version({'date_version': self.wednesday, 'resource_calendar_id': self.calendar_two_slots.id})
            # Monday 9 November 2026
            self.assertEqual(
                self._default_shift(employee, self.monday), (utc(self.monday, 8), utc(self.monday, 16)),
                "Before Wednesday, the 8h calendar of the previous version is used")
            # Wednesday 11 November 2026
            self.assertEqual(
                self._default_shift(employee, self.wednesday), (utc(self.wednesday, 8), utc(self.wednesday, 12)),
                "The calendar of the version in effect on the clicked day is used, not the current one")

    def test_employee_in_another_timezone(self):
        """ The employee timezone is computed when the attendance is created.
        So that the user can be warned if there's a mismatch that can lead to confusion. """
        employee = self._employee(self.calendar_nine_to_five, tz='America/New_York')
        check_in, check_out = self._default_shift(employee, self.wednesday)
        self.assertEqual(
            (check_in, check_out), (utc(self.wednesday, 15), utc(self.wednesday, 23)),
            "The real hours of the employee: 09:00 -> 17:00 in New York")

        attendance = self.env['hr.attendance'].create({
            'employee_id': employee.id, 'check_in': check_in, 'check_out': check_out,
        })
        self.assertEqual(attendance.employee_tz, 'America/New_York',
                        msg="The attendance.employee_tz should match the employee timezone")

    def test_clicked_day_in_employee_timezone(self):
        """ The attendance is created with the employee timezone, even though it may be
        timezone translated in the user's browser."""
        sydney = 'Australia/Sydney'
        employee = self._employee(self.calendar_8h, tz=sydney)
        self.assertEqual(
            self._default_shift(employee, self.wednesday),
            (utc(self.wednesday, 8, tz=sydney), utc(self.wednesday, 16, tz=sydney)),
            "Wednesday in Sydney, which starts on Tuesday in Brussels")
        self.assertEqual(
            self._default_shift(employee, self.wednesday, tz=sydney),
            (utc(self.wednesday, 8, tz=sydney), utc(self.wednesday, 16, tz=sydney)),
            "The browser's timezone does not matter")

        new_york = 'America/New_York'
        employee = self._employee(self.calendar_fully_flexible, tz=new_york)
        self.assertEqual(
            self._default_shift(employee, self.wednesday),
            (utc(self.wednesday, 7, tz=new_york), utc(self.wednesday, 7, tz=new_york)),
            "The fallback is at 07:00 for the employee")

    def test_without_all_day(self):
        employee = self._employee(self.calendar_two_slots)
        self.assertEqual(
            self._default_shift(employee, self.wednesday, start_hour=9, stop_hour=11, all_day=False),
            (utc(self.wednesday, 9), utc(self.wednesday, 11)),
            "A time slot selection is kept as is")

    def _working_hours(self, employee, tz=USER_TZ):
        """Business hours drawn by the attendance calendar for the week of ``self.monday``, viewed in ``tz``."""
        hours = self.env['hr.attendance'].with_context(tz=tz).get_working_hours_for_calendar(
            employee.id, str(self.monday), str(self.monday + timedelta(days=6)))
        return sorted((hour['daysOfWeek'][0], hour['startTime'], hour['endTime']) for hour in hours)

    def test_working_hours_for_calendar(self):
        """The calendar shades what is outside the schedule of the employee, on the clock of the viewer."""
        employee = self._employee(self.calendar_two_slots)
        self.assertEqual(
            self._working_hours(employee),
            [(day, start, end) for day in range(1, 6) for start, end in (('08:00', '12:00'), ('13:00', '17:00'))],
            "FullCalendar numbers the days from Sunday (0)")

        # 09:00 -> 17:00 in Honolulu (UTC-10) is 20:00 -> 04:00 in Brussels (UTC+1): split on each day
        employee = self._employee(self.calendar_nine_to_five, tz='Pacific/Honolulu')
        hours = self._working_hours(employee)
        self.assertIn((1, '20:00', '24:00'), hours, "Monday evening in Brussels")
        self.assertIn((2, '00:00', '04:00'), hours, "The rest of the Monday shift, on Tuesday in Brussels")
        self.assertNotIn((1, '00:00', '04:00'), hours, "Sunday's shift is not worked")

        employee = self._employee(self.calendar_flexible)
        self.assertEqual(
            self._working_hours(employee), [],
            "An undefined schedule has no working hours: everything is shaded")
