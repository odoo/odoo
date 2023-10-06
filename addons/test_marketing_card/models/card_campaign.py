
from odoo import fields, models


class CardCampaign(models.Model):
    _inherit = 'card.campaign'

    def _get_model_selection(self):
        return super()._get_model_selection() + [
            ('card.test.event.performance', 'Event Performance'),
            ('card.test.event.location', 'Event Location')
        ]

    res_model = fields.Selection(selection=_get_model_selection)
