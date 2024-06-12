from collections import defaultdict

from odoo import models, osv

class CardCard(models.Model):
    _inherit = 'card.card'

    def _deferred_create(self):
        """Create new cards based on precommit values."""
        card_values_all = self.env.cr.precommit.data.pop('marketing_card_create_cards_values', None)
        if not card_values_all:
            return

        # only keep the last one
        values_from_campaign_res_pair = dict()
        for values in card_values_all:
            values_from_campaign_res_pair[(values['campaign_id'], values['res_id'])] = values

        # get all existing
        res_ids_from_campaign_id = defaultdict(list)
        for campaign_id, res_id in values_from_campaign_res_pair:
            res_ids_from_campaign_id[campaign_id].append(res_id)
        domain = osv.expression.OR([
            [('campaign_id', '=', campaign_id), ('res_id', 'in', res_ids)]
            for (campaign_id, res_ids) in res_ids_from_campaign_id.items()
        ])
        existing_cards_from_campaign = self.env['card.card'].search_fetch(domain, ['campaign_id', 'res_id']).grouped('campaign_id')
        existing_res_ids_from_campaign_id = {
            campaign.id: set(cards.mapped('res_id'))
            for campaign, cards in existing_cards_from_campaign.items()
        }

        # create missing
        self.env['card.card'].create([
            values for (campaign_id, card_id), values in values_from_campaign_res_pair.items()
            if res_id not in existing_res_ids_from_campaign_id.get(campaign_id, tuple())
        ])
