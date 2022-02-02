# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.exceptions import UserError


class FetchmailServer(models.Model):
    _name = 'fetchmail.server'
    _inherit = ['fetchmail.server', 'microsoft.outlook.mixin']

    _SERVICE_SCOPE = 'https://outlook.office.com/IMAP.AccessAsUser.All'

    @api.constrains('use_microsoft_outlook_service', 'server_type')
    def _check_use_microsoft_outlook_service(self):
        if any(server.use_microsoft_outlook_service and server.server_type != 'imap' for server in self):
            raise UserError(_('Outlook authentication only supports IMAP server type.'))

    @api.onchange('use_microsoft_outlook_service')
    def _onchange_use_microsoft_outlook_service(self):
        """Set the default configuration for a IMAP Outlook server."""
        if self.use_microsoft_outlook_service:
            self.server = 'imap.outlook.com'
            self.server_type = 'imap'
            self.is_ssl = True
            self.port = 993
        else:
            self.server_type = 'pop'
            self.is_ssl = False
            self.microsoft_outlook_refresh_token = False
            self.microsoft_outlook_access_token = False
            self.microsoft_outlook_access_token_expiration = False

    def _imap_login(self, connection):
        """Authenticate the IMAP connection.

        If the mail server is Outlook, we use the OAuth2 authentication protocol.
        """
        self.ensure_one()
        if self.use_microsoft_outlook_service:
            auth_string = self._generate_oauth2_string(self.user)
            connection.authenticate('XOAUTH2', lambda x: auth_string)
            connection.select('INBOX')
        else:
            super(FetchmailServer, self)._imap_login(connection)
