# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from odoo.exceptions import UserError
from odoo.tests import Form
from odoo.tests.common import TransactionCase


class TestVariableResourceCalendar(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.variable_calendar, cls.fixed_calendar = cls.env['resource.calendar'].create([{
            'name': 'Test Variable Calendar',
            'calendar_type': 'variable',
        }, {
            'name': 'Test Fixed Calendar',
            'calendar_type': 'fixed',
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
                    'recurrency_interval': 2,
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

    def test_attendance_intervals_duration_based_domain_filter(self):
        self.variable_calendar.attendance_ids = [(5, 0, 0)] + [
            (0, 0, {'date': date(2026, 1, 5), 'duration_hours': hours, 'hour_from': 0, 'hour_to': 0})
            for hours in [2, 4, 6]
        ]
        att_2h, att_4h, att_6h = sorted(self.variable_calendar.attendance_ids, key=lambda a: a.duration_hours)

        tz = ZoneInfo('UTC')
        start_dt = datetime(2026, 1, 5, 0, 0, 0, tzinfo=tz)
        end_dt = datetime(2026, 1, 5, 23, 59, 59, tzinfo=tz)

        intervals = self.variable_calendar._attendance_intervals_batch(start_dt, end_dt, domain=[('duration_hours', '>', 3)])[False]

        intervals_by_attendance = {att: (start, end) for start, end, att in intervals}
        self.assertEqual(len(intervals_by_attendance), 2, "Only the 4h and 6h attendances match the domain; the 2h one is filtered out")
        self.assertNotIn(att_2h, intervals_by_attendance, "The 2h attendance is filtered out by the domain")

        self.assertEqual(
            intervals_by_attendance[att_4h],
            (datetime(2026, 1, 5, 8, 0, tzinfo=tz), datetime(2026, 1, 5, 12, 0, tzinfo=tz)),
            "The 4h interval must stay at 08:00-12:00 (after the filtered-out 2h line)",
        )
        self.assertEqual(
            intervals_by_attendance[att_6h],
            (datetime(2026, 1, 5, 12, 0, tzinfo=tz), datetime(2026, 1, 5, 18, 0, tzinfo=tz)),
            "The 6h interval must stay at 12:00-18:00",
        )

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

        self.fixed_calendar.attendance_ids.filtered(lambda a: a.dayofweek == '1').unlink()
        attendance = self.env['resource.calendar.attendance'].create({
            'calendar_id': self.fixed_calendar.id,
            'dayofweek': '1',
            'hour_from': 8,
            'hour_to': 17,
        })
        self.assertEqual(attendance.dayofweek, '1', "Attendance with no date should keep the manually set dayofweek")

    def test_change_calendar_type(self):
        calendar = self.env['resource.calendar'].create({
            'name': 'Test Attendance Unlinking',
            # By default it should be fixed schedule type
        })
        self.assertGreaterEqual(len(calendar.attendance_ids), 5, "Should have default attendances created.")

        with Form(calendar) as calendar_form:
            # Should NOT raise an error.
            calendar_form.calendar_type = 'variable'

        self.assertEqual(len(calendar.attendance_ids), 0, "Changing schedule type should unlink attendances of the other type")

        self.env['resource.calendar.attendance'].create({
            'calendar_id': calendar.id,
            'date': date(2025, 1, 1),
            'hour_from': 8,
            'hour_to': 17,
        })
        calendar.calendar_type = 'fixed'
        self.assertEqual(len(calendar.attendance_ids), 0, "Changing schedule type should unlink attendances of the other type")

        calendar = self.env['resource.calendar'].create({
            'name': 'Test Attendance Unlinking 2',
            'calendar_type': 'variable',
        })
        self.assertEqual(len(calendar.attendance_ids), 0, "Variable calendar should not have default attendances created.")

    def setup_collision(self):
        """
        DB = Duration Based; TB = Time Based

        R1 : 1d + 2025-01-02  -  duration: 2h; hour_from: 6h; hour_to: 8h; until: 2025-01-25;
        R2 : 1w + 2025-01-01  -  duration: 8h; hour_from: 8h; hour_to: 16h; until: 2025-01-31;
        R4 : 2d + 2025-01-03  -  duration: 1h; hour_from: 16h; hour_to: 17h;
        R8 : 0  + 2025-01-26  -  duration: 2h;

        2025-01 -----
        S|M|T|W|T|F|S
              2 9 5 1
        5 1 5 3 5 1 5
        1 5 1 7 1 5 1
        5 1 5 3 5 1 5
        8 4 8 6 8 4
        """

        self.variable_calendar.attendance_ids = [(5, 0, 0),
            (0, 0, {
                'hour_from': 6,
                'hour_to': 8,
                'recurrency': True,
                'date': "2025-01-02",
                'recurrency_interval': 1,
                'recurrency_type': "days",
                'recurrency_until': "2025-01-25",
            }),
            (0, 0, {
                'hour_from': 8,
                'hour_to': 16,
                'recurrency': True,
                'date': "2025-01-01",
                'recurrency_interval': 1,
                'recurrency_type': "weeks",
                'recurrency_until': "2025-01-31",
            }),
            (0, 0, {
                'hour_from': 16,
                'hour_to': 17,
                'recurrency': True,
                'date': "2025-01-03",
                'recurrency_interval': 2,
                'recurrency_type': "days",
            }),
            (0, 0, {
                'duration_hours': 2,
                'recurrency': True,
                'date': "2025-01-26",
                'recurrency_interval': 2,
                'recurrency_type': "days",
            }),
        ]

    def test_collision_overlap_adhoc_recurrence(self):
        self.setup_collision()
        with self.assertRaises(UserError):
            self.env["resource.calendar.attendance"].create([
                {
                    'calendar_id': self.variable_calendar.id,
                    'hour_from': 7,
                    'hour_to': 9,
                    'date': '2025-01-08',
                },
            ])

    def test_collision_overlap_recurrence_recurrence(self):
        self.setup_collision()
        with self.assertRaises(UserError):
            self.env["resource.calendar.attendance"].create([
                {
                    'calendar_id': self.variable_calendar.id,
                    'hour_from': 7,
                    'hour_to': 9,
                    'recurrency': True,
                    'recurrency_interval': 1,
                    'recurrency_type': "weeks",
                    'date': '2025-01-08',
                },
            ])

    def test_collision_overlap_adhoc_adhoc(self):
        self.env["resource.calendar.attendance"].create([
            {
                'calendar_id': self.variable_calendar.id,
                'hour_from': 7,
                'hour_to': 9,
                'date': '2024-12-31',
            },
        ])
        with self.assertRaises(UserError):
            self.env["resource.calendar.attendance"].create([
                {
                    'calendar_id': self.variable_calendar.id,
                    'hour_from': 8,
                    'hour_to': 10,
                    'date': '2024-12-31',
                },
            ])

    def test_collision_overlap_recurrence_adhoc(self):
        self.env["resource.calendar.attendance"].create([
            {
                'calendar_id': self.variable_calendar.id,
                'hour_from': 7,
                'hour_to': 9,
                'recurrency': True,
                'recurrency_interval': 1,
                'recurrency_type': "days",
                'date': '2024-12-01',
            },
        ])
        with self.assertRaises(UserError):
            self.env["resource.calendar.attendance"].create([
                {
                    'calendar_id': self.variable_calendar.id,
                    'hour_from': 8,
                    'hour_to': 10,
                    'date': '2024-12-31',
                },
            ])

    def test_collision_duration_adhoc_on_3recurrences(self):
        """
        Adhoc that can make a day with multiple recurrence collision the total duration exceed 24h
        R1: 2h
        R2: 8h
        R3: 1h
        On 2025-01-15: R123 = 11h => +13h not possible
        """
        self.setup_collision()
        self.variable_calendar.attendance_ids.duration_based = True
        with self.assertRaises(UserError):
            self.env["resource.calendar.attendance"].create([
                {
                    'calendar_id': self.variable_calendar.id,
                    'duration_hours': 13.1,
                    'date': '2025-01-15',
                },
            ])
        self.env["resource.calendar.attendance"].create([
            {
                'calendar_id': self.variable_calendar.id,
                'duration_hours': 13,
                'date': '2025-01-15',
            },
        ])

    def test_collision_duration_recurrency_on_3recurrences(self):
        """
        Adhoc that can make a day with multiple recurrence collision the total duration exceed 24h
        R1: 2h
        R2: 8h
        R3: 1h
        On 2025-01-15: R123 = 11h => +13h not possible
        """
        self.setup_collision()
        self.variable_calendar.attendance_ids.duration_based = True
        with self.assertRaises(UserError):
            self.env["resource.calendar.attendance"].create([
                {
                    'calendar_id': self.variable_calendar.id,
                    'duration_hours': 13.1,
                    'recurrency': True,
                    'recurrency_interval': 1,
                    'recurrency_type': 'days',
                    'date': '2025-01-12',
                },
            ])
        self.env["resource.calendar.attendance"].create([
            {
                'calendar_id': self.variable_calendar.id,
                'duration_hours': 13,
                'recurrency': True,
                'recurrency_interval': 1,
                'recurrency_type': 'days',
                'date': '2025-01-12',
            },
        ])

    def test_exclusion_first_occurence(self):
        date_to_exclude = date(2025, 1, 1)
        recurrency = self.env["resource.calendar.attendance"].create([{
            'calendar_id': self.variable_calendar.id,
            'duration_hours': 12,
            'recurrency': True,
            'recurrency_interval': 1,
            'recurrency_type': 'days',
            'date': date_to_exclude,
        }])
        recurrency.exclude_occurence('2025-01-01')
        result = self.variable_calendar.attendance_ids._filter_by_date(date_to_exclude)
        self.assertEqual(len(result), 0)

    def test_exclusion_allows_new_adhoc_on_excluded_date(self):
        """Excluding an occurrence should allow a new adhoc attendance to overlap that date without raising"""
        recurrency = self.env["resource.calendar.attendance"].create({
            'calendar_id': self.variable_calendar.id,
            'hour_from': 8,
            'hour_to': 12,
            'recurrency': True,
            'recurrency_interval': 1,
            'recurrency_type': 'days',
            'date': date(2025, 1, 1),
        })
        recurrency.exclude_occurence('2025-01-05')

        # 2025-01-05 overlaps R1's time range (8-12) but its occurrence is excluded → no error
        self.env["resource.calendar.attendance"].create({
            'calendar_id': self.variable_calendar.id,
            'hour_from': 9,
            'hour_to': 11,
            'date': date(2025, 1, 5),
        })

    def test_exclusion_allows_new_recurrence_on_excluded_date(self):
        """Excluding an occurrence should allow a new recurrence whose only conflicting date is the excluded one"""
        recurrency = self.env["resource.calendar.attendance"].create({
            'calendar_id': self.variable_calendar.id,
            'hour_from': 8,
            'hour_to': 12,
            'recurrency': True,
            'recurrency_interval': 1,
            'recurrency_type': 'days',
            'date': date(2025, 1, 1),
            'recurrency_until': date(2025, 1, 10),
        })
        recurrency.exclude_occurence('2025-01-05')

        # New recurrence scoped to 2025-01-05 only (recurrency_until == date): its sole occurrence
        # overlaps R1's time range (8-12) but that date is excluded → no error
        self.env["resource.calendar.attendance"].create({
            'calendar_id': self.variable_calendar.id,
            'hour_from': 9,
            'hour_to': 11,
            'recurrency': True,
            'recurrency_interval': 1,
            'recurrency_type': 'days',
            'date': date(2025, 1, 5),
            'recurrency_until': date(2025, 1, 5),
        })

    def test_recurrency_count_one_occurrence(self):
        """Test that setting recurrency_count to 1 computes recurrency_until equal to the attendance date."""
        attendance = self.env["resource.calendar.attendance"].create({
            'calendar_id': self.variable_calendar.id,
            'date': date(2025, 3, 10),
            'hour_from': 8,
            'hour_to': 12,
            'recurrency': True,
            'recurrency_interval': 1,
            'recurrency_type': 'weeks',
            'recurrency_end_type': 'times',
            'recurrency_count': 1,
        })
        self.assertEqual(attendance.recurrency_until, date(2025, 3, 10),
            "With 1 occurrence, recurrency_until should equal the attendance date")

    def test_create_ad_hoc_on_single_occurrence_recurrency(self):
        """create_ad_hoc on the first (and only) occurrence of a recurrency: exclude_occurence
        unlinks the original record, so the new adhoc attendance must still be created from the
        previously-captured data instead of copying the (now deleted) source."""
        recurrency = self.env["resource.calendar.attendance"].create({
            'calendar_id': self.variable_calendar.id,
            'hour_from': 8,
            'hour_to': 12,
            'recurrency': True,
            'recurrency_interval': 1,
            'recurrency_type': 'days',
            'date': date(2025, 1, 5),
            'recurrency_end_type': 'date',
            'recurrency_until': date(2025, 1, 5),
        })
        recurrency_id = recurrency.id

        adhoc = recurrency.create_ad_hoc('2025-01-05', {'hour_from': 9, 'hour_to': 11})

        self.assertTrue(adhoc.exists(), "The adhoc attendance must be created")
        self.assertFalse(self.env["resource.calendar.attendance"].browse(recurrency_id).exists(),
            "The original recurrency should have been unlinked by exclude_occurence")
        self.assertFalse(adhoc.recurrency, "The adhoc attendance must not be recurrent")
        self.assertEqual(adhoc.date, date(2025, 1, 5))
        self.assertEqual(adhoc.hour_from, 9)
        self.assertEqual(adhoc.hour_to, 11)
        self.assertEqual(adhoc.calendar_id, self.variable_calendar)

    def test_create_new_recurrency_drops_recurrency_until_when_end_type_not_date(self):
        """create_new_recurrency must drop the copied recurrency_until when the change switches
        recurrency_end_type away from 'date', so it is recomputed from the new end type."""
        recurrency = self.env["resource.calendar.attendance"].create({
            'calendar_id': self.variable_calendar.id,
            'hour_from': 8,
            'hour_to': 12,
            'recurrency': True,
            'recurrency_interval': 1,
            'recurrency_type': 'days',
            'date': date(2025, 1, 1),
            'recurrency_end_type': 'date',
            'recurrency_until': date(2025, 12, 31),
        })

        new_recurrency = recurrency.create_new_recurrency('2025-06-01', {
            'date': date(2025, 6, 1),
            'recurrency_end_type': 'times',
            'recurrency_count': 5,
        })

        self.assertTrue(new_recurrency.recurrency)
        self.assertEqual(new_recurrency.date, date(2025, 6, 1))
        self.assertEqual(new_recurrency.recurrency_end_type, 'times')
        self.assertEqual(new_recurrency.recurrency_count, 5)
        # 5 daily occurrences starting 2025-06-01 = until 2025-06-05, NOT the copied 2025-12-31
        self.assertEqual(new_recurrency.recurrency_until, date(2025, 6, 5),
            "recurrency_until should be recomputed from the new end type, not copied from the source")
        # Original recurrency stops the day before
        self.assertEqual(recurrency.recurrency_end_type, 'date')
        self.assertEqual(recurrency.recurrency_until, date(2025, 5, 31))

    def test_create_ad_hoc_uses_date_from_changes_not_arg(self):
        """When the frontend moves a recurrent occurrence and saves it as an adhoc, the arg date
        identifies the occurrence to exclude from the recurrency; the new adhoc's date must come
        from `changes` (the moved-to date), not be forced to the arg date."""
        recurrency = self.env["resource.calendar.attendance"].create({
            'calendar_id': self.variable_calendar.id,
            'hour_from': 8,
            'hour_to': 12,
            'recurrency': True,
            'recurrency_interval': 1,
            'recurrency_type': 'days',
            'date': date(2025, 1, 1),
            'recurrency_end_type': 'date',
            'recurrency_until': date(2025, 1, 31),
        })

        adhoc = recurrency.create_ad_hoc('2025-01-10', {'date': date(2025, 1, 15), 'hour_from': 12, 'hour_to': 13})

        self.assertFalse(adhoc.recurrency)
        self.assertEqual(adhoc.date, date(2025, 1, 15),
            "adhoc date must come from `changes`, not from the arg date")
        self.assertIn('2025-01-10', recurrency.recurrency_excluded_occurences or [],
            "the arg date must be excluded from the source recurrency")
        self.assertNotIn('2025-01-15', recurrency.recurrency_excluded_occurences or [],
            "the moved-to date must NOT be excluded from the source recurrency")

    def test_create_new_recurrency_uses_date_from_changes_not_arg(self):
        """When the frontend moves a recurrent occurrence and saves it as the start of a new
        recurrency, the arg date is used only to stop the source recurrency the day before; the
        new recurrency's start date must come from `changes` (the moved-to date)."""
        recurrency = self.env["resource.calendar.attendance"].create({
            'calendar_id': self.variable_calendar.id,
            'hour_from': 8,
            'hour_to': 12,
            'recurrency': True,
            'recurrency_interval': 1,
            'recurrency_type': 'days',
            'date': date(2025, 1, 1),
            'recurrency_end_type': 'date',
            'recurrency_until': date(2025, 1, 31),
        })

        new_recurrency = recurrency.create_new_recurrency('2025-01-10', {
            'date': date(2025, 1, 15),
            'hour_from': 9,
            'hour_to': 11,
        })

        self.assertTrue(new_recurrency.recurrency)
        self.assertEqual(new_recurrency.date, date(2025, 1, 15),
            "new recurrency start date must come from `changes`, not from the arg date")
        self.assertEqual(new_recurrency.hour_from, 9)
        self.assertEqual(new_recurrency.hour_to, 11)
        self.assertEqual(recurrency.recurrency_until, date(2025, 1, 9),
            "source recurrency must stop the day before the arg date, not the moved-to date")

    def test_convert_single_occurrence_recurrencies(self):
        shared_data = {
            'calendar_id': self.variable_calendar.id,
            'hour_from': 8,
            'hour_to': 12,
            'recurrency': True,
            'recurrency_interval': 1,
            'recurrency_type': 'weeks',
        }

        single, forever, multi = self.env['resource.calendar.attendance'].create([{
            **shared_data,
            'date': date(2025, 1, 1),
            'recurrency_end_type': 'date',
            'recurrency_until': date(2025, 1, 8),
            'recurrency_excluded_occurences': ['2025-01-08'],
        }, {
            **shared_data,
            'date': date(2025, 1, 2),
            'recurrency_end_type': 'forever',
            'recurrency_excluded_occurences': ['2025-01-09', '2025-01-16'],
        }, {
            **shared_data,
            'date': date(2025, 1, 3),
            'recurrency_end_type': 'date',
            'recurrency_until': date(2025, 1, 17),
            'recurrency_excluded_occurences': ['2025-01-10'],
        }])

        self.variable_calendar._convert_single_occurrence_recurrencies()

        self.assertFalse(single.recurrency, "All-excluded recurrency should be converted to ad-hoc")
        self.assertFalse(single.recurrency_excluded_occurences, "Exclusion list should be cleared after conversion")

        self.assertTrue(forever.recurrency, "Forever recurrency must not be converted")
        self.assertTrue(multi.recurrency, "Recurrency with remaining occurrences must not be converted")

    def test_calendar_clean_excluded_dates(self):
        recurrency = self.env['resource.calendar.attendance'].create({
            'calendar_id': self.variable_calendar.id,
            'date': date(2026, 1, 1),
            'hour_from': 8,
            'hour_to': 12,
            'recurrency': True,
            'recurrency_interval': 1,
            'recurrency_type': 'days',
            'recurrency_end_type': 'forever',
            'recurrency_excluded_occurences': ['2026-01-02', '2026-01-04', '2026-05-09'],
        })

        recurrency.write({
            'date': date(2026, 1, 3),
            'recurrency_interval': 2,
            'recurrency_end_type': 'times',
            'recurrency_count': 2,
        })

        self.variable_calendar._clean_excluded_occurrences()

        self.assertFalse(recurrency.recurrency_excluded_occurences, "Exclusion list should be cleaned of dates before the new start date, after until date and not falling in recurrency")

    def test_exclude_first_occurrence_skips_existing_excluded_days(self):
        recurrency = self.env['resource.calendar.attendance'].create({
            'calendar_id': self.variable_calendar.id,
            'hour_from': 8,
            'hour_to': 16,
            'recurrency': True,
            'recurrency_interval': 1,
            'recurrency_type': 'days',
            'recurrency_end_type': 'forever',
            'date': date(2026, 2, 1),
            'recurrency_excluded_occurences': ['2026-02-02', '2026-02-03'],
        })

        recurrency.exclude_occurence('2026-02-01')

        self.assertEqual(recurrency.date, date(2026, 2, 4), "recurrency.date should skip past the already-excluded days to the next real attendance")
