# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models

class HrEmployeeContract(models.Model):
    _name = 'hr.employee.contract'
    _description = "Employee Contract"
    _order = 'date_from desc'

    name = fields.Char(string='Contract Name', required=True)
    reference = fields.Char(string='Reference', readonly=True)
    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To')
    contract_type_id = fields.Many2one('hr.contract.type', "Contract Type")

    employee_id = fields.Many2one('hr.employee')

    @api.model_create_multi
    def create(self, vals):
        records = super(HrEmployeeContract, self).create(vals)
        for record in records:
            record.reference = record.employee_id.legal_name + '/' + f'{record.employee_id.contract_index:06d}'
            record.employee_id.contract_index += 1
        return records
