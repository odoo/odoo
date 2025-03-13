# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models

class HrEmployeeContract(models.Model):
    _name = 'hr.employee.contract'
    _description = "Employee Contract"
    _order = 'date_to'

    name = fields.Char(string='Contract Reference', required=True)
    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To')
    contract_type_id = fields.Many2one('hr.contract.type', "Contract Type")

    employee_id = fields.Many2one('hr.employee')
