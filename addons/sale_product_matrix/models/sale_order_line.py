from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    product_add_mode = fields.Selection(
        related="product_template_id.product_add_mode",
        depends=["product_template_id"],
    )
