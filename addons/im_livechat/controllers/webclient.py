# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route
from odoo.addons.mail.controllers.webclient import WebclientController
from odoo.addons.mail.tools.discuss import Store


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

    @classmethod
    def _process_request_for_internal_user(self, store: Store, name, params):
        super()._process_request_for_internal_user(store, name, params)
        if name == "im_livechat.channel":
            store.add(request.env["im_livechat.channel"].search([]), ["are_you_inside", "name"])

    @classmethod
    def _process_request_for_all(self, store: Store, name, params):
        super()._process_request_for_all(store, name, params)
        if name == "init_livechat":
            partner, guest = request.env["res.partner"]._get_current_persona()
            if partner or guest:
                store.add_global_values(store_self=Store.One(partner or guest))
            # sudo - im_livechat.channel: allow access to live chat channel to
            # check if operators are available.
            channel = request.env["im_livechat.channel"].sudo().search([("id", "=", params)])
            if not channel:
                return
            country_id = (
                # sudo - res.country: accessing user country is allowed.
                request.env["res.country"].sudo().search([("code", "=", code)])
                if (code := request.geoip.country_code)
                else None
            )
            url = request.httprequest.headers.get("Referer")
            if (
                # sudo - im_livechat.channel.rule: getting channel's rule is allowed.
                matching_rule := request.env["im_livechat.channel.rule"]
                .sudo()
                .match_rule(params, url, country_id)
            ):
                matching_rule = matching_rule.with_context(
                    lang=request.env["chatbot.script"]._get_chatbot_language()
                )
                store.add_global_values(livechat_rule=Store.One(matching_rule))
            store.add_global_values(
                livechat_available=bool(matching_rule.chatbot_script_id
                or channel.available_operator_ids)
            )
