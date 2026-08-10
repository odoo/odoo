# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import unittest
from datetime import date, datetime, timezone
from requests.exceptions import HTTPError

from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import HttpCase

_logger = logging.getLogger(__name__)

try:
    import vobject
except ImportError:
    vobject = None


@tagged('post_install', '-at_install')
class TestEventIcs(HttpCase):

    def _assertRaises404(self, func, msg=None, *args, **kwargs):
        with self.assertRaises(HTTPError, msg=msg):
            try:
                func(*args, **kwargs)
            except HTTPError as e:
                self.assertEqual(e.response.status_code, 404, msg=msg)
                raise

    def test_ics_event_timestamps(self):
        """Check the start and end timestamps of ics files."""
        if not vobject:
            raise unittest.SkipTest("Skip test when `vobject` Python module is not found.")

        (event_start, event_end), (slot_start, slot_end), (other_slot_start, other_slot_end) = (
            event_dts, slot_dts, _other_slot_dts
        ) = (
            (datetime(2025, 4, 21, 6, 30, 0, tzinfo=timezone.utc), datetime(2025, 4, 21, 20, 0, 0, tzinfo=timezone.utc)),
            (datetime(2025, 4, 21, 9, 0, 0, tzinfo=timezone.utc), datetime(2025, 4, 21, 12, 0, 0, tzinfo=timezone.utc)),
            (datetime(2025, 4, 21, 14, 0, 0, tzinfo=timezone.utc), datetime(2025, 4, 21, 17, 0, 0, tzinfo=timezone.utc)),
        )
        self.assertNotEqual(slot_dts, event_dts)
        common_vals = {'date_begin': event_start.replace(tzinfo=None), 'date_end': event_end.replace(tzinfo=None),
                       'date_tz': 'UTC'}
        events_vals = [
            {'name': 'Event', 'event_slot_ids': [
                Command.create({'date': date(2025, 4, 21), 'start_hour': slot_start.hour, 'end_hour': slot_end.hour}),
            ]},
            {'name': 'Other Event', 'event_slot_ids': [
                Command.create({'date': date(2025, 4, 21), 'start_hour': other_slot_start.hour, 'end_hour': other_slot_end.hour}),
            ]},
        ]
        event, other_event = self.env['event.event'].create([common_vals | event_vals for event_vals in events_vals])

        def fetch_timestamps(slot_id=False):
            query = f'?slot_id={slot_id}' if slot_id else ""
            response = self.url_open(f'/event/{event.id}/ics{query}')
            response.raise_for_status()
            v_event = vobject.readOne(response.content.decode()).vevent
            return v_event.dtstart.value, v_event.dtend.value

        self.authenticate(None, None)
        self._assertRaises404(fetch_timestamps, msg="Private event")
        event.website_published = True
        self.assertEqual(fetch_timestamps(), event_dts, msg="No slot -> Expected event timestamps")
        self.assertEqual(fetch_timestamps(event.event_slot_ids.id), slot_dts, msg="Valid slot for event")
        self._assertRaises404(fetch_timestamps, slot_id=other_event.event_slot_ids.id, msg="Invalid slot for event")
