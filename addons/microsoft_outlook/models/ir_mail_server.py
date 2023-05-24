# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import _, api, models
from odoo.exceptions import UserError


class IrMailServer(models.Model):
    """Add the Outlook OAuth authentication on the outgoing mail servers."""

    _name = 'ir.mail_server'
    _inherit = ['ir.mail_server', 'microsoft.outlook.mixin']

    _OUTLOOK_SCOPE = 'https://outlook.office.com/SMTP.Send'

    @api.constrains('use_microsoft_outlook_service', 'smtp_pass', 'smtp_encryption')
    def _check_use_microsoft_outlook_service(self):
        for server in self:
            if not server.use_microsoft_outlook_service:
                continue

            if server.smtp_pass:
                raise UserError(_(
                    'Please leave the password field empty for Outlook mail server %r. '
                    'The OAuth process does not require it')
                    % server.name)

            if server.smtp_encryption != 'starttls':
                raise UserError(_(
                    'Incorrect Connection Security for Outlook mail server %r. '
                    'Please set it to "TLS (STARTTLS)".')
                    % server.name)

            if not server.smtp_user:
                raise UserError(_(
                            'Please fill the "Username" field with your Outlook/Office365 username (your email address). '
                            'This should be the same account as the one used for the Outlook OAuthentication Token.'))

    @api.onchange('smtp_encryption')
    def _onchange_encryption(self):
        """Do not change the SMTP configuration if it's a Outlook server

        (e.g. the port which is already set)"""
        if not self.use_microsoft_outlook_service:
            super()._onchange_encryption()

    @api.onchange('use_microsoft_outlook_service')
    def _onchange_use_microsoft_outlook_service(self):
        if self.use_microsoft_outlook_service:
            self.smtp_host = 'smtp.outlook.com'
            self.smtp_encryption = 'starttls'
            self.smtp_port = 587
        else:
            self.microsoft_outlook_refresh_token = False
            self.microsoft_outlook_access_token = False
            self.microsoft_outlook_access_token_expiration = False

    def _smtp_login(self, connection, smtp_user, smtp_password):
        if len(self) == 1 and self.use_microsoft_outlook_service:
            auth_string = self._generate_outlook_oauth2_string(smtp_user)
            oauth_param = base64.b64encode(auth_string.encode()).decode()
            connection.ehlo()
            connection.docmd('AUTH', 'XOAUTH2 %s' % oauth_param)
        else:
            super()._smtp_login(connection, smtp_user, smtp_password)
