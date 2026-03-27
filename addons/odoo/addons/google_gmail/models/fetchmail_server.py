# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class FetchmailServer(models.Model):
    _name = 'fetchmail.server'
    _inherit = ['fetchmail.server', 'google.gmail.mixin']

    server_type = fields.Selection(selection_add=[('gmail', 'Gmail OAuth Authentication')], ondelete={'gmail': 'set default'})

    def _compute_server_type_info(self):
        gmail_servers = self.filtered(lambda server: server.server_type == 'gmail')
        gmail_servers.server_type_info = _(
            'Connect your Gmail account with the OAuth Authentication process. \n'
            'You will be redirected to the Gmail login page where you will '
            'need to accept the permission.')
        super(FetchmailServer, self - gmail_servers)._compute_server_type_info()

    @api.onchange('server_type', 'is_ssl', 'object_id')
    def onchange_server_type(self):
        """Set the default configuration for a IMAP Gmail server."""
        if self.server_type == 'gmail':
            self.server = 'imap.gmail.com'
            self.is_ssl = True
            self.port = 993
        else:
            self.google_gmail_authorization_code = False
            self.google_gmail_refresh_token = False
            self.google_gmail_access_token = False
            self.google_gmail_access_token_expiration = False
            super(FetchmailServer, self).onchange_server_type()

    def _imap_login(self, connection):
        """Authenticate the IMAP connection.

        If the mail server is Gmail, we use the OAuth2 authentication protocol.
        """
        self.ensure_one()
        if self.server_type == 'gmail':
            auth_string = self._generate_oauth2_string(self.user, self.google_gmail_refresh_token)
            connection.authenticate('XOAUTH2', lambda x: auth_string)
            connection.select('INBOX')
        else:
            super(FetchmailServer, self)._imap_login(connection)

    def _get_connection_type(self):
        """Return which connection must be used for this mail server (IMAP or POP).
        The Gmail mail server used an IMAP connection.
        """
        self.ensure_one()
        return 'imap' if self.server_type == 'gmail' else super()._get_connection_type()
