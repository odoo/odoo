# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2 import IntegrityError
from unittest.mock import patch

from odoo import Command
from odoo.addons.base.models.res_users import Users
from odoo.addons.mail.tests.common import MailCommon, mail_new_test_user
from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger


class TestUser(MailCommon):

    @mute_logger('odoo.sql_db')
    def test_notification_type_constraint(self):
        with self.assertRaises(IntegrityError, msg='Portal user can not receive notification in Odoo'):
            mail_new_test_user(
                self.env,
                login='user_test_constraint_2',
                name='Test User 2',
                email='user_test_constraint_2@test.example.com',
                notification_type='inbox',
                groups='base.group_portal',
            )

    def test_notification_type_convert_internal_inbox_to_portal(self):
        """Tests an internal user using inbox notifications converted to portal
        is automatically set to email notifications"""
        user = mail_new_test_user(
            self.env,
            login='user_test_constraint_3',
            name='Test User 3',
            email='user_test_constraint_3@test.example.com',
            notification_type='inbox',
            groups='base.group_user',
        )

        # Ensure the internal user has well the inbox notification type
        self.assertEqual(user.notification_type, 'inbox')
        self.assertIn(self.env.ref('mail.group_mail_notification_type_inbox'), user.groups_id)

        # Change the internal user to portal, and make sure it automatically converts from inbox to email notifications
        user.write({'groups_id': [
            Command.unlink(self.env.ref('base.group_user').id),
            Command.link(self.env.ref('base.group_portal').id),
        ]})
        self.assertEqual(user.notification_type, 'email')
        self.assertNotIn(self.env.ref('mail.group_mail_notification_type_inbox'), user.groups_id)


@tagged('-at_install', 'post_install')
class TestUserModifyOwnProfile(HttpCase):

    def test_user_modify_own_profile(self):
        """" A user should be able to modify their own profile.
        Even if that user does not have access rights to write on the res.users model. """

        # avoid 'reload_context' action in the middle of the tour to ease steps and form save checks
        with patch.object(Users, 'preference_save', lambda self: True):
            self.start_tour(
                "/web",
                "mail/static/tests/tours/user_modify_own_profile_tour.js",
                login="demo",
                step_delay=100,
            )
        self.assertEqual(self.env.ref('base.user_demo').email, "updatedemail@example.com")
