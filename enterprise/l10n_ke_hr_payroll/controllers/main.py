# Part of Odoo. See LICENSE file for full copyright and licensing details.

from io import BytesIO
from logging import getLogger
from odoo import http, _
from odoo.http import request
from odoo.tools.misc import xlsxwriter

_logger = getLogger(__name__)

class L10nKeHrPayrollNssfReportController(http.Controller):

    @http.route(['/export/nssf/<int:wizard_id>'], type='http', auth='user')
    def export_nssf_report(self, wizard_id):
        wizard = request.env['l10n.ke.hr.payroll.nssf.report.wizard'].browse(wizard_id)
        if not wizard.exists() or not request.env.user.has_group('hr_payroll.group_hr_payroll_user'):
            return request.render(
                'http_routing.http_error',
                {
                    'status_code': 'Oops',
                    'status_message': _('It seems that you either not have the rights to access the nhif reports '
                                        'or that you try to access it outside normal circumstances. '
                                        'If you think there is a problem, please contact an administrator.')
                }
            )

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('nhif_report')
        style_highlight = workbook.add_format({'bold': True, 'pattern': 1, 'bg_color': '#E0E0E0', 'align': 'center'})
        style_normal = workbook.add_format({'align': 'center'})
        column_width = 25
        horizontal_header_height = 35
        vertical_headers = [
            _('NSSF CONTRIBUTION'),
            _('EMPLOYER KRA PIN'),
            _('EMPLOYER NSSF NUMBER'),
            _('EMPLOYER NAME'),
            _('CONTRIBUTIONS PERIOD'),
            _('TOTAL INCOME'),
            _('TOTAL MEMBER'),
            _('TOTAL EMPLOYER'),
            _('TOTAL CONTRIBUTIONS'),
            _('TOTAL RECORDS'),
        ]

        in_between_blank_lines = 1
        horizontal_headers = [
            _('PAYROLL NO'),
            _('SURNAME'),
            _('OTHER NAMES'),
            _('ID NO'),
            _('KRA PIN'),
            _('NSSF NO'),
            _('CONTRIBUTIONS \n TYPE'),
            _('INCOME'),
            _('INCOME \n TYPE'),
            _('MEMBER'),
            _('EMPLOYER'),
            _('TOTAL'),
        ]

        total_employer = 0
        total_member = 0
        total_income = 0
        payslip_no = ""
        horizontal_data = []
        for line in wizard.line_ids:
            sliced_name = line.employee_id.name.split(' ', maxsplit=1)
            horizontal_data.append((
                line.payslip_number,
                sliced_name[0],
                sliced_name[1] if len(sliced_name) > 1 else '',
                line.employee_identification_id or'',
                line.employee_kra_pin or '',
                line.employee_nssf_number or '',
                line.payslip_nssf_code or '',
                line.payslip_income,
                '1',
                line.payslip_nssf_amount_employee,
                line.payslip_nssf_amount_employer,
                line.payslip_nssf_amount_employee + line.payslip_nssf_amount_employer,
            ))
            if payslip_no != line.payslip_number:
                payslip_no = line.payslip_number
                total_income += line.payslip_income
            total_employer += line.payslip_nssf_amount_employer
            total_member += line.payslip_nssf_amount_employee
        total_contribution = total_employer + total_member

        vertical_data = [
            str(wizard_id).zfill(2),
            wizard.company_id.l10n_ke_kra_pin or '',
            wizard.company_id.l10n_ke_nssf_number or '',
            wizard.company_id.name,
            f'{wizard.reference_month.zfill(2)}{wizard.reference_year}',
            total_income,
            total_member,
            total_employer,
            total_contribution,
            len(wizard.line_ids),
        ]

        row = 0
        for (vertical_header, vertical_point) in zip(vertical_headers, vertical_data):
            worksheet.write(row, 0, vertical_header, style_highlight)
            worksheet.write(row, 1, vertical_point, style_normal)
            row += 1

        row += in_between_blank_lines
        worksheet.set_row(row, horizontal_header_height)
        for col, horizontal_header in enumerate(horizontal_headers):
            worksheet.write(row, col, horizontal_header, style_highlight)
            worksheet.set_column(col, col, column_width)

        for payroll_line in horizontal_data:
            row += 1
            for col, payroll_point in enumerate(payroll_line):
                worksheet.write(row, col, payroll_point, style_normal)

        workbook.close()
        xlsx_data = output.getvalue()
        filename = _("nssf_report_%(year)s_%(month)s", year=wizard.reference_year, month=wizard.reference_month)
        response = request.make_response(
            xlsx_data,
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename={filename}.xlsx')],
        )
        return response

    @http.route(['/export/old_nhif/<int:wizard_id>'], type='http', auth='user')
    def export_nhif_report(self, wizard_id):
        wizard = request.env['l10n.ke.hr.payroll.nhif.report.wizard'].browse(wizard_id)
        if not wizard.exists() or not request.env.user.has_group('hr_payroll.group_hr_payroll_user'):
            return request.render(
                'http_routing.http_error',
                {
                    'status_code': 'Oops',
                    'status_message': _('It seems that you either not have the rights to access the nhif reports '
                                        'or that you try to access it outside normal circumstances. '
                                        'If you think there is a problem, please contact an administrator.')
                }
            )

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('nhif_report')
        style_highlight = workbook.add_format({'bold': True, 'pattern': 1, 'bg_color': '#E0E0E0', 'align': 'center'})
        style_normal = workbook.add_format({'align': 'center'})
        column_width = 25
        vertical_headers = [
            _('EMPLOYER CODE'),
            _('EMPLOYER NAME'),
            _('MONTH OF CONTRIBUTION'),
        ]

        vertical_data = [
            wizard.company_id.company_registry or '',
            wizard.company_id.name,
            '%s-%s' % (wizard.reference_year, wizard.reference_month),
        ]
        in_between_blank_lines = 1
        horizontal_headers = [
            _('PAYROLL NO'),
            _('LAST NAME'),
            _('FIRST NAME'),
            _('ID NO'),
            _('NHIF NO'),
            _('AMOUNT'),
        ]
        total_column = len(horizontal_headers) - 2
        total_str = _('TOTAL')
        total = 0

        horizontal_data = []
        for line in wizard.line_ids:
            sliced_name = line.employee_id.name.split(' ', maxsplit=1)
            horizontal_data.append((
                line.payslip_number or '',
                sliced_name[0],
                sliced_name[1] if len(sliced_name) > 1 else '',
                line.employee_identification_id or '',
                line.nhif_number or '',
                line.nhif_amount,
            ))
            total += line.nhif_amount

        row = 0
        for (vertical_header, vertical_point) in zip(vertical_headers, vertical_data):
            worksheet.write(row, 0, vertical_header, style_highlight)
            worksheet.write(row, 1, vertical_point, style_normal)
            row += 1

        row += in_between_blank_lines
        for col, horizontal_header in enumerate(horizontal_headers):
            worksheet.write(row, col, horizontal_header, style_highlight)
            worksheet.set_column(col, col, column_width)

        for payroll_line in horizontal_data:
            row += 1
            for col, payroll_point in enumerate(payroll_line):
                worksheet.write(row, col, payroll_point, style_normal)

        row += 1
        worksheet.write(row, total_column, total_str, style_highlight)
        worksheet.write(row, total_column + 1, total, style_normal)

        workbook.close()
        xlsx_data = output.getvalue()
        filename = _("nhif_report_%(year)s_%(month)s", year=wizard.reference_year, month=wizard.reference_month)
        response = request.make_response(
            xlsx_data,
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename={filename}.xlsx')],
        )
        return response
