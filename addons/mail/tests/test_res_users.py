# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2 import IntegrityError

from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.mail.tests.common import MailCommon, mail_new_test_user
from odoo.tests import RecordCapturer, tagged
from odoo.tools import mute_logger


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
            self.assertMailMailWEmails(
                [user_email], 'sent',
                author=self.user_root.partner_id,
                email_values={
                    'email_from': self.env.company.partner_id.email_formatted,
                },
                fields_values={
                    'email_from': self.env.company.partner_id.email_formatted,
                },
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

@tagged('-at_install', 'post_install')
class TestUserTours(HttpCaseWithUserDemo):

    def test_user_modify_own_profile(self):
        """" A user should be able to modify their own profile.
        Even if that user does not have access rights to write on the res.users model. """
        if 'hr.employee' in self.env and not self.user_demo.employee_id:
            self.env['hr.employee'].create({
                'name': 'Marc Demo',
                'user_id': self.user_demo.id,
            })
        self.user_demo.tz = "Europe/Brussels"
        self.start_tour("/web", "mail/static/tests/tours/user_modify_own_profile_tour.js", login="demo")
        self.assertEqual(self.user_demo.email, "updatedemail@example.com")
