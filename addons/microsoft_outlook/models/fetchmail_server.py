# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class FetchmailServer(models.Model):
    """Add the Outlook OAuth authentication on the incoming mail servers."""

    _name = 'fetchmail.server'
    _inherit = ['fetchmail.server', 'microsoft.outlook.mixin']
    _email_field = 'user'
    _server_type_field = 'server_type'

    server_type = fields.Selection(selection_add=[('outlook', 'Outlook OAuth Authentication')], ondelete={'outlook': 'set default'})

    def _compute_server_type_info(self):
        outlook_servers = self.filtered(lambda server: server.server_type == 'outlook')
        outlook_servers.server_type_info = _(
            'Connect your personal Outlook account using OAuth. \n'
            'You will be redirected to the Outlook login page to accept '
            'the permissions.')
        super(FetchmailServer, self - outlook_servers)._compute_server_type_info()

    @api.constrains('server_type', 'is_ssl')
    def _check_use_microsoft_outlook_service(self):
        for server in self:
            if server.server_type == 'outlook' and not server.is_ssl:
                raise UserError(_('SSL is required for server “%s”.', server.name))

    @api.onchange('server_type')
    def onchange_server_type(self):
        """Set the default configuration for a IMAP Outlook server."""
        if self.server_type == 'outlook':
            self.server = 'imap.outlook.com'
            self.is_ssl = True
            self.port = 993
        else:
            self.microsoft_outlook_token_id = False
            super(FetchmailServer, self).onchange_server_type()

    def _imap_login(self, connection):
        """Authenticate the IMAP connection.

        If the mail server is Outlook, we use the OAuth2 authentication protocol.
        """
        self.ensure_one()
        if self.server_type == 'outlook':
            if not self.microsoft_outlook_token_id:
                raise UserError(_('Please login to your Outlook account.'))
            auth_string = self.microsoft_outlook_token_id._generate_outlook_oauth2_string()
            connection.authenticate('XOAUTH2', lambda x: auth_string)
            connection.select('INBOX')
        else:
            super()._imap_login(connection)

    def _get_connection_type(self):
        """Return which connection must be used for this mail server (IMAP or POP).
        The Outlook mail server used an IMAP connection.
        """
        self.ensure_one()
        return 'imap' if self.server_type == 'outlook' else super()._get_connection_type()
