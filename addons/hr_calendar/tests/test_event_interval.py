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
