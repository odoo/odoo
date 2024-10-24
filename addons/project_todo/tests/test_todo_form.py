from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestTodoForm(HttpCase):
    def test_creation_of_todo_with_deadline_defined(self):
        # Test ensuring the creation of a to-do with a deadline defined
        todo = self.env['project.task'].create({
            'name': 'Test Todo',
            'date_deadline': '2022-12-12',
        })
        self.assertEqual(todo.name, 'Test Todo')
        self.assertEqual(todo.date_deadline.strftime('%Y-%m-%d'), '2022-12-12')
