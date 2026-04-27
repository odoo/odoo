# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from collections import OrderedDict
from odoo import api, fields, models, _
from odoo.fields import Datetime



class L10nChIndividualAccount(models.Model):
    _name = 'l10n.ch.individual.account'
    _inherit = 'hr.payroll.declaration.mixin'
    _description = 'Swiss Payroll: Individual Account'

    def _country_restriction(self):
        return 'CH'

    name = fields.Char(
        string="Description", required=True, compute='_compute_name', readonly=False, store=True)

    @api.depends('year')
    def _compute_name(self):
        for sheet in self:
            sheet.name = _('Individual Accounts - Year %s', sheet.year)

    def action_generate_declarations(self):
        for sheet in self:
            all_payslips = self.env['hr.payslip'].search([
                ('date_to', '<=', datetime.date(int(sheet.year), 12, 31)),
                ('date_from', '>=', datetime.date(int(sheet.year), 1, 1)),
                ('state', 'in', ['done', 'paid']),
                ('company_id', '=', sheet.company_id.id),
            ])
            all_employees = all_payslips.employee_id
            sheet.write({
                'line_ids': [(5, 0, 0)] + [
                    (0, 0, {
                        'employee_id': False,
                        'res_model': 'l10n.ch.individual.account',
                        'res_id': sheet.id})] + [
                    (0, 0, {
                        'employee_id': employee.id,
                        'res_model': 'l10n.ch.individual.account',
                        'res_id': sheet.id,
                    }) for employee in all_employees
                ]
            })
        return super().action_generate_declarations()

    def _get_rendering_data(self, employees):
        self.ensure_one()

        payslips = self.env['hr.payslip'].search([
            ('employee_id', 'in', employees.ids),
            ('state', 'in', ['done', 'paid']),
            ('date_from', '>=', Datetime.now().replace(month=1, day=1, year=int(self.year))),
            ('date_from', '<=', Datetime.now().replace(month=12, day=31, year=int(self.year))),
            ('struct_id.country_id.code', '=', "CH"),
        ])
        employees = list(payslips.employee_id) + [self.env['hr.employee']]
        lines = payslips.line_ids.filtered(lambda l: l.salary_rule_id.appears_on_payslip and l.salary_rule_id.l10n_ch_code)
        payslip_rules = lines.salary_rule_id.sorted(lambda r: r.l10n_ch_code)

        result = {
            employee: {
                'year': self.year,
                'company': employee.company_id or self.company_id,
                'rules': OrderedDict(
                    (rule, {
                        'year': {'name': False, 'total': 0},
                        'month': {m: {'name': False, 'total': 0} for m in range(12)},
                    }) for rule in payslip_rules),
            } for employee in employees
        }

        for line in lines:
            for employee in [line.employee_id, self.env['hr.employee']]:
                rule = result[employee]['rules'][line.salary_rule_id]
                month = line.slip_id.date_from.month - 1
                rule['month'][month]['name'] = line.name
                rule['month'][month]['total'] += line.total
                rule['year']['name'] = line.name
                rule['year']['total'] += line.total
        return result


    def _get_pdf_report(self):
        return self.env.ref('l10n_ch_hr_payroll.action_report_individual_account')

    def _get_pdf_filename(self, employee):
        self.ensure_one()
        if employee:
            return _('%(employee)s-ch-individual-account-%(year)s', employee=employee.name, year=self.year)
        return _('%(company)s-ch-global-account-%(year)s', company=self.company_id.name, year=self.year)
