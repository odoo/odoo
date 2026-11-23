# -*- coding: utf-8 -*-

from odoo.fields import Command, Datetime
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.project.tests.test_project_base import TestProjectCommon

from datetime import date


@tagged('-at_install', 'post_install')
class TestTaskDependencies(TestProjectCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.project_pigs.write({
            'allow_task_dependencies': True,
        })
        cls.task_3 = cls.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Pigs UserTask 2',
            'user_ids': cls.user_projectuser,
            'project_id': cls.project_pigs.id,
        })

    def flush_tracking(self):
        """ Force the creation of tracking values. """
        self.env.flush_all()
        self.cr.precommit.run()

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

    def test_task_dependencies_settings_change(self):

        def set_task_dependencies_setting(enabled):
            features_config = self.env["res.config.settings"].create({'group_project_task_dependencies': enabled})
            features_config.execute()

        self.project_pigs.write({
            'allow_task_dependencies': False,
        })

        # As the Project General Setting group_project_task_dependencies needs to be toggled in order
        # to be applied on the existing projects we need to force it so that it does not depends on anything
        # (like demo data for instance)
        set_task_dependencies_setting(False)
        set_task_dependencies_setting(True)
        self.assertTrue(self.project_pigs.allow_task_dependencies, "Projects allow_task_dependencies should follow group_project_task_dependencies setting changes")

        self.project_chickens = self.env['project.project'].create({
            'name': 'My Chicken Project'
        })
        self.assertTrue(self.project_chickens.allow_task_dependencies, "New Projects allow_task_dependencies should default to group_project_task_dependencies")

        set_task_dependencies_setting(False)
        self.assertFalse(self.project_pigs.allow_task_dependencies, "Projects allow_task_dependencies should follow group_project_task_dependencies setting changes")

        self.project_ducks = self.env['project.project'].create({
            'name': 'My Ducks Project'
        })
        self.assertFalse(self.project_ducks.allow_task_dependencies, "New Projects allow_task_dependencies should default to group_project_task_dependencies")

    def test_duplicate_project_with_task_dependencies(self):
        self.project_pigs.allow_task_dependencies = True
        self.task_1.depend_on_ids = self.task_2
        self.task_1.date_deadline = Datetime.now()
        pigs_copy = self.project_pigs.copy()

        task1_copy = pigs_copy.task_ids.filtered(lambda t: t.name == 'Pigs UserTask')
        task2_copy = pigs_copy.task_ids.filtered(lambda t: t.name == 'Pigs ManagerTask')

        self.assertEqual(len(task1_copy), 1, "Should only contain 1 copy of UserTask")
        self.assertEqual(len(task2_copy), 1, "Should only contain 1 copy of ManagerTask")

        self.assertEqual(task1_copy.depend_on_ids.ids, [task2_copy.id],
                         "Copy should only create a relation between both copy if they are both part of the project")
        self.assertEqual(task1_copy.date_deadline, self.task_1.date_deadline, "date_deadline should be copied")

        task1_copy.depend_on_ids = self.task_1

        pigs_copy_copy = pigs_copy.copy()
        task1_copy_copy = pigs_copy_copy.task_ids.filtered(lambda t: t.name == 'Pigs UserTask')

        self.assertEqual(task1_copy_copy.depend_on_ids.ids, [self.task_1.id],
                         "Copy should not alter the relation if the other task is in a different project")

    def test_duplicate_project_with_subtask_dependencies(self):
        self.project_goats.allow_task_dependencies = True
        parent_task = self.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Parent Task',
            'project_id': self.project_goats.id,
            'child_ids': [
                Command.create({'name': 'Node 1', 'project_id': self.project_goats.id}),
                Command.create({'name': 'SuperNode 2', 'project_id': self.project_goats.id, 'child_ids': [Command.create({'name': 'Node 2', 'project_id': self.project_goats.id})]}),
                Command.create({'name': 'Node 3', 'project_id': self.project_goats.id}),
            ],
        })

        node1 = parent_task.child_ids[0]
        node2 = parent_task.child_ids[1].child_ids
        node3 = parent_task.child_ids[2]

        node1.dependent_ids = node2
        node2.dependent_ids = node3

        # Test copying the whole Node tree
        parent_task_copy = parent_task.copy()
        parent_copy_node1 = parent_task_copy.child_ids[0]
        parent_copy_node2 = parent_task_copy.child_ids[1].child_ids
        parent_copy_node3 = parent_task_copy.child_ids[2]

        # Relation should only be copied between the newly created node
        self.assertEqual(len(parent_copy_node1.dependent_ids), 1)
        self.assertEqual(parent_copy_node1.dependent_ids.ids, parent_copy_node2.ids, 'Node1copy - Node2copy relation should be present')
        self.assertEqual(len(parent_copy_node2.dependent_ids), 1)
        self.assertEqual(parent_copy_node2.dependent_ids.ids, parent_copy_node3.ids, 'Node2copy - Node3copy relation should be present')

        # Original Node should not have new relation
        self.assertEqual(len(node1.dependent_ids), 1)
        self.assertEqual(node1.dependent_ids.ids, node2.ids, 'Only Node1 - Node2 relation should be present')
        self.assertEqual(len(node2.dependent_ids), 1)
        self.assertEqual(node2.dependent_ids.ids, node3.ids, 'Only Node2 - Node3 relation should be present')

        # Test copying Node inside the chain
        single_copy_node2 = node2.copy()

        # Relation should be present between the other original node and the newly copied node
        self.assertEqual(len(single_copy_node2.depend_on_ids), 1)
        self.assertEqual(single_copy_node2.depend_on_ids.ids, node1.ids, 'Node1 - Node2copy relation should be present')
        self.assertEqual(len(single_copy_node2.dependent_ids), 1)
        self.assertEqual(single_copy_node2.dependent_ids.ids, node3.ids, 'Node2copy - Node3 relation should be present')

        # Original Node should have new relations
        self.assertEqual(len(node1.dependent_ids), 2)
        self.assertEqual(len(node3.depend_on_ids), 2)
