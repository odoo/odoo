from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


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

    @api.model
    def default_get(self, fields):
        return self.env["team.team"]._drop_default_of_other_usage(
            super().default_get(fields), "stock"
        )

    @api.depends("picking_type_id", "picking_ids.team_id")
    def _compute_team_id(self):
        _debug.perf.count("batch_team_compute", batches=self)
        for batch in self:
            if not batch.picking_ids:
                batch.team_id = batch.picking_type_id.team_id or batch.team_id
                continue
            teams = batch.picking_ids.team_id
            batch.team_id = teams if len(teams) == 1 else False
