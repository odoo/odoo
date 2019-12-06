# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MergeUtmCampaign(models.TransientModel):
    _name = 'utm.campaign.merge'
    _description = 'Merge UTM Campaigns'

    @api.model
    def default_get(self, fields):
        """Use active_ids from the context to fetch the UTM campaign to merge."""
        record_ids = self._context.get('active_ids')
        result = super(MergeUtmCampaign, self).default_get(fields)
        result['campaign_ids'] = record_ids
        result['campaign_id'] = record_ids[0]
        return result

    campaign_id = fields.Many2one('utm.campaign', string='Campaign to Keep', required=True)
    campaign_ids = fields.Many2many('utm.campaign', string='Campaigns')

    def action_merge(self):
        self.ensure_one()
        self.campaign_ids._merge_utm_campaigns(self.campaign_id)

        action = self.env.ref('utm.utm_campaign_action').read()[0]
        action.update({
            'views': [[False, 'form']],
            'res_id': self.campaign_id.id,
            'view_mode': 'form'
        })
        return action
