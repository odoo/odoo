# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta

from odoo import api, Command, fields, models, _
from odoo.tools import date_utils, format_list
from odoo.exceptions import ValidationError


class L10nAUPayrollFinalisationWizard(models.TransientModel):
    _name = "l10n_au.payroll.finalisation.wizard"
    _description = "STP Finalisation"

    def _default_fiscal_year(self):
        return self._get_fiscal_year_selection()[0][0]

    name = fields.Char("Name", compute="_compute_name", required=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, string="Company", readonly=True)
    abn = fields.Char("ABN", related="company_id.vat")
    branch_code = fields.Char(related="company_id.l10n_au_branch_code")
    bms_id = fields.Char(related="company_id.l10n_au_bms_id")
    date_deadline = fields.Date("Deadline Date", default=lambda self: fields.Date.today(), required=True)
    is_eofy = fields.Boolean("EOFY Declaration", default=False)
    date_start = fields.Date("Date Start", compute="_compute_date_period", required=True)
    date_end = fields.Date("Date End", compute="_compute_date_period", required=True)
    fiscal_year = fields.Selection(selection="_get_fiscal_year_selection", string="Fiscal Year", default=_default_fiscal_year, required=True)
    l10n_au_payroll_finalisation_emp_ids = fields.One2many(
        "l10n_au.payroll.finalisation.wizard.emp",
        "l10n_au_payroll_finalisation_id",
        compute="_compute_all_employees",
        store=True,
        readonly=False,
        string="Employees",
    )
    responsible_user_id = fields.Many2one("res.users", string="Responsible User", default=lambda self: self.env.company.l10n_au_stp_responsible_id.user_id, required=True)
    finalisation = fields.Boolean("Finalisation", default=True, help="Set it to false to un-finalise the employees.")

    def _is_past_fiscal_year(self):
        return self.env["l10n_au.payslip.ytd"]._is_past_fiscal_year(self.date_start)

    def _get_fiscal_year_selection(self):
        today = fields.Date.today()
        selection = []
        fiscal_start, fiscal_end = date_utils.get_fiscal_year(today, self.env.company.fiscalyear_last_day, int(self.env.company.fiscalyear_last_month))
        for year in range(5):
            start = fiscal_start - date_utils.get_timedelta(year, "year")
            end = fiscal_end - date_utils.get_timedelta(year, "year")
            selection.append((fields.Date.to_string(start), f"{start.strftime('%Y')}/{end.strftime('%y')}"))
        return selection

    @api.depends("date_start", "date_end", "finalisation", "is_eofy", "l10n_au_payroll_finalisation_emp_ids")
    def _compute_name(self):
        for rec in self:
            if not rec.finalisation:
                rec.name = _("Amendment of Prior Finalisation - %s", (dict(self._get_fiscal_year_selection())[rec.fiscal_year]))
            if rec.is_eofy and rec.finalisation:
                rec.name = _("EOFY Finalisation - %s", (dict(self._get_fiscal_year_selection())[rec.fiscal_year]))
            elif not rec.is_eofy:
                employees = rec.l10n_au_payroll_finalisation_emp_ids.employee_id
                message = self.env._("Individual Finalisation") if rec.finalisation else self.env._("Individual Amendment of Prior Finalisation")
                rec.name = "%s - %s" % (message, format_list(self.env, employees.mapped('name')))

    @api.depends("is_eofy", "fiscal_year")
    def _compute_date_period(self):
        for rec in self:
            fiscal_start, fiscal_end = date_utils.get_fiscal_year(fields.Date.to_date(rec.fiscal_year), self.env.company.fiscalyear_last_day, int(self.env.company.fiscalyear_last_month))
            rec.date_start = fiscal_start
            if rec._is_past_fiscal_year():
                rec.date_end = rec.date_start + date_utils.get_timedelta(1, "year") - date_utils.get_timedelta(1, "day")
            else:
                rec.date_end = fiscal_end if rec.is_eofy else fields.Date.today()

    @api.depends("company_id", "is_eofy", "fiscal_year")
    def _compute_all_employees(self):
        for rec in self:
            if not rec.is_eofy:
                continue
            employees_to_add = self._get_employees().filtered(
                lambda emp: emp.id not in rec.l10n_au_payroll_finalisation_emp_ids.employee_id.ids)
            rec.update(
                {
                    "l10n_au_payroll_finalisation_emp_ids": [
                        Command.create({"employee_id": emp.id})
                        for emp in employees_to_add
                    ]
                }
            )

    def _get_employees(self):
        # Returns all employees that can be finalised/unfinalised
        # This includes employees with payslips, or YTD balances
        # for the given period
        self.ensure_one()
        slips = self.env["hr.payslip"].search([
            ("company_id", "=", self.company_id.id),
            ("date_from", ">=", self.date_start),
            ("date_from", "<=", self.date_end),
            ("state", "in", ("done", "paid")),
            ("l10n_au_finalised", "!=", self.finalisation),
            "|",
                ("employee_id.departure_date", ">=", self.date_start),
                ("employee_id.departure_date", "=", False)
        ])
        ytd_balance_ids = self.env["l10n_au.payslip.ytd"].search([
            ("start_date", "=", self.date_start),
            ("finalised", "!=", self.finalisation),
            "|",
                ("employee_id.departure_date", ">=", self.date_start),
                ("employee_id.departure_date", "=", False)
        ])
        return slips.employee_id | ytd_balance_ids.employee_id

    def submit_to_ato(self):
        self.ensure_one()
        if self.is_eofy and not self._is_past_fiscal_year():
            date_deadline = self.date_end + timedelta(days=14)
        else:
            date_deadline = self.date_deadline

        if not self.l10n_au_payroll_finalisation_emp_ids:
            raise ValidationError(_("Please select at least one employee to Finalise / Unfinalise."))

        stp = self.env["l10n_au.stp"].with_context(finalization_deadline=date_deadline).create({
            "name": self.name,
            "company_id": self.company_id.id,
            "payevent_type": "update",
            "is_finalisation": self.finalisation,
            "is_unfinalisation": not self.finalisation,
            "start_date": self.date_start,
            "end_date": self.date_end,
            "l10n_au_stp_emp": [
                Command.create({
                    "employee_id": emp.employee_id.id,
                })
                for emp in self.l10n_au_payroll_finalisation_emp_ids
            ]
        })
        return stp._get_records_action()


