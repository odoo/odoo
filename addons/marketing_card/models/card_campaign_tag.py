import random

from odoo import fields, models


class CardCampaignTag(models.Model):
    _name = 'card.campaign.tag'
    _description = 'Marketing Card Campaign Tag'

    def _get_default_color(self):
        return random.randint(1, 11)

    name = fields.Char(required=True, translate=True)
    color = fields.Integer(default=_get_default_color)
