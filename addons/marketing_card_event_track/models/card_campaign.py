
from odoo import fields, models

class Campaign(models.Model):
    _inherit = 'card.campaign'

    res_model = fields.Selection(selection_add=[('event.track', 'Event Track')], ondelete={'event.track': 'cascade'})
