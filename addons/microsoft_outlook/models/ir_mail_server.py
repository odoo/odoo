# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class IrMailServer(models.Model):
    """Add the Outlook OAuth authentication on the outgoing mail servers."""

    _name = 'ir.mail_server'
    _inherit = ['ir.mail_server', 'microsoft.outlook.mixin']

    _OUTLOOK_SCOPE = 'https://outlook.office.com/SMTP.Send'

    smtp_authentication = fields.Selection(
        selection_add=[('outlook', 'Outlook OAuth Authentication')],
        ondelete={'outlook': 'set default'})

    @api.depends('smtp_authentication')
    def _compute_is_microsoft_outlook_configured(self):
        outlook_servers = self.filtered(lambda server: server.smtp_authentication == 'outlook')
        (self - outlook_servers).is_microsoft_outlook_configured = False
        super(IrMailServer, outlook_servers)._compute_is_microsoft_outlook_configured()

    def _compute_smtp_authentication_info(self):
        outlook_servers = self.filtered(lambda server: server.smtp_authentication == 'outlook')
        outlook_servers.smtp_authentication_info = _(
            'Connect your Outlook account with the OAuth Authentication process.  \n'
            'By default, only a user with a matching email address will be able to use this server. '
            'To extend its use, you should set a "mail.default.from" system parameter.')
        super(IrMailServer, self - outlook_servers)._compute_smtp_authentication_info()

    @api.constrains('smtp_authentication', 'smtp_pass', 'smtp_encryption', 'smtp_user')
    def _check_use_microsoft_outlook_service(self):
        outlook_servers = self.filtered(lambda server: server.smtp_authentication == 'outlook')
        for server in outlook_servers:
            if server.smtp_pass:
                raise UserError(_(
                    'Please leave the password field empty for Outlook mail server %r. '
                    'The OAuth process does not require it', server.name))

            if server.smtp_encryption != 'starttls':
                raise UserError(_(
                    'Incorrect Connection Security for Outlook mail server %r. '
                    'Please set it to "TLS (STARTTLS)".', server.name))

            if not server.smtp_user:
                raise UserError(_(
                            'Please fill the "Username" field with your Outlook/Office365 username (your email address). '
                            'This should be the same account as the one used for the Outlook OAuthentication Token.'))

    @api.onchange('smtp_encryption')
    def _onchange_encryption(self):
        """Do not change the SMTP configuration if it's a Outlook server

        (e.g. the port which is already set)"""
        if self.smtp_authentication != 'outlook':
            super()._onchange_encryption()

    @api.onchange('smtp_authentication')
    def _onchange_smtp_authentication_outlook(self):
        if self.smtp_authentication == 'outlook':
            self.smtp_host = 'smtp.outlook.com'
            self.smtp_encryption = 'starttls'
            self.smtp_port = 587
        else:
            self.microsoft_outlook_refresh_token = False
            self.microsoft_outlook_access_token = False
            self.microsoft_outlook_access_token_expiration = False

    @api.onchange('smtp_user', 'smtp_authentication')
    def _on_change_smtp_user_outlook(self):
        """The Outlook mail servers can only be used for the user personal email address."""
        if self.smtp_authentication == 'outlook':
            self.from_filter = self.smtp_user

    def _smtp_login(self, connection, smtp_user, smtp_password):
        if len(self) == 1 and self.smtp_authentication == 'outlook':
            auth_string = self._generate_outlook_oauth2_string(smtp_user)
            oauth_param = base64.b64encode(auth_string.encode()).decode()
            connection.ehlo()
            connection.docmd('AUTH', f'XOAUTH2 {oauth_param}')
        else:
            super()._smtp_login(connection, smtp_user, smtp_password)
