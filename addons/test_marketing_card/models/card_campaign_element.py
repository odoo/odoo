
from odoo import fields, models


class CampaignElement(models.Model):
    _inherit = 'card.campaign.element'

    card_element_role = fields.Selection(selection_add=[
        ('unused', 'Unused Testing Role'),
        ('unused_2', 'Unused Testing Role 2')
    ], ondelete={
        'unused': 'cascade',
        'unused_2': 'cascade',
    })
