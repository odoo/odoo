from odoo import _, api, fields, models
from odoo.exceptions import AccessError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class DigestDigest(models.Model):
    _inherit = "digest.digest"

    kpi_account_total_revenue = fields.Boolean(string="Revenue")
    kpi_account_total_revenue_value = fields.Monetary(
        compute="_compute_kpi_account_total_revenue_value"
    )

    @api.depends_context("uid")
    @_debug.perf.timed
    def _compute_kpi_account_total_revenue_value(self):
        if not self.env.user.has_group("account.group_account_invoice"):
            raise AccessError(
                _("Do not have access, skip this data for user's digest email")
            )

        start, end, companies = self._get_kpi_compute_parameters()

        total_per_companies = dict(
            self.env["account.move.line"]
            .sudo()
            ._read_group(
                groupby=["company_id"],
                aggregates=["balance:sum"],
                domain=[
                    ("company_id", "in", companies.ids),
                    ("date", ">", start),
                    ("date", "<=", end),
                    ("account_id.internal_group", "=", "income"),
                    ("parent_state", "=", "posted"),
                ],
            )
        )

        for record in self:
            company = record.company_id or self.env.company
            record.kpi_account_total_revenue_value = -total_per_companies.get(
                company, 0
            )

    def _get_kpi_actions(self, company, user):
        res = super()._get_kpi_actions(company, user)
        res["kpi_account_total_revenue"] = (
            "account.action_move_out_invoice_type?menu_id=%s"
            % self.env.ref("account.menu_finance").id
        )
        return res
