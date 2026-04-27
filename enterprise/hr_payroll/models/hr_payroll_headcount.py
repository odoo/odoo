# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from random import randint

from odoo import fields, models, api, _


class HrPayrollHeadcount(models.Model):
    _name = 'hr.payroll.headcount'
    _description = 'Payroll Headcount'

    name = fields.Char(string='Name', compute='_compute_name', store=True)
    is_name_custom = fields.Boolean(string='Custom Name', compute="_compute_is_name_custom")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company.id)
    line_ids = fields.One2many('hr.payroll.headcount.line', 'headcount_id')
    employee_count = fields.Integer(string='Employee Count')
    date_from = fields.Date(string='From', default=lambda self: fields.date.today(), required=True)
    date_to = fields.Date(string='To')

    _sql_constraints = [
        ('date_range', 'CHECK (date_from <= date_to)', 'The start date must be anterior to the end date.'),
    ]

    @api.depends('date_from', 'date_to', 'company_id')
    def _compute_name(self):
        for headcount in self:
            if not headcount.is_name_custom:
                headcount.name = headcount.get_default_name()

    @api.depends('name')
    def _compute_is_name_custom(self):
        for headcount in self:
            if headcount.name and headcount.name != headcount.get_default_name():
                headcount.is_name_custom = True
            else:
                headcount.is_name_custom = False

    def get_default_name(self):
        self.ensure_one()
        if self.date_from == self.date_to or not self.date_to:
            return _(
                'Headcount for %(company_name)s on the %(date)s',
                company_name=self.company_id.name,
                date=self.date_from)
        return _(
            'Headcount for %(company_name)s from %(date_from)s to %(date_to)s',
            company_name=self.company_id.name,
            date_from=self.date_from,
            date_to=self.date_to)

    def action_populate(self):
        self.ensure_one()
        if not self.date_to:
            self.date_to = self.date_from
        contracts = self.env['hr.contract'].search([
            ('company_id', '=', self.company_id.id),
            '|',
                ('date_end', '=', False),
                ('date_end', '>=', self.date_from),
            ('date_start', '<=', self.date_to),
            '|',
                ('state', 'in', ['open', 'close']),
                '&',
                    ('state', '=', 'draft'),
                    ('kanban_state', '=', 'done'),
        ], order='employee_id, date_start DESC')

        contracts_by_employee_id = defaultdict(lambda: self.env['hr.contract'])
        working_rates = set()
        for contract in contracts:
            contracts_by_employee_id[contract.employee_id.id] |= contract
            working_rates.add(round(contract.hours_per_week, 2))

        existing_working_rates = self.env['hr.payroll.headcount.working.rate']\
            .search([('rate', 'in', list(working_rates))])
        working_rate_to_create = working_rates - set(existing_working_rates.mapped('rate'))
        if working_rate_to_create:
            created_working_rate = self.env['hr.payroll.headcount.working.rate']\
                .create([{'rate': rate} for rate in working_rate_to_create])
            existing_working_rates |= created_working_rate

        working_rate_id_by_value = {}
        for working_rate in existing_working_rates:
            working_rate_id_by_value[working_rate.rate] = working_rate.id

        lines = [
            (0, 0, {
                'contract_id': contracts[0].id,
                'working_rate_ids': [
                    (6, 0, [working_rate_id_by_value[round(contract.hours_per_week, 2)] for contract in contracts]),
                ],
                'contract_names': ', '.join(contract.name for contract in contracts),
            })
            for contracts in contracts_by_employee_id.values()]
        self.line_ids = [(5, 0, 0)] + lines
        self.employee_count = len(self.line_ids)

    def action_open_lines(self):
        self.ensure_one()
        return {
            'name': _("Headcount's employees"),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payroll.headcount.line',
            'view_mode': 'list',
            'domain': [('headcount_id', '=', self.id)],
            'target': 'current',
            'context': {
                'search_default_group_by_department': True,
            },
        }


class HrPayrollHeadcountLine(models.Model):
    _name = 'hr.payroll.headcount.line'
    _description = 'Headcount Line'

    headcount_id = fields.Many2one('hr.payroll.headcount', string='headcount_id', required=True, ondelete='cascade')
    working_rate_ids = fields.Many2many('hr.payroll.headcount.working.rate', required=True, string='Working Rate')
    contract_names = fields.Char(string='Contract Names', required=True, readonly=True)
    contract_id = fields.Many2one('hr.contract', string='Contract', required=True, readonly=True)
    department_id = fields.Many2one(related='contract_id.department_id', string='Department')
    job_id = fields.Many2one(related='contract_id.job_id', string='Job Title')
    currency_id = fields.Many2one(related='contract_id.currency_id', string='Currency')
    wage_on_payroll = fields.Monetary(string='Wage On Payroll', currency_field='currency_id', compute='_compute_wage_on_payroll')
    employee_id = fields.Many2one(related="contract_id.employee_id", required=True, readonly=True)
    employee_type = fields.Selection(related='employee_id.employee_type', string='Employee Type')

    @api.depends('contract_id')
    def _compute_wage_on_payroll(self):
        for line in self:
            line.wage_on_payroll = line.contract_id._get_contract_wage()


class HrPayrollHeadcountWorkingRate(models.Model):
    _name = 'hr.payroll.headcount.working.rate'
    _description = 'Working Rate'

    rate = fields.Float(string='Rate')
    color = fields.Integer(string='Color', default=lambda self: randint(1, 11))

    @api.depends('rate')
    def _compute_display_name(self):
        for working_rate in self:
            working_rate.display_name = _('%(rate)s Hours/week', rate=working_rate.rate)
