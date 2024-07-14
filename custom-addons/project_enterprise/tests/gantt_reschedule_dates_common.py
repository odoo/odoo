# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.fields import Command
from odoo.addons.project.tests.test_project_base import TestProjectCommon
from odoo.addons.web_gantt.models.models import Base


# As the writing of the new planned_dates is only made when planned_date_start is in the future,
# we need to cheat during the tests
fake_now = datetime(2021, 4, 1)


class ProjectEnterpriseGanttRescheduleCommon(TestProjectCommon):

    @classmethod
    def setUpClass(cls):
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
            'name': 'Pigs UserTask 2',
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
            'name': 'Pigs UserTask 3',
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
            'name': 'Pigs UserTask 4',
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
            'name': 'Pigs UserTask 5',
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
        users = cls.user_projectuser | cls.user_projectmanager
        users.write({
            'resource_calendar_id': cls.calendar_40h.id,
        })

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
