# -*- coding: utf-8 -*-

from odoo.tests import tagged
from odoo.fields import Command
from datetime import datetime, timedelta

from odoo.addons.project.tests.test_project_base import TestProjectCommon

@tagged('-at_install', 'post_install')
class TestTaskGroupExpand(TestProjectCommon):

    def test_task_user_ids_group_expand(self):
        def user_in_groups(user_id):
            return any(
                'user_ids' in group and group['user_ids'][0] == user_id
                for group in groups)

        # Simulate Gantt view
        gantt_domain = [
            ('planned_date_begin', '>=', datetime.today()),
            ('date_deadline', '<=', datetime.today() + timedelta(days=7)),
        ]
        Task = self.env['project.task'].with_user(self.user_projectuser).with_context({
            'gantt_start_date': datetime.today(),
            'gantt_scale': 'week',
        })
        args = ['name'], ['user_ids']

        # 1. Search with no filter on user_ids: Current user should have a group (even if empty)
        groups = Task.read_group(gantt_domain + [('id', '=', self.task_2.id)], *args)
        self.assertTrue(user_in_groups(self.user_projectuser.id),
                        "A group should exist for the current user if no filter is applied on user_ids.")

        # 2. Search with filter on user_ids: Current user should not have a group if empty
        groups = Task.read_group(gantt_domain + [('user_ids', 'in', self.user_projectmanager.id)], *args)
        self.assertFalse(user_in_groups(self.user_projectuser.id),
                        "No empty group should be added for the current user if a filter is applied on user_ids.")

        # 3. Corner case: same search as 2 but with a task not displayed in the gantt view assigned to both user
        test_task = self.env['project.task'].create([{
            'name': 'Shared task test group expand',
            'user_ids': [Command.set([self.user_projectuser.id, self.user_projectmanager.id])],
        }])
        groups = Task.read_group(gantt_domain + [('user_ids', 'in', self.user_projectmanager.id)], *args)
        self.assertFalse(user_in_groups(self.user_projectuser.id),
                        "No empty group should be added for the current user if a filter is applied on user_ids, even if a record not visible in the gantt view match the domain.")

        # 4. Corner case: same case as 3, but with the task visible in the gantt view
        test_task.write({
            'planned_date_begin': datetime.now(),
            'date_deadline': datetime.now() + timedelta(days=2),
        })
        groups = Task.read_group(
            gantt_domain + [('user_ids', 'in', self.user_projectmanager.id)], *args)
        self.assertTrue(user_in_groups(self.user_projectuser.id),
                        "Even if a filter is applied on user_ids, all user row containing visible tasks in the gantt view should be displayed")
