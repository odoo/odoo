from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    gelato_product_uid = fields.Char(
        readonly=True,
        name="Gelato Product UID",
    )
