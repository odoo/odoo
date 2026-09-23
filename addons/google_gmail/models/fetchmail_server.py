from odoo import api, fields, models
from odoo.api import ValuesType
from odoo.exceptions import UserError


class FetchmailServer(models.Model):
    _name = "fetchmail.server"
    _inherit = ["fetchmail.server", "mixin.google.gmail"]

    server_type = fields.Selection(
        selection_add=[("gmail", "Gmail OAuth Authentication")],
        ondelete={"gmail": "set default"},
    )

    def _compute_server_type_info(self):
        gmail_servers = self.filtered(lambda server: server.server_type == "gmail")
        gmail_servers.server_type_info = self.env._(
            "Connect your Gmail account with the OAuth Authentication process. \n"
            "You will be redirected to the Gmail login page where you will "
            "need to accept the permission."
        )
        super(FetchmailServer, self - gmail_servers)._compute_server_type_info()

    @api.constrains("server_type", "encryption", "password", "user")
    def _check_use_google_gmail_service(self):
        """Mirror ``ir.mail_server``'s Gmail constraint on the incoming side.

        The outgoing half has checked all three of these for a long time; the incoming
        half checked only the encryption, so a Gmail server could carry a stored
        password that the OAuth flow never uses and no username for it to match.
        """
        for server in self.filtered(lambda s: s.server_type == "gmail"):
            if server.password:
                raise UserError(
                    self.env._(
                        "Please leave the password field empty for Gmail mail server “%s”. "
                        "The OAuth process does not require it.",
                        server.name,
                    )
                )
            if server.encryption not in ("ssl", "ssl_strict"):
                raise UserError(
                    self.env._(
                        "Incorrect Connection Encryption for Gmail mail server “%s”. "
                        'Please set it to "SSL/TLS".',
                        server.name,
                    )
                )
            if not server.user:
                raise UserError(
                    self.env._(
                        'Please fill the "Username" field with your Gmail username (your email address). '
                        "This should be the same account as the one used for the Gmail "
                        "OAuthentication Token."
                    )
                )

    def _prepare_server_type_defaults(self) -> ValuesType:
        """Gmail is IMAPS on 993, and its tokens belong to no other server type.

        This extends a plain helper rather than overriding ``_onchange_server_type``.
        Overriding the onchange itself meant restating ``@api.onchange``, and the ORM
        reads the trigger list off the single MRO winner -- so whichever OAuth addon
        loaded last silently decided which fields trigger the onchange for everybody.
        """
        vals = super()._prepare_server_type_defaults()
        if self.server_type == "gmail":
            vals.update(server="imap.gmail.com", encryption="ssl_strict", port=993)
        else:
            vals.update(
                google_gmail_refresh_token=False,
                google_gmail_access_token=False,
                google_gmail_access_token_expiration=False,
            )
        return vals

    def _imap_login__(self, connection):
        """Authenticate the IMAP connection.

        If the mail server is Gmail, we use the OAuth2 authentication protocol.
        """
        self.check_singleton()
        if self.server_type == "gmail":
            auth_string = self._generate_oauth2_string(
                self.user, self.google_gmail_refresh_token
            )
            connection.authenticate("XOAUTH2", lambda x: auth_string)
        else:
            super()._imap_login__(connection)

    def _get_connection_type(self):
        """Return which connection must be used for this mail server (IMAP or POP).
        The Gmail mail server used an IMAP connection.
        """
        self.check_singleton()
        return "imap" if self.server_type == "gmail" else super()._get_connection_type()
