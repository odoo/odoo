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
