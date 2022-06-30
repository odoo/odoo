# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCommon
from odoo.tests import users


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
