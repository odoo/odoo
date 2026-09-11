
from odoo import models

from .mail_channel import ODOO_CHANNEL_TYPES


class Partners(models.Model):
    _inherit = "res.partner"

    def _get_channels_as_member(self):
        channels = super()._get_channels_as_member()
        channels |= self.env["mail.channel"].search(
            [
                ("channel_type", "not in", ODOO_CHANNEL_TYPES),
            ]
        )
        return channels
