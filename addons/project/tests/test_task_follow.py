# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .test_project_base import TestProjectCommon

class TestTaskFollow(TestProjectCommon):

    def test_follow_on_create(self):
        # Tests that the user is follower of the task upon creation
        self.assertTrue(self.user_projectuser.partner_id in self.task_1.message_partner_ids)

    def test_follow_on_write(self):
        # Tests that the user is follower of the task upon writing new assignees
        self.task_2.user_ids += self.user_projectmanager
        self.assertTrue(self.user_projectmanager.partner_id in self.task_2.message_partner_ids)

    def test_follow_after_change_project_manager(self):
        # Change the manager to create a mail_follower for user_projectmanager linked to the project_goats
        self.project_goats.user_id = self.user_projectmanager
        # Change the manager again to create a mail_follower for user_projectuser linked to the project_goats
        self.project_goats.user_id = self.user_projectuser
        task = self.env['project.task'].create({
            'name': 'Test Task',
            'project_id': self.project_goats.id,
        })
        self.assertFalse(self.user_projectmanager.partner_id in task.message_follower_ids.partner_id)
