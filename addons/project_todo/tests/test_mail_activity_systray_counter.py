# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from odoo.tests.common import TransactionCase
from odoo import fields


class TestActivitySystrayCounter(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_user = cls.env['res.users'].create({
            'name': 'Test User',
            'login': 'testuser',
        })
        cls.test_project = cls.env['project.project'].create({
            'name': 'Test Project',
        })

        cls._create_task_scenarios(is_todo=False)
        cls._create_task_scenarios(is_todo=True)

    @classmethod
    def _create_task_scenarios(cls, is_todo=False):
        """
        Helper method to create a standard set of test tasks/to-dos and activities.
        :param bool is_todo: If True, creates tasks without a project_id (To-Dos).
                             If False, creates tasks with a project_id.
        """
        today = fields.Date.today()
        yesterday = today - datetime.timedelta(days=1)
        tomorrow = today + datetime.timedelta(days=1)

        task_details = {'user_ids': [(6, 0, [cls.test_user.id])]}
        if not is_todo:
            task_details['project_id'] = cls.test_project.id

        name_prefix = "To-Do" if is_todo else "Task"

        # SCENARIO 1: A single record with TWO overdue activities.
        record_overdue = cls.env['project.task'].create({**task_details, 'name': f'{name_prefix} Overdue Record'})
        cls.env['mail.activity'].create([
            {
                'res_id': record_overdue.id,
                'res_model_id': cls.env.ref('project.model_project_task').id,
                'user_id': cls.test_user.id,
                'date_deadline': yesterday,
                'summary': 'Overdue 1',
            },
            {
                'res_id': record_overdue.id,
                'res_model_id': cls.env.ref('project.model_project_task').id,
                'user_id': cls.test_user.id,
                'date_deadline': yesterday,
                'summary': 'Overdue 2',
            },
        ])

        # SCENARIO 2: A single record with 'today' and 'planned' activities.
        record_today = cls.env['project.task'].create({**task_details, 'name': f'{name_prefix} Today Record'})
        cls.env['mail.activity'].create([
            {
                'res_id': record_today.id,
                'res_model_id': cls.env.ref('project.model_project_task').id,
                'user_id': cls.test_user.id,
                'date_deadline': today,
                'summary': 'Today Activity',
            },
            {
                'res_id': record_today.id,
                'res_model_id': cls.env.ref('project.model_project_task').id,
                'user_id': cls.test_user.id,
                'date_deadline': tomorrow,
                'summary': 'Planned Activity',
            },
        ])

        # SCENARIO 3: A single record with one 'planned' activity.
        record_planned = cls.env['project.task'].create({**task_details, 'name': f'{name_prefix} Planned Record'})
        cls.env['mail.activity'].create({
            'res_id': record_planned.id,
            'res_model_id': cls.env.ref('project.model_project_task').id,
            'user_id': cls.test_user.id,
            'date_deadline': tomorrow,
            'summary': 'Planned',
        })

    def test_systray_task_and_todo_split(self):
        """Tests that activities are correctly split into Task and To-Do groups."""
        activity_groups = self.env['res.users'].with_user(self.test_user)._get_activity_groups()

        task_group = next((g for g in activity_groups if g.get('name') == 'Task'), None)
        todo_group = next((g for g in activity_groups if g.get('name') == 'To-Do'), None)

        # 1. Check that both groups were created
        self.assertTrue(task_group)
        self.assertTrue(todo_group)

        # 2. Check counts for the 'Task' group
        self.assertEqual(task_group['overdue_count'], 1)
        self.assertEqual(task_group['today_count'], 1)
        self.assertEqual(task_group['planned_count'], 1)
        self.assertEqual(task_group['total_count'], 2, "Task total_count should be: overdue + today")

        # 3. Check counts for the 'To-Do' group
        self.assertEqual(todo_group['overdue_count'], 1)
        self.assertEqual(todo_group['today_count'], 1)
        self.assertEqual(todo_group['planned_count'], 1)
        self.assertEqual(todo_group['total_count'], 2, "To-Do total_count should be: overdue + today")
