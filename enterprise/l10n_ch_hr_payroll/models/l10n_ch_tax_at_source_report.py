# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from collections import defaultdict
from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class L10nCHInsuranceReport(models.Model):
    _name = 'l10n.ch.is.report'
    _description = 'Tax at Source Monthly Report'

    @api.model
    def default_get(self, field_list=None):
        if self.env.company.country_id.code != "CH":
            raise UserError(_('You must be logged in a Swiss company to use this feature'))
        return super().default_get(field_list)
    name = fields.Char(required=True)
    year = fields.Integer(required=True, default=lambda self: fields.Date.today().year)
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
    ], default=lambda self: str(fields.Date.today().month))

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    work_location_ids = fields.Many2many('l10n.ch.location.unit')
    report_line_ids = fields.One2many('l10n.ch.is.report.line', 'report_id')

    def _get_canton_rendering_data(self, canton, payslips):
        self.ensure_one()
        mapped_salaries_per_code = defaultdict(lambda: defaultdict(lambda: [0, 0, 0, 0]))
        for payslip in payslips.sudo().filtered(lambda p: p.l10n_ch_is_code.split('-')[0] == canton):
            current_month_log_lines = payslip.l10n_ch_is_log_line_ids.filtered(lambda l: l.payslip_id.id == payslip.id and not l.is_correction)
            for tarif in set(current_month_log_lines.mapped('is_code')):
                is_paid = sum(current_month_log_lines.filtered(lambda l: l.code == 'IS' and l.is_code == tarif).mapped('amount'))
                is_salary = sum(current_month_log_lines.filtered(lambda l: l.code == 'ISSALARY' and l.is_code == tarif).mapped('amount'))
                is_dt_salary = sum(current_month_log_lines.filtered(lambda l: l.code == 'ISDTSALARY' and l.is_code == tarif).mapped('amount'))
                is_dt_aperiodic_salary = sum(current_month_log_lines.filtered(lambda l: l.code == 'ISDTSALARYAPERIODIC' and l.is_code == tarif).mapped('amount'))
                mapped_salaries_per_code[payslip.employee_id][tarif][0] += is_dt_salary
                mapped_salaries_per_code[payslip.employee_id][tarif][1] += is_salary
                mapped_salaries_per_code[payslip.employee_id][tarif][2] += is_dt_aperiodic_salary
                mapped_salaries_per_code[payslip.employee_id][tarif][3] += is_paid

        reporting_data = {
            'report_name': f"Tax At Source Report : {canton}",
            'company': self.company_id,
            'year': self.year,
            'columns': [
                'IS Code', "SV-AS Number", 'Name', 'Determinant Salary', 'IS Salary', 'Aperiodic Salary', 'IS'
            ],
            'employee_data': sorted([
                [
                    is_code.split('-')[1],
                    employee.l10n_ch_sv_as_number,
                    employee.name,
                    '%.2f %s' % (mapped_salaries_per_code[employee][is_code][0], self.currency_id.symbol),
                    '%.2f %s' % (mapped_salaries_per_code[employee][is_code][1], self.currency_id.symbol),
                    '%.2f %s' % (mapped_salaries_per_code[employee][is_code][2], self.currency_id.symbol),
                    '%.2f %s' % (-mapped_salaries_per_code[employee][is_code][3], self.currency_id.symbol),
                ] for employee in mapped_salaries_per_code for is_code in mapped_salaries_per_code[employee]
            ], key=lambda e: (e[2], e[0])),
        }

        return reporting_data

    def _get_rendering_data(self):
        payslips = self.env['hr.payslip'].search([
            ('state', 'in', ['done', 'paid']),
            ('company_id', '=', self.company_id.id),
            ('date_from', '>=', date(self.year, int(self.month), 1)),
            ('date_to', '<=', date(self.year, int(self.month), 1) + relativedelta(days=31)),
            ('l10n_ch_is_code', '!=', False)
        ])

        cantons = set(self.work_location_ids.mapped('canton'))

        return {
            canton: self._get_canton_rendering_data(canton, payslips) for canton in cantons
        }

    def action_generate_pdf(self):
        self.ensure_one()
        rendering_data = self._get_rendering_data()
        report_vals = []
        for canton in rendering_data:
            export_insurance_pdf = self.env["ir.actions.report"].sudo()._render_qweb_pdf(
                self.env.ref('l10n_ch_hr_payroll.action_is_report'),
                res_ids=self.ids, data=rendering_data[canton])[0]
            report_vals.append({
                'canton': canton,
                'pdf_file': base64.encodebytes(export_insurance_pdf),
                'pdf_filename': f"{canton}-{self.month}-{self.year}.pdf"
            })
        self.report_line_ids.unlink()
        self.report_line_ids = self.env['l10n.ch.is.report.line'].create(report_vals)


class L10nCHInsuranceReportLine(models.Model):
    _name = 'l10n.ch.is.report.line'
    _description = 'Tax at Source Monthly Report Line'

    report_id = fields.Many2one('l10n.ch.is.report')
    canton = fields.Char()
    pdf_file = fields.Binary(string="PDF File")
    pdf_filename = fields.Char("PDF Filename")
