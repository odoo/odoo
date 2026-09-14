
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.web import urljoin as url_join

from odoo.addons.mail_oauth2.models.mixin_oauth2_mail_provider import (
    OAUTH2_TOKEN_REQUEST_TIMEOUT,
    OAUTH2_TOKEN_VALIDITY_THRESHOLD,
)
from odoo.addons.mail_oauth2.oauth2_provider import Oauth2MailProvider

OUTLOOK_TOKEN_REQUEST_TIMEOUT = OAUTH2_TOKEN_REQUEST_TIMEOUT
OUTLOOK_TOKEN_VALIDITY_THRESHOLD = OAUTH2_TOKEN_VALIDITY_THRESHOLD

OUTLOOK = Oauth2MailProvider(
    prefix="microsoft_outlook",
    label="Outlook",
    route="microsoft_outlook",
    csrf_scope="microsoft_outlook_oauth",
    iap_service="outlook",
    iap_endpoint_param="mail.server.outlook.iap.endpoint",
    iap_endpoint_default="https://outlook.api.odoo.com",
    authorize_url=lambda records: url_join(
        records._get_microsoft_endpoint(), "authorize"
    ),
    token_url=lambda records: url_join(records._get_microsoft_endpoint(), "token"),
    # offline_access is needed to have the refresh_token
    scope=lambda records: (
        "openid email offline_access "
        f"https://outlook.office.com/User.read {records._OUTLOOK_SCOPE}"
    ),
    authorize_extra_params={"response_mode": "query"},
    token_sends_scope=True,
    token_error_detail=True,
)


class MixinMicrosoftOutlook(models.AbstractModel):
    _name = "mixin.microsoft.outlook"
    _inherit = ["mixin.oauth2.mail.provider"]

    _description = "Microsoft Outlook Mixin"

    _OUTLOOK_SCOPE = None

    # Doors onto `oauth2_credential_id`, not stores. The names stay: they are in
    # the views and in every caller.
    microsoft_outlook_refresh_token = fields.Char(
        string="Outlook Refresh Token",
        compute="_compute_microsoft_outlook_tokens",
        inverse="_inverse_microsoft_outlook_refresh_token",
        copy=False,
        groups="base.group_system",
    )
    microsoft_outlook_access_token = fields.Char(
        string="Outlook Access Token",
        compute="_compute_microsoft_outlook_tokens",
        inverse="_inverse_microsoft_outlook_access_token",
        copy=False,
        groups="base.group_system",
    )
    microsoft_outlook_access_token_expiration = fields.Integer(
        string="Outlook Access Token Expiration Timestamp",
        copy=False,
        groups="base.group_system",
    )
    microsoft_outlook_uri = fields.Char(
        string="Authentication URI",
        compute="_compute_outlook_uri",
        groups="base.group_system",
        help="The URL to generate the authorization code from Outlook",
    )

    @api.depends("oauth2_credential_id")
    def _compute_microsoft_outlook_tokens(self):
        for record in self:
            access_token, refresh_token = record._oauth2_stored_tokens()
            record.microsoft_outlook_access_token = access_token
            record.microsoft_outlook_refresh_token = refresh_token

    def _inverse_microsoft_outlook_access_token(self):
        for record in self:
            record._oauth2_store_tokens(
                access_token=record.microsoft_outlook_access_token
            )

    def _inverse_microsoft_outlook_refresh_token(self):
        for record in self:
            record._oauth2_store_tokens(
                refresh_token=record.microsoft_outlook_refresh_token
            )

    def _compute_outlook_uri(self):
        self._oauth2_compute_uri(OUTLOOK)

    def open_microsoft_outlook_uri(self):
        return self._oauth2_open_uri(OUTLOOK)

    def _get_outlook_refresh_token(self, authorization_code):
        """Request the refresh token and the initial access token from the authorization code.

        :return:
            refresh_token, access_token, access_token_expiration
        """
        return self._oauth2_get_refresh_token(OUTLOOK, authorization_code)

    def _get_outlook_token(self, grant_type, **values):
        return self._oauth2_get_token(OUTLOOK, grant_type, **values)

    def _get_outlook_access_token_iap(self, refresh_token):
        return self._oauth2_get_access_token_iap(OUTLOOK, refresh_token)

    def _generate_outlook_oauth2_string(self, login):
        """Generate a OAuth2 string which can be used for authentication.

        :param login: Email address of the Outlook account to authenticate
        :return: The SASL argument for the OAuth2 mechanism.
        """
        return self._oauth2_generate_string(
            OUTLOOK, login, self._renew_outlook_access_token
        )

    def _renew_outlook_access_token(self):
        if not self.microsoft_outlook_refresh_token:
            raise UserError(
                _("Please connect with your Outlook account before using it.")
            )
        client_id, client_secret = self._oauth2_credentials(OUTLOOK)
        if not client_id or not client_secret:
            (
                self.microsoft_outlook_refresh_token,
                self.microsoft_outlook_access_token,
                _id_token,
                self.microsoft_outlook_access_token_expiration,
            ) = self._get_outlook_access_token_iap(self.microsoft_outlook_refresh_token)
            return
        _access_token, expiration = self._oauth2_refresh_access_token(OUTLOOK)
        self.microsoft_outlook_access_token_expiration = expiration

    def _get_outlook_csrf_token(self):
        return self._oauth2_csrf_token(OUTLOOK)

    @api.model
    def _get_microsoft_endpoint(self):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(
                "microsoft_outlook.endpoint",
                "https://login.microsoftonline.com/common/oauth2/v2.0/",
            )
        )
