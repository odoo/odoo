# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo.addons.project_enterprise.tests.gantt_reschedule_dates_common import fake_now
from .auto_shift_dates_hr_common import AutoShiftDatesHRCommon
from odoo.fields import Command


@freeze_time(fake_now)
class TestGanttRescheduleOnTasks(AutoShiftDatesHRCommon):

    def test_auto_shift_employee_integration(self):
        # We have to bypass the calendar validity computation for employees/students,
        # Otherwise, we will fallback on company calendar if there are no contracts
        # once the test is launched in project_enterprise_hr_contract by extension
        self.armande_employee.employee_type = 'freelance'

        self.task_4.depend_on_ids = [Command.clear()]
        new_task_3_begin_date = self.task_1_date_deadline - timedelta(hours=2)  # 2021 06 24 10:00
        self.task_3.write({
            'planned_date_begin': new_task_3_begin_date,
            'date_deadline': new_task_3_begin_date + (self.task_3_date_deadline - self.task_3_planned_date_begin),
        })
        self.gantt_reschedule_backward(self.task_1, self.task_3)
        failed_message = "The auto shift date feature should take the employee's calendar into account."
        self.assertEqual(self.task_1.planned_date_begin,
                         new_task_3_begin_date - relativedelta(days=1, hour=14), failed_message)
        self.armande_employee.write({
            'resource_calendar_id': self.calendar_morning.id,
        })
        new_task_3_begin_date = self.task_1.planned_date_begin + relativedelta(hour=10)  # 2021 06 23 10:00
        self.task_3.write({
            'planned_date_begin': new_task_3_begin_date,
            'date_deadline': new_task_3_begin_date + (self.task_3_date_deadline - self.task_3_planned_date_begin),
        })
        self.gantt_reschedule_backward(self.task_1, self.task_3)
        self.assertEqual(self.task_1.planned_date_begin,
                         new_task_3_begin_date + relativedelta(days=-1, hour=11), failed_message)
        failed_message = "The auto shift date feature should take the employee's calendar into account even before employee create_date."
        new_task_3_begin_date = self.armande_employee_create_date - relativedelta(days=4, hour=15)
        self.task_3.write({
            'planned_date_begin': new_task_3_begin_date,
            'date_deadline': new_task_3_begin_date + (self.task_3_date_deadline - self.task_3_planned_date_begin),
        })
        self.gantt_reschedule_backward(self.task_1, self.task_3)
        self.assertEqual(self.task_1.date_deadline,
                         new_task_3_begin_date - relativedelta(hour=12), failed_message)
        new_task_1_begin_date = self.armande_departure_date + relativedelta(days=1, hour=11)
        self.task_1.write({
            'planned_date_begin': new_task_1_begin_date,
            'date_deadline': new_task_1_begin_date + (self.task_1_date_deadline - self.task_1_planned_date_begin),
        })
        self.gantt_reschedule_forward(self.task_1, self.task_3)
        self.assertEqual(self.task_3.planned_date_begin,
                         new_task_1_begin_date + relativedelta(days=1, hour=8), failed_message)
        failed_message = "The auto shift date feature should work for tasks landing on the edge of employee create_date or on the edge of departure_date."
        new_task_3_begin_date = self.armande_employee_create_date + relativedelta(hour=13)
        self.task_3.write({
            'planned_date_begin': new_task_3_begin_date,
            'date_deadline': new_task_3_begin_date + (self.task_3_date_deadline - self.task_3_planned_date_begin),
        })
        self.gantt_reschedule_backward(self.task_1, self.task_3)
        self.assertEqual(self.task_1.planned_date_begin,
                         new_task_3_begin_date + relativedelta(hour=9), failed_message)
        new_task_1_begin_date = self.armande_departure_date - relativedelta(days=1, hour=16)
        self.armande_employee.write({
            'resource_calendar_id': self.calendar_afternoon.id,
        })
        self.task_1.write({
            'planned_date_begin': new_task_1_begin_date,
            'date_deadline': new_task_1_begin_date + (self.task_1_date_deadline - self.task_1_planned_date_begin),
        })
        self.gantt_reschedule_forward(self.task_1, self.task_3)
        self.assertEqual(self.task_3.planned_date_begin,
                         new_task_1_begin_date + relativedelta(days=1, hour=13), failed_message)
        failed_message = "The auto shift date feature should work for tasks landing on the edge of employee create_date or on the edge of departure_date, even when falling in the middle of the allocated_hours."
        new_task_3_begin_date = self.armande_employee_create_date + relativedelta(hour=15)
        self.armande_employee.write({
            'resource_calendar_id': self.calendar_morning.id,
        })
        self.task_3.write({
            'planned_date_begin': new_task_3_begin_date,
            'date_deadline': new_task_3_begin_date + (self.task_3_date_deadline - self.task_3_planned_date_begin),
        })
        self.gantt_reschedule_backward(self.task_1, self.task_3)
        self.assertEqual(self.task_1.planned_date_begin,
                         new_task_3_begin_date + relativedelta(hour=9), failed_message)
        new_task_1_begin_date = self.armande_departure_date + relativedelta(hour=10)
        self.task_1.write({
            'planned_date_begin': new_task_1_begin_date,
            'date_deadline': new_task_1_begin_date + (self.task_1_date_deadline - self.task_1_planned_date_begin),
        })
        self.gantt_reschedule_forward(self.task_1, self.task_3)
        self.assertEqual(self.task_3.date_deadline,
                         new_task_1_begin_date + relativedelta(days=1, hour=10), failed_message)

    def test_auto_shift_multiple_assignees(self):
        """
        Tests that the auto shift fallbacks to the company calendar in the case that
        there are multiple assignees to the task.
        """
        self.task_1.user_ids += self.user_projectmanager
        self.task_1.write(self.task_1_date_gantt_reschedule_trigger)
        self.gantt_reschedule_backward(self.task_1, self.task_3)
        failed_message = "The auto shift date feature should move forward a dependent tasks."
        self.assertTrue(self.task_1.date_deadline <= self.task_3.planned_date_begin, failed_message)
