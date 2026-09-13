from datetime import timedelta

from odoo import _, fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import date_utils
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT

_debug = DebugLog(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    invoicing_switch_threshold = fields.Date(
        help="Every payment and invoice before this date will receive the 'From Invoicing' status, hiding all the accounting entries related to it. Use this option after installing Accounting if you were using only Invoicing before, before importing all your actual accounting data in to Odoo."
    )
    predict_bill_product = fields.Boolean()

    sign_invoice = fields.Boolean(string="Display signing field on invoices")
    signing_user = fields.Many2one(comodel_name="res.users")

    deferred_expense_journal_id = fields.Many2one(comodel_name="account.journal")
    deferred_expense_account_id = fields.Many2one(comodel_name="account.account")
    generate_deferred_expense_entries_method = fields.Selection(
        selection=[
            ("on_validation", "On bill validation"),
            ("manual", "Manually & Grouped"),
        ],
        string="Generate Deferred Expense Entries",
        default="on_validation",
        required=True,
    )
    deferred_expense_amount_computation_method = fields.Selection(
        selection=[
            ("day", "Days"),
            ("month", "Months"),
            ("full_months", "Full Months"),
        ],
        string="Deferred Expense Based on",
        default="month",
        required=True,
    )

    deferred_revenue_journal_id = fields.Many2one(comodel_name="account.journal")
    deferred_revenue_account_id = fields.Many2one(comodel_name="account.account")
    generate_deferred_revenue_entries_method = fields.Selection(
        selection=[
            ("on_validation", "On bill validation"),
            ("manual", "Manually & Grouped"),
        ],
        string="Generate Deferred Revenue Entries",
        default="on_validation",
        required=True,
    )
    deferred_revenue_amount_computation_method = fields.Selection(
        selection=[
            ("day", "Days"),
            ("month", "Months"),
            ("full_months", "Full Months"),
        ],
        string="Deferred Revenue Based on",
        default="month",
        required=True,
    )

    @_debug.perf.timed
    def write(self, vals):
        _debug.lifecycle("write", records=self, fields=sorted(vals))
        old_threshold_vals = {}
        for record in self.exists():
            old_threshold_vals[record] = record.invoicing_switch_threshold

        rslt = super().write(vals)

        for record in self.exists():
            if (
                "invoicing_switch_threshold" in vals
                and old_threshold_vals[record] != record.invoicing_switch_threshold
            ):
                _debug.logic(
                    "invoicing_switch_moved",
                    company=record,
                    previous=old_threshold_vals[record],
                    threshold=record.invoicing_switch_threshold,
                    mode="apply" if record.invoicing_switch_threshold else "clear",
                )
                self.env["account.move.line"].flush_model(["move_id", "parent_state"])
                self.env["account.move"].flush_model(
                    [
                        "company_id",
                        "date",
                        "state",
                        "payment_state",
                        "payment_state_before_switch",
                    ]
                )
                if record.invoicing_switch_threshold:
                    params = {
                        "company_id": record.id,
                        "switch_threshold": record.invoicing_switch_threshold,
                    }
                    self.env.cr.execute(
                        """
                        update account_move_line aml
                        set parent_state = 'posted'
                        from account_move move
                        where aml.move_id = move.id
                        and move.payment_state = 'invoicing_legacy'
                        and move.date >= %(switch_threshold)s
                        and move.company_id = %(company_id)s
                    """,
                        params,
                    )
                    _debug.perf.count(
                        "legacy_lines_reposted",
                        company=record,
                        rows=self.env.cr.rowcount,
                    )
                    self.env.cr.execute(
                        """
                        update account_move
                        set state = 'posted',
                            payment_state = payment_state_before_switch,
                            payment_state_before_switch = null
                        where payment_state = 'invoicing_legacy'
                        and date >= %(switch_threshold)s
                        and company_id = %(company_id)s
                    """,
                        params,
                    )
                    _debug.perf.count(
                        "legacy_moves_reposted",
                        company=record,
                        rows=self.env.cr.rowcount,
                    )
                    self.env.cr.execute(
                        """
                        update account_move_line aml
                        set parent_state = 'cancel'
                        from account_move move
                        where aml.move_id = move.id
                        and move.state = 'posted'
                        and move.date < %(switch_threshold)s
                        and move.company_id = %(company_id)s
                    """,
                        params,
                    )
                    _debug.perf.count(
                        "pre_threshold_lines_cancelled",
                        company=record,
                        rows=self.env.cr.rowcount,
                    )
                    self.env.cr.execute(
                        """
                        update account_move
                        set state = 'cancel',
                            payment_state_before_switch = payment_state,
                            payment_state = 'invoicing_legacy'
                        where state = 'posted'
                        and date < %(switch_threshold)s
                        and company_id = %(company_id)s
                    """,
                        params,
                    )
                    _debug.perf.count(
                        "pre_threshold_moves_cancelled",
                        company=record,
                        rows=self.env.cr.rowcount,
                    )
                else:
                    params = {"company_id": record.id}
                    self.env.cr.execute(
                        """
                        update account_move_line aml
                        set parent_state = 'posted'
                        from account_move move
                        where aml.move_id = move.id
                        and move.payment_state = 'invoicing_legacy'
                        and move.company_id = %(company_id)s
                    """,
                        params,
                    )
                    _debug.perf.count(
                        "legacy_lines_restored",
                        company=record,
                        rows=self.env.cr.rowcount,
                    )
                    self.env.cr.execute(
                        """
                        update account_move
                        set state = 'posted',
                            payment_state = payment_state_before_switch,
                            payment_state_before_switch = null
                        where payment_state = 'invoicing_legacy'
                        and company_id = %(company_id)s
                    """,
                        params,
                    )
                    _debug.perf.count(
                        "legacy_moves_restored",
                        company=record,
                        rows=self.env.cr.rowcount,
                    )

                self.env["account.move.line"].invalidate_model(["parent_state"])
                self.env["account.move"].invalidate_model(
                    ["state", "payment_state", "payment_state_before_switch"]
                )

        return rslt

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
            day=self.fiscalyear_last_day,
            month=int(self.fiscalyear_last_month),
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
