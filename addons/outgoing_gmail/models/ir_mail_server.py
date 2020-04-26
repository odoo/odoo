# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import models, api


class IrMailServer(models.Model):
    """Represents an SMTP server, able to send outgoing emails, with SSL and TLS capabilities."""

    _name = 'ir.mail_server'
    _inherit = {'ir.mail_server', 'google.gmail.mixin'}

    def _onchange_encryption(self):
        if not self.is_gmail:
            super(IrMailServer, self)._onchange_encryption()

    @api.onchange('is_gmail')
    def _onchange_is_gmail(self):
        if self.is_gmail:
            self.smtp_host = 'smtp.gmail.com'
            self.smtp_encryption = 'starttls'
            self.smtp_port = 587
        else:
            self.smtp_encryption = 'none'
            self.smtp_pass = ''
            self.smtp_host = ''

    def _smtp_login(self, connection, smtp_user, smtp_password, mail_server):
        if mail_server and mail_server.is_gmail:
            auth_string = self._generate_oauth2_string(smtp_user, mail_server.google_gmail_refresh_token)
            oauth_param = base64.b64encode(auth_string.encode()).decode()
            connection.ehlo()
            connection.docmd('AUTH', f'XOAUTH2 {oauth_param}')
        else:
            super(IrMailServer, self)._smtp_login(connection, smtp_user, smtp_password, mail_server)
