# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io

from collections import defaultdict
from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import format_date
from odoo.tools.misc import xlsxwriter


class L10nChMonthlySummaryWizard(models.Model):
    _name = 'l10n.ch.monthly.summary'
    _description = 'Swiss Payroll: Monthly Summary'
    _order = 'date_start'

    @api.model
    def default_get(self, field_list=None):
        if self.env.company.country_id.code != "CH":
            raise UserError(_('You must be logged in a Swiss company to use this feature'))
        return super().default_get(field_list)

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
    ], required=True, default=lambda self: str((fields.Date.today() + relativedelta(months=-1)).month))
    date_start = fields.Date(
        'Start Period', store=True, readonly=False,
        compute='_compute_dates')
    date_end = fields.Date(
        'End Period', store=True, readonly=False,
        compute='_compute_dates')
    aggregation_type = fields.Selection([
        ('company', 'By Company'),
        ('employee', 'By Employee'),
    ], required=True, default='company')
    company_ids = fields.Many2many('res.company', default=lambda self: self.env.companies.filtered(lambda c: c.country_id.code == "CH"))
    currency_id = fields.Many2one('res.currency', related='company_ids.currency_id')
    monthly_summary_pdf_file = fields.Binary('Monthly Summary PDF', readonly=True, attachment=False)
    monthly_summary_pdf_filename = fields.Char()
    monthly_summary_xls_file = fields.Binary('Monthly Summary XLS', readonly=True, attachment=False)
    monthly_summary_xls_filename = fields.Char()

    @api.depends('date_start')
    def _compute_display_name(self):
        for record in self:
            record.display_name = format_date(self.env, record.date_start, date_format="MMMM y", lang_code=self.env.user.lang)

    @api.depends('year', 'month')
    def _compute_dates(self):
        for record in self:
            record.update({
                'date_start': date(record.year, int(record.month), 1),
                'date_end': date(record.year, int(record.month), 1) + relativedelta(day=31),
            })

    def _get_valid_payslips(self):
        domain = [
            ('state', 'in', ['paid', 'done']),
            ('company_id', 'in', self.company_ids.ids),
            ('date_from', '>=', self.date_start),
            ('date_to', '<=', self.date_end),
        ]
        payslips = self.env['hr.payslip'].search(domain)
        if not payslips:
            raise UserError(_("There is no paid or done payslips over the selected period."))
        return payslips

    def _get_line_values(self):
        self.ensure_one()
        payslips = self._get_valid_payslips()

        rules = self.env['hr.payroll.structure'].search([
            ('country_id', '=', self.env.ref('base.ch').id)
        ]).rule_ids.filtered('l10n_ch_code').sorted(lambda r: int(r.l10n_ch_code))
        line_values = payslips._get_line_values(rules.mapped('code'), compute_sum=True)

        result = defaultdict(lambda: defaultdict(lambda: 0))
        for payslip in payslips:
            for rule in rules:
                if not rule.l10n_ch_code:
                    continue
                if self.aggregation_type == "company":
                    key = payslip.company_id
                else:
                    key = payslip.employee_id
                result[key][rule] += line_values[rule.code][payslip.id]['total']
        return result

    def action_generate_pdf(self):
        self.ensure_one()
        report_data = {
            'date_start': self.date_start.strftime("%d/%m/%Y"),
            'date_end': self.date_end.strftime("%d/%m/%Y"),
            'line_values': self._get_line_values(),
        }

        filename = '%s-%s-monthly-summary.pdf' % (self.date_start.strftime("%d%B%Y"), self.date_end.strftime("%d%B%Y"))
        monthly_summary, _ = self.env["ir.actions.report"].sudo()._render_qweb_pdf(
            self.env.ref('l10n_ch_hr_payroll.action_report_monthly_summary'),
            res_ids=self.ids, data=report_data)

        self.monthly_summary_pdf_filename = filename
        self.monthly_summary_pdf_file = base64.encodebytes(monthly_summary)

    def action_generate_xls(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        line_values = self._get_line_values()

        for aggregate_record, rules_data in line_values.items():
            worksheet = workbook.add_worksheet(aggregate_record.name)
            style_highlight = workbook.add_format({'bold': True, 'pattern': 1, 'bg_color': '#E0E0E0', 'align': 'center'})
            style_normal = workbook.add_format({'align': 'center'})
            row = 0
            col = 0

            headers = ["Code", "Name", "Amount"]
            rows = [(rule.l10n_ch_code, rule.name, total) for rule, total in rules_data.items()]

            for header in headers:
                worksheet.write(row, col, header, style_highlight)
                worksheet.set_column(col, col, 30)
                col += 1

            row = 1
            for employee_row in rows:
                col = 0
                for employee_data in employee_row:
                    worksheet.write(row, col, employee_data, style_normal)
                    col += 1
                row += 1

        workbook.close()
        xlsx_data = output.getvalue()

        self.monthly_summary_xls_file = base64.encodebytes(xlsx_data)
        self.monthly_summary_xls_filename = '%s-%s-monthly-summary.xlsx' % (self.date_start.strftime("%d%B%Y"), self.date_end.strftime("%d%B%Y"))
