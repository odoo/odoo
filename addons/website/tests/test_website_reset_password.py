# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

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
            self.browser_js("/", "odoo.__DEBUG__.services['web_tour.tour'].run('website_reset_password')", "odoo.__DEBUG__.services['web_tour.tour'].tours.website_reset_password.ready", login="admin")
