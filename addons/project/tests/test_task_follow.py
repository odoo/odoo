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

    def test_project_task_follow_propogation(self):
        # Tests that following the project should make user follow its tasks
        self.project_pigs.message_subscribe(partner_ids=[self.user_projectmanager.partner_id.id])
        self.assertTrue(self.user_projectmanager.partner_id in self.project_pigs.message_partner_ids)
        task_1 = self.env['project.task'].with_context(default_project_id=self.project_pigs.id).create({
            'name': 'Test Task'
        })
        self.assertTrue(self.user_projectmanager.partner_id in task_1.message_partner_ids)

    def test_project_task_notification_preferences_propogation(self):
        # Tests that notification preferences set of the user on project should be propogated to the tasks
        subtype = self.env.ref('project.mt_task_ready')
        self.project_pigs.message_subscribe(partner_ids=[self.user_projectmanager.partner_id.id], subtype_ids=[subtype.id])
        task_2 = self.env['project.task'].with_context(default_project_id=self.project_pigs.id).create({
            'name': 'Test task 2'
        })
        self.assertEqual(task_2.message_follower_ids.subtype_ids, self.project_pigs.message_follower_ids.subtype_ids)
