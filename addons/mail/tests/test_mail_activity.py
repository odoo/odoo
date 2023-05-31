# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random
from contextlib import contextmanager
from datetime import datetime, timedelta
from freezegun import freeze_time
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

    def test_delete_old_overdue_activities(self):
        """
        Validate the behaviour of `_cron_delete_overdue_activities`
        """
        @contextmanager
        def _mock_db_cursor():
            with patch.object(type(self.env.cr), 'rollback', lambda x: None):
                yield

        FREEZE_DATE = '2023-05-30'
        OLD_OVERDUE_DAYS_THRESHOLD = 2
        DAY_RANGE = 10
        TIME_WINDOW = 2
        dummy_user = self.env['res.users'].create({
                'name': "some name",
                'login': "someemail@example.com",
                'password': "S3cUr4DP@sSw0rD",
        })
        dummy_lead = self.env['crm.lead'].create({'name': 'dummy_lead'})
        dates = [datetime.fromisoformat(FREEZE_DATE) - timedelta(days=day_delta) for day_delta in range(-DAY_RANGE, DAY_RANGE)]
        activities = self.env['mail.activity']
        for date in dates:
            activities += dummy_lead.activity_schedule(user_id=dummy_user.id, date_deadline=date.date())
        not_overdue_activities_count = len(activities.filtered_domain([('state', '!=', 'overdue')]))
        activity_count = len(activities)
        activities_ids = activities.ids
        with freeze_time(FREEZE_DATE), _mock_db_cursor():
            activities._cron_delete_overdue_activities(older_than_days=OLD_OVERDUE_DAYS_THRESHOLD, time_window_days=TIME_WINDOW)
        leftover_activities = self.env['mail.activity'].search([('id', 'in', activities_ids)])
        self.assertEqual(len(leftover_activities), activity_count - TIME_WINDOW, "More or less activity were removed than expected")
        self.assertFalse(leftover_activities.filtered_domain([
            ('date_deadline', '<=', datetime.fromisoformat(FREEZE_DATE) - timedelta(days=OLD_OVERDUE_DAYS_THRESHOLD)),
            ('date_deadline', '>', datetime.fromisoformat(FREEZE_DATE) - timedelta(days=OLD_OVERDUE_DAYS_THRESHOLD + TIME_WINDOW)),
        ]), "All activities in the timeframe should have been deleted.")
        self.assertEqual(len(leftover_activities.filtered_domain([('state', '!=', 'overdue')])), not_overdue_activities_count,
                         "No activities that weren't overdue should have been touched.")
