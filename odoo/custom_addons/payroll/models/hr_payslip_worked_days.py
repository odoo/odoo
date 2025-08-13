# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrPayslipWorkedDays(models.Model):
    _name = "hr.payslip.worked_days"
    _description = "Payslip Worked Days"
    _order = "payslip_id, sequence"

    name = fields.Char(string="Description", required=True)
    payslip_id = fields.Many2one(
        "hr.payslip", string="Pay Slip", required=True, ondelete="cascade", index=True
    )
    sequence = fields.Integer(required=True, index=True, default=10)
    code = fields.Char(
        required=True, help="The code that can be used in the salary rules"
    )
    number_of_days = fields.Float(string="Number of Days")
    number_of_hours = fields.Float(string="Number of Hours")
    contract_id = fields.Many2one(
        "hr.contract",
        string="Contract",
        required=True,
        help="The contract for which applied this input",
    )
