from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'  # Inherit from product.template

    # Define new fields
    tenant_id = fields.Char('Tenant ID')
    site_code = fields.Char('Site Code')
    