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

    def test_follower_subscription_update_on_move(self):
        """
        Tests that the follower's subscription preferences are updated when a task
        is moved between projects.
        """
        # We only subscribe to 'Task Stage Changed' at the project level.
        self.project_goats.message_subscribe(
            partner_ids=self.user_projectuser.partner_id.ids,
            subtype_ids=self.env.ref('project.mt_project_task_stage').ids,
        )

        # User follows task_1 with only 'Discussions' (default)
        self.task_1.message_subscribe(partner_ids=self.user_projectuser.partner_id.ids)
        task_follower = self.task_1.message_follower_ids.filtered(
            lambda f: f.partner_id == self.user_projectuser.partner_id,
        )
        st_discussion = self.env.ref('mail.mt_comment')
        self.assertEqual(
            task_follower.subtype_ids,
            st_discussion,
            "Task should initially have only the default 'Discussions' subtype.",
        )

        self.task_1.write({'project_id': self.project_goats.id})
        self.assertIn(
            self.env.ref('project.mt_task_stage'),
            task_follower.subtype_ids,
            "Follower should now be subscribed to 'Task Stage Changed'.",
        )
        self.assertIn(
            st_discussion,
            task_follower.subtype_ids,
            "Follower should still be subscribed to 'Discussions'.",
        )

    def test_batch_activity_creation_multi_project_follower(self):
        """ Test batch activity creation on tasks from different projects with a shared follower """
        (self.project_pigs | self.project_goats).message_subscribe(partner_ids=self.user_projectuser.partner_id.ids)
        self.task_2.project_id = self.project_goats
        activity_type = self.env['mail.activity.type'].search([], limit=1)
        wizard = self.env['mail.activity.schedule'].with_context(
            active_ids=(self.task_1 | self.task_2).ids,
            active_model=self.task_1._name,
        ).create({
            'activity_type_id': activity_type.id,
            'activity_user_id': self.user_projectuser.id,
        })
        wizard.action_schedule_activities()
        self.assertIn(self.user_projectuser.partner_id, self.task_1.message_partner_ids)
        self.assertIn(self.user_projectuser.partner_id, self.task_2.message_partner_ids)
