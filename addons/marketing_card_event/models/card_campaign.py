from odoo import models, _


class CardCampaign(models.Model):
    _inherit = 'card.campaign'

    def _compute_target_url_placeholder(self):
        super()._compute_target_url_placeholder()
        for model_name, campaigns in self.grouped('res_model').items():
            if (
                'event_id' in self.env[model_name]
                and model_name in self._get_allowed_event_model_names()
            ):
                if isinstance(self.env[model_name], self.env.registry['website.published.mixin']):
                    campaigns.target_url_placeholder = _("Target record (if published) or Event page")
                else:
                    campaigns.target_url_placeholder = _("Event page")

    def _get_allowed_event_model_names(self):
        """Get list of event models that are allowed in card campaigns."""
        return [
            model_name for model_name, _ in self._get_model_selection()
            if model_name.startswith('event.')
        ]

    # ==========================================================================
    # URL Redirection
    # ==========================================================================

    def _get_record_url(self, record):
        """Return the url of the event if the record itself has no url."""
        record_url = super()._get_record_url(record)
        if not record_url and (
            'event_id' in record
            and record._name in self._get_allowed_event_model_names()
        ):
            return record.event_id.event_share_url
        return record_url
