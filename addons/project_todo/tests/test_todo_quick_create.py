from odoo.addons.project.tests.test_project_base import TestProjectCommon
from odoo.tests import Form, users


class TestTodoQuickCreate(TestProjectCommon):

    @users('armandel')
    def test_create_todo_with_valid_expressions(self):
        valid_expressions = {
            'todo A #Tag1 #tag2 @Armande @Bast !': ('todo A', 2, 2, "1"),
            'todo A #Tag1 #tag2 #tag3 @Armande @Bast': ('todo A', 3, 2, "0"),
            'todo A ! #Tag1 #tag2 #tag3 @Armande @Bast ! #tag4': ('todo A', 4, 2, "1"),
            'todo A': ('todo A', 0, 1, "0"),
            'todo A !': ('todo A', 0, 1, "1"),
            'todo A #Tag1 #tag2     #tag3    @Armande      @Bast': ('todo A', 3, 2, "0"),
            'todo A #Tag1 @Armande #tag3 @Bast #tag2 #tag4': ('todo A', 4, 2, "0"),
            'todo A #tag1 Nothing !': ('todo A #tag1 Nothing', 0, 1, '1'),
            'todo A #Tag1 #tag2 #tag3 @Armande @Bast !': ('todo A', 3, 2, "1"),
            'todo A #Tag1 #tag2 #tag3 @Armande @Bastttt !': ('todo A @Bastttt', 3, 1, "1"),
            'todo A #TAG1 #tag1 #TAG2': ('todo A', 2, 1, "0"),
        }

        for expression, values in valid_expressions.items():
            todo_form = Form(self.env['project.task'], view="project_todo.project_task_view_todo_quick_create_form")
            todo_form.display_name = expression
            todo = todo_form.save()
            results = (todo.name, len(todo.tag_ids), len(todo.user_ids), todo.priority)
            self.assertEqual(results, values)

    @users('armandel')
    def test_create_todo_with_invalid_expressions(self):
        invalid_expressions = {
            '#tag1 #tag2 #tag3 @Armande @Bast': ('Untitled to-do', 0, 1, "0"),
            '@Armande @Bast': ('Untitled to-do', 0, 1, "0"),
            '!': ('Untitled to-do', 0, 1, "0"),
            'todoA!': ('todoA!', 0, 1, "0"),
        }

        for expression, values in invalid_expressions.items():
            todo_form = Form(self.env['project.task'], view="project_todo.project_task_view_todo_quick_create_form")
            todo_form.display_name = expression
            todo = todo_form.save()
            results = (todo.name, len(todo.tag_ids), len(todo.user_ids), todo.priority)
            self.assertEqual(results, values)

    def test_create_task_with_no_name_in_quick_create_view(self):
        todo_form = Form(self.env['project.task'], view="project_todo.project_task_view_todo_quick_create_form")
        todo_form.display_name = False
        with self.assertRaises(AssertionError):
            todo_form.save()
