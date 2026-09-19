from datetime import timedelta

from odoo import _, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import date_utils
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT

_debug = DebugLog(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    @_debug.perf.timed
    def compute_fiscalyear_dates(self, current_date):
        self.check_singleton()
        date_str = current_date.strftime(DEFAULT_SERVER_DATE_FORMAT)

        fiscalyear = self.env["account.fiscal.year"].search(
            [
                ("company_id", "=", self.id),
                ("date_from", "<=", date_str),
                ("date_to", ">=", date_str),
            ],
            limit=1,
        )
        _debug.logic(
            "fiscalyear_record_lookup",
            company=self,
            date=date_str,
            fiscalyear=fiscalyear,
            found=bool(fiscalyear),
        )
        if fiscalyear:
            return {
                "date_from": fiscalyear.date_from,
                "date_to": fiscalyear.date_to,
                "record": fiscalyear,
            }

        date_from, date_to = date_utils.get_fiscal_year(
            current_date,
            day=self.account_config_id.fiscalyear_last_day,
            month=int(self.account_config_id.fiscalyear_last_month),
        )

        date_from_str = date_from.strftime(DEFAULT_SERVER_DATE_FORMAT)
        date_to_str = date_to.strftime(DEFAULT_SERVER_DATE_FORMAT)

        fiscalyear_from = self.env["account.fiscal.year"].search(
            [
                ("company_id", "=", self.id),
                ("date_from", "<=", date_from_str),
                ("date_to", ">=", date_from_str),
            ],
            limit=1,
        )
        if fiscalyear_from:
            date_from = fiscalyear_from.date_to + timedelta(days=1)

        fiscalyear_to = self.env["account.fiscal.year"].search(
            [
                ("company_id", "=", self.id),
                ("date_from", "<=", date_to_str),
                ("date_to", ">=", date_to_str),
            ],
            limit=1,
        )
        if fiscalyear_to:
            date_to = fiscalyear_to.date_from - timedelta(days=1)

        _debug.logic(
            "fiscalyear_dates_computed",
            company=self,
            date_from=date_from,
            date_to=date_to,
            clipped_from=bool(fiscalyear_from),
            clipped_to=bool(fiscalyear_to),
        )
        return {"date_from": date_from, "date_to": date_to}

    def _get_unreconciled_statement_lines_redirect_action(
        self, unreconciled_statement_lines
    ):
        return self.env[
            "account.bank.statement.line"
        ]._action_view_bank_reconciliation_widget(
            extra_domain=[("id", "in", unreconciled_statement_lines.ids)],
            name=_("Unreconciled statements lines"),
        )
