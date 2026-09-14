import hashlib
import hmac
import json
import logging
import secrets
from datetime import timedelta
from urllib.parse import urlencode

import requests
import werkzeug.utils

from odoo import fields, http
from odoo.exceptions import AccessDenied, UserError
from odoo.http import request

_logger = logging.getLogger(__name__)

_OAUTH_NONCE_SESSION_KEY = "integration_oauth_nonce"

_AUTHORIZE_PATH = "/api_transport/oauth/authorize/<int:credential_id>"
_CALLBACK_PATH = "/api_transport/oauth/callback"
_CALLBACK_PATH_LEGACY = "/api_gateway/oauth/callback"
_CALLBACK_PATH_REGISTERED_WITH_PROVIDERS = _CALLBACK_PATH_LEGACY


class OAuthController(http.Controller):
    @http.route(
        _AUTHORIZE_PATH,
        type="http",
        auth="user",
        website=False,
    )
    def authorize(self, credential_id, **kw):
        try:
            if not request.env.user.has_group("credential.group_credential_admin"):
                _logger.warning(
                    "Unauthorized OAuth authorize attempt by user %s "
                    "(credential_id=%s)",
                    request.env.user.login,
                    credential_id,
                )
                raise AccessDenied(
                    request.env._("You are not allowed to authorize API credentials.")
                )

            credential = request.env["credential.credential"].browse(credential_id)

            if not credential.exists():
                raise UserError(
                    request.env._("Credential not found (ID: %s)") % credential_id
                )

            if not credential.active:
                raise UserError(request.env._("Credential is inactive"))

            service = credential.endpoint_id

            if not service.auth_type == "oauth2":
                raise UserError(
                    request.env._(
                        "Service '%s' is not configured for OAuth 2.0 authentication"
                    )
                    % service.name
                )

            client_id = credential._oauth_client_id()
            if not client_id:
                raise UserError(
                    request.env._(
                        "OAuth Client ID not configured for service '%(service)s'. "
                        "Set it on the service, or on the credential itself.",
                        service=service.name,
                    )
                )

            if not service.oauth_auth_endpoint:
                raise UserError(
                    request.env._(
                        "OAuth Authorization URL not configured for service '%s'"
                    )
                    % service.name
                )

            if not service.oauth_token_endpoint:
                raise UserError(
                    request.env._("OAuth Token URL not configured for service '%s'")
                    % service.name
                )

            state = self._get_oauth_state(credential_id)

            redirect_uri = self._get_redirect_uri()

            params = {
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "state": json.dumps(state),
            }

            if service.oauth_scope:
                params["scope"] = service.oauth_scope

            auth_url = f"{service.oauth_auth_endpoint}?{urlencode(params)}"

            _logger.info(
                "OAuth authorization initiated: credential_id=%s, service=%s, user=%s",
                credential_id,
                service.code,
                request.env.user.login,
            )

            return werkzeug.utils.redirect(auth_url, 303)

        except AccessDenied as e:
            return request.render(
                "http_routing.http_error",
                {
                    "status_code": request.env._("Access Denied"),
                    "status_message": str(e),
                },
            )

        except UserError as e:
            return request.render(
                "http_routing.http_error",
                {
                    "status_code": request.env._("OAuth Authorization Error"),
                    "status_message": str(e),
                },
            )

        except Exception:
            _logger.exception("OAuth authorization failed")
            return request.render(
                "http_routing.http_error",
                {
                    "status_code": request.env._("OAuth Authorization Error"),
                    "status_message": request.env._(
                        "An unexpected error occurred. Please contact your administrator."
                    ),
                },
            )

    @http.route(
        [_CALLBACK_PATH, _CALLBACK_PATH_LEGACY],
        type="http",
        auth="user",
        website=False,
        csrf=False,
    )
    def callback(self, code=None, state=None, error=None, error_description=None, **kw):
        try:
            if not request.env.user.has_group("credential.group_credential_admin"):
                _logger.warning(
                    "Unauthorized OAuth callback attempt by user %s",
                    request.env.user.login,
                )
                raise AccessDenied(
                    request.env._(
                        "You are not allowed to complete API credential authorization."
                    )
                )

            if error:
                error_msg = error_description or error
                _logger.warning("OAuth authorization denied: %s", error_msg)
                return self._redirect_with_error(
                    request.env._("Authorization Denied"),
                    request.env._("OAuth authorization was denied: %s") % error_msg,
                )

            if not state:
                raise UserError(request.env._("Missing state parameter"))

            try:
                state_envelope = json.loads(state)
            except json.JSONDecodeError, TypeError:
                raise UserError(request.env._("Invalid state parameter")) from None

            if not isinstance(state_envelope, dict):
                raise UserError(request.env._("Invalid state parameter"))

            state_data = state_envelope.get("payload")
            signature = state_envelope.get("sig")
            if not isinstance(state_data, dict) or not signature:
                raise AccessDenied(request.env._("Invalid state parameter"))

            expected_sig = self._sign_state(state_data)
            if not hmac.compare_digest(expected_sig, signature):
                raise AccessDenied(request.env._("State signature verification failed"))

            session_nonce = request.session.pop(_OAUTH_NONCE_SESSION_KEY, None)
            state_nonce = state_data.get("nonce")
            if (
                not session_nonce
                or not state_nonce
                or not hmac.compare_digest(str(session_nonce), str(state_nonce))
            ):
                raise AccessDenied(
                    request.env._("Invalid or missing OAuth state nonce")
                )

            credential_id = state_data.get("credential_id")
            if not credential_id:
                raise UserError(request.env._("Missing credential_id in state"))

            if state_data.get("db") != request.session.db:
                raise AccessDenied(request.env._("Invalid database in state parameter"))

            if state_data.get("uid") != request.env.uid:
                raise AccessDenied(request.env._("Invalid user in state parameter"))

            state_timestamp_str = state_data.get("timestamp")
            if not state_timestamp_str:
                raise AccessDenied(
                    request.env._("Missing timestamp in state parameter")
                )

            try:
                state_timestamp = fields.Datetime.from_string(state_timestamp_str)
            except ValueError, TypeError:
                raise AccessDenied(
                    request.env._("Invalid timestamp format in state parameter")
                ) from None

            now = fields.Datetime.now()
            age_seconds = (now - state_timestamp).total_seconds()
            max_age_seconds = 600

            if age_seconds > max_age_seconds:
                minutes = int(age_seconds / 60)
                raise AccessDenied(
                    request.env._(
                        "OAuth state expired (%d minutes old). "
                        "The authorization flow took too long. Please try again."
                    )
                    % minutes
                )

            if age_seconds < 0:
                raise AccessDenied(
                    request.env._(
                        "Invalid state timestamp (from future). "
                        "Check your server clock synchronization."
                    )
                )

            if not code:
                raise UserError(request.env._("Missing authorization code"))

            credential = (
                request.env["credential.credential"].sudo().browse(credential_id)
            )

            if not credential.exists():
                raise UserError(request.env._("Credential not found"))

            tokens = self._exchange_code_for_tokens(credential, code)

            vals = {
                "oauth_access_token": tokens.get("access_token"),
                "oauth_refresh_token": tokens.get("refresh_token"),
            }

            if tokens.get("expires_in"):
                date_expiration = fields.Datetime.now() + timedelta(
                    seconds=int(tokens["expires_in"])
                )
                vals["oauth_token_date_expiration"] = date_expiration

            credential.write(vals)

            _logger.info(
                "OAuth tokens obtained successfully: credential_id=%s, service=%s",
                credential.id,
                credential.endpoint_id.code,
            )

            return self._redirect_to_credential(credential_id)

        except AccessDenied as e:
            _logger.error("OAuth callback access denied: %s", e)
            return self._redirect_with_error(
                request.env._("Access Denied"),
                str(e),
            )

        except UserError as e:
            _logger.warning("OAuth callback user error: %s", e)
            return self._redirect_with_error(
                request.env._("OAuth Error"),
                str(e),
            )

        except Exception as e:
            _logger.exception("OAuth callback failed")
            return self._redirect_with_error(
                request.env._("OAuth Error"),
                request.env._("Token exchange failed: %s") % str(e),
            )

    def _get_redirect_uri(self):
        base_url = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("web.base.url", "")
            .rstrip("/")
        )
        if not base_url:
            raise UserError(
                request.env._(
                    "OAuth requires the 'web.base.url' system parameter to be "
                    "configured. Set it in Settings → Technical → System "
                    "Parameters before using OAuth.",
                ),
            )
        return f"{base_url}{_CALLBACK_PATH_REGISTERED_WITH_PROVIDERS}"

    def _get_oauth_state(self, credential_id):
        nonce = secrets.token_urlsafe(32)
        request.session[_OAUTH_NONCE_SESSION_KEY] = nonce

        payload = {
            "db": request.session.db,
            "credential_id": credential_id,
            "uid": request.env.uid,
            "timestamp": fields.Datetime.now().isoformat(),
            "nonce": nonce,
        }
        return {"payload": payload, "sig": self._sign_state(payload)}

    def _sign_state(self, payload):
        secret = (
            request.env["ir.config_parameter"].sudo().get_param("database.secret", "")
        )
        body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()

    def _exchange_code_for_tokens(self, credential, code):
        service = credential.endpoint_id

        redirect_uri = self._get_redirect_uri()

        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": credential._oauth_client_id(),
            "redirect_uri": redirect_uri,
        }

        client_secret = credential._use_secret_payload(
            "integration:oauth_exchange"
        ).get("oauth_client_secret")
        if client_secret:
            token_data["client_secret"] = client_secret

        try:
            with credential.env["ir.egress"].session(
                purpose="oauth_token", policy="private"
            ) as session:
                response = session.post(
                    service.oauth_token_endpoint,
                    data=token_data,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    timeout=30,
                )

            response.raise_for_status()

            tokens = response.json()

            if "access_token" not in tokens:
                raise UserError(request.env._("Missing access_token in response"))

            return tokens

        except requests.exceptions.HTTPError as e:
            error_details = self._parse_token_error(e.response)
            raise UserError(
                request.env._("Token exchange failed: %s") % error_details
            ) from e

        except requests.exceptions.RequestException as e:
            raise UserError(
                request.env._("Token exchange request failed: %s") % str(e)
            ) from e

        except (json.JSONDecodeError, ValueError) as e:
            raise UserError(
                request.env._("Invalid token response format: %s") % str(e)
            ) from e

    def _parse_token_error(self, response):
        try:
            error_data = response.json()
            error = error_data.get("error", "unknown_error")
            error_description = error_data.get("error_description", error)
            return f"{error}: {error_description}"
        except Exception:
            return f"HTTP {response.status_code}: {response.text[:200]}"

    def _redirect_to_credential(self, credential_id):
        url = f"/web#id={credential_id}&model=credential.credential&view_type=form"
        return werkzeug.utils.redirect(url, 303)

    def _redirect_with_error(self, title, message):
        return request.render(
            "http_routing.http_error",
            {
                "status_code": title,
                "status_message": message,
            },
        )
