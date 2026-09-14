from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    purchase_team_ids = fields.Many2many(
        comodel_name="team.team",
        string="Purchase Teams",
        compute="_compute_purchase_team_ids",
        search="_search_purchase_team_ids",
        compute_sudo=True,
    )

    @api.depends(
        "team_member_ids.active",
        "team_member_ids.team_id",
        "team_member_ids.team_id.use_purchase",
    )
    def _compute_purchase_team_ids(self):
        for user in self:
            user.purchase_team_ids = user._get_usage_team_ids("purchase")

    def _search_purchase_team_ids(self, operator, value):
        return self._search_usage_team_ids(operator, value, usage="purchase")
