# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrEmployeeContractWizard(models.TransientModel):
    _name = 'hr.employee.contract.wizard'
    _description = 'Employee Contract wizard'

    def _get_default_employee_id(self):
        active_id = self.env.context.get('active_id', False)
        if active_id:
            return self.env['hr.employee'].search([('id', '=', active_id)])
        return self.env['hr.employee']

    employee_id = fields.Many2one('hr.employee', default=_get_default_employee_id, readonly=True)
    name = fields.Char(string='Contract Name', required=True)
    date_from = fields.Date(required=True, default=lambda self: fields.Date.today())
    date_to = fields.Date()

    overlapping_contract_ids = fields.Many2one('hr.employee.contract',
                                               compute='_compute_overlapping_contract_ids')

    @api.depends('date_from', 'date_to')
    def _compute_overlapping_contract_ids(self):
        self.contract_to_split = self.employee_id._get_contracts(self.date_from)

    def action_create_new_contract(self):
        # if self.contract_to_split.date_from == self.date_from:
        #     raise UserError(_('Another contract was started on that date'))
        new_contract = self.env['hr.employee.contract'].create([{
            'employee_id': self.employee_id.id,
            'name': self.name,
            'date_from': self.date_from,
            'date_to': self.date_to,
        }])
        # self.contract_to_split.date_to = self.date_from - timedelta(days=1)
        self.employee_id.contract_ids |= new_contract
        self.employee_id.selected_contract_id = new_contract

        # return {'type': 'ir.actions.client', 'tag': 'reload'}
