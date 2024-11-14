# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2 import IntegrityError
from unittest import skip
from unittest.mock import patch

from odoo import Command
from odoo.addons.base.models.res_users import ResUsersPatchedInTest
from odoo.addons.mail.tests.common import MailCommon, mail_new_test_user
from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.tests import tagged, users
from odoo.tools import mute_logger


class TestNotifySecurityUpdate(MailCommon):

    @users('employee')
    def test_security_update_email(self):
        """ User should be notified on old email address when the email changes """
        with self.mock_mail_gateway():
            self.env.user.write({'email': 'new@example.com'})

        self.assertMailMailWEmails(['e.e@example.com'], 'outgoing', fields_values={
            'subject': 'Security Update: Email Changed',
        })

    @users('employee')
    def test_security_update_login(self):
        with self.mock_mail_gateway():
            self.env.user.write({'login': 'newlogin'})

        self.assertMailMailWEmails([self.env.user.email_formatted], 'outgoing', fields_values={
            'subject': 'Security Update: Login Changed',
        })

    @users('employee')
    def test_security_update_password(self):
        with self.mock_mail_gateway():
            self.env.user.write({'password': 'newpassword'})

        self.assertMailMailWEmails([self.env.user.email_formatted], 'outgoing', fields_values={
            'subject': 'Security Update: Password Changed',
        })


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
class TestUserModifyOwnProfile(HttpCaseWithUserDemo):

    def test_user_modify_own_profile(self):
        """" A user should be able to modify their own profile.
        Even if that user does not have access rights to write on the res.users model. """

        if 'hr.employee' in self.env and not self.user_demo.employee_id:
            self.env['hr.employee'].create({
                'name': 'Marc Demo',
                'user_id': self.user_demo.id,
            })
            self.user_demo.groups_id += self.env.ref('hr.group_hr_user')
        self.user_demo.tz = "Europe/Brussels"

        # avoid 'reload_context' action in the middle of the tour to ease steps and form save checks
        with patch.object(ResUsersPatchedInTest, 'preference_save', lambda self: True):
            self.start_tour(
                "/odoo",
                "mail/static/tests/tours/user_modify_own_profile_tour.js",
                login="demo",
            )
        self.assertEqual(self.user_demo.email, "updatedemail@example.com")


@tagged("post_install", "-at_install")
class TestUserSettings(MailCommon):

    @skip('Crashes in post_install, probably because other modules force creation through inverse (e.g. voip)')
    def test_create_portal_user(self):
        portal_group = self.env.ref('base.group_portal')
        user = self.env.user.create({
            'name': 'A portal user',
            'login': 'portal_test',
            'groups_id': [(6, 0, [portal_group.id])],
        })
        self.assertFalse(user.res_users_settings_ids, 'Portal users should not have settings by default')

    def test_create_internal_user(self):
        user = self.env.user.create({
            'name': 'A internal user',
            'login': 'test_user',
        })
        self.assertTrue(user.res_users_settings_ids, 'Internal users should have settings by default')

    @users('employee')
    def test_find_or_create_for_user_should_create_record_if_not_existing(self):
        self.user_employee.res_users_settings_ids.unlink()  # pre autocreate or a portal user switching to internal user
        settings = self.user_employee.res_users_settings_ids
        self.assertFalse(settings, "no records should exist")

        self.env['res.users.settings']._find_or_create_for_user(self.user_employee)
        settings = self.user_employee.res_users_settings_ids
        self.assertTrue(settings, "a record should be created after _find_or_create_for_user is called")

    @users('employee')
    def test_find_or_create_for_user_should_return_correct_res_users_settings(self):
        self.user_employee.res_users_settings_ids.unlink()
        settings = self.env['res.users.settings'].create({
            'user_id': self.user_employee.id,
        })
        result = self.env['res.users.settings']._find_or_create_for_user(self.user_employee)
        self.assertEqual(result, settings, "Correct mail user settings should be returned")

    @users('employee')
    def test_set_res_users_settings_should_send_notification_on_bus(self):
        settings = self.user_employee.res_users_settings_id
        settings.is_discuss_sidebar_category_chat_open = False
        settings.is_discuss_sidebar_category_channel_open = False

        with self.assertBus(
                [(self.cr.dbname, 'res.partner', self.partner_employee.id)],
                [{
                    'type': 'res.users.settings',
                    'payload': {
                        'id': settings.id,
                        'is_discuss_sidebar_category_chat_open': True,
                    },
                }]):
            settings.set_res_users_settings({'is_discuss_sidebar_category_chat_open': True})

    @users('employee')
    def test_set_res_users_settings_should_set_settings_properly(self):
        settings = self.user_employee.res_users_settings_id
        settings.set_res_users_settings({'is_discuss_sidebar_category_chat_open': True})
        self.assertEqual(
            settings.is_discuss_sidebar_category_chat_open,
            True,
            "category state should be updated correctly"
        )
