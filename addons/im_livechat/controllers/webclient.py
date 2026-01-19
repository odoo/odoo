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
        if name == "/im_livechat/looking_for_help":
            chats_looking_for_help = request.env["discuss.channel"].search(
                [("livechat_status", "=", "need_help")], order="id ASC", limit=100
            )
            request.update_context(
                channels=request.env.context["channels"] | chats_looking_for_help
            )
        if name == "/im_livechat/session/data":
            channel_id = params.get("channel_id")
            if not channel_id:
                return
            channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
            if not channel:
                return
            fields_to_store = channel._get_livechat_session_fields_to_store()
            store.add(channel, fields=fields_to_store)
        if name == "/im_livechat/fetch_self_expertise":
            store.add(request.env.user, Store.Many("livechat_expertise_ids", ["name"]))

    @classmethod
    def _process_request_for_all(self, store: Store, name, params):
        super()._process_request_for_all(store, name, params)
        if name == "init_livechat":
            partner, guest = request.env["res.partner"]._get_current_persona()
            if partner:
                store.add_global_values(self_partner=Store.One(partner, extra_fields="email"))
            if guest:
                store.add_global_values(self_guest=Store.One(guest))
            # sudo - im_livechat.channel: allow access to live chat channel to
            # check if operators are available.
            channel = request.env["im_livechat.channel"].sudo().search([("id", "=", params)])
            if not channel:
                return
            country_id = (
                # sudo - res.country: accessing user country is allowed.
                request.env["res.country"].sudo().search([("code", "=", code)]).id
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
                    lang=request.env["chatbot.script"]._get_chatbot_language(),
                )
                store.add_global_values(livechat_rule=Store.One(matching_rule))
            store.add_global_values(
                livechat_available=matching_rule.action != "hide_button"
                and bool(matching_rule._is_bot_configured() or channel.available_operator_ids),
                can_download_transcript=bool(
                    request.env.ref("im_livechat.action_report_livechat_conversation", False),
                ),
            )
