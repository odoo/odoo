from odoo import fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    totals_below_sections = fields.Boolean(
        related="company_id.totals_below_sections",
        string="Add totals below sections",
        readonly=False,
        help="When ticked, totals and subtotals appear below the sections of the report.",
    )
    account_return_periodicity = fields.Selection(
        related="company_id.account_return_periodicity",
        string="Periodicity",
        readonly=False,
        required=True,
    )
    account_return_reminder_day = fields.Integer(
        related="company_id.account_return_reminder_day",
        string="Deadline",
        readonly=False,
        required=True,
    )
    account_tax_return_journal_id = fields.Many2one(
        related="company_id.account_tax_return_journal_id",
        string="Journal",
        readonly=False,
    )

    @_debug.perf.timed
    def open_tax_group_list(self):
        _debug.lifecycle("open_tax_group_list", records=self)
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "name": "Tax groups",
            "res_model": "account.tax.group",
            "view_mode": "list",
            "context": {
                "default_country_id": self.account_fiscal_country_id.id,
                "search_default_country_id": self.account_fiscal_country_id.id,
            },
        }
