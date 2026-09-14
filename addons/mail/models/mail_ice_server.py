import datetime
import json
import logging

import requests

from odoo import fields, models
from odoo.libs.debug_log import DebugLog

from odoo.addons.mail.tools.discuss import get_twilio_credentials

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class MailIceServer(models.Model):
    _name = "mail.ice.server"
    _inherit = ["mixin.credential.holder"]
    _description = "ICE Server"
    _rec_name = "uri"
    _credential_holder_field = "ice_credential_id"
    _credential_purpose = "mail:ice_server"
    _CREDENTIAL_FIELDS = {"credential": "credential"}

    server_type = fields.Selection(
        selection=[("stun", "stun:"), ("turn", "turn:")],
        string="Type",
        default="stun",
        required=True,
    )
    uri = fields.Char(
        string="URI",
        required=True,
    )
    username = fields.Char()
    credential = fields.Char(
        compute="_compute_credential_doors",
        inverse="_inverse_credential_doors",
        copy=True,
    )
    ice_credential_id = fields.Many2one(
        comodel_name="credential.credential",
        string="Credential Record",
        copy=False,
        ondelete="restrict",
        groups="base.group_system",
        help="Holds this server's TURN credential.",
    )

    def _get_local_ice_servers(self) -> list:
        ice_servers = self.sudo().search([], limit=5)
        formatted_ice_servers = []
        for ice_server in ice_servers:
            formatted_ice_server = {
                "urls": "%s:%s" % (ice_server.server_type, ice_server.uri),
            }
            if ice_server.username:
                formatted_ice_server["username"] = ice_server.username
            if ice_server.credential:
                formatted_ice_server["credential"] = ice_server.credential
            formatted_ice_servers.append(formatted_ice_server)
        return formatted_ice_servers

    _ICE_CACHE_TTL = 3600
    _ICE_CACHE_PARAM = "mail.ice_servers_cache"

    def _get_ice_servers(self) -> list:
        (account_sid, auth_token) = get_twilio_credentials(self.env)
        if not (account_sid and auth_token):
            _debug.logic("ice_servers", by="local")
            return self._get_local_ice_servers()

        icp = self.env["ir.config_parameter"].sudo()
        now = self.env.cr.now()
        cached = icp.get_param(self._ICE_CACHE_PARAM)
        if cached:
            try:
                payload = json.loads(cached)
                if datetime.datetime.fromisoformat(payload["expiry"]) > now:
                    _debug.logic(
                        "ice_servers", by="twilio_cache", expiry=payload["expiry"]
                    )
                    return payload["servers"]
            except ValueError, KeyError, TypeError:
                pass

        servers = self._get_twilio_ice_servers(account_sid, auth_token)
        if servers is None:
            _debug.logic("ice_servers", by="local_fallback")
            return self._get_local_ice_servers()
        _debug.logic("ice_servers", by="twilio", servers=len(servers))
        icp.set_param(
            self._ICE_CACHE_PARAM,
            json.dumps(
                {
                    "servers": servers,
                    "expiry": (
                        now + datetime.timedelta(seconds=self._ICE_CACHE_TTL)
                    ).isoformat(),
                }
            ),
        )
        return servers

    def _get_twilio_ice_servers(self, account_sid: str, auth_token: str) -> list | None:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Tokens.json"
        try:
            with _debug.perf("twilio_tokens_requested") as span:
                response = self.env["ir.egress"].request(
                    "POST",
                    url,
                    purpose="twilio_ice_servers",
                    auth=(account_sid, auth_token),
                    timeout=5,
                )
                span.set(status=getattr(response, "status_code", None))
        except requests.RequestException:
            _logger.warning("Could not reach Twilio for TURN servers", exc_info=True)
            return None
        if response.ok:
            response_content = response.json()
            if response_content:
                return response_content["ice_servers"]
        else:
            _logger.warning(
                "Failed to obtain TURN servers, status code: %s, content:%s",
                response.status_code,
                response.content,
            )
        return None
