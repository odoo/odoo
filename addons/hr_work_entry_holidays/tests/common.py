# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.fields import Datetime
from odoo.addons.hr_work_entry_contract.tests.common import TestWorkEntryBase


class TestWorkEntryHolidaysBase(TestWorkEntryBase):

    @classmethod
    def setUpClass(cls):
        super(TestWorkEntryHolidaysBase, cls).setUpClass()

        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Legal Leaves',
            'time_type': 'leave',
            'allocation_type': 'no',
            'validity_start': False,
            'work_entry_type_id': cls.work_entry_type_leave.id
        })

        # I create a new employee "Jules"
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
                (0, 0, {'name': 'Monday Evening', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Evening', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Evening', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Evening', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Evening', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'})
            ]
        })
        cls.calendar_35h._onchange_hours_per_day()  # update hours/day
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
            'date_generated_from': datetime.strptime('2015-11-16', '%Y-%m-%d'),
            'date_generated_to': datetime.strptime('2015-11-16', '%Y-%m-%d'),
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
            'date_generated_from': datetime.strptime('2015-11-15', '%Y-%m-%d'),
            'date_generated_to': datetime.strptime('2015-11-15', '%Y-%m-%d'),
        })

    def create_leave(cls, date_from=None, date_to=None):
        date_from = date_from or Datetime.today()
        date_to = date_to or Datetime.today() + relativedelta(days=1)
        return cls.env['hr.leave'].create({
            'name': 'Holiday !!!',
            'employee_id': cls.richard_emp.id,
            'holiday_status_id': cls.leave_type.id,
            'date_to': date_to,
            'date_from': date_from,
            'number_of_days': 1,
        })
