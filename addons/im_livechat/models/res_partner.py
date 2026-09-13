import ast

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.fields import Domain
from odoo.tools.misc import OrderedSet

from odoo.addons.mail.tools.discuss import Store


class ResPartner(models.Model):
    _inherit = "res.partner"

    user_livechat_username = fields.Char(compute="_compute_user_livechat_username")
    chatbot_script_ids = fields.One2many(
        comodel_name="chatbot.script",
        inverse_name="operator_partner_id",
    )
    livechat_channel_count = fields.Integer(compute="_compute_livechat_channel_count")

    def _search_for_channel_invite_to_store(self, store: Store, channel):
        super()._search_for_channel_invite_to_store(store, channel)
        if channel.channel_type != "livechat" or not self:
            return
        lang_name_by_code = dict(self.env["res.lang"].get_installed())
        invite_by_self_count_by_partner = dict(
            self.env["discuss.channel.member"]._read_group(
                [["create_uid", "=", self.env.user.id], ["partner_id", "in", self.ids]],
                groupby=["partner_id"],
                aggregates=["__count"],
            )
        )
        active_livechat_partners = (
            self.env["im_livechat.channel"].search([]).available_operator_ids.partner_id
        )
        for partner in self:
            languages = list(
                OrderedSet(
                    [
                        lang_name_by_code[partner.lang],
                        *partner.user_ids.sudo().livechat_lang_ids.mapped("name"),
                    ]
                )
            )
            store.add(
                partner,
                {
                    "invite_by_self_count": invite_by_self_count_by_partner.get(
                        partner, 0
                    ),
                    "is_available": partner in active_livechat_partners,
                    "lang_name": languages[0],
                    "livechat_expertise": partner.user_ids.sudo().livechat_expertise_ids.mapped(
                        "name"
                    ),
                    "livechat_languages": languages[1:],
                    "user_livechat_username": partner.sudo().user_livechat_username,
                },
                extra_fields=[Store.Attr("is_in_call", sudo=True)],
            )

    @api.depends("user_ids.livechat_username")
    def _compute_user_livechat_username(self):
        for partner in self:
            partner.user_livechat_username = next(
                iter(partner.user_ids.mapped("livechat_username")), False
            )

    def _compute_livechat_channel_count(self):
        livechat_count_by_partner = dict(
            self.env["im_livechat.channel.member.history"]._read_group(
                domain=[
                    ("partner_id", "in", self.ids),
                    ("livechat_member_type", "=", "visitor"),
                ],
                groupby=["partner_id"],
                aggregates=["channel_id:count_distinct"],
            )
        )
        for partner in self:
            partner.livechat_channel_count = livechat_count_by_partner.get(partner, 0)

    def _get_fields_store_livechat_username(self):
        return [
            Store.Attr("name", predicate=lambda p: not p.user_livechat_username),
            "user_livechat_username",
        ]

    def _bus_send_history_message(self, channel, page_history):
        message_body = _("No history found")
        if page_history:
            message_body = Markup("<ul>%s</ul>") % (
                Markup("").join(
                    Markup('<li><a href="%(page)s" target="_blank">%(page)s</a></li>')
                    % {"page": page}
                    for page in page_history
                )
            )
        self._bus_send_transient_message(channel, message_body)

    @api.depends_context("im_livechat_hide_partner_company")
    def _compute_display_name(self):
        if not self.env.context.get("im_livechat_hide_partner_company"):
            super()._compute_display_name()
            return
        portal_partners = self.filtered("partner_share")
        super(ResPartner, portal_partners)._compute_display_name()
        for partner in self - portal_partners:
            partner.display_name = partner.name

    def action_view_livechat_sessions(self):
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "im_livechat.discuss_channel_action"
        )
        livechat_channel_ids = (
            self.env["im_livechat.channel.member.history"]
            .search(
                [
                    ("partner_id", "=", self.id),
                    ("livechat_member_type", "=", "visitor"),
                ]
            )
            .channel_id.ids
        )
        action["domain"] = Domain.AND(
            [ast.literal_eval(action["domain"]), [("id", "in", livechat_channel_ids)]]
        )
        return action
