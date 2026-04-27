# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64encode
from dateutil.relativedelta import relativedelta
from datetime import date
from io import BytesIO

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import xlsxwriter


LINE_CODES = [
    'BASIC', 'BONUS', 'COMMISSION', 'LEAVE120',
    'TAXED_AIRTIME_ALLOWANCE', 'TAXED_FOOD_ALLOWANCE',
    'GROSS', 'NHIF_AMOUNT', 'NSSF_AMOUNT', 'PAYE', 'HELB',
    'STATUTORY_DED', 'ADVANCE', 'LOAN', 'OTHER_DED',
    'NET', 'NITA', 'NSSF_EMP',
]
MONTHS_SELECTION = [
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
# values taken from XlsxWriter@3.2.0
CHAR_WIDTHS = {
    ' ': 3, '!': 5, '"': 6, '#': 7, '$': 7, '%': 11, '&': 10, "'": 3,
    '(': 5, ')': 5, '*': 7, '+': 7, ',': 4, '-': 5, '.': 4, '/': 6,
    '0': 7, '1': 7, '2': 7, '3': 7, '4': 7, '5': 7, '6': 7, '7': 7,
    '8': 7, '9': 7, ':': 4, ';': 4, '<': 7, '=': 7, '>': 7, '?': 7,
    '@': 13, 'A': 9, 'B': 8, 'C': 8, 'D': 9, 'E': 7, 'F': 7, 'G': 9,
    'H': 9, 'I': 4, 'J': 5, 'K': 8, 'L': 6, 'M': 12, 'N': 10, 'O': 10,
    'P': 8, 'Q': 10, 'R': 8, 'S': 7, 'T': 7, 'U': 9, 'V': 9, 'W': 13,
    'X': 8, 'Y': 7, 'Z': 7, '[': 5, '\\': 6, ']': 5, '^': 7, '_': 7,
    '`': 4, 'a': 7, 'b': 8, 'c': 6, 'd': 8, 'e': 8, 'f': 5, 'g': 7,
    'h': 8, 'i': 4, 'j': 4, 'k': 7, 'l': 4, 'm': 12, 'n': 8, 'o': 8,
    'p': 8, 'q': 8, 'r': 5, 's': 6, 't': 5, 'u': 8, 'v': 7, 'w': 11,
    'x': 7, 'y': 7, 'z': 6, '{': 5, '|': 7, '}': 5, '~': 7, 'avg': 7,
    'other': 8,
}


class L10nKePayrollMasterReport(models.Model):
    _name = 'l10n_ke.master.report'
    _description = 'Headover Wizard'

    @staticmethod
    def year_range_selection(start_offset, end_offset, steps=1):
        current_year = fields.Datetime.now().year
        return [(str(year), str(year)) for year in range(current_year - start_offset, current_year + end_offset, steps)]

    @api.model
    def default_get(self, field_list=None):
        if self.env.company.country_id.code != 'KE':
            raise UserError(_('You must be logged in a Kenyan company to use this feature'))
        return super().default_get(field_list)

    reference_month = fields.Selection(
        MONTHS_SELECTION,
        string='Month',
        required=True,
        default=lambda self: str(fields.Datetime.now().month),
        help='Select the month for which you want to see which employees have a running contract.')
    reference_year = fields.Selection(
        string='Year',
        required=True,
        selection=lambda self: self.year_range_selection(50, 10),
        default=lambda self: str(fields.Datetime.now().year),
        help='Select the year for which you want to see which employees have a running contract.')
    xlsx_file = fields.Binary(string='Master Report XLSX', readonly=True)
    xlsx_file_name = fields.Char(readonly=True)
    pdf_file = fields.Binary(string='Master Report PDF', readonly=True)
    pdf_file_name = fields.Char(readonly=True)

    def _compute_display_name(self):
        for record in self:
            record.display_name = _('Master Report')

    def _get_report_data(self):
        self.ensure_one()
        min_date = date(int(self.reference_year), int(self.reference_month), 1)
        max_date = min_date + relativedelta(months=1)
        payslips = self.env['hr.payslip'].search([
            ('state', 'in', ['done', 'paid']),
            ('date_from', '<=', max_date),
            ('date_to', '>=', min_date),
            '|',
                ('struct_id.country_id', '=', False),
                ('struct_id.country_id.code', '=', 'KE'),
        ])
        currency_symbol = self.env.company.currency_id.symbol
        line_values = payslips._get_line_values(LINE_CODES, compute_sum=True)
        payslips_data = {}
        for payslip in payslips:
            payslip_no = payslip.number
            payslips_data[payslip_no] = {
                'payroll_number': payslip.employee_id.registration_number or '',
                'employee_name': payslip.employee_id.name,
                'department': payslip.employee_id.department_id.name or '',
                **{
                    line_code: (
                        ' '.join([str(total), currency_symbol])
                        if (total := line_values[line_code][payslip.id]['total']) else '-'
                    ) for line_code in LINE_CODES
                },
            }
        payslips_data = dict(sorted(payslips_data.items()))
        sums = {line_code: (
                    ' '.join([str(total), currency_symbol])
                    if (total := line_values[line_code]['sum']['total']) else '-'
                ) for line_code in LINE_CODES}
        headers = [
            _('Basic Salary'), _('Bonus'), _('Commission'),
            _('Holiday Pay'), _('Airtime Allowance'),
            _('Meal Allowance'), _('Gross Salary'), _('NHIF'),
            _('NSSF'), _('PAYE'), _('HELB'), _('Total Statutory Deductions'),
            _('Salary Advance'), _('Loan'), _('Total Other Deductions'),
            _('Net Pay'), _('NITA'), _('NSSF - Employer Contribution'),
        ]

        return {
            'company_name': self.env.company.name,
            'payroll_month': dict(self._fields['reference_month'].selection)[self.reference_month],
            'payroll_year': self.reference_year,
            'payslips_data': payslips_data,
            'sums': sums,
            'headers': dict(zip(LINE_CODES, headers))
        }

    def action_generate_xlsx(self):
        def string_width_px(string):
            if '\n' in string:
                return max(string_width_px(line) for line in string.split('\n'))
            return sum(CHAR_WIDTHS.get(char, CHAR_WIDTHS['other']) for char in string)

        def string_width_xlsx(string, font_size=11):
            # this method is used to calculate the approximate width of a column
            return string_width_px(string) * font_size / (CHAR_WIDTHS['avg'] * 10)

        self.ensure_one()
        data = self._get_report_data()

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        style_normal = workbook.add_format({'align': 'right'})
        style_bold = workbook.add_format({'align': 'right', 'bold': True})
        style_bold_center = workbook.add_format({'align': 'center', 'bold': True})

        col_widths = {}
        worksheet = workbook.add_worksheet('Master Report')
        worksheet.write_string(0, 0, _('Company Name'), style_bold)
        worksheet.write(0, 1, data['company_name'])
        worksheet.write_string(1, 0, _('Payroll Month'), style_bold)
        # format the period as 'jan-21' for example
        worksheet.write(1, 1, data['payroll_month'][:3].title() + '-' + data['payroll_year'][2:])
        headers = [_('Payroll Number'), _('Name'), _('Department')] + list(data['headers'].values())
        for col, header in enumerate(headers):
            worksheet.write(3, col, header, style_bold_center)
            col_widths[col] = string_width_xlsx(header)
        row = 4
        for payslip_data in data['payslips_data'].values():
            for col, value in enumerate(payslip_data.values()):
                worksheet.write(row, col, value, style_normal)
                val_size = string_width_xlsx(str(value))
                if val_size > col_widths[col]:
                    col_widths[col] = val_size
            row += 1

        worksheet.write(row, 2, _('Totals'), style_bold)
        for col, value in enumerate(data['sums'].values(), 3):
            worksheet.write(row, col, value, style_bold)
            val_size = string_width_xlsx(str(value))
            if val_size > col_widths[col]:
                col_widths[col] = val_size
        for col, col_width in col_widths.items():
            worksheet.set_column(col, col, col_width)
        workbook.close()
        self.xlsx_file = b64encode(output.getvalue())
        self.xlsx_file_name = _('Master_Report.xlsx')

    def action_generate_pdf(self):
        data = self._get_report_data()
        pdf = self.env["ir.actions.report"].sudo()._render_qweb_pdf(
            report_ref=self.env.ref('l10n_ke_hr_payroll.action_report_master_report').id,
            res_ids=self.ids,
            data={'report_data': data},
        )[0]
        self.pdf_file = b64encode(pdf)
        self.pdf_file_name = _('Master_Report.pdf')
