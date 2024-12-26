# -*- coding: utf-8 -*-

from odoo.tests import tagged

from odoo.addons.project.tests.test_project_base import TestProjectCommon


@tagged('-at_install', 'post_install')
class TestTaskTracking(TestProjectCommon):

    def flush_tracking(self):
        """ Force the creation of tracking values. """
        self.env.flush_all()
        self.cr.precommit.run()

    def test_many2many_tracking(self):
        # Basic test
        # Assign new user
        self.cr.precommit.clear()
        self.task_1.user_ids += self.user_projectmanager
        self.flush_tracking()
        self.assertEqual(len(self.task_1.message_ids), 1,
            "Assigning a new user should log a message.")
        # No change
        self.task_1.user_ids += self.user_projectmanager
        self.flush_tracking()
        self.assertEqual(len(self.task_1.message_ids), 1,
            "Assigning an already assigned user should not log a message.")
        # Removing assigness
        self.task_1.user_ids = False
        self.flush_tracking()
        self.assertEqual(len(self.task_1.message_ids), 2,
            "Removing both assignees should only log one message.")

    def test_many2many_tracking_context(self):
        # Test that the many2many tracking does not throw an error when using
        #  default values for fields that exists both on tasks and on messages
        # Using an invalid value for this test
        self.task_1.with_context(default_parent_id=-1).user_ids += self.user_projectmanager

    def test_many2many_tracking_modify_same_task_in_batch(self):
        """
        In the interface, it's possible to modify the assignees of the same task in batch (e.g. in the Group By of a list view).
        This test ensures that modifying the assignees (many2many tracked field) of the same task in batch works correctly
        and does not trigger any constraint violation about partners following twice the same object (mail_followers_res_partner_res_model_id_uniq).
        """
        self.cr.precommit.clear()
        tasks = self.task_1 + self.task_1 # Twice the same task
        # Assign new user
        tasks.user_ids += self.user_projectmanager
        self.flush_tracking()
        self.assertEqual(len(tasks.message_ids), 1, "Assigning a new user should log a message.")
        self.assertEqual(
            tasks.message_partner_ids,
            self.user_projectuser.partner_id | self.user_projectmanager.partner_id,
            "The followers of the task should be the project user and the project manager who was just added to the assignees.",
        )
