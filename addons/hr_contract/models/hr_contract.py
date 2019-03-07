# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv import expression


class Employee(models.Model):
    _inherit = "hr.employee"

    medic_exam = fields.Date(string='Medical Examination Date', groups="hr.group_hr_user")
    vehicle = fields.Char(string='Company Vehicle', groups="hr.group_hr_user")
    contract_ids = fields.One2many('hr.contract', 'employee_id', string='Employee Contracts')
    contract_id = fields.Many2one('hr.contract', string='Current Contract', help='Current contract of the employee')
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
        # a contract is valid if it ends between the given dates
        clause_1 = ['&', ('date_end', '<=', date_to), ('date_end', '>=', date_from)]
        # OR if it starts between the given dates
        clause_2 = ['&', ('date_start', '<=', date_to), ('date_start', '>=', date_from)]
        # OR if it starts before the date_from and finish after the date_end (or never finish)
        clause_3 = ['&', ('date_start', '<=', date_from), '|', ('date_end', '=', False), ('date_end', '>=', date_to)]
        clause_final = expression.AND([
            [('employee_id', 'in', self.ids), ('state', 'in', states)],
            expression.OR([clause_1, clause_2, clause_3])])
        return self.env['hr.contract'].search(clause_final)

    @api.model
    def _get_all_contracts(self, date_from, date_to, states=['open', 'pending']):
        """
        Returns the contracts of all employees between date_from and date_to
        """
        return self.search([])._get_contracts(date_from, date_to, states=states)


class Contract(models.Model):
    _name = 'hr.contract'
    _description = 'Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Contract Reference', required=True)
    active = fields.Boolean(default=True)
    employee_id = fields.Many2one('hr.employee', string='Employee')
    department_id = fields.Many2one('hr.department', string="Department")
    job_id = fields.Many2one('hr.job', string='Job Position')
    date_start = fields.Date('Start Date', required=True, default=fields.Date.today,
        help="Start date of the contract.")
    date_end = fields.Date('End Date',
        help="End date of the contract (if it's a fixed-term contract).")
    trial_date_end = fields.Date('End of Trial Period',
        help="End date of the trial period (if there is one).")
    resource_calendar_id = fields.Many2one(
        'resource.calendar', 'Working Schedule',
        default=lambda self: self.env['res.company']._company_default_get().resource_calendar_id.id)
    wage = fields.Monetary('Wage', digits=(16, 2), required=True, tracking=True, help="Employee's monthly gross wage.")
    advantages = fields.Text('Advantages')
    notes = fields.Text('Notes')
    state = fields.Selection([
        ('draft', 'New'),
        ('incoming', 'Incoming'),
        ('open', 'Running'),
        ('pending', 'To Renew'),
        ('close', 'Expired'),
        ('cancel', 'Cancelled')
    ], string='Status', group_expand='_expand_states',
       tracking=True, help='Status of the contract', default='draft')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one(string="Currency", related='company_id.currency_id', readonly=True)
    permit_no = fields.Char('Work Permit No', related="employee_id.permit_no", readonly=False)
    visa_no = fields.Char('Visa No', related="employee_id.visa_no", readonly=False)
    visa_expire = fields.Date('Visa Expire Date', related="employee_id.visa_expire", readonly=False)
    reported_to_secretariat = fields.Boolean('Social Secretariat',
        help='Green this button when the contract information has been transfered to the social secretariat.')

    def _expand_states(self, states, domain, order):
        return [key for key, val in type(self).state.selection]

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.job_id = self.employee_id.job_id
            self.department_id = self.employee_id.department_id
            self.resource_calendar_id = self.employee_id.resource_calendar_id

    @api.constrains('employee_id', 'state', 'date_start', 'date_end')
    def _check_current_contract(self):
        """ Two contracts in state [incoming | pending | open | close] cannot overlap """
        for contract in self.filtered(lambda c: c.state not in ['draft', 'cancel']):
            domain = [
                ('id', '!=', contract.id),
                ('employee_id', '=', contract.employee_id.id),
                ('state', 'in', ['incoming', 'pending', 'open', 'close']),
            ]

            if not contract.date_end:
                start_domain = []
                end_domain = ['|', ('date_end', '>=', contract.date_start), ('date_end', '=', False)]
            else:
                start_domain = [('date_start', '<=', contract.date_end)]
                end_domain = ['|', ('date_end', '>', contract.date_start), ('date_end', '=', False)]

            domain = expression.AND([domain, start_domain, end_domain])
            if self.search_count(domain):
                raise ValidationError(_('An employee can only have one contract at the same time. (Excluding Draft and Cancelled contracts)'))

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        if self.filtered(lambda c: c.date_end and c.date_start > c.date_end):
            raise ValidationError(_('Contract start date must be earlier than contract end date.'))

    @api.model
    def update_state(self):
        self.search([
            ('state', '=', 'open'),
            '|',
            '&',
            ('date_end', '<=', fields.Date.to_string(date.today() + relativedelta(days=7))),
            ('date_end', '>=', fields.Date.to_string(date.today() + relativedelta(days=1))),
            '&',
            ('visa_expire', '<=', fields.Date.to_string(date.today() + relativedelta(days=60))),
            ('visa_expire', '>=', fields.Date.to_string(date.today() + relativedelta(days=1))),
        ]).write({
            'state': 'pending'
        })

        self.search([
            ('state', 'in', ('open', 'pending')),
            '|',
            ('date_end', '<=', fields.Date.to_string(date.today() + relativedelta(days=1))),
            ('visa_expire', '<=', fields.Date.to_string(date.today() + relativedelta(days=1))),
        ]).write({
            'state': 'close'
        })

        self.search([('state', '=', 'incoming'), ('date_start', '<=', fields.Date.to_string(date.today())),]).write({
            'state': 'open'
        })
        return True

    @api.multi
    def write(self, vals):
        if vals.get('state') == 'open':
            for contract in self:
                contract.employee_id.contract_id = contract
        return super(Contract, self).write(vals)

    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values and self.state == 'pending':
            return self.env.ref('hr_contract.mt_contract_pending')
        elif 'state' in init_values and self.state == 'close':
            return self.env.ref('hr_contract.mt_contract_close')
        return super(Contract, self)._track_subtype(init_values)
