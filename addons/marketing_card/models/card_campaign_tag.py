import random

from odoo import fields, models


class CardCampaignTag(models.Model):
    _name = 'card.campaign.tag'
    _description = 'Marketing Card Campaign Tag'

    def _get_default_color(self):
        return random.randint(1, 11)

    name = fields.Char(required=True)
    color = fields.Integer(default=_get_default_color)

    _sql_constraints = [('name_uniq', "unique(name)", "Tags may not reuse existing names.")]
