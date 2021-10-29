# -*- coding: utf-8 -*-

from odoo.fields import Command
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
        self.env['base'].flush()
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

    def test_tracking_dependencies(self):
        # Enable the company setting
        self.env['res.config.settings'].create({
            'group_project_task_dependencies': True
        }).execute()
        # `depend_on_ids` is tracked
        self.task_1.with_context(mail_notrack=True).write({
            'depend_on_ids': [Command.link(self.task_2.id)]
        })
        self.cr.precommit.clear()
        # Check that changing a dependency tracked field in task_2 logs a message in task_1.
        self.task_2.write({'date_deadline': date(1983, 3, 1)}) # + 1 message in task_1 and task_2
        self.flush_tracking()
        self.assertEqual(len(self.task_1.message_ids), 1,
            'Changing the deadline on task 2 should have logged a message in task 1.')

        # Check that changing a dependency tracked field in task_1 does not log a message in task_2.
        self.task_1.date_deadline = date(2020, 1, 2) # + 1 message in task_1
        self.flush_tracking()
        self.assertEqual(len(self.task_2.message_ids), 1,
            'Changing the deadline on task 1 should not have logged a message in task 2.')

        # Check that changing a field that is not tracked at all on task 2 does not impact task 1.
        self.task_2.color = 100 # no new message
        self.flush_tracking()
        self.assertEqual(len(self.task_1.message_ids), 2,
            'Changing the color on task 2 should not have logged a message in task 1 since it is not tracked.')

        # Check that changing multiple fields does not log more than one message.
        self.task_2.write({
            'date_deadline': date(2020, 1, 1),
            'kanban_state': 'blocked',
        }) # + 1 message in task_1 and task_2
        self.flush_tracking()
        self.assertEqual(len(self.task_1.message_ids), 3,
            'Changing multiple fields on task 2 should only log one message in task 1.')

    def test_task_dependencies_settings_change(self):

        def set_task_dependencies_setting(enabled):
            features_config = self.env["res.config.settings"].create({'group_project_task_dependencies': enabled})
            features_config.execute()

        self.project_pigs.write({
            'allow_task_dependencies': False,
        })

        # As the the Project General Setting group_project_task_dependencies needs to be toggled in order
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
