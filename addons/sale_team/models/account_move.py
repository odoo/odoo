from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import groupby

_debug = DebugLog(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    team_id = fields.Many2one(
        comodel_name="team.team",
        string="Sales Team",
        compute="_compute_team_id",
        store=True,
        readonly=False,
        domain="[('use_sale', '=', True), ('company_id', 'in', [False, company_id])]",
        ondelete="set null",
        tracking=True,
    )

    @api.depends("invoice_user_id", "company_id")
    def _compute_team_id(self):
        sale_moves = self.filtered(
            lambda move: move.is_sale_document(include_receipts=True),
        )
        _debug.perf.count("move_team_resolved", moves=len(self), sale=len(sale_moves))
        for (user_id, company_id), moves in groupby(
            sale_moves,
            key=lambda m: (m.invoice_user_id.id, m.company_id.id),
        ):
            self.env["account.move"].concat(*moves).team_id = (
                self.env["team.team"]
                .with_context(
                    allowed_company_ids=[company_id],
                )
                ._get_default_team(
                    "sale",
                    user_id=user_id,
                )
            )
