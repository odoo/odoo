# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import populate


class Channel(models.Model):
    _inherit = "mail.channel"
    _populate_dependencies = ["im_livechat.channel"]

    _populate_sizes = {
        'small': 200,
        'medium': 1.105e5,
        'large': 1.51e6,
    }

    def get_channel_type(self):
        return [['channel', 'chat', 'livechat'], [0.05, 0.45, 0.5]]

    def _populate_factories(self):
        res = super(Channel, self)._populate_factories()

        livechats = self.env['im_livechat.channel'].browse(self.env.registry.populated_models['im_livechat.channel'])

        def get_operator_id(values, counter, random):
            if values['channel_type'] == 'livechat':
                livechat = random.choice(livechats)
                user = random.choice(livechat.user_ids)
                return user.partner_id.id
            return False

        def get_partner_ids(values, counter, random):
            channel_partner_ids = values['channel_partner_ids']
            if values['channel_type'] == 'livechat':
                channel_partner_ids[0] = (4, values['livechat_operator_id'])
            return channel_partner_ids

        res.insert(2, ('livechat_operator_id', populate.compute(get_operator_id)))
        res.insert(3, ('channel_partner_ids', populate.compute(get_partner_ids)))

        return res
