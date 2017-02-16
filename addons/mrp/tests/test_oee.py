# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

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
        day = datetime.date.today()

        # Productive time duration (13 min)
        self.create_productivity_line(self.env.ref('mrp.block_reason7'), str(day) + " " + "10:43:22", str(day) + " " + "10:56:22")

        # Material Availability time duration (1.52 min)
        # Check working state is blocked or not.
        workcenter_productivity_1 = self.create_productivity_line(self.env.ref('mrp.block_reason0'), str(day) + " " + "10:47:08")
        self.assertEqual(self.workcenter_1.working_state, 'blocked', "Wrong working state of workcenter.")

        # Check working state is normal or not.
        workcenter_productivity_1.write({'date_end': str(day) + " " + "10:48:39"})
        self.assertEqual(self.workcenter_1.working_state, 'normal', "Wrong working state of workcenter.")

        # Process Defect time duration (1.33 min)
        self.create_productivity_line(self.env.ref('mrp.block_reason5'), str(day) + " " + "10:48:38", str(day) + " " + "10:49:58")
        # Reduced Speed time duration (3.0 min)
        self.create_productivity_line(self.env.ref('mrp.block_reason4'), str(day) + " " + "10:50:22", str(day) + " " + "10:53:22")

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
