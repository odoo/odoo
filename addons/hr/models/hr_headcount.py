# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from random import randint

from odoo import api, fields, models


class HrHeadcount(models.Model):
    _name = 'hr.headcount'
    _description = 'Employee Headcount'

    name = fields.Char(string='Name', compute='_compute_name', store=True)
    is_name_custom = fields.Boolean(string='Custom Name', compute="_compute_is_name_custom")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company.id)
    line_ids = fields.One2many('hr.headcount.line', 'headcount_id')
    employee_count = fields.Integer(string='Employee Count')
    date_from = fields.Date(string='From', default=fields.Date.context_today, required=True)
    date_to = fields.Date(string='To')

    _date_range = models.Constraint(
        'CHECK (date_from <= date_to)',
        "The start date must be anterior to the end date.",
    )

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
            return self.env._(
                'Headcount for %(company_name)s on the %(date)s',
                company_name=self.company_id.name,
                date=self.date_from)
        return self.env._(
            'Headcount for %(company_name)s from %(date_from)s to %(date_to)s',
            company_name=self.company_id.name,
            date_from=self.date_from,
            date_to=self.date_to)

    def action_populate(self):
        self.ensure_one()
        if not self.date_to:
            self.date_to = self.date_from
        versions = self.env['hr.version'].search([
            ('company_id', '=', self.company_id.id),
            ('employee_id', '!=', False),
            '|',
                ('contract_date_end', '=', False),
                ('contract_date_end', '>=', self.date_from),
            ('contract_date_start', '!=', False),
            ('contract_date_start', '<=', self.date_to),
        ], order='employee_id, contract_date_start DESC')

        versions_by_employee_id = defaultdict(lambda: self.env['hr.version'])
        working_rates = set()
        work_rates_by_version = {}
        for version in versions:
            versions_by_employee_id[version.employee_id.id] |= version
            hours_per_week = round(version.resource_calendar_id.hours_per_week, 2)
            working_rates.add(hours_per_week)
            work_rates_by_version[version.id] = hours_per_week

        existing_working_rates = self.env['hr.headcount.working.rate']\
            .search([('rate', 'in', list(working_rates))])
        working_rate_to_create = working_rates - set(existing_working_rates.mapped('rate'))
        if working_rate_to_create:
            created_working_rates = self.env['hr.headcount.working.rate']\
                .create([{'rate': rate} for rate in working_rate_to_create])
            existing_working_rates |= created_working_rates

        working_rate_id_by_value = {}
        for working_rate in existing_working_rates:
            working_rate_id_by_value[working_rate.rate] = working_rate.id

        lines = [
            (0, 0, {
                'version_id': versions[0].id,
                'working_rate_ids': [
                    (6, 0, [
                        working_rate_id_by_value[work_rates_by_version[version.id]] for version in versions
                    ]),
                ],
            })
            for versions in versions_by_employee_id.values()]
        self.line_ids = [(5, 0, 0)] + lines
        self.employee_count = len(self.line_ids)

    def action_open_lines(self):
        self.ensure_one()
        return {
            'name': self.env._("Headcount's employees"),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.headcount.line',
            'view_mode': 'list',
            'domain': [('headcount_id', '=', self.id)],
            'target': 'current',
            'context': {
                'search_default_group_by_department': True,
            },
        }


class HrHeadcountLine(models.Model):
    _name = 'hr.headcount.line'
    _description = 'Headcount Line'

    headcount_id = fields.Many2one('hr.headcount', string='headcount_id', required=True, index=True, ondelete='cascade')
    working_rate_ids = fields.Many2many('hr.headcount.working.rate', required=True, string='Working Rate')
    version_id = fields.Many2one('hr.version', string='Employee Record', required=True, index=True, readonly=True)
    department_id = fields.Many2one(related='version_id.department_id', string='Department')
    job_id = fields.Many2one(related='version_id.job_id', string='Job Title')
    currency_id = fields.Many2one(related='version_id.currency_id', string='Currency')
    wage_on_payroll = fields.Monetary(string='Wage On Payroll', currency_field='currency_id', compute='_compute_wage_on_payroll')
    employee_id = fields.Many2one(related="version_id.employee_id", required=True, readonly=True)
    employee_type = fields.Many2one(related='version_id.employee_type_id', string='Employee Type')

    @api.depends('version_id')
    def _compute_wage_on_payroll(self):
        for line in self:
            line.wage_on_payroll = line.version_id._get_contract_wage()


class HrHeadcountWorkingRate(models.Model):
    _name = 'hr.headcount.working.rate'
    _description = 'Working Rate'

    rate = fields.Float(string='Rate')
    color = fields.Integer(string='Color', default=lambda self: randint(1, 11))

    @api.depends('rate')
    def _compute_display_name(self):
        for working_rate in self:
            working_rate.display_name = self.env._('%(rate)s Hours/week', rate=working_rate.rate)
