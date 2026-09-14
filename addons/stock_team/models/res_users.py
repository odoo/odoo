from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ResUsers(models.Model):
    _inherit = "res.users"

    stock_team_ids = fields.Many2many(
        comodel_name="team.team",
        string="Inventory Teams",
        compute="_compute_stock_team_ids",
        search="_search_stock_team_ids",
        compute_sudo=True,
    )

    @api.depends(
        "team_member_ids.active",
        "team_member_ids.team_id",
        "team_member_ids.team_id.use_stock",
    )
    def _compute_stock_team_ids(self):
        _debug.perf.count("user_stock_teams_compute", users=self)
        for user in self:
            user.stock_team_ids = user._get_usage_team_ids("stock")

    def _search_stock_team_ids(self, operator, value):
        return self._search_usage_team_ids(operator, value, usage="stock")
