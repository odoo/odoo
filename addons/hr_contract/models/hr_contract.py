# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import threading

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

from odoo.osv import expression

import logging
_logger = logging.getLogger(__name__)


class Contract(models.Model):
    _name = 'hr.contract'
    _description = 'Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Contract Reference', required=True)
    active = fields.Boolean(default=True)
    structure_type_id = fields.Many2one('hr.payroll.structure.type', string="Salary Structure Type")
    employee_id = fields.Many2one('hr.employee', string='Employee', tracking=True, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    department_id = fields.Many2one('hr.department', compute='_compute_employee_contract', store=True, readonly=False,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", string="Department")
    job_id = fields.Many2one('hr.job', compute='_compute_employee_contract', store=True, readonly=False,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", string='Job Position')
    date_start = fields.Date('Start Date', required=True, default=fields.Date.today, tracking=True,
        help="Start date of the contract.", index=True)
    date_end = fields.Date('End Date', tracking=True,
        help="End date of the contract (if it's a fixed-term contract).")
    trial_date_end = fields.Date('End of Trial Period',
        help="End date of the trial period (if there is one).")
    resource_calendar_id = fields.Many2one(
        'resource.calendar', 'Working Schedule', compute='_compute_employee_contract', store=True, readonly=False,
        default=lambda self: self.env.company.resource_calendar_id.id, copy=False, index=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    wage = fields.Monetary('Wage', required=True, tracking=True, help="Employee's monthly gross wage.")
    contract_wage = fields.Monetary('Contract Wage', compute='_compute_contract_wage')
    notes = fields.Html('Notes')
    state = fields.Selection([
        ('draft', 'New'),
        ('open', 'Running'),
        ('close', 'Expired'),
        ('cancel', 'Cancelled')
    ], string='Status', group_expand='_expand_states', copy=False,
       tracking=True, help='Status of the contract', default='draft')
    company_id = fields.Many2one('res.company', compute='_compute_employee_contract', store=True, readonly=False,
        default=lambda self: self.env.company, required=True)
    company_country_id = fields.Many2one('res.country', string="Company country", related='company_id.country_id', readonly=True)
    country_code = fields.Char(related='company_country_id.code', readonly=True)
    contract_type_id = fields.Many2one('hr.contract.type', "Contract Type")

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
    visa_expire = fields.Date('Visa Expiration Date', related="employee_id.visa_expire", readonly=False)
    hr_responsible_id = fields.Many2one('res.users', 'HR Responsible', tracking=True,
        help='Person responsible for validating the employee\'s contracts.')
    calendar_mismatch = fields.Boolean(compute='_compute_calendar_mismatch')
    first_contract_date = fields.Date(related='employee_id.first_contract_date')

    @api.depends('employee_id.resource_calendar_id', 'resource_calendar_id')
    def _compute_calendar_mismatch(self):
        for contract in self:
            contract.calendar_mismatch = contract.resource_calendar_id != contract.employee_id.resource_calendar_id

    def _expand_states(self, states, domain, order):
        return [key for key, val in self._fields['state'].selection]

    @api.depends('employee_id')
    def _compute_employee_contract(self):
        for contract in self.filtered('employee_id'):
            contract.job_id = contract.employee_id.job_id
            contract.department_id = contract.employee_id.department_id
            contract.resource_calendar_id = contract.employee_id.resource_calendar_id
            contract.company_id = contract.employee_id.company_id

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            structure_types = self.env['hr.payroll.structure.type'].search([
                '|',
                ('country_id', '=', self.company_id.country_id.id),
                ('country_id', '=', False)])
            if structure_types:
                self.structure_type_id = structure_types[0]
            elif self.structure_type_id not in structure_types:
                self.structure_type_id = False

    @api.onchange('structure_type_id')
    def _onchange_structure_type_id(self):
        if self.structure_type_id.default_resource_calendar_id:
            self.resource_calendar_id = self.structure_type_id.default_resource_calendar_id

    @api.constrains('employee_id', 'state', 'kanban_state', 'date_start', 'date_end')
    def _check_current_contract(self):
        """ Two contracts in state [incoming | open | close] cannot overlap """
        for contract in self.filtered(lambda c: (c.state not in ['draft', 'cancel'] or c.state == 'draft' and c.kanban_state == 'done') and c.employee_id):
            domain = [
                ('id', '!=', contract.id),
                ('employee_id', '=', contract.employee_id.id),
                ('company_id', '=', contract.company_id.id),
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
                raise ValidationError(
                    _(
                        'An employee can only have one contract at the same time. (Excluding Draft and Cancelled contracts).\n\nEmployee: %(employee_name)s',
                        employee_name=contract.employee_id.name
                    )
                )

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for contract in self:
            if contract.date_end and contract.date_start > contract.date_end:
                raise ValidationError(_(
                    'Contract %(contract)s: start date (%(start)s) must be earlier than contract end date (%(end)s).',
                    contract=contract.name, start=contract.date_start, end=contract.date_end,
                ))

    @api.model
    def update_state(self):
        from_cron = 'from_cron' in self.env.context
        contracts = self.search([
            ('state', '=', 'open'), ('kanban_state', '!=', 'blocked'),
            '|',
            '&',
            ('date_end', '<=', fields.Date.to_string(date.today() + relativedelta(days=7))),
            ('date_end', '>=', fields.Date.to_string(date.today() + relativedelta(days=1))),
            '&',
            ('visa_expire', '<=', fields.Date.to_string(date.today() + relativedelta(days=60))),
            ('visa_expire', '>=', fields.Date.to_string(date.today() + relativedelta(days=1))),
        ])

        for contract in contracts:
            contract.activity_schedule(
                'mail.mail_activity_data_todo', contract.date_end,
                _("The contract of %s is about to expire.", contract.employee_id.name),
                user_id=contract.hr_responsible_id.id or self.env.uid)

        if contracts:
            contracts._safe_write_for_cron({'kanban_state': 'blocked'}, from_cron)

        contracts_to_close = self.search([
            ('state', '=', 'open'),
            '|',
            ('date_end', '<=', fields.Date.to_string(date.today())),
            ('visa_expire', '<=', fields.Date.to_string(date.today())),
        ])

        if contracts_to_close:
            contracts_to_close._safe_write_for_cron({'state': 'close'}, from_cron)

        contracts_to_open = self.search([('state', '=', 'draft'), ('kanban_state', '=', 'done'), ('date_start', '<=', fields.Date.to_string(date.today())),])

        if contracts_to_open:
            contracts_to_open._safe_write_for_cron({'state': 'open'}, from_cron)

        contract_ids = self.search([('date_end', '=', False), ('state', '=', 'close'), ('employee_id', '!=', False)])
        # Ensure all closed contract followed by a new contract have a end date.
        # If closed contract has no closed date, the work entries will be generated for an unlimited period.
        for contract in contract_ids:
            next_contract = self.search([
                ('employee_id', '=', contract.employee_id.id),
                ('state', 'not in', ['cancel', 'draft']),
                ('date_start', '>', contract.date_start)
            ], order="date_start asc", limit=1)
            if next_contract:
                contract._safe_write_for_cron({'date_end': next_contract.date_start - relativedelta(days=1)}, from_cron)
                continue
            next_contract = self.search([
                ('employee_id', '=', contract.employee_id.id),
                ('date_start', '>', contract.date_start)
            ], order="date_start asc", limit=1)
            if next_contract:
                contract._safe_write_for_cron({'date_end': next_contract.date_start - relativedelta(days=1)}, from_cron)

        return True

    def _safe_write_for_cron(self, vals, from_cron=False):
        if from_cron:
            auto_commit = not getattr(threading.current_thread(), 'testing', False)
            for contract in self:
                try:
                    with self.env.cr.savepoint():
                        contract.write(vals)
                except ValidationError as e:
                    _logger.warning(e)
                else:
                    if auto_commit:
                        self.env.cr.commit()
        else:
            self.write(vals)

    def _assign_open_contract(self):
        for contract in self:
            contract.employee_id.sudo().write({'contract_id': contract.id})

    @api.depends('wage')
    def _compute_contract_wage(self):
        for contract in self:
            contract.contract_wage = contract._get_contract_wage()

    def _get_contract_wage(self):
        self.ensure_one()
        return self[self._get_contract_wage_field()]

    def _get_contract_wage_field(self):
        return 'wage'

    def write(self, vals):
        res = super(Contract, self).write(vals)
        if vals.get('state') == 'open':
            self._assign_open_contract()
        if vals.get('state') == 'close':
            for contract in self.filtered(lambda c: not c.date_end):
                contract.date_end = max(date.today(), contract.date_start)

        calendar = vals.get('resource_calendar_id')
        if calendar:
            self.filtered(
                lambda c: c.state == 'open' or (c.state == 'draft' and c.kanban_state == 'done' and c.employee_id.contracts_count == 1)
            ).employee_id.resource_calendar_id = calendar

        if 'state' in vals and 'kanban_state' not in vals:
            self.write({'kanban_state': 'normal'})

        return res

    @api.model
    def create(self, vals):
        contracts = super(Contract, self).create(vals)
        if vals.get('state') == 'open':
            contracts._assign_open_contract()
        open_contracts = contracts.filtered(
            lambda c: c.state == 'open' or (c.state == 'draft' and c.kanban_state == 'done' and c.employee_id.contracts_count == 1)
        )
        # sync contract calendar -> calendar employee
        for contract in open_contracts.filtered(lambda c: c.employee_id and c.resource_calendar_id):
            contract.employee_id.resource_calendar_id = contract.resource_calendar_id
        return contracts

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values and self.state == 'open' and 'kanban_state' in init_values and self.kanban_state == 'blocked':
            return self.env.ref('hr_contract.mt_contract_pending')
        elif 'state' in init_values and self.state == 'close':
            return self.env.ref('hr_contract.mt_contract_close')
        return super(Contract, self)._track_subtype(init_values)

    def action_open_contract_form(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.contract",
            "views": [[False, "form"]],
            "res_id": self.id,
        }
