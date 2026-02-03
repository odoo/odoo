from odoo import fields, models


class ResUsersInherit(models.Model):
    """Inherit res.users model to add real estate properties field"""
    _inherit = "res.users"
    
    property_ids = fields.One2many(
        comodel_name='estate.property',
        inverse_name='salesperson_id',   
        string='Real Estate Properties',
        domain="[('active', '=', True)]"
    )