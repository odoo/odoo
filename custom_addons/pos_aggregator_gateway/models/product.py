from odoo import models, fields

class ProductProduct(models.Model):
    _inherit = 'product.product'

    uber_eats_id = fields.Char(string='Uber Eats ID', index=True, help="External Product ID from Uber Eats")
    doordash_id = fields.Char(string='DoorDash ID', index=True, help="External Product ID from DoorDash")
