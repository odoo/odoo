from odoo import fields, models


class WooProductImageUrl(models.Model):
    _name = "woo.product.image.url"
    _description = "WooCommerce Product Image URL"

    name = fields.Char(string="Image Name", required=True)
    url = fields.Char(string="Image URL", required=True)
    alt = fields.Text()
