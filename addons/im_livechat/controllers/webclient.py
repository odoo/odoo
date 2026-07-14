# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route
from odoo.addons.mail.controllers.webclient import WebclientController
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context


class WebClient(WebclientController):
    @route("/web/tests/livechat", type="http", auth="user")
    def test_external_livechat(self, **kwargs):
        return request.render(
            "im_livechat.unit_embed_suite",
            {
                "server_url": request.env["ir.config_parameter"].get_base_url(),
                "session_info": {"view_info": request.env["ir.ui.view"].get_view_info()},
            },
        )

    def _process_request_for_internal_user(self, store, **kwargs):
        super()._process_request_for_internal_user(store, **kwargs)
        if kwargs.get("livechat_channels"):
            store.add(
                request.env["im_livechat.channel"].search([]), fields=["are_you_inside", "name"]
            )
