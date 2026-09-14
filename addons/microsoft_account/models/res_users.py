from datetime import timedelta

from odoo import _, api, fields, models

_UNSET = object()


class ResUsers(models.Model):
    _inherit = "res.users"

    microsoft_calendar_credential_id = fields.Many2one(
        comodel_name="credential.credential",
        string="Microsoft Credential",
        copy=False,
        ondelete="restrict",
        groups="base.group_system",
        help="Holds this user's Microsoft OAuth tokens.",
    )
    microsoft_calendar_rtoken = fields.Char(
        string="Microsoft Refresh Token",
        compute="_compute_microsoft_calendar_tokens",
        inverse="_inverse_microsoft_calendar_rtoken",
        copy=False,
        groups="base.group_system",
    )
    microsoft_calendar_token = fields.Char(
        string="Microsoft User token",
        compute="_compute_microsoft_calendar_tokens",
        inverse="_inverse_microsoft_calendar_token",
        copy=False,
        groups="base.group_system",
    )
    microsoft_calendar_token_validity = fields.Datetime(
        string="Microsoft Token Validity",
        copy=False,
    )

    @api.depends("microsoft_calendar_credential_id")
    def _compute_microsoft_calendar_tokens(self):
        for user in self:
            credential = user.microsoft_calendar_credential_id.sudo()
            tokens = (
                credential._use_secret_payload("microsoft_account:calendar_tokens")
                if credential
                else {}
            )
            user.microsoft_calendar_token = tokens.get("oauth_access_token") or False
            user.microsoft_calendar_rtoken = tokens.get("oauth_refresh_token") or False

    def _inverse_microsoft_calendar_token(self):
        for user in self:
            user._microsoft_store_tokens(access_token=user.microsoft_calendar_token)

    def _inverse_microsoft_calendar_rtoken(self):
        for user in self:
            user._microsoft_store_tokens(refresh_token=user.microsoft_calendar_rtoken)

    def _microsoft_store_tokens(self, access_token=_UNSET, refresh_token=_UNSET):
        """Write whichever tokens were given into this user's credential.

        The default is a sentinel rather than None because None is a value a
        caller means: disconnecting sets both to False, and that has to clear
        them rather than read as "leave this one alone".
        """
        self.check_singleton()
        values = {}
        if access_token is not _UNSET:
            values["oauth_access_token"] = access_token or False
        if refresh_token is not _UNSET:
            values["oauth_refresh_token"] = refresh_token or False

        credential = self.microsoft_calendar_credential_id.sudo()
        if credential:
            if any(values.values()):
                credential.write(values)
            else:
                # No tokens left: the user disconnected, and a user with no
                # credential is what `_is_microsoft_calendar_authenticated` reads.
                self.microsoft_calendar_credential_id = False
                credential.unlink()
            return
        if not any(values.values()):
            return
        self.microsoft_calendar_credential_id = (
            self.env["credential.credential"]
            .sudo()
            .create(
                {
                    "name": _("Microsoft Calendar: %s", self.login),
                    "category_id": self.env.ref(
                        "credential.credential_category_oauth2"
                    ).id,
                    "company_id": self.company_id.id,
                    # In the same create: the oauth2 constraint wants an access token or
                    # a client secret, and it runs there.
                    **values,
                }
            )
            .id
        )

    def _set_microsoft_auth_tokens(self, access_token, refresh_token, ttl):
        self.microsoft_calendar_token_validity = (
            fields.Datetime.now() + timedelta(seconds=ttl) if ttl else False
        )
        for user in self:
            user._microsoft_store_tokens(
                access_token=access_token, refresh_token=refresh_token
            )
