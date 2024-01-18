# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import models
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context


class IrWebsocket(models.AbstractModel):
    _inherit = "ir.websocket"

    def _get_im_status(self, data):
        im_status = super()._get_im_status(data)
        if "mail.guest" in data:
            # sudo: mail.guest - necessary to read im_status from other guests, information is not considered sensitive
            im_status["Persona"] += [{**g, 'type': "guest"} for g in (
                self.env["mail.guest"]
                .sudo()
                .with_context(active_test=False)
                .search_read([("id", "in", data["mail.guest"])], ["im_status"])
            )]
        return im_status

    @add_guest_to_context
    def _build_bus_channel_list(self, channels):
        channels = list(channels)  # do not alter original list
        discuss_channel_ids = list()
        for channel in list(channels):
            if isinstance(channel, str) and channel.startswith("mail.guest_"):
                channels.remove(channel)
                guest = self.env["mail.guest"]._get_guest_from_token(channel.split("_")[1])
                if guest:
                    self = self.with_context(guest=guest)
            if isinstance(channel, str):
                match = re.findall(r'discuss\.channel_(\d+)', channel)
                if match:
                    channels.remove(channel)
                    discuss_channel_ids.append(int(match[0]))
        guest = self.env["mail.guest"]._get_guest_from_context()
        if guest:
            channels.append(guest)
        domain = ["|", ("is_member", "=", True), ("id", "in", discuss_channel_ids)]
        channels.extend(self.env["discuss.channel"].search(domain))
        return super()._build_bus_channel_list(channels)

    @add_guest_to_context
    def _update_bus_presence(self, inactivity_period, im_status_ids_by_model):
        super()._update_bus_presence(inactivity_period, im_status_ids_by_model)
        if not self.env.user or self.env.user._is_public():
            guest = self.env["mail.guest"]._get_guest_from_context()
            if not guest:
                return
            # sudo: bus.presence - guests currently need sudo to write their own presence
            self.env["bus.presence"].sudo().update_presence(
                inactivity_period,
                identity_field="guest_id",
                identity_value=guest.id,
            )
