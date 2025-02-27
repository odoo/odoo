from odoo import api, models


class CardCampaign(models.Model):
    _inherit = 'card.campaign'

    @api.depends('preview_record_ref')
    def _compute_target_url(self):
        for campaign in self.filtered('preview_record_ref'):
            if (
                'event_id' in campaign.preview_record_ref
                and campaign.preview_record_ref._name in self._get_allowed_event_model_names()
            ):
                campaign.target_url = campaign.preview_record_ref.event_id.event_share_url

    def _get_allowed_event_model_names(self):
        """Get list of event models that are allowed in card campaigns."""
        return [
            model_name for model_name, _ in self._get_model_selection()
            if model_name.startswith('event.')
        ]

