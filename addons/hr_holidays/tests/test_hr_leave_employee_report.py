# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime
from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tagged('post_install', '-at_install')
class TestHrLeaveEmployeeReport(TestHrHolidaysCommon):
    """Values of the "Time Off by Employee" report (hr.leave.employee.report): one row per leave and
    per day, with the duration of that day."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        WorkEntryType = cls.env['hr.work.entry.type']
        common = {
            'requires_allocation': False,
            'leave_validation_type': 'no_validation',
            'count_as': 'absence',
        }
        cls.day_type, cls.half_day_type, cls.hour_type, cls.calendar_day_type = WorkEntryType.create([{
            **common,
            'name': 'Report Day',
            'code': 'report_day',
            'request_unit': 'day',
        }, {
            **common,
            'name': 'Report Half Day',
            'code': 'report_half_day',
            'request_unit': 'half_day',
        }, {
            **common,
            'name': 'Report Hour',
            'code': 'report_hour',
            'request_unit': 'hour',
        }, {
            **common,
            'name': 'Report Calendar Days',
            'code': 'report_calendar_days',
            'request_unit': 'day',
            'count_days_as': 'calendar',
        }])
        cls.employee = cls.employee_emp  # Test company, Standard 40h/week (8-12, 13-17), Europe/Brussels

    def _create_leaves(self, vals_list, **ctx):
        return self.env['hr.leave'].with_context(tracking_disable=True, **ctx).create([{
            'employee_id': self.employee.id,
            'work_entry_type_id': self.day_type.id,
            **vals,
        } for vals in vals_list])

    def _report(self, domain=None, company=None):
        """Rows of the report as ``(day, number_of_days, number_of_hours)``, in date order."""
        self.env.cr.flush()
        rows = self.env['hr.leave.employee.report'].with_context(allowed_company_ids=[(company or self.company).id]).search_read(
            domain or [('employee_id', '=', self.employee.id)],
            ['working_schedule_aligned_date_from', 'number_of_days', 'number_of_hours'],
            order='working_schedule_aligned_date_from, leave_id',
        )
        return [
            (row['working_schedule_aligned_date_from'].date(), round(row['number_of_days'], 2), round(row['number_of_hours'], 2))
            for row in rows
        ]

    def test_leave_split_by_day_and_month(self):
        """A leave over three months gets one row per working day, none for the weekends, and the
        months add up to the duration of the leave."""
        leave = self._create_leaves([{'request_date_from': date(2024, 1, 29), 'request_date_to': date(2024, 3, 1)}])
        rows = self._report()
        self.assertEqual(len(rows), 25)
        self.assertTrue(all(day.weekday() < 5 for day, _days, _hours in rows), "No row on Saturdays and Sundays")
        self.assertTrue(all((days, hours) == (1, 8) for _day, days, hours in rows))
        self.assertEqual(leave.number_of_days, 25)

        groups = self.env['hr.leave.employee.report'].with_company(self.company).formatted_read_group(
            [('employee_id', '=', self.employee.id)],
            ['working_schedule_aligned_date_from:month'],
            ['number_of_days:sum'],
        )
        self.assertEqual([group['number_of_days:sum'] for group in groups], [3, 21, 1])  # Jan 29-31, February, Mar 1

    def test_half_days(self):
        """Monday afternoon to Wednesday morning."""
        self._create_leaves([{
            'work_entry_type_id': self.half_day_type.id,
            'request_date_from': date(2024, 4, 8),
            'request_date_from_period': 'pm',
            'request_date_to': date(2024, 4, 10),
            'request_date_to_period': 'am',
        }])
        self.assertEqual(self._report(), [
            (date(2024, 4, 8), 0.5, 4),
            (date(2024, 4, 9), 1, 8),
            (date(2024, 4, 10), 0.5, 4),
        ])

    def test_hours(self):
        self._create_leaves([{
            'work_entry_type_id': self.hour_type.id,
            'request_date_from': date(2024, 6, 3),
            'request_date_to': date(2024, 6, 3),
            'request_hour_from': 10,
            'request_hour_to': 12,
        }])
        # same values as the leave itself
        self.assertEqual(self._report(), [(date(2024, 6, 3), 0.5, 2)])

    def test_public_holiday_inside_leave(self):
        """The public holiday (Wednesday) gets no row."""
        self.env['resource.calendar.leaves'].create({
            'name': 'Public holiday',
            'company_id': self.company.id,
            'date_from': datetime(2024, 5, 7, 22, 0),
            'date_to': datetime(2024, 5, 8, 21, 59, 59),
        })
        leave = self._create_leaves([{'request_date_from': date(2024, 5, 6), 'request_date_to': date(2024, 5, 10)}])
        self.assertEqual(leave.number_of_days, 4)
        self.assertEqual(self._report(), [
            (date(2024, 5, 6), 1, 8),
            (date(2024, 5, 7), 1, 8),
            (date(2024, 5, 9), 1, 8),
            (date(2024, 5, 10), 1, 8),
        ])

    def test_calendar_days_type(self):
        """A type counted in calendar days, from Friday to Monday."""
        self._create_leaves([{
            'work_entry_type_id': self.calendar_day_type.id,
            'request_date_from': date(2024, 9, 6),
            'request_date_to': date(2024, 9, 9),
        }])
        self.assertEqual(self._report(), [
            (date(2024, 9, 6), 1, 8),
            (date(2024, 9, 7), 1, 8),
            (date(2024, 9, 8), 1, 8),
            (date(2024, 9, 9), 1, 8),
        ])

    def test_flexible_schedule(self):
        calendar = self.env['resource.calendar'].create({
            'name': 'Flexible 40h',
            'calendar_type': 'undefined',
            'attendance_ids': [],
            'hours_per_week': 40,
            'hours_per_day': 8.0,
            'company_id': self.company.id,
        })
        self.employee.resource_calendar_id = calendar
        leave = self._create_leaves([{'request_date_from': date(2024, 10, 7), 'request_date_to': date(2024, 10, 9)}])
        self.assertEqual((leave.number_of_days, leave.number_of_hours), (3, 24))
        # Only the days are checked: the hours of each row are the clock hours of the leave on that
        # day (18, 24, 14 here), not the hours of the schedule.
        self.assertEqual([(day, days) for day, days, _hours in self._report()], [
            (date(2024, 10, 7), 1),
            (date(2024, 10, 8), 1),
            (date(2024, 10, 9), 1),
        ])

    def test_overlapping_leaves_not_subtracted(self):
        """The report never subtracts the other leaves of the employee from a day: both overlapping
        leaves count the full Wednesday."""
        week, wednesday = self._create_leaves([
            {'request_date_from': date(2024, 11, 4), 'request_date_to': date(2024, 11, 8)},
            {'request_date_from': date(2024, 11, 6), 'request_date_to': date(2024, 11, 6)},
        ], leave_skip_date_check=True)
        wednesday_rows = self._report([
            ('employee_id', '=', self.employee.id),
            ('working_schedule_aligned_date_from', '>=', '2024-11-06'),
            ('working_schedule_aligned_date_from', '<', '2024-11-07'),
        ])
        self.assertEqual(wednesday_rows, [(date(2024, 11, 6), 1, 8), (date(2024, 11, 6), 1, 8)])
        self.assertEqual(len(self._report([('leave_id', '=', week.id)])), 5)
        self.assertEqual(len(self._report([('leave_id', '=', wednesday.id)])), 1)

    def test_states_and_filters(self):
        """Refused and cancelled leaves are shown with their state, and the filters on the state of
        the leave work."""
        validated, refused, cancelled = self._create_leaves([
            {'request_date_from': date(2024, 2, 5), 'request_date_to': date(2024, 2, 5)},
            {'request_date_from': date(2024, 2, 6), 'request_date_to': date(2024, 2, 6)},
            {'request_date_from': date(2024, 2, 7), 'request_date_to': date(2024, 2, 7)},
        ])
        refused.action_refuse()
        cancelled.with_context(leave_skip_state_check=True).sudo().state = 'cancel'

        self.env.cr.flush()
        Report = self.env['hr.leave.employee.report'].with_company(self.company)
        rows = Report.search([('employee_id', '=', self.employee.id)])
        self.assertEqual(
            {(row.leave_id, row.state) for row in rows},
            {(validated, 'validate'), (refused, 'refuse'), (cancelled, 'cancel')},
        )
        self.assertEqual(Report.search([('leave_id.state', '=', 'refuse')]).leave_id, refused)
        self.assertEqual(Report.search([('leave_id.state', '=', 'validate'), ('employee_id', '=', self.employee.id)]).leave_id, validated)

    def test_time_rule_output_excluded(self):
        """Leaves produced by a time rule are not in the report, even when a leave becomes one later."""
        kept, reclassified = self._create_leaves([
            {'request_date_from': date(2024, 3, 11), 'request_date_to': date(2024, 3, 11)},
            {'request_date_from': date(2024, 3, 12), 'request_date_to': date(2024, 3, 12)},
        ])
        rule = self.env['hr.time.rule'].create({
            'name': 'Inactive rule',
            'active': False,
            'condition_work_entry_type_ids': [(4, self.day_type.id)],
            'work_entry_type_id': self.half_day_type.id,
            'working_hours_mode': 'day',
            'expected_hours': 0.0,
        })
        reclassified.sudo().time_rule_id = rule
        self.env.cr.flush()
        rows = self.env['hr.leave.employee.report'].with_company(self.company).search([('employee_id', '=', self.employee.id)])
        self.assertEqual(rows.leave_id, kept)

    def test_multi_company(self):
        """Only the leaves of the employees of the selected companies are shown."""
        self.employee = self.employee_external
        leave = self._create_leaves([{'request_date_from': date(2024, 7, 1), 'request_date_to': date(2024, 7, 1)}])
        domain = [('employee_id', '=', self.employee_external.id)]
        self.assertFalse(self._report(domain, company=self.company))
        self.assertEqual(self._report(domain, company=self.external_company), [(date(2024, 7, 1), 1, 8)])
        self.assertEqual(leave.number_of_days, 1)

    # The report reads hr.leave.day_durations: it must follow every change of the leaves.

    def _days(self, leave):
        return [day for day, _days, _hours in self._report([('leave_id', '=', leave.id)])]

    def test_report_reads_stored_days(self):
        """Reading the report does not compute any duration: it reads the stored days."""
        leave = self._create_leaves([{'request_date_from': date(2024, 1, 8), 'request_date_to': date(2024, 1, 9)}])
        self.env.cr.flush()
        self.assertEqual(sorted(leave.sudo().day_durations.values()), [[1, 8], [1, 8]])
        with patch.object(self.registry['hr.leave'], '_get_durations', side_effect=AssertionError("durations computed")):
            self.assertEqual(len(self._report()), 2)

    def test_days_follow_dates(self):
        leave = self._create_leaves([{'request_date_from': date(2024, 1, 8), 'request_date_to': date(2024, 1, 10)}])
        self.assertEqual(self._days(leave), [date(2024, 1, 8), date(2024, 1, 9), date(2024, 1, 10)])
        leave.with_context(leave_skip_state_check=True).request_date_to = date(2024, 1, 12)
        self.assertEqual(self._days(leave), [date(2024, 1, d) for d in (8, 9, 10, 11, 12)])

    def test_days_follow_public_holidays(self):
        """Adding, moving and removing a public holiday inside a leave updates its days."""
        leave = self._create_leaves([{'request_date_from': date(2024, 1, 8), 'request_date_to': date(2024, 1, 12)}])
        holiday = self.env['resource.calendar.leaves'].create({
            'name': 'Public holiday',
            'company_id': self.company.id,
            'date_from': datetime(2024, 1, 9, 23, 0),  # Wednesday in Europe/Brussels
            'date_to': datetime(2024, 1, 10, 22, 59, 59),
        })
        self.assertEqual(self._days(leave), [date(2024, 1, d) for d in (8, 9, 11, 12)])
        holiday.write({'date_from': datetime(2024, 1, 10, 23, 0), 'date_to': datetime(2024, 1, 11, 22, 59, 59)})
        self.assertEqual(self._days(leave), [date(2024, 1, d) for d in (8, 9, 10, 12)])
        holiday.unlink()
        self.assertEqual(self._days(leave), [date(2024, 1, d) for d in (8, 9, 10, 11, 12)])

    def test_days_follow_schedule(self):
        """Moving the leave to a schedule without Thursday and Friday removes these days."""
        leave = self._create_leaves([{'request_date_from': date(2024, 1, 8), 'request_date_to': date(2024, 1, 12)}])
        calendar = self.env['resource.calendar'].create({
            'name': 'Monday to Wednesday',
            'company_id': self.company.id,
            'attendance_ids': [
                (0, 0, {'dayofweek': weekday, 'hour_from': hour, 'hour_to': hour + 4})
                for weekday in ['0', '1', '2']
                for hour in [8, 13]
            ],
        })
        leave.resource_calendar_id = calendar
        self.assertEqual(self._days(leave), [date(2024, 1, 8), date(2024, 1, 9), date(2024, 1, 10)])

    def test_days_follow_type(self):
        """Switching to a type counted in calendar days adds the weekend."""
        leave = self._create_leaves([{'request_date_from': date(2024, 1, 12), 'request_date_to': date(2024, 1, 15)}])
        self.assertEqual(self._days(leave), [date(2024, 1, 12), date(2024, 1, 15)])
        leave.with_context(leave_skip_state_check=True).work_entry_type_id = self.calendar_day_type
        self.assertEqual(self._days(leave), [date(2024, 1, d) for d in (12, 13, 14, 15)])

    def test_days_with_duration_given_at_creation(self):
        """A leave created with its duration (e.g. when a leave is split on a new version) still gets its days."""
        leave = self._create_leaves([{
            'request_date_from': date(2024, 1, 8),
            'request_date_to': date(2024, 1, 9),
            'number_of_days': 2,
            'number_of_hours': 16,
        }])
        self.assertEqual(self._days(leave), [date(2024, 1, 8), date(2024, 1, 9)])
