# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo.fields import Command
from odoo.tests.common import users, tagged, freeze_time
from .gantt_reschedule_dates_common import ProjectEnterpriseGanttRescheduleCommon, fake_now


@tagged('gantt_reschedule', 'post_install', '-at_install')
@freeze_time(fake_now)
class TestGanttRescheduleOnTasks(ProjectEnterpriseGanttRescheduleCommon):

    def test_gantt_reschedule_date_not_active(self):
        """ This test purpose is to ensure that auto shift date feature is not active when it shouldn't:
            * When the task has no project (either the moved task or the linked one (depend_on_ids or dependent_ids).
            * When the calculated planned_start_date is prior to now.
        """

        def test_task_3_dates_unchanged(task_1_new_planned_dates, failed_message, domain_force=False, **context):
            task_1 = self.task_1.with_context(context) if domain_force else self.task_1.with_context(**context)
            task_1.write(task_1_new_planned_dates)
            self.gantt_reschedule_backward(self.task_1, self.task_3)
            self.assertEqual(self.task_3_planned_date_begin, self.task_3.planned_date_begin, failed_message)
            self.assertEqual(self.task_3_date_deadline, self.task_3.date_deadline, failed_message)
            task_1.write({
                'planned_date_begin': self.task_1_planned_date_begin,
                'date_deadline': self.task_1_date_deadline,
            })

        self.task_4.depend_on_ids = [Command.clear()]

        # Checks that no date shift is made when the moved task has no project_id
        failed_message = "The auto shift date feature should not be triggered after having moved a task that " \
                         "does not have a project_id."
        project_id = self.task_1.project_id
        self.task_1.write({
            'project_id': False
        })
        test_task_3_dates_unchanged(self.task_1_date_gantt_reschedule_trigger, failed_message)
        self.task_1.write({
            'project_id': project_id.id
        })

        # Checks that no date shift is made when the linked task has no project_id
        failed_message = "The auto shift date feature should not be triggered on tasks (depend_on_ids/dependent_ids) " \
                         "that do have a project_id."
        project_id = self.task_3.project_id
        self.task_3.write({
            'project_id': False
        })
        test_task_3_dates_unchanged(self.task_1_date_gantt_reschedule_trigger, failed_message)
        self.task_3.write({
            'project_id': project_id.id
        })

        # Checks that no date shift is made when the new planned_date is prior to the current datetime.
        with freeze_time(self.task_1_no_date_gantt_reschedule_trigger['planned_date_begin'] + relativedelta(weeks=1)):
            failed_message = "The auto shift date feature should not trigger any changes when the new planned_date " \
                             "is prior to the current datetime."
            test_task_3_dates_unchanged(self.task_1_date_gantt_reschedule_trigger, failed_message)

    def test_gantt_reschedule_dependent_task(self):
        """ This test purpose is to ensure that a task B that depends on a task A is shifted forward, up to after
            A date_deadline field value.

                             ┌─────────┐
                             │ Task 1  │
                             │         │
                             │ 24/06   │
                             │11H > 14H│
                             └─────────┘
                                   |
                                   |  ┌─────────┐
                                   |  │ Task 3  │
                                   -->│         │   task 3 should move to the right
                                      │ 24/06   │             =>
                                      │13H > 15H│
                                      └─────────┘
        """

        task_3_old_planned_date_begin, task_3_old_date_deadline = self.task_3.planned_date_begin, self.task_3.date_deadline
        self.task_1.write(self.task_1_date_gantt_reschedule_trigger)
        res = self.gantt_reschedule_forward(self.task_1, self.task_3)
        self.assert_old_tasks_vals(res, 'success', 'Reschedule done successfully.', self.task_3, {
            self.task_3.name: (task_3_old_planned_date_begin, task_3_old_date_deadline)
        })

        failed_message = "The auto shift date feature should move forward a dependent tasks."
        self.assertEqual(self.task_3.planned_date_begin, datetime(2021, 6, 24, 14), failed_message)
        self.assertEqual(self.task_3.date_deadline, datetime(2021, 6, 24, 16), failed_message)
        self.assertTrue(self.task_1.date_deadline <= self.task_3.planned_date_begin, failed_message)

        self.task_3.action_rollback_scheduling(res['old_vals_per_pill_id'])
        self.assertEqual(self.task_3.planned_date_begin, task_3_old_planned_date_begin)
        self.assertEqual(self.task_3.date_deadline, task_3_old_date_deadline)

    def test_gantt_reschedule_depend_on_task(self):
        """ This test purpose is to ensure that a task A that depends on a task B is shifted backward, up to before
            B planned_date_start field value.

                             ┌─────────┐
        task 1 should move   │ Task 1  │
            to the left      │         │
                <=           │ 24/06   │
                             │ 9H > 12H│
                             └─────────┘
                                   |
                                   |  ┌─────────┐
                                   |  │ Task 3  │
                                   -->│         │
                                      │ 24/06   │
                                      │11H > 13H│
                                      └─────────┘
        """
        self.task_3.write(self.task_3_date_gantt_reschedule_trigger)
        task_1_old_planned_date_begin, task_1_old_date_deadline = self.task_1.planned_date_begin, self.task_1.date_deadline
        res = self.gantt_reschedule_backward(self.task_1, self.task_3)
        self.assert_old_tasks_vals(res, 'success', 'Reschedule done successfully.', self.task_1, {
            self.task_1.name: (task_1_old_planned_date_begin, task_1_old_date_deadline)
        })
        failed_message = "The auto shift date feature should move backward a task the moved task depends on."
        self.assertEqual(self.task_1.planned_date_begin, datetime(2021, 6, 24, 8), failed_message)
        self.assertEqual(self.task_1.date_deadline, datetime(2021, 6, 24, 11), failed_message)
        self.assertTrue(self.task_3.planned_date_begin >= self.task_1.date_deadline, failed_message)

        self.task_1.action_rollback_scheduling(res['old_vals_per_pill_id'])
        self.assertEqual(self.task_1.planned_date_begin, task_1_old_planned_date_begin)
        self.assertEqual(self.task_1.date_deadline, task_1_old_date_deadline)

    @users('admin')
    # @warmup
    def test_gantt_reschedule_on_dependent_task_with_allocated_hours(self):
        """ This test purpose is to ensure that the task planned_date_fields (begin/end) are calculated accordingly to
            the allocated_hours if any. So if a dependent task has to be move forward up to before an unavailable period
            of time and that its allocated_hours is such that the date_deadline would fall into that unavailable
            period, then the date_deadline will be push forward after the unavailable period so that the
            allocated_hours constraint is met.
        """
        self.task_1.write({
            'planned_date_begin': self.task_3_planned_date_begin,
            'date_deadline': self.task_3_planned_date_begin + (self.task_1_date_deadline - self.task_1_planned_date_begin),
        })
        # FIXME as indeterminately fails. Suspected indeterminate cache invalidation.
        # with self.assertQueryCount(20):
        #     self.env.invalidate_all()
        self.gantt_reschedule_forward(self.task_1, self.task_3)
        failed_message = ("The auto shift date feature should take the allocated_hours into account and update the"
                         "date_deadline accordingly when moving a task forward.")
        self.assertEqual(
            self.task_3.date_deadline, self.task_3_date_deadline + relativedelta(days=1, hour=9),
            failed_message
        )

    @users('admin')
    # @warmup
    def test_gantt_reschedule_on_task_depending_on_with_allocated_hours(self):
        """ This test purpose is to ensure that the task planned_date_fields (planned_date_begin/date_deadline) are calculated accordingly to
            the allocated_hours if any. So if a task, that the current task depends on, has to be move backward up to
            after an unavailable period of time and that its allocated_hours is such that the date_deadline would fall
            into that unavailable period, then the planned_date_begin will be push backward before the unavailable
            period so that the allocated_hours constraint is met.
        """
        new_task_3_begin_date = self.task_1_date_deadline - timedelta(hours=2)
        self.task_3.write({
            'planned_date_begin': new_task_3_begin_date,
            'date_deadline': new_task_3_begin_date + (self.task_3_date_deadline - self.task_3_planned_date_begin),
        })
        # FIXME as indeterminately fails. Suspected indeterminate cache invalidation.
        # with self.assertQueryCount(38):
        #     self.env.invalidate_all()
        self.gantt_reschedule_backward(self.task_1, self.task_3)
        failed_message = ("The auto shift date feature should take the allocated_hours into account and update the"
                         "planned_date_begin accordingly when moving a task backward.")
        self.assertEqual(self.task_1.planned_date_begin,
                         self.task_1_planned_date_begin + relativedelta(days=-1, hour=16), failed_message)

    @users('admin')
    # @warmup
    def test_gantt_reschedule_on_dependent_task_without_allocated_hours(self):
        """ This test purpose is to ensure that the interval made by the task planned_date_fields (begin/end) is
            preserved when no allocated_hours is set.
        """
        self.task_3.write({
            'allocated_hours': 0,
        })
        self.task_1.write({
            'planned_date_begin': self.task_3_planned_date_begin,
            'date_deadline': self.task_3_planned_date_begin + (
                        self.task_1_date_deadline - self.task_1_planned_date_begin),
        })
        # FIXME as indeterminately fails. Suspected indeterminate cache invalidation.
        # with self.assertQueryCount(38):
        #     self.env.invalidate_all()
        self.gantt_reschedule_backward(self.task_1, self.task_3)
        failed_message = "When allocated_hours=0, the auto shift date feature should preserve the time interval between" \
                         "planned_date_begin and date_deadline when moving a task forward."
        self.assertEqual(self.task_3.date_deadline - self.task_3.planned_date_begin,
                         self.task_3_date_deadline - self.task_3_planned_date_begin, failed_message)

    @users('admin')
    # @warmup
    def test_gantt_reschedule_on_task_depending_on_without_allocated_hours(self):
        """ This test purpose is to ensure that the interval made by the task planned_date_fields (begin/end) is
            preserved when no allocated_hours is set.
        """
        new_task_3_begin_date = self.task_1_date_deadline - timedelta(hours=2)
        self.task_1.write({
            'allocated_hours': 0,
        })
        self.task_3.write({
            'planned_date_begin': new_task_3_begin_date,
            'date_deadline': new_task_3_begin_date + (self.task_3_date_deadline - self.task_3_planned_date_begin),
        })
        # FIXME as indeterminately fails. Suspected indeterminate cache invalidation.
        # with self.assertQueryCount(20):
        #     self.env.invalidate_all()
        self.gantt_reschedule_forward(self.task_1, self.task_3)
        failed_message = "The auto shift date feature should take the allocated_hours into account and update the" \
                         "planned_date_begin accordingly when moving a task backward."
        self.assertEqual(self.task_1.date_deadline - self.task_1.planned_date_begin,
                         self.task_1_date_deadline - self.task_1_planned_date_begin, failed_message)

    @users('admin')
    # @warmup
    def test_gantt_reschedule_next_work_time_with_allocated_hours(self):
        """ This test purpose is to ensure that computed dates are in accordance with the user resource_calendar
            if any is set, or with the user company resource_calendar if not.
        """
        new_task_1_planned_date_begin = self.task_3_planned_date_begin + timedelta(hours=1)
        self.task_1.write({
            'planned_date_begin': new_task_1_planned_date_begin,
            'date_deadline': new_task_1_planned_date_begin + (
                        self.task_1_date_deadline - self.task_1_planned_date_begin),
        })
        # FIXME as indeterminately fails. Suspected indeterminate cache invalidation.
        # with self.assertQueryCount(20):
        #     self.env.invalidate_all()
        self.gantt_reschedule_forward(self.task_1, self.task_3)
        failed_message = "The auto shift date feature should take the user company resource_calendar into account."
        self.assertEqual(self.task_3.planned_date_begin,
                         self.task_3_planned_date_begin + relativedelta(days=1, hour=8), failed_message)

    @users('admin')
    # @warmup
    def test_gantt_reschedule_previous_work_time_with_allocated_hours(self):
        """ This test purpose is to ensure that computed dates are in accordance with the user resource_calendar
            if any is set, or with the user company resource_calendar if not.
        """
        new_task_3_begin_date = self.task_1_planned_date_begin - timedelta(hours=1)
        self.task_3.write({
            'planned_date_begin': new_task_3_begin_date,
            'date_deadline': new_task_3_begin_date + (self.task_3_date_deadline - self.task_3_planned_date_begin),
        })
        # FIXME as indeterminately fails. Suspected indeterminate cache invalidation.
        # with self.assertQueryCount(38):
        #     self.env.invalidate_all()
        self.gantt_reschedule_backward(self.task_1, self.task_3)
        failed_message = "The auto shift date feature should take the user company resource_calendar into account."
        self.assertEqual(self.task_1.date_deadline,
                         self.task_1_date_deadline + relativedelta(days=-1, hour=17), failed_message)

    @users('admin')
    # @warmup
    def test_gantt_reschedule_next_work_time_without_allocated_hours(self):
        """ This test purpose is to ensure that computed dates are in accordance with the user resource_calendar
            if any is set, or with the user company resource_calendar if not.
        """
        new_task_1_planned_date_begin = self.task_3_planned_date_begin + timedelta(hours=1)
        self.task_3.write({
            'allocated_hours': 0,
        })
        self.task_1.write({
            'planned_date_begin': new_task_1_planned_date_begin,
            'date_deadline': new_task_1_planned_date_begin + (self.task_1_date_deadline - self.task_1_planned_date_begin),
        })
        # FIXME as indeterminately fails. Suspected indeterminate cache invalidation.
        # with self.assertQueryCount(20):
        #     self.env.invalidate_all()
        self.gantt_reschedule_forward(self.task_1, self.task_3)
        failed_message = "The auto shift date feature should take the user company resource_calendar into account."
        self.assertEqual(self.task_3.planned_date_begin,
                         self.task_3_planned_date_begin + relativedelta(days=1, hour=8), failed_message)

    @users('admin')
    # @warmup
    def test_gantt_reschedule_previous_work_time_without_allocated_hours(self):
        """ This test purpose is to ensure that computed dates are in accordance with the user resource_calendar
            if any is set, or with the user company resource_calendar if not.
        """
        new_task_3_begin_date = self.task_1_planned_date_begin - timedelta(hours=1)
        self.task_1.write({
            'allocated_hours': 0,
        })
        self.task_3.write({
            'planned_date_begin': new_task_3_begin_date,
            'date_deadline': new_task_3_begin_date + (self.task_3_date_deadline - self.task_3_planned_date_begin),
        })
        # FIXME as indeterminately fails. Suspected indeterminate cache invalidation.
        # with self.assertQueryCount(38):
        #     self.env.invalidate_all()
        self.gantt_reschedule_backward(self.task_1, self.task_3)
        failed_message = "The auto shift date feature should take the user company resource_calendar into account."
        self.assertEqual(self.task_1.date_deadline,
                         self.task_1_date_deadline + relativedelta(days=-1, hour=17), failed_message)

    @users('admin')
    # @warmup
    def test_gantt_reschedule_next_work_time_long_leaves(self):
        """ This test purpose is to ensure that computed dates are in accordance with the user resource_calendar
            if any is set, or with the user company resource_calendar if not. This test is made on a long leave period
            to ensure that it works when the new dates are further than the default fetched data. This test focuses on
            ensuring that a task is pushed forward up to after the holiday leave period when a task that it depends on
            is moved so that it creates an overlap between, the tasks.
        """
        self.task_3.write({
            'planned_date_begin': self.task_4_planned_date_begin,
            'date_deadline': self.task_4_planned_date_begin + (self.task_3_date_deadline - self.task_3_planned_date_begin),
        })
        # FIXME as indeterminately fails. Suspected indeterminate cache invalidation.
        # with self.assertQueryCount(37):
        #     self.env.invalidate_all()
        self.gantt_reschedule_forward(self.task_3, self.task_4)
        failed_message = "The auto shift date feature should take the user company resource_calendar into account and" \
                         "works also for long periods (requiring extending the search interval period)."
        self.assertEqual(self.task_4.planned_date_begin,
                         self.task_4_planned_date_begin + relativedelta(month=8, day=2, hour=8), failed_message)

    @users('admin')
    # @warmup
    def test_gantt_reschedule_previous_work_time_long_leaves(self):
        """ This test purpose is to ensure that computed dates are in accordance with the user resource_calendar
            if any is set, or with the user company resource_calendar if not. This test is made on a long leave period
            to ensure that it works when the new dates are further than the default fetched data. This test focuses on
            ensuring that a task is pushed backward up to before the holiday leave period when a dependent task is moved
            so that it creates an overlap between the tasks.
        """
        self.task_6.write({
            'planned_date_begin': self.task_5_planned_date_begin,
            'date_deadline': self.task_5_planned_date_begin + (
                        self.task_6_date_deadline - self.task_6_planned_date_begin),
        })
        # FIXME as indeterminately fails. Suspected indeterminate cache invalidation.
        # with self.assertQueryCount(31):
        #     self.env.invalidate_all()
        self.gantt_reschedule_backward(self.task_5, self.task_6)
        failed_message = "The auto shift date feature should take the user company resource_calendar into account and" \
                         "works also for long periods (requiring extending the search interval period)."
        self.assertEqual(self.task_5.date_deadline,
                         self.task_5_date_deadline + relativedelta(month=6, day=30, hour=17), failed_message)

    @users('admin')
    # @warmup
    def test_gantt_reschedule_cascading_forward(self):
        """ This test purpose is to ensure that the cascade is well supported on dependent tasks
            (task A move impacts B that moves forwards and then impacts C that is moved forward).
            Project structure for this test (check ProjectEnterpriseGanttRescheduleCommon for the initial structure)

            ┌─────────┐      ┌─────────┐              ┌─────────┐      ┌─────────┐
            │ Task 1  │ -->  │ Task 3  │        ----->│ Task 5  │ -->  │ Task 6  │
            │         │      │         │        |     │02/08 8H │      │         │
            │ 24/06   │      │ 30/06   │        |     │   ->    │      │ 10/08   │
            │ 9H > 12H│      │14H > 16H│        |     │03/08 17H│      │ 8H->17H │
            └─────────┘      └─────────┘        |     └─────────┘      └─────────┘
                                |               |
                                |  ┌─────────┐  |
                                |  │ Task 4  │  |
                                -->│         │---
                                   │ 30/06   │
                                   │15H > 17H│
                                   └─────────┘
            Task 4 will move after task 3, it will create a conflict with task 5 so it should be moved to resolve
            this conflict, task 6 should not move as after moving both 4 and 5, no conflict will be creating with task 6.
        """
        new_task_3_planned_date_begin = self.task_4_planned_date_begin - timedelta(hours=1)
        self.task_3.write({
            'planned_date_begin': new_task_3_planned_date_begin,
            'date_deadline': new_task_3_planned_date_begin + (self.task_3_date_deadline - self.task_3_planned_date_begin),
        })
        new_task_6_planned_date_begin = datetime(year=2021, month=8, day=10, hour=8)
        self.task_6.write({
            'planned_date_begin': new_task_6_planned_date_begin,
            'date_deadline': new_task_6_planned_date_begin + (self.task_6_date_deadline - self.task_6_planned_date_begin),
        })
        initial_dates = {
            'Pigs UserTask 6': (self.task_6.planned_date_begin, self.task_6.date_deadline),
        }
        # FIXME as indeterminately fails. Suspected indeterminate cache invalidation.
        # with self.assertQueryCount(43):
        #     self.env.invalidate_all()
        self.gantt_reschedule_forward(self.task_3, self.task_4)
        failed_message = "The auto shift date feature should handle correctly dependencies cascades."
        self.assertEqual(self.task_4.planned_date_begin,
                         self.task_3.date_deadline, failed_message)
        self.assertEqual(self.task_4.date_deadline,
                         self.task_4_planned_date_begin + relativedelta(month=8, day=2, hour=9), failed_message)
        self.assertEqual(self.task_5.planned_date_begin,
                         self.task_4.date_deadline, failed_message)
        self.assertEqual(self.task_5.date_deadline,
                         self.task_5_date_deadline + relativedelta(days=1, hour=9), failed_message)
        self.assert_task_not_replanned(self.task_6, initial_dates)

    @users('admin')
    # @warmup
    def test_gantt_reschedule_cascading_backward(self):
        """ This test purpose is to ensure that the cascade is well supported on tasks that the current task depends on
            (task A move impacts B that moves backward and then impacts C that is moved backward).
        """
        new_task_6_planned_date_begin = self.task_5_planned_date_begin + timedelta(hours=1)
        self.task_6.write({
            'planned_date_begin': new_task_6_planned_date_begin,
            'date_deadline': new_task_6_planned_date_begin + (self.task_6_date_deadline - self.task_6_planned_date_begin),
        })
        # FIXME as indeterminately fails. Suspected indeterminate cache invalidation.
        # with self.assertQueryCount(35):
        #     self.env.invalidate_all()
        self.gantt_reschedule_backward(self.task_5, self.task_6)
        failed_message = "The auto shift date feature should handle correctly dependencies cascades."
        self.assertEqual(self.task_5.date_deadline,
                         new_task_6_planned_date_begin, failed_message)
        self.assertEqual(self.task_5.planned_date_begin,
                         datetime(year=2021, month=6, day=29, hour=9), failed_message)
        self.assertEqual(self.task_4.date_deadline,
                         self.task_5.planned_date_begin, failed_message)
        self.assertEqual(self.task_4.planned_date_begin,
                         datetime(year=2021, month=6, day=28, hour=16), failed_message)

    def test_gantt_reschedule_project_user(self):
        """ This test purpose is to ensure that the project user has the sufficient rights to trigger a gantt
            reschedule.
        """
        new_task_6_planned_date_begin = self.task_5_planned_date_begin + timedelta(hours=1)
        self.task_6.with_user(self.user_projectuser).write({
            'planned_date_begin': new_task_6_planned_date_begin,
            'date_deadline': new_task_6_planned_date_begin + (self.task_6_date_deadline - self.task_6_planned_date_begin),
        })
        self.gantt_reschedule_backward(self.task_5, self.task_6)
        failed_message = "The auto shift date feature should handle correctly dependencies cascades."
        self.assertEqual(self.task_5.date_deadline,
                         new_task_6_planned_date_begin, failed_message)
        self.assertEqual(self.task_5.planned_date_begin,
                         datetime(year=2021, month=6, day=29, hour=9), failed_message)
        self.assertEqual(self.task_4.date_deadline,
                         self.task_5.planned_date_begin, failed_message)
        self.assertEqual(self.task_4.planned_date_begin,
                         datetime(year=2021, month=6, day=28, hour=16), failed_message)

    @users('admin')
    def test_project2_reschedule_cascading_forward(self):
        """
            This test concerns project2 tasks, when the right arrow is clicked. task 0 should move ahead of task 8.
            As tasks 1, 2, 3 are children of 0, they should be done after it,
            they should also be moved forward in one of this 2 valid orders
                1- ['0', '1', '2', '3']
                2- ['0', '1', '3', '2']
                but it will be usually the first option as task 3 is the first in the dependent_ids of task 1
            All the other tasks should not move.
        """
        self.project2_task_1.dependent_ids = self.project2_task_1.dependent_ids.sorted(key=lambda t: t.name, reverse=True)
        self.gantt_reschedule_forward(self.project2_task_8, self.project2_task_0)
        self.assert_task_not_replanned(
            self.project2_task_4 | self.project2_task_5 | self.project2_task_6 | self.project2_task_7 | self.project2_task_8 | self.project2_task_9 |
            self.project2_task_10 | self.project2_task_11 | self.project2_task_12 | self.project2_task_13 | self.project2_task_14,
            self.initial_dates,
        )

        self.assert_new_dates(
            self.project2_task_0,
            datetime(year=2024, month=3, day=18, hour=8),
            datetime(year=2024, month=3, day=18, hour=12),
            "task 0 duration = 4 Hours. 4 hours will be planned on 18/03/2024 from 8H to 12H"
        )

        self.assert_new_dates(
            self.project2_task_1,
            datetime(year=2024, month=3, day=18, hour=13),
            datetime(year=2024, month=3, day=18, hour=17),
            "task 1 duration = 4 Hours. 4 hours will be planned on 18/03/2024 from 13H to 17H"
        )

        self.assert_new_dates(
            self.project2_task_2,
            datetime(year=2024, month=3, day=19, hour=8),
            datetime(year=2024, month=3, day=19, hour=10),
            "task 2 duration = 2 Hours. 2 hours will be planned on 19/03/2024 from 8H to 10H"
        )

        self.assert_new_dates(
            self.project2_task_3,
            datetime(year=2024, month=3, day=19, hour=10),
            datetime(year=2024, month=3, day=19, hour=16),
            "task 3 duration = 5 Hours. 5 hours will be planned on 19/03/2024 from 10H to 16H"
        )

    @users('admin')
    def test_project2_reschedule_cascading_backward(self):
        """
            This test concerns project2 tasks, when the left arrow is clicked. task 8 should be moved behind task 0
            As tasks 4, 6, 5, 7 are ancestors for 8 and should be done before it, they should be moved backward.
            A valid topo order can be:
                1- ['8', '7', '5', '6', '4']
                2- ['8', '7', '6', '4', '5']
                it will be usually 2 as task 5 is the first in the depend_on_ids of task 7.
            9 and 10 should not be impacted as they are not ancestors of 8.
            We shouldn't have conflicts with 11, 12, 13 and 14 that are already planned in the past
            All the other tasks should not move.
        """
        self.project2_task_7.depend_on_ids = self.project2_task_7.depend_on_ids.sorted(key=lambda t: t.name)
        self.gantt_reschedule_backward(self.project2_task_8, self.project2_task_0)
        self.assert_task_not_replanned(
            self.project2_task_0 | self.project2_task_1 | self.project2_task_2 | self.project2_task_3 | self.project2_task_9 |
            self.project2_task_10 | self.project2_task_11 | self.project2_task_12 | self.project2_task_13 | self.project2_task_14,
            self.initial_dates,
        )

        self.assert_new_dates(
            self.project2_task_8,
            datetime(year=2024, month=2, day=27, hour=10),
            datetime(year=2024, month=2, day=29, hour=17),
            """
                task 8 duration = 13 Hours.
                Only 2 hours available on 29/02/2024 because task 12 and 13 are planned from 9H to 16H.
                Only 5 hours available on 28/02/2024 because task 11 is planned from 8H to 11H.
                The remaining 6 hours will be planned in 27/02/2024 from 10H
            """
        )
        self.assert_new_dates(
            self.project2_task_7,
            datetime(year=2024, month=2, day=26, hour=15),
            datetime(year=2024, month=2, day=27, hour=10),
            """
                task 7 duration = 4 Hours.
                2 hours available on 27/02/2024 from 8H to 10H.
                2 hours available on 26/02/2024 from 15H to 17H.
            """
        )

        self.assert_new_dates(
            self.project2_task_6,
            datetime(year=2024, month=2, day=21, hour=13),
            datetime(year=2024, month=2, day=23, hour=17),
            """
                task 6 duration = 20 Hours.
                no hours available in 26/02/2024 as task 7 was planned from 15H to 17H
                and task 14 planned from 8H to 15H
                16 hours will be planned on 22/02 and 23/02
                4 hours will be planned on 21/02 from 13H to 17H
            """
        )

        self.assert_new_dates(
            self.project2_task_4,
            datetime(year=2024, month=2, day=19, hour=13),
            datetime(year=2024, month=2, day=21, hour=12),
            """
                task 4 duration = 16 Hours
                4 Hours on 19/02
                8 hours on 20/02
                4 hours on 21/02 from 8H to 12H
            """
        )

        self.assert_new_dates(
            self.project2_task_5, datetime(year=2024, month=2, day=15, hour=13),
            datetime(year=2024, month=2, day=19, hour=12),
            """
                task 5 duration = 16 Hours.
                4 hours will be planned on 19/02
                8 hours will be planned on 16/02
                4 hours will be planned on 15 from 13H to 17H
            """
        )

    @users('admin')
    def test_project2_reschedule_cascading_backward_no_planning_in_the_past(self):
        """
        This test concerns project2 tasks, when the left arrow is clicked. task 8 should be moved behind task 0
        As tasks 4, 6, 5, 7 are ancestors for 8 and should be done before it, they should be moved backward.
        As we can't plan taks in the past and there are no available intervals to plan, so they should be
        planned starting from now and it will create conflicts

        fake now (01/04)                 07/04
                |                          |
                |                          |
                |                          |

                   [ 7 ]--->[8]----->[0]->[1]->[2]
                [ 6 ]
                [ 4 ]
                [ 5 ]
        """
        self.project2_task_0.planned_date_begin = datetime(year=2021, month=4, day=7, hour=8)
        res = self.gantt_reschedule_backward(self.project2_task_8, self.project2_task_0)
        moved_tasks = self.project2_task_8 + self.project2_task_7 + self.project2_task_6 + self.project2_task_5 + self.project2_task_4
        self.assert_old_tasks_vals(res, 'info',
            'Some tasks were scheduled concurrently, resulting in a conflict due to the limited availability of the assignees. The planned dates for these tasks may not align with their allocated hours.',
            moved_tasks, self.initial_dates
        )

        self.assert_new_dates(
            self.project2_task_8,
            datetime(year=2021, month=4, day=5, hour=11),
            datetime(year=2021, month=4, day=6, hour=17),
            """
                task 8 duration = 13 Hours.
                8 hours to plan on 06/04
                5 hours to plan on 05/04 from 11H to 17H
            """
        )

        self.assert_new_dates(
            self.project2_task_7,
            datetime(year=2021, month=4, day=2, hour=16),
            datetime(year=2021, month=4, day=5, hour=11),
            """
                task 8 duration = 4 Hours.
                5 hours to plan on 05/04 from 8H to 11H
                1 hour to plan on 02/04 from 16H to 17H
            """
        )

        self.assert_new_dates(
            self.project2_task_5,
            datetime(year=2021, month=4, day=1, hour=8),
            datetime(year=2021, month=4, day=2, hour=17),
            """
                task 8 duration = 16 Hours.
                No available slot to plan it, so it will be planned in conflict starting from the first available slot 01/04/2021
            """
        )

        self.assert_new_dates(
            self.project2_task_6,
            datetime(year=2021, month=4, day=1, hour=8),
            datetime(year=2021, month=4, day=5, hour=12),
            """
                task 8 duration = 20 Hours.
                No available slot to plan it, so it will be planned in conflict starting from the first available slot 01/04/2021
            """
        )

        self.assert_new_dates(
            self.project2_task_4,
            datetime(year=2021, month=4, day=1, hour=8),
            datetime(year=2021, month=4, day=2, hour=17),
            """
                task 8 duration = 16 Hours.
                No available slot to plan it, so it will be planned in conflict starting from the first available slot 01/04/2021
            """
        )

        moved_tasks.action_rollback_scheduling(res['old_vals_per_pill_id'])
        self.assert_task_not_replanned(moved_tasks, self.initial_dates)

    @users('admin')
    def test_compute_task_duration(self):
        """
            when task allocated_hours = 0, duration is computed as the intersection of work intervals and [planned_date_begin, date_deadline]
            example: task 6 is planned from datetime(2024, 3, 9, 8, 0) to datetime(2024, 3, 13, 12, 0)
            duration is 20:
            - 0 on 09/03 and 10/03 as it's weekend
            - 8 on 11/03
            - 8 on 12/03
            - 4 from 8H to 12H
        """
        durations = self.project2_task_6._get_tasks_durations(self.user_projectuser, 'planned_date_begin', 'date_deadline')
        self.assertEqual(durations[self.project2_task_6.id], 20 * 3600)

    @users('admin')
    def test_backward_cross_project(self):
        """
            When the move back/for{ward} concerns 2 tasks from 2 different projects, it's done
            exactly like the previous cases (tasks belonging to same project). There is nothing
            special for this case.

            Test dependencies Project     [5]---       ---->[6]---      -->[8]
                                               |       |         |      |
            project_pigs                       |    [4]-         --->[7]-
                                               |_________________|
        """
        self.project2_task_7.dependent_ids = self.project2_task_7.dependent_ids.sorted(key=lambda t: t.name)
        (self.project2_task_0 + self.project2_task_4 + self.project2_task_7).project_id = self.project_pigs.id
        self.gantt_reschedule_backward(self.project2_task_8, self.project2_task_0)
        self.assert_task_not_replanned(
            self.project2_task_0 | self.project2_task_1 | self.project2_task_2 | self.project2_task_3 | self.project2_task_9 |
            self.project2_task_10 | self.project2_task_11 | self.project2_task_12 | self.project2_task_13 | self.project2_task_14,
            self.initial_dates,
        )

        self.assert_new_dates(
            self.project2_task_8,
            datetime(year=2024, month=2, day=27, hour=10),
            datetime(year=2024, month=2, day=29, hour=17),
            """
                task 8 duration = 13 Hours.
                Only 2 hours available on 29/02/2024 because task 12 and 13 are planned from 9H to 16H.
                Only 5 hours available on 28/02/2024 because task 11 is planned from 8H to 11H.
                The remaining 6 hours will be planned in 27/02/2024 from 10H
            """
        )
        self.assert_new_dates(
            self.project2_task_7,
            datetime(year=2024, month=2, day=26, hour=15),
            datetime(year=2024, month=2, day=27, hour=10),
            """
                task 8 duration = 4 Hours.
                2 hours available on 27/02/2024 from 8H to 10H.
                2 hours available on 26/02/2024 from 15H to 17H.
            """
        )

        self.assert_new_dates(
            self.project2_task_5,
            datetime(year=2024, month=2, day=15, hour=13),
            datetime(year=2024, month=2, day=19, hour=12),
            """
                task 5 duration = 16 Hours.
                day 17/02 and 18/02 are weekend
                4 hours planned on day 15/02
                8 hours planned on day 16/02
                4 hours planned on day 19/02
            """
        )

        self.assert_new_dates(
            self.project2_task_6,
            datetime(year=2024, month=2, day=21, hour=13),
            datetime(year=2024, month=2, day=23, hour=17),
            """
                task 6 duration = 20 Hours.
                4 Hours on 21/02, 16 Hours on 22/02 and 23/02
            """
        )

        self.assert_new_dates(
            self.project2_task_4,
            datetime(year=2024, month=2, day=19, hour=13),
            datetime(year=2024, month=2, day=21, hour=12),
            """
                task 4 duration = 16 Hours
                4 Hours on 19/02
                8 hours on 20/02
                4 hours on 21/02 from 8H to 12H
            """
        )

    def test_move_forward_without_conflicts(self):
        """
                                      [4]->[6]
                                            |
                      ----------<x>-------- |
                      |                   | |    [15]
                      |                   | |     |
                      |                   v v     v
                     [0]->[1]->[2]->[5]->[ 7 ]->[ 8 ]------------>[13]->[ 14 ]--------->[16]
                           |          |                                  ^  ^
                           v          v                                  |  |
                          [3]        [9]->[10]----------------------------  |
                           |                                                |
                           v                                                |
                          [11]->[12]-----------------------------------------

            if we move forward task 0 to task 7,
            first, we need to advance the children of 0 that are at the same time ancestors of 7 (excluded)
            with respecting the topological sort for sure (0, 1, 2, 5)
            second, after advancing 0, 1, 2, 5, their children 3, 11, 12 (children of 1), 9, 10 (children of 5) will become in conflict
            (planned before their parent) so they need to be moved,
            14 and 16 are also children but there are still in a valid position so they don't need to move.

            3, 11, 12, 9, 10 should also be moved forward after 7.
            9, 10, 3, 11, 12 is also a valid order but in this test it will be second order as 2 will be visited
            before 3 from 1
            4, 6, 7, 15, 8, 13 should not be moved
            14 and 16 should not move as they're not impacted by any conflict created by any moved task
        """
        initial_dates_deep_copy = dict(self.initial_dates)
        initial_dates_deep_copy['8'] = (datetime(2024, 3, 22, 13, 0), datetime(2024, 3, 22, 17, 0))
        self.project2_task_8.write({
            'planned_date_begin': initial_dates_deep_copy['8'][0],
            'date_deadline': initial_dates_deep_copy['8'][1],
            'dependent_ids': [Command.link(self.project2_task_13.id), Command.unlink(self.project2_task_0.id)],
        })
        initial_dates_deep_copy['7'] = (datetime(2024, 3, 21, 13, 0), datetime(2024, 3, 21, 17, 0))
        self.project2_task_7.write({
            'planned_date_begin': initial_dates_deep_copy['7'][0],
            'date_deadline': initial_dates_deep_copy['7'][1],
            'depend_on_ids': [Command.link(self.project2_task_0.id)]
        })
        initial_dates_deep_copy['5'] = (datetime(2024, 3, 7, 8, 0), datetime(2024, 3, 8, 17, 0))
        self.project2_task_5.write({
            'planned_date_begin': initial_dates_deep_copy['5'][0],
            'date_deadline': initial_dates_deep_copy['5'][1],
            'depend_on_ids': [Command.link(self.project2_task_2.id)]
        })
        initial_dates_deep_copy['15'] = (datetime(2024, 3, 22, 8, 0), datetime(2024, 3, 22, 12, 0))
        initial_dates_deep_copy['16'] = (datetime(2024, 6, 3, 13, 0), datetime(2024, 6, 5, 17, 0))
        task_15, task_16 = self.ProjectTask.create([{
            'name': '15',
            'user_ids': self.user_projectuser,
            'project_id': self.project2.id,
            'dependent_ids': [Command.link(self.project2_task_8.id)],
            'planned_date_begin': initial_dates_deep_copy['15'][0],
            'date_deadline': initial_dates_deep_copy['15'][1],
        }, {
            'name': '16',
            'user_ids': self.user_projectuser,
            'project_id': self.project2.id,
            'planned_date_begin': initial_dates_deep_copy['16'][0],
            'date_deadline': initial_dates_deep_copy['16'][1],
            'depend_on_ids': [Command.link(self.project2_task_14.id)],
        }])

        initial_dates_deep_copy['13'] = (datetime(2024, 4, 3, 8, 0), datetime(2024, 4, 3, 12, 0))
        self.project2_task_13.write({
            'planned_date_begin': initial_dates_deep_copy['13'][0],
            'date_deadline': initial_dates_deep_copy['13'][1],
        })
        initial_dates_deep_copy['14'] = (datetime(2024, 4, 3, 13, 0), datetime(2024, 4, 5, 17, 0))
        self.project2_task_14.write({
            'planned_date_begin': initial_dates_deep_copy['14'][0],
            'date_deadline': initial_dates_deep_copy['14'][1],
            'depend_on_ids': [Command.link(self.project2_task_13.id), Command.link(self.project2_task_10.id), Command.link(self.project2_task_12.id)],
        })
        initial_dates_deep_copy['11'] = (datetime(2024, 3, 15, 13, 0), datetime(2024, 3, 18, 17, 0))
        self.project2_task_11.write({
            'planned_date_begin': initial_dates_deep_copy['11'][0],
            'date_deadline': initial_dates_deep_copy['11'][1],
            'depend_on_ids': [Command.link(self.project2_task_3.id)],
        })
        initial_dates_deep_copy['12'] = (datetime(2024, 3, 19, 8, 0), datetime(2024, 3, 20, 12, 0))
        self.project2_task_12.write({
            'planned_date_begin': initial_dates_deep_copy['12'][0],
            'date_deadline': initial_dates_deep_copy['12'][1],
            'depend_on_ids': [Command.link(self.project2_task_11.id)],
        })
        self.project2_task_3.allocated_hours = 4
        self.project2_task_1.dependent_ids = self.project2_task_1.dependent_ids.sorted(key=lambda t: t.name)
        not_moved_tasks = self.project2_task_4 | self.project2_task_6 | self.project2_task_7 | self.project2_task_8 | task_15 | self.project2_task_13 | task_16 | self.project2_task_14
        moved_tasks = self.project2.task_ids - not_moved_tasks
        res = self.gantt_reschedule_forward(self.project2_task_0, self.project2_task_7)
        self.assert_old_tasks_vals(res, 'success', 'Reschedule done successfully.', moved_tasks, initial_dates_deep_copy)

        self.assert_task_not_replanned(
            not_moved_tasks,
            initial_dates_deep_copy,
        )

        # assert tasks [0]->[1]->[2]->[5] planned first just before [7]
        self.assert_new_dates(
            self.project2_task_5,
            datetime(year=2024, month=3, day=19, hour=13),
            datetime(year=2024, month=3, day=21, hour=12),
            """
                task 5 duration = 16 Hours
                4 Hours on 19/03
                8 hours on 20/03
                4 Hours on 21/03
            """
        )

        self.assert_new_dates(
            self.project2_task_2,
            datetime(year=2024, month=3, day=19, hour=10),
            datetime(year=2024, month=3, day=19, hour=12),
            """
                task 2 duration = 2 Hours
                2 Hours on 19/03
            """
        )

        self.assert_new_dates(
            self.project2_task_1,
            datetime(year=2024, month=3, day=18, hour=15),
            datetime(year=2024, month=3, day=19, hour=10),
            """
                task 1 duration = 4 Hours
                2 Hours on 18/03 and 2 Hours on 19/03
            """
        )
        self.assert_new_dates(
            self.project2_task_0,
            datetime(year=2024, month=3, day=18, hour=10),
            datetime(year=2024, month=3, day=18, hour=15),
            """
                task 0 duration = 4 Hours
                4 Hours on 18/03
            """
        )

        # assert 3, 11, 12, 9, 10 planned after 7
        self.assert_new_dates(
            self.project2_task_3,
            datetime(year=2024, month=3, day=25, hour=8),
            datetime(year=2024, month=3, day=25, hour=12),
            """
                task 3 duration = 4 Hours
                4 Hours on 25/03
            """
        )
        self.assert_new_dates(
            self.project2_task_11,
            datetime(year=2024, month=3, day=25, hour=13),
            datetime(year=2024, month=3, day=26, hour=17),
            """
                task 11 duration = 12 Hours
                4 Hours on 25/03
                8 Hours on 26/03
            """
        )
        self.assert_new_dates(
            self.project2_task_12,
            datetime(year=2024, month=3, day=27, hour=8),
            datetime(year=2024, month=3, day=28, hour=12),
            """
                task 12 duration = 12 Hours
                8 Hours on 27/03
                4 Hours on 28/03
            """
        )
        self.assert_new_dates(
            self.project2_task_9,
            datetime(year=2024, month=3, day=28, hour=13),
            datetime(year=2024, month=3, day=28, hour=17),
            """
                task 9 duration = 4 Hours
                4 Hours on 28/03
            """
        )
        self.assert_new_dates(
            self.project2_task_10,
            datetime(year=2024, month=3, day=29, hour=8),
            datetime(year=2024, month=3, day=29, hour=12),
            """
                task 10 duration = 4 Hours
                4 Hours on 29/03
            """
        )

        moved_tasks.action_rollback_scheduling(res['old_vals_per_pill_id'])
        self.assert_task_not_replanned(moved_tasks, initial_dates_deep_copy)

    def test_move_backward_without_conflicts(self):
        """
                  [16]<------------------
                                        |
        [18]--------------------->[4]->[6]---------
                                                  |
                            ----------<x>-------- |
                            |                   | |    [15]
                            |                   | |     |
                            |                   v v     v
        [17]-------------->[0]->[1]->[2]->[5]->[ 7 ]->[ 8 ]------------>[13]->[ 14 ]
                                 |          |                                  ^ ^
                                 v          v                                  | |
                                [3]        [9]->[10]---------------------------- |
                                 |                                               |
                                 v                                               |
                                [11]->[12]----------------------------------------

            if we move backward task 7 to task 0, we need to move all the ancestors of 7 stopping at 0
            (1, 2, 5, 4, 6, 7)
            the children of 0 that are at the same time ancestors of 7 should be planned after 0
            with respecting the topological sort for sure (1, 2, 5, 7)
            4, 6 should also be moved to avoid creating conflicts as 7 will be moved and they should stay planned
            before 7.
            18 should not be moved as after moving 4 and 6, no conflict created with task 18
            3, 11, 12, 9, 10, 8, 15, 13, 14, 16, 17 should not be moved
        """
        initial_dates_deep_copy = dict(self.initial_dates)
        initial_dates_deep_copy['8'] = (datetime(2024, 3, 22, 13, 0), datetime(2024, 3, 22, 17, 0))
        self.project2_task_8.write({
            'planned_date_begin': initial_dates_deep_copy['8'][0],
            'date_deadline': initial_dates_deep_copy['8'][1],
            'dependent_ids': [Command.link(self.project2_task_13.id), Command.unlink(self.project2_task_0.id)],
        })
        initial_dates_deep_copy['7'] = (datetime(2024, 3, 21, 13, 0), datetime(2024, 3, 21, 17, 0))
        self.project2_task_7.write({
            'planned_date_begin': initial_dates_deep_copy['7'][0],
            'date_deadline': initial_dates_deep_copy['7'][1],
            'depend_on_ids': [Command.link(self.project2_task_0.id)]
        })
        initial_dates_deep_copy['5'] = (datetime(2024, 3, 7, 8, 0), datetime(2024, 3, 8, 17, 0))
        self.project2_task_5.write({
            'planned_date_begin': initial_dates_deep_copy['5'][0],
            'date_deadline': initial_dates_deep_copy['5'][1],
            'depend_on_ids': [Command.link(self.project2_task_2.id)]
        })
        initial_dates_deep_copy['15'] = (datetime(2024, 3, 22, 8, 0), datetime(2024, 3, 22, 12, 0))
        initial_dates_deep_copy['16'] = (datetime(2024, 2, 22, 8, 0), datetime(2024, 2, 22, 12, 0))
        initial_dates_deep_copy['17'] = (datetime(2024, 2, 1, 8, 0), datetime(2024, 2, 1, 12, 0))
        initial_dates_deep_copy['18'] = (datetime(2024, 2, 1, 8, 0), datetime(2024, 2, 1, 12, 0))

        self.ProjectTask.create([{
                'name': '15',
                "user_ids": self.user_projectuser,
                "project_id": self.project2.id,
                'dependent_ids': [Command.link(self.project2_task_8.id)],
                'planned_date_begin': initial_dates_deep_copy['15'][0],
                'date_deadline': initial_dates_deep_copy['15'][1],
            },
            {
                'name': '16',
                "user_ids": self.user_projectuser,
                "project_id": self.project2.id,
                'depend_on_ids': [Command.link(self.project2_task_6.id)],
                'planned_date_begin': initial_dates_deep_copy['16'][0],
                'date_deadline': initial_dates_deep_copy['16'][1],
            },
            {
                'name': '17',
                "user_ids": self.user_projectuser,
                "project_id": self.project2.id,
                'dependent_ids': [Command.link(self.project2_task_0.id)],
                'planned_date_begin': initial_dates_deep_copy['17'][0],
                'date_deadline': initial_dates_deep_copy['17'][1],
            },
            {
                'name': '18',
                "user_ids": self.user_projectuser,
                "project_id": self.project2.id,
                'dependent_ids': [Command.link(self.project2_task_4.id)],
                'planned_date_begin': initial_dates_deep_copy['18'][0],
                'date_deadline': initial_dates_deep_copy['18'][1],
            }
        ])

        initial_dates_deep_copy['13'] = (datetime(2024, 4, 3, 8, 0), datetime(2024, 4, 3, 12, 0))
        self.project2_task_13.write({
            'planned_date_begin': initial_dates_deep_copy['13'][0],
            'date_deadline': initial_dates_deep_copy['13'][1],
        })
        initial_dates_deep_copy['14'] = (datetime(2024, 4, 3, 13, 0), datetime(2024, 4, 5, 17, 0))
        self.project2_task_14.write({
            'planned_date_begin': initial_dates_deep_copy['14'][0],
            'date_deadline': initial_dates_deep_copy['14'][1],
            'depend_on_ids': [Command.link(self.project2_task_13.id), Command.link(self.project2_task_10.id), Command.link(self.project2_task_12.id)],
        })
        initial_dates_deep_copy['11'] = (datetime(2024, 3, 15, 13, 0), datetime(2024, 3, 18, 17, 0))
        self.project2_task_11.write({
            'planned_date_begin': initial_dates_deep_copy['11'][0],
            'date_deadline': initial_dates_deep_copy['11'][1],
            'depend_on_ids': [Command.link(self.project2_task_3.id)],
        })
        initial_dates_deep_copy['12'] = (datetime(2024, 3, 19, 8, 0), datetime(2024, 3, 20, 12, 0))
        self.project2_task_12.write({
            'planned_date_begin': initial_dates_deep_copy['12'][0],
            'date_deadline': initial_dates_deep_copy['12'][1],
            'depend_on_ids': [Command.link(self.project2_task_11.id)],
        })
        self.project2_task_3.allocated_hours = 4
        self.project2_task_1.dependent_ids = self.project2_task_1.dependent_ids.sorted(key=lambda t: t.name)

        initial_dates_deep_copy['6'] = (datetime(2024, 3, 5, 13, 0), datetime(2024, 3, 5, 17, 0))
        self.project2_task_6.write({
            'planned_date_begin': initial_dates_deep_copy['6'][0],
            'date_deadline': initial_dates_deep_copy['6'][1],
        })

        initial_dates_deep_copy['4'] = (datetime(2024, 3, 4, 8, 0), datetime(2024, 3, 4, 12, 0))
        self.project2_task_4.write({
            'planned_date_begin': initial_dates_deep_copy['4'][0],
            'date_deadline': initial_dates_deep_copy['4'][1],
        })

        moved_tasks = self.project2_task_1 | self.project2_task_2 | self.project2_task_5 | self.project2_task_7 | self.project2_task_6 | self.project2_task_4
        not_moved_tasks = self.project2.task_ids - moved_tasks
        res = self.gantt_reschedule_backward(self.project2_task_0, self.project2_task_7)
        self.assert_old_tasks_vals(res, 'success', 'Reschedule done successfully.', moved_tasks, initial_dates_deep_copy)
        self.assert_task_not_replanned(
            not_moved_tasks,
            initial_dates_deep_copy,
        )

        self.assert_new_dates(
            self.project2_task_1,
            datetime(year=2024, month=3, day=1, hour=13),
            datetime(year=2024, month=3, day=1, hour=17),
            """
                task 1 duration = 4 Hours
                4 Hours on 01/03
            """
        )

        self.assert_new_dates(
            self.project2_task_2,
            datetime(year=2024, month=3, day=4, hour=8),
            datetime(year=2024, month=3, day=4, hour=10),
            """
                task 2 duration = 2 Hours
                2 Hours on 04/03
            """
        )

        self.assert_new_dates(
            self.project2_task_5,
            datetime(year=2024, month=3, day=4, hour=10),
            datetime(year=2024, month=3, day=6, hour=10),
            """
                task 5 duration = 16 Hours
                6 Hours on 04/03
                8 Hours on 05/03
                2 Hours on 06/03
            """
        )

        self.assert_new_dates(
            self.project2_task_7,
            datetime(year=2024, month=3, day=6, hour=10),
            datetime(year=2024, month=3, day=6, hour=15),
            """
                task 7 duration = 4 Hours
                4 Hours on 06/03
            """
        )

        # the project will automatically be timesheetable since the default value is true and so the allocated_hours will
        # not be recomputed when the project is timesheetable since we assume the user will manually set the allocated
        # hours on his tasks to correctly timesheets.
        allocated_hours = 4
        day = 21
        start_project2_task4 = 21
        hour_task4 = 8
        if self.is_module_timesheet_grid_installed:
            day = 19
            allocated_hours = 20
            start_project2_task4 = 15
            hour_task4 = 13

        # assert 4, 6 planned before 0, 6 should be planned before 16
        self.assert_new_dates(
            self.project2_task_6,
            datetime(year=2024, month=2, day=day, hour=13),
            datetime(year=2024, month=2, day=21, hour=17),
            f"""
                task 6 duration = allocated_hours = {allocated_hours} Hours
                even than task 0 starts on 01/03, we need to plan task 6 before task 16 (starts on 22/02 8H)
            """
        )
        self.assert_new_dates(
            self.project2_task_4,
            datetime(year=2024, month=2, day=start_project2_task4, hour=hour_task4),
            datetime(year=2024, month=2, day=day, hour=12),
            f"""
                task 4 duration = allocated_hours = {allocated_hours} Hours
                4 Hours on 19/02
                8 Hours on 16/02
                4 Hours on 15/02
            """
        )

        moved_tasks.action_rollback_scheduling(res['old_vals_per_pill_id'])
        self.assert_task_not_replanned(moved_tasks, initial_dates_deep_copy)

    def test_move_forward_with_multi_users(self):
        """
                        -------------------------------------------------
                        |                                               |
                        v                                               |
            Raouf 1    [0]->[ 1 ]------>[2]----------->[5]   |->[7]    [8]
                             |  |        ^      --------|----
                             |  |        |      |       |
            Raouf 2          |  -->[3]   |      |       ----->[9]----->[10]
                             |           |      |
                             |           |      |
            Raouf 3 and 2    ---------->[4]---->[6]

            When we move 0 in front of 8:
            - 3, 4 can be planned in // just after the end of 1
            - 2, 6 can be planned in // just after the end of 4
            - 5 planned after 2
            - 9, 10 should wait for 5 to be planned even if there are available slots before
            - 7 planned after 6
        """
        self.project2_task_8.write({
            'depend_on_ids': [Command.unlink(self.project2_task_7.id)],
        })
        (self.project2_task_4 + self.project2_task_6).write({
            'user_ids': [self.user2.id, self.user1.id],
        })

        (self.project2_task_9 + self.project2_task_10).write({
            'user_ids': [self.user1.id],
        })

        self.project2_task_2.write({
            'dependent_ids': [Command.link(self.project2_task_5.id)],
            'depend_on_ids': [Command.link(self.project2_task_4.id), Command.unlink(self.project2_task_7.id)],
        })

        self.project2_task_5.write({
            'dependent_ids': [Command.unlink(self.project2_task_7.id)]
        })

        self.project2_task_1.write({
            'dependent_ids': [Command.link(self.project2_task_4.id)]
        })

        res = self.gantt_reschedule_forward(self.project2_task_8, self.project2_task_0)
        moved_tasks = self.project2.task_ids - self.project2_task_8 - self.project2_task_12 - self.project2_task_13 - self.project2_task_14 - self.project2_task_11
        self.assert_old_tasks_vals(res, 'success', 'Reschedule done successfully.', moved_tasks, self.initial_dates)
        self.assert_new_dates(
            self.project2_task_0,
            datetime(year=2024, month=3, day=18, hour=8),
            datetime(year=2024, month=3, day=18, hour=12),
        )

        self.assert_new_dates(
            self.project2_task_1,
            datetime(year=2024, month=3, day=18, hour=13),
            datetime(year=2024, month=3, day=18, hour=17),
        )

        self.assert_new_dates(
            self.project2_task_3,
            datetime(year=2024, month=3, day=19, hour=8),
            datetime(year=2024, month=3, day=19, hour=14),
        )

        self.assert_new_dates(
            self.project2_task_4,
            datetime(year=2024, month=3, day=19, hour=8),
            datetime(year=2024, month=3, day=20, hour=17),
        )

        self.assert_new_dates(
            self.project2_task_2,
            datetime(year=2024, month=3, day=21, hour=8),
            datetime(year=2024, month=3, day=21, hour=10),
        )

        self.assert_new_dates(
            self.project2_task_6,
            datetime(year=2024, month=3, day=21, hour=8),
            datetime(year=2024, month=3, day=25, hour=12),
            "allocated_hours = 20"
        )

        self.assert_new_dates(
            self.project2_task_7,
            datetime(year=2024, month=3, day=25, hour=13),
            datetime(year=2024, month=3, day=25, hour=17),
        )

        self.assert_new_dates(
            self.project2_task_5,
            datetime(year=2024, month=3, day=21, hour=10),
            datetime(year=2024, month=3, day=25, hour=10),
        )

        self.assert_new_dates(
            self.project2_task_9,
            datetime(year=2024, month=3, day=25, hour=13),
            datetime(year=2024, month=3, day=25, hour=17),
            """
                task 9 should start after task 5 which is its blocking task and after task 6
                as user Raouf 2 was busy doing it.
            """
        )

        self.assert_new_dates(
            self.project2_task_10,
            datetime(year=2024, month=3, day=26, hour=8),
            datetime(year=2024, month=3, day=26, hour=12),
        )

        moved_tasks.action_rollback_scheduling(res['old_vals_per_pill_id'])
        self.assert_task_not_replanned(moved_tasks, self.initial_dates)

    def test_move_backward_with_multi_users(self):
        """
                         ----------------------------------------------------------------
                         |                                                              |
                         v                                                              |
            Raouf 1     [13]    [0]->[ 1 ]------>[2]----------->[5]   |->[7]---------->[8]
                                      |  |        ^      --------|-----                 ^
                                      |  |        |      |       |                      |
            Raouf 2                   |  -->[3]   |      |       ----->[9]------------>[10]
                                      |           |      |
                                      |           |      |
            Raouf 3 & Raouf 2         ---------->[4]---->[6]

            When we move 8 before 13:
            - all the ancestors of 8 should move before 8 (0, 1, 4, 2, 6, 7, 5, 9, 10, 8)
        """
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

        res = self.gantt_reschedule_backward(self.project2_task_8, self.project2_task_13)
        moved_tasks = self.project2.task_ids - self.project2_task_13 - self.project2_task_3 - self.project2_task_11 - self.project2_task_14 - self.project2_task_12
        self.assert_old_tasks_vals(res, 'success', 'Reschedule done successfully.', moved_tasks, self.initial_dates)

        self.assert_new_dates(
            self.project2_task_0,
            datetime(year=2024, month=2, day=14, hour=9),
            datetime(year=2024, month=2, day=14, hour=14),
        )

        self.assert_new_dates(
            self.project2_task_1,
            datetime(year=2024, month=2, day=14, hour=14),
            datetime(year=2024, month=2, day=15, hour=9),
        )

        self.assert_new_dates(
            self.project2_task_4,
            datetime(year=2024, month=2, day=15, hour=9),
            datetime(year=2024, month=2, day=19, hour=9),
        )

        self.assert_new_dates(
            self.project2_task_2,
            datetime(year=2024, month=2, day=21, hour=15),
            datetime(year=2024, month=2, day=21, hour=17),
        )

        self.assert_new_dates(
            self.project2_task_6,
            datetime(year=2024, month=2, day=19, hour=9),
            datetime(year=2024, month=2, day=21, hour=14),
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
        moved_tasks.action_rollback_scheduling(res['old_vals_per_pill_id'])
        self.assert_task_not_replanned(moved_tasks, self.initial_dates)

    def test_web_gantt_write(self):
        users = self.user_projectuser + self.user_projectmanager
        self.task_1.write({'user_ids': users.ids})
        self.task_2.write({'user_ids': self.user_projectuser.ids})
        tasks = self.task_1 + self.task_2
        tasks.web_gantt_write({'user_ids': self.user_projectmanager.ids})
        self.assertEqual(self.task_1.user_ids, users, "The assignees set on Task 1 should remain the same if the new assigne was in fact already in the assigness of the task.")
        self.assertEqual(self.task_2.user_ids, self.user_projectmanager, "The assignees set on Task 2 should be the new one and the user initially assinged should be unassigned.")

        tasks.web_gantt_write({'user_ids': False})
        self.assertFalse(tasks.user_ids, "No assignees should be set on the both tasks")

        tasks.web_gantt_write({'user_ids': self.user_portal.ids})
        self.assertEqual(self.task_1.user_ids, self.user_portal, "User portal should be assigned to Task 1.")
        self.assertEqual(self.task_2.user_ids, self.user_portal, "User portal should be assigned to Task 2.")

        tasks.web_gantt_write({'user_ids': users.ids})
        self.assertEqual(self.task_1.user_ids, users, "Project user and Prohect manager should be assigned to the task 1 and portal user should be assigned.")
        self.assertEqual(self.task_2.user_ids, users, "Project user and Prohect maanger should be assigned to the task 2 and portal user should be assigned.")
