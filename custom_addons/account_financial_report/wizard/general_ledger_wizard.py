# Author: Damien Crier
# Author: Julien Coux
# Author: Jordi Ballester
# Copyright 2016 Camptocamp SA
# Copyright 2017 Akretion - Alexis de Lattre
# Copyright 2017 ForgeFlow, S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


import time
from ast import literal_eval

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import date_utils


class GeneralLedgerReportWizard(models.TransientModel):
    """General ledger report wizard."""

    _name = "general.ledger.report.wizard"
    _description = "General Ledger Report Wizard"
    _inherit = "account_financial_report_abstract_wizard"

    date_range_id = fields.Many2one(comodel_name="date.range", string="Date range")
    date_from = fields.Date(required=True, default=lambda self: self._init_date_from())
    date_to = fields.Date(required=True, default=fields.Date.context_today)
    fy_start_date = fields.Date(compute="_compute_fy_start_date")
    target_move = fields.Selection(
        [("posted", "All Posted Entries"), ("all", "All Entries")],
        string="Target Moves",
        required=True,
        default="posted",
    )
    account_ids = fields.Many2many(
        comodel_name="account.account", string="Filter accounts"
    )
    centralize = fields.Boolean(string="Activate centralization", default=True)
    hide_account_at_0 = fields.Boolean(
        string="Hide account ending balance at 0",
        help="Use this filter to hide an account or a partner "
        "with an ending balance at 0. "
        "If partners are filtered, "
        "debits and credits totals will not match the trial balance.",
    )
    receivable_accounts_only = fields.Boolean()
    payable_accounts_only = fields.Boolean()
    partner_ids = fields.Many2many(
        comodel_name="res.partner",
        string="Filter partners",
        default=lambda self: self._default_partners(),
    )
    account_journal_ids = fields.Many2many(
        comodel_name="account.journal", string="Filter journals"
    )
    cost_center_ids = fields.Many2many(
        comodel_name="account.analytic.account", string="Filter cost centers"
    )
    only_one_unaffected_earnings_account = fields.Boolean(
        readonly=True,
        default=lambda self: self._only_one_unaffected_earnings_account(),
    )
    foreign_currency = fields.Boolean(
        string="Show foreign currency",
        help="Display foreign currency for move lines, unless "
        "account currency is not setup through chart of accounts "
        "will display initial and final balance in that currency.",
        default=lambda self: self._default_foreign_currency(),
    )
    account_code_from = fields.Many2one(
        comodel_name="account.account",
        help="Starting account in a range",
    )
    account_code_to = fields.Many2one(
        comodel_name="account.account",
        help="Ending account in a range",
    )
    grouped_by = fields.Selection(
        selection=[("none", "None"), ("partners", "Partners"), ("taxes", "Taxes")],
        default="partners",
        required=True,
    )
    show_cost_center = fields.Boolean(
        string="Show Analytic Account",
        default=True,
    )
    domain = fields.Char(
        string="Journal Items Domain",
        default=[],
        help="This domain will be used to select specific domain for Journal " "Items",
    )

    def _get_account_move_lines_domain(self):
        domain = literal_eval(self.domain) if self.domain else []
        return domain

    @api.onchange("account_code_from", "account_code_to")
    def on_change_account_range(self):
        if (
            self.account_code_from
            and self.account_code_from.code.isdigit()
            and self.account_code_to
            and self.account_code_to.code.isdigit()
        ):
            start_range = int(self.account_code_from.code)
            end_range = int(self.account_code_to.code)
            domain = [("code", ">=", start_range), ("code", "<=", end_range)]
            if self.company_id:
                domain.append(("company_ids", "in", self.company_id.ids))
            self.account_ids = self.env["account.account"].search(domain)

    def _init_date_from(self):
        """set start date to begin of current year if fiscal year running"""
        today = fields.Date.context_today(self)
        company = self.company_id or self.env.company
        last_fsc_month = company.fiscalyear_last_month
        last_fsc_day = company.fiscalyear_last_day

        if (
            today.month < int(last_fsc_month)
            or today.month == int(last_fsc_month)
            and today.day <= last_fsc_day
        ):
            return time.strftime("%Y-01-01")
        else:
            return False

    def _default_foreign_currency(self):
        return self.env.user.has_group("base.group_multi_currency")

    @api.depends("date_from")
    def _compute_fy_start_date(self):
        for wiz in self:
            if wiz.date_from:
                date_from, date_to = date_utils.get_fiscal_year(
                    wiz.date_from,
                    day=self.company_id.fiscalyear_last_day,
                    month=int(self.company_id.fiscalyear_last_month),
                )
                wiz.fy_start_date = date_from
            else:
                wiz.fy_start_date = False

    def _only_one_unaffected_earnings_account(self):
        count = self.env["account.account"].search_count(
            [
                ("account_type", "=", "equity_unaffected"),
                ("company_ids", "in", [self.company_id.id or self.env.company.id]),
            ]
        )
        return count == 1

    @api.onchange("company_id")
    def onchange_company_id(self):
        """Handle company change."""
        self.only_one_unaffected_earnings_account = (
            self._only_one_unaffected_earnings_account()
        )
        if (
            self.company_id
            and self.date_range_id.company_id
            and self.date_range_id.company_id != self.company_id
        ):
            self.date_range_id = False
        if self.company_id and self.account_journal_ids:
            self.account_journal_ids = self.account_journal_ids.filtered(
                lambda p: p.company_id == self.company_id or not p.company_id
            )
        if self.company_id and self.partner_ids:
            self.partner_ids = self.partner_ids.filtered(
                lambda p: p.company_id == self.company_id or not p.company_id
            )
        if self.company_id and self.account_ids:
            if self.receivable_accounts_only or self.payable_accounts_only:
                self.onchange_type_accounts_only()
            else:
                self.account_ids = self.account_ids.filtered(
                    lambda a: self.company_id in a.company_ids
                )
        if self.company_id and self.cost_center_ids:
            self.cost_center_ids = self.cost_center_ids.filtered(
                lambda c: c.company_id == self.company_id
            )
        res = {
            "domain": {
                "account_ids": [],
                "partner_ids": [],
                "account_journal_ids": [],
                "cost_center_ids": [],
                "date_range_id": [],
            }
        }
        if not self.company_id:
            return res
        else:
            res["domain"]["account_ids"] += [("company_ids", "in", self.company_id.ids)]
            res["domain"]["account_journal_ids"] += [
                ("company_id", "=", self.company_id.id)
            ]
            res["domain"]["partner_ids"] += self._get_partner_ids_domain()
            res["domain"]["cost_center_ids"] += [
                ("company_id", "=", self.company_id.id)
            ]
            res["domain"]["date_range_id"] += [
                "|",
                ("company_id", "=", self.company_id.id),
                ("company_id", "=", False),
            ]
        return res

    @api.onchange("date_range_id")
    def onchange_date_range_id(self):
        """Handle date range change."""
        if self.date_range_id:
            self.date_from = self.date_range_id.date_start
            self.date_to = self.date_range_id.date_end

    @api.constrains("company_id", "date_range_id")
    def _check_company_id_date_range_id(self):
        for rec in self.sudo():
            if (
                rec.company_id
                and rec.date_range_id.company_id
                and rec.company_id != rec.date_range_id.company_id
            ):
                raise ValidationError(
                    self.env._(
                        "The Company in the General Ledger Report Wizard and in "
                        "Date Range must be the same."
                    )
                )

    @api.onchange("receivable_accounts_only", "payable_accounts_only")
    def onchange_type_accounts_only(self):
        """Handle receivable/payable accounts only change."""
        if self.receivable_accounts_only or self.payable_accounts_only:
            domain = [("company_ids", "in", [self.company_id.id])]
            if self.receivable_accounts_only and self.payable_accounts_only:
                domain += [
                    ("account_type", "in", ("asset_receivable", "liability_payable"))
                ]
            elif self.receivable_accounts_only:
                domain += [("account_type", "=", "asset_receivable")]
            elif self.payable_accounts_only:
                domain += [("account_type", "=", "liability_payable")]
            self.account_ids = self.env["account.account"].search(domain)
        else:
            self.account_ids = None

    @api.onchange("partner_ids")
    def onchange_partner_ids(self):
        """Handle partners change."""
        if self.partner_ids:
            self.receivable_accounts_only = self.payable_accounts_only = True
        else:
            self.receivable_accounts_only = self.payable_accounts_only = False

    @api.depends("company_id")
    def _compute_unaffected_earnings_account(self):
        for record in self:
            record.unaffected_earnings_account = self.env["account.account"].search(
                [
                    ("account_type", "=", "equity_unaffected"),
                    ("company_ids", "in", [record.company_id.id]),
                ]
            )

    unaffected_earnings_account = fields.Many2one(
        comodel_name="account.account",
        compute="_compute_unaffected_earnings_account",
        store=True,
    )

    def _print_report(self, report_type):
        self.ensure_one()
        data = self._prepare_report_general_ledger()
        if report_type == "xlsx":
            report_name = "a_f_r.report_general_ledger_xlsx"
        else:
            report_name = "account_financial_report.general_ledger"
        return (
            self.env["ir.actions.report"]
            .search(
                [("report_name", "=", report_name), ("report_type", "=", report_type)],
                limit=1,
            )
            .report_action(self, data=data)
        )

    def _prepare_report_general_ledger(self):
        self.ensure_one()
        return {
            "wizard_id": self.id,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "only_posted_moves": self.target_move == "posted",
            "hide_account_at_0": self.hide_account_at_0,
            "foreign_currency": self.foreign_currency,
            "company_id": self.company_id.id,
            "account_ids": self.account_ids.ids,
            "partner_ids": self.partner_ids.ids,
            "grouped_by": self.grouped_by,
            "cost_center_ids": self.cost_center_ids.ids,
            "show_cost_center": self.show_cost_center,
            "journal_ids": self.account_journal_ids.ids,
            "centralize": self.centralize,
            "fy_start_date": self.fy_start_date,
            "unaffected_earnings_account": self.unaffected_earnings_account.id,
            "account_financial_report_lang": self.env.lang,
            "domain": self._get_account_move_lines_domain(),
        }

    def _export(self, report_type):
        """Default export is PDF."""
        return self._print_report(report_type)

    def _get_atr_from_dict(self, obj_id, data, key):
        try:
            return data[obj_id][key]
        except KeyError:
            return data[str(obj_id)][key]
