# Part of Odoo. See LICENSE file for full copyright and licensing details

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.addons.project.tests.test_project_base import TestProjectCommon


class TestSmartScheduleCommon(TestProjectCommon):
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
        cls.is_module_timesheet_grid_installed = hasattr(cls.env['project.task'], 'allow_timesheets')
