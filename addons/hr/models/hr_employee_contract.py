# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models

class HrEmployeeContract(models.Model):
    _name = 'hr.employee.contract'
    _description = "Employee Contract"
    _order = 'date_from desc'

    name = fields.Char(string='Contract Name', required=True)
    index = fields.Integer(string='Index', compute='_compute_index', store=True)
    reference = fields.Char(string='Reference', compute='_compute_reference', readonly=True)
    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To')
    contract_type_id = fields.Many2one('hr.contract.type', "Contract Type")

    employee_id = fields.Many2one('hr.employee')

    @api.depends('employee_id')
    def _compute_index(self):
        for contract in self:
            employee_contracts = contract.env['hr.employee.contract'].search([
                ('employee_id', '=', contract.employee_id),
                ('create_date', '<', contract.create_date)
            ], order='create_date')
            contract.index = len(employee_contracts) + 1  # TODO: this does not work if we delete contracts

    @api.depends('employee_id.legal_name', 'index')
    def _compute_reference(self):
        for contract in self:
            contract.reference = contract.employee_id.legal_name + '/' + f'{contract.index:06d}'
