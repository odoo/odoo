# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class FetchmailServer(models.Model):
    _name = 'fetchmail.server'
    _inherit = ['fetchmail.server', 'google.gmail.mixin']
    _email_field = 'user'
    _server_type_field = 'server_type'

    server_type = fields.Selection(
        selection_add=[('gmail', 'Gmail OAuth Authentication')],
        ondelete={'gmail': 'set default'})

    def _compute_server_type_info(self):
        gmail_servers, normal_servers = self._split_gmail_servers()
        gmail_servers.server_type_info = _(
            'Connect your Gmail account with the OAuth Authentication process. \n'
            'You will be redirected to the Gmail login page where you will '
            'need to accept the permission.')
        super(FetchmailServer, normal_servers)._compute_server_type_info()

    @api.onchange('server_type', 'is_ssl', 'object_id')
    def onchange_server_type(self):
        """Set the default configuration for a IMAP Gmail server."""
        if self.server_type == 'gmail':
            self.server = 'imap.gmail.com'
            self.is_ssl = True
            self.port = 993
        else:
            self.google_gmail_token_id = False
            super(FetchmailServer, self).onchange_server_type()

    def _imap_login(self, connection):
        """Authenticate the IMAP connection.

        If the mail server is Gmail, we use the OAuth2 authentication protocol.
        """
        self.ensure_one()
        if self.server_type == 'gmail':
            if not self.google_gmail_token_id:
                raise UserError(_('Please login to your Gmail account.'))
            auth_string = self.google_gmail_token_id._generate_oauth2_string()
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
