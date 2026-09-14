from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ResUsers(models.Model):
    _inherit = "res.users"

    sale_team_ids = fields.Many2many(
        comodel_name="team.team",
        string="Sales Teams",
        compute="_compute_sale_team_ids",
        search="_search_sale_team_ids",
        compute_sudo=True,
    )
    sale_team_id = fields.Many2one(
        comodel_name="team.team",
        string="User Sales Team",
        compute="_compute_sale_team_id",
        store=True,
        help="Main user sales team. Used notably for pipeline, or to set sales team in invoicing or subscription.",
    )

    @api.depends(
        "team_member_ids.active",
        "team_member_ids.team_id",
        "team_member_ids.team_id.use_sale",
    )
    def _compute_sale_team_ids(self):
        for user in self:
            user.sale_team_ids = user._get_usage_team_ids("sale")

    def _search_sale_team_ids(self, operator, value):
        return self._search_usage_team_ids(operator, value, usage="sale")

    @api.depends(
        "team_member_ids.team_id",
        "team_member_ids.active",
        "team_member_ids.team_id.use_sale",
    )
    def _compute_sale_team_id(self):
        for user in self:
            memberships = user.team_member_ids.filtered(
                lambda m: m.active and m.team_id.use_sale
            )
            user.sale_team_id = memberships[:1].team_id
            _debug.logic(
                "sale_team_resolved",
                user=user,
                memberships=memberships,
                team=user.sale_team_id,
            )
