# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time
from odoo.tests import tagged, TransactionCase
from odoo import Command


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSandwichLeave(TransactionCase):

    def setUp(self):
        super().setUp()
        self.indian_company = self.env['res.company'].create({
            'name': 'Test Indian Company',
            'country_id': self.env.ref('base.in').id
        })
        self.env = self.env(context=dict(self.env.context, allowed_company_ids=self.indian_company.ids))
        self.demo_user = self.env["res.users"].with_company(self.indian_company).create({
            "login": "piyush",
            "name": "piyush_demo",
            "group_ids": [Command.link(self.env.ref("base.group_user").id)]
        })

        self.demo_employee = self.env['hr.employee'].with_company(self.indian_company).create({
            'name': 'Piyush',
            'user_id': self.demo_user.id,
        })

        self.leave_type_day, self.leave_type_half_day, self.leave_type_hours, self.leave_type_day_without_sl = self.env['hr.leave.type'].create([{
            'name': 'Test Leave Type',
            'request_unit': 'day',
            'requires_allocation': False,
            'l10n_in_is_sandwich_leave': True,
            'company_id': self.indian_company.id,
        }, {
            'name': 'Test Leave Type 2',
            'request_unit': 'half_day',
            'requires_allocation': False,
            'l10n_in_is_sandwich_leave': True,
            'company_id': self.indian_company.id,
        }, {
            'name': 'Test Leave Type 3',
            'request_unit': 'hour',
            'requires_allocation': False,
            'l10n_in_is_sandwich_leave': True,
            'company_id': self.indian_company.id,
        }, {
            'name': 'Test leave type without sandwich leave',
            'request_unit': 'day',
            'requires_allocation': False,
            'company_id': self.indian_company.id,
        }])
        self.rahul_emp = self.env['hr.employee'].create({
            'name': 'Rahul',
            'country_id': self.env.ref('base.in').id,
            'company_id': self.indian_company.id,
        })
        self.wednesday_public_holiday = self.env['resource.calendar.leaves'].create({
            'name': 'test public holiday',
            'date_from': '2025-01-29 00:00:00',
            'date_to': '2025-01-29 23:59:59',
            'resource_id': False,
        })

    def test_approved_leave_does_not_raise_access_error(self):
        """
        Ensure opening a validated time off as a normal user
        does not raise a UserError or AccessError
        """
        approved_leave = self.env['hr.leave'].create({
            'name': 'Approved Sandwich Leave',
            'employee_id': self.demo_employee.id,
            'holiday_status_id': self.leave_type_day.id,
            'request_date_from': '2025-08-14',
            'request_date_to': '2025-08-18',
            'state': 'confirm',
        })
        approved_leave.action_approve()
        self.assertIsNotNone(approved_leave.with_user(self.demo_user).leave_type_increases_duration)

        approved_leave_without_sl = self.env['hr.leave'].create({
            'name': 'Without sandwich leave',
            'employee_id': self.demo_employee.id,
            'holiday_status_id': self.leave_type_day_without_sl.id,
            'request_date_from': '2025-12-15',
            'request_date_to': '2025-12-15',
            'state': 'confirm',
        })
        approved_leave_without_sl.action_approve()
        self.assertEqual(
            approved_leave_without_sl.with_user(self.demo_user)._get_durations()[approved_leave_without_sl.id][0],
            1
        )

    def test_long_sandwich_leave(self):
        self.env['resource.calendar.leaves'].create({
            'name': "Independence Day",
            'date_from': "2025-08-15",
            'date_to': "2025-08-15",
            'resource_id': False,
            'company_id': self.indian_company.id,
        })
        holiday_leave = self.env['hr.leave'].create({
            'name': "Test Leave",
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type_day.id,
            'request_date_from': "2025-08-13",
            'request_date_to': "2025-08-17",
        })
        self.assertEqual(holiday_leave.number_of_days, 2, "The total leaves should be 2")

    def test_half_day_leave(self):
        half_leave = self.env['hr.leave'].create({
            'name': "Half Day Leave",
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type_half_day.id,
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
            'holiday_status_id': self.leave_type_day.id,
            'request_date_from': "2025-01-17",
            'request_date_to': "2025-01-20",
        })
        self.assertTrue(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 4)

    @freeze_time('2025-01-15')
    def test_sandwich_leave_saturday_monday(self):
        holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type_day.id,
            'request_date_from': "2025-01-18",
            'request_date_to': "2025-01-20",
        })
        self.assertFalse(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 1)

    @freeze_time('2025-01-15')
    def test_sandwich_leave_friday_sunday(self):
        holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type_day.id,
            'request_date_from': "2025-01-17",
            'request_date_to': "2025-01-19",
        })
        self.assertFalse(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 1)

    @freeze_time('2025-01-15')
    def test_sandwich_leave_saturday_sunday(self):
        holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type_day.id,
            'request_date_from': "2025-01-18",
            'request_date_to': "2025-01-19",
        })
        self.assertFalse(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 0)

    @freeze_time('2025-01-15')
    def test_sandwich_leave_saturday(self):
        holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type_day.id,
            'request_date_from': "2025-01-18",
            'request_date_to': "2025-01-18",
        })
        self.assertFalse(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 0)

    @freeze_time('2025-01-15')
    def test_sandwich_leave_sunday(self):
        holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type_day.id,
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
            'holiday_status_id': self.leave_type_day.id,
            'request_date_from': "2025-01-28",
            'request_date_to': "2025-01-30",
        })
        self.assertTrue(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 3)

    @freeze_time('2025-01-15')
    def test_sandwich_leave_2days_stop_with_public_holidays(self):
        holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type_day.id,
            'request_date_from': "2025-01-28",
            'request_date_to': "2025-01-29",
        })
        self.assertFalse(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 1)

    @freeze_time('2025-01-15')
    def test_sandwich_leave_2days_start_with_public_holidays(self):
        holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type_day.id,
            'request_date_from': "2025-01-29",
            'request_date_to': "2025-01-30",
        })
        self.assertFalse(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 1)

    @freeze_time('2025-01-15')
    def test_sandwich_leave_public_holidays(self):
        holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type_day.id,
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
            'holiday_status_id': self.leave_type_day.id,
            'request_date_from': "2025-01-18",
            'request_date_to': "2025-02-01",
        })
        self.assertTrue(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 12)

    @freeze_time('2025-01-15')
    def test_sandwich_in_two_part_1(self):
        """
            -- woking days: 28th and 30th January
            -- non-working days: 29th January (public holiday)
        """
        before_holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type_day.id,
            'request_date_from': "2025-01-28",
            'request_date_to': "2025-01-28",
        })
        after_holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type_day.id,
            'request_date_from': "2025-01-30",
            'request_date_to': "2025-01-30",
        })

        self.assertFalse(before_holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(before_holiday_leave.number_of_days, 1)
        self.assertTrue(after_holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(after_holiday_leave.number_of_days, 2)

    @freeze_time('2025-01-15')
    def test_sandwich_in_two_part_2(self):
        """
            -- woking days: 28th and 30th January
            -- non-working days: 29th January (public holiday)
        """
        before_holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type_day.id,
            'request_date_from': "2025-01-28",
            'request_date_to': "2025-01-28",
        })
        after_holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type_day.id,
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
            'holiday_status_id': self.leave_type_day.id,
            'request_date_from': "2025-01-18",
            'request_date_to': "2025-01-24",
        })
        after_holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type_day.id,
            'request_date_from': "2025-01-27",
            'request_date_to': "2025-02-01",
        })
        self.assertFalse(before_holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(before_holiday_leave.number_of_days, 5)
        self.assertTrue(after_holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(after_holiday_leave.number_of_days, 7)

    @freeze_time('2025-01-15')
    def test_sandwich_for_leave_type_hours(self):
        """
            --working days: 24th and 27th January
            --non-working days: 25th, 26th January
        """
        before_holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type_hours.id,
            'request_date_from': "2025-01-24",
            'request_date_to': "2025-01-24",
        })
        after_holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type_hours.id,
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
            'holiday_status_id': self.leave_type_half_day.id,
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
            'holiday_status_id': self.leave_type_half_day.id,
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
            'holiday_status_id': self.leave_type_half_day.id,
            'request_date_from': "2025-12-12",
            'request_date_to': "2025-12-12",
            'request_date_from_period': 'am',
            'request_date_to_period': 'pm',
        })
        after_holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type_half_day.id,
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
    def test_sandwich_for_two_different_leave_type(self):
        """
            This test ensure that if we have different leave type around the non-working days and one of them
            doesn't enabled sandwich leave then it's not calculated as sandwich leave
            --working days: 24th and 27th January
            --non-working days: 25th, 26th January
        """
        other_leave_type = self.env['hr.leave.type'].create({
            'name': 'Test Leave Type',
            'request_unit': 'day',
            'requires_allocation': False,
        })
        before_holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': other_leave_type.id,
            'request_date_from': "2025-01-24",
            'request_date_to': "2025-01-24",
        })
        after_holiday_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type_day.id,
            'request_date_from': "2025-01-27",
            'request_date_to': "2025-01-27",
        })
        self.assertFalse(before_holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(before_holiday_leave.number_of_days, 1)
        self.assertFalse(after_holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(after_holiday_leave.number_of_days, 1)

        # checking for different leave type with sandwich set as True
        other_leave_type.l10n_in_is_sandwich_leave = True
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
            'holiday_status_id': self.leave_type_hours.id,
            'request_date_from': "2025-01-24",
            'request_date_to': "2025-01-24",
            'request_hour_from': 8.0,
            'request_hour_to': 12.0,
        })
        full_leave = self.env['hr.leave'].create({
            'name': 'Full Monday Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type_hours.id,
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
            'holiday_status_id': self.leave_type_hours.id,
            'request_date_from': "2025-01-17",
            'request_date_to': "2025-01-17",
        })
        full_leave = self.env['hr.leave'].create({
            'name': 'Full Monday Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type_hours.id,
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
        })
        before_leave = self.env['hr.leave'].create({
            'name': 'Test Leave Before',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type_day.id,
            'request_date_from': "2025-07-03",
            'request_date_to': "2025-07-04",
        })
        self.assertEqual(before_leave.number_of_days, 2)

        after_leave = self.env['hr.leave'].create({
            'name': 'Test Leave After',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type_day.id,
            'request_date_from': "2025-07-10",
            'request_date_to': "2025-07-11",
        })
        self.assertEqual(after_leave.number_of_days, 2)

        middle_sandwich_leave = self.env['hr.leave'].create({
            'name': 'Test Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type_day.id,
            'request_date_from': "2025-07-07",
            'request_date_to': "2025-07-08",
        })
        self.assertTrue(middle_sandwich_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(middle_sandwich_leave.number_of_days, 5)

    @freeze_time('2025-07-15')
    def test_sandwich_when_linked_leave_delete(self):
        before_leave = self.env['hr.leave'].create({
            'name': 'Monday Leave',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type_day.id,
            'request_date_from': "2025-07-11",
            'request_date_to': "2025-07-11",
        })
        self.assertEqual(before_leave.number_of_days, 1)

        after_leave = self.env['hr.leave'].create({
            'name': 'Friday',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type_day.id,
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
            'holiday_status_id': self.leave_type_day.id,
            'request_date_from': "2025-07-11",
            'request_date_to': "2025-07-11",
        })
        self.assertEqual(before_leave.number_of_days, 1)

        after_leave = self.env['hr.leave'].create({
            'name': 'Fri',
            'employee_id': self.rahul_emp.id,
            'holiday_status_id': self.leave_type_day.id,
            'request_date_from': "2025-07-14",
            'request_date_to': "2025-07-14",
        })
        self.assertTrue(after_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(after_leave.number_of_days, 3)

        # Refuse the linked Monday leave -> Friday should drop back to 1 day
        before_leave.action_refuse()
        self.assertEqual(after_leave.number_of_days, 1)
