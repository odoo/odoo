# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from odoo.tests import Form
from odoo.tests.common import TransactionCase


class TestVariableResourceCalendar(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.variable_calendar, cls.fixed_calendar = cls.env['resource.calendar'].create([{
            'name': 'Test Variable Calendar',
            'schedule_type': 'variable',
        }, {
            'name': 'Test Fixed Calendar',
            'schedule_type': 'fixed',
        }])

    def test_attendance_intervals_batch_variable_calendar(self):
        """Test that _attendance_intervals_batch returns only attendances in the selected date range"""
        start = date(1, 1, 1)
        self.variable_calendar.attendance_ids = [(5, 0, 0)] + [
            (0, 0,
                {
                    'date': start + timedelta(days=day, weeks=week),
                    'hour_from': hour,
                    'hour_to': hour + 4,
                    'recurrency': True,
                    'recurrency_type': 'weeks',
                    'interval': 2,
                })
            for day in range(5)
            for week in range(2)
            for hour in [8, 13]
        ]

        tz = ZoneInfo('UTC')
        start_dt = datetime(2025, 11, 10, 0, 0, 0, tzinfo=tz)
        end_dt = datetime(2025, 11, 20, 23, 59, 59, tzinfo=tz)

        intervals = self.variable_calendar._attendance_intervals_batch(start_dt, end_dt)[False]

        # Should only take attendance with date between Nov 10 and Nov 20 (18 attendances)
        # Attendances based on dayofweek are ignored in variable calendars
        self.assertEqual(len(intervals), 18, "Should have 18 attendance in range")
        self.assertEqual(intervals._items[0][0:2], (datetime(2025, 11, 10, 8, 0, tzinfo=tz), datetime(2025, 11, 10, 12, 0, tzinfo=tz)))
        self.assertEqual(intervals._items[-1][0:2], (datetime(2025, 11, 20, 13, 0, tzinfo=tz), datetime(2025, 11, 20, 17, 0, tzinfo=tz)))

    def test_copy_from_week(self):
        """Test copying attendances from one week to another"""
        source_date = date(2026, 1, 7)
        target_date = date(2026, 1, 14)

        source_monday = date(2026, 1, 5)
        self.variable_calendar.attendance_ids = [(5, 0, 0)] + [
            (0, 0,
                {
                    'date': source_monday + timedelta(days=weekday),
                    'hour_from': 8,
                    'hour_to': 17,
                })
            for weekday in range(0, 5)
        ]

        self.assertEqual(len(self.variable_calendar.attendance_ids.filtered_domain([
            ('date', '>=', date(2026, 1, 12)),
            ('date', '<=', date(2026, 1, 18)),
        ])), 0, "Should have 0 attendances in target week")

        self.variable_calendar.copy_from(source_date, target_date)

        target_attendances = self.variable_calendar.attendance_ids.filtered_domain([
            ('date', '>=', date(2026, 1, 12)),
            ('date', '<=', date(2026, 1, 18)),
        ])

        self.assertEqual(len(target_attendances), 5, "Should have 5 attendances in target week")

        target_monday = date(2026, 1, 12)
        for weekday in range(0, 5):
            att_date = target_monday + timedelta(days=weekday)
            matching_atts = target_attendances.filtered(lambda att: att.date == att_date and att.hour_from == 8 and att.hour_to == 17)
            self.assertEqual(len(matching_atts), 1, f"Should have attendance on {att_date} from 8 to 17")
        self.assertFalse(target_attendances.filtered(lambda att: int(att.dayofweek) >= 5), "Should have no attendance on weekends")

    def test_dayofweek_compute(self):
        """Test that the dayofweek is correctly computed based on the date"""
        attendance = self.env['resource.calendar.attendance'].create({
            'calendar_id': self.variable_calendar.id,
            'date': date(1, 1, 5),  # This is a Friday
            'hour_from': 8,
            'hour_to': 17,
        })
        self.assertEqual(attendance.dayofweek, '4', "Attendance on Friday should have dayofweek 4")

        attendance.date = date(1, 1, 3)  # This is a Wednesday
        self.assertEqual(attendance.dayofweek, '2', "Attendance on Wednesday should have dayofweek 2")

        attendance = self.env['resource.calendar.attendance'].create({
            'calendar_id': self.fixed_calendar.id,
            'dayofweek': '1',
            'hour_from': 8,
            'hour_to': 17,
        })
        self.assertEqual(attendance.dayofweek, '1', "Attendance with no date should keep the manually set dayofweek")

    def test_change_schedule_type(self):
        calendar = self.env['resource.calendar'].create({
            'name': 'Test Attendance Unlinking',
            # By default it should be fixed schedule type
        })
        self.assertGreaterEqual(len(calendar.attendance_ids), 5, "Should have default attendances created.")

        with Form(calendar) as calendar_form:
            # Should NOT raise an error.
            calendar_form.schedule_type = 'variable'

        self.assertEqual(len(calendar.attendance_ids), 0, "Changing schedule type should unlink attendances of the other type")

        self.env['resource.calendar.attendance'].create({
            'calendar_id': calendar.id,
            'date': date(2025, 1, 1),
            'hour_from': 8,
            'hour_to': 17,
        })
        calendar.schedule_type = 'fixed'
        self.assertEqual(len(calendar.attendance_ids), 0, "Changing schedule type should unlink attendances of the other type")

        calendar = self.env['resource.calendar'].create({
            'name': 'Test Attendance Unlinking 2',
            'schedule_type': 'variable',
        })
        self.assertEqual(len(calendar.attendance_ids), 0, "Variable calendar should not have default attendances created.")
