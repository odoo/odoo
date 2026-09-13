from odoo import fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _update_general_dashboard_data(self, dashboard_data):
        super()._update_general_dashboard_data(dashboard_data)

        companies_with_returns_to_do = sum(
            (
                company_data[0]
                for company_data in self.env["account.return"]._read_group(
                    domain=[
                        ("company_ids", "in", self.env.companies.ids),
                        ("is_completed", "=", False),
                        ("date_to", "<", fields.Date.today()),
                    ],
                    groupby=["company_ids"],
                )
            ),
            self.env["res.company"],
        )

        for journal in self.filtered(lambda j: j.type == "general"):
            is_return_journal = (
                journal == journal.company_id.account_tax_return_journal_id
            )
            dashboard_data[journal.id]["is_account_return_journal"] = is_return_journal
            if is_return_journal:
                dashboard_data[journal.id]["tax_return_button_primary"] = (
                    journal.company_id in companies_with_returns_to_do
                    or not journal.company_id.account_opening_date
                )

    @_debug.perf.timed
    def action_view_bank_balance_in_gl(self):
        """Show the bank balance inside the General Ledger report.
        :return: An action opening the General Ledger.
        """
        _debug.lifecycle("action_view_bank_balance_in_gl", records=self)
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "account.action_account_report_general_ledger"
        )

        action["context"] = dict(
            self.env["ir.actions.actions"]._eval_action_context(action["context"]),
            default_filter_accounts=self.default_account_id.code,
        )

        return action
