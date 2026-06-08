# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route

from odoo.addons.mail.controllers.webclient import WebclientController
from odoo.addons.mail.tools.discuss import Store
from odoo.addons.mail.tools.store_handler import store_handler


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

    @store_handler("im_livechat.channel")
    def store_im_livechat_channel(self, store: Store):
        store.add(request.env["im_livechat.channel"].search([]), ["are_you_inside", "name"])

    @store_handler("/im_livechat/looking_for_help")
    def store_im_livechat_looking_for_help(self, store: Store):
        chats_looking_for_help = request.env["discuss.channel"].search(
            [("livechat_status", "=", "need_help")],
            order="livechat_looking_for_help_since_dt ASC, id ASC",
            limit=100,
        )
        request.update_context(channels=request.env.context["channels"] | chats_looking_for_help)

    @store_handler("/im_livechat/session/data")
    def store_im_livechat_session_data(self, store: Store, channel_id):
        if not channel_id:
            return
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        store.add(channel, "_store_livechat_extra_fields")

    @store_handler("/im_livechat/fetch_self_expertise")
    def store_im_livechat_fetch_self_expertise(self, store: Store):
        store.add(request.env.user, lambda res: res.many("livechat_expertise_ids", ["name"]))

    @store_handler("init_livechat", audience="everyone", readonly=False)
    def store_init_livechat(self, store: Store, livechat_channel_id=None):
        store.add_global_values(
            lambda res: self._store_init_livechat_fields(res, livechat_channel_id),
        )

    @classmethod
    def _store_init_livechat_fields(cls, res: Store.FieldList, params):
        user, guest = request.env["res.users"]._get_current_persona()
        if user:
            res.one(
                "self_user",
                lambda res: res.one(
                    "partner_id",
                    lambda res: (
                        res.from_method("_store_partner_fields"),
                        res.attr("email"),
                    ),
                ),
                value=user,
            )
        if guest:
            res.one(
                "self_guest",
                lambda res: (
                    res.from_method("_store_avatar_fields"),
                    res.from_method("_store_im_status_fields"),
                ),
                value=guest,
            )
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
            res.one("livechat_rule", "_store_channel_rule_fields", value=matching_rule)
        res.attr(
            "livechat_available",
            matching_rule.action != "hide_button"
            and bool(matching_rule._is_bot_configured() or channel.available_operator_ids),
        )
        res.attr(
            "can_download_transcript",
            bool(request.env.ref("im_livechat.action_report_livechat_conversation", False)),
        )
