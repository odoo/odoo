from datetime import datetime, date

from odoo.tests.common import TransactionCase


class TestRruleUntilTimezone(TransactionCase):

    def test_until_conversion(self):
        cases = [
            # (label, rule, event_tz, expected_date)
            # UNTIL=20231026T025959Z = Oct 26 02:59:59 UTC
            ('UTC-3: Oct 25 local',     'FREQ=WEEKLY;BYDAY=TH;UNTIL=20231026T025959Z', 'America/Argentina/Buenos_Aires', date(2023, 10, 25)),
            ('UTC: Oct 26',             'FREQ=WEEKLY;BYDAY=TH;UNTIL=20231026T025959Z', 'UTC',                            date(2023, 10, 26)),
            ('UTC+5:30: Oct 26',        'FREQ=WEEKLY;BYDAY=TH;UNTIL=20231026T025959Z', 'Asia/Kolkata',                   date(2023, 10, 26)),
            # UNTIL=20231025T185959Z: crosses midnight in UTC+5:30 -> Oct 26 local
            ('UTC+5:30 cross midnight', 'FREQ=WEEKLY;BYDAY=TH;UNTIL=20231025T185959Z', 'Asia/Kolkata',                   date(2023, 10, 26)),
            # UNTIL without Z is naive: stored as-is, no timezone conversion
            ('naive UNTIL',             'FREQ=WEEKLY;BYDAY=TH;UNTIL=20231026T025959',  'America/Argentina/Buenos_Aires', date(2023, 10, 26)),
        ]
        for label, rule, event_tz, expected_date in cases:
            with self.subTest(label):
                event = self.env['calendar.event'].create({
                    'name': 'Weekly Thursday',
                    'start': datetime(2023, 10, 5, 15, 0),
                    'stop': datetime(2023, 10, 5, 16, 0),
                })
                recurrence = self.env['calendar.recurrence'].create({
                    'base_event_id': event.id,
                    'calendar_event_ids': [(4, event.id)],
                    'event_tz': event_tz,
                    'rrule': rule,
                })
                self.assertEqual(recurrence.until, expected_date)


