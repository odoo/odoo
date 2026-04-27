# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
import calendar
from odoo import api, fields, models
from odoo.tools.misc import xlsxwriter

MONTH_SELECTION = [
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
]


class HrEPFReport(models.Model):
    _name = 'l10n.in.hr.payroll.epf.report'
    _description = 'Indian Payroll: Employee Provident Fund Report'

    month = fields.Selection(MONTH_SELECTION, default='1', required=True)
    year = fields.Integer(required=True, default=lambda self: fields.Date.context_today(self).year)
    xls_file = fields.Binary(string="XLS file")
    xls_filename = fields.Char()

    @api.depends('month', 'year')
    def _compute_display_name(self):
        month_description = dict(self._fields['month']._description_selection(self.env))
        for report in self:
            report.display_name = f"{month_description.get(report.month)}-{report.year}"

    @api.model
    def _get_employee_pf_data(self, year, month):
        # Get the relevant records based on the year and month
        indian_employees = self.env['hr.employee'].search([('contract_id.l10n_in_provident_fund', '=', True)]).filtered(lambda e: e.company_country_code == 'IN')

        result = []
        end_date = calendar.monthrange(year, int(month))[1]

        payslips = self.env['hr.payslip'].search([
            ('employee_id', 'in', indian_employees.ids),
            ('date_from', '>=', f'{year}-{month}-1'),
            ('date_to', '<=', f'{year}-{month}-{end_date}'),
            ('state', 'in', ('done', 'paid'))
        ])

        if not payslips:
            return []

        payslip_line_values = payslips._get_line_values(['GROSS', 'BASIC', 'PF'])

        for employee in indian_employees:

            wage = 0
            epf = 0
            eps = 0
            epf_contri = 0

            payslip_ids = payslips.filtered(lambda p: p.employee_id == employee)

            if not payslip_ids:
                continue

            for payslip in payslip_ids:
                pf_value = payslip_line_values['PF'][payslip.id]['total']
                if pf_value == 0:
                    continue

                epf_contri -= pf_value
                wage += payslip_line_values['GROSS'][payslip.id]['total']
                epf += payslip_line_values['BASIC'][payslip.id]['total']

            # Skip the employee if there are no valid PF contributions
            if epf_contri == 0:
                continue

            # Calculate contributions and differences
            eps = min(payslip_ids[0]._rule_parameter('l10n_in_pf_amount'), epf)
            eps_contri = round(eps * payslip_ids[0]._rule_parameter('l10n_in_eps_contri_percent'), 2)
            diff = round(epf_contri - eps_contri, 2)

            result.append((
                employee.l10n_in_uan,
                employee.name,
                wage,
                epf,
                eps,
                eps,
                epf_contri,
                eps_contri,
                diff,
                0, 0,
            ))

        return result

    def action_export_xlsx(self):
        self.ensure_one()

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Employee_provident_fund_report')
        style_highlight = workbook.add_format({'bold': True, 'pattern': 1, 'bg_color': '#E0E0E0', 'align': 'center'})
        style_normal = workbook.add_format({'align': 'center', 'font_size': 12})
        row = 0
        worksheet.set_row(row, 20)

        headers = [
            "UAN",
            "MEMBER NAME",
            "GROSS WAGES",
            "EPF WAGES",
            "EPS WAGES",
            "EDLI WAGES",
            "EPF CONTRIBUTION REMITTED",
            "EPS CONTRIBUTION REMITTED",
            "EPF EPS DIFFERENCE REMITTED",
            "NCP DAYS",
            "REFUNDED OF ADVANCES"
        ]

        rows = self._get_employee_pf_data(self.year, self.month)

        for col, header in enumerate(headers):
            worksheet.write(row, col, header, style_highlight)
            worksheet.set_column(col, col, 30)

        row = 1
        for data_row in rows:
            col = 0
            worksheet.set_row(row, 20)
            for data in data_row:
                worksheet.write(row, col, data, style_normal)
                col += 1
            row += 1

        workbook.close()
        xlsx_data = output.getvalue()

        self.xls_file = base64.encodebytes(xlsx_data)
        self.xls_filename = f"{self.display_name} EPF Report.xlsx"
