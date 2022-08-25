# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

import odoo
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
            website_1 = self.env['website'].browse(1)
            website_2 = self.env['website'].browse(2)

            website_1.domain = "my-test-domain.com"
            website_2.domain = "https://domain-not-used.fr"

            user.partner_id.website_id = 2
            self.env.invalidate_all()  # invalidate get_base_url

            user.action_reset_password()
            self.assertIn(website_2.domain, user.signup_url)

            self.env.invalidate_all()

            user.partner_id.website_id = 1
            user.action_reset_password()
            self.assertIn(website_1.domain, user.signup_url)

            (website_1 + website_2).domain = ""

            user.action_reset_password()
            self.env.invalidate_all()

            self.start_tour(user.signup_url, 'website_reset_password', login=None)

    def test_02_multi_user_login(self):
        # In case Specific User Account is activated on a website, the same login can be used for
        # several users. Make sure we can still log in if 2 users exist.
        website = self.env["website"].get_current_website()
        website.ensure_one()

        # Use AAA and ZZZ as names since res.users are ordered by 'login, name'
        self.env["res.users"].create(
            {"website_id": False, "login": "bobo@mail.com", "name": "AAA", "password": "bobo@mail.com"}
        )
        user2 = self.env["res.users"].create(
            {"website_id": website.id, "login": "bobo@mail.com", "name": "ZZZ", "password": "bobo@mail.com"}
        )

        # The most specific user should be selected
        self.authenticate("bobo@mail.com", "bobo@mail.com")
        self.assertEqual(self.session["uid"], user2.id)
