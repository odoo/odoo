import zlib
from datetime import timedelta

import requests

from odoo import fields, models

OAUTH2_REFRESH_LOCK = zlib.crc32(b"credential.oauth2.refresh") & 0x7FFFFFFF

OAUTH2_EXPIRY_MARGIN = timedelta(minutes=1)


class CredentialCredential(models.Model):
    _inherit = "credential.credential"

    def _oauth2_access_token_is_current(self):
        self.check_singleton()
        expiry = self.oauth_token_date_expiration
        return bool(expiry and expiry > fields.Datetime.now() + OAUTH2_EXPIRY_MARGIN)

    def _oauth2_refresh(
        self,
        token_url,
        client_id,
        client_secret,
        *,
        purpose,
        policy="public",
        timeout=10,
        extra=None,
    ):
        self.check_singleton()
        credential = self.sudo()
        self.env.cr.execute(
            "SELECT pg_advisory_xact_lock(%s, %s)", [OAUTH2_REFRESH_LOCK, credential.id]
        )
        credential.invalidate_recordset()
        tokens = credential._use_secret_payload(f"{purpose}:oauth2_refresh")
        if credential._oauth2_access_token_is_current() and tokens.get(
            "oauth_access_token"
        ):
            return tokens["oauth_access_token"], credential._oauth2_seconds_left()
        response = self.env["ir.egress"].request(
            "POST",
            token_url,
            purpose=purpose,
            policy=policy,
            data={
                "grant_type": "refresh_token",
                "refresh_token": tokens.get("oauth_refresh_token") or "",
                "client_id": client_id,
                "client_secret": client_secret,
                **(extra or {}),
            },
            timeout=timeout,
        )
        if not response.ok:
            raise requests.HTTPError(
                f"{token_url} refused the refresh grant", response=response
            )
        body = response.json()
        expires_in = int(body.get("expires_in") or 0)
        values = {
            "oauth_access_token": body.get("access_token") or False,
            "oauth_token_date_expiration": fields.Datetime.now()
            + timedelta(seconds=expires_in)
            if expires_in
            else False,
        }
        if body.get("refresh_token"):
            values["oauth_refresh_token"] = body["refresh_token"]
        credential.write(values)
        return values["oauth_access_token"], expires_in

    def _oauth2_seconds_left(self):
        self.check_singleton()
        expiry = self.oauth_token_date_expiration
        if not expiry:
            return 0
        return max(int((expiry - fields.Datetime.now()).total_seconds()), 0)
