# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.project.tests.test_project_base import TestProjectCommon


@tagged('-at_install', 'post_install')
class TestTaskState(TestProjectCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.project_goats.write({
            'allow_task_dependencies': True,
        })
        (cls.task_1 + cls.task_2).write({
            'project_id': cls.project_goats.id,
        })

    def test_base_state(self):
        """ Test the task base state features

            Test Case:
            =========
            1) check that task_1 and task_2 are in_progress by default
            2) add task_2 as a dependency for task_1, check that task_1 state has gone to waiting_normal.
            3) force task_1 state to done, the state of task_1 should become done
            4) switch task_1 state back to in progress, its state should automatically switch back to waiting normal because of the task_2 dependency
            5) change task_2 state to canceled, check that task_1 state has gone back to in_progress.
        """

        # 1) check that task_1 and task2 are in_progress by default
        self.assertEqual(self.task_1.state, '01_in_progress', "The task_1 should be in progress by default")
        self.assertEqual(self.task_2.state, '01_in_progress', "The task_2 should be in progress by default")

        # 2) add task2 as a dependency for task 1, check that task_1 state has gone to waiting_normal.
        self.task_1.write({
            'depend_on_ids': [Command.link(self.task_2.id)],
        })
        self.assertEqual(self.task_1.state, '04_waiting_normal', "The task_1 should be in waiting_normal after depending on another open task")


        # 3) force task_1 state to done, the state of task_1 should become done
        self.task_1.write({
            'state': '1_done',
        })
        self.assertEqual(self.task_1.state, '1_done', "The task_1 should be in done even if it has a depending task not closed")

        # 4) switch task_1 state back to in progress, its state should automatically switch back to waiting normal because of the task2 dependency

        self.task_1.write({
            'state': '01_in_progress',
        })
        self.assertEqual(self.task_1.state, '04_waiting_normal', "task_1 state should automatically switch back to waiting_normal because of the task2 dependency")

        # 5) change task_2 state to done, check that task_1 state has gone back to in_progress.

        self.task_2.write({
            'state': '1_canceled',
        })
        self.assertEqual(self.task_1.state, '01_in_progress', "task_1 state should automatically switch back to in_progress when its dependency closes")

    def test_change_stage_or_project(self):
        """
            Test special cases where the task is moved from a stage to another or a project to another

            Test Case:
            =========
            1) change task_1 to an open state and task_2 to a closed state
            2) change task_1 and task_2 stage, task_1 should go back to in_progress, task_2 should stay in its closing state
            3) change task_1 and task_2 project, they should both go back to in_progress
        """

        # 1) change task_1 to an open state and task_2 to a closed state

        stage_won = self.env['project.task.type'].search([('name', '=', 'Won')])
        project_pigs = self.env['project.project'].search([('name', '=', 'Pigs')])

        self.task_1.write({
            'state': '02_changes_requested',
        })
        self.task_2.write({
            'state': '1_canceled',
        })
        # 2) change task_1 and task_2 from stage, task_1 should go back to in_progress, task_2 should stay in its closing state
        (self.task_1 + self.task_2).write({
            'stage_id': stage_won.id,
        })
        self.task_1._onchange_stage_id()
        self.task_2._onchange_stage_id()
        self.assertEqual(self.task_1.state, '01_in_progress', "task_1 state should automatically switch back to in_progress when its stage changes")
        self.assertEqual(self.task_2.state, '1_canceled', "task_2 state should stay in its closed state")

        # 3) change task_1 and task_2 project, they should both go back to in_progress

        # we make change the task_1 state back to an open state
        self.task_1.write({
            'state': '02_changes_requested',
        })

        (self.task_1 + self.task_2).write({
            'project_id': project_pigs.id
        })
        self.task_1._onchange_project_id()
        self.task_2._onchange_project_id()
        self.assertEqual(self.task_1.state, '01_in_progress', "task_1 state should automatically switch back to in_progress when its project changes")
        self.assertEqual(self.task_2.state, '01_in_progress', "task_2 state should automatically switch back to in_progress when its project changes")

    def test_duplicate_dependent_task(self):
        self.task_1.write({
            'depend_on_ids': [Command.link(self.task_2.id)],
        })
        self.assertEqual(self.task_1.state, '04_waiting_normal', "The task_1 should be in waiting_normal after depending on another open task")

        self.task_1_copy = self.task_1.copy()
        self.assertEqual(self.task_1.state, '04_waiting_normal', "The task_1_copy should keep his dependence and stay in waiting_normal")

        self.task_2.write({
            'state': '03_approved',
        })
        self.task_2_copy = self.task_2.copy()
        self.assertEqual(self.task_2_copy.state, '01_in_progress', "The task_2_copy should go back to in_progress")

        self.task_2.write({
            'state': '1_done',
        })
        self.assertEqual(self.task_1.state, '04_waiting_normal', "The task_1 should have both tasks as dependencies and so should stay in waiting when one of the two is completed")
        self.assertEqual(self.task_1_copy.state, '04_waiting_normal', "The task_1_copy should have both tasks as dependencies and so should stay in waiting when one of the two is completed")

        self.task_2_copy.write({
            'state': '1_done',
        })

        self.assertEqual(self.task_1.state, '01_in_progress', "The task_1 should have both tasks as dependencies and so should stay go to 'done' when both dependencies are completed")
        self.assertEqual(self.task_1_copy.state, '01_in_progress', "The task_1_copy should have both tasks as dependencies and so should stay go to 'done' when both dependencies are completed")
