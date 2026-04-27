# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import contextlib
import csv
import io
import logging
import re

from odoo import http, fields
from odoo.http import request, content_disposition
from odoo.tools import pycompat
from odoo.tools.misc import xlsxwriter

_logger = logging.getLogger(__name__)


class L10nBeHrPayrollEcoVoucherController(http.Controller):

    @http.route(["/export/ecovouchers/<int:wizard_id>"], type='http', auth='user')
    def export_eco_vouchers(self, wizard_id):
        wizard = request.env['l10n.be.eco.vouchers.wizard'].browse(wizard_id)
        if not wizard.exists() or not request.env.user.has_group('hr_payroll.group_hr_payroll_user'):
            return request.render(
                'http_routing.http_error', {
                    'status_code': 'Oops',
                    'status_message': "Please contact an administrator..."})

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Worksheet')
        style_highlight = workbook.add_format({'bold': True, 'pattern': 1, 'bg_color': '#E0E0E0', 'align': 'center'})
        style_normal = workbook.add_format({'align': 'center'})
        row = 0
        reference_year = wizard.reference_year

        headers = [
            "Numéro de registre national",
            "Salarié nom",
            "Salarié prénom",
            "Numéro interne du salarié",
            "Nombre de chèques [a]",
            "Valeur faciale du chèque [b]",
            "Total [a] x [b]",
            "Date de naissance du salarié (dd/mm/yyyy)",
            "Sexe du salarié (m/f)",
            "Langue du salarié (nl/fr/en)",
            "Centre de coûts (maximum 10 caractères)",
            "Numéro d'entreprise",
            "Adresse de livraison rue",
            "Adresse de livraison numéro",
            "Adresse de livraison boite",
            "Adresse de livraison code postal",
            "Adresse de livraison ville",
            "Statut contrat",
        ]

        rows = []
        for line in wizard.line_ids:
            employee = line.employee_id
            employee_name = re.sub(r"[\(].*?[\)]", "", employee.legal_name)
            quantity = 1
            amount = round(line.amount, 2)
            birthdate = employee.birthday or fields.Date.today()
            lang = employee.lang
            if lang == 'fr_FR':
                lang = 'FR'
            elif lang == 'nl_NL':
                lang = 'NL'
            else:
                lang = 'EN'

            rows.append((
                employee.niss.replace('.', '').replace('-', '') if employee.niss else '',
                employee_name.split(' ')[0],
                ' '.join(employee_name.split(' ')[1:]),
                ' ',
                quantity,
                amount,
                quantity * amount,
                f'{birthdate:%m/%d/%Y}',
                'F' if employee.gender == 'female' else 'M',
                lang,
                ' ', ' ', ' ', ' ', ' ', ' ', ' ',
                'Actif' if employee.contract_id.state == 'open' else 'Fin de la collaboration',
            ))

        col = 0
        for header in headers:
            worksheet.write(row, col, header, style_highlight)
            worksheet.set_column(col, col, 15)
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
        response = request.make_response(
            xlsx_data,
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename=Eco_vouchers_{reference_year}.xlsx')],
        )
        return response

class L10nBeHrPayrollGroupInsuranceController(http.Controller):

    @http.route(["/export/group_insurance/<int:wizard_id>"], type='http', auth='user')
    def export_group_insurance(self, wizard_id):
        wizard = request.env['l10n.be.group.insurance.wizard'].browse(wizard_id)
        if not wizard.exists() or not request.env.user.has_group('hr_payroll.group_hr_payroll_user'):
            return request.render(
                'http_routing.http_error', {
                    'status_code': 'Oops',
                    'status_message': "Please contact an administrator..."})

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Worksheet')
        style_highlight = workbook.add_format({'bold': True, 'pattern': 1, 'bg_color': '#E0E0E0', 'align': 'center'})
        style_normal = workbook.add_format({'align': 'center'})
        row = 0

        headers = [
            "NISS",
            "Name",
            "Amount",
            "Birthdate",
        ]

        rows = []
        for line in wizard.line_ids:
            employee = line.employee_id
            employee_name = employee.legal_name
            amount = round(line.amount, 2)
            birthdate = employee.birthday or fields.Date.today()

            rows.append((
                employee.niss.replace('.', '').replace('-', '') if employee.niss else '',
                employee_name,
                amount,
                '%s/%s/%s' % (birthdate.day, birthdate.month, birthdate.year),
            ))

        col = 0
        for header in headers:
            worksheet.write(row, col, header, style_highlight)
            worksheet.set_column(col, col, 15)
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
        response = request.make_response(
            xlsx_data,
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', 'attachment; filename=group_insurance.xlsx')],
        )
        return response

class L10nBeHrPayrollWarrantPayslipsController(http.Controller):
    @http.route("/export/warrant_payslips/<int:wizard_id>", type='http', auth='user')
    def export_employee_file(self, wizard_id):
        wizard = request.env['hr.payroll.generate.warrant.payslips'].browse(wizard_id)
        with io.StringIO() as buf:
            writer = csv.writer(buf, quoting=1)
            writer.writerow(["Employee Name", "ID", "Commission on Target"])
            writer.writerows(
                [line.employee_id.name, line.employee_id.id, line.commission_amount]
                for line in wizard.line_ids
            )
            content = buf.getvalue()

        name = "exported_employees.csv"
        wizard.write({'state': 'export', 'name': name})

        headers = [
            ('Content-Type', 'text/csv'),
            ('Content-Disposition', content_disposition('exported_employees.csv'))
        ]
        return request.make_response(content, headers=headers)
