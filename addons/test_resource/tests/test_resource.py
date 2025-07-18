# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from pytz import utc

from odoo.tools.date_utils import sum_intervals
from odoo.tools.intervals import Intervals

from odoo.addons.test_resource.tests.common import TestResourceCommon


class TestResource(TestResourceCommon):

    def test_calendars_validity_within_period(self):
        calendars = self.jean.resource_id._get_calendars_validity_within_period(
            utc.localize(datetime(2021, 7, 1, 8, 0, 0)),
            utc.localize(datetime(2021, 7, 30, 17, 0, 0)),
        )
        interval = Intervals([(
            utc.localize(datetime(2021, 7, 1, 8, 0, 0)),
            utc.localize(datetime(2021, 7, 30, 17, 0, 0)),
            self.env['resource.calendar.attendance'],
        )])

        self.assertEqual(1, len(calendars), "The dict returned by calendars validity should only have 1 entry")
        self.assertEqual(1, len(calendars[self.jean.resource_id.id]), "Jean should only have one calendar")
        jean_entry = calendars[self.jean.resource_id.id]
        jean_calendar = next(iter(jean_entry))
        self.assertEqual(self.jean.resource_calendar_id, jean_calendar, "It should be Jean's Calendar")
        self.assertFalse(jean_entry[jean_calendar] - interval, "Interval should cover all calendar's validity")
        self.assertFalse(interval - jean_entry[jean_calendar], "Calendar validity should cover all interval")

        calendars = self.env['resource.resource']._get_calendars_validity_within_period(
            utc.localize(datetime(2021, 7, 1, 8, 0, 0)),
            utc.localize(datetime(2021, 7, 30, 17, 0, 0)),
        )
        self.assertEqual(1, len(calendars), "The dict returned by calendars validity should only have 1 entry")
        self.assertEqual(1, len(calendars[False]), "False (default) should only have one calendar")
        false_entry = calendars[False]
        false_calendar = next(iter(false_entry))
        self.assertEqual(self.env.company.resource_calendar_id, false_calendar, "It should be company calendar Calendar")
        self.assertFalse(false_entry[false_calendar] - interval, "Interval should cover all calendar's validity")
        self.assertFalse(interval - false_entry[false_calendar], "Calendar validity should cover all interval")

    def test_performance(self):
        calendars = [self.calendar_jean, self.calendar_john, self.calendar_jules, self.calendar_patel]
        calendars_len = len(calendars)
        self.resources_test = self.env['resource.test'].create([{
            'name': 'resource ' + str(i),
            'resource_calendar_id': calendars[i % calendars_len].id,
        } for i in range(0, 50)])

        start = utc.localize(datetime(2021, 7, 7, 12, 0, 0))
        end = utc.localize(datetime(2021, 7, 16, 23, 59, 59))
        with self.assertQueryCount(13):
            work_intervals, _ = self.resources_test.resource_id._get_valid_work_intervals(start, end)

        self.assertEqual(len(work_intervals), 50)

    def test_get_valid_work_intervals(self):
        start = utc.localize(datetime(2021, 7, 7, 12, 0, 0))
        end = utc.localize(datetime(2021, 7, 16, 23, 59, 59))
        work_intervals, _ = self.jean.resource_id._get_valid_work_intervals(start, end)
        sum_work_intervals = sum_intervals(work_intervals[self.jean.resource_id.id])
        self.assertEqual(58, sum_work_intervals, "Sum of the work intervals for the resource jean should be 40h+18h = 58h")

    def test_get_valid_work_intervals_calendars_only(self):
        calendars = [self.calendar_jean, self.calendar_john, self.calendar_jules, self.calendar_patel]
        start = utc.localize(datetime(2021, 7, 7, 12, 0, 0))
        end = utc.localize(datetime(2021, 7, 16, 23, 59, 59))
        _, calendars_intervals = self.env['resource.resource']._get_valid_work_intervals(start, end, calendars)
        sum_work_intervals_jean = sum_intervals(calendars_intervals[self.calendar_jean.id])
        self.assertEqual(58, sum_work_intervals_jean, "Sum of the work intervals for the calendar of jean should be 40h+18h = 58h")
        sum_work_intervals_john = sum_intervals(calendars_intervals[self.calendar_john.id])
        self.assertEqual(26 - 1 / 3600, sum_work_intervals_john, "Sum of the work intervals for the calendar of john should be 20h+6h-1s = 25h59m59s")
        sum_work_intervals_jules = sum_intervals(calendars_intervals[self.calendar_jules.id])
        self.assertEqual(31, sum_work_intervals_jules, "Sum of the work intervals for the calendar of jules should be Wodd:15h+Wpair:16h = 31h")
        sum_work_intervals_patel = sum_intervals(calendars_intervals[self.calendar_patel.id])
        self.assertEqual(49, sum_work_intervals_patel, "Sum of the work intervals for the calendar of patel should be 14+35h = 49h")

    def test_switch_two_weeks_resource(self):
        """
            Check that it is possible to switch the company's default calendar
        """
        self.env.company.resource_calendar_id = self.two_weeks_resource
        company_resource = self.env.company.resource_calendar_id
        # Switch two times to be sure to test both cases
        company_resource.switch_calendar_type()
        company_resource.switch_calendar_type()

    def test_create_company_using_two_weeks_resource(self):
        """
            Check that we can create a new company
            if the default company calendar is two weeks
        """
        self.env.company.resource_calendar_id = self.two_weeks_resource
        self.env['res.company'].create({'name': 'New Company'})

    def test_empty_working_hours_for_two_weeks_resource(self):
        resource = self._define_calendar_2_weeks(
            'Two weeks resource',
            [],
            'Europe/Brussels',
        )
        self.env['resource.calendar.attendance'].create({
            'name': 'test',
            'calendar_id': resource.id,
            'hour_from': 0,
            'hour_to': 0,
        })
        resource_hour = resource._get_hours_per_day()
        self.assertEqual(resource_hour, 0.0)

    def test_resource_without_calendar(self):
        resource = self.env['resource.resource'].create({
            'name': 'resource',
            'calendar_id': False,
        })

        resource.company_id.resource_calendar_id = False
        unavailabilities = resource._get_unavailable_intervals(datetime(2024, 7, 11), datetime(2024, 7, 12))
        self.assertFalse(unavailabilities)
