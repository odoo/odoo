# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from markupsafe import Markup
from odoo.tests.common import TransactionCase


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
