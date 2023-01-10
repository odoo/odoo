# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import UserError


class FetchmailServer(models.Model):
    _name = 'fetchmail.server'
    _inherit = ['fetchmail.server', 'google.gmail.mixin']

    @api.constrains('use_google_gmail_service', 'server_type')
    def _check_use_google_gmail_service(self):
        if any(server.use_google_gmail_service and server.server_type != 'imap' for server in self):
            raise UserError(_('Gmail authentication only supports IMAP server type.'))

    @api.onchange('use_google_gmail_service')
    def _onchange_use_google_gmail_service(self):
        """Set the default configuration for a IMAP Gmail server."""
        if self.use_google_gmail_service:
            self.server = 'imap.gmail.com'
            self.server_type = 'imap'
            self.is_ssl = True
            self.port = 993
        else:
            self.google_gmail_authorization_code = False
            self.google_gmail_refresh_token = False
            self.google_gmail_access_token = False
            self.google_gmail_access_token_expiration = False

    def _imap_login(self, connection):
        """Authenticate the IMAP connection.

        If the mail server is Gmail, we use the OAuth2 authentication protocol.
        """
        self.ensure_one()
        if self.use_google_gmail_service:
            auth_string = self._generate_oauth2_string(self.user, self.google_gmail_refresh_token)
            connection.authenticate('XOAUTH2', lambda x: auth_string)
            connection.select('INBOX')
        else:
            super(FetchmailServer, self)._imap_login(connection)
