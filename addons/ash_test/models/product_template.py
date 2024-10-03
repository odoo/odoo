from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'  # Inherit from product.template

    # Define new fields
    tenant_id = fields.Char('Tenant ID')
    site_code = fields.Char('Site Code')

    sku = fields.Char('SKU', unique=True)
    outer_gtin = fields.Char('Outer GTIN')
    brand = fields.Char('Brand')
    source = fields.Char('Source')
    pack_size_pcs = fields.Integer('Pack Size in pcs')
    carton_length = fields.Char('Carton Length')
    carton_width = fields.Char('Carton Width')
    carton_height = fields.Char('Carton Height')
    product_length = fields.Char('Product Length')
    product_width = fields.Char('Product Width')
    product_height = fields.Char('Product Height')
    image_url = fields.Char('Image URL')
    automation_manual_product = fields.Selection([
        ('automation', 'Automation'),
        ('manual', 'Manual'),
        ('none', 'None'),
    ], string='Automation Manual Product', default='none')