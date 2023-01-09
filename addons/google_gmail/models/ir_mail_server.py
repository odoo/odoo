# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import _, fields, models, api
from odoo.exceptions import UserError


class IrMailServer(models.Model):
    """Represents an SMTP server, able to send outgoing emails, with SSL and TLS capabilities."""

    _name = 'ir.mail_server'
    _inherit = ['ir.mail_server', 'google.gmail.mixin']

    smtp_authentication = fields.Selection(
        selection_add=[('gmail', 'Gmail OAuth Authentication')],
        ondelete={'gmail': 'set default'})

    def _compute_smtp_authentication_info(self):
        gmail_servers = self.filtered(lambda server: server.smtp_authentication == 'gmail')
        gmail_servers.smtp_authentication_info = _(
            'Connect your Gmail account with the OAuth Authentication process.  \n'
            'By default, only a user with a matching email address will be able to use this server. '
            'To extend its use, you should set a "mail.default.from" system parameter.')
        super(IrMailServer, self - gmail_servers)._compute_smtp_authentication_info()

    @api.onchange('smtp_encryption')
    def _onchange_encryption(self):
        """Do not change the SMTP configuration if it's a Gmail server
        (e.g. the port which is already set)"""
        if self.smtp_authentication != 'gmail':
            super(IrMailServer, self)._onchange_encryption()

    @api.onchange('smtp_authentication')
    def _onchange_smtp_authentication_gmail(self):
        if self.smtp_authentication == 'gmail':
            self.smtp_host = 'smtp.gmail.com'
            self.smtp_encryption = 'starttls'
            self.smtp_port = 587
        else:
            self.google_gmail_authorization_code = False
            self.google_gmail_refresh_token = False
            self.google_gmail_access_token = False
            self.google_gmail_access_token_expiration = False

    @api.onchange('smtp_user', 'smtp_authentication')
    def _on_change_smtp_user_gmail(self):
        """The Gmail mail servers can only be used for the user personal email address."""
        if self.smtp_authentication == 'gmail':
            self.from_filter = self.smtp_user

    @api.constrains('smtp_authentication', 'smtp_pass', 'smtp_encryption', 'from_filter', 'smtp_user')
    def _check_use_google_gmail_service(self):
        gmail_servers = self.filtered(lambda server: server.smtp_authentication == 'gmail')
        for server in gmail_servers:
            if server.smtp_pass:
                raise UserError(_(
                    'Please leave the password field empty for Gmail mail server %r. '
                    'The OAuth process does not require it', server.name))

            if server.smtp_encryption != 'starttls':
                raise UserError(_(
                    'Incorrect Connection Security for Gmail mail server %r. '
                    'Please set it to "TLS (STARTTLS)".', server.name))

            if server.from_filter != server.smtp_user:
                raise UserError(_(
                    'This server %r can only be used for your personal email address. '
                    'Please fill the "from_filter" field with %r.', server.name, server.smtp_user))

    def _smtp_login(self, connection, smtp_user, smtp_password):
        if len(self) == 1 and self.smtp_authentication == 'gmail':
            auth_string = self._generate_oauth2_string(smtp_user, self.google_gmail_refresh_token)
            oauth_param = base64.b64encode(auth_string.encode()).decode()
            connection.ehlo()
            connection.docmd('AUTH', f'XOAUTH2 {oauth_param}')
        else:
            super(IrMailServer, self)._smtp_login(connection, smtp_user, smtp_password)
