import odoo.addons.decimal_precision as dp # type: ignore
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

class TiktokProduct(models.Model):
    _name = 'tiktok.product'
    _description = 'Tiktok Product'

    name = fields.Char('Name')
    item_id = fields.Float('Item ID', size=16, digits=(16,0))
    price = fields.Float('Price')
    price_after_tax = fields.Float('Price After Tax')
    
    shop_id = fields.Many2one('tiktok.shop', 'Shop')
    product_tmpl_id = fields.Many2one('product.template', 'Product')

    @api.onchange('product_tmpl_id')
    def onchange_product_tmpl(self):
        self.name = self.product_tmpl_id.name

class TiktokProductVariant(models.Model):
    _name = 'tiktok.product.variant'
    _description = 'Tiktok Product Variant'

    name = fields.Char('Name')
    product_id = fields.Many2one('product.product', 'Product')
    product_tmpl_id = fields.Many2one(related='product_id.product_tmpl_id', relation='product.template', string='Product Template', store=True)
    shop_id = fields.Many2one('tiktok.shop', 'Shop')

    variation_id = fields.Float('Variation ID', size=16, digits=(16,0))
    price = fields.Float('Price')
    price_after_tax = fields.Float('Price After Tax')

    @api.onchange('product_id')
    def onchange_product(self):
        self.name = self.product_id.display_name
    