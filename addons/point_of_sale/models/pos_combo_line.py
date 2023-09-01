from odoo import fields, models


class PosComboLine(models.Model):
    _name = "pos.combo.line"
    _description = "Product Combo Items"

    product_id = fields.Many2one("product.product", string="Product", required=True)
    combo_price = fields.Float("Price Extra", default=0.0)
    lst_price = fields.Float("Original Price", related="product_id.lst_price")
    combo_id = fields.Many2one("pos.combo")
