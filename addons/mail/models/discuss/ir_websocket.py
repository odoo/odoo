# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import models
from odoo.fields import Domain


class IrWebsocket(models.AbstractModel):
    """Override to handle discuss specific features (channel in particular)."""

    _inherit = "ir.websocket"

    def _filter_accessible_presences(self, partners, guests):
        allowed_partners, allowed_guests = super()._filter_accessible_presences(partners, guests)
        if self.env.user and self.env.user._is_internal():
            return allowed_partners, allowed_guests
        current_partner, current_guest = self.env["res.partner"]._get_current_persona()
        # sudo - mail.guest: guest can access their own channels.
        channels_domain = Domain(
            "channel_ids", "in", (current_partner or current_guest.sudo()).channel_ids.ids
        )
        # sudo - res.partner: allow access when sharing a common channel.
        allowed_partners |= (
            self.env["res.partner"]
            .with_context(active_test=False)
            .sudo()
            .search(Domain("id", "in", partners.ids) & channels_domain)
        )
        # sudo - mail.guest: allow access when sharing a common channel.
        allowed_guests |= (
            self.env["mail.guest"].sudo().search(Domain("id", "in", guests.ids) & channels_domain)
        )
        return allowed_partners, allowed_guests

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
        all_user_channels = self.env["discuss.channel"].search(domain)
        member_specific_channels = [(c, "members") for c in all_user_channels if c.id not in discuss_channel_ids]
        channels.extend([*all_user_channels, *member_specific_channels])
        return super()._build_bus_channel_list(channels)
