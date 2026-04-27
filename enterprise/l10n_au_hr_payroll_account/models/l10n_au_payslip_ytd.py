from datetime import date
from dateutil.relativedelta import relativedelta
from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import create_index


class L10nAUPayslipYTD(models.Model):
    _name = "l10n_au.payslip.ytd"
    _description = "YTD Opening Balances"

    name = fields.Char(string="Description", compute="_compute_name", required=True)
    start_date = fields.Date(string="Fiscal Start Date", inverse="_fiscal_start_date", required=True, help="The date should be the start of the fiscal year.")
    employee_id = fields.Many2one("hr.employee", string="Employee", required=True)
    company_id = fields.Many2one(related="employee_id.company_id", required=True)
    currency_id = fields.Many2one(related="company_id.currency_id")
    code = fields.Char(related="rule_id.code")
    struct_id = fields.Many2one(
        "hr.payroll.structure",
        compute="_compute_struct_id",
        store=True,
        readonly=False,
        string="Payroll Structure",
        required=True,
    )
    rule_id = fields.Many2one("hr.salary.rule", string="Salary Rule", required=True)
    requires_inputs = fields.Boolean("Requires Inputs")
    l10n_au_payslip_ytd_input_ids = fields.One2many("l10n_au.payslip.ytd.input", "l10n_au_payslip_ytd_id", string="Inputs")
    start_value = fields.Monetary(string="Start Value")
    ytd_amount = fields.Float(string="YTD Amount", compute="_compute_total_ytd")
    finalised = fields.Boolean(string="Finalised")

    ####################################################
    # HELPER METHODS
    ####################################################

    @api.model
    def _get_start_date(self, start_date: date):
        fiscal_year_last_month = int(self.env.company.fiscalyear_last_month)
        start_year = start_date.year
        # Start is previous year
        if start_date.month <= fiscal_year_last_month:
            start_year -= 1
        if fiscal_year_last_month == 12:
            fiscal_year_last_month = 0
        return start_date.replace(day=1, month=fiscal_year_last_month + 1, year=start_year)

    @api.model
    def _is_past_fiscal_year(self, start_date):
        return self._get_start_date(start_date) < self._get_start_date(fields.Date.today())

    ####################################################
    # ORM METHODS
    ####################################################

    def _auto_init(self):
        super()._auto_init()
        create_index(self._cr, 'l10n_au_payslip_ytd_employee_date', 'l10n_au_payslip_ytd', ["employee_id", "start_date"])

    def _fiscal_start_date(self):
        for rec in self:
            if rec.start_date:
                rec.start_date = rec._get_start_date(rec.start_date)

    @api.depends("l10n_au_payslip_ytd_input_ids", "l10n_au_payslip_ytd_input_ids.ytd_amount", "start_value")
    def _compute_total_ytd(self):
        for rec in self:
            if rec.requires_inputs:
                rec.ytd_amount = sum(rec.l10n_au_payslip_ytd_input_ids.mapped("ytd_amount"))
            else:
                rec.ytd_amount = rec.start_value

    @api.depends("employee_id", "rule_id")
    def _compute_name(self):
        for rec in self:
            rec.name = f"{rec.employee_id.name} - {rec.rule_id.name}"

    @api.depends("employee_id")
    def _compute_struct_id(self):
        for rec in self:
            rec.struct_id = rec.employee_id.contract_id.structure_type_id.default_struct_id

    @api.constrains("employee_id", "rule_id", "start_value")
    def _check_unique_rule(self):
        for rec in self:
            if not rec.finalised:
                if self.search_count([
                    ("employee_id", "=", rec.employee_id.id),
                    ("rule_id", "=", rec.rule_id.id),
                    ("id", "!=", rec.id),
                    ("start_date", "=", rec.start_date),
                ]):
                    raise UserError(_("A record for %(rule)s rule for %(employee)s already exists for the selected fiscal year. "
                        "Please update that before creating new one.", rule=rec.rule_id.name, employee=rec.employee_id.name))
            start_date = self._get_start_date(rec.start_date)
            end_date = start_date + relativedelta(years=1, days=-1)
            if self.env["hr.payslip"].search_count([
                ("employee_id", "=", rec.employee_id.id),
                ("state", "in", ("done", "paid")),
                ("date_from", "<=", end_date),
                ("date_from", ">=", start_date)]):
                raise UserError(_("You can't create or update YTD opening balances for %s, because there are "
                                  "validated payslips for this employee during the selected fiscal year.", (rec.employee_id.name)))

    def write(self, vals):
        if any(finalised for finalised in self.mapped("finalised")) and vals.get("finalised", True):
            raise UserError(_("YTD Balances cannot be updated once finalised."))
        is_negative = self.filtered(lambda x: x.rule_id.code in ["WORKPLACE.GIVING", "WITHHOLD.TOTAL"])
        if self in is_negative and "start_value" in vals:
            vals["start_value"] = -abs(vals["start_value"])
        return super().write(vals)

    def action_add_inputs(self):
        self.ensure_one()
        return self._get_records_action(
            name="Add ytd inputs",
            view_id="l10n_au_hr_payroll_account.l10n_au_payslip_ytd_form",
            target="new",
        )

    def button_finalise(self):
        """ Mark previous fiscal year imported YTD records as finalised after updating
            This allows the records to be marked as finalised without submitting to ATO.
        """
        self.write({
            "finalised": True
        })

    @api.model
    def _get_ote_total(self, employee_ids, start_date):
        start_date = self._get_start_date(start_date)
        ote_input_type_ids = self.env["hr.payslip.input.type"].search([
            ("l10n_au_superannuation_treatment", "=", "ote")
        ]).ids
        ote_work_entry_type_ids = self.env["hr.work.entry.type"].search([
            ("l10n_au_is_ote", "=", True)
        ]).ids
        opening_balances = self.env["l10n_au.payslip.ytd.input"].read_group([
                ("l10n_au_payslip_ytd_id.employee_id", "in", employee_ids),
                ("l10n_au_payslip_ytd_id.start_date", "=", start_date),
                '|',
                    '&',
                        ('res_model', '=', 'hr.payslip.input.type'),
                        ('res_id', 'in', ote_input_type_ids),
                    '&',
                        ('res_model', '=', 'hr.work.entry.type'),
                        ('res_id', 'in', ote_work_entry_type_ids)
            ],
            ["ytd_amount:sum"],
            ["employee_id"],
        )
        opening_balances = {r["employee_id"][0]: r["ytd_amount"] for r in opening_balances}
        res = defaultdict(float, opening_balances)
        rtw_lines = self.search_read([
                ("employee_id", "in", employee_ids),
                ("start_date", "=", start_date),
                ("rule_id.code", "=", "RTW")
            ],
            ["ytd_amount", "employee_id"], load="")
        for rtw in rtw_lines:
            res[rtw["employee_id"]] += rtw["ytd_amount"]
        return res


