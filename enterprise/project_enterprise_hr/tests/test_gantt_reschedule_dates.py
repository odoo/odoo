# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo.addons.project_enterprise.tests.gantt_reschedule_dates_common import fake_now
from .auto_shift_dates_hr_common import AutoShiftDatesHRCommon
from odoo.fields import Command
from odoo.tests import freeze_time


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
        new_task_3_begin_date = self.armande_employee_create_date + relativedelta(hour=10)
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
        new_task_3_begin_date = self.armande_employee_create_date + relativedelta(hour=10)
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

    def test_move_backward_with_multi_users(self):
        """
                         -------------------------------------------------------------
            Raouf 1 & 2  |     [0]                                                   |
                         v      |                                                    |
            Raouf 1     [13]    ->[ 1 ]------>[2]----------->[5]   |->[7]---------->[8]
                                   |  |        ^      --------|-----                 ^
                                   |  |        |      |       |                      |
            Raouf 2                |  -->[3]   |      |       ----->[9]------------>[10]
                                   |           |      |
                                   |           |      |
            Raouf 3 & 2            ---------->[4]---->[6]

            When we move 8 before 13:
            - all the ancestors of 8 should move before 8 (0, 1, 4, 2, 6, 7, 5, 9, 10, 8)
        """
        self.armande_employee.resource_calendar_id = self.calendar_40h.id

        self.env["hr.employee"].create([{
                "name": user.name,
                "user_id": user.id,
                "employee_type": "freelance",
            } for user in [self.user1, self.user2]
        ])

        self.env['resource.calendar.leaves'].create([{
            'name': 'scheduled leave',
            'date_from': datetime(year=2024, month=2, day=15, hour=0),
            'date_to': datetime(year=2024, month=2, day=15, hour=23),
            'resource_id': self.user1.employee_id.resource_id.id,
            'time_type': 'leave',
        }, {
            'name': 'scheduled leave',
            'date_from': datetime(year=2024, month=2, day=20, hour=0),
            'date_to': datetime(year=2024, month=2, day=20, hour=23),
            'resource_id': self.user1.employee_id.resource_id.id,
            'time_type': 'leave',
        }, {
            'name': 'scheduled leave',
            'date_from': datetime(year=2024, month=2, day=16, hour=0),
            'date_to': datetime(year=2024, month=2, day=16, hour=23),
            'resource_id': self.user2.employee_id.resource_id.id,
            'time_type': 'leave',
        }])

        self.annual_holiday.write({
            'date_from': datetime(year=2024, month=2, day=12, hour=0),
            'date_to': datetime(year=2024, month=2, day=12, hour=23),
        })

        self.project2_task_7.dependent_ids = self.project2_task_7.dependent_ids.sorted(key=lambda t: t.name)
        self.project2_task_8.write({
            'depend_on_ids': [Command.link(self.project2_task_10.id), Command.link(self.project2_task_7.id)],
            'dependent_ids': [Command.unlink(self.project2_task_0.id), Command.link(self.project2_task_13.id)],
        })

        (self.project2_task_4 + self.project2_task_6).write({
            'user_ids': [self.user2.id, self.user1.id],
        })

        (self.project2_task_9 + self.project2_task_10).write({
            'user_ids': [self.user1.id],
        })

        self.project2_task_2.write({
            'dependent_ids': [Command.link(self.project2_task_5.id)],
            'depend_on_ids': [Command.unlink(self.project2_task_7.id), Command.link(self.project2_task_4.id)],
        })

        self.project2_task_5.write({
            'dependent_ids': [Command.unlink(self.project2_task_7.id)]
        })

        self.project2_task_1.write({
            'dependent_ids': [Command.link(self.project2_task_4.id)]
        })

        self.project2_task_0.write({
            'user_ids': [self.user_projectuser.id, self.user1.id],
            'allocated_hours': 8,
        })

        self.gantt_reschedule_backward(self.project2_task_8, self.project2_task_13)
        self.assert_new_dates(
            self.project2_task_0,
            datetime(year=2024, month=2, day=7, hour=14),
            datetime(year=2024, month=2, day=8, hour=14),
        )

        self.assert_new_dates(
            self.project2_task_1,
            datetime(year=2024, month=2, day=8, hour=14),
            datetime(year=2024, month=2, day=9, hour=9),
        )

        self.assert_new_dates(
            self.project2_task_4,
            datetime(year=2024, month=2, day=9, hour=9),
            datetime(year=2024, month=2, day=14, hour=9),
            """
                allocated_hours = 16 Hours
                day 10 and 11 weekend
                day 12 public holiday
            """
        )

        self.assert_new_dates(
            self.project2_task_2,
            datetime(year=2024, month=2, day=21, hour=15),
            datetime(year=2024, month=2, day=21, hour=17),
        )

        self.assert_new_dates(
            self.project2_task_6,
            datetime(year=2024, month=2, day=14, hour=9),
            datetime(year=2024, month=2, day=21, hour=14),
            """
                allocated_hours = 20
                Raouf 2 off day 15 and 20
                Raouf 3 off day 16
                the task will be planned when both are available:
                    - 7 hours day 14
                    - 8 hours day 19
                    - 5 hours day 21
            """
        )

        self.assert_new_dates(
            self.project2_task_7,
            datetime(year=2024, month=2, day=21, hour=14),
            datetime(year=2024, month=2, day=27, hour=9),
        )

        self.assert_new_dates(
            self.project2_task_5,
            datetime(year=2024, month=2, day=22, hour=8),
            datetime(year=2024, month=2, day=23, hour=17),
        )

        self.assert_new_dates(
            self.project2_task_9,
            datetime(year=2024, month=2, day=26, hour=9),
            datetime(year=2024, month=2, day=26, hour=14),
        )

        self.assert_new_dates(
            self.project2_task_10,
            datetime(year=2024, month=2, day=26, hour=14),
            datetime(year=2024, month=2, day=27, hour=9),
        )

        self.assert_new_dates(
            self.project2_task_8,
            datetime(year=2024, month=2, day=27, hour=9),
            datetime(year=2024, month=2, day=29, hour=9),
        )
