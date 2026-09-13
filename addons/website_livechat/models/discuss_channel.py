from datetime import datetime, timedelta

from odoo import _, fields, models

from odoo.addons.im_livechat.models.discuss_channel import is_livechat_channel
from odoo.addons.mail.tools.discuss import Store


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    is_pending_chat_request = fields.Boolean(
        string="When created from an operator, whether the channel is yet to be opened on the visitor side."
    )
    livechat_visitor_id = fields.Many2one(
        comodel_name="website.visitor",
        string="Visitor",
        index="btree_not_null",
    )

    def channel_pin(self, pinned=False):
        super().channel_pin(pinned=pinned)
        if self.channel_type == "livechat" and not pinned and not self.message_ids:
            self.sudo().unlink()

    def _to_store_defaults(self, target):
        return super()._to_store_defaults(target) + [
            Store.One(
                "livechat_visitor_id",
                [
                    Store.One("country_id", ["code"]),
                    "display_name",
                    "page_visit_history",
                    Store.One("lang_id", ["name"]),
                    Store.One("partner_id", [Store.One("country_id", ["code"])]),
                    Store.One("website_id", ["name"]),
                ],
                predicate=lambda channel: (
                    channel.channel_type == "livechat"
                    and self.livechat_visitor_id.has_access("read")
                ),
            ),
            Store.Attr(
                "requested_by_operator",
                lambda channel: (
                    channel.create_uid
                    in channel.sudo().livechat_agent_history_ids.partner_id.user_ids
                ),
                predicate=is_livechat_channel,
            ),
        ]

    def _get_visitor_history(self, visitor):
        return visitor._get_visitor_history()

    def _get_visitor_leave_message(self, operator=False, cancel=False):
        if not cancel:
            if self.livechat_visitor_id.id:
                return _(
                    "Visitor #%(id)d left the conversation.",
                    id=self.livechat_visitor_id.id,
                )
            return _("Visitor left the conversation.")
        return _(
            "%(visitor)s started a conversation with %(operator)s.\nThe chat request has been cancelled",
            visitor=self.livechat_visitor_id.display_name or _("The visitor"),
            operator=operator or _("an operator"),
        )

    def _get_livechat_session_fields_to_store(self):
        fields_to_store = super()._get_livechat_session_fields_to_store()
        domain = [
            ("channel_type", "=", "livechat"),
            ("livechat_visitor_id", "=", self.livechat_visitor_id.id),
            (
                "create_date",
                ">=",
                fields.Datetime.to_string(datetime.now() - timedelta(days=7)),
            ),
        ]
        channels = self.env["discuss.channel"].search(domain, limit=5)
        fields_to_store.append(
            Store.One(
                "livechat_visitor_id",
                [
                    Store.Many(
                        "discuss_channel_ids",
                        value=channels,
                    ),
                ],
                predicate=is_livechat_channel,
            ),
        )
        return fields_to_store

    def message_post(self, **kwargs):
        message = super().message_post(**kwargs)
        message_author_id = message.author_id
        visitor = self.livechat_visitor_id
        if (
            len(self) == 1
            and visitor
            and message_author_id != self.livechat_operator_id
        ):
            visitor.sudo()._update_visitor_last_visit()
        return message
