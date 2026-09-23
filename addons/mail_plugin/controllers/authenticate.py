import base64
import datetime
import hmac
import json
import logging
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from werkzeug.exceptions import NotFound

import odoo
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class Authenticate(http.Controller):
    @http.route(
        ["/mail_client_extension/auth", "/mail_plugin/auth"],
        type="http",
        auth="user",
        methods=["GET"],
        website=True,
    )
    def auth(self, **values):
        if not request.env.user._is_internal():
            return request.render(
                "mail_plugin.app_error",
                {
                    "error": request.env._(
                        "Access Error: Only Internal Users can link their inboxes to this database."
                    )
                },
            )
        return request.render("mail_plugin.app_auth", values)

    @http.route(
        ["/mail_client_extension/auth/confirm", "/mail_plugin/auth/confirm"],
        type="http",
        auth="user",
        methods=["POST"],
    )
    def auth_confirm(self, scope, friendlyname, redirect, info=None, do=None, **kw):
        parsed_redirect = urlsplit(redirect)
        params = dict(parse_qsl(parsed_redirect.query))
        if do:
            name = friendlyname if not info else f"{friendlyname}: {info}"
            auth_code = self._generate_auth_code(scope, name)
            params.update(
                {"success": 1, "auth_code": auth_code, "state": kw.get("state", "")}
            )
        else:
            params.update({"success": 0, "state": kw.get("state", "")})
        updated_redirect = parsed_redirect._replace(query=urlencode(params))
        return request.redirect(urlunsplit(updated_redirect), local=False)

    @http.route(
        ["/mail_plugin/auth/check_version"],
        type="jsonrpc",
        auth="none",
        cors="*",
        methods=["POST", "OPTIONS"],
    )
    def auth_check_version(self):
        return 1

    @http.route(
        ["/mail_client_extension/auth/access_token", "/mail_plugin/auth/access_token"],
        type="jsonrpc",
        auth="none",
        cors="*",
        methods=["POST", "OPTIONS"],
    )
    def auth_access_token(self, auth_code="", **kw):
        if not auth_code:
            return {"error": "Invalid code"}
        auth_message = self._get_auth_code_data(auth_code)
        if not auth_message:
            return {"error": "Invalid code"}
        request.update_env(user=auth_message["uid"])
        scope = "odoo.plugin." + auth_message.get("scope", "")
        api_key = request.env["res.users.apikeys"]._generate(
            scope,
            auth_message["name"],
            datetime.datetime.now() + datetime.timedelta(days=1),
        )
        return {"access_token": api_key}

    def _get_auth_code_data(self, auth_code):
        data, auth_code_signature = auth_code.split(".")
        data = base64.b64decode(data)
        auth_code_signature = base64.b64decode(auth_code_signature)
        signature = odoo.tools.misc.hmac(
            request.env(su=True), "mail_plugin", data
        ).encode()
        if not hmac.compare_digest(auth_code_signature, signature):
            return None

        auth_message = json.loads(data)
        if datetime.datetime.now(datetime.UTC) - datetime.datetime.fromtimestamp(
            auth_message["timestamp"], tz=datetime.UTC
        ) > datetime.timedelta(minutes=3):
            return None

        return auth_message

    def _generate_auth_code(self, scope, name):
        if not request.env.user._is_internal():
            raise NotFound
        auth_dict = {
            "scope": scope,
            "name": name,
            "timestamp": int(datetime.datetime.now(datetime.UTC).timestamp()),
            "uid": request.env.uid,
        }
        auth_message = json.dumps(auth_dict, sort_keys=True).encode()
        signature = odoo.tools.misc.hmac(
            request.env(su=True), "mail_plugin", auth_message
        ).encode()
        auth_code = "%s.%s" % (
            base64.b64encode(auth_message).decode(),
            base64.b64encode(signature).decode(),
        )
        _logger.info("Auth code created - user %s, scope %s", request.env.user, scope)
        return auth_code
