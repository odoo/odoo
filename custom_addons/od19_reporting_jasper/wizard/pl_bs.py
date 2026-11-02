# -*- coding: utf-8 -*-
"""Profit & Loss and Balance Sheet (งบกำไรขาดทุน / งบแสดงฐานะทางการเงิน).

Fifth and sixth ported Jasper forms.  Like General Ledger and Trial Balance
they are not bound to a single document: the legacy wizard was opened from the
Accounting reporting menu and selects its own scope (company, accounting
period, target moves, analytic accounts, level of detail).

Odoo 19 adaptations applied to the ported ``jrxml/pl_bs.jrxml``:

* The legacy chart was a recursive tree (``parent_account_id`` /
  ``is_control_account`` split into ``lvl1``..``lvl5``).  Those columns were
  dropped in Odoo 19, so the hierarchy is rebuilt **flat** from
  ``account_account.account_type``: the ``internal_group``
  (``split_part(account_type, '_', 1)`` = asset / liability / equity / income /
  expense) is level 1 and the ``account_type`` is level 2.  The "Level"
  selector then chooses how deep the printed report goes (see ``p_Level``).
* ``account_account.name_th`` / ``name_en`` no longer exist; the label is read
  from the translated ``name`` jsonb (``name->>'th_TH'`` / ``name->>'en_US'``).
* ``account_account.code`` is company dependent and stored in ``code_store``.
* ``account_move.is_year_end`` and the ``dtr_year_end`` table have no Odoo 19
  equivalent.  The Balance Sheet accumulates every posted entry up to the end
  of the period, while the Profit & Loss restarts at January 1st of the year
  (income/expense accounts are reset every year).
* For the Balance Sheet the current year earnings (the ``equity_unaffected``
  account) is fed with the Profit & Loss result computed in Python, exactly as
  the legacy ``is_calculate_from_pl`` flag did.

The legacy ``r_ac_014`` / ``r_ac_015`` report-allow records do not exist in
Odoo 19 and their guard is dropped.
"""
import calendar
from datetime import datetime

from odoo import fields, models
from odoo.tools import SQL

MONTH_LIST = [
    ("1", "มกราคม"),
    ("2", "กุมภาพันธ์"),
    ("3", "มีนาคม"),
    ("4", "เมษายน"),
    ("5", "พฤษภาคม"),
    ("6", "มิถุนายน"),
    ("7", "กรกฎาคม"),
    ("8", "สิงหาคม"),
    ("9", "กันยายน"),
    ("10", "ตุลาคม"),
    ("11", "พฤศจิกายน"),
    ("12", "ธันวาคม"),
]

# The legacy misspelling "Febuary" is kept on purpose so the printed English
# month names match the Odoo 15 output byte for byte.
MONTH_LIST_EN = [
    ("1", "January"),
    ("2", "Febuary"),
    ("3", "March"),
    ("4", "April"),
    ("5", "May"),
    ("6", "June"),
    ("7", "July"),
    ("8", "August"),
    ("9", "September"),
    ("10", "October"),
    ("11", "November"),
    ("12", "December"),
]

# JasperStarter maps ``pl_bs_lvl3`` / ``pl_bs_lvl4`` / ``pl_bs`` onto the
# printed depth because the flat Odoo 19 chart only exposes three semantic
# levels: internal group, account type and account.
LEVEL_SELECTION = [
    ("pl_bs_lvl3", "Level - 3"),
    ("pl_bs_lvl4", "Level - 4"),
    ("pl_bs", "Full"),
]

LEVEL_BY_TEMPLATE = {"pl_bs_lvl3": "3", "pl_bs_lvl4": "4", "pl_bs": "5"}

POSTED_CLAUSE = SQL("AND a.state = 'posted'")


