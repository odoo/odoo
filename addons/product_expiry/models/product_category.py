from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = "product.category"

    use_expiration_date = fields.Boolean(
        help="When this box is ticked, products in this category default to managing"
        " product expiration, with dates on the product and on the corresponding"
        " lot/serial numbers"
    )
