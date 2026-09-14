from odoo import fields, models


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    team_id = fields.Many2one(
        comodel_name="team.team",
        string="Team",
        index="btree_not_null",
        domain="[('use_stock', '=', True), ('company_id', 'in', [False, company_id])]",
        check_company=True,
        help="The team running this operation: its transfers are filed under it.",
    )
