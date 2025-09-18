from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    sale_order_line_ids = fields.One2many(
        comodel_name="sale.order.line",
        inverse_name="product_id",
        string="SO Lines",
    )  # used to compute quantities
