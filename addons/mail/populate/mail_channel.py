# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import populate


class Channel(models.Model):
    _inherit = "mail.channel"
    _populate_dependencies = ["res.groups", "res.partner"]

    _populate_sizes = {
        'small': 100,
        'medium': 1.105e5,
        'large': 5.1e5,
    }

    def get_channel_type(self):
        return [['channel', 'chat'], [0.1, 0.9]]

    def _populate_factories(self):
        partner_ids = self.env.registry.populated_models['res.partner']
        group_ids = self.env.registry.populated_models['res.groups']

        def get_group_public_id(values, counter, random):
            if values.get('public') == 'groups':
                return random.choice(group_ids)

        def get_partner_ids(values, counter, random):
            if values.get('channel_type') == 'chat' and len(partner_ids) > counter:
                partner = partner_ids[counter]
                partners = [p for p in partner_ids if p != partner][:50]
                return [(4, partner), (4, random.choice(partners))]
            if values.get('channel_type') == 'channel':
                k = int(self._populate_sizes[self._context.get('size')] / 3)
            else:
                k = 2
            return [(4, partner_id) for partner_id in random.choices(partner_ids, k=k)]

        def get_channel_privacy(values, counter, random):
            if values['channel_type'] == 'chat':
                return 'private'
            return random.choices(['public', 'private', 'groups'], [0.4, 0.4, 0.2])[0]

        return [
            ('channel_type', populate.randomize(*self.get_channel_type())),
            ('channel_partner_ids', populate.compute(get_partner_ids)),
            ('name', populate.constant("channel - {counter}")),
            ('public', populate.compute(get_channel_privacy)),
            ('group_public_id', populate.compute(get_group_public_id))
        ]

    def _populate(self, size):
        return super(Channel, self.with_context(size=size))._populate(size)
