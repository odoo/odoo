# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class L10nCHISMutationLine(models.Model):
    _name = 'hr.employee.is.line'
    _description = 'IS Entry / Withdrawals / Mutations'

    employee_id = fields.Many2one('hr.employee', required=True)
    reason = fields.Char()
    valid_as_of = fields.Date(required=True)
    correction_date = fields.Date(required=True)
    payslips_to_correct = fields.Many2many('hr.payslip', domain="[('employee_id', '=', employee_id), ('state', 'in', ['done', 'paid'])]")
