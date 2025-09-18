from odoo import fields, models


class StockReference(models.Model):
    _inherit = "stock.reference"

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    sale_ids = fields.Many2many(
        comodel_name="sale.order",
        relation="stock_reference_sale_rel",
        column1="reference_id",
        column2="sale_id",
        string="Sales",
    )
