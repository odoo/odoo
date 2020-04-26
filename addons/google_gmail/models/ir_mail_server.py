# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import models, api


class IrMailServer(models.Model):
    """Represents an SMTP server, able to send outgoing emails, with SSL and TLS capabilities."""

    _name = 'ir.mail_server'
    _inherit = ['ir.mail_server', 'google.gmail.mixin']

    @api.onchange('smtp_encryption')
    def _onchange_encryption(self):
        """Do not change the SMTP configuration if it's a Gmail server

        (e.g. the port which is already set)"""
        if not self.use_google_gmail_service:
            super()._onchange_encryption()

    @api.onchange('use_google_gmail_service')
    def _onchange_use_google_gmail_service(self):
        if self.use_google_gmail_service:
            self.smtp_host = 'smtp.gmail.com'
            self.smtp_encryption = 'starttls'
            self.smtp_port = 587
        else:
            self.smtp_encryption = 'none'
            self.google_gmail_authorization_code = False
            self.google_gmail_refresh_token = False
            self.google_gmail_access_token = False
            self.google_gmail_access_token_expiration = False

    def _smtp_login(self, connection, smtp_user, smtp_password):
        if len(self) == 1 and self.use_google_gmail_service:
            auth_string = self._generate_oauth2_string(smtp_user, self.google_gmail_refresh_token)
            oauth_param = base64.b64encode(auth_string.encode()).decode()
            connection.ehlo()
            connection.docmd('AUTH', 'XOAUTH2 %s' % oauth_param)
        else:
            super(IrMailServer, self)._smtp_login(connection, smtp_user, smtp_password)
