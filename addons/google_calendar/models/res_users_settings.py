from datetime import timedelta

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

# `_` is the translation function; a sentinel needs its own object.
_UNSET = object()


class ResUsersSettings(models.Model):
    _inherit = "res.users.settings"

    # Google Calendar tokens and synchronization information.
    #
    # The two tokens rest in credential.credential, encrypted,
    # access-logged and rate-limited, and the fields become doors onto it so
    # every reader and the session_info blacklist are unchanged. The validity is
    # not a secret and stays a column of its own.
    google_calendar_credential_id = fields.Many2one(
        comodel_name="credential.credential",
        string="Google Credential",
        copy=False,
        ondelete="restrict",
        groups="base.group_system",
        help="Holds this user's Google OAuth tokens.",
    )
    google_calendar_rtoken = fields.Char(
        string="Refresh Token",
        compute="_compute_google_calendar_tokens",
        inverse="_inverse_google_calendar_rtoken",
        copy=False,
        groups="base.group_system",
    )
    google_calendar_token = fields.Char(
        string="User token",
        compute="_compute_google_calendar_tokens",
        inverse="_inverse_google_calendar_token",
        copy=False,
        groups="base.group_system",
    )
    google_calendar_token_validity = fields.Datetime(
        string="Token Validity",
        copy=False,
        groups="base.group_system",
    )
    google_calendar_sync_token = fields.Char(
        string="Next Sync Token",
        copy=False,
        groups="base.group_system",
    )
    google_calendar_cal_id = fields.Char(
        string="Calendar ID",
        copy=False,
        groups="base.group_system",
        help="Last Calendar ID who has been synchronized. If it is changed, we remove all links between GoogleID and Odoo Google Internal ID",
    )
    google_synchronization_stopped = fields.Boolean(
        string="Google Synchronization stopped",
        copy=False,
        groups="base.group_system",
    )

    @api.model
    def _get_fields_blacklist(self):
        """Get list of google fields that won't be formatted in session_info."""
        google_fields_blacklist = [
            "google_calendar_rtoken",
            "google_calendar_token",
            "google_calendar_token_validity",
            "google_calendar_sync_token",
            "google_calendar_cal_id",
            "google_synchronization_stopped",
        ]
        return super()._get_fields_blacklist() + google_fields_blacklist

    @api.depends("google_calendar_credential_id")
    def _compute_google_calendar_tokens(self):
        for settings in self:
            credential = settings.google_calendar_credential_id.sudo()
            tokens = (
                credential._use_secret_payload("google_calendar:tokens")
                if credential
                else {}
            )
            settings.google_calendar_token = tokens.get("oauth_access_token") or False
            settings.google_calendar_rtoken = tokens.get("oauth_refresh_token") or False

    def _inverse_google_calendar_token(self):
        for settings in self:
            settings._google_store_tokens(access_token=settings.google_calendar_token)

    def _inverse_google_calendar_rtoken(self):
        for settings in self:
            settings._google_store_tokens(refresh_token=settings.google_calendar_rtoken)

    def _google_store_tokens(self, access_token=_UNSET, refresh_token=_UNSET):
        """Write whichever tokens were given into this user's credential.

        The default is a sentinel rather than None because None is a value a
        caller means: `_set_google_auth_tokens(False, False, 0)` disconnects, and
        that has to clear both rather than read as "leave these alone".
        """
        self.check_singleton()
        values = {}
        if access_token is not _UNSET:
            values["oauth_access_token"] = access_token or False
        if refresh_token is not _UNSET:
            values["oauth_refresh_token"] = refresh_token or False

        credential = self.google_calendar_credential_id.sudo()
        if credential:
            if any(values.values()):
                credential.write(values)
            else:
                # Nothing left: the user disconnected, and holding no credential
                # is what `_google_calendar_authenticated` reads.
                self.google_calendar_credential_id = False
                credential.unlink()
            return
        if not any(values.values()):
            return
        self.google_calendar_credential_id = (
            self.env["credential.credential"]
            .sudo()
            .create(
                {
                    "name": _("Google Calendar: %s", self.user_id.login),
                    "category_id": self.env.ref(
                        "credential.credential_category_oauth2"
                    ).id,
                    "company_id": self.user_id.company_id.id,
                    # In the same create: the oauth2 constraint runs there.
                    **values,
                }
            )
            .id
        )

    def _set_google_auth_tokens(self, access_token, refresh_token, ttl):
        self.sudo().write(
            {
                "google_calendar_token_validity": fields.Datetime.now()
                + timedelta(seconds=ttl)
                if ttl
                else False,
            }
        )
        for settings in self.sudo():
            settings._google_store_tokens(
                access_token=access_token, refresh_token=refresh_token
            )

    def _google_calendar_authenticated(self):
        self.check_singleton()
        return bool(self.sudo().google_calendar_rtoken)

    def _is_google_calendar_valid(self):
        self.check_singleton()
        return (
            self.sudo().google_calendar_token_validity
            and self.sudo().google_calendar_token_validity
            >= (fields.Datetime.now() + timedelta(minutes=1))
        )

    def _refresh_google_calendar_token(self):
        self.check_singleton()

        try:
            _access_token, ttl = self.env["google.service"]._refresh_google_token(
                "calendar", self.sudo().google_calendar_credential_id
            )
            self.sudo().google_calendar_token_validity = (
                fields.Datetime.now() + timedelta(seconds=ttl)
            )
            self.invalidate_recordset(
                ["google_calendar_token", "google_calendar_rtoken"]
            )
        except requests.HTTPError as error:
            if error.response.status_code in (
                400,
                401,
            ):  # invalid grant or invalid client
                # Delete refresh token and make sure it's commited
                self.env.cr.rollback()
                self.sudo()._set_google_auth_tokens(False, False, 0)
                self.env.cr.commit()
            error_key = error.response.json().get("error", "nc")
            error_msg = _(
                "An error occurred while generating the token. Your authorization code may be invalid or has already expired [%s]. "
                "You should check your Client ID and secret on the Google APIs plateform or try to stop and restart your calendar synchronization.",
                error_key,
            )
            raise UserError(error_msg) from error
