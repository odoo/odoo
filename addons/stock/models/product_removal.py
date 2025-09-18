from odoo import fields, models


class ProductRemoval(models.Model):
    _name = "product.removal"
    _description = "Removal Strategy"

    name = fields.Char(
        string="Name",
        required=True,
        translate=True,
    )
    method = fields.Char(
        string="Method",
        required=True,
        translate=True,
        help="FIFO, LIFO...",
    )
