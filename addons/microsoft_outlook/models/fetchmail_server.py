from odoo import api, fields, models
from odoo.api import ValuesType
from odoo.exceptions import UserError


class FetchmailServer(models.Model):
    """Add the Outlook OAuth authentication on the incoming mail servers."""

    _name = "fetchmail.server"
    _inherit = ["fetchmail.server", "mixin.microsoft.outlook"]

    _OUTLOOK_SCOPE = "https://outlook.office.com/IMAP.AccessAsUser.All"

    server_type = fields.Selection(
        selection_add=[("outlook", "Outlook OAuth Authentication")],
        ondelete={"outlook": "set default"},
    )

    def _compute_server_type_info(self):
        outlook_servers = self.filtered(lambda server: server.server_type == "outlook")
        outlook_servers.server_type_info = self.env._(
            "Connect your personal Outlook account using OAuth. \n"
            "You will be redirected to the Outlook login page to accept "
            "the permissions."
        )
        super(FetchmailServer, self - outlook_servers)._compute_server_type_info()

    @api.constrains("server_type", "encryption", "password", "user")
    def _check_use_microsoft_outlook_service(self):
        """Mirror ``ir.mail_server``'s Outlook constraint on the incoming side.

        The outgoing half has checked all three of these for a long time; the incoming
        half checked only the encryption, so an Outlook server could carry a stored
        password that the OAuth flow never uses and no username for it to match.
        """
        for server in self.filtered(lambda s: s.server_type == "outlook"):
            if server.password:
                raise UserError(
                    self.env._(
                        "Please leave the password field empty for Outlook mail server “%s”. "
                        "The OAuth process does not require it.",
                        server.name,
                    )
                )
            if server.encryption not in ("ssl", "ssl_strict"):
                raise UserError(
                    self.env._(
                        "Incorrect Connection Encryption for Outlook mail server “%s”. "
                        'Please set it to "SSL/TLS".',
                        server.name,
                    )
                )
            if not server.user:
                raise UserError(
                    self.env._(
                        'Please fill the "Username" field with your Outlook/Office365 username (your email address). '
                        "This should be the same account as the one used for the Outlook "
                        "OAuthentication Token."
                    )
                )

    def _prepare_server_type_defaults(self) -> ValuesType:
        """Outlook is IMAPS on 993, and its tokens belong to no other server type.

        This extends a plain helper rather than overriding ``_onchange_server_type``.
        Overriding the onchange itself meant restating ``@api.onchange``, and the ORM
        reads the trigger list off the single MRO winner -- so this class, loading
        last, used to disable the ``encryption`` trigger for every server type.
        """
        vals = super()._prepare_server_type_defaults()
        if self.server_type == "outlook":
            vals.update(server="imap.outlook.com", encryption="ssl_strict", port=993)
        else:
            vals.update(
                microsoft_outlook_refresh_token=False,
                microsoft_outlook_access_token=False,
                microsoft_outlook_access_token_expiration=False,
            )
        return vals

    def _imap_login__(self, connection):
        """Authenticate the IMAP connection.

        If the mail server is Outlook, we use the OAuth2 authentication protocol.
        """
        self.check_singleton()
        if self.server_type == "outlook":
            auth_string = self._generate_outlook_oauth2_string(self.user)
            connection.authenticate("XOAUTH2", lambda x: auth_string)
        else:
            super()._imap_login__(connection)

    def _get_connection_type(self):
        """Return which connection must be used for this mail server (IMAP or POP).

        The Outlook mail server uses an IMAP connection.
        """
        self.check_singleton()
        return (
            "imap" if self.server_type == "outlook" else super()._get_connection_type()
        )
