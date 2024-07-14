# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tests import tagged
from odoo.addons.project.tests.test_project_base import TestProjectCommon
from freezegun import freeze_time


@tagged('-at_install', 'post_install')
@freeze_time('2023-01-01')
class TestSmartSchedule(TestProjectCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.projectuser_resource, cls.projectmanager_resource = cls.env['resource.resource'].create([
            {
                'calendar_id': cls.project_pigs.resource_calendar_id.id,
                'company_id': cls.user_projectuser.company_id.id,
                'name': cls.user_projectuser.name,
                'user_id': cls.user_projectuser.id,
                'tz': cls.user_projectuser.tz,
            },
            {
                'calendar_id': cls.project_pigs.resource_calendar_id.id,
                'company_id': cls.user_projectmanager.company_id.id,
                'name': cls.user_projectmanager.name,
                'user_id': cls.user_projectmanager.id,
                'tz': cls.user_projectmanager.tz,
            },
        ])

        tasks = cls.env['project.task'].create([
            # Tasks with project pigs
            {
                'name': 'task_project_pigs_with_allocated_hours_user',
                'allocated_hours': 8,
                'project_id': cls.project_pigs.id,
                'user_ids': [cls.user_projectuser.id],
            },
            {
                'name': 'task_project_pigs_with_allocated_hours_manager',
                'allocated_hours': 10,
                'project_id': cls.project_pigs.id,
                'user_ids': [cls.user_projectmanager.id],
            },
            {
                'name': 'task_project_pigs_with_allocated_hours_no_user',
                'allocated_hours': 10,
                'project_id': cls.project_pigs.id,
                'user_ids': None,
            },
            {
                'name': 'task_project_pigs_no_allocated_hours_user',
                'project_id': cls.project_pigs.id,
                'user_ids': [cls.user_projectuser.id],
            },
            {
                'name': 'task_project_pigs_no_allocated_hours_manager',
                'project_id': cls.project_pigs.id,
                'user_ids': [cls.user_projectmanager.id],
            },
            {
                'name': 'task_project_pigs_no_allocated_hours_no_user',
                'project_id': cls.project_pigs.id,
                'user_ids': None,
            },
            # Tasks with project goats
            {
                'name': 'task_project_goats_with_allocated_hours_user',
                'project_id': cls.project_goats.id,
                'allocated_hours': 10,
                'user_ids': [cls.user_projectuser.id],
            },
            {
                'name': 'task_project_goats_no_allocated_hours_user',
                'project_id': cls.project_goats.id,
                'user_ids': [cls.user_projectuser.id],
            },
        ])

        cls.task_project_pigs_with_allocated_hours_user, cls.task_project_pigs_with_allocated_hours_manager, \
            cls.task_project_pigs_with_allocated_hours_no_user, cls.task_project_pigs_no_allocated_hours_user, \
            cls.task_project_pigs_no_allocated_hours_manager, cls.task_project_pigs_no_allocated_hours_no_user, \
            cls.task_project_goats_with_allocated_hours_user, cls.task_project_goats_no_allocated_hours_user = tasks

        cls.start_date_view = datetime.now()
        cls.end_date_view = cls.start_date_view + relativedelta(days=31)
        cls.start_date_view_str = cls.start_date_view.strftime('%Y-%m-%d %H:%M:%S')
        cls.end_date_view_str = cls.end_date_view.strftime('%Y-%m-%d %H:%M:%S')

    def test_tasks_allocated_hours_multiple_users(self):
        result = (
            self.task_project_pigs_with_allocated_hours_user + self.task_project_pigs_with_allocated_hours_manager
        ).with_context({
            'last_date_view': self.end_date_view_str,
            'gantt_scale': "week",
            'cell_part': 2.0,
        }).schedule_tasks({
            'planned_date_begin': self.start_date_view_str,
            'date_deadline': (self.start_date_view + relativedelta(day=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'user_ids': self.user_projectmanager.ids,
        })
        # Test no warning is displayed
        self.assertDictEqual(result, {}, 'No warnings should be displayed')
        # Checking of the planned dates
        self.assertEqual(self.task_project_pigs_with_allocated_hours_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-02 07:00:00',
                         )
        self.assertEqual(self.task_project_pigs_with_allocated_hours_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-02 16:00:00',
                         )
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-03 07:00:00',
                         )
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-04 09:00:00',
                         )
        # Check if the user is the target one
        self.assertEqual(self.task_project_pigs_with_allocated_hours_user.user_ids, self.user_projectmanager, "Wrong user id")
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.user_ids, self.user_projectmanager, "Wrong user id")

    def test_tasks_allocated_hours_no_user(self):
        result = (
            self.task_project_pigs_with_allocated_hours_user + self.task_project_pigs_with_allocated_hours_no_user
        ).with_context({
            'last_date_view': self.end_date_view_str,
            'gantt_scale': "week",
            'cell_part': 2.0,
        }).schedule_tasks({
            'planned_date_begin': self.start_date_view_str,
            'date_deadline': (self.start_date_view + relativedelta(day=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'user_ids': None,
        })
        # That no warning is displayed
        self.assertDictEqual(result, {}, 'No warnings should be displayed')
        # Checking of the planned dates
        self.assertEqual(self.task_project_pigs_with_allocated_hours_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-02 07:00:00',
                         )
        self.assertEqual(self.task_project_pigs_with_allocated_hours_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-02 16:00:00',
                         )
        self.assertEqual(self.task_project_pigs_with_allocated_hours_no_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-02 07:00:00',
                         )
        self.assertEqual(self.task_project_pigs_with_allocated_hours_no_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-03 09:00:00',
                         )
        # Check if the user is the target one
        self.assertEqual(self.task_project_pigs_with_allocated_hours_user.user_ids, self.user_projectuser, "Wrong user id")
        self.assertFalse(self.task_project_pigs_with_allocated_hours_no_user.user_ids, "Wrong user id")

    def test_tasks_allocated_hours_multiple_projects(self):
        result = (
            self.task_project_pigs_with_allocated_hours_manager + self.task_project_goats_with_allocated_hours_user
        ).with_context({
            'last_date_view': self.end_date_view_str,
            'gantt_scale': "week",
            'cell_part': 2.0,
        }).schedule_tasks({
            'planned_date_begin': self.start_date_view_str,
            'date_deadline': (self.start_date_view + relativedelta(day=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'user_ids': self.user_projectmanager.ids,
        })
        # Test no warning is displayed
        self.assertDictEqual(result, {}, 'No warnings should be displayed')
        # Checking of the planned dates
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-02 07:00:00',
                         )
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-03 09:00:00',
                         )
        self.assertEqual(self.task_project_goats_with_allocated_hours_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-03 12:00:00',
                         )
        self.assertEqual(self.task_project_goats_with_allocated_hours_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-04 14:00:00',
                         )
        # Check if the user is the target one
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.user_ids, self.user_projectmanager, "Wrong user id")
        self.assertEqual(self.task_project_goats_with_allocated_hours_user.user_ids, self.user_projectmanager, "Wrong user id")

    def test_tasks_allocated_hours_with_leaves(self):
        # Creation of a leave from tuesday to thursday
        begin_leave = self.start_date_view + relativedelta(days=2)
        end_leave = begin_leave + relativedelta(days=2)
        self.env['resource.calendar.leaves'].create([
            {
                'name': 'scheduled leave',
                'date_from': begin_leave.strftime('%Y-%m-%d %H:%M:%S'),
                'date_to': end_leave.strftime('%Y-%m-%d %H:%M:%S'),
                'calendar_id': self.user_projectuser.resource_calendar_id.id,
                'time_type': 'leave',
            },
        ])

        result = (
            self.task_project_pigs_with_allocated_hours_user + self.task_project_goats_with_allocated_hours_user
        ).with_context({
            'last_date_view': self.end_date_view_str,
            'gantt_scale': "week",
            'cell_part': 2.0,
        }).schedule_tasks({
            'planned_date_begin': self.start_date_view_str,
            'date_deadline': (self.start_date_view + relativedelta(day=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'user_ids': self.user_projectuser.ids,
        })
        # Test no warning is displayed
        self.assertDictEqual(result, {}, 'No warnings should be displayed')
        # Checking of the planned dates
        self.assertEqual(self.task_project_pigs_with_allocated_hours_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-02 07:00:00',
                         )
        self.assertEqual(self.task_project_pigs_with_allocated_hours_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-02 16:00:00',
                         )
        self.assertEqual(self.task_project_goats_with_allocated_hours_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-05 07:00:00',
                         )
        self.assertEqual(self.task_project_goats_with_allocated_hours_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-06 09:00:00',
                         )
        # Check if the user is the target one
        self.assertEqual(self.task_project_pigs_with_allocated_hours_user.user_ids, self.user_projectuser, "Wrong user id")
        self.assertEqual(self.task_project_goats_with_allocated_hours_user.user_ids, self.user_projectuser, "Wrong user id")

    def test_tasks_allocated_hours_dependency(self):
        task_already_planned = self.env['project.task'].create(
            {
                'name': 'task_already_planned',
                'planned_date_begin': self.start_date_view + relativedelta(days=3),
                'date_deadline': self.start_date_view + relativedelta(days=4),
                'project_id': self.project_pigs.id,
                'user_ids': [self.user_projectuser.id],
            },
        )
        self.task_project_pigs_with_allocated_hours_user.depend_on_ids |= task_already_planned

        result = (
            self.task_project_pigs_with_allocated_hours_user
        ).with_context({
            'last_date_view': self.end_date_view_str,
            'gantt_scale': "week",
            'cell_part': 2.0,
        }).schedule_tasks({
            'planned_date_begin': self.start_date_view_str,
            'date_deadline': (self.start_date_view + relativedelta(day=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'user_ids': self.user_projectuser.ids,
        })
        # Test no warning is displayed
        self.assertDictEqual(result, {}, 'No warnings should be displayed')
        # Checking of the planned dates
        self.assertEqual(self.task_project_pigs_with_allocated_hours_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-05 07:00:00',
                         )
        self.assertEqual(self.task_project_pigs_with_allocated_hours_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-05 16:00:00',
                         )
        # Check if the user is the target one
        self.assertEqual(self.task_project_pigs_with_allocated_hours_user.user_ids, self.user_projectuser, "Wrong user id")

    def test_tasks_no_allocated_hours_for_day_scale(self):
        result = (
            self.task_project_pigs_with_allocated_hours_manager + self.task_project_pigs_no_allocated_hours_user + self.task_project_pigs_no_allocated_hours_no_user + self.task_project_goats_no_allocated_hours_user
        ).with_context({
            'last_date_view': self.end_date_view_str,
            'gantt_scale': "day",
            'cell_part': 2.0,
        }).schedule_tasks({
            'planned_date_begin': self.start_date_view_str,
            'date_deadline': (self.start_date_view + relativedelta(day=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'user_ids': self.user_projectuser.ids,
        })
        # Test no warning is displayed
        self.assertDictEqual(result, {}, 'No warnings should be displayed')
        # Checking of the planned dates
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-02 07:00:00',
                         )
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-03 09:00:00',
                         )
        self.assertEqual(self.task_project_pigs_no_allocated_hours_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-03 12:00:00',
                         )
        self.assertEqual(self.task_project_pigs_no_allocated_hours_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-03 16:00:00',
                         )
        self.assertEqual(self.task_project_pigs_no_allocated_hours_no_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-04 07:00:00',
                         )
        self.assertEqual(self.task_project_pigs_no_allocated_hours_no_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-04 11:00:00',
                         )
        self.assertEqual(self.task_project_goats_no_allocated_hours_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-04 12:00:00',
                         )
        self.assertEqual(self.task_project_goats_no_allocated_hours_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-04 16:00:00',
                         )
        # Check if the user is the target one
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.user_ids, self.user_projectuser, "Wrong user id")
        self.assertEqual(self.task_project_pigs_no_allocated_hours_user.user_ids, self.user_projectuser, "Wrong user id")
        self.assertEqual(self.task_project_pigs_no_allocated_hours_no_user.user_ids, self.user_projectuser, "Wrong user id")
        self.assertEqual(self.task_project_goats_no_allocated_hours_user.user_ids, self.user_projectuser, "Wrong user id")

    def test_tasks_no_allocated_hours_for_week_scale(self):
        result = (
            self.task_project_pigs_with_allocated_hours_manager + self.task_project_pigs_no_allocated_hours_user + self.task_project_pigs_no_allocated_hours_no_user + self.task_project_goats_no_allocated_hours_user
        ).with_context({
            'last_date_view': self.end_date_view_str,
            'gantt_scale': "week",
            'cell_part': 2.0,
        }).schedule_tasks({
            'planned_date_begin': self.start_date_view_str,
            'date_deadline': (self.start_date_view + relativedelta(day=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'user_ids': self.user_projectuser.ids,
        })
        # Test no warning is displayed
        self.assertDictEqual(result, {}, 'No warnings should be displayed')
        # Checking of the planned dates
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-02 07:00:00',
                         )
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-03 09:00:00',
                         )
        self.assertEqual(self.task_project_pigs_no_allocated_hours_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-03 12:00:00',
                         )
        self.assertEqual(self.task_project_pigs_no_allocated_hours_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-03 16:00:00',
                         )
        self.assertEqual(self.task_project_pigs_no_allocated_hours_no_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-04 07:00:00',
                         )
        self.assertEqual(self.task_project_pigs_no_allocated_hours_no_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-04 11:00:00',
                         )
        self.assertEqual(self.task_project_goats_no_allocated_hours_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-04 12:00:00',
                         )
        self.assertEqual(self.task_project_goats_no_allocated_hours_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-04 16:00:00',
                         )
        # Check if the user is the target one
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.user_ids, self.user_projectuser, "Wrong user id")
        self.assertEqual(self.task_project_pigs_no_allocated_hours_user.user_ids, self.user_projectuser, "Wrong user id")
        self.assertEqual(self.task_project_pigs_no_allocated_hours_no_user.user_ids, self.user_projectuser, "Wrong user id")
        self.assertEqual(self.task_project_goats_no_allocated_hours_user.user_ids, self.user_projectuser, "Wrong user id")

    def test_tasks_no_allocated_hours_for_month_scale_with_precision_one_day(self):
        result = (
            self.task_project_pigs_with_allocated_hours_manager + self.task_project_pigs_no_allocated_hours_user + self.task_project_pigs_no_allocated_hours_no_user + self.task_project_goats_no_allocated_hours_user
        ).with_context({
            'last_date_view': self.end_date_view_str,
            'gantt_scale': "month",
            'cell_part': 1.0,
        }).schedule_tasks({
            'planned_date_begin': self.start_date_view_str,
            'date_deadline': (self.start_date_view + relativedelta(day=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'user_ids': self.user_projectuser.ids,
        })
        # Test no warning is displayed
        self.assertDictEqual(result, {}, 'No warnings should be displayed')
        # Checking of the planned dates
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-02 07:00:00',
                         )
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-03 09:00:00',
                         )
        self.assertEqual(self.task_project_pigs_no_allocated_hours_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-04 07:00:00',
                         )
        self.assertEqual(self.task_project_pigs_no_allocated_hours_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-04 16:00:00',
                         )
        self.assertEqual(self.task_project_pigs_no_allocated_hours_no_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-05 07:00:00',
                         )
        self.assertEqual(self.task_project_pigs_no_allocated_hours_no_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-05 16:00:00',
                         )
        self.assertEqual(self.task_project_goats_no_allocated_hours_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-06 07:00:00',
                         )
        self.assertEqual(self.task_project_goats_no_allocated_hours_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-06 16:00:00',
                         )
        # Check if the user is the target one
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.user_ids, self.user_projectuser, "Wrong user id")
        self.assertEqual(self.task_project_pigs_no_allocated_hours_user.user_ids, self.user_projectuser, "Wrong user id")
        self.assertEqual(self.task_project_pigs_no_allocated_hours_no_user.user_ids, self.user_projectuser, "Wrong user id")
        self.assertEqual(self.task_project_goats_no_allocated_hours_user.user_ids, self.user_projectuser, "Wrong user id")

    def test_tasks_no_allocated_hours_for_year_scale_with_out_of_scale_notification(self):
        result = (
            self.task_project_pigs_with_allocated_hours_manager + self.task_project_pigs_no_allocated_hours_user
        ).with_context({
            'last_date_view': self.end_date_view_str,
            'gantt_scale': "year",
            'cell_part': 1.0,
        }).schedule_tasks({
            'planned_date_begin': self.start_date_view_str,
            'date_deadline': (self.start_date_view + relativedelta(day=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'user_ids': self.user_projectmanager.ids,
        })
        # Test no warning is displayed
        self.assertDictEqual(result, {'out_of_scale_notification': 'Tasks have been successfully scheduled for the upcoming periods.'},
                             'The out of scale warning should be displayed')
        # Checking of the planned dates
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-02 07:00:00',
                         )
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-03 09:00:00',
                         )
        self.assertEqual(self.task_project_pigs_no_allocated_hours_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-02-01 07:00:00',
                         )
        self.assertEqual(self.task_project_pigs_no_allocated_hours_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-02-28 16:00:00',
                         )
        # Check if the user is the target one
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.user_ids, self.user_projectmanager, "Wrong user id")
        self.assertEqual(self.task_project_pigs_no_allocated_hours_user.user_ids, self.user_projectmanager, "Wrong user id")