class TestRecurrenceRule(TransactionCase):

    def test_daily_count(self):
        recurrence = self.env['calendar.recurrence'].create({
            'rrule_type': 'daily',
            'interval': 2,
            'count': 3,
            'event_tz': 'UTC',
        })
        self.assertEqual(recurrence.name, 'Every 2 Days for 3 events')

    def test_daily_until(self):
        recurrence = self.env['calendar.recurrence'].create({
            'rrule_type': 'daily',
            'interval': 2,
            'end_type': 'end_date',
            'until': datetime(2024, 11, 15),
            'event_tz': 'UTC',
        })
        self.assertEqual(recurrence.name, 'Every 2 Days until 2024-11-15')

    def test_daily_none(self):
        recurrence = self.env['calendar.recurrence'].create({
            'rrule_type': 'daily',
            'interval': 2,
            'end_type': '',
            'event_tz': 'UTC',
        })
        self.assertEqual(recurrence.name, 'Every 2 Days')

    def test_weekly_count(self):
        """ Every week, on Tuesdays, for 3 occurences """
        recurrence = self.env['calendar.recurrence'].create({
            'rrule_type': 'weekly',
            'tue': True,
            'wed': True,
            'interval': 2,
            'count': 3,
            'event_tz': 'UTC',
        })
        self.assertEqual(recurrence.name, 'Every 2 Weeks on Tuesday, Wednesday for 3 events')

    def test_weekly_until(self):
        """ Every week, on Tuesdays, for 3 occurences """
        recurrence = self.env['calendar.recurrence'].create({
            'rrule_type': 'weekly',
            'tue': True,
            'wed': True,
            'interval': 2,
            'end_type': 'end_date',
            'until': datetime(2024, 11, 15),
            'event_tz': 'UTC',
        })
        self.assertEqual(recurrence.name, 'Every 2 Weeks on Tuesday, Wednesday until 2024-11-15')

    def test_weekly_none(self):
        """ Every week, on Tuesdays, for 3 occurences """
        recurrence = self.env['calendar.recurrence'].create({
            'rrule_type': 'weekly',
            'tue': True,
            'wed': True,
            'interval': 2,
            'end_type': '',
            'event_tz': 'UTC',
        })
        self.assertEqual(recurrence.name, 'Every 2 Weeks on Tuesday, Wednesday')

    def test_monthly_count_by_day(self):
        recurrence = self.env['calendar.recurrence'].create({
            'rrule_type': 'monthly',
            'interval': 2,
            'month_by': 'day',
            'byday': '1',
            'weekday': 'MON',
            'end_type': 'count',
            'count': 3,
            'event_tz': 'UTC',
        })
        self.assertEqual(recurrence.name, 'Every 2 Months on the First Monday for 3 events')

    def test_monthly_until_by_day(self):
        recurrence = self.env['calendar.recurrence'].create({
            'rrule_type': 'monthly',
            'interval': 2,
            'month_by': 'day',
            'byday': '1',
            'weekday': 'MON',
            'end_type': 'end_date',
            'until': datetime(2024, 11, 15),
            'event_tz': 'UTC',
        })
        self.assertEqual(recurrence.name, 'Every 2 Months on the First Monday until 2024-11-15')

    def test_monthly_none_by_day(self):
        recurrence = self.env['calendar.recurrence'].create({
            'rrule_type': 'monthly',
            'interval': 2,
            'month_by': 'day',
            'byday': '1',
            'weekday': 'MON',
            'end_type': '',
            'event_tz': 'UTC',
        })
        self.assertEqual(recurrence.name, 'Every 2 Months on the First Monday')

    def test_monthly_count_by_date(self):
        recurrence = self.env['calendar.recurrence'].create({
            'rrule_type': 'monthly',
            'interval': 2,
            'month_by': 'date',
            'day': 27,
            'weekday': 'MON',
            'end_type': 'count',
            'count': 3,
            'event_tz': 'UTC',
        })
        self.assertEqual(recurrence.name, 'Every 2 Months day 27 for 3 events')

    def test_monthly_until_by_date(self):
        recurrence = self.env['calendar.recurrence'].create({
            'rrule_type': 'monthly',
            'interval': 2,
            'month_by': 'date',
            'day': 27,
            'weekday': 'MON',
            'end_type': 'end_date',
            'until': datetime(2024, 11, 15),
            'event_tz': 'UTC',
        })
        self.assertEqual(recurrence.name, 'Every 2 Months day 27 until 2024-11-15')

    def test_monthly_none_by_date(self):
        recurrence = self.env['calendar.recurrence'].create({
            'rrule_type': 'monthly',
            'interval': 2,
            'month_by': 'date',
            'day': 27,
            'weekday': 'MON',
            'end_type': '',
            'event_tz': 'UTC',
        })
        self.assertEqual(recurrence.name, 'Every 2 Months day 27')

    def test_yearly_count(self):
        recurrence = self.env['calendar.recurrence'].create({
            'rrule_type': 'yearly',
            'interval': 2,
            'count': 3,
            'event_tz': 'UTC',
        })
        self.assertEqual(recurrence.name, 'Every 2 Years for 3 events')

    def test_yearly_until(self):
        recurrence = self.env['calendar.recurrence'].create({
            'rrule_type': 'yearly',
            'interval': 2,
            'end_type': 'end_date',
            'until': datetime(2024, 11, 15),
            'event_tz': 'UTC',
        })
        self.assertEqual(recurrence.name, 'Every 2 Years until 2024-11-15')

    def test_yearly_none(self):
        recurrence = self.env['calendar.recurrence'].create({
            'rrule_type': 'yearly',
            'interval': 2,
            'end_type': '',
            'event_tz': 'UTC',
        })
        self.assertEqual(recurrence.name, 'Every 2 Years')
