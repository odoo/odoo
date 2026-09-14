from odoo import api, fields, models
from odoo.fields import Domain, DomainCondition

IN_MAX = 10_000


class ResUsers(models.Model):
    _inherit = "res.users"

    team_ids = fields.Many2many(
        comodel_name="team.team",
        string="Teams",
        compute="_compute_team_ids",
        search="_search_team_ids",
        compute_sudo=True,
    )
    team_member_ids = fields.One2many(
        comodel_name="team.member",
        inverse_name="user_id",
        string="Team Memberships",
    )

    @api.depends("team_member_ids.active", "team_member_ids.team_id")
    def _compute_team_ids(self):
        for user in self:
            user.team_ids = user.team_member_ids.filtered("active").team_id

    def _search_team_ids(self, operator, value):
        return self._search_usage_team_ids(operator, value)

    def _get_usage_team_ids(self, usage):
        self.check_singleton()
        return self.team_ids.filtered_domain(
            self.env["team.team"]._get_domain_usage(usage)
        )

    def _search_usage_team_ids(self, operator, value, usage=None):
        live = (
            Domain("team_id", "any!", self.env["team.team"]._get_domain_usage(usage))
            if usage
            else None
        )
        domain = self.env["team.member"]._search_live_projection(
            "team_member_ids", "team_id", operator, value, live=live
        )
        if domain is NotImplemented:
            return NotImplemented

        if not (isinstance(domain, DomainCondition) and domain.operator == "any!"):
            return domain

        user_ids = (
            self.env["res.users"]
            .with_context(active_test=False)
            ._search(domain, limit=IN_MAX)
            .get_result_ids()
        )
        if len(user_ids) < IN_MAX:
            return [("id", "in", user_ids)]

        return domain

    def write(self, vals):
        res = super().write(vals)
        if "active" in vals and not vals["active"]:
            self.env["team.member"].sudo().search(
                [("user_id", "in", self.ids)]
            ).action_archive()
        elif "company_ids" in vals:
            memberships = (
                self.env["team.member"].sudo().search([("user_id", "in", self.ids)])
            )
            stale = memberships.filtered(
                lambda m: (
                    m.team_id.company_id
                    and m.team_id.company_id not in m.user_id.company_ids
                )
            )
            if stale:
                stale.action_archive()
        return res
