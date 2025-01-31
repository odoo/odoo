# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

import odoo
from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged('post_install', '-at_install')
class TestWebsiteResetPassword(HttpCase):

    def test_01_website_reset_password_tour(self):
        """The goal of this test is to make sure the reset password works."""
        # We override unlink because we don't want the email to be auto deleted
        # if the send works.
        MailMail = odoo.addons.mail.models.mail_mail.MailMail

        # We override send_mail because in HttpCase on runbot we don't have an
        # SMTP server, so if force_send is set, the test is going to fail.
        MailTemplate = odoo.addons.mail.models.mail_template.MailTemplate
        original_send_mail = MailTemplate.send_mail

        def my_send_mail(*args, **kwargs):
            kwargs.update(force_send=False)
            return original_send_mail(*args, **kwargs)

        with patch.object(MailMail, 'unlink', lambda self: None), patch.object(MailTemplate, 'send_mail', my_send_mail):
            user = self.env['res.users'].create({
                'login': 'test',
                'name': 'The King',
                'email': 'noop@example.com',
            })
            websites = self.env['website'].search([])
            website_1 = websites[0]
            if len(websites) == 1:
                website_2 = self.env['website'].create({
                    'name': 'My Website 2',
                    'domain': '',
                    'sequence': 20,
                })
            else:
                website_2 = websites[1]

            website_1.domain = "my-test-domain.com"
            website_2.domain = "https://domain-not-used.fr"

            user.partner_id.website_id = website_2.id
            self.env.invalidate_all()  # invalidate get_base_url

            user.action_reset_password()
            self.assertIn(website_2.domain, user.partner_id._get_signup_url())

            self.env.invalidate_all()

            user.partner_id.website_id = website_1.id
            user.partner_id.signup_prepare(signup_type="reset")
            self.assertIn(website_1.domain, user.partner_id._get_signup_url())

            (website_1 + website_2).domain = False

            user.partner_id.signup_prepare(signup_type="reset")
            self.env.invalidate_all()

            self.start_tour(user.partner_id._get_signup_url(), 'website_reset_password', login=None)

    def test_02_multi_user_login(self):
        # In case Specific User Account is activated on a website, the same login can be used for
        # several users. Make sure we can still log in if 2 users exist.
        website = self.env["website"].get_current_website()
        website.ensure_one()
        internal_group = self.env.ref('base.group_user')
        portal_group = self.env.ref('base.group_portal')

        # Use AAA and ZZZ as names since res.users are ordered by 'login, name'
        self.env["res.users"].create({
            "website_id": False, "login": "bobo@mail.com", "name": "AAA",
            "password": "bobo@mail.com", "group_ids": [
                Command.link(portal_group.id),
                Command.unlink(internal_group.id),
            ],
        })
        user2 = self.env["res.users"].create({
            "website_id": website.id, "login": "bobo@mail.com", "name": "ZZZ",
            "password": "bobo@mail.com", "group_ids": [
                Command.link(portal_group.id),
                Command.unlink(internal_group.id),
            ],
        })

        # The most specific user should be selected
        self.authenticate("bobo@mail.com", "bobo@mail.com")
        self.assertEqual(self.session["uid"], user2.id)

    def test_multi_website_reset_password_user_specific_user_account(self):
        # Create same user on different websites with 'Specific User Account'
        # option enabled and then reset password. Only the user from the
        # current website should be reset.
        website_1, website_2 = self.env['website'].create([
            {'name': 'Website 1', 'specific_user_account': True},
            {'name': 'Website 2', 'specific_user_account': True},
        ])

        internal_group = self.env.ref('base.group_user')
        portal_group = self.env.ref('base.group_portal')
        login = 'user@example.com'  # same login for both users
        user_website_1, user_website_2 = self.env['res.users'].with_context(no_reset_password=True).create([
            {'website_id': website_1.id, 'login': login, 'email': login, 'name': login, "group_ids": [Command.link(portal_group.id), Command.unlink(internal_group.id)]},
            {'website_id': website_2.id, 'login': login, 'email': login, 'name': login, "group_ids": [Command.link(portal_group.id), Command.unlink(internal_group.id)]},
        ])

        self.assertFalse(user_website_1.signup_type)
        self.assertFalse(user_website_2.signup_type)

        self.env['res.users'].with_context(website_id=website_1.id).reset_password(login)

        self.assertTrue(user_website_1.signup_type)
        self.assertFalse(user_website_2.signup_type)
