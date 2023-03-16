# -*- coding: utf-8 -*-
from odoo import models
from odoo.tools import populate

class ChannelMember(models.Model):
    _inherit = "mail.channel.member"
    _populate_dependencies = ["res.partner", "mail.channel"]
    _populate_sizes = {'small': 10, 'medium': 100, 'large': 1000}

    def _populate_factories(self):
        partner_ids = self.env.registry.populated_models["res.partner"]
        channel_ids = self.env.registry.populated_models["mail.channel"]
        return [
            ("partner_id", populate.randomize(partner_ids)),
            ("channel_id", populate.randomize(channel_ids)),
        ]

    def _populate(self, size):
        channel_ids = self.env.registry.populated_models["mail.channel"]
        for channel_id in channel_ids:
            self.env['mail.channel.member'].create({
                'partner_id': self.env.ref('base.user_admin').partner_id.id,
                'channel_id': channel_id
            })
        return super()._populate(size)