class L10nAUPayslipYTDInput(models.Model):
    _name = "l10n_au.payslip.ytd.input"
    _description = "YTD Opening Balances Inputs"

    l10n_au_payslip_ytd_id = fields.Many2one("l10n_au.payslip.ytd", required=True, ondelete="cascade")
    name = fields.Char(string="Description", compute="_compute_name", store=True)
    employee_id = fields.Many2one(related="l10n_au_payslip_ytd_id.employee_id")
    res_id = fields.Many2oneReference('Input', model_field='res_model', readonly=True)
    res_model = fields.Selection(
        selection=[
            ("hr.payslip.input.type", "Other Input"),
            ("hr.work.entry.type", "Work Entry Type"),
        ],
        string="Model",
        readonly=True,
    )
    ytd_amount = fields.Float(string="YTD Amount")

    @api.depends("res_id")
    def _compute_name(self):
        for rec in self:
            if rec.res_model == "hr.payslip.input.type":
                rec.name = rec.input_type.name
            elif rec.res_model == "hr.work.entry.type":
                rec.name = rec.work_entry_type.name

    @property
    def work_entry_type(self):
        work_entry_ids = self.filtered(lambda l: l.res_model == "hr.work.entry.type").mapped("res_id")
        return self.env["hr.work.entry.type"].browse(work_entry_ids)

    @property
    def input_type(self):
        input_ids = self.filtered(lambda l: l.res_model == "hr.payslip.input.type").mapped("res_id")
        return self.env["hr.payslip.input.type"].browse(input_ids)

    def write(self, vals):
        # Should be negative
        is_negative = self.filtered(lambda x: x.input_type.code in [
            "SS.O", "CHILD_SUPPORT_GARNISHEE"
        ] or x.name in [
            "Salary Sacrificed Workplace Giving",
            "Child Support Deduction",
        ])
        if self in is_negative and "ytd_amount" in vals:
            vals["ytd_amount"] = -abs(vals["ytd_amount"])
        return super().write(vals)
