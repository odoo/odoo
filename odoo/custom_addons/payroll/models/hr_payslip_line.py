# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrPayslipLine(models.Model):
    _name = "hr.payslip.line"
    _inherit = "hr.salary.rule"
    _description = "Payslip Line"
    _order = "contract_id, sequence"

    slip_id = fields.Many2one(
        "hr.payslip", string="Pay Slip", required=True, ondelete="cascade"
    )
    date_from = fields.Date("Date From", related="slip_id.date_from", store=True)
    payslip_run_id = fields.Many2one(
        "hr.payslip.run", related="slip_id.payslip_run_id", string="Payslip Batch"
    )
    child_ids = fields.One2many(
        "hr.payslip.line", "parent_line_id", string="Child Payslip Lines"
    )
    parent_line_id = fields.Many2one(
        "hr.payslip.line",
        string="Parent Payslip Line",
        compute="_compute_parent_line_id",
        store=True,
    )
    salary_rule_id = fields.Many2one("hr.salary.rule", string="Rule", required=True)
    employee_id = fields.Many2one("hr.employee", string="Employee", required=True)
    contract_id = fields.Many2one(
        "hr.contract", string="Contract", required=True, index=True
    )
    rate = fields.Float(string="Rate (%)", digits="Payroll Rate", default=100.0)
    amount = fields.Float(digits="Payroll")
    quantity = fields.Float(digits="Payroll", default=1.0)
    total = fields.Float(
        compute="_compute_total",
        digits="Payroll",
        store=True,
    )
    allow_edit_payslip_lines = fields.Boolean(
        "Allow editing", compute="_compute_allow_edit_payslip_lines"
    )

    def _compute_allow_edit_payslip_lines(self):
        self.allow_edit_payslip_lines = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("payroll.allow_edit_payslip_lines")
        )

    @api.depends("parent_rule_id", "contract_id", "slip_id")
    def _compute_parent_line_id(self):
        for line in self:
            if line.parent_rule_id:
                parent_line = line.slip_id.line_ids.filtered(
                    lambda record, line=line: record.salary_rule_id
                    == line.parent_rule_id
                    and record.contract_id == line.contract_id
                    and record.slip_id == line.slip_id
                )
                if parent_line and len(parent_line) > 1:
                    raise UserError(
                        _("Recursion error. Only one line should be parent of %s")
                        % line.parent_rule_id.name
                    )
                line.parent_line_id = (
                    parent_line[0].id if len(parent_line) == 1 else False
                )
            else:
                line.parent_line_id = False

    @api.depends("quantity", "amount", "rate")
    def _compute_total(self):
        for line in self:
            line.total = float(line.quantity) * line.amount * line.rate / 100

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if "employee_id" not in values or "contract_id" not in values:
                payslip = self.env["hr.payslip"].browse(values.get("slip_id"))
                values["employee_id"] = (
                    values.get("employee_id") or payslip.employee_id.id
                )
                values["contract_id"] = (
                    values.get("contract_id")
                    or payslip.contract_id
                    and payslip.contract_id.id
                )
                if not values["contract_id"]:
                    raise UserError(
                        _("You must set a contract to create a payslip line.")
                    )
        return super().create(vals_list)
