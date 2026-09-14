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

    @api.depends("user_id", "company_id")
    def _compute_team_id(self):
        Team = self.env["team.team"]
        for order in self:
            if not order.user_id:
                order.team_id = order.team_id if order.team_id.use_purchase else False
                continue
            if order.team_id and order.user_id in (
                order.team_id.member_ids | order.team_id.user_id
            ):
                continue
            order.team_id = (
                Team.with_company(order.company_id)
                .with_context(default_team_id=order.team_id.id)
                ._get_default_team("purchase", user_id=order.user_id.id)
            )
