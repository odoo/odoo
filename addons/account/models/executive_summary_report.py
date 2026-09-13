from odoo import fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountReport(models.Model):
    _inherit = "account.report"

    @_debug.perf.timed
    def _report_custom_engine_executive_summary_ndays(
        self,
        expressions,
        options,
        date_scope,
        current_groupby,
        next_groupby,
        offset=0,
        limit=None,
        warnings=None,
    ):
        if current_groupby or next_groupby:
            raise UserError(
                self.env._(
                    "NDays expressions of executive summary report don't support the 'group by' feature."
                )
            )

        date_diff = fields.Date.from_string(
            options["date"]["date_to"]
        ) - fields.Date.from_string(options["date"]["date_from"])
        return {"result": date_diff.days + 1}
