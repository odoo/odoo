# Part of Odoo. See LICENSE file for full copyright and licensing details.
import math

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.addons.l10n_au_hr_payroll.models.hr_contract import CESSATION_TYPE_CODE
from odoo.exceptions import UserError


class TerminationPaymentWizard(models.TransientModel):
    _name = "l10n_au.termination.payment"
    _description = "Termination Payment"

    employee_id = fields.Many2one("hr.employee")
    contract_id = fields.Many2one(
        "hr.contract",
        compute="_compute_contract_id"
    )
    contract_end_date = fields.Date(
        "Contract End Date",
        default=fields.Date.today
    )
    cessation_type_code = fields.Selection(CESSATION_TYPE_CODE, required=True)
    unused_annual_leaves = fields.Float(
        string="Annual Leaves",
        compute="_compute_unused_leaves",
    )
    unused_long_service_leaves = fields.Float(
        string="Long Service Leaves",
        compute="_compute_unused_leaves",
    )
    termination_type = fields.Selection([
        ("normal", "Non-Genuine Redundancy"),
        ("genuine", "Genuine Redundancy"),
    ], required=True, default="normal", string="Termination Type")

    @api.model
    def default_get(self, field_list=None):
        if self.env.company.country_id.code != 'AU':
            raise UserError(_("You must be logged in an Australian company to use that feature."))
        return super().default_get(field_list)

    @api.depends('employee_id', 'contract_end_date')
    def _compute_contract_id(self):
        for record in self:
            contracts = record.employee_id._get_contracts(
                date_from=record.contract_end_date,
                date_to=record.contract_end_date,
            ) or record.employee_id._get_incoming_contracts(
                date_from=record.contract_end_date,
                date_to=record.contract_end_date,
            )
            record.contract_id = contracts and contracts[0]

    @api.depends("employee_id", "contract_id", "contract_end_date")
    def _compute_unused_leaves(self):
        for record in self:
            leaves = self.env["hr.leave.allocation"].search([
                ("state", "=", "validate"),
                ("holiday_status_id.l10n_au_leave_type", "in", ['annual', 'long_service']),
                ("employee_id", "=", self.employee_id.id),
                ("date_from", "<=", record.contract_id.date_end or record.contract_end_date),
            ])

            annual_leaves = leaves.filtered(lambda l: l.holiday_status_id.l10n_au_leave_type == 'annual')
            long_service_leaves = leaves - annual_leaves

            record.unused_annual_leaves = sum(annual_leaves.mapped("number_of_days")) - sum(annual_leaves.mapped("leaves_taken"))
            record.unused_long_service_leaves = sum(long_service_leaves.mapped("number_of_days")) - sum(long_service_leaves.mapped("leaves_taken"))

    def button_terminate(self):
        self.ensure_one()
        if not self.contract_id:
            raise UserError(_("You cannot terminate an employee if there is no contract running at this time."))

        self.contract_id.write({
            'l10n_au_cessation_type_code':  self.cessation_type_code,
            'date_end':  self.contract_end_date,
        })
        # Implement New payslip create
        payslip = self.env["hr.payslip"].create({
            "name": f"Termination Salary Slip - {self.employee_id.name}",
            "employee_id": self.employee_id.id,
            "contract_id": self.contract_id.id,
            "date_from": self._get_termination_payslip_period_start(),
            "date_to": self.contract_end_date,
            "l10n_au_termination_type": self.termination_type})

        return {
            "name": "Termination",
            "type": "ir.actions.act_window",
            "res_model": "hr.payslip",
            "views": [[False, "form"]],
            "view_mode": "form",
            "res_id": payslip.id
        }

    @api.model
    def _get_termination_payslip_period_start(self):
        self.ensure_one()
        schedule = self.contract_id.schedule_pay or self.contract_id.structure_type_id.default_schedule_pay
        date_to = self.contract_end_date
        week_start = self.env["res.lang"]._lang_get(self.env.user.lang).week_start

        if schedule == 'quarterly':
            current_year_quarter = math.ceil(date_to.month / 3)
            date_from = date_to.replace(day=1, month=(current_year_quarter - 1) * 3 + 1)
        elif schedule == 'semi-annually':
            is_second_half = math.floor((date_to.month - 1) / 6)
            date_from = date_to.replace(day=1, month=7) if is_second_half else date_to.replace(day=1, month=1)
        elif schedule == 'annually':
            date_from = date_to.replace(day=1, month=1)
        elif schedule == 'weekly':
            week_day = date_to.weekday()
            date_from = date_to + relativedelta(days=-week_day)
        elif schedule == 'bi-weekly':
            week = int(date_to.strftime("%U") if week_start == '7' else date_to.strftime("%W"))
            week_day = date_to.weekday()
            is_second_week = week % 2 == 0
            date_from = date_to + relativedelta(days=-week_day - 7 * int(is_second_week))
        elif schedule == 'bi-monthly':
            current_year_slice = math.ceil(date_to.month / 2)
            date_from = date_to.replace(day=1, month=(current_year_slice - 1) * 2 + 1)
        else:  # if not handled, put the monthly behaviour
            date_from = date_to.replace(day=1)

        if self.contract_id.date_start and date_from < self.contract_id.date_start:
            date_from = self.contract_id.date_start
        return date_from
