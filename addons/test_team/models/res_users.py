from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    alpha_team_ids = fields.Many2many(
        comodel_name="team.team",
        compute="_compute_alpha_team_ids",
        search="_search_alpha_team_ids",
        compute_sudo=True,
    )
    beta_team_ids = fields.Many2many(
        comodel_name="team.team",
        compute="_compute_beta_team_ids",
        search="_search_beta_team_ids",
        compute_sudo=True,
    )

    @api.depends(
        "team_member_ids.active",
        "team_member_ids.team_id",
        "team_member_ids.team_id.use_alpha",
    )
    def _compute_alpha_team_ids(self):
        for user in self:
            user.alpha_team_ids = user._get_usage_team_ids("alpha")

    @api.depends(
        "team_member_ids.active",
        "team_member_ids.team_id",
        "team_member_ids.team_id.use_beta",
    )
    def _compute_beta_team_ids(self):
        for user in self:
            user.beta_team_ids = user._get_usage_team_ids("beta")

    def _search_alpha_team_ids(self, operator, value):
        return self._search_usage_team_ids(operator, value, usage="alpha")

    def _search_beta_team_ids(self, operator, value):
        return self._search_usage_team_ids(operator, value, usage="beta")
