# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import UserError


class FetchmailServer(models.Model):
    _name = 'fetchmail.server'
    _inherit = {'fetchmail.server', 'google.gmail.mixin'}

    @api.constrains('is_gmail', 'server', 'server_type')
    def _check_is_gmail(self):
        if any(server.is_gmail and server.server_type != 'imap' for server in self):
            raise UserError(_('Gmail only supports IMAP.'))

    @api.onchange('is_gmail')
    def _onchange_is_gmail(self):
        """Set the default configuration for a IMAP Gmail server."""
        if self.is_gmail:
            self.server = 'imap.gmail.com'
            self.server_type = 'imap'
            self.is_ssl = True
            self.port = 993
        else:
            self.password = ''
            self.server = ''
            self.server_type = 'pop'
            self.is_ssl = False

    def _imap_login(self, connection):
        """Authenticate the IMAP connection.

        If the mail server is Gmail, we use the OAuth2 authentication protocol.
        """
        if self.is_gmail:
            auth_string = self._generate_oauth2_string(self.user, self.google_gmail_refresh_token)
            connection.authenticate('XOAUTH2', lambda x: auth_string)
            connection.select('INBOX')
        else:
            super(FetchmailServer, self).connect(connection)
