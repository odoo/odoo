# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.addons.auth_totp.controllers.home import TRUSTED_DEVICE_AGE
from odoo.addons.mail.tests.common import MailCommon
from odoo.tests import tagged, users


@tagged('-at_install', 'post_install', 'mail_tools', 'res_users')
class TestNotifySecurityUpdateTotp(MailCommon):
    @users('employee')
    def test_security_update_totp_enabled_disabled(self):
        recipients = [self.env.user.email_formatted]
        with self.mock_mail_gateway():
            self.env.user.write({'totp_secret': 'test'})

        self.assertMailMailWEmails(recipients, 'outgoing', fields_values={
            'subject': 'Security Update: 2FA Activated',
        })

        with self.mock_mail_gateway():
            self.env.user.write({'totp_secret': False})

        self.assertMailMailWEmails(recipients, 'outgoing', fields_values={
            'subject': 'Security Update: 2FA Deactivated',
        })

    @users('employee')
    def test_security_update_trusted_device_added_removed(self):
        """ Make sure we notify the user when TOTP trusted devices are added/removed on his account. """
        recipients = [self.env.user.email_formatted]
        with self.mock_mail_gateway():
            self.env['auth_totp.device'].sudo()._generate(
                'trusted_device_chrome',
                'Chrome on Windows',
                datetime.now() + timedelta(seconds=TRUSTED_DEVICE_AGE)
            )

        self.assertMailMailWEmails(recipients, 'outgoing', fields_values={
            'subject': 'Security Update: Device Added',
        })

        # generating a key outside of the 'auth_totp.device' model should however not notify
        with self.mock_mail_gateway():
            self.env['res.users.apikeys']._generate(
                'new_api_key',
                'New Key',
                datetime.now() + timedelta(days=1)
            )
        self.assertNotSentEmail(recipients)

        # now remove the key using the user's relationship
        with self.mock_mail_gateway():
            self.env['auth_totp.device'].flush_model()
            self.env.user.sudo(False)._revoke_all_devices()

        self.assertMailMailWEmails(recipients, 'outgoing', fields_values={
            'subject': 'Security Update: Device Removed',
        })
