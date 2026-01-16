# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime

from odoo.tests import tagged, TransactionCase


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSandwichLeaveWorkEntry(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        country_in = cls.env.ref('base.in')
        cls.env.user.tz = 'Asia/Kolkata'
        cls.Leave = cls.env['hr.leave']
        cls.company_in = cls.env['res.company'].create({
            'name': 'Indian Company',
            'country_id': country_in.id,
        })
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=cls.company_in.ids))
        cls.in_resource_calendar_id = cls.env['resource.calendar'].create({
            'name': 'Classic 40h/week',
            'hours_per_day': 8.0,
            'company_id': cls.company_in.id,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thrusday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thrusday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
            ],
        })
        cls.kohli_emp = cls.env['hr.employee'].create({
            'name': 'Virat Kohli',
            'country_id': cls.env.ref('base.in').id,
            'company_id': cls.company_in.id,
            'contract_date_start': date(2024, 12, 1),
            'wage': 100000,
            'resource_calendar_id': cls.in_resource_calendar_id.id,
        })
        cls.kohli_version = cls.kohli_emp.version_id
        cls.work_entry_type_leave, cls.work_entry_type_public_leave, cls.work_entry_type_leave_1 = cls.env['hr.work.entry.type'].create([{
            'name': 'Time Off Work Eentry',
            'category': 'absence',
            'code': 'LEAVETEST200',
        }, {
            'name': 'Public Leave Work Entry',
            'category': 'absence',
            'code': 'PUBLICTEST100',
        }, {
            'name': 'Leave Work Entry',
            'category': 'absence',
            'code': 'LEAVETEST300',
        }])
        cls.leave_type_test, cls.leave_type_test_1 = cls.env['hr.leave.type'].create([{
            'name': 'Test Leave Type',
            'request_unit': 'day',
            'l10n_in_is_sandwich_leave': True,
            'requires_allocation': False,
            'work_entry_type_id': cls.work_entry_type_leave.id,
        }, {
            'name': 'Test Leave Type 1',
            'request_unit': 'half_day',
            'l10n_in_is_sandwich_leave': True,
            'requires_allocation': False,
            'work_entry_type_id': cls.work_entry_type_leave_1.id,
        }])

    def get_work_entry_type_count(self, work_entry_create_vals, work_entry_type):
        return len(work_entry_create_vals.filtered(lambda we: we.work_entry_type_id == work_entry_type))

    def check_work_entry_type_for_work_entry(self, work_entry_create_vals, work_entry_type):
        self.assertTrue(all(work_entry.work_entry_type_id == work_entry_type for work_entry in work_entry_create_vals),
                        'work entry type of work entry and leave should be same')

    def _generate_and_search_work_entries(self, date_from, date_to):
        """Generate work entries then fetch them in the date range for the employee."""
        self.kohli_version.generate_work_entries(date_from.date(), date_to.date(), force=True)
        return self.env['hr.work.entry'].search([
            ('employee_id', '=', self.kohli_emp.id),
            ('date', '>=', date_from.date()),
            ('date', '<=', date_to.date()),
        ], order='date asc')

    def test_sandwich_leave_work_entry(self):
        """
        In this test case, we are verifying that if a leave is created between non-working days, it should be marked as
        sandwich leave, and work entries for those non-working days should be created.
            -- Working days: 27th (Friday) and 30th December (Monday)
            -- Non-working days: 28th and 29th December (Weekends)
        """
        sandwich_leave = self.Leave.create({
            'name': 'Test Leave',
            'employee_id': self.kohli_emp.id,
            'holiday_status_id': self.leave_type_test.id,
            'request_date_from': "2024-12-27",
            'request_date_to': "2024-12-30",
        })
        sandwich_leave.action_approve()
        self.assertEqual(sandwich_leave.number_of_days, 4, 'Created leave should be 4 days long')
        self.assertTrue(sandwich_leave.l10n_in_contains_sandwich_leaves)
        work_entries = self._generate_and_search_work_entries(
            datetime(2024, 12, 27),
            datetime(2024, 12, 30),
        )
        self.assertEqual(len(work_entries), 4, 'Should have generated 4 work entries.')
        self.check_work_entry_type_for_work_entry(work_entries, self.work_entry_type_leave)

    def test_separate_sandwich_leave_work_entry(self):
        """
        This test case verifies that if an employee has already validated leave on a working day and then creates another leave
        on the following working day, which includes non-working days in between, the new leave should be considered as part of
        the sandwich leave. Consequently, work entries should be generated for the non-working days.
            -- Working days: 6th (Friday) and 9th December (Monday)
            -- Non-working days: 7th and 8th December (Weekends)
        """
        before_holiday_leave = self.Leave.create({
            'name': 'Test Leave 1',
            'employee_id': self.kohli_emp.id,
            'holiday_status_id': self.leave_type_test.id,
            'request_date_from': "2024-12-06",
            'request_date_to': "2024-12-06",
        })
        before_holiday_leave._action_validate()
        self.assertEqual(before_holiday_leave.number_of_days, 1, 'Created leave should be 1 day long')

        after_holiday_leave = self.Leave.create({
            'name': 'Test Leave 2',
            'employee_id': self.kohli_emp.id,
            'holiday_status_id': self.leave_type_test.id,
            'request_date_from': "2024-12-09",
            'request_date_to': "2024-12-09",
        })

        after_holiday_leave._action_validate()
        self.assertTrue(after_holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(after_holiday_leave.number_of_days, 3, 'Created leave should be 3 days long')
        work_entries = self._generate_and_search_work_entries(
            datetime(2024, 12, 6),
            datetime(2024, 12, 9),
        )
        self.assertEqual(len(work_entries), 4, 'Should have generated 4 work entries.')
        self.check_work_entry_type_for_work_entry(work_entries, self.work_entry_type_leave)

    def test_reverse_separate_sandwich_leave_work_entry(self):
        """
        This test case verifies that if an employee has already validated leave on a working day and then creates another leave
        on the past working day, which includes non-working days in between, the new leave should be considered as part of
        the sandwich leave. Consequently, work entries should be generated for the non-working days.
            -- Working days: 13th(Friday) and 16th December (Monday)
            -- Non-working days: 14th and 15th December (Weekends)
        """
        before_holiday_leave = self.Leave.create({
            'name': 'Test Leave 1',
            'employee_id': self.kohli_emp.id,
            'holiday_status_id': self.leave_type_test.id,
            'request_date_from': "2024-12-16",
            'request_date_to': "2024-12-16",
        })
        before_holiday_leave._action_validate()
        self.assertEqual(before_holiday_leave.number_of_days, 1, 'Created leave should be 1 day long')

        after_holiday_leave = self.Leave.create({
            'name': 'Test Leave 2',
            'employee_id': self.kohli_emp.id,
            'holiday_status_id': self.leave_type_test.id,
            'request_date_from': "2024-12-13",
            'request_date_to': "2024-12-14",
        })
        after_holiday_leave._action_validate()
        self.assertEqual(after_holiday_leave.number_of_days, 3, 'Created leave should be 3 days long')
        self.assertTrue(after_holiday_leave.l10n_in_contains_sandwich_leaves)
        work_entries = self._generate_and_search_work_entries(
            datetime(2024, 12, 13),
            datetime(2024, 12, 16),
        )
        self.assertEqual(len(work_entries), 4, 'Should have generated 4 work entries.')
        self.check_work_entry_type_for_work_entry(work_entries, self.work_entry_type_leave)

    def test_sandwich_contain_public_holiday_and_non_working_days(self):
        """
        This test case verifies that if a leave is created between a public holiday, it should be
        marked as a sandwich leave. The public holiday should be included as part of the leave, and work entries should
        be created accordingly.
            -- Working Days: 26th(Thursday) and 30th December (Monday)
            -- Non-working Days: 28th and 29th December (Weekends)
            -- Public Holiday: 27th December (Friday)
        """
        self.env['resource.calendar.leaves'].create({
            'name': 'Public Holiday',
            'date_from': datetime(2024, 12, 27),
            'date_to': datetime(2024, 12, 27),
            'calendar_id': self.in_resource_calendar_id.id,
            'company_id': self.company_in.id,
            'work_entry_type_id': self.work_entry_type_public_leave.id,
        })

        sandwich_leave = self.Leave.create({
            'name': 'Test Leave',
            'employee_id': self.kohli_emp.id,
            'holiday_status_id': self.leave_type_test.id,
            'request_date_from': "2024-12-26",
            'request_date_to': "2024-12-30",
        })
        sandwich_leave._action_validate()
        self.assertEqual(sandwich_leave.number_of_days, 5, 'Created leave should be 5 days long')
        self.assertTrue(sandwich_leave.l10n_in_contains_sandwich_leaves)
        # here search should be from 26th to 30th december because work entries are created for non-working days(28th,29th) and public holiday(27th)
        work_entries = self._generate_and_search_work_entries(
            datetime(2024, 12, 26),
            datetime(2024, 12, 30),
        )
        self.assertEqual(len(work_entries), 5, 'Should have generated 5 work entries.')
        self.check_work_entry_type_for_work_entry(work_entries, self.work_entry_type_leave)

    def test_sandwich_leave_around_public_holiday(self):
        """
        This test case verifies that if separate leaves are created around a public holiday, the leaves are marked as
        sandwich leaves, and the work entry type of the public holiday is set as the leave's work entry type.
            -- Working Days: 19th(Thursday) and 23th December (Monday)
            -- Non-working Days: 21th and 22th December (Weekends)
            -- Public Holiday: 20th December (Friday)
        """
        self.env['resource.calendar.leaves'].create({
            'name': 'Public Holiday',
            'date_from': datetime(2024, 12, 20),
            'date_to': datetime(2024, 12, 20),
            'calendar_id': self.in_resource_calendar_id.id,
            'company_id': self.company_in.id,
            'work_entry_type_id': self.work_entry_type_public_leave.id,
        })

        before_holiday_leave = self.Leave.create({
            'name': 'Test Leave',
            'employee_id': self.kohli_emp.id,
            'holiday_status_id': self.leave_type_test.id,
            'request_date_from': "2024-12-19",
            'request_date_to': "2024-12-19",
        })
        before_holiday_leave._action_validate()
        self.assertFalse(before_holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(before_holiday_leave.number_of_days, 1, 'Created leave should be 1 day long')

        after_holiday_leave = self.Leave.create({
            'name': 'Test Leave 1',
            'employee_id': self.kohli_emp.id,
            'holiday_status_id': self.leave_type_test.id,
            'request_date_from': "2024-12-23",
            'request_date_to': "2024-12-23",
        })
        after_holiday_leave._action_validate()
        self.assertEqual(after_holiday_leave.number_of_days, 4, 'Created leave should be 4 days long')
        self.assertTrue(after_holiday_leave.l10n_in_contains_sandwich_leaves)
        work_entries = self._generate_and_search_work_entries(
            datetime(2024, 12, 19),
            datetime(2024, 12, 23),
        )
        self.assertEqual(len(work_entries), 5, 'Should have generated 5 work entries.')
        self.check_work_entry_type_for_work_entry(work_entries, self.work_entry_type_leave)

    def test_long_sandwich_leave_covering_multiple_week(self):
        """
        This test verifies that if a sandwich leave starts and ends with non-working days and includes both working and
        non-working days in between, work entries should be created only for the non-working days.
            -- Working Days: 23rd(Friday) to 30th December (Monday), 30th(Monday) to 3rd January (Friday)
            -- Non-working Days: 28th and 29th December (Weekends)
        """
        sandwich_leave = self.Leave.create([{
            'name': 'Test Leave',
            'employee_id': self.kohli_emp.id,
            'holiday_status_id': self.leave_type_test.id,
            'request_date_from': "2024-12-21",
            'request_date_to': "2025-01-04",
        }])
        sandwich_leave._action_validate()
        self.assertEqual(sandwich_leave.number_of_days, 12, 'Created leave should be 12 days long')
        work_entries = self._generate_and_search_work_entries(
            datetime(2024, 12, 21),
            datetime(2025, 1, 4),
        )
        self.assertEqual(len(work_entries), 12, 'Should have generated 12 work entries.')
        self.check_work_entry_type_for_work_entry(work_entries, self.work_entry_type_leave)

    def test_sandwich_in_two_weeks_in_two(self):
        """
            This test case verifies that if a leave is created for multiple weeks, it should be marked as a sandwich leave,
            and work entries should be created for the non-working days.
            -- Working Days: 3th(Friday), 6th(Monday)-10th(friday) , 13th(Monday)-17th(friday), 20th(Monday) January
            -- Non-working Days: 4th-5th, 10th-11th, 18th-19th January (Weekends)
        """
        holiday_leave = self.Leave.create({
            'name': 'Test Leave',
            'employee_id': self.kohli_emp.id,
            'holiday_status_id': self.leave_type_test.id,
            'request_date_from': "2025-01-03",
            'request_date_to': "2025-01-20",
        })
        holiday_leave._action_validate()
        self.assertTrue(holiday_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(holiday_leave.number_of_days, 18)
        work_entries = self._generate_and_search_work_entries(
            datetime(2025, 1, 3),
            datetime(2025, 1, 20),
        )
        self.assertEqual(len(work_entries), 18, 'Should have generated 18 work entries.')
        self.check_work_entry_type_for_work_entry(work_entries, self.work_entry_type_leave)

    def test_edge_sandwich_public_leave_work_entry(self):
        """
            This test case verifies that if a sandwich leave is created with a public holiday at the edge, it should be
            not counted as part of the sandwich leave.
            -- Public Holiday: 12 February (Wednesday)
            -- Working Days: 7th(Friday), 10th(Monday), 11th(Tuesday) February
            -- Non-working Days: 8th, 9th February (Weekends)
        """
        self.env['resource.calendar.leaves'].create({
            'name': 'Public Holiday',
            'date_from': datetime(2025, 2, 12),
            'date_to': datetime(2025, 2, 12),
            'calendar_id': self.in_resource_calendar_id.id,
            'company_id': self.company_in.id,
            'work_entry_type_id': self.work_entry_type_public_leave.id,
        })
        sandwich_leave = self.Leave.create([{
            'name': 'Test Leave',
            'employee_id': self.kohli_emp.id,
            'holiday_status_id': self.leave_type_test.id,
            'request_date_from': "2025-02-07",
            'request_date_to': "2025-02-12",
        }])
        sandwich_leave._action_validate()
        self.assertEqual(sandwich_leave.number_of_days, 5, 'Created leave should be 5 days long')
        work_entries = self._generate_and_search_work_entries(
            datetime(2025, 2, 7),
            datetime(2025, 2, 12),
        )
        # - 1 work entry per day (working, non-working, and public holiday)
        self.assertEqual(len(work_entries), 6, 'Should have generated 6 work entries.')
        self.check_work_entry_type_for_work_entry(work_entries, self.work_entry_type_leave)

    def test_sandwich_leave_with_public_holiday_at_edge(self):
        """
            this test case verifies that if we have sandwich leave and public holiday at the edge of the sandwich leave,
            then public holiday should not be counted as part of the sandwich leave.
            -- Public Holiday: 12 February (Wednesday)
            -- Working Days: 7th(Friday), 10th(Monday), 11th(Tuesday) February
            -- Non-working Days: 8th, 9th February (Weekends)
        """
        self.env['resource.calendar.leaves'].create({
            'name': 'Public Holiday',
            'date_from': datetime(2025, 2, 12),
            'date_to': datetime(2025, 2, 12),
            'calendar_id': self.in_resource_calendar_id.id,
            'company_id': self.company_in.id,
            'work_entry_type_id': self.work_entry_type_public_leave.id,
        })
        before_leave = self.Leave.create([{
            'name': 'Test Leave first',
            'employee_id': self.kohli_emp.id,
            'holiday_status_id': self.leave_type_test.id,
            'request_date_from': "2025-02-07",
            'request_date_to': "2025-02-12",
        }])
        before_leave._action_validate()
        self.assertEqual(before_leave.number_of_days, 5, 'Created leave should be 5 days long')
        after_leave = self.Leave.create([{
            'name': 'Test Leave after',
            'employee_id': self.kohli_emp.id,
            'holiday_status_id': self.leave_type_test.id,
            'request_date_from': "2025-02-13",
            'request_date_to': "2025-02-13",
        }])
        after_leave._action_validate()
        self.assertEqual(after_leave.number_of_days, 2, 'Created leave should be 2 days long')
        work_entries = self._generate_and_search_work_entries(
            datetime(2025, 2, 7),
            datetime(2025, 2, 13),
        )
        # - 1 entry for public holiday (12th February)
        # - 1 entry for working day (7-11, 13th February)
        self.assertEqual(len(work_entries), 7, 'Should have generated 7 work entries.')
        self.check_work_entry_type_for_work_entry(work_entries, self.work_entry_type_leave)

    def test_sandwich_leave_with_different_leave_type(self):
        """
        This test case verifies that if a sandwich leave is created with a different leave type, it should still be
        considered as a sandwich leave, and work entries should be created accordingly.
        Also checks the leave days after refusing the before sandwich leave.
            -- Working Days: 4th(Friday) and 7th July (Monday)
            -- Non-working Days: 5th and 6th July (weekends)
        """
        before_sandwich_leave = self.Leave.create({
            'name': 'Test Leave',
            'employee_id': self.kohli_emp.id,
            'holiday_status_id': self.leave_type_test.id,
            'request_date_from': "2025-07-04",
            'request_date_to': "2025-07-04",
        })
        before_sandwich_leave._action_validate()
        self.assertEqual(before_sandwich_leave.number_of_days, 1, 'Created leave should be 1 days long')

        after_sandwich_leave = self.Leave.create({
            'name': 'Test Leave 1',
            'employee_id': self.kohli_emp.id,
            'holiday_status_id': self.leave_type_test_1.id,
            'request_date_from': "2025-07-07",
            'request_date_to': "2025-07-07",
        })
        after_sandwich_leave._action_validate()
        self.assertTrue(after_sandwich_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(after_sandwich_leave.number_of_days, 3, 'Created leave should be 3 days long')
        work_entries = self._generate_and_search_work_entries(
            datetime(2025, 7, 4),
            datetime(2025, 7, 7),
        )
        # - 2 entries for working day(7th July)
        # - 2 entries for non-working days
        self.assertEqual(len(work_entries), 4, 'Should have generated 4 work entries.')
        # Newly created work entries should have the work entry type of the after leave
        self.check_work_entry_type_for_work_entry(work_entries[0], self.work_entry_type_leave)
        self.check_work_entry_type_for_work_entry(work_entries[1:], self.work_entry_type_leave_1)
        before_sandwich_leave.action_refuse()
        self.assertEqual(after_sandwich_leave.number_of_days, 1, 'After refusing before sandwich leave, after sandwich leave should be 1 day long')
        self.assertFalse(after_sandwich_leave.l10n_in_contains_sandwich_leaves)

    def test_multi_sandwich_leave_with_edge_public_holiday(self):
        self.env['resource.calendar.leaves'].create([{
            'name': 'Public Holiday',
            'date_from': datetime(2025, 7, 4, 00, 00, 00),
            'date_to': datetime(2025, 7, 4, 23, 59, 59),
            'calendar_id': self.in_resource_calendar_id.id,
            'company_id': self.company_in.id,
            'work_entry_type_id': self.work_entry_type_public_leave.id,
        }, {
            'name': 'Public Holiday',
            'date_from': datetime(2025, 7, 14, 00, 00, 00),
            'date_to': datetime(2025, 7, 14, 23, 59, 59),
            'calendar_id': self.in_resource_calendar_id.id,
            'company_id': self.company_in.id,
            'work_entry_type_id': self.work_entry_type_public_leave.id,
        }])

        before_leave = self.Leave.create({
            'name': 'Test Leave Before',
            'employee_id': self.kohli_emp.id,
            'holiday_status_id': self.leave_type_test.id,
            'request_date_from': "2025-07-04",
            'request_date_to': "2025-07-11",
        })
        self.assertEqual(before_leave.number_of_days, 5, 'Created leave should be 5 days long')
        after_leave = self.Leave.create({
            'name': 'Test Leave After',
            'employee_id': self.kohli_emp.id,
            'holiday_status_id': self.leave_type_test.id,
            'request_date_from': "2025-07-14",
            'request_date_to': "2025-07-18",
        })
        self.assertTrue(after_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(after_leave.number_of_days, 7, 'Created leave should be 7 days long')
        (before_leave + after_leave)._action_validate()
        work_entries = self._generate_and_search_work_entries(
            datetime(2025, 7, 4),
            datetime(2025, 7, 18),
        )
        # - 9 entries for working days (5th-18th July)
        # - 2 entries for non-working days (12th, 13th July)
        # - 2 entiries for public holiday(4th, 14th July)
        self.assertEqual(len(work_entries), 13, 'Should have generated 12 work entries.')
        self.check_work_entry_type_for_work_entry(work_entries[0], self.work_entry_type_public_leave)
        self.check_work_entry_type_for_work_entry(work_entries[1:], self.work_entry_type_leave)

    def test_bidirectional_sandwich_leave(self):
        """
            This test case verifies that if a sandwich leave is created with a before and after linked sandwich leave,
            it should adjust the dates accordingly and create work entries for the non-working days.
                -- public holiday: 9th July(wednesday)
                -- working days: 3th-4th(Thu-Fri) July, 7th-8th(Mon-Tue) July, 10th-11th(Thu-Fri) July
                -- non-working days: 5th-6th(Sat-Sun) July,
        """
        self.env['resource.calendar.leaves'].create({
            'name': 'Public Holiday',
            'date_from': datetime(2025, 7, 9),
            'date_to': datetime(2025, 7, 9),
            'calendar_id': self.in_resource_calendar_id.id,
            'company_id': self.company_in.id,
            'work_entry_type_id': self.work_entry_type_public_leave.id,
        })
        before_leave = self.Leave.create({
            'name': 'Test Leave Before',
            'employee_id': self.kohli_emp.id,
            'holiday_status_id': self.leave_type_test.id,
            'request_date_from': "2025-07-03",
            'request_date_to': "2025-07-04",
        })
        before_leave._action_validate()
        self.assertEqual(before_leave.number_of_days, 2, 'Created leave should be 2 days long')

        after_leave = self.Leave.create({
            'name': 'Test Leave After',
            'employee_id': self.kohli_emp.id,
            'holiday_status_id': self.leave_type_test.id,
            'request_date_from': "2025-07-10",
            'request_date_to': "2025-07-11",
        })
        after_leave._action_validate()
        self.assertEqual(after_leave.number_of_days, 2, 'Created leave should be 2 days long')

        middle_sandwich_leave = self.Leave.create({
            'name': 'Test Leave',
            'employee_id': self.kohli_emp.id,
            'holiday_status_id': self.leave_type_test.id,
            'request_date_from': "2025-07-07",
            'request_date_to': "2025-07-08",
        })
        middle_sandwich_leave._action_validate()
        self.assertTrue(middle_sandwich_leave.l10n_in_contains_sandwich_leaves)
        self.assertEqual(middle_sandwich_leave.number_of_days, 5, 'Created leave should be 5 days long')

        work_entries = self._generate_and_search_work_entries(
            datetime(2025, 7, 3),
            datetime(2025, 7, 11),
        )
        # - 1 entry per day including non-working days and the public holiday
        self.assertEqual(len(work_entries), 9, 'Should have generated 9 work entries.')
        self.check_work_entry_type_for_work_entry(work_entries, self.work_entry_type_leave)
