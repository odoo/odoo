from datetime import date, datetime

from odoo.addons.test_resource.tests.common import TestResourceCommon


class TestResMixin(TestResourceCommon):

    def test_adjust_calendar(self):
        # Calendar:
        # Tuesdays 8-16
        # Fridays 8-13 and 16-23
        result = self.john._adjust_to_calendar(
            self.datetime_tz(2020, 4, 3, 9, 0, 0, tzinfo=self.john.tz),
            self.datetime_tz(2020, 4, 3, 14, 0, 0, tzinfo=self.john.tz),
        )
        self.assertEqual(result[self.john], (
            self.datetime_tz(2020, 4, 3, 8, 0, 0, tzinfo=self.john.tz),
            self.datetime_tz(2020, 4, 3, 13, 0, 0, tzinfo=self.john.tz),
        ))

        result = self.john._adjust_to_calendar(
            self.datetime_tz(2020, 4, 3, 13, 1, 0, tzinfo=self.john.tz),
            self.datetime_tz(2020, 4, 3, 14, 0, 0, tzinfo=self.john.tz),
        )
        self.assertEqual(result[self.john], (
            self.datetime_tz(2020, 4, 3, 16, 0, 0, tzinfo=self.john.tz),
            self.datetime_tz(2020, 4, 3, 23, 0, 0, tzinfo=self.john.tz),
        ))

        result = self.john._adjust_to_calendar(
            self.datetime_tz(2020, 4, 4, 9, 0, 0, tzinfo=self.john.tz),  # both a day without attendance
            self.datetime_tz(2020, 4, 4, 14, 0, 0, tzinfo=self.john.tz),
        )
        self.assertEqual(result[self.john], (None, None))

        result = self.john._adjust_to_calendar(
            self.datetime_tz(2020, 4, 3, 8, 0, 0, tzinfo=self.john.tz),
            self.datetime_tz(2020, 4, 4, 14, 0, 0, tzinfo=self.john.tz),  # day without attendance
        )
        self.assertEqual(result[self.john], (
            self.datetime_tz(2020, 4, 3, 8, 0, 0, tzinfo=self.john.tz),
            self.datetime_tz(2020, 4, 3, 23, 0, 0, tzinfo=self.john.tz),
        ))

        result = self.john._adjust_to_calendar(
            self.datetime_tz(2020, 4, 2, 8, 0, 0, tzinfo=self.john.tz),  # day without attendance
            self.datetime_tz(2020, 4, 3, 14, 0, 0, tzinfo=self.john.tz),
        )
        self.assertEqual(result[self.john], (
            self.datetime_tz(2020, 4, 3, 8, 0, 0, tzinfo=self.john.tz),
            self.datetime_tz(2020, 4, 3, 13, 0, 0, tzinfo=self.john.tz),
        ))

        result = self.john._adjust_to_calendar(
            self.datetime_tz(2020, 3, 31, 0, 0, 0, tzinfo=self.john.tz),  # search between Tuesday and Thursday
            self.datetime_tz(2020, 4, 2, 23, 59, 59, tzinfo=self.john.tz),
        )
        self.assertEqual(result[self.john], (
            self.datetime_tz(2020, 3, 31, 8, 0, tzinfo=self.john.tz),
            self.datetime_tz(2020, 3, 31, 16, 0, tzinfo=self.john.tz),
        ))

        result = self.john._adjust_to_calendar(
            self.datetime_tz(2020, 3, 31, 0, 0, 0, tzinfo=self.john.tz),  # search between Tuesday and Friday
            self.datetime_tz(2020, 4, 3, 23, 59, 59, tzinfo=self.john.tz),
        )
        result = self.john._adjust_to_calendar(
            self.datetime_tz(2020, 3, 31, 8, 0, 0, tzinfo=self.john.tz),
            self.datetime_tz(2020, 4, 3, 23, 0, 0, tzinfo=self.john.tz),
        )
        # It should find the start and end within the search range
        result = self.paul._adjust_to_calendar(
            self.datetime_tz(2020, 4, 2, 2, 0, 0, tzinfo='UTC'),
            self.datetime_tz(2020, 4, 3, 1, 59, 59, tzinfo='UTC'),
        )

        self.assertEqual(result[self.paul], (
            self.datetime_tz(2020, 4, 2, 4, 0, tzinfo='UTC'),
            self.datetime_tz(2020, 4, 2, 18, 0, tzinfo='UTC'),
        ), "It should have found the start and end of the shift on the same day on April 2nd, 2020")

    def test_adjust_calendar_timezone_before(self):
        # Calendar:
        # Every day 8-16
        self.jean.tz = 'Asia/Tokyo'
        self.calendar_jean.tz = 'Europe/Brussels'

        result = self.jean._adjust_to_calendar(
            self.datetime_tz(2020, 4, 1, 0, 0, 0, tzinfo='Asia/Tokyo'),
            self.datetime_tz(2020, 4, 1, 23, 59, 59, tzinfo='Asia/Tokyo'),
        )
        self.assertEqual(result[self.jean], (
            self.datetime_tz(2020, 4, 1, 8, 0, 0, tzinfo='Asia/Tokyo'),
            self.datetime_tz(2020, 4, 1, 16, 0, 0, tzinfo='Asia/Tokyo'),
        ), "It should have found a starting time the 1st")

    def test_adjust_calendar_timezone_after(self):
        # Calendar:
        # Tuesdays 8-16
        # Fridays 8-13 and 16-23
        tz = 'Europe/Brussels'
        self.john.tz = tz
        result = self.john._adjust_to_calendar(
            datetime(2020, 4, 2, 23, 0, 0),  # The previous day in UTC, but the 3rd in Europe/Brussels
            datetime(2020, 4, 3, 20, 0, 0),
        )
        self.assertEqual(result[self.john], (
            datetime(2020, 4, 3, 6, 0, 0),
            datetime(2020, 4, 3, 21, 0, 0),
        ), "It should have found a starting time the 3rd")

    def test_work_days_data(self):
        # Looking at Jean's calendar

        # Viewing it as Jean
        data = self.jean._get_work_days_data_batch(
            self.datetime_tz(2018, 4, 2, 0, 0, 0, tzinfo=self.jean.tz),
            self.datetime_tz(2018, 4, 6, 16, 0, 0, tzinfo=self.jean.tz),
        )[self.jean.id]
        self.assertEqual(data, {'days': 5, 'hours': 40})

        # Viewing it as Bob
        data = self.bob._get_work_days_data_batch(
            self.datetime_tz(2018, 4, 2, 0, 0, 0, tzinfo=self.bob.tz),
            self.datetime_tz(2018, 4, 6, 16, 0, 0, tzinfo=self.bob.tz),
        )[self.bob.id]
        self.assertEqual(data, {'days': 5, 'hours': 40})

        # Viewing it as Patel
        # Views from 2018/04/01 20:00:00 to 2018/04/06 12:00:00
        data = self.jean._get_work_days_data_batch(
            self.datetime_tz(2018, 4, 2, 0, 0, 0, tzinfo=self.patel.tz),
            self.datetime_tz(2018, 4, 6, 16, 0, 0, tzinfo=self.patel.tz),
        )[self.jean.id]
        self.assertEqual(data, {'days': 4.5, 'hours': 36})  # We see only 36 hours

        # Viewing it as John
        # Views from 2018/04/02 09:00:00 to 2018/04/07 02:00:00
        data = self.jean._get_work_days_data_batch(
            self.datetime_tz(2018, 4, 2, 0, 0, 0, tzinfo=self.john.tz),
            self.datetime_tz(2018, 4, 6, 16, 0, 0, tzinfo=self.john.tz),
        )[self.jean.id]
        # still showing as 5 days because of rounding, but we see only 39 hours
        self.assertEqual(data, {'days': 4.875, 'hours': 39})

        # Looking at John's calendar

        # Viewing it as Jean
        # Views from 2018/04/01 15:00:00 to 2018/04/06 14:00:00
        data = self.john._get_work_days_data_batch(
            self.datetime_tz(2018, 4, 2, 0, 0, 0, tzinfo=self.jean.tz),
            self.datetime_tz(2018, 4, 6, 23, 0, 0, tzinfo=self.jean.tz),
        )[self.john.id]
        self.assertEqual(data, {'days': 1.417, 'hours': 13})

        # Viewing it as Patel
        # Views from 2018/04/01 11:00:00 to 2018/04/06 10:00:00
        data = self.john._get_work_days_data_batch(
            self.datetime_tz(2018, 4, 2, 0, 0, 0, tzinfo=self.patel.tz),
            self.datetime_tz(2018, 4, 6, 23, 0, 0, tzinfo=self.patel.tz),
        )[self.john.id]
        self.assertEqual(data, {'days': 1.167, 'hours': 10})

        # Viewing it as John
        data = self.john._get_work_days_data_batch(
            self.datetime_tz(2018, 4, 2, 0, 0, 0, tzinfo=self.john.tz),
            self.datetime_tz(2018, 4, 6, 23, 0, 0, tzinfo=self.john.tz),
        )[self.john.id]
        self.assertEqual(data, {'days': 2, 'hours': 20})

        # using Jean as a timezone reference
        data = self.john._get_work_days_data_batch(
            self.datetime_tz(2018, 4, 2, 0, 0, 0, tzinfo=self.john.tz),
            self.datetime_tz(2018, 4, 6, 23, 0, 0, tzinfo=self.john.tz),
            calendar=self.calendar_jean,
        )[self.john.id]
        self.assertEqual(data, {'days': 5, 'hours': 40})

        # half days
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'half',
            'calendar_id': self.calendar_jean.id,
            'resource_id': self.jean.resource_id.id,
            'date_from': self.datetime_str(2018, 4, 2, 10, 0, 0, tzinfo=self.jean.tz),
            'date_to': self.datetime_str(2018, 4, 2, 14, 0, 0, tzinfo=self.jean.tz),
        })

        data = self.jean._get_work_days_data_batch(
            self.datetime_tz(2018, 4, 2, 0, 0, 0, tzinfo=self.jean.tz),
            self.datetime_tz(2018, 4, 6, 23, 0, 0, tzinfo=self.jean.tz),
        )[self.jean.id]
        self.assertEqual(data, {'days': 4.5, 'hours': 36})

        # using John as a timezone reference, leaves are outside attendances
        data = self.john._get_work_days_data_batch(
            self.datetime_tz(2018, 4, 2, 0, 0, 0, tzinfo=self.john.tz),
            self.datetime_tz(2018, 4, 6, 23, 0, 0, tzinfo=self.john.tz),
            calendar=self.calendar_jean,
        )[self.john.id]
        self.assertEqual(data, {'days': 5, 'hours': 40})

        leave.unlink()

        # leave size 0
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'zero',
            'calendar_id': self.calendar_jean.id,
            'resource_id': False,
            'date_from': self.datetime_str(2018, 4, 2, 10, 0, 0, tzinfo=self.jean.tz),
            'date_to': self.datetime_str(2018, 4, 2, 10, 0, 0, tzinfo=self.jean.tz),
        })

        data = self.jean._get_work_days_data_batch(
            self.datetime_tz(2018, 4, 2, 0, 0, 0, tzinfo=self.jean.tz),
            self.datetime_tz(2018, 4, 6, 23, 0, 0, tzinfo=self.jean.tz),
        )[self.jean.id]
        self.assertEqual(data, {'days': 5, 'hours': 40})

        leave.unlink()

        # leave very small size
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'small',
            'calendar_id': self.calendar_jean.id,
            'resource_id': False,
            'date_from': self.datetime_str(2018, 4, 2, 10, 0, 0, tzinfo=self.jean.tz),
            'date_to': self.datetime_str(2018, 4, 2, 10, 0, 1, tzinfo=self.jean.tz),
        })

        data = self.jean._get_work_days_data_batch(
            self.datetime_tz(2018, 4, 2, 0, 0, 0, tzinfo=self.jean.tz),
            self.datetime_tz(2018, 4, 6, 23, 0, 0, tzinfo=self.jean.tz),
        )[self.jean.id]
        self.assertEqual(data['days'], 5)
        self.assertAlmostEqual(data['hours'], 40, 2)

    def test_leaves_days_data(self):
        # Jean takes a leave
        self.env['resource.calendar.leaves'].create({
            'name': 'Jean is visiting India',
            'calendar_id': self.jean.resource_calendar_id.id,
            'resource_id': self.jean.resource_id.id,
            'date_from': self.datetime_str(2018, 4, 10, 8, 0, 0, tzinfo=self.jean.tz),
            'date_to': self.datetime_str(2018, 4, 10, 16, 0, 0, tzinfo=self.jean.tz),
        })

        # John takes a leave for Jean
        self.env['resource.calendar.leaves'].create({
            'name': 'Jean is comming in USA',
            'calendar_id': self.jean.resource_calendar_id.id,
            'resource_id': self.jean.resource_id.id,
            'date_from': self.datetime_str(2018, 4, 12, 8, 0, 0, tzinfo=self.john.tz),
            'date_to': self.datetime_str(2018, 4, 12, 16, 0, 0, tzinfo=self.john.tz),
        })

        # Jean asks to see how much leave he has taken
        data = self.jean._get_leave_days_data_batch(
            self.datetime_tz(2018, 4, 9, 0, 0, 0, tzinfo=self.jean.tz),
            self.datetime_tz(2018, 4, 13, 23, 59, 59, tzinfo=self.jean.tz),
        )[self.jean.id]
        # Sees only 1 day and 8 hours because, as john is in UTC-7 the second leave is not in
        # the attendances of Jean
        self.assertEqual(data, {'days': 1, 'hours': 8})

        # Patel Asks to see when Jean has taken some leaves
        # Patel should see the same
        data = self.jean._get_leave_days_data_batch(
            self.datetime_tz(2018, 4, 9, 0, 0, 0, tzinfo=self.patel.tz),
            self.datetime_tz(2018, 4, 13, 23, 59, 59, tzinfo=self.patel.tz),
        )[self.jean.id]
        self.assertEqual(data, {'days': 1, 'hours': 8})

        # use Patel as a resource, jean's leaves are not visible
        datas = self.patel._get_leave_days_data_batch(
            self.datetime_tz(2018, 4, 9, 0, 0, 0, tzinfo=self.patel.tz),
            self.datetime_tz(2018, 4, 13, 23, 59, 59, tzinfo=self.patel.tz),
            calendar=self.calendar_jean,
        )[self.patel.id]
        self.assertEqual(datas['days'], 0)
        self.assertEqual(datas['hours'], 0)

        # Jean takes a leave for John
        # Gives 3 hours (3/8 of a day)
        self.env['resource.calendar.leaves'].create({
            'name': 'John is sick',
            'calendar_id': self.john.resource_calendar_id.id,
            'resource_id': self.john.resource_id.id,
            'date_from': self.datetime_str(2018, 4, 10, 0, 0, 0, tzinfo=self.jean.tz),
            'date_to': self.datetime_str(2018, 4, 10, 20, 0, 0, tzinfo=self.jean.tz),
        })

        # John takes a leave
        # Gives all day (12 hours)
        self.env['resource.calendar.leaves'].create({
            'name': 'John goes to holywood',
            'calendar_id': self.john.resource_calendar_id.id,
            'resource_id': self.john.resource_id.id,
            'date_from': self.datetime_str(2018, 4, 13, 7, 0, 0, tzinfo=self.john.tz),
            'date_to': self.datetime_str(2018, 4, 13, 18, 0, 0, tzinfo=self.john.tz),
        })

        # John asks how much leaves he has
        # He sees that he has only 15 hours of leave in his attendances
        data = self.john._get_leave_days_data_batch(
            self.datetime_tz(2018, 4, 9, 0, 0, 0, tzinfo=self.john.tz),
            self.datetime_tz(2018, 4, 13, 23, 59, 59, tzinfo=self.john.tz),
        )[self.john.id]
        self.assertEqual(data, {'days': 0.958, 'hours': 10})

        # half days
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'half',
            'calendar_id': self.calendar_jean.id,
            'resource_id': self.jean.resource_id.id,
            'date_from': self.datetime_str(2018, 4, 2, 10, 0, 0, tzinfo=self.jean.tz),
            'date_to': self.datetime_str(2018, 4, 2, 14, 0, 0, tzinfo=self.jean.tz),
        })

        data = self.jean._get_leave_days_data_batch(
            self.datetime_tz(2018, 4, 2, 0, 0, 0, tzinfo=self.jean.tz),
            self.datetime_tz(2018, 4, 6, 23, 0, 0, tzinfo=self.jean.tz),
        )[self.jean.id]
        self.assertEqual(data, {'days': 0.5, 'hours': 4})

        leave.unlink()

        # leave size 0
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'zero',
            'calendar_id': self.calendar_jean.id,
            'resource_id': False,
            'date_from': self.datetime_str(2018, 4, 2, 10, 0, 0, tzinfo=self.jean.tz),
            'date_to': self.datetime_str(2018, 4, 2, 10, 0, 0, tzinfo=self.jean.tz),
        })

        data = self.jean._get_leave_days_data_batch(
            self.datetime_tz(2018, 4, 2, 0, 0, 0, tzinfo=self.jean.tz),
            self.datetime_tz(2018, 4, 6, 23, 0, 0, tzinfo=self.jean.tz),
        )[self.jean.id]
        self.assertEqual(data, {'days': 0, 'hours': 0})

        leave.unlink()

        # leave very small size
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'small',
            'calendar_id': self.calendar_jean.id,
            'resource_id': False,
            'date_from': self.datetime_str(2018, 4, 2, 10, 0, 0, tzinfo=self.jean.tz),
            'date_to': self.datetime_str(2018, 4, 2, 10, 0, 1, tzinfo=self.jean.tz),
        })

        data = self.jean._get_leave_days_data_batch(
            self.datetime_tz(2018, 4, 2, 0, 0, 0, tzinfo=self.jean.tz),
            self.datetime_tz(2018, 4, 6, 23, 0, 0, tzinfo=self.jean.tz),
        )[self.jean.id]
        self.assertEqual(data['days'], 0)
        self.assertAlmostEqual(data['hours'], 0, 2)

        leave.unlink()

    def test_list_leaves(self):
        jean_leave = self.env['resource.calendar.leaves'].create({
            'name': "Jean's son is sick",
            'calendar_id': self.jean.resource_calendar_id.id,
            'resource_id': False,
            'date_from': self.datetime_str(2018, 4, 10, 0, 0, 0, tzinfo=self.jean.tz),
            'date_to': self.datetime_str(2018, 4, 10, 23, 59, 59, tzinfo=self.jean.tz),
        })

        leaves = self.jean.list_leaves(
            self.datetime_tz(2018, 4, 9, 0, 0, 0, tzinfo=self.jean.tz),
            self.datetime_tz(2018, 4, 13, 23, 59, 59, tzinfo=self.jean.tz),
        )
        self.assertEqual(leaves, [(date(2018, 4, 10), 8, jean_leave)])

        # half days
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'half',
            'calendar_id': self.jean.resource_calendar_id.id,
            'resource_id': self.jean.resource_id.id,
            'date_from': self.datetime_str(2018, 4, 2, 10, 0, 0, tzinfo=self.jean.tz),
            'date_to': self.datetime_str(2018, 4, 2, 14, 0, 0, tzinfo=self.jean.tz),
        })

        leaves = self.jean.list_leaves(
            self.datetime_tz(2018, 4, 2, 0, 0, 0, tzinfo=self.jean.tz),
            self.datetime_tz(2018, 4, 6, 23, 0, 0, tzinfo=self.jean.tz),
        )
        self.assertEqual(leaves, [(date(2018, 4, 2), 4, leave)])

        leave.unlink()

        # very small size
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'small',
            'calendar_id': self.jean.resource_calendar_id.id,
            'resource_id': self.jean.resource_id.id,
            'date_from': self.datetime_str(2018, 4, 2, 10, 0, 0, tzinfo=self.jean.tz),
            'date_to': self.datetime_str(2018, 4, 2, 10, 0, 1, tzinfo=self.jean.tz),
        })

        leaves = self.jean.list_leaves(
            self.datetime_tz(2018, 4, 2, 0, 0, 0, tzinfo=self.jean.tz),
            self.datetime_tz(2018, 4, 6, 23, 0, 0, tzinfo=self.jean.tz),
        )
        self.assertEqual(len(leaves), 1)
        self.assertEqual(leaves[0][0], date(2018, 4, 2))
        self.assertAlmostEqual(leaves[0][1], 0, 2)
        self.assertEqual(leaves[0][2].id, leave.id)

        leave.unlink()

        # size 0
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'zero',
            'calendar_id': self.jean.resource_calendar_id.id,
            'resource_id': self.jean.resource_id.id,
            'date_from': self.datetime_str(2018, 4, 2, 10, 0, 0, tzinfo=self.jean.tz),
            'date_to': self.datetime_str(2018, 4, 2, 10, 0, 0, tzinfo=self.jean.tz),
        })

        leaves = self.jean.list_leaves(
            self.datetime_tz(2018, 4, 2, 0, 0, 0, tzinfo=self.jean.tz),
            self.datetime_tz(2018, 4, 6, 23, 0, 0, tzinfo=self.jean.tz),
        )
        self.assertEqual(leaves, [])

        leave.unlink()

    def test_list_work_time_per_day(self):
        working_time = self.john._list_work_time_per_day(
            self.datetime_tz(2018, 4, 9, 0, 0, 0, tzinfo=self.john.tz),
            self.datetime_tz(2018, 4, 13, 23, 59, 59, tzinfo=self.john.tz),
        )[self.john.id]
        self.assertEqual(working_time, [
            (date(2018, 4, 10), 8),
            (date(2018, 4, 13), 12),
        ])

        # change john's resource's timezone
        self.john.resource_id.tz = 'Europe/Brussels'
        self.assertEqual(self.john.tz, 'Europe/Brussels')
        self.assertEqual(self.calendar_john.tz, 'America/Los_Angeles')
        working_time = self.john._list_work_time_per_day(
            self.datetime_tz(2018, 4, 9, 0, 0, 0, tzinfo=self.john.tz),
            self.datetime_tz(2018, 4, 13, 23, 59, 59, tzinfo=self.john.tz),
        )[self.john.id]
        self.assertEqual(working_time, [
            (date(2018, 4, 10), 8),
            (date(2018, 4, 13), 12),
        ])

        # half days
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'small',
            'calendar_id': self.jean.resource_calendar_id.id,
            'resource_id': self.jean.resource_id.id,
            'date_from': self.datetime_str(2018, 4, 2, 10, 0, 0, tzinfo=self.jean.tz),
            'date_to': self.datetime_str(2018, 4, 2, 14, 0, 0, tzinfo=self.jean.tz),
        })

        working_time = self.jean._list_work_time_per_day(
            self.datetime_tz(2018, 4, 2, 0, 0, 0, tzinfo=self.jean.tz),
            self.datetime_tz(2018, 4, 6, 23, 0, 0, tzinfo=self.jean.tz),
        )[self.jean.id]
        self.assertEqual(working_time, [
            (date(2018, 4, 2), 4),
            (date(2018, 4, 3), 8),
            (date(2018, 4, 4), 8),
            (date(2018, 4, 5), 8),
            (date(2018, 4, 6), 8),
        ])

        leave.unlink()

        # very small size
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'small',
            'calendar_id': self.jean.resource_calendar_id.id,
            'resource_id': self.jean.resource_id.id,
            'date_from': self.datetime_str(2018, 4, 2, 10, 0, 0, tzinfo=self.jean.tz),
            'date_to': self.datetime_str(2018, 4, 2, 10, 0, 1, tzinfo=self.jean.tz),
        })

        working_time = self.jean._list_work_time_per_day(
            self.datetime_tz(2018, 4, 2, 0, 0, 0, tzinfo=self.jean.tz),
            self.datetime_tz(2018, 4, 6, 23, 0, 0, tzinfo=self.jean.tz),
        )[self.jean.id]
        self.assertEqual(len(working_time), 5)
        self.assertEqual(working_time[0][0], date(2018, 4, 2))
        self.assertAlmostEqual(working_time[0][1], 8, 2)

        leave.unlink()

        # size 0
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'zero',
            'calendar_id': self.jean.resource_calendar_id.id,
            'resource_id': self.jean.resource_id.id,
            'date_from': self.datetime_str(2018, 4, 2, 10, 0, 0, tzinfo=self.jean.tz),
            'date_to': self.datetime_str(2018, 4, 2, 10, 0, 0, tzinfo=self.jean.tz),
        })

        working_time = self.jean._list_work_time_per_day(
            self.datetime_tz(2018, 4, 2, 0, 0, 0, tzinfo=self.jean.tz),
            self.datetime_tz(2018, 4, 6, 23, 0, 0, tzinfo=self.jean.tz),
        )[self.jean.id]
        self.assertEqual(working_time, [
            (date(2018, 4, 2), 8),
            (date(2018, 4, 3), 8),
            (date(2018, 4, 4), 8),
            (date(2018, 4, 5), 8),
            (date(2018, 4, 6), 8),
        ])

        leave.unlink()
