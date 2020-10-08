# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import populate


class EventRegistration(models.Model):
    _inherit = 'event.registration'
    _populate_sizes = {
        'small': 5*5,
        'medium': 150*5,
        'large': 400*5
    }
    _populate_dependencies = [
        'event.event',
        'res.partner',  # customer
    ]

    def _populate_factories(self):
        event_ids = self.env.registry.populated_models['res.company']
        partner_ids = self.env.registry.populated_models['res.partner']

        return [
            ('event_id', populate.randomize(event_ids)),
            ('partner_id', populate.iterate(
                [False] + partner_ids,
                [1] + [1/(len(partner_ids) or 1)]*len(partner_ids))
             ),
        ]
