# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request
from odoo.tools.misc import verify_limited_field_access_token

from odoo.addons.mail.controllers.webclient import WebclientController
from odoo.addons.mail.tools.discuss import Store


class ResPartnerWebclientController(WebclientController):
    """Override to add res.partner specific features."""

    @classmethod
    def _process_request_loop(self, store: Store, fetch_params):
        """Override to add res.partner specific features."""
        # aggregate of channels to return, to batch them in a single query when all the fetch params
        # have been processed
        request.update_context(partners=request.env["res.partner"], partners_no_fields=False)
        super()._process_request_loop(store, fetch_params)
        partners = request.env.context["partners"]
        if partners and request.env.context["partners_no_fields"]:
            store.add(partners, fields=["id"])

    @classmethod
    def _process_request_for_all(self, store: Store, name, params):
        """Override to return channel as member and last messages."""
        super()._process_request_for_all(store, name, params)
        if name == "partners_no_fields":
            partners = request.env["res.partner"].browse(params["partner_ids"])
            partners.filtered(
                lambda p: (
                    (not request.env.user.share and p.has_access("read"))
                    or (
                        verify_limited_field_access_token(
                            p,
                            "id",
                            params.get("partner_ids_mention_token", {}).get(str(p.id), ""),
                            scope="mail.message_mention",
                        )
                    )
                )
            )
            request.update_context(partners=partners, partners_no_fields=True)
