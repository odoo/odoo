from odoo import models, fields


class ResUsers(models.Model):
    _inherit = "res.users"
    
    property_ids = fields.One2many("estate.property", "sales_person_id", domain=[('state', 'in', ('new', 'offer_received'))])