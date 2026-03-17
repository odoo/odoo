import logging
import urllib.parse
from contextlib import suppress
from datetime import timedelta

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..services.qbo_api_client import QBOApiClient
from ..services.qbo_sync_engine import QBOSyncEngine

_logger = logging.getLogger(__name__)

QBO_AUTH_URL = "https://appcenter.intuit.com/connect/oauth2"
QBO_TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
QBO_REVOKE_URL = "https://developer.api.intuit.com/v2/oauth2/tokens/revoke"
QBO_DISCOVERY_URL = "https://developer.api.intuit.com/.well-known/openid_sandbox_configuration"

SCOPES = "com.intuit.quickbooks.accounting"


class QboRealm(models.Model):
    """Represents one QuickBooks Online company (realm).

    A realm holds the OAuth2 credentials for a single QBO company ID.
    Multiple Odoo companies can map to the same realm via qbo.company.mapping.
    """

    _name = "qbo.realm"
    _description = "QBO Realm (Company)"
    _order = "name"

    # ── Identity ──────────────────────────────────────────────────────────────
    name = fields.Char(string="Realm name", required=True)
    realm_id = fields.Char(
        string="QBO Company ID",
        required=True,
        help="The realmId returned by Intuit after OAuth authorization.",
    )

    # ── OAuth2 app credentials (stored per realm; use Intuit dev portal) ─────
    client_id = fields.Char(string="Client ID", required=True)
    client_secret = fields.Char(string="Client secret", required=True, groups="base.group_system")

    # ── OAuth2 tokens ─────────────────────────────────────────────────────────
    access_token = fields.Text(string="Access token", groups="base.group_system")
    refresh_token = fields.Text(string="Refresh token", groups="base.group_system")
    token_expiry = fields.Datetime(string="Token expiry")
    redirect_uri = fields.Char(
        string="Redirect URI",
        default=lambda self: self._default_redirect_uri(),
        help="Must match exactly what is registered in the Intuit developer portal.",
    )

    # ── State ─────────────────────────────────────────────────────────────────
    state = fields.Selection(
        [
            ("draft", "Not connected"),
            ("connected", "Connected"),
            ("error", "Error"),
        ],
        default="draft",
        string="Status",
    )
    last_error = fields.Text(string="Last error", readonly=True)
    last_sync_date = fields.Datetime(string="Last sync", readonly=True)

    # ── Relations ─────────────────────────────────────────────────────────────
    mapping_ids = fields.One2many(
        "qbo.company.mapping", "realm_id", string="Company mappings",
    )

    # ── Sandbox toggle ────────────────────────────────────────────────────────
    is_sandbox = fields.Boolean(
        string="Sandbox mode",
        default=False,
        help="Use the QBO sandbox API endpoint instead of production.",
    )

    # =========================================================================
    # Defaults
    # =========================================================================

    @api.model
    def _default_redirect_uri(self):
        base = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "")
        return f"{base}/qbo/callback"

    # =========================================================================
    # Computed helpers
    # =========================================================================

    @api.depends("token_expiry")
    def _compute_token_valid(self):
        now = fields.Datetime.now()
        for rec in self:
            rec.token_valid = bool(rec.token_expiry and rec.token_expiry > now)

    token_valid = fields.Boolean(compute="_compute_token_valid", string="Token valid")

    @property
    def api_base_url(self):
        if self.is_sandbox:
            return f"https://sandbox-quickbooks.api.intuit.com/v3/company/{self.realm_id}"
        return f"https://quickbooks.api.intuit.com/v3/company/{self.realm_id}"

    # =========================================================================
    # OAuth2 flow
    # =========================================================================

    def action_get_authorization_url(self):
        """Build and return the Intuit OAuth2 authorization URL for the user to visit."""
        self.ensure_one()

        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "scope": SCOPES,
            "redirect_uri": self.redirect_uri,
            "state": str(self.id),
        }
        url = f"{QBO_AUTH_URL}?{urllib.parse.urlencode(params)}"
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }

    def action_exchange_code(self, code):
        """Exchange the authorization code for access + refresh tokens.

        Called by the OAuth callback controller after the user grants access.
        """
        self.ensure_one()
        resp = requests.post(
            QBO_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
            },
            auth=(self.client_id, self.client_secret),
            headers={"Accept": "application/json"},
            timeout=15,
        )
        self._handle_token_response(resp)

    def _refresh_access_token(self):
        """Use the refresh token to obtain a new access token.

        Called automatically by QBOApiClient before each request when the
        access token has expired.
        """
        self.ensure_one()
        if not self.refresh_token:
            self._set_error("No refresh token available. Re-authorise the connection.")
            raise UserError(_("QBO realm %s has no refresh token. Please re-connect.") % self.name)

        resp = requests.post(
            QBO_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            },
            auth=(self.client_id, self.client_secret),
            headers={"Accept": "application/json"},
            timeout=15,
        )
        self._handle_token_response(resp)

    def _handle_token_response(self, resp):
        try:
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            self._set_error(str(exc))
            raise UserError(_("QBO token exchange failed: %s") % exc) from exc

        expiry = fields.Datetime.now() + timedelta(seconds=data.get("expires_in", 3600))
        self.sudo().write(
            {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token", self.refresh_token),
                "token_expiry": expiry,
                "state": "connected",
                "last_error": False,
            },
        )
        _logger.info("QBO realm %s token refreshed; expires %s", self.name, expiry)

    def action_test_connection(self):
        """Ping the QBO company endpoint to verify connectivity."""
        self.ensure_one()

        client = QBOApiClient(self)
        try:
            info = client.get_company_info()
            company_name = info.get("CompanyInfo", {}).get("CompanyName", "?")
            self.state = "connected"
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Connected"),
                    "message": _("Successfully connected to QBO company: %s") % company_name,
                    "type": "success",
                },
            }
        except Exception as exc:
            self._set_error(str(exc))
            raise UserError(_("Connection test failed: %s") % exc) from exc

    def action_disconnect(self):
        """Revoke tokens and reset to draft."""
        self.ensure_one()
        if self.access_token:
            with suppress(Exception):
                requests.post(
                    QBO_REVOKE_URL,
                    json={"token": self.refresh_token or self.access_token},
                    auth=(self.client_id, self.client_secret),
                    headers={"Accept": "application/json"},
                    timeout=10,
                )
        self.sudo().write(
            {
                "access_token": False,
                "refresh_token": False,
                "token_expiry": False,
                "state": "draft",
                "last_error": False,
            },
        )

    # =========================================================================
    # Internal helpers
    # =========================================================================

    def _set_error(self, message):
        self.sudo().write({"state": "error", "last_error": message})
        _logger.error("QBO realm %s error: %s", self.name, message)

    # =========================================================================
    # Cron entry point
    # =========================================================================

    @api.model
    def cron_sync_all_realms(self):
        """Called by the scheduled action. Iterates all active mappings."""
        mappings = self.env["qbo.company.mapping"].search([("sync_enabled", "=", True)])
        now = fields.Datetime.now()
        for mapping in mappings:
            if (
                mapping.sync_interval_minutes
                and mapping.last_sync_date
                and (now - mapping.last_sync_date).total_seconds()
                < (mapping.sync_interval_minutes * 60)
            ):
                continue
            try:
                engine = QBOSyncEngine(self.env, mapping)
                engine.sync_all()
            except Exception:
                _logger.exception("Cron sync failed for mapping %s", mapping.display_name)
