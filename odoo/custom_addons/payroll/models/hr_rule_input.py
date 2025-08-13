# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrRuleInput(models.Model):
    _name = "hr.rule.input"
    _description = "Salary Rule Input"

    name = fields.Char(string="Description", required=True)
    code = fields.Char(
        required=True, help="The code that can be used in the salary rules"
    )
    input_id = fields.Many2one(
        "hr.salary.rule", string="Salary Rule Input", required=True
    )
