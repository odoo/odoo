from odoo import api, fields, models


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    team_id = fields.Many2one(
        comodel_name="team.team",
        string="Team",
        compute="_compute_team_id",
        precompute=True,
        store=True,
        index="btree_not_null",
        readonly=False,
        domain="[('use_mrp', '=', True), ('company_id', 'in', [False, company_id])]",
        check_company=True,
        tracking=True,
    )

    @api.depends("picking_type_id.team_id")
    def _compute_team_id(self):
        for production in self:
            team = production.picking_type_id.team_id
            production.team_id = team if team.use_mrp else production.team_id
