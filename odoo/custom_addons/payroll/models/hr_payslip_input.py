# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrPayslipInput(models.Model):
    _name = "hr.payslip.input"
    _description = "Payslip Input"
    _order = "payslip_id, sequence"

    name = fields.Char(string="Description", required=True)
    payslip_id = fields.Many2one(
        "hr.payslip", string="Pay Slip", required=True, ondelete="cascade", index=True
    )
    sequence = fields.Integer(required=True, index=True, default=10)
    code = fields.Char(
        required=True, help="The code that can be used in the salary rules"
    )
    amount = fields.Float(
        help="It is used in computation. For e.g. A rule for sales having "
        "1% commission of basic salary for per product can defined in "
        "expression like result = inputs.SALEURO.amount * contract.wage*0.01."
    )
    amount_qty = fields.Float(
        "Amount Quantity", help="It can be used in computation for other inputs"
    )
    contract_id = fields.Many2one(
        "hr.contract",
        string="Contract",
        required=True,
        help="The contract for which applied this input",
    )
