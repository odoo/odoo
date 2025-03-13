# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.addons.mail.tools.discuss import Store


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
        if self.livechat_active and not self.message_ids:
            self.sudo().unlink()

    def _field_store_repr(self, field_name):
        if field_name == "visitor":
            return [
                Store.Attr(
                    "visitor",
                    lambda channel: Store.One(
                        channel.livechat_visitor_id,
                        [
                            "country",
                            "history",
                            "is_connected",
                            "lang_name",
                            "name",
                            "partner_id",
                            "website_name",
                        ],
                    ),
                    predicate=lambda channel: channel.livechat_visitor_id
                    and self.livechat_visitor_id.has_access("read"),
                ),
            ]
        if field_name == "requested_by_operator":
            return [
                Store.Attr(
                    "requested_by_operator",
                    lambda channel: channel.create_uid in channel.livechat_operator_id.user_ids,
                    predicate=lambda channel: channel.livechat_visitor_id,
                ),
            ]
        return super()._field_store_repr(field_name)

    def _to_store_defaults(self, for_current_user=True):
        return super()._to_store_defaults(for_current_user=for_current_user) + [
            "requested_by_operator",
            "visitor",
        ]

    def _get_visitor_history(self, visitor):
        return visitor._get_visitor_history()

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
