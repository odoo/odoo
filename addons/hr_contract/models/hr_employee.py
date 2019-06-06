# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Employee(models.Model):
    _inherit = "hr.employee"

    medic_exam = fields.Date(string='Medical Examination Date', groups="hr.group_hr_user")
    vehicle = fields.Char(string='Company Vehicle', groups="hr.group_hr_user")
    contract_ids = fields.One2many('hr.contract', 'employee_id', string='Employee Contracts')
    contract_id = fields.Many2one('hr.contract', string='Current Contract',
        groups="hr.group_hr_user", help='Current contract of the employee')
    contracts_count = fields.Integer(compute='_compute_contracts_count', string='Contract Count')

    def _compute_contracts_count(self):
        # read_group as sudo, since contract count is displayed on form view
        contract_data = self.env['hr.contract'].sudo().read_group([('employee_id', 'in', self.ids)], ['employee_id'], ['employee_id'])
        result = dict((data['employee_id'][0], data['employee_id_count']) for data in contract_data)
        for employee in self:
            employee.contracts_count = result.get(employee.id, 0)

    def _get_contracts(self, date_from, date_to, states=['open', 'pending']):
        """
        Returns the contracts of the employee between date_from and date_to
        """
        return self.env['hr.contract'].search([
            '&', '&', '&',
            ('employee_id', 'in', self.ids),
            ('state', 'in', states),
            ('date_start', '<=', date_to),
            '|', ('date_end', '=', False), ('date_end', '>=', date_from)
        ])

    @api.model
    def _get_all_contracts(self, date_from, date_to, states=['open', 'pending']):
        """
        Returns the contracts of all employees between date_from and date_to
        """
        return self.search([])._get_contracts(date_from, date_to, states=states)
