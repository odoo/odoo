from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    team_id = fields.Many2one(
        comodel_name="team.team",
        string="Purchase Team",
        compute="_compute_team_id",
        precompute=True,
        store=True,
        index="btree_not_null",
        readonly=False,
        domain="[('use_purchase', '=', True), ('company_id', 'in', [False, company_id])]",
        ondelete="set null",
        check_company=True,
        tracking=True,
    )

    @api.model
    def default_get(self, fields):
        return self.env["team.team"]._drop_default_of_other_usage(
            super().default_get(fields), "purchase"
        )

    @api.depends("user_id", "company_id")
    def _compute_team_id(self):
        Team = self.env["team.team"]
        for order in self:
            team = order.team_id
            if team.company_id and team.company_id != order.company_id:
                team = Team
            if not order.user_id:
                order.team_id = team if team.use_purchase else False
                continue
            if team and order.user_id in (team.member_ids | team.user_id):
                order.team_id = team
                continue
            order.team_id = (
                Team.with_context(
                    allowed_company_ids=order.company_id.ids,
                    default_team_id=team.id,
                )
                .sudo()
                ._get_default_team("purchase", user_id=order.user_id.id, fallback=False)
                .with_env(self.env)
            )
