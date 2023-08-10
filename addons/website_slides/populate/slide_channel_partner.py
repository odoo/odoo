# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random
from collections import defaultdict

from odoo import models
from odoo.tools import populate


class SlideChannelPartner(models.Model):
    _inherit = 'slide.channel.partner'
    _populate_dependencies = ['res.partner', 'slide.channel']
    # 50% more than partners, so supports 0 to N courses per partner.
    _populate_sizes = {'small': 150, 'medium': 3_000, 'large': 150_000}

    # Will ensure some courses have many partners
    choices_weights = {}

    def _populate_factories(self):
        partner_ids = self.env.registry.populated_models['res.partner']
        partner_not_company_ids = (
            self.env['res.partner'].search([['id', 'in', partner_ids], ['is_company', '=', False]]).ids
        )
        channel_ids_set = set(self.env.registry.populated_models['slide.channel'])
        attendees_partner_ids = partner_not_company_ids * len(channel_ids_set)
        random.shuffle(attendees_partner_ids)

        def _compute_next_attendee(iterator, *args):
            partners_channel_ids = defaultdict(set)
            for values, partner_id in zip(iterator, attendees_partner_ids):
                partner_channel_ids = partners_channel_ids[partner_id]
                remaining_channel_ids = list(channel_ids_set - partner_channel_ids)
                channel_id = random.choices(
                    remaining_channel_ids,
                    weights=self._get_courses_weights(len(remaining_channel_ids)),
                    k=1,
                )[0]

                partners_channel_ids[partner_id].add(channel_id)

                yield {**values, 'partner_id': partner_id, 'channel_id': channel_id}

        return [
            ('_attendee', _compute_next_attendee),
            ('active', populate.randomize([True, False], weights=[4, 1])),
            (
                'member_status',
                populate.randomize(
                    ['invited', 'joined', 'ongoing', 'completed'],
                    weights=[10, 50, 30, 20],
                ),
            ),
        ]

    def _get_courses_weights(self, n_choices):
        if not (weights := self.choices_weights.get(n_choices)):
            weights = [1 / i for i in range(1, n_choices + 1)]
            scaling_factor = 1 / sum(weights)
            weights = [x * scaling_factor for x in weights]
            self.choices_weights[n_choices] = weights
            return weights
        return weights
