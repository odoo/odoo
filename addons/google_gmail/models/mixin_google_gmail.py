
from odoo import api, fields, models

from odoo.addons.mail_oauth2.models.mixin_oauth2_mail_provider import (
    OAUTH2_TOKEN_REQUEST_TIMEOUT,
    OAUTH2_TOKEN_VALIDITY_THRESHOLD,
)
from odoo.addons.mail_oauth2.oauth2_provider import Oauth2MailProvider

GMAIL_TOKEN_REQUEST_TIMEOUT = OAUTH2_TOKEN_REQUEST_TIMEOUT
GMAIL_TOKEN_VALIDITY_THRESHOLD = OAUTH2_TOKEN_VALIDITY_THRESHOLD

GMAIL = Oauth2MailProvider(
    prefix="google_gmail",
    label="Gmail",
    route="google_gmail",
    csrf_scope="google_gmail_oauth",
    iap_service="gmail",
    iap_endpoint_param="mail.server.gmail.iap.endpoint",
    iap_endpoint_default="https://gmail.api.odoo.com",
    authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
    token_url="https://oauth2.googleapis.com/token",
    # The scope `https://mail.google.com/` is needed for SMTP and IMAP
    # https://developers.google.com/workspace/gmail/imap/xoauth2-protocol
    scope="https://mail.google.com/ https://www.googleapis.com/auth/userinfo.email",
    # access_type and prompt needed to get a refresh token
    authorize_extra_params={"access_type": "offline", "prompt": "consent"},
)


class MixinGoogleGmail(models.AbstractModel):
    _name = "mixin.google.gmail"
    _inherit = ["mixin.oauth2.mail.provider"]

    _description = "Google Gmail Mixin"

    _SERVICE_SCOPE = GMAIL.scope

    # Doors onto `oauth2_credential_id`, not stores. The names stay: they are in
    # the views and in every caller.
    google_gmail_refresh_token = fields.Char(
        string="Refresh Token",
        compute="_compute_google_gmail_tokens",
        inverse="_inverse_google_gmail_refresh_token",
        copy=False,
        groups="base.group_system",
    )
    google_gmail_access_token = fields.Char(
        string="Access Token",
        compute="_compute_google_gmail_tokens",
        inverse="_inverse_google_gmail_access_token",
        copy=False,
        groups="base.group_system",
    )
    google_gmail_access_token_expiration = fields.Integer(
        string="Access Token Expiration Timestamp",
        copy=False,
        groups="base.group_system",
    )
    google_gmail_uri = fields.Char(
        string="URI",
        compute="_compute_gmail_uri",
        groups="base.group_system",
        help="The URL to generate the authorization code from Google",
    )

    @api.depends("oauth2_credential_id")
    def _compute_google_gmail_tokens(self):
        for record in self:
            access_token, refresh_token = record._oauth2_stored_tokens()
            record.google_gmail_access_token = access_token
            record.google_gmail_refresh_token = refresh_token

    def _inverse_google_gmail_access_token(self):
        for record in self:
            record._oauth2_store_tokens(access_token=record.google_gmail_access_token)

    def _inverse_google_gmail_refresh_token(self):
        for record in self:
            record._oauth2_store_tokens(refresh_token=record.google_gmail_refresh_token)

    def _compute_gmail_uri(self):
        self._oauth2_compute_uri(GMAIL)

    def open_google_gmail_uri(self):
        return self._oauth2_open_uri(GMAIL)

    def _get_gmail_refresh_token(self, authorization_code):
        """Request the refresh token and the initial access token from the authorization code.

        :return:
            refresh_token, access_token, access_token_expiration
        """
        return self._oauth2_get_refresh_token(GMAIL, authorization_code)

    def _get_gmail_token(self, grant_type, **values):
        return self._oauth2_get_token(GMAIL, grant_type, **values)

    def _get_gmail_access_token_iap(self, refresh_token):
        return self._oauth2_get_access_token_iap(GMAIL, refresh_token)

    def _generate_oauth2_string(self, user, refresh_token):
        """Generate a OAuth2 string which can be used for authentication.

        :param user: Email address of the Gmail account to authenticate
        :param refresh_token: unused -- the stored token is read off the record

        :return: The SASL argument for the OAuth2 mechanism.
        """
        return self._oauth2_generate_string(GMAIL, user, self._renew_gmail_access_token)

    def _renew_gmail_access_token(self):
        client_id, client_secret = self._oauth2_credentials(GMAIL)
        if not client_id or not client_secret:
            access_token, expiration = self._get_gmail_access_token_iap(
                self.google_gmail_refresh_token
            )
            self.write(
                {
                    "google_gmail_access_token": access_token,
                    "google_gmail_access_token_expiration": expiration,
                }
            )
            return
        _access_token, expiration = self._oauth2_refresh_access_token(GMAIL)
        self.google_gmail_access_token_expiration = expiration

    def _get_gmail_csrf_token(self):
        return self._oauth2_csrf_token(GMAIL)
