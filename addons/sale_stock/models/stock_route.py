from odoo import fields, models


class StockRoute(models.Model):
    _inherit = "stock.route"

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    sale_selectable = fields.Boolean(
        string="Selectable on Sales Order Line",
    )
