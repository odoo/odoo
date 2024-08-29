
from odoo.addons import marketing_card
from odoo import fields, models


class CardCampaignElement(models.Model, marketing_card.CardCampaignElement):

    card_element_role = fields.Selection(selection_add=[
        ('unused', 'Unused Testing Role'),
        ('unused_2', 'Unused Testing Role 2')
    ], ondelete={
        'unused': 'cascade',
        'unused_2': 'cascade',
    })
