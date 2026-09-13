from odoo import fields, models


class ProductRemoval(models.Model):
    _name = "product.removal"
    _description = "Removal Strategy"

    name = fields.Char(
        translate=True,
        required=True,
    )
    method = fields.Char(
        help="FIFO, LIFO...",
        translate=True,
        required=True,
    )
