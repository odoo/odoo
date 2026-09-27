# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _auth_method_force_guest(cls, routing: dict):
        """Identify the caller as the guest matching the ``guest_token`` parameter.

        :raise NotFound: if no guest matches the token.
        """
        cls._auth_method_force_guest_optional(routing)
        if not request.env["mail.guest"]._get_guest_from_context():
            raise NotFound()

    @classmethod
    def _auth_method_force_guest_optional(cls, routing: dict):
        """Same as ``force_guest``, for the routes a visitor reaches before
        having a guest, such as the creation of the live chat session."""
        cls._auth_method_none(routing)
        request.session.can_save = False  # the uid dropped below must not be saved
        request.session.uid = None
        cls._auth_method_public(routing)
        # Cookies cannot be trusted here: odoo subdomains are same-site, so a
        # call from A.odoo to B.odoo carries B's cookie. Trust only the token.
        request.cookies = {}
        if guest := request.env["mail.guest"]._get_guest_from_token(cls._get_guest_token(routing)):
            request.update_context(guest=guest)

    @classmethod
    def _get_guest_token(cls, routing: dict):
        """Read the ``guest_token`` parameter, which the dispatcher has not
        parsed into ``request.params`` yet when authentication runs."""
        if "json" not in routing["type"]:
            return request.get_http_params().get("guest_token")
        try:
            body = request.get_json_data()
        except ValueError:
            body = None
        if not isinstance(body, dict):
            return None  # the dispatcher rejects a body it cannot read
        # jsonrpc nests the parameters, json2 sends them at the top level
        params = body.get("params") if routing["type"] == "jsonrpc" else body
        return params.get("guest_token") if isinstance(params, dict) else None
