from datetime import datetime
from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestCalendarEventTimeExtraction(TransactionCase):

    def setUp(self):
        super().setUp()
        self.CalendarEvent = self.env['calendar.event']

    def test_parse_time_from_title_single_times(self):
        test_cases = [
            ('9am meeting', 9, 0, 10, 0),
            ('9h coffee break', 9, 0, 10, 0),
            ('9H standup', 9, 0, 10, 0),
            ('9:00 presentation', 9, 0, 10, 0),
            ('09:00 call', 9, 0, 10, 0),
            ('9 am sync', 9, 0, 10, 0),
            ('21h dinner', 21, 0, 22, 0),
            ('21:30 evening call', 21, 30, 22, 30),
            ('2pm review', 14, 0, 15, 0),
            ('14:30 meeting', 14, 30, 15, 30),
            ('9:30pm sync', 21, 30, 22, 30),
            ('sync 9:30', 9, 30, 10, 30),
        ]

        for title, start_h, start_m, end_h, end_m in test_cases:
            event = self.CalendarEvent.new({'name': title})
            result = event._parse_time_from_title(title)

            self.assertIsNotNone(result, f"Failed to parse time from: {title}")
            self.assertEqual(result['start_time'].hour, start_h, f"Wrong start hour for: {title}")
            self.assertEqual(result['start_time'].minute, start_m, f"Wrong start minute for: {title}")
            self.assertEqual(result['end_time'].hour, end_h, f"Wrong end hour for: {title}")
            self.assertEqual(result['end_time'].minute, end_m, f"Wrong end minute for: {title}")

    def test_parse_time_from_title_ranges(self):
        test_cases = [
            # Basic ranges
            ('9-10 workshop', 9, 0, 10, 0),
            ('9 to 10 workshop', 9, 0, 10, 0),
            ('9–11h training', 9, 0, 11, 0),  # en-dash
            ('2pm-4pm meeting', 14, 0, 16, 0),
            ('14:30-16:00 review', 14, 30, 16, 0),
            ('9:00-10:30 session', 9, 0, 10, 30),
            ('10h-12h break', 10, 0, 12, 0),
            ('11 pm to 1 am lan party', 23, 0, 1, 0),

            # Mixed suffix inheritance
            ('9am-11 workshop', 9, 0, 11, 0),
            ('9-11am workshop', 9, 0, 11, 0),
            ('9am–11h training', 9, 0, 11, 0),
            ('9–11 pm shift', 21, 0, 23, 0),

            # Minutes on one side only
            ('9:30-11 meeting', 9, 30, 11, 0),
            ('9-11:30 meeting', 9, 0, 11, 30),
        ]

        for title, start_h, start_m, end_h, end_m in test_cases:
            event = self.CalendarEvent.new({'name': title})
            result = event._parse_time_from_title(title)

            self.assertIsNotNone(result, f"Failed to parse time from: {title}")
            self.assertEqual(result['start_time'].hour, start_h, f"Wrong start hour for: {title}")
            self.assertEqual(result['start_time'].minute, start_m, f"Wrong start minute for: {title}")
            self.assertIn('end_time', result, f"Should have end_time for: {title}")
            self.assertEqual(result['end_time'].hour, end_h, f"Wrong end hour for: {title}")
            self.assertEqual(result['end_time'].minute, end_m, f"Wrong end minute for: {title}")

    def test_parse_time_from_title_no_time(self):
        """Test titles without time information"""
        test_cases = [
            # No time
            'Project meeting',
            'Standup',
            'Quick sync',
            'Review session',

            # Numbers that are not times
            'Version 2.10 release',
            'RFC 3339 discussion',
            'Budget 2024 review',
            'Top 10 priorities',

            # Invalid times
            '25h maintenance',
            '9:99 meeting',
            '32:00 review',

            # Partial or ambiguous
            'meeting at nine',
            'room 9 booking',
            'phase 2 planning',

            # Broken ranges
            '9-11-12 meeting',
            '9- meeting',
            '-11 training',
            '9--11 workshop',
        ]

        for title in test_cases:
            event = self.CalendarEvent.new({'name': title})
            result = event._parse_time_from_title(title)
            self.assertIsNone(result, f"Should not find time in: {title}")

    def get_event_times_in_user_tz(self, event):
        timezone = self.env.context.get('tz') or self.env.user.partner_id.tz or 'UTC'
        self_tz = event.with_context(tz=timezone)

        start_tz = fields.Datetime.context_timestamp(self_tz, fields.Datetime.from_string(event.start))
        stop_tz = fields.Datetime.context_timestamp(self_tz, fields.Datetime.from_string(event.stop))

        return start_tz, stop_tz

    def test_onchange_name_with_quick_create_context(self):
        event = self.CalendarEvent.with_context(is_quick_create_form=True).new({
            'name': '9am meeting',
            'allday': True,
            'start': datetime(2024, 1, 15),
        })

        event._onchange_name_extract_time()

        # Event times are stored as UTC. Convert date and time into user timezone
        start_tz, stop_tz = self.get_event_times_in_user_tz(event)

        self.assertFalse(event.allday)
        self.assertEqual(event.name, "meeting")
        self.assertEqual(start_tz.hour, 9, "Start hour should be updated to 9")
        self.assertEqual(start_tz.minute, 0, "Start minute should be 0")
        self.assertEqual(stop_tz.hour, 10, "end hour should be updated to 10")
        self.assertEqual(stop_tz.minute, 0, "End minute should be 0")
        self.assertEqual(start_tz.date(), datetime(2024, 1, 15).date(), "Date should remain unchanged")

    def test_onchange_name_with_time_range(self):
        event = self.CalendarEvent.with_context(is_quick_create_form=True).new({
            'name': '14:30-16:00 review',
            'allday': True,
            'start': datetime(2024, 1, 15),
        })

        event._onchange_name_extract_time()

        # Event times are stored as UTC. Convert date and time into user timezone
        start_tz, stop_tz = self.get_event_times_in_user_tz(event)

        self.assertFalse(event.allday)
        self.assertEqual(event.name, "review")
        self.assertEqual(start_tz.hour, 14, "Start hour should be 14")
        self.assertEqual(start_tz.minute, 30, "Start minute should be 30")
        self.assertEqual(stop_tz.hour, 16, "Stop hour should be 16")
        self.assertEqual(stop_tz.minute, 0, "Stop minute should be 0")
        self.assertEqual(start_tz.date(), datetime(2024, 1, 15).date(), "Start date should remain unchanged")
        self.assertEqual(stop_tz.date(), datetime(2024, 1, 15).date(), "Stop date should remain unchanged")

    def test_onchange_name_without_quick_create_context(self):
        original_start = datetime(2024, 1, 15, 10, 0, 0)

        # Create event WITHOUT quick create context
        event = self.CalendarEvent.new({
            'name': '9am meeting',
            'start': original_start,
        })

        event._onchange_name_extract_time()

        self.assertEqual(event.start, original_start, "Start should not change without quick create context")

    def test_onchange_name_no_time_in_title(self):
        original_start = datetime(2024, 1, 15)

        event = self.CalendarEvent.with_context(is_quick_create_form=True).new({
            'name': 'Project meeting',
            'allday': True,
            'start': original_start,
        })

        event._onchange_name_extract_time()

        self.assertTrue(event.allday)
        self.assertEqual(event.start, original_start, "Start should not change when no time in title")

    def test_convert_to_24h(self):
        event = self.CalendarEvent.new({})

        self.assertEqual(event._convert_to_24h(9, 'am'), 9)
        self.assertEqual(event._convert_to_24h(12, 'am'), 0)  # Midnight
        self.assertEqual(event._convert_to_24h(2, 'pm'), 14)
        self.assertEqual(event._convert_to_24h(12, 'pm'), 12)  # Noon
        self.assertEqual(event._convert_to_24h(14, 'h'), 14)
        self.assertEqual(event._convert_to_24h(9, 'h'), 9)
        self.assertEqual(event._convert_to_24h(15, None), 15)
        self.assertEqual(event._convert_to_24h(9, None), 9)
