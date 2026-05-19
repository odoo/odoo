# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta

from odoo import fields, models
from odoo.exceptions import UserError

from .baiwang_client import BaiwangClient


class ResCompany(models.Model):
    _inherit = 'res.company'

    # ------------------
    # Fields declaration
    # ------------------

    l10n_cn_baiwang_app_key = fields.Char(string="Baiwang App Key")
    l10n_cn_baiwang_app_secret = fields.Char(string="Baiwang App Secret")
    l10n_cn_baiwang_salt = fields.Char(string="Baiwang Salt")
    l10n_cn_baiwang_cached_token = fields.Char(string="Baiwang Token")
    l10n_cn_baiwang_token_expiry = fields.Datetime(string="Token Expiry")
    l10n_cn_edi_mode = fields.Selection(
        selection=[
            ('test', 'Pre-Production'),
            ('prod', 'Production'),
        ],
        # Nothing will happen until the user register, so it can be set by default.
        default="test",
    )

    # ----------------
    # Business methods
    # ----------------

    def _get_valid_baiwang_token(self):
        """ Returns the cached token if valid, otherwise fetches a new one. """
        self.ensure_one()

        # If we have a token and it hasn't expired yet
        if self.l10n_cn_baiwang_cached_token and self.l10n_cn_baiwang_token_expiry:
            if self.l10n_cn_baiwang_token_expiry > fields.Datetime.now():
                return self.l10n_cn_baiwang_cached_token

        # Token is missing or expired, we must fetch a new one!
        # (Note: Replace 'baiwang.oauth.token' with the actual endpoint from Baiwang docs)
        client = BaiwangClient(self.l10n_cn_baiwang_app_key, self.l10n_cn_baiwang_app_secret, self.l10n_cn_baiwang_salt)

        try:
            # Usually, token endpoints require AppKey and AppSecret
            payload = {
                "appKey": self.l10n_cn_baiwang_app_key,
                "appSecret": self.l10n_cn_baiwang_app_secret,
            }
            response = client.call_api("baiwang.oauth.token", payload, token=None)  # No token needed to get a token

            if response.get("success"):
                new_token = response.get("response", {}).get("token")
                # Assume Baiwang tokens last 24 hours. Adjust based on their specs.
                new_expiry = fields.Datetime.now() + timedelta(hours=23)

                # Save it to the database
                self.write({
                    'l10n_cn_baiwang_cached_token': new_token,
                    'l10n_cn_baiwang_token_expiry': new_expiry,
                })

                # Odoo's environment needs to commit this immediately so other concurrent
                # processes don't also try to refresh the token at the same time.
                self.env.cr.commit()

                return new_token
            msg = "Failed to refresh Baiwang Token. Please check your App Key and Secret."
            raise UserError(msg)
        except Exception as e:
            raise UserError(f"Network error while refreshing token: {e!s}")
