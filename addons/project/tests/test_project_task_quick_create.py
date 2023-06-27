# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.project.tests.test_project_base import TestProjectCommon
from odoo.tests.common import Form


class TestProjectTaskQuickCreate(TestProjectCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user1, cls.user2 = cls.env['res.users'].with_context({'no_reset_password': True}).create([{
            'name': 'Raouf 1',
            'login': 'raouf1',
            'password': 'raouf1aa',
            'email': 'raouf1@example.com',
        }, {
            'name': 'Raouf 2',
            'login': 'raouf2',
            'password': 'raouf2aa',
            'email': 'raouf2@example.com',
        }])

    def test_create_task_with_valid_expressions(self):
        # dict format = {display name: (expected name, expected tags count, expected users count, expected priority, expected planned hours)}
        valid_expressions = {
            'task A 30H 2.5h #Tag1 #tag2 @Armande @Bast @raouf1 @raouf2 !': ('task A 30H 2.5h', 2, 4, "1", 0),
            'task A 30H 2.5h #Tag1 #tag2 #tag3 @Armande @Bast @raouf1 ! @raouf2': ('task A 30H 2.5h', 3, 4, "1", 0),
            'task A ! 30H 2.5h #Tag1 #tag2 #tag3 @Armande @Bast ! @raouf1 #tag4': ('task A 30H 2.5h', 4, 3, "1", 0),
            'task A': ('task A', 0, 0, "0", 0),
            'task A !': ('task A', 0, 0, "1", 0),
            'task A 30H   2.5h #Tag1 #tag2     #tag3    @Armande      @Bast @raouf1 @raouf2': ('task A 30H   2.5h', 3, 4, "0", 0),
            'task A 30H 2.5h #Tag1 @Armande #tag3 @Bast @raouf1 #tag2 @raouf2 #tag4': ('task A 30H 2.5h', 4, 4, "0", 0),
            'task A 30H #tag1 @raouf1 Nothing !': ('task A 30H #tag1 @raouf1 Nothing', 0, 0, '1', 0),
            'task A 30H 2.5h #Tag1 #tag2 #tag3 @Armande @Bast @raouf !': ('task A 30H 2.5h @raouf', 3, 2, "1", 0),
            'task A 30H 2.5h #Tag1 #tag2 #tag3 @Armande @Bastttt @raouf1 @raouf2 !': ('task A 30H 2.5h @Bastttt', 3, 3, "1", 0),
            'task A 30H 2.5h #TAG1 #tag1 #TAG2': ('task A 30H 2.5h', 2, 0, "0", 0),
        }

        for expression, values in valid_expressions.items():
            task_form = Form(self.env['project.task'].with_context({'tracking_disable': True, 'default_project_id': self.project_pigs.id}), view="project.quick_create_task_form")
            task_form.display_name = expression
            task = task_form.save()
            results = (task.name, len(task.tag_ids), len(task.user_ids), task.priority, task.allocated_hours)
            self.assertEqual(results, values)

    def test_create_task_with_invalid_expressions(self):
        invalid_expressions = (
            '#tag1 #tag2 #tag3 @Armande @Bast @raouf1 @raouf2',
            '@Armande @Bast @raouf1 @raouf2',
            '!',
            'task A!'
        )

        for expression in invalid_expressions:
            task_form = Form(self.env['project.task'].with_context({'tracking_disable': True, 'default_project_id': self.project_pigs.id}), view="project.quick_create_task_form")
            task_form.display_name = expression
            task = task_form.save()
            results = (task.name, len(task.tag_ids), len(task.user_ids), task.priority, task.allocated_hours)
            self.assertEqual(results, (expression, 0, 0, '0', 0))

    def test_set_stage_on_project_from_task(self):
        new_stage = self.env['project.task.type'].create({
            'name': 'New Stage',
        })
        self.env['project.task'].create({
            'name': 'Test Task',
            'stage_id': new_stage.id,
            'project_id': self.project_pigs.id,
        })
        self.assertEqual(self.project_pigs.type_ids, new_stage, "Task stage is not set in project")
