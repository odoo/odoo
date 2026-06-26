# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from freezegun import freeze_time

from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSandwichLeave(TransactionCase):

    def setUp(self):
        super().setUp()
        self.indian_company = self.env['res.company'].create({
            'name': 'Test Indian Company',
            'country_id': self.env.ref('base.in').id,
            'tz': 'UTC',
        })
        self.test_calendar = self.env["resource.calendar"].create({
            "name": "Test 8-17 Calendar",
            "company_id": self.indian_company.id,
            "attendance_ids": [
                Command.create({
                    "dayofweek": str(day),
                    "hour_from": hour_from,
                    "hour_to": hour_to,
                })
                for day in range(5)
                for hour_from, hour_to in (
                    (8, 12),
                    (13, 17),
                )
            ]},
        )
        self.indian_company.resource_calendar_id = self.test_calendar
        self.env = self.env(context=dict(self.env.context, allowed_company_ids=self.indian_company.ids))
        self.demo_user = self.env["res.users"].with_company(self.indian_company).create({
            "login": "piyush",
            "name": "piyush_demo",
            "group_ids": [Command.link(self.env.ref("base.group_user").id), Command.link(self.env.ref("hr_holidays.group_hr_holidays_employee").id)],
        })

        self.demo_employee = self.env['hr.employee'].with_company(self.indian_company).create({
            'name': 'Piyush',
            'user_id': self.demo_user.id,
        })

        self.work_entry_type_day, self.work_entry_type_half_day, self.work_entry_type_hours, self.work_entry_type_day_without_sl, self.work_entry_type_public_holiday = self.env['hr.work.entry.type'].create([{
            'name': 'Test Leave Type',
            'code': 'Test Leave Type',
            'request_unit': 'day',
            'unit_of_measure': 'day',
            'requires_allocation': False,
            'l10n_in_is_sandwich_leave': True,
            'count_as': 'absence',
        }, {
            'name': 'Test Leave Type 2',
            'code': 'Test Leave Type 2',
            'request_unit': 'half_day',
            'unit_of_measure': 'day',
            'requires_allocation': False,
            'l10n_in_is_sandwich_leave': True,
            'count_as': 'absence',
        }, {
            'name': 'Test Leave Type 3',
            'code': 'Test Leave Type 3',
            'request_unit': 'hour',
            'unit_of_measure': 'hour',
            'requires_allocation': False,
            'l10n_in_is_sandwich_leave': True,
            'count_as': 'absence',
        }, {
            'name': 'Test leave type without sandwich leave',
            'code': 'Test leave type without sandwich leave',
            'request_unit': 'day',
            'requires_allocation': False,
            'count_as': 'absence',
        }, {
            'name': 'Public Holiday',
            'code': 'Public Holiday',
            'request_unit': 'day',
            'unit_of_measure': 'day',
            'requires_allocation': False,
            'count_as': 'absence',
        }])
        self.rahul_emp = self.env['hr.employee'].create({
            'name': 'Rahul',
            'country_id': self.env.ref('base.in').id,
            'company_id': self.indian_company.id,
            'resource_calendar_id': self.test_calendar.id,
            'contract_date_start': '2024-12-01',
            'date_version': '2024-12-01',
            'wage': 100000,
        })
        self.wednesday_public_holiday = self.env['resource.calendar.leaves'].create({
            'name': 'test public holiday',
            'date_from': '2025-01-29 00:00:00',
            'date_to': '2025-01-29 23:59:59',
            'resource_id': False,
            'company_id': self.indian_company.id,
            'work_entry_type_id': self.work_entry_type_public_holiday.id,
        })

    def _generate_and_search_work_entries(self, employee, date_from, date_to):
        work_entry_vals = employee.version_id.generate_work_entries(date_from.date(), date_to.date())
        return sorted([
            vals for vals in work_entry_vals
            if vals.get('employee_id') in (employee, employee.id)
            and date_from.date() <= vals.get('date') <= date_to.date()
        ], key=lambda vals: vals['date'])

    def _assert_work_entries_type(self, work_entries, expected_work_entry_type):
        self.assertTrue(work_entries, "Expected generated work entries to validate their type.")
        for entry in work_entries:
            work_entry_type = entry.get('work_entry_type_id')
            self.assertEqual(work_entry_type.id, expected_work_entry_type.id)

    def test_approved_leave_does_not_raise_access_error(self):
        """
        Ensure opening a validated time off as a normal user
        does not raise a UserError or AccessError
        """
        approved_leave = self.env['hr.leave'].create({
            'name': 'Approved Sandwich Leave',
            'employee_id': self.demo_employee.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': '2025-08-14',
            'request_date_to': '2025-08-18',
            'state': 'confirm',
        })
        self.assertIsNotNone(approved_leave.with_user(self.demo_user).work_entry_type_increases_duration)

        approved_leave_without_sl = self.env['hr.leave'].create({
            'name': 'Without sandwich leave',
            'employee_id': self.demo_employee.id,
            'work_entry_type_id': self.work_entry_type_day_without_sl.id,
            'request_date_from': '2025-12-15',
            'request_date_to': '2025-12-15',
            'state': 'confirm',
        })
        self.assertEqual(
            approved_leave_without_sl.with_user(self.demo_user)._get_durations()[approved_leave_without_sl.id][0],
            1
        )

    def test_long_sandwich_leave(self):
        self.env['resource.calendar.leaves'].create({
            'name': "Independence Day",
            'date_from': "2025-08-15 00:00:00",
            'date_to': "2025-08-15 23:59:59",
            'resource_id': False,
            'work_entry_type_id': self.work_entry_type_public_holiday.id,
            'company_id': self.indian_company.id,
        })
        holiday_leave = self.env['hr.leave'].create({
            'name': "Test Leave",
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2025-08-13",
            'request_date_to': "2025-08-17",
        })
        self.assertEqual(holiday_leave.number_of_days, 2, "The total leaves should be 2")
        holiday_leave._action_validate()
        work_entries = self._generate_and_search_work_entries(
            self.rahul_emp,
            datetime(2025, 8, 13),
            datetime(2025, 8, 17),
        )
        self.assertEqual(len(work_entries), 3)
        self._assert_work_entries_type(work_entries[:1], self.work_entry_type_day)
        self._assert_work_entries_type(work_entries[2:], self.work_entry_type_public_holiday)

    def test_half_day_leave(self):
        half_leave = self.env['hr.leave'].create({
            'name': "Half Day Leave",
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_half_day.id,
            'request_date_from': "2025-08-29",
            'request_date_to': "2025-08-29",
            'request_date_from_period': 'am',
            'request_date_to_period': 'am',
        })

        leave = half_leave._get_durations()
        self.assertEqual(leave[half_leave.id][0], 0.5, "The total leaves should be 0.5")

    @freeze_time('2025-01-15')
    def test_sandwich_leave_friday_monday(self):
        holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2025-01-17",
            'request_date_to': "2025-01-20",
        })
        self.assertTrue(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 4)
        holiday_leave._action_validate()
        work_entries = self._generate_and_search_work_entries(
            self.rahul_emp,
            datetime(2025, 1, 17),
            datetime(2025, 1, 20),
        )
        self.assertEqual(len(work_entries), 4)
        self._assert_work_entries_type(work_entries, self.work_entry_type_day)

    @freeze_time('2025-01-15')
    def test_updating_older_leave_does_not_reclaim_sandwich_days(self):
        friday_leave = self.env['hr.leave'].create({
            'name': 'Friday Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2025-01-17",
            'request_date_to': "2025-01-17",
        })
        monday_leave = self.env['hr.leave'].create({
            'name': 'Monday Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2025-01-20",
            'request_date_to': "2025-01-20",
        })
        self.assertTrue(monday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(monday_leave.number_of_days, 3)

        friday_leave.with_context(leave_skip_state_check=True).write({
            'request_date_from': "2025-01-16",
            'request_date_to': "2025-01-17",
        })
        self.assertFalse(friday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(friday_leave.number_of_days, 2)
        self.assertTrue(monday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(monday_leave.number_of_days, 3)

        (monday_leave + friday_leave)._action_validate()
        work_entries = self._generate_and_search_work_entries(
            self.rahul_emp,
            datetime(2025, 1, 16),
            datetime(2025, 1, 20),
        )
        self.assertEqual(len(work_entries), 5)
        self._assert_work_entries_type(work_entries, self.work_entry_type_day)

    @freeze_time('2025-01-15')
    def test_sandwich_leave_saturday_monday(self):
        holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2025-01-18",
            'request_date_to': "2025-01-20",
        })
        self.assertFalse(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 1)

    @freeze_time('2025-01-15')
    def test_sandwich_leave_friday_sunday(self):
        holiday_leave = self.env['hr.leave'].with_context(leave_fast_create=True).create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2025-01-17",
            'request_date_to': "2025-01-19",
        })
        self.assertFalse(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 1)

    @freeze_time('2025-01-15')
    def test_sandwich_leave_saturday_sunday(self):
        holiday_leave = self.env['hr.leave'].with_context(leave_fast_create=True).create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2025-01-18",
            'request_date_to': "2025-01-19",
        })
        self.assertFalse(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 0)

    @freeze_time('2025-01-15')
    def test_sandwich_leave_saturday(self):
        holiday_leave = self.env['hr.leave'].with_context(leave_fast_create=True).create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2025-01-18",
            'request_date_to': "2025-01-18",
        })
        self.assertFalse(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 0)

    @freeze_time('2025-01-15')
    def test_sandwich_leave_sunday(self):
        holiday_leave = self.env['hr.leave'].with_context(leave_fast_create=True).create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2025-01-19",
            'request_date_to': "2025-01-19",
        })
        self.assertFalse(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 0)

    @freeze_time('2025-01-15')
    def test_sandwich_leave_3days_with_public_holidays(self):
        holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2025-01-28",
            'request_date_to': "2025-01-30",
        })
        self.assertTrue(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 3)
        holiday_leave._action_validate()
        work_entries = self._generate_and_search_work_entries(
            self.rahul_emp,
            datetime(2025, 1, 28),
            datetime(2025, 1, 30),
        )
        self.assertEqual(len(work_entries), 3)
        self._assert_work_entries_type(work_entries[:1], self.work_entry_type_day)
        self._assert_work_entries_type(work_entries[2:], self.work_entry_type_day)

    @freeze_time('2025-03-01')
    def test_sandwich_leave_with_utc_full_day_public_holiday(self):
        """
            Public holiday for one full local day in IST:
            - local day: 12-Mar-2025 12:00 AM to 11:59:59 PM
            - UTC value: 11-Mar-2025 18:30:00 to 12-Mar-2025 18:29:59
        """
        self.env['resource.calendar.leaves'].create({
            'name': 'IST Full Day Public Holiday',
            'date_from': '2025-03-11 18:30:00',
            'date_to': '2025-03-12 18:29:59',
            'resource_id': False,
            'company_id': self.indian_company.id,
        })
        self.indian_company.tz = 'Asia/Kolkata'
        before_holiday_leave = self.env['hr.leave'].create({
            'name': 'Before Public Holiday',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': '2025-03-11',
            'request_date_to': '2025-03-11',
        })
        after_holiday_leave = self.env['hr.leave'].create({
            'name': 'After Public Holiday',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': '2025-03-13',
            'request_date_to': '2025-03-13',
        })

        self.assertFalse(before_holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(before_holiday_leave.number_of_days, 1)
        self.assertTrue(after_holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(after_holiday_leave.number_of_days, 2)

    @freeze_time('2025-01-15')
    def test_sandwich_leave_2days_stop_with_public_holidays(self):
        holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2025-01-28",
            'request_date_to': "2025-01-29",
        })
        self.assertFalse(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 1)
        holiday_leave._action_validate()
        work_entries = self._generate_and_search_work_entries(
            self.rahul_emp,
            datetime(2025, 1, 28),
            datetime(2025, 1, 29),
        )
        self.assertEqual(len(work_entries), 2)
        self._assert_work_entries_type(work_entries[:1], self.work_entry_type_day)
        self._assert_work_entries_type(work_entries[1:], self.work_entry_type_public_holiday)

    @freeze_time('2025-01-15')
    def test_sandwich_leave_2days_start_with_public_holidays(self):
        holiday_leave = self.env['hr.leave'].with_context(leave_fast_create=True).create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2025-01-29",
            'request_date_to': "2025-01-30",
        })
        self.assertFalse(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 1)
        holiday_leave._action_validate()
        work_entries = self._generate_and_search_work_entries(
            self.rahul_emp,
            datetime(2025, 1, 29),
            datetime(2025, 1, 30),
        )
        self.assertEqual(len(work_entries), 2)
        self._assert_work_entries_type(work_entries[:1], self.work_entry_type_public_holiday)
        self._assert_work_entries_type(work_entries[1:], self.work_entry_type_day)

    @freeze_time('2025-01-15')
    def test_sandwich_leave_public_holidays(self):
        holiday_leave = self.env['hr.leave'].with_context(leave_fast_create=True).create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2025-01-29",
            'request_date_to': "2025-01-29",
        })
        self.assertFalse(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 0)

    @freeze_time('2025-01-15')
    def test_sandwich_in_two_weeks(self):
        holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2025-01-18",
            'request_date_to': "2025-02-01",
        })
        self.assertTrue(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 12)
        holiday_leave._action_validate()
        work_entries = self._generate_and_search_work_entries(
            self.rahul_emp,
            datetime(2025, 1, 18),
            datetime(2025, 2, 1),
        )
        self.assertEqual(len(work_entries), 12)
        self._assert_work_entries_type(work_entries, self.work_entry_type_day)

    @freeze_time('2025-01-15')
    def test_sandwich_in_two_part_1(self):
        """
            -- woking days: 28th and 30th January
            -- non-working days: 29th January (public holiday)
        """
        before_holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2025-01-28",
            'request_date_to': "2025-01-28",
        })
        after_holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2025-01-30",
            'request_date_to': "2025-01-30",
        })

        self.assertFalse(before_holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(before_holiday_leave.number_of_days, 1)
        self.assertTrue(after_holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(after_holiday_leave.number_of_days, 2)
        (before_holiday_leave + after_holiday_leave)._action_validate()
        work_entries = self._generate_and_search_work_entries(
            self.rahul_emp,
            datetime(2025, 1, 28),
            datetime(2025, 1, 30),
        )
        self.assertEqual(len(work_entries), 3)
        self._assert_work_entries_type(work_entries, self.work_entry_type_day)

    @freeze_time('2025-01-15')
    def test_sandwich_in_two_part_2(self):
        """
            -- woking days: 28th and 30th January
            -- non-working days: 29th January (public holiday)
        """
        before_holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2025-01-28",
            'request_date_to': "2025-01-28",
        })
        after_holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2025-01-30",
            'request_date_to': "2025-01-30",
        })
        self.assertFalse(before_holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(before_holiday_leave.number_of_days, 1)
        self.assertTrue(after_holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(after_holiday_leave.number_of_days, 2)

    @freeze_time('2025-01-15')
    def test_sandwich_in_two_weeks_in_two(self):
        before_holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2025-01-18",
            'request_date_to': "2025-01-24",
        })
        after_holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2025-01-27",
            'request_date_to': "2025-02-01",
        })
        self.assertFalse(before_holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(before_holiday_leave.number_of_days, 5)
        self.assertTrue(after_holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(after_holiday_leave.number_of_days, 7)
        (before_holiday_leave + after_holiday_leave)._action_validate()
        work_entries = self._generate_and_search_work_entries(
            self.rahul_emp,
            datetime(2025, 1, 18),
            datetime(2025, 2, 1),
        )
        self.assertEqual(len(work_entries), 12)
        self._assert_work_entries_type(work_entries, self.work_entry_type_day)

    @freeze_time('2025-01-15')
    def test_sandwich_for_work_entry_type_hours(self):
        """
            --working days: 24th and 27th January
            --non-working days: 25th, 26th January
        """
        before_holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_hours.id,
            'request_date_from': "2025-01-24",
            'request_date_to': "2025-01-24",
        })
        after_holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_hours.id,
            'request_date_from': "2025-01-27",
            'request_date_to': "2025-01-27",
        })
        self.assertFalse(before_holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(before_holiday_leave.number_of_hours, 8)
        self.assertTrue(after_holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(after_holiday_leave.number_of_hours, 24)

    @freeze_time('2025-12-10')
    def test_sandwich_for_half_day_spanning_weekend_without_fullday(self):
        """
            --working days: 12th and 15th December
            --non-working days: 13th, 14th December
        """
        holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_half_day.id,
            'request_date_from': "2025-12-12",
            'request_date_to': "2025-12-15",
            'request_date_from_period': 'pm',
            'request_date_to_period': 'am',
        })
        self.assertFalse(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 1)

    @freeze_time('2025-12-10')
    def test_sandwich_for_half_day_spanning_weekend(self):
        """
            --working days: 12th and 15th December
            --non-working days: 13th, 14th December
        """
        holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_half_day.id,
            'request_date_from': "2025-12-12",
            'request_date_to': "2025-12-15",
            'request_date_from_period': 'am',
            'request_date_to_period': 'pm',
        })
        self.assertTrue(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 4)

    @freeze_time('2025-12-10')
    def test_sandwich_for_half_day_full_then_partial(self):
        """
            --working days: 12th and 15th December
            --non-working days: 13th, 14th December
        """
        before_holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_half_day.id,
            'request_date_from': "2025-12-12",
            'request_date_to': "2025-12-12",
            'request_date_from_period': 'am',
            'request_date_to_period': 'pm',
        })
        after_holiday_leave = self.env['hr.leave'].with_context(leave_fast_create=True).create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_half_day.id,
            'request_date_from': "2025-12-15",
            'request_date_to': "2025-12-15",
            'request_date_from_period': 'am',
            'request_date_to_period': 'pm',
        })
        self.assertFalse(before_holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertTrue(after_holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(after_holiday_leave.number_of_days, 3)

        after_holiday_leave.write({
            'request_date_from_period': 'pm',
            'request_date_to_period': 'pm',
        })
        self.assertEqual(after_holiday_leave.number_of_days, 0.5)
        self.assertFalse(after_holiday_leave.l10n_in_contains_sandwich_leaves)

    @freeze_time('2025-01-15')
    def test_sandwich_for_two_different_work_entry_type(self):
        """
            This test ensure that if we have different leave type around the non-working days and one of them
            doesn't enabled sandwich leave then it's not calculated as sandwich leave
            --working days: 24th and 27th January
            --non-working days: 25th, 26th January
        """
        other_work_entry_type = self.env['hr.work.entry.type'].create({
            'name': 'Test Leave Type',
            'code': 'Test Other Leave Type',
            'request_unit': 'day',
            'unit_of_measure': 'day',
            'requires_allocation': False,
            'count_as': 'absence',
        })
        before_holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': other_work_entry_type.id,
            'request_date_from': "2025-01-24",
            'request_date_to': "2025-01-24",
        })
        after_holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2025-01-27",
            'request_date_to': "2025-01-27",
        })
        self.assertFalse(before_holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(before_holiday_leave.number_of_days, 1)
        self.assertFalse(after_holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(after_holiday_leave.number_of_days, 1)

        # checking for different leave type with sandwich set as True
        other_work_entry_type.l10n_in_is_sandwich_leave = True
        leave_duration_dict = after_holiday_leave._get_durations()
        self.assertEqual(leave_duration_dict[after_holiday_leave.id][0], 3)

    @freeze_time('2025-01-15')
    def test_partial_hour_leave_not_counted(self):
        """
            Partial hour leave should not trigger sandwich computations.
            -- working days: 24th and 27th January
            -- non-working days: 25th, 26th January
        """
        partial_leave = self.env['hr.leave'].create({
            'name': 'Partial Friday Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_hours.id,
            'request_date_from': "2025-01-24",
            'request_date_to': "2025-01-24",
            'request_hour_from': 8,
            'request_hour_to': 12,
        })
        full_leave = self.env['hr.leave'].create({
            'name': 'Full Monday Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_hours.id,
            'request_date_from': "2025-01-27",
            'request_date_to': "2025-01-27",
        })
        self.assertFalse(partial_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(partial_leave.number_of_hours, 4)
        self.assertFalse(full_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(full_leave.number_of_hours, 8)

        partial_leave = self.env['hr.leave'].create({
            'name': 'Partial Friday Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_hours.id,
            'request_date_from': "2025-01-17",
            'request_date_to': "2025-01-17",
        })
        full_leave = self.env['hr.leave'].create({
            'name': 'Full Monday Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_hours.id,
            'request_date_from': "2025-01-20",
            'request_date_to': "2025-01-20",
        })

        self.assertFalse(partial_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(partial_leave.number_of_hours, 8)
        self.assertTrue(full_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(full_leave.number_of_hours, 24)

    @freeze_time('2025-07-15')
    def test_bidirectional_sandwich_leave(self):
        """
            This test case verifies that if a sandwich leave is created with a before and after linked sandwich leave,
            -- public holiday: 9th July(wednesday)
            -- working days: 3th-4th(Thu-Fri) July, 7th-8th(Mon-Tue) July, 10th-11th(Thu-Fri) July
            -- non-working days: 5th-6th(Sat-Sun) July,
        """
        self.env['resource.calendar.leaves'].create({
            'name': 'Public Holiday',
            'date_from': '2025-07-09 00:00:00',
            'date_to': '2025-07-09 23:59:59',
            'work_entry_type_id': self.work_entry_type_public_holiday.id,
        })
        before_leave = self.env['hr.leave'].create({
            'name': 'Test Leave Before',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2025-07-03",
            'request_date_to': "2025-07-04",
        })
        self.assertEqual(before_leave.number_of_days, 2)

        after_leave = self.env['hr.leave'].create({
            'name': 'Test Leave After',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2025-07-10",
            'request_date_to': "2025-07-11",
        })
        self.assertEqual(after_leave.number_of_days, 2)

        middle_sandwich_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2025-07-07",
            'request_date_to': "2025-07-08",
        })
        self.assertTrue(middle_sandwich_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(middle_sandwich_leave.number_of_days, 5)
        (before_leave + middle_sandwich_leave + after_leave)._action_validate()
        work_entries = self._generate_and_search_work_entries(
            self.rahul_emp,
            datetime(2025, 7, 3),
            datetime(2025, 7, 11),
        )
        self.assertEqual(len(work_entries), 9)
        self._assert_work_entries_type(work_entries, self.work_entry_type_day)

    @freeze_time('2025-07-15')
    def test_sandwich_when_linked_leave_delete(self):
        before_leave = self.env['hr.leave'].create({
            'name': 'Monday Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2025-07-11",
            'request_date_to': "2025-07-11",
        })
        self.assertEqual(before_leave.number_of_days, 1)

        after_leave = self.env['hr.leave'].create({
            'name': 'Friday',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2025-07-14",
            'request_date_to': "2025-07-14",
        })
        self.assertTrue(after_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(after_leave.number_of_days, 3)

        before_leave.unlink()
        self.assertEqual(after_leave.number_of_days, 1)

    @freeze_time('2025-07-15')
    def test_sandwich_when_linked_leave_refuse(self):
        before_leave = self.env['hr.leave'].create({
            'name': 'Mon',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2025-07-11",
            'request_date_to': "2025-07-11",
        })
        self.assertEqual(before_leave.number_of_days, 1)

        after_leave = self.env['hr.leave'].create({
            'name': 'Fri',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2025-07-14",
            'request_date_to': "2025-07-14",
        })
        self.assertTrue(after_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(after_leave.number_of_days, 3)

        # Refuse the linked Monday leave -> Friday should drop back to 1 day
        before_leave.action_refuse()
        self.assertEqual(after_leave.number_of_days, 1)

    def test_sandwich_leave_weekend_only_policy(self):
        """
        Verify that only weekend days are counted as sandwich days
        when the sandwich policy is set to weekend-only.
        """
        self.work_entry_type_day.l10n_in_sandwich_policy = 'weekend'

        # Create a public holiday on a working day
        # This should be ignored for weekend-only policy
        self.env['resource.calendar.leaves'].create({
            'name': 'test public holiday',
            'date_from': '2026-01-16 00:00:00',  # Friday
            'date_to': '2026-01-16 23:59:59',
            'resource_id': False,
            'work_entry_type_id': self.work_entry_type_public_holiday.id,
        })

        weekend_sandwich_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2026-01-15",  # Thursday
            'request_date_to': "2026-01-19",    # Monday
        })

        self.assertTrue(weekend_sandwich_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(weekend_sandwich_leave.number_of_days, 4)
        weekend_sandwich_leave._action_validate()
        work_entries = self._generate_and_search_work_entries(
            self.rahul_emp,
            datetime(2026, 1, 15),
            datetime(2026, 1, 19),
        )
        self.assertEqual(len(work_entries), 5)
        self._assert_work_entries_type(work_entries[:1], self.work_entry_type_day)
        self._assert_work_entries_type(work_entries[1:2], self.work_entry_type_public_holiday)
        self._assert_work_entries_type(work_entries[2:], self.work_entry_type_day)

    def test_sandwich_leave_public_holiday_only_policy(self):
        """
        Verify that only public holiday days are counted as sandwich days
        when the sandwich policy is set to public-holiday-only.
        """
        self.work_entry_type_day.l10n_in_sandwich_policy = 'public_holiday'

        self.env['resource.calendar.leaves'].create({
            'name': 'test public holiday',
            'date_from': '2026-01-16 00:00:00',  # Friday
            'date_to': '2026-01-16 23:59:59',
            'resource_id': False,
        })

        # Leave from Thursday to Monday with public holiday in between
        public_holiday_sandwich_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2026-01-15",  # Thursday
            'request_date_to': "2026-01-19",    # Monday
        })

        self.assertTrue(public_holiday_sandwich_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(public_holiday_sandwich_leave.number_of_days, 3)
        public_holiday_sandwich_leave._action_validate()
        work_entries = self._generate_and_search_work_entries(
            self.rahul_emp,
            datetime(2026, 1, 15),
            datetime(2026, 1, 19),
        )
        self.assertEqual(len(work_entries), 3)
        self._assert_work_entries_type(work_entries, self.work_entry_type_day)

    @freeze_time('2025-01-15')
    def test_sandwich_leave_reapprove(self):
        self.env['resource.calendar.leaves'].create({
            'name': "Public Holiday",
            'date_from': "2025-01-21",
            'date_to': "2025-01-21",
            'resource_id': False,
            'company_id': self.indian_company.id,
        })

        fri_mon_leave = self.env['hr.leave'].create({
            'name': "Fri-Mon Leave",
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2025-01-17",  # Friday
            'request_date_to': "2025-01-20",    # Monday
        })
        wed_leave = self.env['hr.leave'].create({
            'name': "Wednesday Leave",
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2025-01-22",  # Wednesday
            'request_date_to': "2025-01-22",
        })
        self.assertEqual(fri_mon_leave.number_of_days, 4)
        self.assertEqual(wed_leave.number_of_days, 2)

        # Refuse Fri-Mon: Wed shrinks to 1 day
        fri_mon_leave.action_refuse()
        self.assertEqual(wed_leave.number_of_days, 1)

        # Approve: Fri-Mon = 5 days, Wed = 1 days → total 6
        fri_mon_leave.action_approve()
        self.assertEqual(fri_mon_leave.number_of_days, 5)
        self.assertEqual(wed_leave.number_of_days, 1)

        # Refuse Wed: Fri-Mon shrinks to 4 day
        wed_leave.action_refuse()
        self.assertEqual(fri_mon_leave.number_of_days, 4)

        # Approve: wed = 2 days, Fri-Mon = 4 days → total 6
        wed_leave.action_approve()
        self.assertEqual(fri_mon_leave.number_of_days, 4)
        self.assertEqual(wed_leave.number_of_days, 2)

    @freeze_time('2026-03-10')
    def test_sandwich_leave_multi_public_holiday_bridge(self):
        self.env['resource.calendar.leaves'].create([{
            'name': "Public Holiday 17 March",
            'date_from': "2026-03-17 00:00:00",
            'date_to': "2026-03-17 23:59:59",
            'resource_id': False,
            'work_entry_type_id': self.work_entry_type_public_holiday.id,
            'company_id': self.indian_company.id,
        }, {
            'name': "Public Holiday 19 March",
            'date_from': "2026-03-19 00:00:00",
            'date_to': "2026-03-19 23:59:59",
            'resource_id': False,
            'work_entry_type_id': self.work_entry_type_public_holiday.id,
            'company_id': self.indian_company.id,
        }])

        before_leave = self.env['hr.leave'].create({
            'name': "Before Leave",
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2026-03-13",
            'request_date_to': "2026-03-13",
        })
        after_leave = self.env['hr.leave'].create({
            'name': "After Leave",
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2026-03-16",
            'request_date_to': "2026-03-16",
        })
        self.assertEqual(after_leave.number_of_days, 3)

        leave_20_23 = self.env['hr.leave'].create({
            'name': "Leave 20 to 23 March",
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2026-03-20",
            'request_date_to': "2026-03-23",
        })
        self.assertEqual(leave_20_23.number_of_days, 4)

        leave_18 = self.env['hr.leave'].create({
            'name': "Leave 18 March",
            'employee_id': self.rahul_emp.id,
            'work_entry_type_id': self.work_entry_type_day.id,
            'request_date_from': "2026-03-18",
            'request_date_to': "2026-03-18",
        })
        self.assertEqual(leave_18.number_of_days, 3)
        (before_leave + after_leave + leave_20_23 + leave_18)._action_validate()
        work_entries = self._generate_and_search_work_entries(
            self.rahul_emp,
            datetime(2026, 3, 13, 0, 0, 0),
            datetime(2026, 3, 23, 23, 59, 59),
        )
        self.assertEqual(len(work_entries), 11)
        self._assert_work_entries_type(work_entries, self.work_entry_type_day)
