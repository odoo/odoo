# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details
from datetime import datetime
from pytz import UTC, timezone

from odoo.addons.resource.models.utils import Intervals
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

@tagged('post_install', '-at_install')
class TestPlanningContract(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.dep_rd = cls.env['hr.department'].create({
            'name': 'Research & Development - Test',
        })
        cls.jules_emp = cls.env['hr.employee'].create({
            'name': 'Jules',
            'gender': 'male',
            'birthday': '1984-05-01',
            'country_id': cls.env.ref('base.be').id,
            'department_id': cls.dep_rd.id,
        })

        cls.calendar_35h = cls.env['resource.calendar'].create({
            'name': '35h calendar',
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Lunch', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Monday Evening', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Lunch', 'dayofweek': '1', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Tuesday Evening', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Lunch', 'dayofweek': '2', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Wednesday Evening', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Lunch', 'dayofweek': '3', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Thursday Evening', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Lunch', 'dayofweek': '4', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Friday Evening', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'})
            ]
        })
        cls.calendar_40h = cls.env['resource.calendar'].create({'name': 'Default calendar'})

        # This contract ends at the 15th of the month
        cls.contract_cdd = cls.env['hr.contract'].create({  # Fixed term contract
            'date_end': datetime.strptime('2015-11-15', '%Y-%m-%d'),
            'date_start': datetime.strptime('2015-01-01', '%Y-%m-%d'),
            'name': 'First CDD Contract for Jules',
            'resource_calendar_id': cls.calendar_40h.id,
            'wage': 5000.0,
            'employee_id': cls.jules_emp.id,
            'state': 'open',
            'kanban_state': 'blocked',
        })

        # This contract starts the next day
        cls.contract_cdi = cls.env['hr.contract'].create({
            'date_start': datetime.strptime('2015-11-16', '%Y-%m-%d'),
            'name': 'Contract for Jules',
            'resource_calendar_id': cls.calendar_35h.id,
            'wage': 5000.0,
            'employee_id': cls.jules_emp.id,
            'state': 'open',
            'kanban_state': 'normal',
        })

    def test_employee_contract_validity_per_period(self):
        start = datetime(2015, 11, 8, 00, 00, 00, tzinfo=UTC)
        end = datetime(2015, 11, 21, 23, 59, 59, tzinfo=UTC)
        jules_resource = self.jules_emp.resource_id
        calendars_validity_within_period = jules_resource._get_calendars_validity_within_period(start, end, default_company=self.jules_emp.company_id)
        tz = timezone(self.jules_emp.tz)

        self.assertEqual(len(calendars_validity_within_period[jules_resource.id]), 2, "There should exist 2 calendars within the period")
        interval_calendar_40h = Intervals([(
            start,
            tz.localize(datetime.combine(self.contract_cdd.date_end, datetime.max.time())),
            self.env['resource.calendar.attendance']
        )])
        interval_calendar_35h = Intervals([(
            tz.localize(datetime.combine(self.contract_cdi.date_start, datetime.min.time())),
            end,
            self.env['resource.calendar.attendance']
        )])
        computed_interval_40h = calendars_validity_within_period[jules_resource.id][self.calendar_40h]
        computed_interval_35h = calendars_validity_within_period[jules_resource.id][self.calendar_35h]
        self.assertFalse(computed_interval_40h - interval_calendar_40h, "The interval of validity for the 40h calendar must be from 2015-11-16 to 2015-11-21, not more")
        self.assertFalse(interval_calendar_40h - computed_interval_40h, "The interval of validity for the 40h calendar must be from 2015-11-16 to 2015-11-21, not less")
        self.assertFalse(computed_interval_35h - interval_calendar_35h, "The interval of validity for the 35h calendar must be from 2015-11-08 to 2015-11-15, not more")
        self.assertFalse(interval_calendar_35h - computed_interval_35h, "The interval of validity for the 35h calendar must be from 2015-11-08 to 2015-11-15, not less")

    def test_employee_work_intervals(self):
        start = datetime(2015, 11, 8, 00, 00, 00, tzinfo=UTC)
        end = datetime(2015, 11, 21, 23, 59, 59, tzinfo=UTC)
        work_intervals, _ = self.jules_emp.resource_id._get_valid_work_intervals(start, end)
        sum_work_intervals = sum(
            (stop - start).total_seconds() / 3600
            for start, stop, _resource in work_intervals[self.jules_emp.resource_id.id]
        )
        self.assertEqual(75, sum_work_intervals, "Sum of the work intervals for the employee Jules should be 40h+35h = 75h")

    def test_employee_work_planning_hours_info(self):
        planning_hours_info = self.env['planning.slot'].gantt_progress_bar(
            ['resource_id'], {'resource_id': self.jules_emp.resource_id.ids}, '2015-11-08 00:00:00', '2015-11-21 23:59:59'
        )['resource_id']
        self.assertEqual(75, planning_hours_info[self.jules_emp.resource_id.id]['max_value'], "Work hours for the employee Jules should be 40h+35h = 75h")
