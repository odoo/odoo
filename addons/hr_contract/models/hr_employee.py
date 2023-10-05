# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from pytz import UTC
from datetime import date, datetime, time

from odoo import api, fields, models
from odoo.osv import expression

class EmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    first_contract_date = fields.Date(compute='_compute_manager_only_fields', search='_search_first_contract_date')

    def _get_manager_only_fields(self):
        return super()._get_manager_only_fields() + ['first_contract_date']

    def _search_first_contract_date(self, operator, value):
        employees = self.env['hr.employee'].sudo().search([('id', 'child_of', self.env.user.employee_id.ids), ('first_contract_date', operator, value)])
        return [('id', 'in', employees.ids)]


class EmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    @api.model
    def _get_new_hire_field(self):
        return 'first_contract_date'


class Employee(models.Model):
    _inherit = "hr.employee"

    vehicle = fields.Char(string='Company Vehicle', groups="hr.group_hr_user")
    contract_ids = fields.One2many('hr.contract', 'employee_id', string='Employee Contracts')
    contract_id = fields.Many2one(
        'hr.contract', string='Current Contract', groups="hr.group_hr_user",
        domain="[('company_id', '=', company_id), ('employee_id', '=', id)]", help='Current contract of the employee')
    calendar_mismatch = fields.Boolean(related='contract_id.calendar_mismatch')
    contracts_count = fields.Integer(compute='_compute_contracts_count', string='Contract Count')
    contract_warning = fields.Boolean(string='Contract Warning', store=True, compute='_compute_contract_warning', groups="hr.group_hr_user")
    first_contract_date = fields.Date(compute='_compute_first_contract_date', groups="hr.group_hr_user", store=True)

    def _get_first_contracts(self):
        self.ensure_one()
        contracts = self.sudo().contract_ids.filtered(lambda c: c.state != 'cancel')
        if self.env.context.get('before_date'):
            contracts = contracts.filtered(lambda c: c.date_start <= self.env.context['before_date'])
        return contracts

    def _get_first_contract_date(self, no_gap=True):
        self.ensure_one()

        def remove_gap(contracts):
            # We do not consider a gap of more than 4 days to be a same occupation
            # contracts are considered to be ordered correctly
            if not contracts:
                return self.env['hr.contract']
            if len(contracts) == 1:
                return contracts
            current_contract = contracts[0]
            older_contracts = contracts[1:]
            current_date = current_contract.date_start
            for i, other_contract in enumerate(older_contracts):
                # Consider current_contract.date_end being false as an error and cut the loop
                gap = (current_date - (other_contract.date_end or date(2100, 1, 1))).days
                current_date = other_contract.date_start
                if gap >= 4:
                    return older_contracts[0:i] + current_contract
            return older_contracts + current_contract

        contracts = self._get_first_contracts().sorted('date_start', reverse=True)
        if no_gap:
            contracts = remove_gap(contracts)
        return min(contracts.mapped('date_start')) if contracts else False

    @api.depends('contract_ids.state', 'contract_ids.date_start')
    def _compute_first_contract_date(self):
        for employee in self:
            employee.first_contract_date = employee._get_first_contract_date()

    @api.depends('contract_id', 'contract_id.state', 'contract_id.kanban_state')
    def _compute_contract_warning(self):
        for employee in self:
            employee.contract_warning = not employee.contract_id or employee.contract_id.kanban_state == 'blocked' or employee.contract_id.state != 'open'

    def _compute_contracts_count(self):
        # read_group as sudo, since contract count is displayed on form view
        contract_histories = self.env['hr.contract.history'].sudo().search([('employee_id', 'in', self.ids)])
        for employee in self:
            contract_history = contract_histories.filtered(lambda ch: ch.employee_id == employee)
            employee.contracts_count = contract_history.contract_count

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
        return self.search(['|', ('active', '=', True), ('active', '=', False)])._get_contracts(date_from, date_to, states=states)

    def _get_unusual_days(self, date_from, date_to=None):
        employee_contracts = self.env['hr.contract'].sudo().search([
            ('state', '!=', 'cancel'),
            ('employee_id', '=', self.id),
            ('date_start', '<=', date_to),
            '|',
            ('date_end', '=', False),
            ('date_end', '>=', date_from),
        ])
        if not employee_contracts:
            return super()._get_unusual_days(date_from, date_to)
        unusual_days = {}
        date_from_date = datetime.strptime(date_from, '%Y-%m-%d %H:%M:%S').date()
        date_to_date = datetime.strptime(date_to, '%Y-%m-%d %H:%M:%S').date() if date_to else None
        for contract in employee_contracts:
            tmp_date_from = max(date_from_date, contract.date_start)
            tmp_date_to = min(date_to_date, contract.date_end) if contract.date_end else date_to_date
            unusual_days.update(contract.resource_calendar_id._get_unusual_days(
                datetime.combine(fields.Date.from_string(tmp_date_from), time.min).replace(tzinfo=UTC),
                datetime.combine(fields.Date.from_string(tmp_date_to), time.max).replace(tzinfo=UTC)
            ))
        return unusual_days

    def _get_calendar_attendances(self, date_from, date_to):
        self.ensure_one()
        valid_contracts = self.sudo()._get_contracts(date_from, date_to, states=['open', 'close'])
        if not valid_contracts:
            return super()._get_calendar_attendances(date_from, date_to)
        return valid_contracts.resource_calendar_id.get_work_duration_data(date_from, date_to)

    def write(self, vals):
        res = super().write(vals)
        if vals.get('contract_id'):
            for employee in self:
                employee.resource_calendar_id.transfer_leaves_to(employee.contract_id.resource_calendar_id, employee.resource_id)
                if employee.resource_calendar_id:
                    employee.resource_calendar_id = employee.contract_id.resource_calendar_id
        return res

    def action_open_contract(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id('hr_contract.action_hr_contract')
        action['views'] = [(False, 'form')]
        if not self.contract_ids:
            action['context'] = {
                'default_employee_id': self.id,
            }
            action['target'] = 'new'
            return action

        target_contract = self.contract_id
        if target_contract:
            action['res_id'] = target_contract.id
            return action

        target_contract = self.contract_ids.filtered(lambda c: c.state == 'draft')
        if target_contract:
            action['res_id'] = target_contract[0].id
            return action

        action['res_id'] = self.contract_ids[0].id
        return action
