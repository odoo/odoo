# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from .test_common import TestCommon


class TestPerformance(TestCommon):
    def test_performance_recompute_shifts_in_leave_periods(self):
        """ Test performance of _recompute_shifts_in_leave_periods method

            This method is used in the CUD operations of `resource.calendar.leave`, so
            we need to check the method is not too costly to not having a performance
            issue when some public leaves are created or some leaves are validated for
            a employe or sone leaves are renoved.
        """
        self.employee_bert.create_date = datetime(2020, 1, 1)
        public_holiday = self.env['resource.calendar.leaves'].create({
            'name': 'Public holiday',
            'calendar_id': self.calendar.id,
            'date_from': datetime(2020, 5, 1, 8, 0),
            'date_to': datetime(2020, 5, 1, 17, 0),
        })
        leaves = self.env['resource.calendar.leaves'].create([{
            'resource_id': self.resource_bert.id,
            'date_from': datetime(2020, 5, 3 + 7 * i),
            'date_to': datetime(2020, 5, 3 + 7 * i),
        } for i in range(5)])

        slot_vals_list = [{
            'employee_id': self.employee_bert.id,
            'start_datetime': datetime(2020, 4, 30, 8, 0),
            'end_datetime': datetime(2020, 4, 30, 17, 0),
        }]
        slot_vals_list += [{
            'employee_id': self.employee_bert.id,
            'start_datetime': datetime(2020, 5, i, 8, 0),
            'end_datetime': datetime(2020, 5, i, 12, 0),
        } for i in range(1, 31)]
        slot_vals_list += [{
            'employee_id': self.employee_bert.id,
            'start_datetime': datetime(2020, 5, i, 13, 0),
            'end_datetime': datetime(2020, 5, i, 17, 0),
        } for i in range(1, 31)]
        self.env['planning.slot'].create(slot_vals_list)
        resource_calendar_leaves = leaves + public_holiday
        self.assertEqual(len(resource_calendar_leaves), 6)
        with self.assertQueryCount(__system__=1):
            resource_calendar_leaves._recompute_shifts_in_leave_periods()
