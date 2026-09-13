from odoo import fields, models


class StockReference(models.Model):
    _inherit = "stock.reference"

    production_ids = fields.Many2many(
        comodel_name="mrp.production",
        relation="stock_reference_production_rel",
        column1="reference_id",
        column2="production_id",
        string="Productions",
    )
