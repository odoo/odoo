# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import models
from odoo.tools.misc import verify_limited_field_access_token


class IrWebsocket(models.AbstractModel):
    """Override to handle discuss specific features (channel in particular)."""

    _inherit = "ir.websocket"

    def _build_bus_channel_list(self, channels):
        channels = list(channels)  # do not alter original list
        discuss_channel_ids = list()
        discuss_category_id_token_map = {}
        for channel in list(channels):
            if isinstance(channel, str) and channel.startswith("mail.guest_"):
                channels.remove(channel)
                guest = self.env["mail.guest"]._get_guest_from_token(channel.split("_")[1])
                if guest:
                    self = self.with_context(guest=guest)
            if isinstance(channel, str) and channel.startswith("discuss.category_"):
                channels.remove(channel)
                split_str = channel.rsplit("_", 2)
                cid, token = int(split_str[1]), split_str[2] if len(split_str) == 3 else None
                if token or not discuss_category_id_token_map.get(cid):
                    discuss_category_id_token_map[cid] = token
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
        internal_specific_channels = [
            (c, "internal_users")
            for c in all_user_channels
            if not self.env.user.share
        ]
        channels.extend([*all_user_channels, *internal_specific_channels])
        discuss_categories = self.env["discuss.category"].browse(discuss_category_id_token_map.keys())
        allowed_discuss_categories = discuss_categories.filtered(
            lambda category: verify_limited_field_access_token(
                category, "id", discuss_category_id_token_map[category.id], scope="bus.channel"
            )
            or category.has_access("read"),
        )
        channels.extend(allowed_discuss_categories)
        return super()._build_bus_channel_list(channels)