class PlBsReport(models.TransientModel):
    """Shared base for the Profit & Loss and the Balance Sheet wizards."""

    _name = "pl.bs.report"
    _description = "Profit & Loss / Balance Sheet Report"
    _inherit = "od19.jasper.report"

    # ``name`` is the inherited technical rec_name (invisible in the wizard);
    # give it a distinct label so it does not collide with ``rpt_nm``'s
    # "Report Name" (otherwise Odoo logs a duplicate-label warning).
    name = fields.Char(string="Internal Name", default="Financial Statement")
    jasper_file = fields.Char(
        default=lambda self: self.get_jasper_file(__file__, base_name="pl_bs")
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    rpt_nm = fields.Char(string="Report Name", default=lambda self: self._default_rpt_nm())
    rpt_month = fields.Selection(
        MONTH_LIST,
        string="Month",
        required=True,
        default=lambda self: str(fields.Date.context_today(self).month),
    )
    rpt_year = fields.Selection(
        selection=lambda self: self._selection_year(),
        string="Year",
        required=True,
        default=lambda self: str(fields.Date.context_today(self).year),
    )
    rpt_amt_flag = fields.Boolean(string="Only with Movement", default=True)
    target_move = fields.Selection(
        [("posted", "เฉพาะที่ผ่านรายการแล้ว"), ("all", "ทั้งหมด")],
        string="Target Move",
        required=True,
        default="posted",
    )
    # Options shared by both statements; the Balance Sheet adds a third one
    # ("comp") through ``selection_add`` to avoid overriding the selection.
    show_type = fields.Selection(
        [
            ("summ", "แสดงเฉพาะผลรวม"),
            ("drcr", "แสดงพร้อม Dr/Cr"),
        ],
        string="Display Condition",
        required=True,
        default="summ",
    )
    cmp_month = fields.Selection(
        MONTH_LIST,
        string="Month ",
        default=lambda self: str(fields.Date.context_today(self).month),
    )
    cmp_year = fields.Selection(
        selection=lambda self: self._selection_year(),
        string="Year ",
        default=lambda self: str(fields.Date.context_today(self).year - 1),
    )
    report_template = fields.Selection(
        LEVEL_SELECTION, string="Level", required=True, default="pl_bs_lvl3"
    )
    analytic_account_ids = fields.Many2many(
        "account.analytic.account", string="Analytic Account"
    )
    p_language = fields.Selection(
        [("thai", "Thai"), ("english", "English")],
        string="Document Language",
        default="thai",
    )

    # ------------------------------------------------------------------ setup
    def _default_rpt_nm(self):
        return self.env.context.get("rpt_nm", "")

    def _selection_year(self):
        current_year = datetime.now().year
        return [
            (str(year), str(year + 543))
            for year in range(current_year, current_year - 5, -1)
        ]

    def _include_account_types(self):
        """``account_type`` values printed by this statement (overridden)."""
        return []

    def _year_text(self, ce_year, is_english=False):
        """Buddhist-era label for a CE year (or the CE year for English)."""
        label = dict(self._selection_year()).get(str(ce_year), str(ce_year))
        if is_english:
            return str(int(label) - 543)
        return label

    def get_move_criteria(self):
        """Date/state predicate template; ``{year}-{month}-{eom}`` placeholders.

        The Balance Sheet accumulates everything up to the end of the period.
        """
        return "where b.date <= date '{0}-{1}-{2}'"

    def _account_criteria(self):
        account_types = self._include_account_types()
        if not account_types:
            return ""
        return "and aa.account_type in (%s)" % ", ".join(
            "'%s'" % account_type for account_type in account_types
        )

    def _movement_criteria(self, criteria):
        """Legacy "Only with Movement" clause, keyed on ``line``/``cmp``."""
        return {
            "drcr": "%s and (abs(line.balance) > 0 or line.debit > 0 or line.credit > 0)" % criteria,
            "comp": "%s and (abs(line.balance) > 0 or cmp.balance > 0)" % criteria,
            "summ": "%s and (abs(line.balance) > 0)" % criteria,
        }.get(self.show_type, criteria)

    def _company_clause(self):
        """Scope the movement sub-queries to the selected company."""
        return " and b.company_id = %s" % self.company_id.id

    def _analytic_clause(self):
        if not self.analytic_account_ids:
            return ""
        keys = ", ".join("'%s'" % i for i in self.analytic_account_ids.ids)
        return " and b.analytic_distribution ?| array[%s]" % keys

    # ------------------------------------------------------------- lifecycle
    def show_report(self, report_name=False, email_subject=False, email_document_number=False):
        self.jasper_file = self.get_jasper_file(__file__, base_name="pl_bs")
        return super().show_report(report_name, email_subject, email_document_number)

    # ------------------------------------------------------------ parameters
    def get_parameters(self):
        is_english = self.p_language == "english"
        months = MONTH_LIST_EN if is_english else MONTH_LIST
        month_name = dict(months).get(self.rpt_month)
        year_text = self._year_text(self.rpt_year, is_english)
        month_padded = "%02d" % int(self.rpt_month)
        eom = calendar.monthrange(int(self.rpt_year), int(self.rpt_month))[1]

        move_criteria = self.get_move_criteria().format(
            self.rpt_year, month_padded, eom
        )
        if self.target_move == "posted":
            move_criteria = "%s and a.state = 'posted'" % move_criteria

        cmp_label = ""
        # A "where 1 = 0" clause keeps the comparison sub-query valid when the
        # user is not comparing two periods.
        comp_criteria = "where 1 = 0"
        if self.show_type == "comp":
            cmp_month_padded = "%02d" % int(self.cmp_month)
            cmp_eom = calendar.monthrange(int(self.cmp_year), int(self.cmp_month))[1]
            comp_criteria = self.get_move_criteria().format(
                self.cmp_year, cmp_month_padded, cmp_eom
            )
            if self.target_move == "posted":
                comp_criteria = "%s and a.state = 'posted'" % comp_criteria
            cmp_label = "{0} - {1}".format(
                dict(months).get(self.cmp_month),
                self._year_text(self.cmp_year, is_english),
            )

        display = {
            "drcr": {
                "rpt_label": "Balance" if is_english else "ยอดคงเหลือ",
                "cmp_label": "Credit" if is_english else "เครดิต",
                "show_dr_cr": "1",
                "show_comp": "0",
            },
            "comp": {
                "rpt_label": "{0} - {1}".format(month_name, year_text),
                "cmp_label": cmp_label,
                "show_dr_cr": "0",
                "show_comp": "1",
            },
            "summ": {
                "rpt_label": "",
                "cmp_label": "",
                "show_dr_cr": "0",
                "show_comp": "0",
            },
        }.get(self.show_type)

        parms = {
            "report_name": self.rpt_nm or self.name,
            "report_date": ("As at " if is_english else "ณ วันที่ ")
            + "{0} {1} {2}".format(eom, month_name, year_text),
            "report_analytic": "",
            "company_id": "%s" % self.company_id.id,
            "p_Level": LEVEL_BY_TEMPLATE.get(self.report_template, "5"),
            "move_criteria": move_criteria,
            "comp_criteria": comp_criteria,
            "account_criteria": self._account_criteria(),
            "rpt_label": display["rpt_label"],
            "cmp_label": display["cmp_label"],
            "show_dr_cr": display["show_dr_cr"],
            "show_comp": display["show_comp"],
            "pl_dr": "0.00",
            "pl_cr": "0.00",
            "pl_balance": "0.00",
            "pl_cmp_balance": "0.00",
            "p_Print_By": self._legacy_print_by(),
            "p_language": self.p_language,
        }

        analytic_clause = self._analytic_clause()
        company_clause = self._company_clause()
        parms["move_criteria"] = "%s%s" % (parms["move_criteria"], company_clause)
        parms["comp_criteria"] = "%s%s" % (parms["comp_criteria"], company_clause)
        if analytic_clause:
            for keyword in ("move_criteria", "comp_criteria"):
                parms[keyword] = "%s%s" % (parms[keyword], analytic_clause)
            parms["report_analytic"] = "( {0} )".format(
                ", ".join(self.analytic_account_ids.mapped("name"))
            )

        if self.rpt_amt_flag:
            parms["account_criteria"] = self._movement_criteria(parms["account_criteria"])
        return parms


class ProfitLossReport(models.TransientModel):
    """Profit & Loss (งบกำไรขาดทุน)."""

    _name = "profit.loss.report"
    _description = "Profit and Loss Report"
    _inherit = "pl.bs.report"

    name = fields.Char(default="Profit and Loss")
    options = fields.Selection(
        [("total", "ยอดสะสม"), ("period", "กำหนดเอง")],
        string="Options",
        default="total",
    )
    rpt_month = fields.Selection(
        MONTH_LIST,
        string="Month",
        required=False,
        default=lambda self: str(fields.Date.context_today(self).month),
    )
    rpt_year = fields.Selection(
        selection=lambda self: self._selection_year(),
        string="Year",
        required=False,
        default=lambda self: str(fields.Date.context_today(self).year),
    )
    period_start = fields.Date(string="Period")
    period_end = fields.Date(string="Period End")

    def _include_account_types(self):
        return [
            "income",
            "income_other",
            "expense",
            "expense_other",
            "expense_depreciation",
            "expense_direct_cost",
        ]

    def get_move_criteria(self):
        # Profit & Loss accounts are reset every January 1st.
        return "where b.date >= '{0}-01-01' and b.date <= date '{0}-{1}-{2}'"

    def get_parameters(self):
        parms = super().get_parameters()
        is_english = self.p_language == "english"
        months = MONTH_LIST_EN if is_english else MONTH_LIST

        if self.options == "period" and self.period_start and self.period_end:
            move_criteria = "where b.date >= '{0}' and b.date <= '{1}'".format(
                self.period_start, self.period_end
            )
            if self.target_move == "posted":
                move_criteria = "%s and a.state = 'posted'" % move_criteria
            move_criteria = "%s%s" % (move_criteria, self._company_clause())
            analytic_clause = self._analytic_clause()
            if analytic_clause:
                move_criteria = "%s%s" % (move_criteria, analytic_clause)
            parms["move_criteria"] = move_criteria
            parms["comp_criteria"] = "where 1 = 0%s" % self._company_clause()

        if is_english:
            parms["report_name"] = "Profit & Loss Statement"

        if self.options == "total":
            parms["report_date"] = (
                "for the period January to {0} {1}"
                if is_english
                else "ประจำงวด มกราคม - {0} {1}"
            ).format(
                dict(months).get(self.rpt_month),
                self._year_text(self.rpt_year, is_english),
            )
        elif self.options == "period" and self.period_start and self.period_end:
            if is_english:
                pattern = "for the period {0} {1} {2} to {3} {4} {5}"
                year_start = self.period_start.strftime("%Y")
                year_end = self.period_end.strftime("%Y")
            else:
                pattern = "ประจำงวดวันที่ {0} {1} {2} ถึงวันที่ {3} {4} {5}"
                year_start = self._year_text(self.period_start.strftime("%Y"))
                year_end = self._year_text(self.period_end.strftime("%Y"))
            parms["report_date"] = pattern.format(
                self.period_start.day,
                dict(months).get(str(self.period_start.month)),
                year_start,
                self.period_end.day,
                dict(months).get(str(self.period_end.month)),
                year_end,
            )
        return parms


class BalanceSheetReport(models.TransientModel):
    """Balance Sheet (งบแสดงฐานะทางการเงิน)."""

    _name = "balance.sheet.report"
    _description = "Balance Sheet Report"
    _inherit = "pl.bs.report"

    name = fields.Char(default="Balance Sheet")
    show_type = fields.Selection(
        selection_add=[("comp", "แสดงพร้อมเปรียบเทียบ")],
        ondelete={"comp": "set default"},
    )

    def _include_account_types(self):
        return [
            "asset_receivable",
            "asset_cash",
            "asset_current",
            "asset_non_current",
            "asset_prepayments",
            "asset_fixed",
            "liability_payable",
            "liability_credit_card",
            "liability_current",
            "liability_non_current",
            "equity",
            "equity_unaffected",
        ]

    def get_move_criteria(self):
        # The Balance Sheet carries the whole history forward.
        return "where b.date <= date '{0}-{1}-{2}'"

    def _movement_criteria(self, criteria):
        # The current year earnings row stays visible even when the account has
        # no movement of its own: its balance is injected from the P&L result.
        return {
            "drcr": "%s and (aa.account_type = 'equity_unaffected' or abs(line.balance) > 0 or line.debit > 0 or line.credit > 0)" % criteria,
            "comp": "%s and (aa.account_type = 'equity_unaffected' or abs(line.balance) > 0 or cmp.balance > 0)" % criteria,
            "summ": "%s and (aa.account_type = 'equity_unaffected' or abs(line.balance) > 0)" % criteria,
        }.get(self.show_type, criteria)

    def _sum_movement(self, year, month, account_types, sign):
        """Debit/credit/balance of a set of account types up to ``month``."""
        self.ensure_one()
        last_day = calendar.monthrange(int(year), int(month))[1]
        date_from = "%s-01-01" % year
        date_to = "%s-%02d-%02d" % (year, int(month), last_day)
        state_clause = POSTED_CLAUSE if self.target_move == "posted" else SQL("")
        rows = self.env.execute_query_dict(
            SQL(
                """
                SELECT COALESCE(SUM(b.debit), 0) AS debit,
                       COALESCE(SUM(b.credit), 0) AS credit,
                       COALESCE(SUM(b.debit - b.credit) * %s, 0) AS balance
                  FROM account_move a
                  JOIN account_move_line b ON b.move_id = a.id
                  JOIN account_account acc ON acc.id = b.account_id
                 WHERE b.company_id = %s
                   AND b.date >= %s AND b.date <= %s
                   AND acc.account_type IN %s
                   %s
                """,
                sign,
                self.company_id.id,
                date_from,
                date_to,
                tuple(account_types),
                state_clause,
            )
        )
        row = rows[0] if rows else {}
        return (
            row.get("debit") or 0.0,
            row.get("credit") or 0.0,
            row.get("balance") or 0.0,
        )

    def get_parameters(self):
        parms = super().get_parameters()
        if self.p_language == "english":
            parms["report_name"] = "Balance Sheet"

        revenue_types = ("income", "income_other")
        expense_types = (
            "expense",
            "expense_other",
            "expense_depreciation",
            "expense_direct_cost",
        )

        rev_dr, rev_cr, rev_balance = self._sum_movement(
            self.rpt_year, self.rpt_month, revenue_types, -1
        )
        exp_dr, exp_cr, exp_balance = self._sum_movement(
            self.rpt_year, self.rpt_month, expense_types, 1
        )
        parms["pl_dr"] = str(rev_dr - exp_dr)
        parms["pl_cr"] = str(rev_cr - exp_cr)
        parms["pl_balance"] = str(rev_balance - exp_balance)
        parms["pl_cmp_balance"] = "0.00"

        if self.show_type == "comp":
            cmp_rev = self._sum_movement(self.cmp_year, self.cmp_month, revenue_types, -1)
            cmp_exp = self._sum_movement(self.cmp_year, self.cmp_month, expense_types, 1)
            parms["pl_cmp_balance"] = str(cmp_rev[2] - cmp_exp[2])
        return parms
