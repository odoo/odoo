# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.addons.im_livechat.models.discuss_channel import is_livechat_channel
from odoo.addons.mail.tools.discuss import Store
from datetime import datetime, timedelta


class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    is_pending_chat_request = fields.Boolean(
        "When created from an operator, whether the channel is yet to be opened on the visitor side.",
    )
    livechat_visitor_id = fields.Many2one('website.visitor', string='Visitor', index='btree_not_null')

    def channel_pin(self, pinned=False):
        """ Override to clean an empty livechat channel.
         This is typically called when the operator send a chat request to a website.visitor
         but don't speak to them and closes the chatter.
         This allows operators to send the visitor a new chat request.
         If active empty livechat channel,
         delete discuss_channel as not useful to keep empty chat
         """
        super().channel_pin(pinned=pinned)
        if self.channel_type == "livechat" and not pinned and not self.message_ids:
            self.sudo().unlink()

    def _store_channel_fields(self, res: Store.FieldList):
        super()._store_channel_fields(res)
        res.one(
            "livechat_visitor_id",
            lambda res: (
                res.one("country_id", ["code"]),
                res.attr("display_name"),
                res.one("lang_id", ["name"]),
                res.one("partner_id", lambda partner_res: partner_res.one("country_id", ["code"])),
                res.one("website_id", ["name"]),
                res.from_method("_store_visitor_history_fields"),
            ),
            predicate=lambda channel: channel.channel_type == "livechat"
            and channel.livechat_visitor_id.has_access("read"),
        )
        # sudo: discuss.channel - visitor can access to the channel member history of
        # an accessible channel when computing requested_by_operator
        res.attr(
            "requested_by_operator",
            lambda channel: channel.create_uid
            in channel.sudo().livechat_agent_history_ids.partner_id.user_ids,
            predicate=is_livechat_channel,
        )

    def _get_visitor_leave_message(self, operator=False, cancel=False):
        if not cancel:
            if self.livechat_visitor_id.id:
                return _("Visitor #%(id)d left the conversation.", id=self.livechat_visitor_id.id)
            return _("Visitor left the conversation.")
        return _(
            "%(visitor)s started a conversation with %(operator)s.\nThe chat request has been cancelled",
            visitor=self.livechat_visitor_id.display_name or _("The visitor"),
            operator=operator or _("an operator"),
        )

    def _store_livechat_extra_fields(self, res: Store.FieldList):
        super()._store_livechat_extra_fields(res)
        res.one(
            "livechat_visitor_id",
            lambda res: res.many(
                "discuss_channel_ids",
                "_store_channel_fields",
                # Not batched by simplicity as it is always called on a single channel.
                value=lambda visitor: visitor.env["discuss.channel"].search(
                    [
                        ("channel_type", "=", "livechat"),
                        ("livechat_visitor_id", "=", visitor.id),
                        ("create_date", ">=", datetime.now() - timedelta(days=7)),
                    ],
                    limit=5,
                ),
            ),
            predicate=is_livechat_channel,
        )

    def message_post(self, **kwargs):
        """Override to mark the visitor as still connected.
        If the message sent is not from the operator (so if it's the visitor or
        odoobot sending closing chat notification, the visitor last action date is updated."""
        message = super().message_post(**kwargs)
        message_author_id = message.author_id
        visitor = self.livechat_visitor_id
        if len(self) == 1 and visitor and message_author_id != self.livechat_operator_id:
            # sudo: website.visitor: updating data of a specific visitor
            visitor.sudo()._update_visitor_last_visit()
        return message
