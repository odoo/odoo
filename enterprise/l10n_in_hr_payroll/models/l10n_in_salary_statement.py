import calendar

from odoo import api, fields, models, Command, _
from dateutil.relativedelta import relativedelta
from collections import defaultdict
from datetime import datetime


class L10nInSalaryStatement(models.Model):
    _name = 'l10n_in_hr_payroll.salary.statement'
    _inherit = 'hr.payroll.declaration.mixin'
    _description = 'Salary Statement Report'

    name = fields.Char(string="Description", required=True, compute='_compute_name', readonly=False, store=True)
    month = fields.Selection([
        ('1', 'January'),
        ('2', 'February'),
        ('3', 'March'),
        ('4', 'April'),
        ('5', 'May'),
        ('6', 'June'),
        ('7', 'July'),
        ('8', 'August'),
        ('9', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], required=True, default=lambda self: str((fields.Date.today() + relativedelta(months=-1)).month))

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res['year'] = str(datetime.now().year)
        return res

    @api.depends('year', 'month')
    def _compute_name(self):
        for sheet in self:
            month_name = calendar.month_name[int(sheet.month)]
            sheet.name = _('Salary Statement - %(month)s, %(year)s', month=month_name, year=sheet.year)

    def action_generate_declarations(self):
        for sheet in self:
            date_from = datetime(int(sheet.year), int(sheet.month), 1)
            date_to = date_from + relativedelta(months=1, days=-1)
            employees = self.env['hr.payslip'].search([
                ('date_to', '<=', date_to),
                ('date_from', '>=', date_from),
                ('state', 'in', ['done', 'paid']),
                ('company_id', '=', sheet.company_id.id),
            ]).mapped('employee_id')

            sheet.write({
                'line_ids': [Command.clear()] + [Command.create({
                    'employee_id': employee.id,
                    'res_model': 'l10n_in_hr_payroll.salary.statement',
                    'res_id': sheet.id,
                }) for employee in employees]
            })
        return super().action_generate_declarations()

    def _country_restriction(self):
        return 'IN'

    def _get_pdf_report(self):
        return self.env.ref('l10n_in_hr_payroll.action_report_salary_statement')

    def _get_rendering_data(self, employees):
        self.ensure_one()
        date_from = datetime(int(self.year), int(self.month), 1)
        date_to = date_from + relativedelta(months=1)
        payslips = self.env['hr.payslip'].search([
            ('employee_id', 'in', employees.ids),
            ('state', 'in', ['done', 'paid']),
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to),
        ])

        result = defaultdict(lambda: {
            'month': calendar.month_name[int(self.month)],
            'year': self.year,
            'allow_rules': defaultdict(lambda: {'name': '', 'total': 0, 'total_annual': 0}),
            'deduct_rules': defaultdict(lambda: {'name': '', 'total': 0, 'total_annual': 0}),
            'ctc': 0,
            'ctc_annual': 0
        })

        for line in payslips.line_ids.filtered(lambda l: l.salary_rule_id.appears_on_payslip):
            employee_id = line.employee_id
            rule_category = result[employee_id]['deduct_rules' if line.total < 0 else 'allow_rules'][line.salary_rule_id]

            rule_category['name'] = line.salary_rule_id.name
            rule_category['total'] = line.total
            rule_category['total_annual'] = line.total * 12

            if line.code == 'GROSS' or line.total < 0:
                total = abs(line.total)
                result[employee_id]['ctc'] += total
                result[employee_id]['ctc_annual'] += total * 12
            result[employee_id]['date'] = line.date_from.strftime('%d/%m/%Y')

        result = dict(result)
        return result

    def _get_pdf_filename(self, employee):
        self.ensure_one()
        month_name = calendar.month_name[int(self.month)]
        return _('%(employee_name)s-salary-statement-report-%(month)s-%(year)s', employee_name=employee.name, month=month_name, year=self.year)
