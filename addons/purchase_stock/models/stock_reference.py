from odoo import fields, models


class StockReference(models.Model):
    _inherit = "stock.reference"

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    purchase_ids = fields.Many2many(
        comodel_name="purchase.order",
        relation="stock_reference_purchase_rel",
        column1="reference_id",
        column2="purchase_id",
        string="Purchases",
        copy=False,
    )
