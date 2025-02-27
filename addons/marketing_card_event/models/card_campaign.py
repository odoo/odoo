from odoo import models


class CardCampaign(models.Model):
    _inherit = 'card.campaign'

    def _get_allowed_event_model_names(self):
        """Get list of event models that are allowed in card campaigns."""
        return [
            model_name for model_name, _ in self._get_model_selection()
            if model_name.startswith('event.')
        ]

