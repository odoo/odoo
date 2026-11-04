# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons.mail.tools.discuss import Store


class MailMessage(models.Model):
    _inherit = "mail.message"

    def _extras_to_store(self, store: Store, format_reply):
        super()._extras_to_store(store, format_reply=format_reply)
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
                for message in channel_messages:
                    sub_channel = sub_channel_by_message.get(message, self.env["discuss.channel"])
                    store.add(
                        message,
                        {"linkedSubChannel": Store.one(sub_channel, as_thread=True, only_id=True)},
                    )
            # sudo: mail.message: access to parent is allowed
            for message in self.sudo().filtered(lambda message: message.model == "discuss.channel"):
                store.add(
                    message, {"parentMessage": Store.one(message.parent_id, format_reply=False)}
                )

    def _bus_channel(self):
        self.ensure_one()
        if self.model == "discuss.channel" and self.res_id:
            return self.env["discuss.channel"].browse(self.res_id)._bus_channel()
        guest = self.env["mail.guest"]._get_guest_from_context()
        if self.env.user._is_public() and guest:
            return guest._bus_channel()
        return super()._bus_channel()
