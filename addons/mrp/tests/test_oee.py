# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta, time
from pytz import timezone, utc

from odoo import fields
from odoo.addons.mrp.tests.common import TestMrpCommon


class TestOee(TestMrpCommon):
    def create_productivity_line(self, loss_reason, date_start=False, date_end=False):
        return self.env['mrp.workcenter.productivity'].create({
            'workcenter_id': self.workcenter_1.id,
            'date_start': date_start,
            'date_end': date_end,
            'loss_id': loss_reason.id,
            'description': loss_reason.name
        })

    def test_wrokcenter_oee(self):
        """  Test case workcenter oee. """
        day = datetime.date(datetime.today())
        # Make the test work the weekend. It will fails due to workcenter working hours.
        if day.weekday() in (5, 6):
            day -= timedelta(days=2)

        tz = timezone(self.workcenter_1.resource_calendar_id.tz)

        def time_to_string_utc_datetime(time):
            return fields.Datetime.to_string(
                tz.localize(datetime.combine(day, time)).astimezone(utc)
            )

        start_time = time_to_string_utc_datetime(time(10, 43, 22))
        end_time = time_to_string_utc_datetime(time(10, 56, 22))
        # Productive time duration (13 min)
        self.create_productivity_line(self.env.ref('mrp.block_reason7'), start_time, end_time)

        # Material Availability time duration (1.52 min)
        # Check working state is blocked or not.
        start_time = time_to_string_utc_datetime(time(10, 47, 8))
        workcenter_productivity_1 = self.create_productivity_line(self.env.ref('mrp.block_reason0'), start_time)
        self.assertEqual(self.workcenter_1.working_state, 'blocked', "Wrong working state of workcenter.")

        # Check working state is normal or not.
        end_time = time_to_string_utc_datetime(time(10, 48, 39))
        workcenter_productivity_1.write({'date_end': end_time})
        self.assertEqual(self.workcenter_1.working_state, 'normal', "Wrong working state of workcenter.")

        # Process Defect time duration (1.33 min)
        start_time = time_to_string_utc_datetime(time(10, 48, 38))
        end_time = time_to_string_utc_datetime(time(10, 49, 58))
        self.create_productivity_line(self.env.ref('mrp.block_reason5'), start_time, end_time)
        # Reduced Speed time duration (3.0 min)
        start_time = time_to_string_utc_datetime(time(10, 50, 22))
        end_time = time_to_string_utc_datetime(time(10, 53, 22))
        self.create_productivity_line(self.env.ref('mrp.block_reason4'), start_time, end_time)

        # Block time : ( Process Defact (1.33 min) + Reduced Speed (3.0 min) + Material Availability (1.52 min)) = 5.85 min
        blocked_time_in_hour = round(((1.33 + 3.0 + 1.52) / 60.0), 2)
        # Productive time : Productive time duration (13 min)
        productive_time_in_hour = round((13.0 / 60.0), 2)

        # Check blocked time and productive time
        self.assertEqual(self.workcenter_1.blocked_time, blocked_time_in_hour, "Wrong block time on workcenter.")
        self.assertEqual(self.workcenter_1.productive_time, productive_time_in_hour, "Wrong productive time on workcenter.")

        # Check overall equipment effectiveness
        computed_oee = round(((productive_time_in_hour * 100.0)/(productive_time_in_hour + blocked_time_in_hour)), 2)
        self.assertEqual(self.workcenter_1.oee, computed_oee, "Wrong oee on workcenter.")
