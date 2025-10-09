# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import pytz

from odoo.exceptions import ValidationError
from odoo.tests.common import tagged
from odoo.fields import Date
from odoo.addons.hr_work_entry_holidays.tests.common import TestWorkEntryHolidaysBase


@tagged('work_entry')
class TestWorkeEntryHolidaysWorkEntry(TestWorkEntryHolidaysBase):
    @classmethod
    def setUpClass(cls):
        super(TestWorkeEntryHolidaysWorkEntry, cls).setUpClass()
        cls.tz = pytz.timezone(cls.richard_emp.tz)
        cls.start = datetime(2015, 11, 1, 1, 0, 0)
        cls.end = datetime(2015, 11, 30, 23, 59, 59)
        cls.resource_calendar_id = cls.env['resource.calendar'].create({'name': 'Zboub'})
        cls.richard_emp.create_version({
            'date_version': cls.start.date() - relativedelta(days=5),
            'contract_date_start': cls.start.date() - relativedelta(days=5),
            'contract_date_end': Date.to_date('2017-12-31'),
            'name': 'dodo',
            'resource_calendar_id': cls.resource_calendar_id.id,
            'wage': 1000,
            'date_generated_from': cls.end.date() + relativedelta(days=5),
        })
        cls.calendar_leave_type = cls.env['hr.leave.type'].create({
            'name': 'Calendar Type Time Off',
            'requires_allocation': False,
            'count_days_as': 'calendar',
            'work_entry_type_id': cls.work_entry_type_leave.id,
        })
        cls.public_leave_work_entry_type = cls.env['hr.work.entry.type'].create({
            'name': 'Public Leave Work Entry',
            'is_leave': True,
            'code': 'PUBLICLEAVE100',
        })

        cls.work_entry_type_remote = cls.env['hr.work.entry.type'].create({
            'name': 'Remote Work',
            'is_leave': True,
            'code': 'WORKTEST100',
        })

        cls.leave_remote_type = cls.env['hr.leave.type'].create({
            'name': 'Legal Leaves',
            'time_type': 'other',
            'requires_allocation': False,
            'allow_request_on_top': True,
            'work_entry_type_id': cls.work_entry_type_remote.id,
        })

    def assert_work_entry_type(self, work_entry_create_vals, work_entry_type, expected_count=None):
        """
        Assert that all work entries have the given work_entry_type.
        Optionally checks for an expected count of such entries.
        """
        actual_count = sum(work_entry['work_entry_type_id'] == work_entry_type.id
                        for work_entry in work_entry_create_vals)

        if expected_count is None:
            self.assertEqual(
                actual_count, len(work_entry_create_vals),
                f"All work entries should be of type {work_entry_type.name}."
            )
        else:
            self.assertEqual(
                actual_count, expected_count,
                f"Expected {expected_count} work entries of type {work_entry_type.name}, "
                f"but got {actual_count}."
            )

    def test_time_week_leave_work_entry(self):
        # /!\ this is a week day => it exists an calendar attendance at this time
        self.leave_type.request_unit = 'hour'
        leave = self.env['hr.leave'].create({
            'name': '1leave',
            'employee_id': self.richard_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': date(2015, 11, 2),
            'request_date_to': date(2015, 11, 2),
            'request_hour_from': 11,
            'request_hour_to': 17,
        })
        leave.action_approve()

        work_entries = self.richard_emp.generate_work_entries(self.start.date(), self.end.date())
        work_entries.action_validate()
        leave_work_entry = work_entries.filtered(lambda we: we.work_entry_type_id in self.work_entry_type_leave)
        sum_hours = sum(leave_work_entry.mapped('duration'))

        self.assertEqual(sum_hours, 5.0, "It should equal the number of hours richard should have worked")

    def test_work_entries_generation_if_parent_leave_zero_hours(self):
        # Test case: The employee has a parental leave at 0 hours per week
        # The employee has a leave during that period

        calendar = self.env['resource.calendar'].create({
            'name': 'Parental 0h',
            'attendance_ids': False,
        })
        employee = self.env['hr.employee'].create({
            'name': 'My employee',
            'contract_date_start': self.start.date() - relativedelta(years=1),
            'contract_date_end': False,
            'resource_calendar_id': calendar.id,
            'wage': 1000,
        })

        leave_type = self.env['hr.leave.type'].create({
            'name': 'Sick',
            'request_unit': 'hour',
            'leave_validation_type': 'both',
            'requires_allocation': False,
        })

        leave = self.env['hr.leave'].create({
            'name': "Sick 1 that doesn't make sense, but it's the prod so YOLO",
            'employee_id': employee.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': date(2020, 9, 4),
            'request_date_to': date(2020, 9, 4),
        })

        # TODO I don't know what this test is supposed to test, but I feel that
        # in any case it should raise a Validation Error, as it's trying to
        # validate a leave in a period the employee is not supposed to work.
        with self.assertRaises(ValidationError):
            leave.action_approve()

        work_entries = employee.version_id.generate_work_entries(date(2020, 7, 1), date(2020, 9, 30))

        self.assertEqual(len(work_entries), 0)

    def test_work_entries_leave_if_leave_conflict_with_public_holiday(self):
        date_from = datetime(2023, 2, 1, 0, 0, 0)
        date_to = datetime(2023, 2, 28, 23, 59, 59)
        work_entry_type_holiday = self.env['hr.work.entry.type'].create({
            'name': 'Public Holiday',
            'is_leave': True,
            'code': 'LEAVETEST500'
        })
        self.env['resource.calendar.leaves'].create({
            'name': 'Public Holiday',
            'date_from': datetime(2023, 2, 6, 0, 0, 0),
            'date_to': datetime(2023, 2, 7, 23, 59, 59),
            'calendar_id': self.richard_emp.resource_calendar_id.id,
            'work_entry_type_id': work_entry_type_holiday.id,
        })
        leave = self.env['hr.leave'].create({
            'name': 'AL',
            'employee_id': self.richard_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': date(2023, 2, 3),
            'request_date_to': date(2023, 2, 9),
        })
        leave.action_approve()

        self.richard_emp.generate_work_entries(date_from, date_to, True)
        work_entries = self.env['hr.work.entry'].search([
            ('employee_id', '=', self.richard_emp.id),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('state', '!=', 'validated')])
        leave_work_entry = work_entries.filtered(lambda we: we.work_entry_type_id in self.work_entry_type_leave)
        self.assertEqual(leave_work_entry.leave_id.id, leave.id, "Leave work entry should have leave_id value")

        public_holiday_work_entry = work_entries.filtered(lambda we: we.work_entry_type_id == work_entry_type_holiday)
        self.assertEqual(len(public_holiday_work_entry.leave_id), 0, "Public holiday work entry should not have leave_id")

    def test_work_entries_overlap_work_leaves(self):
        remote = self.env['hr.leave'].create({
            'name': 'remote1',
            'employee_id': self.richard_emp.id,
            'holiday_status_id': self.leave_remote_type.id,
            'request_date_from': date(2015, 11, 2),  # Monday
            'request_date_to': date(2015, 11, 6),
        })
        remote.action_approve()

        self.leave_type.request_unit = 'hour'
        leave = self.env['hr.leave'].create({
            'name': '1leave',
            'employee_id': self.richard_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': date(2015, 11, 3),
            'request_date_to': date(2015, 11, 3),
            'request_hour_from': 11,
            'request_hour_to': 17,
        })
        leave.action_approve()

        work_entries = self.richard_emp.generate_work_entries(self.start.date(), self.end.date())
        remote_work_entry = work_entries.filtered(lambda we: we.work_entry_type_id in self.work_entry_type_remote)
        leave_work_entry = work_entries.filtered(lambda we: we.work_entry_type_id in self.work_entry_type_leave)
        self.assertEqual(len(remote_work_entry), 5, "There should be five remote work entries")
        self.assertEqual(len(leave_work_entry), 1, "There should be one leave work entry")
        sum_remote_hours = sum(remote_work_entry.mapped('duration'))
        sum_leave_hours = sum(leave_work_entry.mapped('duration'))
        self.assertEqual(sum_remote_hours, 35, "It should equal the number of hours richard worked in remote")  # 5 days * 8 hours - 5 hours for leave
        self.assertEqual(sum_leave_hours, 5.0, "It should equal the number of hours richard was on leave")

    def test_work_entries_with_calendar_duration_type_leave(self):
        """
        Test Case:
        Verify that when an employee takes a leave of type 'calendar duration',
        work entries are generated for both working and non-working days.

        Expected Behavior:
        - Leave duration: 2nd Oct to 5th Oct (4 days).
        - Since it's calendar-based, entries should include:
            * 4 entries for working days.
            * 2 entries for non-working days (weekend).
        - Total = 6 work entries, all of type 'leave'.
        """
        leave = self.env['hr.leave'].create({
            'name': 'Calendar type leave',
            'employee_id': self.richard_emp.id,
            'holiday_status_id': self.calendar_leave_type.id,
            'request_date_from': date(2015, 10, 2),
            'request_date_to': date(2015, 10, 5),
        })

        leave.action_approve()
        work_entry_create_vals = self.richard_emp.version_id._get_version_work_entries_values(
            datetime(2015, 10, 2),
            datetime(2015, 10, 5, 23, 59, 59),
        )
        self.assertEqual(len(work_entry_create_vals), 6, 'Should have generated 6 work entries.')
        self.assert_work_entry_type(work_entry_create_vals, self.work_entry_type_leave)

    def test_work_entries_with_working_duration_type_leave(self):
        """
        Test Case:
        Verify that when an employee takes a leave of type 'working duration',
        work entries are only created for actual working days, excluding weekends.

        Expected Behavior:
        - Leave duration: 2nd Oct to 5th Oct (4 days).
        - Since it's working-days only:
            * 4 entries should be generated (working days only).
        - Total = 4 work entries, all of type 'leave'.
        """
        self.calendar_leave_type.count_days_as = 'working'
        leave = self.env['hr.leave'].create({
            'name': 'Working type leave',
            'employee_id': self.richard_emp.id,
            'holiday_status_id': self.calendar_leave_type.id,
            'request_date_from': date(2015, 10, 2),
            'request_date_to': date(2015, 10, 5),
        })

        leave.action_approve()
        work_entry_create_vals = self.richard_emp.version_id._get_version_work_entries_values(
            datetime(2015, 10, 2),
            datetime(2015, 10, 5, 23, 59, 59),
        )
        self.assertEqual(len(work_entry_create_vals), 4, 'Should have generated 4 work entries.')
        self.assert_work_entry_type(work_entry_create_vals, self.work_entry_type_leave)

    def test_work_entry_with_calendar_type_leave_excludes_public_holidays(self):
        """
        Test Case:
        Verify that when calendar-type leave excludes public holidays
        (`include_public_holidays_in_duration=False`), the public holiday is
        skipped in duration calculation but still generates public holiday
        work entries.

        Scenario:
        - Leave requested: 13th Oct to 15th Oct (3 calendar days).
        - 14th Oct is a public holiday.
        - Expected Behavior:
            * Work entries should still generate for 13th, 14th, and 15th.
            * On the public holiday (14th), entries should be created with the
            `public_leave_work_entry_type`.
            * Total = 6 work entries (4 for 13th & 15th, 2 for 14th public holiday).
        """
        self.env['resource.calendar.leaves'].create({
            'name': 'Public Holiday',
            'date_from': datetime(2015, 10, 14, 0, 0, 0),
            'date_to': datetime(2015, 10, 14, 23, 59, 59),
            'work_entry_type_id': self.public_leave_work_entry_type.id,
        })

        leave = self.env['hr.leave'].create({
            'name': 'Calendar type leave (exclude PH)',
            'employee_id': self.richard_emp.id,
            'holiday_status_id': self.calendar_leave_type.id,
            'request_date_from': date(2015, 10, 13),
            'request_date_to': date(2015, 10, 15),
        })

        leave.action_approve()
        self.assertEqual(leave.number_of_days, 2, 'Leave should be 2 days long (excluding PH).')

        work_entry_create_vals = self.richard_emp.version_id._get_version_work_entries_values(
            datetime(2015, 10, 13),
            datetime(2015, 10, 15, 23, 59, 59),
        )

        self.assertEqual(len(work_entry_create_vals), 6, 'Should have generated 4 work entries.')
        self.assert_work_entry_type(work_entry_create_vals, self.public_leave_work_entry_type, 2)
        self.assert_work_entry_type(work_entry_create_vals, self.work_entry_type_leave, 4)

    def test_work_entry_with_calendar_type_leave_includes_public_holidays(self):
        """
        Test Case:
        Verify that when calendar-type leave includes public holidays
        (`include_public_holidays_in_duration=True`), the holiday is included
        in duration calculation and work entries.

        Scenario:
        - Leave requested: 13th Oct to 15th Oct (3 calendar days).
        - 14th Oct is a public holiday.
        - Expected Behavior:
            * Leave duration should be counted as 3 days (13th, 14th, 15th).
            * Work entries should generate:
                - 4 entries for working days (13th, 15th).
                - 2 entries for public holiday (14th), marked with PH type.
            * Total = 6 work entries.
        """

        self.env['resource.calendar.leaves'].create({
            'name': 'Public Holiday',
            'date_from': datetime(2015, 10, 14, 0, 0, 0),
            'date_to': datetime(2015, 10, 14, 23, 59, 59),
            'work_entry_type_id': self.public_leave_work_entry_type.id,
        })

        self.calendar_leave_type.include_public_holidays_in_duration = True
        leave = self.env['hr.leave'].create({
            'name': 'Calendar type leave (include PH)',
            'employee_id': self.richard_emp.id,
            'holiday_status_id': self.calendar_leave_type.id,
            'request_date_from': date(2015, 10, 13),
            'request_date_to': date(2015, 10, 15),
        })

        leave.action_approve()
        self.assertEqual(leave.number_of_days, 3, 'Leave should be 3 days long (including PH).')

        work_entry_create_vals = self.richard_emp.version_id._get_version_work_entries_values(
            datetime(2015, 10, 13),
            datetime(2015, 10, 15, 23, 59, 59),
        )

        self.assertEqual(len(work_entry_create_vals), 6, 'Should have generated 6 work entries.')
        self.assert_work_entry_type(work_entry_create_vals, self.public_leave_work_entry_type, 0)
        self.assert_work_entry_type(work_entry_create_vals, self.work_entry_type_leave, 6)

    def test_leave_work_entry_with_ph_and_weekend_included(self):
        """
        Test Case:
        Verify behavior when calendar-type leave includes public holidays
        (`include_public_holidays_in_duration=True`).

        Scenario:
        - Leave requested: 1st Oct to 5th Oct (5 calendar days).
        - 2nd Oct is a public holiday.
        - 3rd and 4th Oct are weekends (non-working).
        - Expected:
            * Leave duration should count as 5 days.
            * Work entries:
                - 4 for working days (1st, 5th).
                - 2 for weekend (3rd, 4th).
                - 2 for public holiday (2nd).
            * Total = 8 work entries.
        """
        self.env['resource.calendar.leaves'].create({
            'name': 'Public Holiday',
            'date_from': datetime(2015, 10, 2, 0, 0, 0),
            'date_to': datetime(2015, 10, 2, 23, 59, 59),
            'work_entry_type_id': self.public_leave_work_entry_type.id,
        })

        self.calendar_leave_type.include_public_holidays_in_duration = True
        leave = self.env['hr.leave'].create({
            'name': 'Calendar type leave (include PH)',
            'employee_id': self.richard_emp.id,
            'holiday_status_id': self.calendar_leave_type.id,
            'request_date_from': date(2015, 10, 1),
            'request_date_to': date(2015, 10, 5),
        })

        leave.action_approve()
        self.assertEqual(leave.number_of_days, 5, 'Leave should count full 5 days (including PH).')

        work_entry_create_vals = self.richard_emp.version_id._get_version_work_entries_values(
            datetime(2015, 10, 1),
            datetime(2015, 10, 5, 23, 59, 59),
        )
        self.assertEqual(len(work_entry_create_vals), 8, 'Should have generated 8 work entries.')
        self.assert_work_entry_type(work_entry_create_vals, self.public_leave_work_entry_type, 0)
        self.assert_work_entry_type(work_entry_create_vals, self.work_entry_type_leave, 8)

    def test_leave_work_entry_with_exclude_ph_and_include_weekend(self):
        """
        Test Case:
        Verify behavior when calendar-type leave excludes public holidays
        (`include_public_holidays_in_duration=False`).

        Scenario:
        - Leave requested: 1st Oct to 5th Oct (5 calendar days).
        - 2nd Oct is a public holiday.
        - 3rd and 4th Oct are weekends (non-working).
        - Expected:
            * Leave duration should count as 4 days (excluding the public holiday).
            * Work entries:
                - 4 for working days (1st, 5th).
                - 2 for weekend (3rd, 4th).
                - 2 for public holiday (2nd), but **not linked to leave**.
            * Total = 8 work entries.
        """
        self.env['resource.calendar.leaves'].create({
            'name': 'Public Holiday',
            'date_from': datetime(2015, 10, 2, 0, 0, 0),
            'date_to': datetime(2015, 10, 2, 23, 59, 59),
            'work_entry_type_id': self.public_leave_work_entry_type.id,
        })

        leave = self.env['hr.leave'].create({
            'name': 'Calendar type leave (exclude PH)',
            'employee_id': self.richard_emp.id,
            'holiday_status_id': self.calendar_leave_type.id,
            'request_date_from': date(2015, 10, 1),
            'request_date_to': date(2015, 10, 5),
        })

        leave.action_approve()
        self.assertEqual(leave.number_of_days, 4, 'Leave should exclude the PH and count 4 days only.')

        work_entry_create_vals = self.richard_emp.version_id._get_version_work_entries_values(
            datetime(2015, 10, 1),
            datetime(2015, 10, 5, 23, 59, 59),
        )
        self.assertEqual(len(work_entry_create_vals), 8, 'Should have generated 8 work entries.')
        self.assert_work_entry_type(work_entry_create_vals, self.public_leave_work_entry_type, 2)
        self.assert_work_entry_type(work_entry_create_vals, self.work_entry_type_leave, 6)
