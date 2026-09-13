from odoo import api, fields, models
from odoo.fields import DomainCondition


class ResUsers(models.Model):
    _inherit = "res.users"

    crm_team_ids = fields.Many2many(
        comodel_name="crm.team",
        string="Sales Teams",
        compute="_compute_crm_team_ids",
        search="_search_crm_team_ids",
        compute_sudo=True,
        copy=False,
        readonly=True,
    )
    crm_team_member_ids = fields.One2many(
        comodel_name="crm.team.member",
        inverse_name="user_id",
        string="Sales Team Members",
    )
    sale_team_id = fields.Many2one(
        comodel_name="crm.team",
        string="User Sales Team",
        compute="_compute_sale_team_id",
        store=True,
        readonly=True,
        help="Main user sales team. Used notably for pipeline, or to set sales team in invoicing or subscription.",
    )

    @api.depends("crm_team_member_ids.active", "crm_team_member_ids.crm_team_id")
    def _compute_crm_team_ids(self):
        for user in self:
            user.crm_team_ids = user.crm_team_member_ids.filtered("active").crm_team_id

    def _search_crm_team_ids(self, operator, value):
        domain = self.env["crm.team.member"]._search_live_projection(
            "crm_team_member_ids", "crm_team_id", operator, value
        )
        if domain is NotImplemented:
            return NotImplemented

        if not (isinstance(domain, DomainCondition) and domain.operator == "any!"):
            return domain

        IN_MAX = 10_000
        user_ids = (
            self.env["res.users"]
            .with_context(active_test=False)
            ._search(domain, limit=IN_MAX)
            .get_result_ids()
        )
        if len(user_ids) < IN_MAX:
            return [("id", "in", user_ids)]

        return domain

    @api.depends(
        "crm_team_member_ids.crm_team_id",
        "crm_team_member_ids.create_date",
        "crm_team_member_ids.active",
    )
    def _compute_sale_team_id(self):
        for user in self:
            memberships = user.crm_team_member_ids.filtered("active")
            user.sale_team_id = memberships[:1].crm_team_id

    def write(self, vals):
        res = super().write(vals)
        if vals.get("active") is False:
            self.env["crm.team.member"].sudo().search(
                [("user_id", "in", self.ids)]
            ).action_archive()
        elif "company_ids" in vals:
            memberships = (
                self.env["crm.team.member"].sudo().search([("user_id", "in", self.ids)])
            )
            stale = memberships.filtered(
                lambda m: (
                    m.crm_team_id.company_id
                    and m.crm_team_id.company_id not in m.user_id.company_ids
                )
            )
            if stale:
                stale.action_archive()
        return res