class L10nAUPayrollFinalisationEmp(models.TransientModel):
    _name = "l10n_au.payroll.finalisation.wizard.emp"
    _description = "STP Finalisation Employees"

    l10n_au_payroll_finalisation_id = fields.Many2one("l10n_au.payroll.finalisation.wizard", string="Finalisation Wizard", required=True, ondelete="cascade")
    company_id = fields.Many2one(related="l10n_au_payroll_finalisation_id.company_id", string="Company", store=True)
    available_employee_ids = fields.Many2many("hr.employee", compute="_compute_available_employees")
    employee_id = fields.Many2one("hr.employee", string="Employee", required=True, domain="[('id', 'in', available_employee_ids)]")
    contract_id = fields.Many2one("hr.contract", related="employee_id.contract_id", string="Contract", required=True)
    contract_start_date = fields.Date("Contract Start Date", related="contract_id.date_start", required=True)
    contract_end_date = fields.Date("Contract End Date", related="contract_id.date_end")
    contract_active = fields.Boolean("Active", related="employee_id.active")
    ytd_balance_ids = fields.Many2many("l10n_au.payslip.ytd", string="YTD Balances", compute="_compute_amounts_to_report")
    payslip_ids = fields.Many2many("hr.payslip", string="Payslips", compute="_compute_amounts_to_report")

    @api.constrains("employee_id")
    def _check_employee(self):
        for rec in self:
            if not rec.payslip_ids and not rec.ytd_balance_ids:
                if rec.l10n_au_payroll_finalisation_id.finalisation:
                    raise ValidationError(_("There is no data to finalise for employee %s for the selected Fiscal year. "
                                            "Please unfinalise the employee to make any adjustments.", rec.employee_id.name))
                else:
                    raise ValidationError(_("There is no data to unfinalise for employee %s for the selected Fiscal year.", rec.employee_id.name))
            if not rec.employee_id.private_phone:
                raise ValidationError(_("Employee %s has no phone number set.", rec.employee_id.name))

    @api.depends("employee_id",
                 "l10n_au_payroll_finalisation_id.fiscal_year",
                 "l10n_au_payroll_finalisation_id.date_start",
                 "l10n_au_payroll_finalisation_id.date_end",
                 "l10n_au_payroll_finalisation_id.finalisation")
    def _compute_amounts_to_report(self):
        for rec in self:
            rec.ytd_balance_ids = self.env["l10n_au.payslip.ytd"].search(
                [
                    ("employee_id", "=", rec.employee_id.id),
                    ("start_date", "=", rec.l10n_au_payroll_finalisation_id.date_start),
                    ("finalised", "!=", rec.l10n_au_payroll_finalisation_id.finalisation),
                ]
            )
            rec.payslip_ids = self.env["hr.payslip"].search(
                [
                    ("employee_id", "=", rec.employee_id.id),
                    ("date_from", ">=", rec.l10n_au_payroll_finalisation_id.date_start),
                    ("date_from", "<=", rec.l10n_au_payroll_finalisation_id.date_end),
                    ("state", "in", ("done", "paid")),
                    ("l10n_au_finalised", "!=", rec.l10n_au_payroll_finalisation_id.finalisation),
                ]
            )

    @api.depends("company_id", "l10n_au_payroll_finalisation_id.fiscal_year")
    def _compute_available_employees(self):
        for wiz in self.l10n_au_payroll_finalisation_id:
            wiz.l10n_au_payroll_finalisation_emp_ids.available_employee_ids = wiz._get_employees()
