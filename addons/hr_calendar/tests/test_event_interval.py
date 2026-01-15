# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from datetime import datetime
from pytz import timezone
from odoo.addons.hr_calendar.tests.common import TestHrCalendarCommon


@tagged('event_interval')
class TestEventInterval(TestHrCalendarCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_A.resource_calendar_id = cls.calendar_35h

    def test_empty_event(self):
        event, allday_event = self.env['calendar.event'].with_context(company_id=self.company_A.id).create([
            {
                'start': datetime(2024, 7, 12),
                'stop': datetime(2024, 7, 12),
                'name': "Event"
            },
            {
                'start': datetime(2024, 7, 12),
                'stop': datetime(2024, 7, 12),
                'allday': True,
                'name': "Event all day"
            }
        ])
        result = (event + allday_event)._get_events_interval()
        self.assertEqual(result.get(event)._items, [])
        self.assertEqual(result.get(allday_event)._items, [
            (
                timezone('Europe/Brussels').localize(datetime(2024, 7, 12, 8, 0, 0)),
                timezone('Europe/Brussels').localize(datetime(2024, 7, 12, 12, 0, 0)),
                self.env['resource.calendar']
            ),
            (
                timezone('Europe/Brussels').localize(datetime(2024, 7, 12, 13, 0, 0)),
                timezone('Europe/Brussels').localize(datetime(2024, 7, 12, 16, 0, 0)),
                self.env['resource.calendar']
            )
        ])

    def test_allday_event_during_working_day(self):
        event = self.env['calendar.event'].with_context(company_id=self.company_A.id).create([
            {
                'start': datetime(2024, 7, 12),
                'stop': datetime(2024, 7, 12, 23, 59, 59),
                'allday': True,
                'name': "Event 1"
            }
        ])
        result = event._get_events_interval()
        self.assertEqual(result.get(event)._items, [
            (
                timezone('Europe/Brussels').localize(datetime(2024, 7, 12, 8, 0, 0)),
                timezone('Europe/Brussels').localize(datetime(2024, 7, 12, 12, 0, 0)),
                self.env['resource.calendar']
            ),
            (
                timezone('Europe/Brussels').localize(datetime(2024, 7, 12, 13, 0, 0)),
                timezone('Europe/Brussels').localize(datetime(2024, 7, 12, 16, 0, 0)),
                self.env['resource.calendar']
            )
        ])

    def test_allday_event_during_no_working_day(self):
        """
        An allday event is calculated using the company's calendar. If the event is scheduled on a day when the company
        is closed, the duration of the event will be set to zero.
        """

        # A : Saturday
        # B : Friday - Saturday
        # C : Sunday - Monday
        # D : Friday - Saturday - Sunday - Monday
        events = self.env['calendar.event'].with_context(company_id=self.company_A.id).create([
            {
                'start': datetime(2024, 7, 13),
                'stop': datetime(2024, 7, 13, 23, 59, 59),
                'allday': True,
                'name': "Event A"
            },
            {
                'start': datetime(2024, 7, 12),
                'stop': datetime(2024, 7, 13, 23, 59, 59),
                'allday': True,
                'name': "Event B"
            },
            {
                'start': datetime(2024, 7, 14),
                'stop': datetime(2024, 7, 15, 23, 59, 59),
                'allday': True,
                'name': "Event C"
            },
            {
                'start': datetime(2024, 7, 12),
                'stop': datetime(2024, 7, 15, 23, 59, 59),
                'allday': True,
                'name': "Event D"
            }
        ])
        result = events._get_events_interval()
        for interval in result.values():
            self.assertEqual(interval._items, [])

    def test_event_during_working_day(self):
        event = self.env['calendar.event'].with_context(company_id=self.company_A.id).create([
            {
                'start': datetime(2024, 7, 12, 8, 30, 0),
                'stop': datetime(2024, 7, 12, 9, 30, 0),
                'name': "Event 3"
            }
        ])
        result = event._get_events_interval()
        self.assertEqual(result.get(event)._items, [
            (
                timezone('UTC').localize(datetime(2024, 7, 12, 8, 30, 0)),
                timezone('UTC').localize(datetime(2024, 7, 12, 9, 30, 0)),
                self.env['resource.calendar']
            )
        ])
