from odoo import fields, models


class BaseOrderStockTestOrderLine(models.Model):
    _name = "base_order_stock.test.order.line"
    _inherit = ["mixin.order.line.stock"]
    _description = "Base Order Stock Test Order Line"

    state = fields.Selection(
        selection=[("draft", "Draft"), ("done", "Done")],
        default="draft",
    )
    display_type = fields.Selection(
        selection=[("line_section", "Section"), ("line_note", "Note")]
    )
    product_qty = fields.Float()
    qty_transferred = fields.Float()
