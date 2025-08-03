from odoo import fields, models

class estate_res_users (models.Model):
    _inherit = 'res.users'          # extend, do NOT create a new model

    property_ids = fields.One2many(
        comodel_name='estate.property',
        inverse_name='seller',      # the Many2one in estate.property pointing here
        string='Properties',
        domain=[('Status', 'in', ('new', 'offerReceived', 'offerAccepted'))]
    )