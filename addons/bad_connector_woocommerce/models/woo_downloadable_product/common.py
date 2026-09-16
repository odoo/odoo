from odoo import fields, models


class WooDownloadableProduct(models.Model):
    _name = "woo.downloadable.product"
    _inherit = ["woo.binding"]
    _description = "WooCommerce Downloadable Product"

    name = fields.Char(string="File Name", required=True)
    url = fields.Char(string="File URL")
    woo_product_id = fields.Many2one(
        "woo.product.product",
        ondelete="cascade",
    )
