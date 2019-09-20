# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

from odoo.osv import expression

class Contract(models.Model):
    _name = 'hr.contract'
    _description = 'Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Contract Reference', required=True)
    active = fields.Boolean(default=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', tracking=True, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    department_id = fields.Many2one('hr.department', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", string="Department")
    job_id = fields.Many2one('hr.job', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", string='Job Position')
    date_start = fields.Date('Start Date', required=True, default=fields.Date.today,
        help="Start date of the contract.")
    date_end = fields.Date('End Date',
        help="End date of the contract (if it's a fixed-term contract).")
    trial_date_end = fields.Date('End of Trial Period',
        help="End date of the trial period (if there is one).")
    resource_calendar_id = fields.Many2one(
        'resource.calendar', 'Working Schedule',
        default=lambda self: self.env.company.resource_calendar_id.id, copy=False,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    wage = fields.Monetary('Wage', required=True, tracking=True, help="Employee's monthly gross wage.")
    advantages = fields.Text('Advantages')
    notes = fields.Text('Notes')
    state = fields.Selection([
        ('draft', 'New'),
        ('open', 'Running'),
        ('close', 'Expired'),
        ('cancel', 'Cancelled')
    ], string='Status', group_expand='_expand_states', copy=False,
       tracking=True, help='Status of the contract', default='draft')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    """
        kanban_state:
            * draft + green = "Incoming" state (will be set as Open once the contract has started)
            * open + red = "Pending" state (will be set as Closed once the contract has ended)
            * red = Shows a warning on the employees kanban view
    """
    kanban_state = fields.Selection([
        ('normal', 'Grey'),
        ('done', 'Green'),
        ('blocked', 'Red')
    ], string='Kanban State', default='normal', tracking=True, copy=False)
    currency_id = fields.Many2one(string="Currency", related='company_id.currency_id', readonly=True)
    permit_no = fields.Char('Work Permit No', related="employee_id.permit_no", readonly=False)
    visa_no = fields.Char('Visa No', related="employee_id.visa_no", readonly=False)
    visa_expire = fields.Date('Visa Expire Date', related="employee_id.visa_expire", readonly=False)
    hr_responsible_id = fields.Many2one('res.users', 'HR Responsible', tracking=True,
        help='Person responsible for validating the employee\'s contracts.')
    calendar_mismatch = fields.Boolean(compute='_compute_calendar_mismatch')

    @api.depends('employee_id.resource_calendar_id', 'resource_calendar_id')
    def _compute_calendar_mismatch(self):
        for contract in self:
            contract.calendar_mismatch = contract.resource_calendar_id != contract.employee_id.resource_calendar_id

    def _expand_states(self, states, domain, order):
        return [key for key, val in type(self).state.selection]


    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.job_id = self.employee_id.job_id
            self.department_id = self.employee_id.department_id
            self.resource_calendar_id = self.employee_id.resource_calendar_id
            self.company_id = self.employee_id.company_id

    @api.constrains('employee_id', 'state', 'kanban_state', 'date_start', 'date_end')
    def _check_current_contract(self):
        """ Two contracts in state [incoming | open | close] cannot overlap """
        for contract in self.filtered(lambda c: c.state not in ['draft', 'cancel'] or c.state == 'draft' and c.kanban_state == 'done'):
            domain = [
                ('id', '!=', contract.id),
                ('employee_id', '=', contract.employee_id.id),
                '|',
                    ('state', 'in', ['open', 'close']),
                    '&',
                        ('state', '=', 'draft'),
                        ('kanban_state', '=', 'done') # replaces incoming
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
            'kanban_state': 'blocked'
        })

        self.search([
            ('state', '=', 'open'),
            '|',
            ('date_end', '<=', fields.Date.to_string(date.today() + relativedelta(days=1))),
            ('visa_expire', '<=', fields.Date.to_string(date.today() + relativedelta(days=1))),
        ]).write({
            'state': 'close'
        })

        self.search([('state', '=', 'draft'), ('kanban_state', '=', 'done'), ('date_start', '<=', fields.Date.to_string(date.today())),]).write({
            'state': 'open'
        })
        return True

    def _assign_open_contract(self):
        for contract in self:
            contract.employee_id.sudo().write({'contract_id': contract.id})

    def write(self, vals):
        res = super(Contract, self).write(vals)
        if vals.get('state') == 'open':
            self._assign_open_contract()

        calendar = vals.get('resource_calendar_id')
        if calendar and (self.state == 'open' or (self.state == 'draft' and self.kanban_state == 'done')):
            self.mapped('employee_id').write({'resource_calendar_id': calendar})

        if 'state' in vals and 'kanban_state' not in vals:
            self.write({'kanban_state': 'normal'})

        return res

    @api.model
    def create(self, vals):
        contracts = super(Contract, self).create(vals)
        if vals.get('state') == 'open':
            contracts._assign_open_contract()
        open_contracts = contracts.filtered(lambda c: c.state == 'open' or c.state == 'draft' and c.kanban_state == 'done')
        # sync contract calendar -> calendar employee
        for contract in open_contracts.filtered(lambda c: c.resource_calendar_id):
            contract.employee_id.resource_calendar_id = contract.resource_calendar_id
        return contracts

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values and self.state == 'open' and 'kanban_state' in init_values and self.kanban_state == 'blocked':
            return self.env.ref('hr_contract.mt_contract_pending')
        elif 'state' in init_values and self.state == 'close':
            return self.env.ref('hr_contract.mt_contract_close')
        return super(Contract, self)._track_subtype(init_values)
