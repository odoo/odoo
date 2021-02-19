# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import populate


class Message(models.Model):
    _inherit = "mail.message"
    _populate_dependencies = ["mail.channel", "res.partner"]

    _populate_sizes = {
        'small': 1e4,
        'medium': 1e7,
        'large': 1.5e8,
    }

    def _populate_factories(self):
        partner_ids = self.env.registry.populated_models['res.partner']
        channels = self.env['mail.channel'].browse(self.env.registry.populated_models['mail.channel'])

        def get_res_id(values, counter, random):
            if values['model'] == 'mail.channel':
                values['channel'] = random.choice(channels)
                return values['channel'].id
            return random.choice(partner_ids)

        def get_author_id(values, counter, random):
            if values['model'] == 'res.partner':
                return random.choice(partner_ids)
            channel = values.pop('channel')
            return random.choice(channel.channel_last_seen_partner_ids.partner_id.ids)

        return [
            ('body', populate.constant('<p>Message {counter}</p>')),
            ('model', populate.randomize(['res.partner', 'mail.channel'], [0.1, 0.9])),
            ('res_id', populate.compute(get_res_id)),
            ('author_id', populate.compute(get_author_id)),
        ]
