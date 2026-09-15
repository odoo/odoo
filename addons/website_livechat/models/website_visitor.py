from odoo import Command, _, api, fields, models
from odoo.db.schema import column_exists, create_column
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools import get_lang

from odoo.addons.mail.tools.discuss import Store

_debug = DebugLog(__name__)


class WebsiteVisitor(models.Model):
    _inherit = "website.visitor"

    livechat_operator_id = fields.Many2one(
        comodel_name="res.partner",
        string="Speaking with",
        compute="_compute_livechat_operator_id",
        store=True,
        index="btree_not_null",
    )
    livechat_operator_name = fields.Char(
        related="livechat_operator_id.name",
        string="Operator Name",
    )
    discuss_channel_ids = fields.One2many(
        comodel_name="discuss.channel",
        inverse_name="livechat_visitor_id",
        string="Visitor's livechat channels",
        readonly=True,
    )
    session_count = fields.Integer(
        string="# Sessions",
        compute="_compute_session_count",
    )

    def _auto_init(self):
        if not column_exists(self.env.cr, "website_visitor", "livechat_operator_id"):
            create_column(
                self.env.cr, "website_visitor", "livechat_operator_id", "int4"
            )
        return super()._auto_init()

    @api.depends(
        "discuss_channel_ids.livechat_end_dt",
        "discuss_channel_ids.livechat_operator_id",
    )
    def _compute_livechat_operator_id(self):
        results = self.env["discuss.channel"].search_read(
            [("livechat_visitor_id", "in", self.ids), ("livechat_end_dt", "=", False)],
            ["livechat_visitor_id", "livechat_operator_id"],
        )
        visitor_operator_map = {
            int(result["livechat_visitor_id"][0]): int(
                result["livechat_operator_id"][0]
            )
            for result in results
        }
        for visitor in self:
            visitor.livechat_operator_id = visitor_operator_map.get(visitor.id, False)

    @api.depends("discuss_channel_ids")
    def _compute_session_count(self):
        sessions = self.env["discuss.channel"].search(
            [("livechat_visitor_id", "in", self.ids)]
        )
        session_count = dict.fromkeys(self.ids, 0)
        for session in sessions.filtered(lambda c: c.message_ids):
            session_count[session.livechat_visitor_id.id] += 1
        for visitor in self:
            visitor.session_count = session_count.get(visitor.id, 0)

    def action_send_chat_request(self):
        unavailable_visitors_count = self.env["discuss.channel"].search_count(
            [("livechat_visitor_id", "in", self.ids), ("livechat_end_dt", "=", False)]
        )
        if unavailable_visitors_count:
            _debug.logic(
                "visitor_unlink_refused",
                reason="live_chat_open",
                sessions=unavailable_visitors_count,
            )
            raise UserError(
                _(
                    "Recipients are not available. Please refresh the page to get latest visitors status."
                )
            )
        for website in self.mapped("website_id"):
            if not website.channel_id:
                _debug.logic(
                    "livechat_refused", reason="no_channel", website=website.id
                )
                raise UserError(
                    _(
                        "No Livechat Channel allows you to send a chat request for website %s.",
                        website.name,
                    )
                )
        self.website_id.channel_id.write({"user_ids": [(4, self.env.user.id)]})
        discuss_channel_vals_list = []
        for visitor in self:
            operator = self.env.user
            country = visitor.country_id
            visitor_name = (
                "Visitor #%d (%s)" % (visitor.id, country.name)
                if country
                else f"Visitor #{visitor.id}"
            )
            members_to_add = [Command.link(operator.partner_id.id)]
            if visitor.partner_id:
                members_to_add.append(Command.link(visitor.partner_id.id))
            discuss_channel_vals_list.append(
                {
                    "channel_partner_ids": members_to_add,
                    "is_pending_chat_request": True,
                    "livechat_channel_id": visitor.website_id.channel_id.id,
                    "livechat_operator_id": self.env.user.partner_id.id,
                    "channel_type": "livechat",
                    "country_id": country.id,
                    "name": ", ".join(
                        [
                            visitor_name,
                            operator.livechat_username or operator.name,
                        ]
                    ),
                    "livechat_visitor_id": visitor.id,
                }
            )
        discuss_channels = self.env["discuss.channel"].create(discuss_channel_vals_list)
        for channel in discuss_channels:
            if not channel.livechat_visitor_id.partner_id:
                guest = (
                    self.env["mail.guest"]
                    .sudo()
                    .create(
                        {
                            "country_id": country.id,
                            "lang": get_lang(channel.env).code,
                            "name": _("Visitor #%d", channel.livechat_visitor_id.id),
                            "timezone": visitor.timezone,
                        }
                    )
                )
                channel._add_members(guests=guest, post_joined_message=False)
        Store(bus_channel=self.env.user).add(
            discuss_channels,
            extra_fields={"open_chat_window": True},
        ).bus_send()

    def _merge_visitor(self, target):
        target.discuss_channel_ids |= self.discuss_channel_ids
        self.discuss_channel_ids.channel_partner_ids = [
            (3, self.env.ref("base.public_partner").id),
            (4, target.partner_id.id),
        ]
        return super()._merge_visitor(target)

    def _upsert_visitor(self, access_token, force_track_values=None, **visitor_values):
        visitor_id, created = super()._upsert_visitor(
            access_token, force_track_values=force_track_values, **visitor_values
        )
        if created:
            visitor_sudo = self.sudo().browse(visitor_id)
            if guest := self.env["mail.guest"]._get_guest_from_context():
                guest_livechats = guest.sudo().channel_ids.filtered(
                    lambda c: c.channel_type == "livechat"
                )
                guest_livechats.livechat_visitor_id = visitor_sudo.id
                guest_livechats.country_id = visitor_sudo.country_id
        return visitor_id, created

    def _field_store_repr(self, field_spec):
        if field_spec == "page_visit_history":
            return [
                Store.Attr(
                    "page_visit_history",
                    lambda visitor: visitor.sudo()._get_visitor_history(),
                ),
            ]
        return [field_spec]

    def _get_visitor_history(self):
        self.check_singleton()
        recent_history = self.env["website.track"].search(
            [("page_id", "!=", False), ("visitor_id", "=", self.id)], limit=3
        )
        return [
            (visit.page_id.name, fields.Datetime.to_string(visit.visit_datetime))
            for visit in reversed(recent_history)
        ]
