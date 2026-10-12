# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import http
from odoo.http import request

from odoo.addons.mail.tools.discuss import Store, mail_route
from odoo.addons.mail.tools.store_handler import store_handler_registry


class StoreController(http.Controller):
    """Base controller exposing the `/mail/store` route and store dispatch.

    Extend this class and decorate your own methods with `@store_handler` to add store handlers."""

    @mail_route("/mail/store", methods=["POST"], type="jsonrpc", auth="public", readonly=lambda self, *_: self._is_mail_fetch_readonly())
    def mail_store(self, fetch_params, context=None):
        """Returns store data for the given fetch_params."""
        context_user_id = context.get("uid") if context else None
        store = Store()
        if context_user_id and (not self.env.user or context_user_id != self.env.user.id):
            # The user has been logged out in the meantime
            return store

        if context:
            request.update_context(**context)
        self._process_request_loop(store, fetch_params)
        return store

    def _is_mail_fetch_readonly(self):
        if request.httprequest.method == "OPTIONS":
            # CORS preflight request has an empty body, nothing to parse
            return True
        fetch_params = request.get_json_data().get("params", {}).get("fetch_params", [])
        return store_handler_registry.is_fetch_readonly(fetch_params)

    def _process_request_loop(self, store: Store, fetch_params):
        store_handler_registry.execute_for_user(self, store, fetch_params)
