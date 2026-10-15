# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields
from odoo.addons.mail.tools.discuss import Store


class MailMessage(models.Model):
    _inherit = "mail.message"

    call_history_ids = fields.One2many("discuss.call.history", "start_call_message_id")
    channel_id = fields.Many2one("discuss.channel", compute="_compute_channel_id")

    @api.depends("model", "res_id")
    def _compute_channel_id(self):
        for message in self:
            if message.model == "discuss.channel" and message.res_id:
                message.channel_id = self.env["discuss.channel"].browse(message.res_id)
            else:
                message.channel_id = False

    def _get_with_access(self, mode="read", **kwargs):
        """Override to allow users/guests to edit their own messages in channels."""
        res = super()._get_with_access(mode=mode, **kwargs)
        if not res and mode == "write" and self.channel_id and self.is_current_user_or_guest_author:
            return self
        return res

    def _store_message_fields(self, res: Store.FieldList, **kwargs):
        super()._store_message_fields(res, **kwargs)
        res.many(
            "call_history_ids",
            ["duration_hour", "end_dt"],
            predicate=lambda m: m.body and 'data-oe-type="call"' in m.body,
        )

    def _store_extra_fields(self, res: Store.FieldList, *, format_reply):
        super()._store_extra_fields(res, format_reply=format_reply)
        if format_reply:
            channel_ids = self.filtered(lambda m: m.model == "discuss.channel").mapped("res_id")
            # sudo: discuss.channel - can read the type of the channel of an accessible message
            channels = self.env["discuss.channel"].sudo().browse(channel_ids)
            top_channel_ids = channels.filtered(
                lambda channel: channel.channel_type == "channel" and not channel.parent_channel_id,
            ).ids
            if channel_messages := self.filtered(
                lambda message: (
                    message.model == "discuss.channel" and message.res_id in top_channel_ids
                ),
            ):
                sub_channels = self.env["discuss.channel"].search_fetch(
                    [("from_message_id", "in", channel_messages.ids)],
                    ["from_message_id"],
                )
                sub_channel_by_message = {
                    channel.from_message_id: channel for channel in sub_channels
                }
                res.one(
                    "linkedSubChannel",
                    [],
                    predicate=lambda message: message in channel_messages,
                    value=lambda message: sub_channel_by_message.get(
                        message,
                        self.env["discuss.channel"],
                    ),
                )
            # sudo: mail.message: access to parent is allowed
            res.one(
                "parent_id",
                "_store_message_fields",
                fields_params={"format_reply": False},
                predicate=lambda m: m.channel_id,
                sudo=True,
            )

    def _bus_channels(self):
        self.ensure_one()
        if self.channel_id:
            return self.channel_id._bus_channels()
        guest = self.env["mail.guest"]._get_guest_from_context()
        if self.env.user._is_public() and guest:
            return guest._bus_channels()
        return super()._bus_channels()
