# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare
from odoo.tools.datetime import datetime, date
from odoo.addons.resource.tests.common import TestResourceCommon


class TestErrors(TestResourceCommon):
    def setUp(self):
        super(TestErrors, self).setUp()

    def test_create_negative_leave(self):
        # from > to
        with self.assertRaises(ValidationError):
            self.env['resource.calendar.leaves'].create({
                'name': 'error cannot return in the past',
                'resource_id': False,
                'calendar_id': self.calendar_1.id,
                'date_from': datetime(2018, 4, 3, 20, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
                'date_to': datetime(2018, 4, 3, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
            })

        with self.assertRaises(ValidationError):
            self.env['resource.calendar.leaves'].create({
                'name': 'error caused by timezones',
                'resource_id': False,
                'calendar_id': self.calendar_1.id,
                'date_from': datetime(2018, 4, 3, 10, 0, 0, tzinfo='UTC'),
                'date_to': datetime(2018, 4, 3, 12, 0, 0, tzinfo='Etc/GMT-6')
            })


class TestCalendar(TestResourceCommon):
    def setUp(self):
        super(TestCalendar, self).setUp()

    def test_get_work_hours_count(self):
        self.env['resource.calendar.leaves'].create({
            'name': 'Global Leave',
            'resource_id': False,
            'calendar_id': self.calendar_1.id,
            'date_from': datetime(2018, 4, 3, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
            'date_to': datetime(2018, 4, 3, 23, 59, 59, tzinfo=self.jean.resource_calendar_id.tz),
        })

        self.env['resource.calendar.leaves'].create({
            'name': 'leave for Jean',
            'calendar_id': self.calendar_1.id,
            'resource_id': self.jean.resource_id.id,
            'date_from': datetime(2018, 4, 5, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
            'date_to': datetime(2018, 4, 5, 23, 59, 59, tzinfo=self.jean.resource_calendar_id.tz),
        })

        hours = self.calendar_1.get_work_hours_count(datetime(2018, 4, 2, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
                                                    datetime(2018, 4, 6, 23, 59, 59, tzinfo=self.jean.resource_calendar_id.tz))

        self.assertEqual(hours, 32)

        hours = self.calendar_1.get_work_hours_count(datetime(2018, 4, 2, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
                                                    datetime(2018, 4, 6, 23, 59, 59, tzinfo=self.jean.resource_calendar_id.tz),
                                                    compute_leaves=False)
        self.assertEqual(hours, 40)

        # leave of size 0
        self.env['resource.calendar.leaves'].create({
            'name': 'zero_length',
            'calendar_id': self.calendar_2.id,
            'resource_id': False,
            'date_from': datetime(2018, 4, 3, 0, 0, 0, tzinfo=self.patel.resource_calendar_id.tz),
            'date_to': datetime(2018, 4, 3, 0, 0, 0, tzinfo=self.patel.resource_calendar_id.tz),
        })

        hours = self.calendar_2.get_work_hours_count(datetime(2018, 4, 2, 0, 0, 0, tzinfo=self.patel.resource_calendar_id.tz),
                                                     datetime(2018, 4, 6, 23, 59, 59, tzinfo=self.patel.resource_calendar_id.tz))

        self.assertEqual(hours, 35)

        # leave of medium size
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'zero_length',
            'calendar_id': self.calendar_2.id,
            'resource_id': False,
            'date_from': datetime(2018, 4, 3, 9, 0, 0, tzinfo=self.patel.resource_calendar_id.tz),
            'date_to': datetime(2018, 4, 3, 12, 0, 0, tzinfo=self.patel.resource_calendar_id.tz),
        })

        hours = self.calendar_2.get_work_hours_count(datetime(2018, 4, 2, 0, 0, 0, tzinfo=self.patel.resource_calendar_id.tz),
                                                     datetime(2018, 4, 6, 23, 59, 59, tzinfo=self.patel.resource_calendar_id.tz))

        self.assertEqual(hours, 32)

        leave.unlink()

        # leave of very small size
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'zero_length',
            'calendar_id': self.calendar_2.id,
            'resource_id': False,
            'date_from': datetime(2018, 4, 3, 0, 0, 0, tzinfo=self.patel.resource_calendar_id.tz),
            'date_to': datetime(2018, 4, 3, 0, 0, 10, tzinfo=self.patel.resource_calendar_id.tz),
        })

        hours = self.calendar_2.get_work_hours_count(datetime(2018, 4, 2, 0, 0, 0, tzinfo=self.patel.resource_calendar_id.tz),
                                                     datetime(2018, 4, 6, 23, 59, 59, tzinfo=self.patel.resource_calendar_id.tz))

        self.assertEqual(hours, 35)

        leave.unlink()

        # no timezone given should be converted to UTC
        # Should equal to a leave between 2018/04/03 10:00:00 and 2018/04/04 10:00:00
        self.env['resource.calendar.leaves'].create({
            'name': 'no timezone',
            'calendar_id': self.calendar_2.id,
            'resource_id': False,
            'date_from': datetime(2018, 4, 3, 4, 0, 0),
            'date_to': datetime(2018, 4, 4, 4, 0, 0),
        })

        hours = self.calendar_2.get_work_hours_count(datetime(2018, 4, 2, 0, 0, 0, tzinfo=self.patel.resource_calendar_id.tz),
                                                     datetime(2018, 4, 6, 23, 59, 59, tzinfo=self.patel.resource_calendar_id.tz))

        self.assertEqual(hours, 28)

        hours = self.calendar_2.get_work_hours_count(datetime(2018, 4, 2, 23, 59, 59, tzinfo=self.patel.resource_calendar_id.tz),
                                                     datetime(2018, 4, 2, 0, 0, 0, tzinfo=self.patel.resource_calendar_id.tz))

        self.assertEqual(hours, 0)

    def test_plan_hours(self):
        self.env['resource.calendar.leaves'].create({
            'name': 'global',
            'calendar_id': self.calendar_1.id,
            'resource_id': False,
            'date_from': datetime(2018, 4, 11, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
            'date_to': datetime(2018, 4, 11, 23, 59, 59, tzinfo=self.jean.resource_calendar_id.tz),
        })

        time = self.calendar_1.plan_hours(2, datetime(2018, 4, 10, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz), compute_leaves=False)
        self.assertEqual(time, datetime(2018, 4, 10, 10, 0, 0, tzinfo=self.jean.resource_calendar_id.tz))

        time = self.calendar_1.plan_hours(20, datetime(2018, 4, 10, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz), compute_leaves=False)
        self.assertEqual(time, datetime(2018, 4, 12, 12, 0, 0, tzinfo=self.jean.resource_calendar_id.tz))

        time = self.calendar_1.plan_hours(5, datetime(2018, 4, 10, 15, 0, 0, tzinfo=self.jean.resource_calendar_id.tz), compute_leaves=True)
        self.assertEqual(time, datetime(2018, 4, 12, 12, 0, 0, tzinfo=self.jean.resource_calendar_id.tz))

        # negative planning
        time = self.calendar_1.plan_hours(-10, datetime(2018, 4, 10, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz), compute_leaves=True)
        self.assertEqual(time, datetime(2018, 4, 6, 14, 0, 0, tzinfo=self.jean.resource_calendar_id.tz))

        # zero planning
        time = self.calendar_1.plan_hours(0, datetime(2018, 4, 10, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz), compute_leaves=True)
        self.assertEqual(time, datetime(2018, 4, 10, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz))

        # very small planning sets to the first hour it finds
        time = self.calendar_1.plan_hours(0.0002, datetime(2018, 4, 10, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz), compute_leaves=True)
        self.assertEqual(time, datetime(2018, 4, 10, 8, 0, 0, tzinfo=self.jean.resource_calendar_id.tz))

        # huge planning
        time = self.calendar_1.plan_hours(3000, datetime(2018, 4, 10, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz), compute_leaves=False)
        self.assertEqual(time, datetime(2019, 9, 16, 16, 0, 0, tzinfo=self.jean.resource_calendar_id.tz))

    def test_plan_days(self):
        self.env['resource.calendar.leaves'].create({
            'name': 'global',
            'calendar_id': self.calendar_1.id,
            'resource_id': False,
            'date_from': datetime(2018, 4, 11, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
            'date_to': datetime(2018, 4, 11, 23, 59, 59, tzinfo=self.jean.resource_calendar_id.tz),
        })

        time = self.calendar_1.plan_days(1, datetime(2018, 4, 10, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz), compute_leaves=False)
        self.assertEqual(time, datetime(2018, 4, 10, 16, 0, 0, tzinfo=self.jean.resource_calendar_id.tz))

        time = self.calendar_1.plan_days(3, datetime(2018, 4, 10, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz), compute_leaves=False)
        self.assertEqual(time, datetime(2018, 4, 12, 16, 0, 0, tzinfo=self.jean.resource_calendar_id.tz))

        time = self.calendar_1.plan_days(4, datetime(2018, 4, 10, 16, 0, 0, tzinfo=self.jean.resource_calendar_id.tz), compute_leaves=True)
        self.assertEqual(time, datetime(2018, 4, 17, 16, 0, 0, tzinfo=self.jean.resource_calendar_id.tz))

        # negative planning
        time = self.calendar_1.plan_days(-10, datetime(2018, 4, 10, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz), compute_leaves=True)
        self.assertEqual(time, datetime(2018, 3, 27, 8, 0, 0, tzinfo=self.jean.resource_calendar_id.tz))

        # zero planning
        time = self.calendar_1.plan_days(0, datetime(2018, 4, 10, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz), compute_leaves=True)
        self.assertEqual(time, datetime(2018, 4, 10, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz))

        # very small planning returns False in this case
        # TODO: decide if this behaviour is alright
        time = self.calendar_1.plan_days(0.0002, datetime(2018, 4, 10, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz), compute_leaves=True)
        self.assertEqual(time, False)

        # huge planning
        # TODO: Same as above
        # NOTE: Maybe allow to set a max limit to the method
        time = self.calendar_1.plan_days(3000, datetime(2018, 4, 10, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz), compute_leaves=False)
        self.assertEqual(time, False)


class TestResMixin(TestResourceCommon):
    def setUp(self):
        super(TestResMixin, self).setUp()

    def test_work_days_data(self):
        # Looking at Jean's calendar

        # Viewing it as Jean
        datas = self.jean.get_work_days_data(datetime(2018, 4, 2, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
                                             datetime(2018, 4, 6, 16, 0, 0, tzinfo=self.jean.resource_calendar_id.tz))
        self.assertEqual(datas['days'], 5)
        self.assertEqual(datas['hours'], 40)
        # Viewing it as Patel
        # Views from 2018/04/01 20:00:00 to 2018/04/06 12:00:00
        datas = self.jean.get_work_days_data(datetime(2018, 4, 2, 0, 0, 0, tzinfo=self.patel.resource_calendar_id.tz),
                                             datetime(2018, 4, 6, 16, 0, 0, tzinfo=self.patel.resource_calendar_id.tz))
        self.assertEqual(datas['days'], 4.5)
        self.assertEqual(datas['hours'], 36)  # We see only 36 hours
        # Viewing it as John
        # Views from 2018/04/02 09:00:00 to 2018/04/07 02:00:00
        datas = self.jean.get_work_days_data(datetime(2018, 4, 2, 0, 0, 0, tzinfo=self.john.resource_calendar_id.tz),
                                             datetime(2018, 4, 6, 16, 0, 0, tzinfo=self.john.resource_calendar_id.tz))
        self.assertEqual(datas['days'], 5)  # Still showing as 5 days because of rounding
        self.assertEqual(datas['hours'], 39)  # We see only 39 hours

        # Looking at John's calendar

        # Viewing it as Jean
        # Views from 2018/04/01 15:00:00 to 2018/04/06 14:00:00
        datas = self.john.get_work_days_data(datetime(2018, 4, 2, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
                                             datetime(2018, 4, 6, 23, 0, 0, tzinfo=self.jean.resource_calendar_id.tz))
        self.assertEqual(datas['days'], 1.5)
        self.assertEqual(datas['hours'], 13)

        # Viewing it as Patel
        # Views from 2018/04/01 11:00:00 to 2018/04/06 10:00:00
        datas = self.john.get_work_days_data(datetime(2018, 4, 2, 0, 0, 0, tzinfo=self.patel.resource_calendar_id.tz),
                                             datetime(2018, 4, 6, 23, 0, 0, tzinfo=self.patel.resource_calendar_id.tz))
        self.assertEqual(datas['days'], 1.25)
        self.assertEqual(datas['hours'], 10)

        # Viewing it as John
        datas = self.john.get_work_days_data(datetime(2018, 4, 2, 0, 0, 0, tzinfo=self.john.resource_calendar_id.tz),
                                             datetime(2018, 4, 6, 23, 0, 0, tzinfo=self.john.resource_calendar_id.tz))
        self.assertEqual(datas['days'], 2)
        self.assertEqual(datas['hours'], 20)

        # half days
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'half',
            'calendar_id': self.calendar_1.id,
            'resource_id': self.jean.resource_id.id,
            'date_from': datetime(2018, 4, 2, 10, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
            'date_to': datetime(2018, 4, 2, 14, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
        })

        datas = self.jean.get_work_days_data(datetime(2018, 4, 2, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
                                             datetime(2018, 4, 6, 23, 0, 0, tzinfo=self.jean.resource_calendar_id.tz))

        self.assertEqual(datas['days'], 4.5)
        self.assertEqual(datas['hours'], 36)

        leave.unlink()

        # leave size 0
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'zero',
            'calendar_id': self.calendar_1.id,
            'resource_id': False,
            'date_from': datetime(2018, 4, 2, 10, 0, 0, tzinfo=self.calendar_1.tz),
            'date_to': datetime(2018, 4, 2, 10, 0, 0, tzinfo=self.calendar_1.tz),
        })

        datas = self.jean.get_work_days_data(datetime(2018, 4, 2, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
                                             datetime(2018, 4, 6, 23, 0, 0, tzinfo=self.jean.resource_calendar_id.tz))

        self.assertEqual(datas['days'], 5)
        self.assertEqual(datas['hours'], 40)

        leave.unlink()

        # leave very small size
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'small',
            'calendar_id': self.calendar_1.id,
            'resource_id': False,
            'date_from': datetime(2018, 4, 2, 10, 0, 0, tzinfo=self.calendar_1.tz),
            'date_to': datetime(2018, 4, 2, 10, 0, 1, tzinfo=self.calendar_1.tz),
        })

        datas = self.jean.get_work_days_data(datetime(2018, 4, 2, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
                                             datetime(2018, 4, 6, 23, 0, 0, tzinfo=self.jean.resource_calendar_id.tz))

        self.assertEqual(datas['days'], 5)
        self.assertEqual(float_compare(datas['hours'], 40, precision_digits=2), 0)

        leave.unlink()

    def test_leaves_days_data(self):
        # Jean takes a leave
        self.env['resource.calendar.leaves'].create({
            'name': 'Jean is visiting India',
            'calendar_id': self.jean.resource_calendar_id.id,
            'resource_id': self.jean.resource_id.id,
            'date_from': datetime(2018, 4, 10, 8, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
            'date_to': datetime(2018, 4, 10, 16, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
        })

        # John takes a leave for Jean
        self.env['resource.calendar.leaves'].create({
            'name': 'Jean is comming in USA',
            'calendar_id': self.jean.resource_calendar_id.id,
            'resource_id': self.jean.resource_id.id,
            'date_from': datetime(2018, 4, 12, 8, 0, 0, tzinfo=self.john.resource_calendar_id.tz),
            'date_to': datetime(2018, 4, 12, 16, 0, 0, tzinfo=self.john.resource_calendar_id.tz),
        })

        # Jean asks to see how much leave he has taken
        datas = self.jean.get_leave_days_data(datetime(2018, 4, 9, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
                                               datetime(2018, 4, 13, 23, 59, 59, tzinfo=self.jean.resource_calendar_id.tz))
        # Sees only 1 day and 8 hours because, as john is in UTC-7 the second leave is not in
        # the attendances of Jean
        self.assertEqual(datas['days'], 1)
        self.assertEqual(datas['hours'], 8)

        # Patel Asks to see when Jean has taken some leaves
        # Patel should see the same
        datas = self.jean.get_leave_days_data(datetime(2018, 4, 9, 0, 0, 0, tzinfo=self.patel.resource_calendar_id.tz),
                                               datetime(2018, 4, 13, 23, 59, 59, tzinfo=self.patel.resource_calendar_id.tz))
        self.assertEqual(datas['days'], 1)
        self.assertEqual(datas['hours'], 8)

        # Jean takes a leave for John
        # Gives 3 hours (3/8 of a day)
        self.env['resource.calendar.leaves'].create({
            'name': 'John is sick',
            'calendar_id': self.john.resource_calendar_id.id,
            'resource_id': self.john.resource_id.id,
            'date_from': datetime(2018, 4, 10, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
            'date_to': datetime(2018, 4, 10, 20, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
        })

        # John takes a leave
        # Gives all day (12 hours)
        self.env['resource.calendar.leaves'].create({
            'name': 'John goes to holywood',
            'calendar_id': self.john.resource_calendar_id.id,
            'resource_id': self.john.resource_id.id,
            'date_from': datetime(2018, 4, 13, 7, 0, 0, tzinfo=self.john.resource_calendar_id.tz),
            'date_to': datetime(2018, 4, 13, 18, 0, 0, tzinfo=self.john.resource_calendar_id.tz),
        })

        # John asks how much leaves he has
        # He sees that he has only 15 hours of leave in his attendances
        datas = self.john.get_leave_days_data(datetime(2018, 4, 9, 0, 0, 0, tzinfo=self.john.resource_calendar_id.tz),
                                               datetime(2018, 4, 13, 23, 59, 59, tzinfo=self.john.resource_calendar_id.tz))

        self.assertEqual(datas['days'], 1)
        self.assertEqual(datas['hours'], 10)

        # half days
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'half',
            'calendar_id': self.calendar_1.id,
            'resource_id': self.jean.resource_id.id,
            'date_from': datetime(2018, 4, 2, 10, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
            'date_to': datetime(2018, 4, 2, 14, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
        })

        datas = self.jean.get_leave_days_data(datetime(2018, 4, 2, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
                                             datetime(2018, 4, 6, 23, 0, 0, tzinfo=self.jean.resource_calendar_id.tz))

        self.assertEqual(datas['days'], .5)
        self.assertEqual(datas['hours'], 4)

        leave.unlink()

        # leave size 0
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'zero',
            'calendar_id': self.calendar_1.id,
            'resource_id': False,
            'date_from': datetime(2018, 4, 2, 10, 0, 0, tzinfo=self.calendar_1.tz),
            'date_to': datetime(2018, 4, 2, 10, 0, 0, tzinfo=self.calendar_1.tz),
        })

        datas = self.jean.get_leave_days_data(datetime(2018, 4, 2, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
                                             datetime(2018, 4, 6, 23, 0, 0, tzinfo=self.jean.resource_calendar_id.tz))

        self.assertEqual(datas['days'], 0)
        self.assertEqual(datas['hours'], 0)

        leave.unlink()

        # leave very small size
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'small',
            'calendar_id': self.calendar_1.id,
            'resource_id': False,
            'date_from': datetime(2018, 4, 2, 10, 0, 0, tzinfo=self.calendar_1.tz),
            'date_to': datetime(2018, 4, 2, 10, 0, 1, tzinfo=self.calendar_1.tz),
        })

        datas = self.jean.get_leave_days_data(datetime(2018, 4, 2, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
                                             datetime(2018, 4, 6, 23, 0, 0, tzinfo=self.jean.resource_calendar_id.tz))

        self.assertEqual(datas['days'], 0)
        self.assertEqual(float_compare(datas['hours'], 0, precision_digits=2), 0)

        leave.unlink()

    def test_list_leaves(self):
        jean_leave = self.env['resource.calendar.leaves'].create({
            'name': "Jean's son is sick",
            'calendar_id': self.jean.resource_calendar_id.id,
            'resource_id': False,
            'date_from': datetime(2018, 4, 10, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
            'date_to': datetime(2018, 4, 10, 23, 59, 59, tzinfo=self.jean.resource_calendar_id.tz),
        })

        leaves = self.jean.list_leaves(datetime(2018, 4, 9, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
                                       datetime(2018, 4, 13, 23, 59, 59, tzinfo=self.jean.resource_calendar_id.tz))

        self.assertEqual(len(leaves), 1)
        self.assertEqual(leaves[0][0], date(2018, 4, 10))
        self.assertEqual(leaves[0][1], 8)
        self.assertEqual(leaves[0][2].id, jean_leave.id)

        # half days
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'half',
            'calendar_id': self.jean.resource_calendar_id.id,
            'resource_id': self.jean.resource_id.id,
            'date_from': datetime(2018, 4, 2, 10, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
            'date_to': datetime(2018, 4, 2, 14, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
        })

        leaves = self.jean.list_leaves(datetime(2018, 4, 2, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
                                       datetime(2018, 4, 6, 23, 0, 0, tzinfo=self.jean.resource_calendar_id.tz))

        self.assertEqual(len(leaves), 1)
        self.assertEqual(leaves[0][0], date(2018, 4, 2))
        self.assertEqual(leaves[0][1], 4)
        self.assertEqual(leaves[0][2].id, leave.id)

        leave.unlink()

        # very small size
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'small',
            'calendar_id': self.jean.resource_calendar_id.id,
            'resource_id': self.jean.resource_id.id,
            'date_from': datetime(2018, 4, 2, 10, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
            'date_to': datetime(2018, 4, 2, 10, 0, 1, tzinfo=self.jean.resource_calendar_id.tz),
        })

        leaves = self.jean.list_leaves(datetime(2018, 4, 2, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
                                       datetime(2018, 4, 6, 23, 0, 0, tzinfo=self.jean.resource_calendar_id.tz))

        self.assertEqual(len(leaves), 1)
        self.assertEqual(leaves[0][0], date(2018, 4, 2))
        self.assertEqual(float_compare(leaves[0][1], 0, precision_digits=2), 0)
        self.assertEqual(leaves[0][2].id, leave.id)

        leave.unlink()

        # size 0
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'zero',
            'calendar_id': self.jean.resource_calendar_id.id,
            'resource_id': self.jean.resource_id.id,
            'date_from': datetime(2018, 4, 2, 10, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
            'date_to': datetime(2018, 4, 2, 10, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
        })

        leaves = self.jean.list_leaves(datetime(2018, 4, 2, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
                                       datetime(2018, 4, 6, 23, 0, 0, tzinfo=self.jean.resource_calendar_id.tz))

        self.assertEqual(len(leaves), 0)

        leave.unlink()

    def test_list_work_time_per_day(self):
        working_time = self.john.list_work_time_per_day(datetime(2018, 4, 9, 0, 0, 0, tzinfo=self.john.resource_calendar_id.tz),
                                                        datetime(2018, 4, 13, 23, 59, 59, tzinfo=self.john.resource_calendar_id.tz))

        self.assertEqual(len(working_time), 2)
        self.assertEqual(working_time[0][0], date(2018, 4, 10))
        self.assertEqual(working_time[0][1], 8)

        # half days
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'small',
            'calendar_id': self.jean.resource_calendar_id.id,
            'resource_id': self.jean.resource_id.id,
            'date_from': datetime(2018, 4, 2, 10, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
            'date_to': datetime(2018, 4, 2, 14, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
        })

        working_time = self.jean.list_work_time_per_day(datetime(2018, 4, 2, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
                                                        datetime(2018, 4, 6, 23, 0, 0, tzinfo=self.jean.resource_calendar_id.tz))

        self.assertEqual(len(working_time), 5)
        self.assertEqual(working_time[0][0], date(2018, 4, 2))
        self.assertEqual(working_time[0][1], 4)

        leave.unlink()

        # very small size
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'small',
            'calendar_id': self.jean.resource_calendar_id.id,
            'resource_id': self.jean.resource_id.id,
            'date_from': datetime(2018, 4, 2, 10, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
            'date_to': datetime(2018, 4, 2, 10, 0, 1, tzinfo=self.jean.resource_calendar_id.tz),
        })

        working_time = self.jean.list_work_time_per_day(datetime(2018, 4, 2, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
                                                        datetime(2018, 4, 6, 23, 0, 0, tzinfo=self.jean.resource_calendar_id.tz))

        self.assertEqual(len(working_time), 5)
        self.assertEqual(working_time[0][0], date(2018, 4, 2))
        self.assertEqual(float_compare(working_time[0][1], 8, precision_digits=2), 0)

        leave.unlink()

        # size 0
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'zero',
            'calendar_id': self.jean.resource_calendar_id.id,
            'resource_id': self.jean.resource_id.id,
            'date_from': datetime(2018, 4, 2, 10, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
            'date_to': datetime(2018, 4, 2, 10, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
        })

        working_time = self.jean.list_work_time_per_day(datetime(2018, 4, 2, 0, 0, 0, tzinfo=self.jean.resource_calendar_id.tz),
                                                        datetime(2018, 4, 6, 23, 0, 0, tzinfo=self.jean.resource_calendar_id.tz))

        self.assertEqual(len(working_time), 5)
        self.assertEqual(working_time[0][0], date(2018, 4, 2))
        self.assertEqual(working_time[0][1], 8)

        leave.unlink()


class TestTimezones(TestResourceCommon):
    def setUp(self):
        super(TestTimezones, self).setUp()

        self.tz1 = 'Etc/GMT+6'
        self.tz2 = 'Europe/Brussels'
        self.tz3 = 'Etc/GMT-10'
        self.tz4 = 'Etc/GMT+10'

    def test_work_hours_count(self):
        # When no timezone => UTC
        count = self.calendar_1.get_work_hours_count(datetime(2018, 4, 10, 8, 0, 0),
                                                     datetime(2018, 4, 10, 12, 0, 0))

        self.assertEqual(count, 4)

        # This timezone is not the same as the calendar's one
        count = self.calendar_1.get_work_hours_count(datetime(2018, 4, 10, 8, 0, 0, tzinfo=self.tz1),
                                                     datetime(2018, 4, 10, 12, 0, 0, tzinfo=self.tz1))

        self.assertEqual(count, 0)

        # Using two different timezones
        # 10-04-2018 06:00:00 - 10-04-2018 02:00:00
        count = self.calendar_1.get_work_hours_count(datetime(2018, 4, 10, 8, 0, 0, tzinfo=self.tz2),
                                                     datetime(2018, 4, 10, 12, 0, 0, tzinfo=self.tz3))

        self.assertEqual(count, 0)

        # Using two different timezones
        # 2018-4-10 06:00:00 - 2018-4-10 22:00:00
        count = self.calendar_1.get_work_hours_count(datetime(2018, 4, 10, 8, 0, 0, tzinfo=self.tz2),
                                                     datetime(2018, 4, 10, 12, 0, 0, tzinfo=self.tz4))

        self.assertEqual(count, 8)

    def test_plan_hours(self):
        dt = self.calendar_1.plan_hours(10, datetime(2018, 4, 10, 8, 0, 0))

        self.assertEqual(dt, datetime(2018, 4, 11, 12, 0, 0, tzinfo=self.tz2))

        dt = self.calendar_1.plan_hours(10, datetime(2018, 4, 10, 8, 0, 0, tzinfo=self.tz4))

        self.assertEqual(dt, datetime(2018, 4, 12, 10, 0, 0, tzinfo=self.tz2))

    def test_plan_days(self):
        dt = self.calendar_1.plan_days(2, datetime(2018, 4, 10, 8, 0, 0))

        self.assertEqual(dt, datetime(2018, 4, 11, 16, 0, 0, tzinfo=self.tz2))

        # We lose one day because of timezone
        dt = self.calendar_1.plan_days(2, datetime(2018, 4, 10, 8, 0, 0, tzinfo=self.tz4))

        self.assertEqual(dt, datetime(2018, 4, 12, 16, 0, 0, tzinfo=self.tz2))

    def test_work_data(self):
        # 09-04-2018 10:00:00 - 13-04-2018 18:00:00
        data = self.jean.get_work_days_data(datetime(2018, 4, 9, 8, 0, 0),
                                            datetime(2018, 4, 13, 16, 0, 0))

        self.assertEqual(data['hours'], 38)

        # 09-04-2018 00:00:00 - 13-04-2018 08:00:00
        data = self.jean.get_work_days_data(datetime(2018, 4, 9, 8, 0, 0, tzinfo=self.tz3),
                                            datetime(2018, 4, 13, 16, 0, 0, tzinfo=self.tz3))

        self.assertEqual(data['hours'], 32)

        # 09-04-2018 08:00:00 - 14-04-2018 12:00:00
        data = self.jean.get_work_days_data(datetime(2018, 4, 9, 8, 0, 0, tzinfo=self.tz2),
                                            datetime(2018, 4, 13, 16, 0, 0, tzinfo=self.tz4))

        self.assertEqual(data['hours'], 40)

    def test_leave_data(self):
        self.env['resource.calendar.leaves'].create({
            'name': '',
            'calendar_id': self.jean.resource_calendar_id.id,
            'resource_id': self.jean.resource_id.id,
            'date_from': datetime(2018, 4, 9, 8, 0, 0, tzinfo=self.tz2),
            'date_to': datetime(2018, 4, 9, 14, 0, 0, tzinfo=self.tz2),
        })

        # 09-04-2018 10:00:00 - 13-04-2018 18:00:00
        data = self.jean.get_leave_days_data(datetime(2018, 4, 9, 8, 0, 0),
                                            datetime(2018, 4, 13, 16, 0, 0))

        self.assertEqual(data['hours'], 4)

        # 09-04-2018 00:00:00 - 13-04-2018 08:00:00
        data = self.jean.get_leave_days_data(datetime(2018, 4, 9, 8, 0, 0, tzinfo=self.tz3),
                                            datetime(2018, 4, 13, 16, 0, 0, tzinfo=self.tz3))

        self.assertEqual(data['hours'], 6)

        # 09-04-2018 08:00:00 - 14-04-2018 12:00:00
        data = self.jean.get_leave_days_data(datetime(2018, 4, 9, 8, 0, 0, tzinfo=self.tz2),
                                            datetime(2018, 4, 13, 16, 0, 0, tzinfo=self.tz4))

        self.assertEqual(data['hours'], 6)

    def test_leaves(self):
        self.env['resource.calendar.leaves'].create({
            'name': '',
            'calendar_id': self.jean.resource_calendar_id.id,
            'resource_id': self.jean.resource_id.id,
            'date_from': datetime(2018, 4, 9, 8, 0, 0, tzinfo=self.tz2),
            'date_to': datetime(2018, 4, 9, 14, 0, 0, tzinfo=self.tz2),
        })

        # 09-04-2018 10:00:00 - 13-04-2018 18:00:00
        leaves = self.jean.list_leaves(datetime(2018, 4, 9, 8, 0, 0),
                                       datetime(2018, 4, 13, 16, 0, 0))

        self.assertEqual(len(leaves), 1)
        self.assertEqual(leaves[0][1], 4)

        # 09-04-2018 00:00:00 - 13-04-2018 08:00:00
        leaves = self.jean.list_leaves(datetime(2018, 4, 9, 8, 0, 0, tzinfo=self.tz3),
                                       datetime(2018, 4, 13, 16, 0, 0, tzinfo=self.tz3))

        self.assertEqual(len(leaves), 1)
        self.assertEqual(leaves[0][1], 6)

        # 09-04-2018 08:00:00 - 14-04-2018 12:00:00
        leaves = self.jean.list_leaves(datetime(2018, 4, 9, 8, 0, 0, tzinfo=self.tz2),
                                       datetime(2018, 4, 13, 16, 0, 0, tzinfo=self.tz4))

        self.assertEqual(len(leaves), 1)
        self.assertEqual(leaves[0][1], 6)

    def test_works(self):
        work = self.jean.list_work_time_per_day(datetime(2018, 4, 9, 8, 0, 0),
                                           datetime(2018, 4, 13, 16, 0, 0))

        self.assertEqual(len(work), 5)
        self.assertEqual(work[0][1], 6)

        work = self.jean.list_work_time_per_day(datetime(2018, 4, 9, 8, 0, 0, tzinfo=self.tz3),
                                           datetime(2018, 4, 13, 16, 0, 0, tzinfo=self.tz3))

        self.assertEqual(len(work), 4)

        work = self.jean.list_work_time_per_day(datetime(2018, 4, 9, 8, 0, 0, tzinfo=self.tz2),
                                           datetime(2018, 4, 13, 16, 0, 0, tzinfo=self.tz4))

        self.assertEqual(len(work), 5)
        self.assertEqual(work[0][1], 8)
