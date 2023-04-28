# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import populate


class ChannelMember(models.Model):
    _inherit = "discuss.channel.member"
    _populate_dependencies = ["res.partner", "discuss.channel"]
    _populate_sizes = {"small": 10, "medium": 100, "large": 1000}

    def _populate_factories(self):
        partner_ids = self.env.registry.populated_models["res.partner"]
        channel_ids = self.env.registry.populated_models["discuss.channel"]
        return [
            ("partner_id", populate.randomize(partner_ids)),
            ("channel_id", populate.randomize(channel_ids)),
        ]

    def _populate(self, size):
        channel_ids = self.env.registry.populated_models["discuss.channel"]
        for channel_id in channel_ids:
            self.env["discuss.channel.member"].create(
                {"partner_id": self.env.ref("base.user_admin").partner_id.id, "channel_id": channel_id}
            )
        return super()._populate(size)
