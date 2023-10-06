import random

from odoo import fields, models


class CampaignTag(models.Model):
    _name = 'social.share.campaign.tag'
    _description = 'Social Share Campaign Tag'

    def _get_default_color(self):
        return random.randint(1, 11)

    name = fields.Char()
    color = fields.Integer(default=_get_default_color)
