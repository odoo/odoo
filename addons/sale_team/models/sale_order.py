from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    team_id = fields.Many2one(
        comodel_name="team.team",
        string="Sales Team",
        compute="_compute_team_id",
        precompute=True,
        change_default=True,
        store=True,
        index=True,
        readonly=False,
        domain="[('use_sale', '=', True), ('company_id', 'in', [False, company_id])]",
        ondelete="set null",
        check_company=True,
        tracking=True,
    )
    tag_ids = fields.Many2many(
        comodel_name="crm.tag",
        relation="sale_order_tag_rel",
        column1="order_id",
        column2="tag_id",
        string="Tags",
        groups="sale.group_sale_salesman,sale.group_sale_readonly",
    )

    @api.depends("user_id", "company_id")
    def _compute_team_id(self):
        cached_teams = {}
        for order in self:
            default_team_id = order._get_default_sale_team_id()
            user_id = order.user_id.id
            company_id = order.company_id.id
            key = (default_team_id, user_id, company_id)
            if key not in cached_teams:
                cached_teams[key] = (
                    self.env["team.team"]
                    .with_context(
                        default_team_id=default_team_id,
                        allowed_company_ids=[company_id],
                    )
                    ._get_default_team(
                        "sale",
                        user_id=user_id,
                        domain=self.env["team.team"]._check_company_domain(company_id),
                    )
                )
            order.team_id = cached_teams[key]
        _debug.perf.count(
            "team_defaults_resolved", orders=len(self), keys=len(cached_teams)
        )

    def _get_default_sale_team_id(self):
        return self.env.context.get("default_team_id", False) or self.team_id.id

    def _prepare_invoice_vals(self):
        return super()._prepare_invoice_vals() | {"team_id": self.team_id.id}

    def _switch_negative_moves(self, moves, final):
        with self.env.protecting(
            [moves._fields["team_id"]],
            moves.sudo().filtered(lambda m: m.amount_total < 0),
        ):
            super()._switch_negative_moves(moves, final)
