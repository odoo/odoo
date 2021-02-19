# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import populate


class ImLivechatChannel(models.Model):
    _inherit = "im_livechat.channel"
    _populate_dependencies = ["res.users"]

    _populate_sizes = {
        'small': 10,
        'medium': 100,
        'large': 1000,
    }

    def _populate_factories(self):
        user_ids = self.env.registry.populated_models['res.users']

        def get_operator_ids(values, counter, random):
            operator_size = int(self._populate_sizes[self._context.get('size')] / 3)
            return random.choices(user_ids, k=operator_size)

        return [
            ('name', populate.constant('Livechat Channel {counter}')),
            ('user_ids', populate.compute(get_operator_ids)),
        ]

    def _populate(self, size):
        return super(ImLivechatChannel, self.with_context(size=size))._populate(size)
