# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Employee(models.Model):

    _inherit = "hr.employee"

    manager = fields.Boolean(string='Is a Manager')
    medic_exam = fields.Date(string='Medical Examination Date')
    place_of_birth = fields.Char('Place of Birth')
    children = fields.Integer(string='Number of Children')
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
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    name = fields.Char('Contract Reference', required=True, track_visibility='onchange')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, track_visibility='onchange')
    department_id = fields.Many2one('hr.department', track_visibility='onchange', string="Department")
    type_id = fields.Many2one('hr.contract.type', string='Contract Type', required=True,
                              default=lambda self: self.env['hr.contract.type'].search([], limit=1),
                              track_visibility='onchange')
    job_id = fields.Many2one('hr.job', string='Job Title', track_visibility='onchange')
    date_start = fields.Date('Start Date', required=True, default=fields.Date.today, track_visibility='onchange')
    date_end = fields.Date('End Date', track_visibility='onchange')
    trial_date_start = fields.Date('Trial Start Date', default=fields.Date.today, track_visibility='onchange')
    trial_date_end = fields.Date('Trial End Date', track_visibility='onchange')
    working_hours = fields.Many2one('resource.calendar', string='Working Schedule', track_visibility='onchange')
    wage = fields.Float('Wage', digits=(16, 2), required=True, track_visibility='onchange', help="Basic Salary of the employee")
    advantages = fields.Text('Advantages', track_visibility='onchange')
    notes = fields.Text('Notes', track_visibility='onchange')
    permit_no = fields.Char('Work Permit No', track_visibility='onchange')
    visa_no = fields.Char('Visa No', track_visibility='onchange')
    visa_expire = fields.Date('Visa Expire Date', track_visibility='onchange')
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

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        if self.filtered(lambda c: c.date_end and c.date_start > c.date_end):
            raise ValidationError(_('Contract start date must be less than contract end date.'))

    @api.multi
    def set_as_pending(self):
        return self.write({'state': 'pending'})

    @api.multi
    def set_as_close(self):
        return self.write({'state': 'close'})

    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values and self.state == 'pending':
            return 'hr_contract.mt_contract_pending'
        elif 'state' in init_values and self.state == 'close':
            return 'hr_contract.mt_contract_close'
        return super(Contract, self)._track_subtype(init_values)
