# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, time
from pytz import timezone

from odoo import _, api, fields, models
from odoo.osv import expression
from odoo.addons.resource.models.resource import Intervals
from odoo.exceptions import UserError


class Employee(models.Model):
    _inherit = "hr.employee"

    vehicle = fields.Char(string='Company Vehicle', groups="hr.group_hr_user")
    contract_ids = fields.One2many('hr.contract', 'employee_id', string='Employee Contracts')
    contract_id = fields.Many2one(
        'hr.contract', string='Current Contract', groups="hr.group_hr_user",
        domain="[('company_id', '=', company_id), ('employee_id', '=', id)]", help='Current contract of the employee', copy=False)
    calendar_mismatch = fields.Boolean(related='contract_id.calendar_mismatch')
    contracts_count = fields.Integer(compute='_compute_contracts_count', string='Contract Count')
    contract_warning = fields.Boolean(string='Contract Warning', store=True, compute='_compute_contract_warning', groups="hr.group_hr_user")
    first_contract_date = fields.Date(compute='_compute_first_contract_date', groups="hr.group_hr_user", store=True)

    def _get_first_contracts(self):
        self.ensure_one()
        return self.sudo().contract_ids.filtered(lambda c: c.state != 'cancel')

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

    @api.depends('contract_ids.state', 'contract_ids.date_start', 'contract_ids.active')
    def _compute_first_contract_date(self):
        for employee in self:
            employee.first_contract_date = employee._get_first_contract_date()

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
        return self.search(['|', ('active', '=', True), ('active', '=', False)])._get_contracts(date_from, date_to, states=states)

    def _get_expected_attendances(self, date_from, date_to, domain=None):
        self.ensure_one()
        valid_contracts = self.sudo()._get_contracts(date_from, date_to, states=['open', 'close'])
        if not valid_contracts:
            return super()._get_expected_attendances(date_from, date_to, domain)
        employee_tz = timezone(self.tz) if self.tz else None
        duration_data = Intervals()
        for contract in valid_contracts:
            contract_start = datetime.combine(contract.date_start, time.min, employee_tz)
            contract_end = datetime.combine(contract.date_end or date.max, time.max, employee_tz)
            calendar = contract.resource_calendar_id or contract.company_id.resource_calendar_id
            contract_intervals = calendar._work_intervals_batch(
                                    max(date_from, contract_start),
                                    min(date_to, contract_end),
                                    tz=employee_tz,
                                    domain=domain,
                                    resources=self.resource_id)[self.resource_id.id]
            duration_data = duration_data | contract_intervals
        return duration_data


    def write(self, vals):
        res = super(Employee, self).write(vals)
        if vals.get('contract_id'):
            for employee in self:
                employee.resource_calendar_id.transfer_leaves_to(employee.contract_id.resource_calendar_id, employee.resource_id)
                employee.resource_calendar_id = employee.contract_id.resource_calendar_id
        return res
    
    @api.ondelete(at_uninstall=False)
    def _unlink_except_open_contract(self):
        if any(contract.state == 'open' for contract in self.contract_ids):
            raise UserError(_('You cannot delete an employee with a running contract.'))

    def action_open_contract_history(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id('hr_contract.hr_contract_history_view_form_action')
        action['res_id'] = self.id
        return action
