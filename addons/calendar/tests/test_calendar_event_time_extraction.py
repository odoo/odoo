from datetime import datetime
from odoo.tests import TransactionCase, tagged, new_test_user, users


@tagged('post_install', '-at_install')
class TestCalendarEventTimeExtraction(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_utc_tz = new_test_user(
            cls.env,
            login='user_utc_tz',
            name='Humphrey Appleby',
            groups='base.group_user',
            tz='UTC',
        )
        cls.user_brussels_tz = new_test_user(
            cls.env,
            login='user_brussels_tz',
            name='Hercule Poirot',
            groups='base.group_user',
            tz='Europe/Brussels',
        )
        cls.user_japan_tz = new_test_user(
            cls.env,
            login='user_japan_tz',
            name='Gojo Satoru',
            groups='base.group_user',
            tz='Asia/Tokyo',
        )

    @users('user_utc_tz')
    def test_parse_time_from_title(self):
        test_cases = [
            # Single times
            ('9am meeting', 9, 0, 10, 0),
            ('9h coffee break', 9, 0, 10, 0),
            ('9H standup', 9, 0, 10, 0),
            ('9:00 presentation', 9, 0, 10, 0),
            ('09:00 call', 9, 0, 10, 0),
            ('9 pm sync', 21, 0, 22, 0),
            ('21h dinner', 21, 0, 22, 0),
            ('21:30 evening call', 21, 30, 22, 30),
            ('2pm review', 14, 0, 15, 0),
            ('14:30 meeting', 14, 30, 15, 30),
            ('9:30pm sync', 21, 30, 22, 30),
            ('sync 9:30', 9, 30, 10, 30),

            # Basic ranges
            ('9-10 workshop', 9, 0, 10, 0),
            ('9 to 10 workshop', 9, 0, 10, 0),
            ('9–11h training', 9, 0, 11, 0),  # en-dash
            ('2pm-4pm meeting', 14, 0, 16, 0),
            ('14:30-16:00 review', 14, 30, 16, 0),
            ('9:00-10:30 session', 9, 0, 10, 30),
            ('10h-12h break', 10, 0, 12, 0),
            ('11 pm to 1 am lan party', 23, 0, 1, 0),
            ('9 to 5 worktime', 9, 0, 17, 0),

            # Mixed suffix inheritance
            ('9am-11 workshop', 9, 0, 11, 0),
            ('9-11am workshop', 9, 0, 11, 0),
            ('9am–11h training', 9, 0, 11, 0),
            ('9–11 pm shift', 9, 0, 23, 0),

            # Minutes on one side only
            ('9:30-11 meeting', 9, 30, 11, 0),
            ('9-11:30 meeting', 9, 0, 11, 30),

            # Time range boundaries
            ('Meeting 9-10', 9, 0, 10, 0),
        ]

        for title, start_h, start_m, end_h, end_m in test_cases:
            event = self.env['calendar.event'].new({'name': title})
            result = event._parse_time_from_title()

            self.assertIsNotNone(result, f"Failed to parse time from: {title}")
            self.assertEqual(result[0].hour, start_h, f"Wrong start hour for: {title}")
            self.assertEqual(result[0].minute, start_m, f"Wrong start minute for: {title}")
            self.assertEqual(result[1].hour, end_h, f"Wrong end hour for: {title}")
            self.assertEqual(result[1].minute, end_m, f"Wrong end minute for: {title}")

    @users('user_utc_tz')
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
            'test 19-3-2026',
            '9-11-12 meeting',
            '9- meeting',
            '-11 training',
            '9--11 workshop',
            'foo10am',
            'meeting10-11',
        ]

        for title in test_cases:
            event = self.env['calendar.event'].new({'name': title})
            result = event._parse_time_from_title()
            self.assertIsNone(result, f"Should not find time in: {title}")

    @users('user_utc_tz', 'user_brussels_tz', 'user_japan_tz')
    def test_onchange_name_with_different_timezones(self):
        event = self.env['calendar.event'].with_context(is_quick_create_form=True).create([{
            'name': '8-10am meeting',
            'allday': True,
            'start': datetime(2024, 1, 15),
        }])

        timezone_to_utc = {
            'UTC': (8, 10),                # UTC
            'Europe/Brussels': (7, 9),     # UTC+1
            'Asia/Tokyo': (23, 1)          # UTC+9, different date!
        }

        event._onchange_name_extract_time()
        start_hour_utc, end_hour_utc = timezone_to_utc.get(self.env.user.tz)

        self.assertFalse(event.allday)
        self.assertEqual(event.start.hour, start_hour_utc, "Start hour should be updated to 9 (UTC)")
        self.assertEqual(event.stop.hour, end_hour_utc, "End hour should be updated to 10 (UTC)")

        if self.env.user.tz == 'Asia/Tokyo':
            self.assertEqual(event.start.date(), datetime(2024, 1, 14).date(), "Japan's event should start one day earlier")
            self.assertEqual(event.stop.date(), datetime(2024, 1, 15).date(), "End time for japan should be the same day")
        else:
            self.assertEqual(event.start.date(), datetime(2024, 1, 15).date(), "Date should remain unchanged")

    @users('user_utc_tz')
    def test_onchange_name_without_parsing(self):
        original_start = datetime(2024, 1, 15, 10, 0, 0)

        event_no_quickcreate = self.env['calendar.event'].new({
            'name': '9am meeting',
            'allday': True,
            'start': original_start,
        })
        event_no_time = self.env['calendar.event'].with_context(is_quick_create_form=True).new({
            'name': 'Project meeting',
            'allday': True,
            'start': original_start,
        })
        for event in (event_no_quickcreate, event_no_time):
            with self.subTest(event=event):
                event._onchange_name_extract_time()
                self.assertTrue(event.allday, "Event should remain allday without quickcreate context")
                self.assertEqual(event.start, original_start, "Start should not change without quick create context")
