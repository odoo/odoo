from odoo import _, api, fields, models
from odoo.exceptions import AccessError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class DigestDigest(models.Model):
    _inherit = "digest.digest"

    kpi_account_bank_cash = fields.Boolean(string="Bank & Cash Moves")
    kpi_account_bank_cash_value = fields.Monetary(
        compute="_compute_kpi_account_bank_cash_value"
    )

    @api.depends_context("uid")
    @_debug.perf.timed
    def _compute_kpi_account_bank_cash_value(self):
        if not self.env.user.has_group("account.group_account_user"):
            raise AccessError(
                _("Do not have access, skip this data for user's digest email")
            )

        start, end, companies = self._get_kpi_compute_parameters()
        data = self.env["account.move"]._read_group(
            [
                ("date", ">=", start),
                ("date", "<", end),
                ("journal_id.type", "in", ("cash", "bank")),
                ("company_id", "in", companies.ids),
            ],
            ["company_id"],
            ["amount_total:sum"],
        )
        data = dict(data)

        for record in self:
            company = record.company_id or self.env.company
            record.kpi_account_bank_cash_value = data.get(company)

    def _get_kpi_actions(self, company, user):
        res = super()._get_kpi_actions(company, user)
        res.update(
            {
                "kpi_account_bank_cash": "account.open_account_journal_dashboard_kanban?menu_id=%s"
                % (self.env.ref("account.menu_finance").id)
            }
        )
        return res
