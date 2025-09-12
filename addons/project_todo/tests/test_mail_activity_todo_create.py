# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from markupsafe import Markup
from odoo.tests.common import TransactionCase
from odoo import fields


class TestMailActivityTodo(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mail_activity = cls.env['mail.activity.todo.create'].create({
            'summary': 'test_summary',
            'date_deadline': datetime.date.today(),
            'note': Markup('<p>details</p>'),
            'user_id': cls.env.ref('base.user_admin').id,
        })
        cls.mail_activity.create_todo_activity()

    def test_create_todo_activity(self):
        todo_1 = self.env['project.task'].search([('name', 'ilike', 'test_summary')], limit=1)
        activity_1 = self.env['mail.activity'].search([('summary', 'ilike', 'test_summary')], limit=1)
        self.assertTrue(todo_1.exists(), 'A Todo should have been created')
        self.assertEqual(todo_1.description, Markup('<p>details</p>'), 'The Todo description should be the same as the mail.activity.todo.create note')
        self.assertTrue(activity_1.exists(), 'An Activity should have been created')
        self.assertEqual(activity_1.summary, todo_1.name, 'The Todo and The Activity should have the same name/summary')
        self.assertEqual(activity_1.user_id, todo_1.user_ids, 'The Todo and The Activity should have the same user')
        self.assertEqual(activity_1.date_deadline, todo_1.date_deadline.date(), 'The Todo and The Activity should have the same date deadline')


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

    def _create_task_scenarios(self, is_todo=False):
        """
        Helper method to create a standard set of test tasks/to-dos and activities.
        :param bool is_todo: If True, creates tasks without a project_id (To-Dos).
                             If False, creates tasks with a project_id.
        """
        today = fields.Date.today()
        yesterday = today - datetime.timedelta(days=1)
        tomorrow = today + datetime.timedelta(days=1)

        task_details = {'user_ids': [(6, 0, [self.test_user.id])]}
        if not is_todo:
            task_details['project_id'] = self.test_project.id

        # SCENARIO 1: A single record with TWO overdue activities.
        record_overdue = self.env['project.task'].create({**task_details, 'name': 'Overdue Record'})
        self.env['mail.activity'].create([
            {
                'res_id': record_overdue.id,
                'res_model_id': self.env.ref('project.model_project_task').id,
                'user_id': self.test_user.id,
                'date_deadline': yesterday,
                'summary': 'Overdue 1',
            },
            {
                'res_id': record_overdue.id,
                'res_model_id': self.env.ref('project.model_project_task').id,
                'user_id': self.test_user.id,
                'date_deadline': yesterday,
                'summary': 'Overdue 2',
            },
        ])

        # SCENARIO 2: A single record with 'today' and 'planned' activities.
        record_today = self.env['project.task'].create({**task_details, 'name': 'Today Record'})
        self.env['mail.activity'].create([
            {
                'res_id': record_today.id,
                'res_model_id': self.env.ref('project.model_project_task').id,
                'user_id': self.test_user.id,
                'date_deadline': today,
                'summary': 'Today Activity',
            },
            {
                'res_id': record_today.id,
                'res_model_id': self.env.ref('project.model_project_task').id,
                'user_id': self.test_user.id,
                'date_deadline': tomorrow,
                'summary': 'Planned Activity',
            },
        ])

        # SCENARIO 3: A single record with one 'planned' activity.
        record_planned = self.env['project.task'].create({**task_details, 'name': 'Planned Record'})
        self.env['mail.activity'].create({
            'res_id': record_planned.id,
            'res_model_id': self.env.ref('project.model_project_task').id,
            'user_id': self.test_user.id,
            'date_deadline': tomorrow,
            'summary': 'Planned',
        })

    def test_systray_task_counting(self):
        """Tests the logic for tasks linked to a project."""
        self._create_task_scenarios(is_todo=False)

        activity_groups = self.env['res.users'].with_user(self.test_user)._get_activity_groups()

        task_group = next((g for g in activity_groups if g.get('name') == 'Task'), None)
        self.assertTrue(task_group)
        self.assertEqual(task_group['overdue_count'], 1)
        self.assertEqual(task_group['today_count'], 1)
        self.assertEqual(task_group['planned_count'], 1)
        self.assertEqual(task_group['total_count'], 2)  # overdue + today

    def test_systray_todo_counting(self):
        """Tests the logic for To-Dos (tasks not linked to a project)."""
        self._create_task_scenarios(is_todo=True)

        activity_groups = self.env['res.users'].with_user(self.test_user)._get_activity_groups()

        todo_group = next((g for g in activity_groups if g.get('name') == 'To-Do'), None)
        self.assertTrue(todo_group)
        self.assertEqual(todo_group['overdue_count'], 1)
        self.assertEqual(todo_group['today_count'], 1)
        self.assertEqual(todo_group['planned_count'], 1)
        self.assertEqual(todo_group['total_count'], 2)  # overdue + today
