# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo.fields import Command
from odoo.addons.project_enterprise_hr.tests.auto_shift_dates_hr_common import AutoShiftDatesHRCommon
from odoo.addons.project_enterprise.tests.gantt_reschedule_dates_common import fake_now


@freeze_time(fake_now)
class TestGanttRescheduleOnTasks(AutoShiftDatesHRCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.contract_1 = cls.env['hr.contract'].create({
            'date_start': cls.task_1_planned_date_begin.date() - relativedelta(days=1),
            'date_end': cls.task_1_planned_date_begin.date() + relativedelta(days=1),
            'name': 'First CDD Contract for Armande ProjectUser',
            'resource_calendar_id': cls.calendar_morning.id,
            'wage': 5000.0,
            'employee_id': cls.armande_employee.id,
            'state': 'close',
        })
        cls.contract_2 = cls.env['hr.contract'].create({
            'date_start': cls.task_1_planned_date_begin.date() + relativedelta(days=2),
            'name': 'CDI Contract for Armande ProjectUser',
            'resource_calendar_id': cls.calendar_afternoon.id,
            'wage': 5000.0,
            'employee_id': cls.armande_employee.id,
            'state': 'open',
        })
        cls.armande_user_calendar = cls.env['resource.calendar'].create({
            'name': 'Wednesday calendar',
            'attendance_ids': [
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Lunch', 'dayofweek': '2', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Wednesday Evening', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
            ],
            'tz': 'UTC',
        })

    def test_auto_shift_employee_contract_integration(self):
        # As the fallback is the company and not the resource's calendar, we have to create a contract for armande in the past
        self.contract_3 = self.env['hr.contract'].create({
            'date_start': self.task_1_planned_date_begin.date() - relativedelta(months=1),
            'date_end': self.task_1_planned_date_begin.date() - relativedelta(days=2),
            'name': 'Other CDD Contract for Armande ProjectUser',
            'resource_calendar_id': self.armande_user_calendar.id,
            'wage': 5000.0,
            'employee_id': self.armande_employee.id,
            'state': 'close',
        })

        self.task_4.depend_on_ids = [Command.clear()]
        new_task_3_begin_date = self.task_1_date_deadline - timedelta(hours=2)  # 2021 06 24 10:00
        self.task_3.write({
            'planned_date_begin': new_task_3_begin_date,
            'date_deadline': new_task_3_begin_date + (self.task_3_date_deadline - self.task_3_planned_date_begin),
        })
        self.gantt_reschedule_backward(self.task_1, self.task_3)
        failed_message = "The auto shift date feature should take the employee's calendar into account."
        self.assertEqual(self.task_1.planned_date_begin,
                         new_task_3_begin_date - relativedelta(days=1, hour=11), failed_message)
        new_task_3_begin_date = self.task_1.planned_date_begin - relativedelta(days=2)  # 2021 06 21 11:00
        self.task_3.write({
            'planned_date_begin': new_task_3_begin_date,
            'date_deadline': new_task_3_begin_date + (self.task_3_date_deadline - self.task_3_planned_date_begin),
        })
        self.gantt_reschedule_backward(self.task_1, self.task_3)
        failed_message = "The auto shift date feature should take the employee's calendar when no contract cover the period."
        self.assertEqual(self.task_1.planned_date_begin,
                         new_task_3_begin_date + relativedelta(day=16, hour=14), failed_message)
        tmp_date_start = self.contract_3.date_start
        # Test like there are no active contract covering < 2021 06 15
        self.contract_3.write({
            'date_start': self.contract_3.date_end - relativedelta(days=1)
        })
        new_task_3_begin_date = self.task_1.planned_date_begin - relativedelta(days=2)  # 2021 06 14 14:00
        self.task_3.write({
            'planned_date_begin': new_task_3_begin_date,
            'date_deadline': new_task_3_begin_date + (self.task_3_date_deadline - self.task_3_planned_date_begin),
        })
        self.gantt_reschedule_backward(self.task_1, self.task_3)
        failed_message = "The auto shift date feature should take the company's calendar when no contract cover the period and no calendar is set on the employee."
        self.assertEqual(self.task_1.planned_date_begin,
                         new_task_3_begin_date + relativedelta(hour=10), failed_message)
        # Reset contract
        self.contract_3.write({
            'date_start': tmp_date_start
        })
        new_task_1_begin_date = self.contract_2.date_start + relativedelta(days=1, hour=14)  # 2021 06 27 14:00
        self.task_1.write({
            'planned_date_begin': new_task_1_begin_date,
            'date_deadline': new_task_1_begin_date + (self.task_1_date_deadline - self.task_1_planned_date_begin),
        })
        self.gantt_reschedule_forward(self.task_1, self.task_3)
        self.assertEqual(self.task_3.planned_date_begin,
                         new_task_1_begin_date + relativedelta(days=1, hour=13), failed_message)

    def test_auto_shift_period_without_contract(self):
        self.contract_3 = self.env['hr.contract'].create({
            'date_start': self.task_1_planned_date_begin.date() - relativedelta(months=1),
            'date_end': self.task_1_planned_date_begin.date() - relativedelta(days=5),
            'name': 'Other CDD Contract for Armande ProjectUser',
            'resource_calendar_id': self.calendar_afternoon.id,
            'wage': 5000.0,
            'employee_id': self.armande_employee.id,
            'state': 'close',
        })
        self.armande_employee.write({
            'resource_calendar_id': self.calendar_morning.id,
        })

        self.task_4.depend_on_ids = [Command.clear()]
        new_task_3_begin_date = self.task_1_date_deadline - timedelta(hours=2)  # 2021 06 24 10:00
        self.task_3.write({
            'planned_date_begin': new_task_3_begin_date,
            'date_deadline': new_task_3_begin_date + (self.task_3_date_deadline - self.task_3_planned_date_begin),
        })
        self.gantt_reschedule_backward(self.task_1, self.task_3)
        failed_message = "The auto shift date feature should take the employee's calendar into account."
        self.assertEqual(self.task_1.planned_date_begin,
                         new_task_3_begin_date - relativedelta(days=1, hour=11), failed_message)
        new_task_3_begin_date = self.task_1.planned_date_begin - relativedelta(days=2)  # 2021 06 21 11:00
        self.task_3.write({
            'planned_date_begin': new_task_3_begin_date,
            'date_deadline': new_task_3_begin_date + (self.task_3_date_deadline - self.task_3_planned_date_begin),
        })
        self.gantt_reschedule_backward(self.task_1, self.task_3)
        failed_message = "The auto shift date feature should take the company's calendar when no contract covers the period."
        self.assertEqual(self.task_1.planned_date_begin,
                         new_task_3_begin_date + relativedelta(day=21, hour=8), failed_message)
        # between the two contracts, the fallback is done on company calendar.
