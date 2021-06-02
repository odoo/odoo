# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class Employee(models.Model):
    _inherit = "hr.employee"

    medic_exam = fields.Date(string='Medical Examination Date', groups="hr.group_hr_user")
    vehicle = fields.Char(string='Company Vehicle', groups="hr.group_hr_user")
    contract_ids = fields.One2many('hr.contract', 'employee_id', string='Employee Contracts')
    contract_id = fields.Many2one('hr.contract', string='Current Contract',
        groups="hr.group_hr_user",domain="[('company_id', '=', company_id)]", help='Current contract of the employee')
    calendar_mismatch = fields.Boolean(related='contract_id.calendar_mismatch')
    contracts_count = fields.Integer(compute='_compute_contracts_count', string='Contract Count')
    contract_warning = fields.Boolean(string='Contract Warning', store=True, compute='_compute_contract_warning', groups="hr.group_hr_user")

    @api.depends('contract_id', 'contract_id.state', 'contract_id.kanban_state')
    def _compute_contract_warning(self):
        for employee in self:
            employee.contract_warning = not employee.contract_id or employee.contract_id.kanban_state == 'blocked' or employee.contract_id.state != 'open'

    def _compute_contracts_count(self):
        # read_group as sudo, since contract count is displayed on form view
        contract_data = self.env['hr.contract'].sudo().read_group([('employee_id', 'in', self.ids)], ['employee_id'], ['employee_id'])
        result = dict((data['employee_id'][0], data['employee_id_count']) for data in contract_data)
        for employee in self:
            employee.contracts_count = result.get(employee.id, 0)

    def _get_contracts(self, date_from, date_to, states=['open'], kanban_state=False):
        """
        Returns the contracts of the employee between date_from and date_to
        """
        state_domain = [('state', 'in', states)]
        if kanban_state:
            state_domain = expression.AND([state_domain, [('kanban_state', 'in', kanban_state)]])

        return self.env['hr.contract'].search(
            expression.AND([[('employee_id', 'in', self.ids)],
            state_domain,
            [('date_start', '<=', date_to),
                '|',
                    ('date_end', '=', False),
                    ('date_end', '>=', date_from)]]))

    def _get_incoming_contracts(self, date_from, date_to):
        return self._get_contracts(date_from, date_to, states=['draft'], kanban_state=['done'])

    @api.model
    def _get_all_contracts(self, date_from, date_to, states=['open']):
        """
        Returns the contracts of all employees between date_from and date_to
        """
        return self.search([])._get_contracts(date_from, date_to, states=states)

    def write(self, vals):
        res = super(Employee, self).write(vals)
        if vals.get('contract_id'):
            for employee in self:
                employee.resource_calendar_id.transfer_leaves_to(employee.contract_id.resource_calendar_id, employee.resource_id)
                employee.resource_calendar_id = employee.contract_id.resource_calendar_id
        return res
