# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from io import BytesIO
from copy import deepcopy

from odoo import http, _
from odoo.http import request
from odoo.tools.misc import xlsxwriter


class L10nInSalaryRegisterController(http.Controller):

    def _get_payslip_rules(self, employee_ids, payslips, struct_id=None):
        rule_by_name = []
        if struct_id and struct_id.rule_ids:
            rule_by_name = [(i.code, i.name) for i in struct_id.rule_ids]
        else:
            rule_by_name = [
                (rule.code, rule.name)
                for payslip in payslips
                for rule in payslip.struct_id.rule_ids
            ]
        child_dict = {code: [name, 0] for code, name in rule_by_name}
        rules_per_employee = {employee_id: deepcopy(child_dict) for employee_id in employee_ids}
        rules_by_name = dict(rule_by_name)
        return rules_by_name, rules_per_employee

    @http.route(['/export/salary-register/<int:wizard_id>'], type='http', auth='user')
    def export_salary_register(self, wizard_id):
        wizard = request.env['salary.register.wizard'].browse(wizard_id)
        if not wizard.exists() or not request.env.user.has_group('hr_payroll.group_hr_payroll_user'):
            return request.render(
                'http_routing.http_error',
                {
                    'status_code': 'Oops',
                    'status_message': _('It seems that you either not have the rights to access the Salary Register '
                                        'or that you try to access it outside normal circumstances. '
                                        'If you think there is a problem, please contact an administrator.')
                }
            )
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('salary_register_report')
        style_highlight = workbook.add_format({'bold': True, 'pattern': 1, 'bg_color': '#E0E0E0', 'align': 'center'})
        style_normal = workbook.add_format({'align': 'center'})
        column_width = 30

        date_from = str(wizard.date_from)
        date_to = str(wizard.date_to)
        employee_ids = wizard.employee_ids
        struct_id = wizard.struct_id

        #  VERTICAL HEADERS
        vertical_headers = [
            _('EMPLOYER ID'),
            _('EMPLOYER NAME'),
            _('FROM DATE'),
            _('TO DATE'),
        ]
        # VERTICAL DATA
        vertical_data = [
            wizard.company_id.company_registry or '',
            wizard.company_id.name,
            date_from,
            date_to,
        ]
        blank_lines = 1

        # HORIZONTAL HEADERS
        horizontal_headers = [
            _('EMPLOYEE CODE'),
            _('EMPLOYEE NAME'),
        ]

        # HORIZONTAL DATA
        domain = [('employee_id', 'in', employee_ids.ids), ('date_from', '>=', date_from), ('date_to', '<=', date_to), ('state', '=', 'paid')]
        if struct_id:
            domain.append(('struct_id', '=', struct_id.id))
        payslips_per_employee = dict(request.env['hr.payslip']._read_group(
                domain=domain,
                groupby=['employee_id'],
                aggregates=['id:recordset'],
            ))
        rules_by_name, rules_per_employee = self._get_payslip_rules(employee_ids, payslips_per_employee.values(), struct_id=struct_id)
        rules_per_employee = {
            employee: rules
            for employee, rules in rules_per_employee.items()
            if employee in payslips_per_employee
        }
        # Dynamically calculated headers
        horizontal_headers = [*horizontal_headers, *rules_by_name.values()]
        for employee_id, payslips in payslips_per_employee.items():
            rule_codes = payslips.struct_id.rule_ids.mapped('code')
            payslip_rules = payslips._get_line_values(rule_codes, compute_sum=True)
            for code, rule in payslip_rules.items():
                rules_per_employee[employee_id][code][1] += rule['sum']['total']

        horizontal_data = []
        for employee_id in rules_per_employee:
            dynamic_horizontal_data = [data[1] for data in rules_per_employee[employee_id].values()]
            horizontal_data.append((
                employee_id.registration_number or "",
                employee_id.name,
                *dynamic_horizontal_data,
            ))

        # WRITE IN WORKSHEET
        row = 0
        for (vertical_header, vertical_point) in zip(vertical_headers, vertical_data):
            worksheet.write(row, 0, vertical_header, style_highlight)
            worksheet.write(row, 1, vertical_point, style_normal)
            row += 1

        row += blank_lines
        for col, horizontal_header in enumerate(horizontal_headers):
            worksheet.write(row, col, horizontal_header, style_highlight)
            worksheet.set_column(col, col, column_width)

        for payroll_line in horizontal_data:
            row += 1
            for col, payroll_point in enumerate(payroll_line):
                worksheet.write(row, col, payroll_point, style_normal)

        row += 1
        workbook.close()
        xlsx_data = output.getvalue()
        date_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
        filename = _("salary_register_report_%(year)s_%(month)s", year=date_obj.year, month=date_obj.month)
        response = request.make_response(
            xlsx_data,
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename={filename}.xlsx')],
        )
        return response
