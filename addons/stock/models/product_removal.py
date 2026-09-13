from odoo import fields, models


class ProductRemoval(models.Model):
    _name = "product.removal"
    _description = "Removal Strategy"

    name = fields.Char(
        translate=True,
        required=True,
    )
    method = fields.Char(
        translate=True,
        required=True,
        help="FIFO, LIFO...",
    )
