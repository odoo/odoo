# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo.addons.project_enterprise.tests.gantt_reschedule_dates_common import ProjectEnterpriseGanttRescheduleCommon
from odoo.fields import Command


class AutoShiftDatesHRCommon(ProjectEnterpriseGanttRescheduleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.armande_employee_create_date = cls.task_3_planned_date_begin - relativedelta(months=1, hour=12, minute=0, second=0, microsecond=0)
        cls.armande_employee = cls.env['hr.employee'].create({
            'name': 'Armande ProjectUser',
            'user_id': cls.user_projectuser.id,
            'tz': 'UTC',
            'create_date': cls.armande_employee_create_date,
        })
        cls.calendar_morning = cls.env['resource.calendar'].create({
            'name': '20h calendar morning',
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
            ],
            'tz': 'UTC',
        })
        cls.calendar_afternoon = cls.env['resource.calendar'].create({
            'name': '20h calendar afternoon',
            'attendance_ids': [
                (0, 0, {'name': 'Monday Evening', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Evening', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Evening', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Evening', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Evening', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
            ],
            'tz': 'UTC',
        })
        cls.armande_departure_date = cls.task_1_date_deadline.date() + relativedelta(day=29)  # 2021 06 25
        cls.armande_employee.write({
            'departure_date': cls.armande_departure_date,
            'resource_calendar_id': cls.calendar_afternoon.id,
        })
