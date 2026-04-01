# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class FetchmailServer(models.Model):
    """Add the Outlook OAuth authentication on the incoming mail servers."""

    _name = 'fetchmail.server'
    _inherit = ['fetchmail.server', 'microsoft.outlook.mixin']

    _OUTLOOK_SCOPE = 'https://outlook.office.com/IMAP.AccessAsUser.All'

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
            self.microsoft_outlook_refresh_token = False
            self.microsoft_outlook_access_token = False
            self.microsoft_outlook_access_token_expiration = False
            super().onchange_server_type()

    def _imap_login__(self, connection):  # noqa: PLW3201
        """Authenticate the IMAP connection.

        If the mail server is Outlook, we use the OAuth2 authentication protocol.
        """
        self.ensure_one()
        if self.server_type == 'outlook':
            auth_string = self._generate_outlook_oauth2_string(self.user)
            connection.authenticate('XOAUTH2', lambda x: auth_string)
            connection.select('INBOX')
        else:
            super()._imap_login__(connection)

    def _get_connection_type(self):
        """Return which connection must be used for this mail server (IMAP or POP).
        The Outlook mail server used an IMAP connection.
        """
        self.ensure_one()
        return 'imap' if self.server_type == 'outlook' else super()._get_connection_type()
