# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models
from odoo.tools import populate


class SlideChannelPartner(models.Model):
    _inherit = 'slide.channel.partner'
    _populate_dependencies = ['res.partner', 'slide.channel']
    # 50% more than partners, so supports 0 to N courses per partner.
    _populate_sizes = {'small': 150, 'medium': 3_000, 'large': 150_000}

    def _populate_factories(self):
        random = populate.Random('slidechannelpartners')
        partner_ids = self.env.registry.populated_models['res.partner']
        partner_not_company_ids = (
            self.env['res.partner'].search([('id', 'in', partner_ids), ('is_company', '=', False)]).ids
        )
        channel_ids_set = set(self.env.registry.populated_models['slide.channel'])
        attendees_partner_ids = partner_not_company_ids * len(channel_ids_set)
        random.shuffle(attendees_partner_ids)

        courses_weights = [1 / i for i in range(1, len(channel_ids_set) + 1)]  # skewed for perf evals

        def _compute_next_attendee(iterator, *args):
            partners_channel_ids = defaultdict(set)
            for values, partner_id in zip(iterator, attendees_partner_ids):
                remaining_channel_ids = list(channel_ids_set - partners_channel_ids[partner_id])
                channel_id = random.choices(
                    remaining_channel_ids,
                    weights=courses_weights[:len(remaining_channel_ids)],
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
