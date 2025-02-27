from odoo import api, models


class CardCampaign(models.Model):
    _inherit = 'card.campaign'

    @api.depends('preview_record_ref')
    def _compute_target_url(self):
        for campaign in self.filtered('preview_record_ref'):
            if campaign.preview_record_ref._name.startswith('event.') and 'event_id' in campaign.preview_record_ref:
                campaign.target_url = campaign.preview_record_ref.event_id.event_share_url
