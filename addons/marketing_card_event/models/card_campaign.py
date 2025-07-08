from odoo import api, models


class CardCampaign(models.Model):
    _inherit = 'card.campaign'

    @api.depends('preview_record_ref')
    def _compute_target_url(self):
        for campaign in self.filtered('preview_record_ref'):
            campaign_model = campaign.preview_record_ref._name
            if (
                campaign_model.startswith('event.')
                and 'event_id' in campaign.preview_record_ref
                and campaign_model in (allowed_model_name for allowed_model_name, _ in self._get_model_selection())
            ):
                campaign.target_url = campaign.preview_record_ref.event_id.event_share_url
