# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Employee(models.Model):

    _inherit = "hr.employee"

    manager = fields.Boolean(string='Is a Manager')
    medic_exam = fields.Date(string='Medical Examination Date')
    place_of_birth = fields.Char('Place of Birth')
    children = fields.Integer(string='Number of Children')
    # TODO make a many2one
    vehicle = fields.Char(string='Company Vehicle')
    vehicle_distance = fields.Integer(string='Home-Work Dist.', help="In kilometers")
    contract_ids = fields.One2many('hr.contract', 'employee_id', string='Contracts')
    contract_id = fields.Many2one('hr.contract', compute='_compute_contract_id', string='Current Contract', help='Latest contract of the employee')
    contracts_count = fields.Integer(compute='_compute_contracts_count', string='Contracts')

    def _compute_contract_id(self):
        """ get the lastest contract """
        Contract = self.env['hr.contract']
        for employee in self:
            employee.contract_id = Contract.search([('employee_id', '=', employee.id)], order='date_start desc', limit=1)

    def _compute_contracts_count(self):
        # read_group as sudo, since contract count is displayed on form view
        contract_data = self.env['hr.contract'].sudo().read_group([('employee_id', 'in', self.ids)], ['employee_id'], ['employee_id'])
        result = dict((data['employee_id'][0], data['employee_id_count']) for data in contract_data)
        for employee in self:
            employee.contracts_count = result.get(employee.id, 0)


class ContractType(models.Model):

    _name = 'hr.contract.type'
    _description = 'Contract Type'
    _order = 'sequence, id'

    name = fields.Char(string='Contract Type', required=True)
    sequence = fields.Integer(help="Gives the sequence when displaying a list of Contract.", default=10)


class Contract(models.Model):

    _name = 'hr.contract'
    _description = 'Contract'
    _inherit = ['mail.thread']

    name = fields.Char('Contract Reference', required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    department_id = fields.Many2one('hr.department', string="Department")
    type_id = fields.Many2one('hr.contract.type', string="Contract Type", required=True, default=lambda self: self.env['hr.contract.type'].search([], limit=1))
    job_id = fields.Many2one('hr.job', string='Job Title')
    date_start = fields.Date('Start Date', required=True, default=fields.Date.today)
    date_end = fields.Date('End Date')
    trial_date_start = fields.Date('Trial Start Date')
    trial_date_end = fields.Date('Trial End Date')
    resource_calendar_id = fields.Many2one(
        'resource.calendar', 'Working Schedule',
        default=lambda self: self.env['res.company']._company_default_get().resource_calendar_id.id)
    wage = fields.Float('Wage', digits=(16, 2), required=True, help="Basic Salary of the employee")
    advantages = fields.Text('Advantages')
    notes = fields.Text('Notes')
    permit_no = fields.Char('Work Permit No')
    visa_no = fields.Char('Visa No')
    visa_expire = fields.Date('Visa Expire Date')
    state = fields.Selection([
        ('draft', 'New'),
        ('open', 'Running'),
        ('pending', 'To Renew'),
        ('close', 'Expired'),
    ], string='Status', track_visibility='onchange', help='Status of the contract', default='draft')

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.job_id = self.employee_id.job_id
            self.department_id = self.employee_id.department_id
            self.resource_calendar_id = self.employee_id.resource_calendar_id

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        if self.filtered(lambda c: c.date_end and c.date_start > c.date_end):
            raise ValidationError(_('Contract start date must be less than contract end date.'))

    @api.model
    def create(self, vals):
        if vals.get('state', False) == 'open':
            if self.env['hr.contract'].search_count([('employee_id', '=', self.employee_id.id), ('state', '=', 'open')]):
                raise ValidationError(_("An employee can't have more than one open contract!"))
        return super(Contract, self).create(vals)

    def write(self, vals):
        if vals.get('state', False) == 'open':
            for contract in self:
                if self.env['hr.contract'].search_count([('employee_id', '=', contract.employee_id.id), ('state', '=', 'open')]):
                    raise ValidationError(_("An employee can't have more than one open contract!"))
        return super(Contract, self).write(vals)

    @api.model
    def update_to_pending(self):
        soon_expired_contracts = self.search([
            ('state', '=', 'open'),
            '|',
            ('date_end', '>=', fields.Date.to_string(date.today() + relativedelta(days=-7))),
            ('visa_expire', '>=', fields.Date.to_string(date.today() + relativedelta(days=-60)))
        ])
        return soon_expired_contracts.write({
            'state': 'pending'
        })

    @api.model
    def update_to_close(self):
        expired_contracts = self.search([
            '|',
            ('date_end', '>=', fields.Date.to_string(date.today() + relativedelta(days=1))),
            ('visa_expire', '>=', fields.Date.to_string(date.today() + relativedelta(days=1)))
        ])
        return expired_contracts.write({
            'state': 'close'
        })

    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values and self.state == 'pending':
            return 'hr_contract.mt_contract_pending'
        elif 'state' in init_values and self.state == 'close':
            return 'hr_contract.mt_contract_close'
        return super(Contract, self)._track_subtype(init_values)
