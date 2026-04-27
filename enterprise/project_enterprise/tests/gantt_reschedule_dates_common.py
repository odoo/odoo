# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.fields import Command
from odoo.addons.project.tests.test_project_base import TestProjectCommon
from odoo.addons.web_gantt.models.models import Base
from odoo.tests import new_test_user


# As the writing of the new planned_dates is only made when planned_date_start is in the future,
# we need to cheat during the tests
fake_now = datetime(2021, 4, 1)


class ProjectEnterpriseGanttRescheduleCommon(TestProjectCommon):

    @classmethod
    def setUpClass(cls):
        """
            project structure

            ┌─────────┐      ┌─────────┐      ┌─────────┐      ┌─────────┐      ┌─────────┐
            │ Task 1  │ -->  │ Task 3  │ -->  │ Task 4  │ -->  │ Task 5  │ -->  │ Task 6  │
            │         │      │         │      │         │      │02/08 8H │      │         │
            │ 24/06   │      │ 24/06   │      │ 30/06   │      │   ->    │      │ 04/08   │
            │ 9H > 12H│      │13H > 15H│      │15H > 17H│      │03/08 17H│      │ 8H->17H │
            └─────────┘      └─────────┘      └─────────┘      └─────────┘      └─────────┘

            1 --> 3: 3 blocked by 1

        """
        super().setUpClass()

        test_additional_context = {'mail_create_nolog': True, 'tracking_disable': True, 'mail_notrack': True}
        test_context = dict(cls.env.context, **test_additional_context)
        cls.env = cls.env(context=test_context)

        cls.ProjectTask = cls.env['project.task']
        cls.dependency_field_name = 'depend_on_ids'
        cls.dependency_inverted_field_name = 'dependent_ids'
        cls.start_date_field_name = 'planned_date_begin'
        cls.stop_date_field_name = 'date_deadline'
        cls.Settings = cls.env["res.config.settings"]
        cls.project_pigs.write({
            'allow_task_dependencies': True,
        })
        cls.task_1 = cls.task_1.with_context(**test_context)
        cls.task_1_planned_date_begin = datetime(2021, 6, 24, 9, 0, 0)
        cls.task_1_date_deadline = datetime(2021, 6, 24, 12, 0, 0)
        cls.task_1.write({
            'planned_date_begin': cls.task_1_planned_date_begin,
            'date_deadline': cls.task_1_date_deadline,
            'allocated_hours': 3.0,
        })
        cls.task_3_planned_date_begin = datetime(2021, 6, 24, 13, 0, 0)
        cls.task_3_date_deadline = datetime(2021, 6, 24, 15, 0, 0)
        cls.task_3 = cls.ProjectTask.create({
            'name': 'Pigs UserTask 3',
            'user_ids': cls.user_projectuser,
            'project_id': cls.project_pigs.id,
            'depend_on_ids': [Command.link(cls.task_1.id)],
            'planned_date_begin': cls.task_3_planned_date_begin,
            'date_deadline': cls.task_3_date_deadline,
            'allocated_hours': 2.0,
        })
        cls.task_4_planned_date_begin = datetime(2021, 6, 30, 15, 0, 0)
        cls.task_4_date_deadline = datetime(2021, 6, 30, 17, 0, 0)
        cls.task_4 = cls.ProjectTask.create({
            'name': 'Pigs UserTask 4',
            'user_ids': cls.user_projectuser,
            'project_id': cls.project_pigs.id,
            'depend_on_ids': [Command.link(cls.task_3.id)],
            'planned_date_begin': cls.task_4_planned_date_begin,
            'date_deadline': cls.task_4_date_deadline,
            'allocated_hours': 2.0,
        })
        cls.task_5_planned_date_begin = datetime(2021, 8, 2, 8, 0, 0)
        cls.task_5_date_deadline = datetime(2021, 8, 3, 17, 0, 0)
        cls.task_5 = cls.ProjectTask.create({
            'name': 'Pigs UserTask 5',
            'user_ids': cls.user_projectuser,
            'project_id': cls.project_pigs.id,
            'depend_on_ids': [Command.link(cls.task_4.id)],
            'planned_date_begin': cls.task_5_planned_date_begin,
            'date_deadline': cls.task_5_date_deadline,
            'allocated_hours': 16.0,
        })
        cls.task_6_planned_date_begin = datetime(2021, 8, 4, 8, 0, 0)
        cls.task_6_date_deadline = datetime(2021, 8, 4, 17, 0, 0)
        cls.task_6 = cls.ProjectTask.create({
            'name': 'Pigs UserTask 6',
            'user_ids': cls.user_projectuser,
            'project_id': cls.project_pigs.id,
            'depend_on_ids': [Command.link(cls.task_5.id)],
            'planned_date_begin': cls.task_6_planned_date_begin,
            'date_deadline': cls.task_6_date_deadline,
            'allocated_hours': 8.0,
        })
        overlapping_delta = cls.task_3_planned_date_begin - cls.task_1_date_deadline + timedelta(hours=1)
        cls.task_1_date_gantt_reschedule_trigger = {
            'planned_date_begin': cls.task_1.planned_date_begin + overlapping_delta,
            'date_deadline': cls.task_1.date_deadline + overlapping_delta,
        }
        cls.task_3_date_gantt_reschedule_trigger = {
            'planned_date_begin': cls.task_3.planned_date_begin - overlapping_delta,
            'date_deadline': cls.task_3.date_deadline - overlapping_delta,
        }
        cls.task_1_no_date_gantt_reschedule_trigger = {
            'planned_date_begin': cls.task_1.planned_date_begin + overlapping_delta - timedelta(hours=1),
            'date_deadline': cls.task_1.date_deadline + overlapping_delta - timedelta(hours=1),
        }
        cls.calendar_40h = cls.env['resource.calendar'].create({
            'name': '40h calendar',
            'attendance_ids': [
                (0, 0, {
                    'name': 'Monday Morning', 'dayofweek': '0',
                    'hour_from': 8, 'hour_to': 12,
                    'day_period': 'morning'}
                ),
                (0, 0, {
                    'name': 'Monday Lunch', 'dayofweek': '0',
                    'hour_from': 12, 'hour_to': 13,
                    'day_period': 'lunch'}
                ),
                (0, 0, {
                    'name': 'Monday Evening', 'dayofweek': '0',
                    'hour_from': 13, 'hour_to': 17,
                    'day_period': 'afternoon'}
                ),
                (0, 0, {
                    'name': 'Tuesday Morning', 'dayofweek': '1',
                    'hour_from': 8, 'hour_to': 12,
                    'day_period': 'morning'}
                ),
                (0, 0, {
                    'name': 'Tuesday Lunch', 'dayofweek': '1',
                    'hour_from': 12, 'hour_to': 13,
                    'day_period': 'lunch'}
                ),
                (0, 0, {
                    'name': 'Tuesday Evening', 'dayofweek': '1',
                    'hour_from': 13, 'hour_to': 17,
                    'day_period': 'afternoon'}
                ),
                (0, 0, {
                    'name': 'Wednesday Morning', 'dayofweek': '2',
                    'hour_from': 8, 'hour_to': 12,
                    'day_period': 'morning'}
                ),
                (0, 0, {
                    'name': 'Wednesday Lunch', 'dayofweek': '2',
                    'hour_from': 12, 'hour_to': 13,
                    'day_period': 'lunch'}
                ),
                (0, 0, {
                    'name': 'Wednesday Evening', 'dayofweek': '2',
                    'hour_from': 13, 'hour_to': 17,
                    'day_period': 'afternoon'}
                ),
                (0, 0, {
                    'name': 'Thursday Morning', 'dayofweek': '3',
                    'hour_from': 8, 'hour_to': 12,
                    'day_period': 'morning'}
                ),
                (0, 0, {
                    'name': 'Thursday Lunch', 'dayofweek': '3',
                    'hour_from': 12, 'hour_to': 13,
                    'day_period': 'lunch'}
                ),
                (0, 0, {
                    'name': 'Thursday Evening', 'dayofweek': '3',
                    'hour_from': 13, 'hour_to': 17,
                    'day_period': 'afternoon'}
                ),
                (0, 0, {
                    'name': 'Friday Morning', 'dayofweek': '4',
                    'hour_from': 8, 'hour_to': 12,
                    'day_period': 'morning'}
                ),
                (0, 0, {
                    'name': 'Friday Lunch', 'dayofweek': '4',
                    'hour_from': 12, 'hour_to': 13,
                    'day_period': 'lunch'}
                ),
                (0, 0, {
                    'name': 'Friday Evening', 'dayofweek': '4',
                    'hour_from': 13, 'hour_to': 17,
                    'day_period': 'afternoon'}
                ),
            ],
            'tz': 'UTC',
        })
        cls.annual_holiday = cls.env['resource.calendar.leaves'].create({
            'name': 'Building leave',
            'resource_id': False,
            'calendar_id': cls.calendar_40h.id,
            'date_from': datetime(2021, 7, 1, 0, 0, 0),
            'date_to': datetime(2021, 7, 31, 23, 59, 59),
        })
        cls.env.company.write({
            'resource_calendar_id': cls.calendar_40h.id,
        })
        cls.user1 = new_test_user(cls.env, login='raouf2')
        cls.user2 = new_test_user(cls.env, login='raouf3')

        """
            Second project structure (with more nodes and use cases)

                                                             [4]->[6]
                                                                   |
             [14]     [13]                                         v
                 [11]    [12]        --->[0]->[1]->[2]       [5]->[7]->[8]-----------------
                                     |         |              |                           |
                                     |         v              v                           |
                                     |        [3]            [9]->[10]                    |
                                     |                                                    |
                                     ---------------------<x>------------------------------

            [0]->[1] means 1 blocked by 0
            <: left arrow to move task 8 backward task 0
            >: right arrow to move task 0 forward task 8
            x: delete the dependence
        """
        cls.project2 = cls.env['project.project'].create({
            'name': 'Test dependencies Project',
            'type_ids': [Command.create({'name': 'To Do'})],
            'allow_task_dependencies': True,
        })

        cls.initial_dates = {
            '0': (datetime(2024, 3, 1, 8, 0), datetime(2024, 3, 1, 12, 0)),
            '1': (datetime(2024, 3, 1, 13, 0), datetime(2024, 3, 1, 17, 0)),
            '2': (datetime(2024, 3, 4, 8, 0), datetime(2024, 3, 4, 10, 0)),
            '3': (datetime(2024, 3, 2, 11, 0), datetime(2024, 3, 2, 17, 0)),
            '4': (datetime(2024, 3, 5, 8, 0), datetime(2024, 3, 6, 17, 0)),
            '5': (datetime(2024, 3, 7, 8, 0), datetime(2024, 3, 8, 17, 0)),
            '6': (datetime(2024, 3, 9, 8, 0), datetime(2024, 3, 13, 12, 0)),
            '7': (datetime(2024, 3, 13, 13, 0), datetime(2024, 3, 13, 17, 0)),
            '8': (datetime(2024, 3, 15, 8, 0), datetime(2024, 3, 16, 14, 0)),
            '9': (datetime(2024, 3, 14, 8, 0), datetime(2024, 3, 14, 12, 0)),
            '10': (datetime(2024, 3, 14, 13, 0), datetime(2024, 3, 14, 17, 0)),
            '11': (datetime(2024, 2, 28, 8, 0), datetime(2024, 2, 28, 11, 0)),
            '12': (datetime(2024, 2, 29, 15, 0), datetime(2024, 2, 29, 16, 0)),
            '13': (datetime(2024, 2, 29, 9, 0), datetime(2024, 2, 29, 15, 0)),
            '14': (datetime(2024, 2, 26, 8, 0), datetime(2024, 2, 26, 15, 0)),
        }

        vals_list = []
        for name, dates in cls.initial_dates.items():
            vals_list.append({
                "name": name,
                "user_ids": cls.user_projectuser,
                "project_id": cls.project2.id,
                "planned_date_begin": dates[0],
                "date_deadline": dates[1],
            })

        cls.project2_task_0, \
        cls.project2_task_1, \
        cls.project2_task_2, \
        cls.project2_task_3, \
        cls.project2_task_4, \
        cls.project2_task_5, \
        cls.project2_task_6, \
        cls.project2_task_7, \
        cls.project2_task_8, \
        cls.project2_task_9, \
        cls.project2_task_10, \
        cls.project2_task_11, \
        cls.project2_task_12, \
        cls.project2_task_13, \
        cls.project2_task_14 = cls.ProjectTask.create(vals_list)

        cls.project2_task_0.write({
            'depend_on_ids': [Command.link(cls.project2_task_8.id)],
            'dependent_ids': [Command.link(cls.project2_task_1.id)],
        })
        cls.project2_task_1.write({
            'dependent_ids': [Command.link(cls.project2_task_2.id), Command.link(cls.project2_task_3.id)]
        })
        cls.project2_task_3.write({
            'allocated_hours': 5,
        })
        cls.project2_task_4.write({
            'allocated_hours': 16,
        })
        cls.project2_task_5.write({
            'allocated_hours': 16,
        })
        cls.project2_task_6.write({
            'depend_on_ids': [Command.link(cls.project2_task_4.id)],
            'allocated_hours': 20,
        })
        cls.project2_task_7.write({
            'depend_on_ids': [Command.link(cls.project2_task_5.id), Command.link(cls.project2_task_6.id)],
        })
        cls.project2_task_8.write({
            'depend_on_ids': [Command.link(cls.project2_task_7.id)],
            'allocated_hours': 13,
        })
        cls.project2_task_9.write({
            'depend_on_ids': [Command.link(cls.project2_task_5.id)],
        })
        cls.project2_task_10.write({
            'depend_on_ids': [Command.link(cls.project2_task_9.id)],
        })
        cls.is_module_timesheet_grid_installed = hasattr(cls.env['project.task'], 'allow_timesheets')

    def setUp(self):
        super().setUp()
        self.env.user.has_group('.')
        self.env.user.has_group('base.group_system')

    @classmethod
    def gantt_reschedule_forward(cls, master_record, slave_record):
        return cls.ProjectTask.web_gantt_reschedule(
            Base._WEB_GANTT_RESCHEDULE_FORWARD,
            master_record.id, slave_record.id,
            cls.dependency_field_name, cls.dependency_inverted_field_name,
            cls.start_date_field_name, cls.stop_date_field_name
        )

    @classmethod
    def gantt_reschedule_backward(cls, master_record, slave_record):
        return cls.ProjectTask.web_gantt_reschedule(
            Base._WEB_GANTT_RESCHEDULE_BACKWARD,
            master_record.id, slave_record.id,
            cls.dependency_field_name, cls.dependency_inverted_field_name,
            cls.start_date_field_name, cls.stop_date_field_name
        )

    def assert_task_not_replanned(cls, tasks, initial_dates):
        for task in tasks:
            cls.assertEqual((task.planned_date_begin, task.date_deadline), initial_dates[task.name], f"task {task.name} should not be replanned")

    def assert_new_dates(cls, task, planned_date_begin, date_deadline, message=None):
        cls.assertEqual(task.planned_date_begin, planned_date_begin, message)
        cls.assertEqual(task.date_deadline, date_deadline, message)

    def assert_old_tasks_vals(cls, res, _type, message, moved_tasks, initial_dates):
        cls.assertDictEqual(res, {
            'type': _type,
            'message': message,
            'old_vals_per_pill_id': {
                task.id: {
                    'planned_date_begin': initial_dates[task.name][0],
                    'date_deadline': initial_dates[task.name][1],
                } for task in moved_tasks
            },
        })
