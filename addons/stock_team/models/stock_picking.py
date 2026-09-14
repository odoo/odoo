from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    team_id = fields.Many2one(
        comodel_name="team.team",
        string="Team",
        compute="_compute_team_id",
        precompute=True,
        store=True,
        index="btree_not_null",
        readonly=False,
        domain="[('use_stock', '=', True), ('company_id', 'in', [False, company_id])]",
        check_company=True,
        tracking=True,
    )

    @api.model
    def default_get(self, fields):
        return self.env["team.team"]._drop_default_of_other_usage(
            super().default_get(fields), "stock"
        )

    @api.depends("picking_type_id")
    def _compute_team_id(self):
        for picking in self:
            picking.team_id = picking.picking_type_id.team_id
