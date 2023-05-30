# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random
from contextlib import contextmanager
from unittest.mock import patch

from odoo.tests.common import tagged, HttpCase, TransactionCase


@tagged("-at_install", "post_install")
class TestMailActivityChatter(HttpCase):

    def test_chatter_activity_tour(self):
        testuser = self.env['res.users'].create({
            'email': 'testuser@testuser.com',
            'name': 'Test User',
            'login': 'testuser',
            'password': 'testuser',
        })
        self.start_tour(
            f"/web#id={testuser.partner_id.id}&model=res.partner",
            "mail_activity_schedule_from_chatter",
            login="admin",
        )

@tagged('-at_install', 'post_install')
class TestMailActivity(TransactionCase):

    def test_delete_activities_of_archived_users(self):
        """
        Validate the functionality of the cron `_cron_delete_activities_of_archived_users`
        """

        @contextmanager
        def _mock_db_cursor():
            with patch.object(type(self.env.cr), 'rollback', lambda x: None):
                yield

        users = self.env['res.users'].create([
            {
                'name': f"Clone Nr:{i}",
                'login': f"clone_{i}@example.com",
                'password': "S3cUr4DP@sSw0rD",
            } for i in range(5)
        ])
        dummy_lead = self.env['crm.lead'].create({'name': 'dummy_lead'})
        # for each user schedule 1 activity
        for user in users:
            dummy_lead.activity_schedule(user_id=user.id)
        archived_users = self.env['res.users'].browse(
            map(lambda x: x.id, random.sample(users, 2)))  # pick 2 users to archive
        archived_users.action_archive()
        active_users = users - archived_users
        with _mock_db_cursor():
            self.env['mail.activity']._cron_delete_activities_of_archived_users()
        # activities of archived users should be deleted
        activities = self.env['mail.activity'].search([('user_id', 'in', archived_users.ids)])
        self.assertFalse(activities)
        # activities of active users shouldn't be touched, each has exactly 1 activity present
        for user in active_users:
            activities = self.env['mail.activity'].search([('user_id', '=', user.id)])
            self.assertEqual(len(activities), 1)
