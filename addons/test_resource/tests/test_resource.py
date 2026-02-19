# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, UTC

from odoo.exceptions import ValidationError

from odoo.tools.date_utils import sum_intervals
from odoo.tools.intervals import Intervals

from odoo.tests import tagged, Form

from odoo.addons.test_resource.tests.common import TestResourceCommon


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestResource(TestResourceCommon):

    def test_calendars_validity_within_period(self):
        calendars = self.jean.resource_id._get_calendars_validity_within_period(
            datetime(2021, 7, 1, 8, 0, 0).replace(tzinfo=UTC),
            datetime(2021, 7, 30, 17, 0, 0).replace(tzinfo=UTC),
        )
        interval = Intervals([(
            datetime(2021, 7, 1, 8, 0, 0).replace(tzinfo=UTC),
            datetime(2021, 7, 30, 17, 0, 0).replace(tzinfo=UTC),
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
            datetime(2021, 7, 1, 8, 0, 0).replace(tzinfo=UTC),
            datetime(2021, 7, 30, 17, 0, 0).replace(tzinfo=UTC),
        )
        self.assertEqual(1, len(calendars), "The dict returned by calendars validity should only have 1 entry")
        self.assertEqual(1, len(calendars[False]), "False (default) should only have one calendar")
        false_entry = calendars[False]
        false_calendar = next(iter(false_entry))
        self.assertEqual(self.env.company.resource_calendar_id, false_calendar, "It should be company calendar Calendar")
        self.assertFalse(false_entry[false_calendar] - interval, "Interval should cover all calendar's validity")
        self.assertFalse(interval - false_entry[false_calendar], "Calendar validity should cover all interval")

    def test_performance(self):
        calendars = [self.calendar_jean, self.calendar_john, self.calendar_patel]
        calendars_len = len(calendars)
        self.resources_test = self.env['resource.test'].create([{
            'name': 'resource ' + str(i),
            'resource_calendar_id': calendars[i % calendars_len].id,
        } for i in range(0, 50)])

        start = datetime(2021, 7, 7, 12, 0, 0).replace(tzinfo=UTC)
        end = datetime(2021, 7, 16, 23, 59, 59).replace(tzinfo=UTC)
        with self.assertQueryCount(13):
            work_intervals, _ = self.resources_test.resource_id._get_valid_work_intervals(start, end)

        self.assertEqual(len(work_intervals), 50)

    def test_get_valid_work_intervals(self):
        start = datetime(2021, 7, 7, 12, 0, 0).replace(tzinfo=UTC)
        end = datetime(2021, 7, 16, 23, 59, 59).replace(tzinfo=UTC)
        work_intervals, _ = self.jean.resource_id._get_valid_work_intervals(start, end)
        sum_work_intervals = sum_intervals(work_intervals[self.jean.resource_id.id])
        self.assertEqual(58, sum_work_intervals, "Sum of the work intervals for the resource jean should be 40h+18h = 58h")

    def test_get_valid_work_intervals_calendars_only(self):
        calendars = [self.calendar_jean, self.calendar_john, self.calendar_patel]
        start = datetime(2021, 7, 7, 12, 0, 0).replace(tzinfo=UTC)
        end = datetime(2021, 7, 16, 23, 59, 59).replace(tzinfo=UTC)
        _, calendars_intervals = self.env['resource.resource']._get_valid_work_intervals(start, end, calendars)
        sum_work_intervals_jean = sum_intervals(calendars_intervals[self.calendar_jean.id])
        self.assertEqual(60, sum_work_intervals_jean, "Sum of the work intervals for the calendar of jean should be 40h+20h = 60h")
        sum_work_intervals_john = sum_intervals(calendars_intervals[self.calendar_john.id])
        self.assertEqual(32, sum_work_intervals_john, "Sum of the work intervals for the calendar of john should be 24h+8h = 32h")
        sum_work_intervals_patel = sum_intervals(calendars_intervals[self.calendar_patel.id])
        self.assertEqual(53, sum_work_intervals_patel, "Sum of the work intervals for the calendar of patel should be 4h+14h+35h = 53h")

    def test_resource_without_calendar(self):
        resource = self.env['resource.resource'].create({
            'name': 'resource',
            'calendar_id': False,
        })

        resource.company_id.resource_calendar_id = False
        unavailabilities = resource._get_unavailable_intervals(datetime(2024, 7, 11), datetime(2024, 7, 12))
        self.assertFalse(unavailabilities)

    def test_multi_company_prevent_incoherent_calendar_for_material_resource(self):
        """ Test that changing the company of a material resource sets its
            working calendar to False in order to prevent incoherent data.

            Test case:
            1) create multiple companies by setting up second company
            2) set a material of default company with a working calendar
            3) switch the company of material resource to 2nd_company
            4) verify that the working calendar is set to False
        """

        # create a second company
        second_company = self.env['res.company'].create({
            'name': 'Arasaka',
            'currency_id': self.env.ref('base.USD').id,
        })
        # create a working calendar for the material resource
        resource = self.env['resource.resource'].create({
            'name': 'resource',
            'calendar_id': False,
            'resource_type': 'material',
        })

        # create a working calendar for the material resource
        resource.calendar_id = self.env['resource.calendar'].create({
            'name': 'Classic 20h/week',
            'tz': 'UTC',
            'company_id': self.env.company.id,
            'hours_per_day': 4.0,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
            ]
        })

        # change company via the Form view
        form = Form(resource)
        form.company_id = second_company
        form.save()

        # check that the working calendar is set to False
        self.assertEqual(resource.company_id, second_company, "Material resource should have the new company set")
        self.assertFalse(resource.calendar_id, "Material resource should have its working calendar set to False when changing its company")

    def test_change_company_id_with_linked_resources_should_raise_validation_error(self):
        self.company_a = self.env['res.company'].create({'name': 'Company A'})
        self.company_b = self.env['res.company'].create({'name': 'Company B'})
        self.calendar = self.env['resource.calendar'].create({
            'name': 'Test Calendar',
            'company_id': self.company_a.id,
        })
        self.resource = self.env['resource.resource'].create({
            'name': 'Test Resource',
            'calendar_id': self.calendar.id,
            'company_id': self.company_a.id,
        })

        with self.assertRaises(ValidationError):
            self.calendar.write({'company_id': self.company_b.id})
