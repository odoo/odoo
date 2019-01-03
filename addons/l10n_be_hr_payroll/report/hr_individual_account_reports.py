# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict

from odoo import api, models, _
from odoo.fields import Datetime
from odoo.exceptions import UserError


class IndividualAccountReport(models.AbstractModel):
    _name = 'report.l10n_be_hr_payroll.report_individual_account'
    _description = 'Individual Account Report'

    def _get_report_data(self, data):
        year = data['year']
        employees = self.env['hr.employee'].browse(data['employee_ids'])

        payslips = self.env['hr.payslip'].search([
            ('employee_id', 'in', employees.ids),
            ('state', '=', 'done'),
            ('date_from', '>=', Datetime.now().replace(month=1, day=1, year=year)),
            ('date_from', '<=', Datetime.now().replace(month=12, day=31, year=year)),
            '|',
            ('struct_id.country_id', '=', False),
            ('struct_id.country_id', '=', self.env.ref('base.be').id),
        ])
        lines = payslips.mapped('line_ids')
        payslip_rules = [(rule.code, rule.sequence) for rule in lines.mapped('salary_rule_id')]
        payslip_rules = sorted(payslip_rules, key=lambda x: x[1])
        worked_days = payslips.mapped('worked_days_line_ids')

        result = {
            employee: {
                'rules': OrderedDict(
                    (rule[0], {
                        'year': {'name': False, 'total': 0},
                        'month': {m: {'name': False, 'total': 0} for m in range(12)},
                        'quarter': {q: {'name': False, 'total': 0} for q in range(4)}
                    }) for rule in payslip_rules),
                'worked_days': {
                    code: {
                        'year': {'name': False, 'number_of_days': 0, 'number_of_hours': 0},
                        'month': {m: {'name': False, 'number_of_days': 0, 'number_of_hours': 0} for m in range(12)},
                        'quarter': {q: {'name': False, 'number_of_days': 0, 'number_of_hours': 0} for q in range(4)}
                    } for code in worked_days.mapped('code')
                }
            } for employee in employees
        }

        for line in lines:
            rule = result[line.employee_id]['rules'][line.salary_rule_id.code]
            month = line.slip_id.date_from.month - 1
            rule['month'][month]['name'] = line.name
            rule['month'][month]['total'] += line.total
            rule['quarter'][(month) // 3]['name'] = line.name
            rule['quarter'][(month) // 3]['total'] += line.total
            rule['year']['name'] = line.name
            rule['year']['total'] += line.total

            rule['month'][month]['total'] = round(rule['month'][month]['total'], 2)
            rule['quarter'][(month) // 3]['total'] = round(rule['quarter'][(month) // 3]['total'], 2)
            rule['year']['total'] = round(rule['year']['total'], 2)

        for worked_day in worked_days:
            work = result[worked_day.payslip_id.employee_id]['worked_days'][worked_day.code]
            month = worked_day.payslip_id.date_from.month - 1

            work['month'][month]['name'] = worked_day.name
            work['month'][month]['number_of_days'] += worked_day.number_of_days
            work['month'][month]['number_of_hours'] += worked_day.number_of_hours
            work['quarter'][(month) // 3]['name'] = worked_day.name
            work['quarter'][(month) // 3]['number_of_days'] += worked_day.number_of_days
            work['quarter'][(month) // 3]['number_of_hours'] += worked_day.number_of_hours
            work['year']['name'] = worked_day.name
            work['year']['number_of_days'] += worked_day.number_of_days
            work['year']['number_of_hours'] += worked_day.number_of_hours

        return {
            'year': year,
            'employee_data': result
        }

    @api.model
    def _get_report_values(self, docids, data=None):
        if self.env.user.company_id.country_id != self.env.ref('base.be'):
            raise UserError(_("You must be logged into a Belgian company to print the individual account."))
        return {'report_data': self._get_report_data(data)}
