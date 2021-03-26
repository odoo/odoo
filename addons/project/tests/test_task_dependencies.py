# -*- coding: utf-8 -*-

from odoo.fields import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.project.tests.test_project_base import TestProjectCommon


@tagged('-at_install', 'post_install', 'task_dependencies')
class TestTaskDependencies(TestProjectCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.project_pigs.write({
            'allow_task_dependencies': True,
        })
        cls.task_3 = cls.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Pigs UserTask 2',
            'user_id': cls.user_projectuser.id,
            'project_id': cls.project_pigs.id,
        })

    def test_task_dependencies(self):
        """ Test the task dependencies feature

            Test Case:
            =========
            1) Add task2 as dependency in task1
            2) Checks if the task1 has the task in depend_on_ids field.
        """
        self.assertEqual(len(self.task_1.depend_on_ids), 0, "The task 1 should not have any dependency.")
        self.task_1.write({
            'depend_on_ids': [Command.link(self.task_2.id)],
        })
        self.assertEqual(len(self.task_1.depend_on_ids), 1, "The task 1 should have a dependency.")
        self.task_1.write({
            'depend_on_ids': [Command.link(self.task_3.id)],
        })
        self.assertEqual(len(self.task_1.depend_on_ids), 2, "The task 1 should have two dependencies.")

    def test_cyclic_dependencies(self):
        """ Test the cyclic dependencies

            Test Case:
            =========
            1) Check initial setting on three tasks
            2) Add task2 as dependency in task1
            3) Add task3 as dependency in task2
            4) Add task1 as dependency in task3 and check a validation error is raised
            5) Add task1 as dependency in task2 and check a validation error is raised
        """
        # 1) Check initial setting on three tasks
        self.assertTrue(
            len(self.task_1.depend_on_ids) == len(self.task_2.depend_on_ids) == len(self.task_3.depend_on_ids) == 0,
            "The three tasks should depend on no tasks.")
        self.assertTrue(self.task_1.allow_task_dependencies, 'The task dependencies feature should be enable.')
        self.assertTrue(self.task_2.allow_task_dependencies, 'The task dependencies feature should be enable.')
        self.assertTrue(self.task_3.allow_task_dependencies, 'The task dependencies feature should be enable.')

        # 2) Add task2 as dependency in task1
        self.task_1.write({
            'depend_on_ids': [Command.link(self.task_2.id)],
        })
        self.assertEqual(len(self.task_1.depend_on_ids), 1, 'The task 1 should have one dependency.')

        # 3) Add task3 as dependency in task2
        self.task_2.write({
            'depend_on_ids': [Command.link(self.task_3.id)],
        })
        self.assertEqual(len(self.task_2.depend_on_ids), 1, "The task 2 should have one dependency.")

        # 4) Add task1 as dependency in task3 and check a validation error is raised
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.task_3.write({
                'depend_on_ids': [Command.link(self.task_1.id)],
            })
        self.assertEqual(len(self.task_3.depend_on_ids), 0, "The dependency should not be added in the task 3 because of a cyclic dependency.")

        # 5) Add task1 as dependency in task2 and check a validation error is raised
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.task_2.write({
                'depend_on_ids': [Command.link(self.task_1.id)],
            })
        self.assertEqual(len(self.task_2.depend_on_ids), 1, "The number of dependencies should no change in the task 2 because of a cyclic dependency.")
