from odoo import fields, models


class StockReference(models.Model):
    _inherit = "stock.reference"

    pos_order_ids = fields.Many2many(
        comodel_name="pos.order",
        relation="stock_reference_pos_order_rel",
        column1="reference_id",
        column2="pos_order_id",
        string="PoS Orders",
    )
