import hashlib
import hmac
import logging

from odoo import api, fields, models

from odoo.addons.rate_limit.tools import EndpointRateLimiter

_logger = logging.getLogger(__name__)


class MixinCredentialAuth(models.AbstractModel):
    _name = "mixin.credential.auth"
    _description = "Credential Authentication Mixin"

    rate_limit_enabled = fields.Boolean(
        string="Enable Rate Limiting",
        default=True,
        help="Enable rate limiting using token bucket algorithm",
    )
    rate_limit_requests = fields.Integer(
        string="Max Requests",
        default=100,
        help="Maximum number of requests allowed per time period",
    )
    rate_limit_strict = fields.Boolean(
        string="Strict Rate Limiting",
        default=False,
        help="Deny the request when the rate-limit bucket cannot be read "
        "(lock contention, timeout, internal error) instead of allowing it. "
        "Enable wherever the limit is a security control rather than a "
        "best-effort cap.",
    )

    credential_id = fields.Many2one(
        comodel_name="credential.credential",
        string="Active Credential",
        index=True,
        ondelete="restrict",
        help="Encrypted credential for authentication. Managed by credential.",
    )
    auth_type = fields.Selection(
        selection=[
            ("none", "No Authentication"),
            ("bearer", "Bearer Token"),
            ("api_key", "API Key"),
            ("hmac_sha256", "HMAC-SHA256"),
            ("hmac_sha512", "HMAC-SHA512"),
            ("custom", "Custom"),
        ],
        string="Authentication Type",
        default="bearer",
        required=True,
        help="Method used for authentication",
    )
    credential_fingerprint = fields.Char(
        compute="_compute_credential_fingerprint",
        compute_sudo=True,
        store=True,
        index=True,
        copy=False,
        groups="base.group_system",
        help="SHA-256 of the credential's secret. Lets a presented token be "
        "verified, and its channel found, without decrypting anything.",
    )

    @api.depends("credential_id", "credential_id.credential_value_encrypted")
    def _compute_credential_fingerprint(self):
        for record in self:
            credential = record.credential_id
            value = (
                credential._use_secret(
                    "fingerprint", prefer=record._secret_slot_for_auth_type()
                )
                if credential
                else False
            )
            record.credential_fingerprint = (
                hashlib.sha256(value.encode()).hexdigest() if value else False
            )

    def _secret_slot_for_auth_type(self):
        self.check_singleton()
        return {
            "bearer": "bearer_token",
            "api_key": "api_key",
        }.get(self.auth_type)

    @api.model
    def _fingerprint_token(self, token):
        return hashlib.sha256(token.encode()).hexdigest() if token else False

    def is_valid_token(self, token):
        self.check_singleton()
        stored = self.sudo().credential_fingerprint
        if not stored or not token:
            return False
        return hmac.compare_digest(stored, self._fingerprint_token(token))

    @api.model
    def _get_by_credential_token(self, token, domain=None):
        fingerprint = self._fingerprint_token(token)
        if not fingerprint:
            return self.browse()
        return self.sudo().search(
            [("credential_fingerprint", "=", fingerprint), *(domain or [])]
        )

    def _rate_limit_company_id(self):
        return

    def check_rate_limit(self, company_id=None):
        self.check_singleton()
        if company_id is None:
            company_id = self._rate_limit_company_id()
        return EndpointRateLimiter(self.env, self, company_id).check_limit()
