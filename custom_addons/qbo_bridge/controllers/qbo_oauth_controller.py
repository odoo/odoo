"""HTTP controller that handles the OAuth2 redirect callback from Intuit.

Intuit redirects the user's browser to <base_url>/qbo/callback?code=...&state=...
after authorization. This controller exchanges the code for tokens and
redirects back to the QBO Realms list.
"""
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class QboOAuthController(http.Controller):

    def _realm_list_url(self):
        action = request.env.ref("qbo_bridge.action_qbo_realm", raise_if_not_found=False)
        if not action:
            return "/web"
        return f"/web#action={action.id}&model=qbo.realm&view_type=list"

    def _realm_form_url(self, realm):
        action = request.env.ref("qbo_bridge.action_qbo_realm", raise_if_not_found=False)
        if not action:
            return "/web"
        return (
            f"/web#action={action.id}&id={realm.id}"
            f"&model=qbo.realm&view_type=form"
        )

    @http.route("/qbo/callback", type="http", auth="user", methods=["GET"])
    def oauth_callback(self, **kwargs):
        code = kwargs.get("code")
        state = kwargs.get("state")   # We encode the realm record ID as state
        error = kwargs.get("error")

        if error:
            _logger.warning("QBO OAuth error: %s — %s", error, kwargs.get("error_description"))
            return request.redirect(
                self._realm_list_url(),
            )

        if not code or not state:
            return request.redirect(self._realm_list_url())

        try:
            realm_id = int(state)
        except (ValueError, TypeError):
            _logger.error("QBO callback: invalid state value %r", state)
            return request.redirect(self._realm_list_url())

        realm = request.env["qbo.realm"].browse(realm_id)
        if not realm.exists():
            _logger.error("QBO callback: realm ID %s not found", realm_id)
            return request.redirect(self._realm_list_url())

        try:
            realm.action_exchange_code(code)
            _logger.info("QBO realm %s authorised successfully", realm.name)
        except Exception:
            _logger.exception("QBO token exchange failed for realm %s", realm.name)

        return request.redirect(self._realm_form_url(realm))
