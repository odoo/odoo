# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2 import IntegrityError
from unittest.mock import patch

from odoo.addons.base.models.res_users import Users
from odoo.addons.mail.tests.common import MailCommon, mail_new_test_user
from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.tests import RecordCapturer, tagged, users
from odoo.tools import mute_logger


@tagged('-at_install', 'post_install', 'mail_tools', 'res_users')
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


@tagged('-at_install', 'post_install', 'mail_tools', 'res_users')
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
            (3, self.env.ref('base.group_user').id),
            (4, self.env.ref('base.group_portal').id),
        ]})
        self.assertEqual(user.notification_type, 'email')
        self.assertNotIn(self.env.ref('mail.group_mail_notification_type_inbox'), user.groups_id)

        admin = mail_new_test_user(
            self.env,
            login="user_test_constraint_4",
            name="Test User 4",
            email="user_test_constraint_3@test.example.com",
            notification_type='inbox',
            groups='base.group_erp_manager',
        )
        # Re-check that no error occurs when we have overlapping writes on admin user
        admin.write({
            'notification_type': 'email',
            'groups_id': [
                (3, self.env.ref('base.group_user').id),
                (4, self.env.ref('base.group_portal').id),
            ],
        })
        self.assertFalse(admin._is_admin())
        self.assertTrue(admin._is_portal())
        self.assertEqual(admin.notification_type, 'email')
        self.assertNotIn(self.env.ref('mail.group_mail_notification_type_inbox'), admin.groups_id)

    def test_web_create_users(self):
        src = [
            'POILUCHETTE@test.example.com',
            '"Jean Poilvache" <POILVACHE@test.example.com>',
        ]
        with self.mock_mail_gateway(), \
             RecordCapturer(self.env['res.users'], []) as capture:
            self.env['res.users'].web_create_users(src)

        exp_emails = ['poiluchette@test.example.com', 'poilvache@test.example.com']
        # check reset password are effectively sent
        for user_email in exp_emails:
            # do not use assertMailMailWEmails as mails are removed whatever we
            # try to do, code is using a savepoint to avoid storing mail.mail
            # in DB
            self.assertSentEmail(
                self.env.company.partner_id.email_formatted,
                [user_email],
                email_from=self.env.company.partner_id.email_formatted,
            )

        # order does not seem guaranteed
        self.assertEqual(len(capture.records), 2, 'Should create one user / entry')
        self.assertEqual(
            sorted(capture.records.mapped('name')),
            sorted(('poiluchette@test.example.com', 'Jean Poilvache'))
        )
        self.assertEqual(
            sorted(capture.records.mapped('email')),
            sorted(exp_emails)
        )


@tagged('-at_install', 'post_install', 'res_users')
class TestUserTours(HttpCaseWithUserDemo):

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
        with patch.object(Users, 'preference_save', lambda self: True):
            self.start_tour(
                "/web",
                "mail/static/tests/tours/user_modify_own_profile_tour.js",
                login="demo",
                step_delay=100,
            )
        self.assertEqual(self.user_demo.email, "updatedemail@example.com")
