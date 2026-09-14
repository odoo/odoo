from odoo import api, fields, models


class StockPickingBatch(models.Model):
    _inherit = "stock.picking.batch"

    team_id = fields.Many2one(
        comodel_name="team.team",
        string="Team",
        compute="_compute_team_id",
        store=True,
        index="btree_not_null",
        readonly=False,
        domain="[('use_stock', '=', True), ('company_id', 'in', [False, company_id])]",
        check_company=True,
    )

    @api.depends("picking_type_id.team_id", "picking_ids.team_id")
    def _compute_team_id(self):
        for batch in self:
            teams = batch.picking_type_id.team_id or batch.picking_ids.team_id
            batch.team_id = teams if len(teams) == 1 else batch.team_id
