from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    asset_position_id = fields.Many2one(
        comodel_name="resource.asset.kind.position",
        string="Position",
        help="Where on the repaired asset this part goes in or comes out.",
    )
