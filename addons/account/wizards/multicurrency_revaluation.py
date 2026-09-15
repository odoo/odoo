import json

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command, Date
from odoo.libs.debug_log import DebugLog
from odoo.tools import format_date

_debug = DebugLog(__name__)


class AccountMulticurrencyRevaluationWizard(models.TransientModel):
    _name = "account.multicurrency.revaluation.wizard"
    _description = "Multicurrency Revaluation Wizard"

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        compute="_compute_accounting_values",
        inverse="_inverse_journal_id",
        compute_sudo=True,
        readonly=False,
        required=True,
        domain=[("type", "=", "general")],
    )
    date = fields.Date(
        default=lambda self: self.env.context[
            "multicurrency_revaluation_report_options"
        ]["date"]["date_to"],
        required=True,
    )
    reversal_date = fields.Date(required=True)
    expense_provision_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Expense Account",
        compute="_compute_accounting_values",
        inverse="_inverse_expense_provision_account_id",
        compute_sudo=True,
        readonly=False,
        required=True,
    )
    income_provision_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Income Account",
        compute="_compute_accounting_values",
        inverse="_inverse_income_provision_account_id",
        compute_sudo=True,
        readonly=False,
        required=True,
    )
    preview_data = fields.Text(compute="_compute_preview_data")
    show_warning_move_id = fields.Many2one(
        comodel_name="account.move",
        compute="_compute_show_warning_move_id",
    )

    @api.model
    @_debug.perf.timed
    def default_get(self, fields):
        _debug.lifecycle("default_get", records=self)
        rec = super().default_get(fields)
        if "reversal_date" in fields:
            report_options = self.env.context[
                "multicurrency_revaluation_report_options"
            ]
            rec["reversal_date"] = Date.to_date(
                report_options["date"]["date_to"]
            ) + relativedelta(days=1)
        if (
            not self.env.context.get("revaluation_no_loop")
            and not self.with_context(revaluation_no_loop=True)._prepare_move_vals()[
                "line_ids"
            ]
        ):
            _debug.logic("revaluation_defaults_rejected", reason="no_adjustment_needed")
            raise UserError(_("No adjustment needed"))
        return rec

    @api.depends(
        "expense_provision_account_id", "income_provision_account_id", "reversal_date"
    )
    @_debug.perf.timed
    def _compute_show_warning_move_id(self):
        for record in self:
            last_move = (
                self.env["account.move.line"]
                .search(  # noqa: E8507 - a transient wizard opened on one company
                    [
                        (
                            "account_id",
                            "in",
                            (
                                record.expense_provision_account_id
                                + record.income_provision_account_id
                            ).ids,
                        ),
                        ("date", "<", record.reversal_date),
                    ],
                    order="date desc",
                    limit=1,
                )
                .move_id
            )
            record.show_warning_move_id = (
                False if last_move.reversed_entry_id else last_move
            )

    @api.depends(
        "expense_provision_account_id",
        "income_provision_account_id",
        "date",
        "journal_id",
    )
    @_debug.perf.timed
    def _compute_preview_data(self):
        preview_columns = [
            {"field": "account_id", "label": _("Account")},
            {"field": "name", "label": _("Label")},
            {"field": "debit", "label": _("Debit"), "class": "text-end text-nowrap"},
            {"field": "credit", "label": _("Credit"), "class": "text-end text-nowrap"},
        ]
        for record in self:
            preview_vals = [
                self.env["account.move"]._move_dict_to_preview_vals(
                    self._prepare_move_vals(), record.company_id.currency_id
                )
            ]
            record.preview_data = json.dumps(
                {
                    "groups_vals": preview_vals,
                    "options": {
                        "columns": preview_columns,
                    },
                }
            )

    @api.depends("company_id")
    def _compute_accounting_values(self):
        for record in self:
            record.journal_id = record.company_id.account_revaluation_journal_id
            record.expense_provision_account_id = (
                record.company_id.account_revaluation_expense_provision_account_id
            )
            record.income_provision_account_id = (
                record.company_id.account_revaluation_income_provision_account_id
            )

    def _inverse_journal_id(self):
        for record in self:
            record.company_id.sudo().account_revaluation_journal_id = record.journal_id

    def _inverse_expense_provision_account_id(self):
        for record in self:
            record.company_id.sudo().account_revaluation_expense_provision_account_id = record.expense_provision_account_id

    def _inverse_income_provision_account_id(self):
        for record in self:
            record.company_id.sudo().account_revaluation_income_provision_account_id = (
                record.income_provision_account_id
            )

    @api.model
    @_debug.perf.timed
    def _prepare_move_vals(self):
        def _get_model_id(parsed_line, selected_model):
            for _dummy, parsed_res_model, parsed_res_id in parsed_line:
                if parsed_res_model == selected_model:
                    return parsed_res_id
            return None

        def _get_adjustment_balance(line):
            for column in line.get("columns"):
                if column.get("expression_label") == "adjustment":
                    return column.get("no_format")
            return None

        report = self.env.ref("account.multicurrency_revaluation_report")
        included_line_id = report.line_ids.filtered(
            lambda l: l.code == "multicurrency_included"
        ).id
        generic_included_line_id = report._get_generic_line_id(
            "account.report.line", included_line_id
        )
        options = {
            **self.env.context["multicurrency_revaluation_report_options"],
            "unfold_all": True,
        }
        report_lines = report._get_lines(options)
        _debug.pipeline(
            "revaluation_report_lines_loaded",
            report=report,
            included_line=included_line_id,
            report_lines=len(report_lines),
        )
        move_lines = []

        for report_line in report._get_unfolded_lines(
            report_lines, generic_included_line_id
        ):
            parsed_line_id = report._parse_line_id(report_line.get("id"))
            balance = _get_adjustment_balance(report_line)
            # parsed_line_id[-1][-2] corresponds to res_model of the current line
            if parsed_line_id[-1][
                -2
            ] == "account.account" and not self.env.company.currency_id.is_zero(
                balance
            ):
                account_id = _get_model_id(parsed_line_id, "account.account")
                currency_id = _get_model_id(parsed_line_id, "res.currency")
                move_lines.append(
                    Command.create(
                        {
                            "name": _(
                                "Provision for %(for_cur)s (1 %(comp_cur)s = %(rate)s %(for_cur)s)",
                                for_cur=self.env["res.currency"]
                                .browse(currency_id)
                                .display_name,
                                comp_cur=self.env.company.currency_id.display_name,
                                rate=options["currency_rates"][str(currency_id)][
                                    "rate"
                                ],
                            ),
                            "debit": max(0, balance),
                            "credit": -balance if balance < 0 else 0,
                            "amount_currency": 0,
                            "currency_id": currency_id,
                            "account_id": account_id,
                        }
                    )
                )
                if balance < 0:
                    move_line_name = _(
                        "Expense Provision for %s",
                        self.env["res.currency"].browse(currency_id).display_name,
                    )
                else:
                    move_line_name = _(
                        "Income Provision for %s",
                        self.env["res.currency"].browse(currency_id).display_name,
                    )
                move_lines.append(
                    Command.create(
                        {
                            "name": move_line_name,
                            "debit": -balance if balance < 0 else 0,
                            "credit": max(0, balance),
                            "amount_currency": 0,
                            "currency_id": currency_id,
                            "account_id": self.expense_provision_account_id.id
                            if balance < 0
                            else self.income_provision_account_id.id,
                        }
                    )
                )

        _debug.pipeline(
            "revaluation_move_lines_built",
            report=report,
            move_lines=len(move_lines),
            adjusted_accounts=len(move_lines) // 2,
        )
        return {
            "ref": _(
                "Foreign currencies adjustment entry as of %s",
                format_date(self.env, self.date),
            ),
            "journal_id": self.journal_id.id,
            "date": self.date,
            "line_ids": move_lines,
        }

    @_debug.perf.timed
    def create_entries(self):
        self.check_singleton()
        move_vals = self._prepare_move_vals()
        _debug.pipeline(
            "create_entries_reversal",
            revaluation=self,
            line_ids_count=len(move_vals["line_ids"]),
            reversal_date=self.reversal_date,
        )
        if move_vals["line_ids"]:
            move = (
                self.env["account.move"]
                .with_context(skip_invoice_sync=True)
                .create(move_vals)
            )
            move.action_post()
            reverse_move = move._reverse_moves(
                default_values_list=[
                    {
                        "ref": _("Reversal of: %s", move.ref),
                    }
                ]
            )
            reverse_move.date = self.reversal_date
            reverse_move.action_post()

            form = self.env.ref("account.view_move_form", False)
            ctx = self.env.context.copy()
            ctx.pop("id", "")
            return {
                "type": "ir.actions.act_window",
                "res_model": "account.move",
                "res_id": move.id,
                "view_mode": "form",
                "view_id": form.id,
                "views": [(form.id, "form")],
                "context": ctx,
            }
        raise UserError(_("No provision needed was found."))
