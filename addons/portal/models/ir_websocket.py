# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import models
from odoo.addons.portal.models.mail_thread import _add_portal_partner_to_context


class IrWebsocket(models.AbstractModel):
    _inherit = "ir.websocket"

    def _build_bus_channel_list(self, channels):
        channels = list(channels)
        for channel in list(channels):
            if isinstance(channel, str) and channel.startswith("portal.channel_"):
                channels.remove(channel)
                params_map = json.loads(channel.split("portal.channel_")[1])
                _add_portal_partner_to_context(self.env, params_map)
                if portal_partner := self.env["res.partner"]._get_portal_partner_from_context():
                    channels.append(portal_partner)
        return super()._build_bus_channel_list(channels)
