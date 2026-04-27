# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from datetime import date
from collections import defaultdict
from lxml import etree

from odoo import _, models, api
from odoo.exceptions import UserError
from odoo.tools import format_list


class L10nHkIr56f(models.Model):
    _name = 'l10n_hk.ir56f'
    _inherit = 'l10n_hk.ird'
    _description = 'IR56F Sheet'
    _order = 'start_period'

    @api.depends('xml_file')
    def _compute_validation_state(self):
        xsd_schema_file_path = self._get_xml_resource('ir56f.xsd')
        xsd_root = etree.parse(xsd_schema_file_path)
        schema = etree.XMLSchema(xsd_root)

        no_xml_file_records = self.filtered(lambda record: not record.xml_file)
        no_xml_file_records.update({
            'xml_validation_state': 'normal',
            'error_message': False})
        for record in self - no_xml_file_records:
            xml_root = etree.fromstring(base64.b64decode(record.xml_file))
            try:
                schema.assertValid(xml_root)
                record.xml_validation_state = 'done'
            except etree.DocumentInvalid as err:
                record.xml_validation_state = 'invalid'
                record.error_message = str(err)

    @api.depends('start_year', 'start_month', 'end_year', 'end_month')
    def _compute_period(self):
        super()._compute_period()
        for record in self:
            record.end_period = date(record.start_year + 1, int(record.end_month), 31)

    @api.model
    def _check_employees(self, employees):
        error_messages = super()._check_employees(employees)
        invalid_lines = self.line_ids.filtered(lambda line: not line.employee_id.departure_reason_id.l10n_hk_ir56f_code)
        if invalid_lines:
            error_messages += "\n" + _(
                "The following employees don't have a valid departure reason: %s",
                format_list(self.env, invalid_lines.employee_id.mapped("name")),
            )
        return error_messages

    def _get_rendering_data(self, employees):
        self.ensure_one()

        employees_error = self._check_employees(employees)
        if employees_error:
            return {'error': employees_error}

        report_info = self._get_report_info_data()

        payslip_info = self._get_employees_payslip_data(employees)
        if 'error' in payslip_info:
            return {'error': payslip_info['error']}
        all_payslips = payslip_info['all_payslips']

        employee_payslips = defaultdict(lambda: self.env['hr.payslip'])
        for payslip in all_payslips:
            employee_payslips[payslip.employee_id] |= payslip

        line_codes = ['BASIC', 'COMMISSION', 'REFERRAL_FEE', 'END_OF_YEAR_PAYMENT', 'BACKPAY', 'ALW.INT', 'HRA', 'MPF_GROSS', 'EEMC', 'ERMC', 'EEVC', 'ERVC']
        all_line_values = all_payslips._get_line_values(line_codes, vals_list=['total', 'quantity'])

        sequence = 0
        employees_data = []
        for employee in employee_payslips:
            sheet_line = self.line_ids.filtered(lambda line: line.employee_id == employee)
            payslips = employee_payslips[employee]
            sequence += 1

            mapped_total = {
                code: sum(all_line_values[code][p.id]['total'] for p in payslips)
                for code in line_codes}

            start_date = self.start_period if self.start_period > employee.first_contract_date else employee.first_contract_date
            end_date = employee.contract_id.date_end if employee.contract_id.date_end else self.end_period

            rental_ids = employee.l10n_hk_rental_ids.filtered_domain([
                ('state', 'in', ['open', 'close']),
                ('date_start', '<=', self.end_period),
                '|', ('date_end', '>', start_date), ('date_end', '=', False),
            ]).sorted('date_start')

            departure_code = sheet_line.employee_id.departure_reason_id.l10n_hk_ir56f_code
            if departure_code == 5:
                departure_reason_other = sheet_line.employee_id.departure_description
                departure_reason_str = sheet_line.employee_id.departure_description
            else:
                departure_reason_other = ''
                departure_reason_str = {
                    '1': 'Resignation',
                    '2': 'Retirement',
                    '3': 'Dismissal',
                    '4': 'Death',
                }[departure_code]

            sheet_values = {
                **self._get_employee_data(employee),
                **self._get_employee_spouse_data(employee),
                'date_from': self.start_period,
                'date_to': self.end_period,
                'SheetNo': sequence,
                'TypeOfForm': self.type_of_form,
                'CESSATION_DATE': end_date,
                'CESSATION_REASON': departure_code,
                'CESSATION_REASON_OTHER': departure_reason_other,
                'cessation_reason_str': departure_reason_str,
                'RTN_ASS_YR': self.end_year,
                'StartDateOfEmp': start_date,
                'EndDateOfEmp': end_date,
                'AmtOfSalary': int(mapped_total['BASIC']),
                'AmtOfCommFee': int(mapped_total['COMMISSION']) + int(mapped_total['REFERRAL_FEE']),
                'AmtOfBonus': int(mapped_total['END_OF_YEAR_PAYMENT']),
                'AmtOfBpEtc': int(mapped_total['BACKPAY']),
                'NatureOtherRAP1': 'Internet Allowance' if int(mapped_total['ALW.INT']) else '',
                'AmtOfOtherRAP1': int(mapped_total['ALW.INT']),
                'TotalIncome': int(mapped_total['MPF_GROSS'] - mapped_total['HRA']),
                'PlaceOfResInd': int(bool(rental_ids)),
                'AddrOfPlace1': '',
                'NatureOfPlace1': '',
                'PerOfPlace1': '',
                'RentPaidEe1': 0,
                'RentRefund1': 0,
                'AddrOfPlace2': '',
                'NatureOfPlace2': '',
                'PerOfPlace2': '',
                'RentPaidEe2': 0,
                'RentRefund2': 0,
                'AmtOfEEMC': int(mapped_total['EEMC']),
                'AmtOfERMC': int(mapped_total['ERMC']),
                'AmtOfEEVC': int(mapped_total['EEVC']),
                'AmtOfERVC': int(mapped_total['ERVC']),
            }

            for count, rental in enumerate(rental_ids):
                payslips_rental = payslips.filtered_domain([
                    ('date_from', '>=', rental.date_start),
                    ('date_to', '<=', rental.date_end or self.end_period),
                ])
                date_start_rental = rental.date_start if rental.date_start > start_date else start_date
                date_start_rental_str = date_start_rental.strftime('%Y%m%d')
                date_end_rental_str = (rental.date_end or self.end_period).strftime('%Y%m%d')
                period_rental_str = '{} - {}'.format(date_start_rental_str, date_end_rental_str)

                amount_rental = sum(all_line_values['HRA'][p.id]['total'] for p in payslips_rental)

                sheet_values.update({
                    'AddrOfPlace%s' % (count + 1): rental.address,
                    'NatureOfPlace%s' % (count + 1): rental.nature,
                    'PerOfPlace%s' % (count + 1): period_rental_str,
                    'RentPaidEe%s' % (count + 1): int(amount_rental),
                    'RentRefund%s' % (count + 1): int(amount_rental),
                })

            employees_data.append(sheet_values)

        sheets_count = len(employees_data)

        total_data = {
            'NoRecordBatch': '{:05}'.format(sheets_count),
            'TotIncomeBatch': int(sum(ed['TotalIncome'] for ed in employees_data)),
        }

        return {'data': report_info, 'employees_data': employees_data, 'total_data': total_data}

    def action_generate_xml(self):
        self.ensure_one()
        self.xml_filename = 'IR56F_-_%s.xml' % (self.start_year)
        data = self._get_rendering_data(self.line_ids.employee_id)
        if 'error' in data:
            raise UserError(data['error'])
        xml_str = self.env['ir.qweb']._render('l10n_hk_hr_payroll.ir56f_xml_report', data)

        # Prettify xml string
        root = etree.fromstring(xml_str, parser=etree.XMLParser(remove_blank_text=True))
        xml_formatted_str = etree.tostring(root, pretty_print=True, encoding='utf-8', xml_declaration=True, standalone=True)

        self.xml_file = base64.encodebytes(xml_formatted_str)
        self.state = 'waiting'

    def _get_pdf_report(self):
        return self.env.ref('l10n_hk_hr_payroll.action_report_employee_ir56f')

    def _get_pdf_filename(self, employee):
        self.ensure_one()
        return _('%(employee_name)s_-_IR56F_-_%(start_year)s', employee_name=employee.name, start_year=self.start_year)

    def _post_process_rendering_data_pdf(self, rendering_data):
        result = {}
        for sheet_values in rendering_data['employees_data']:
            result[sheet_values['employee']] = {**sheet_values, **rendering_data['data']}
        return result

    def _get_posted_document_owner(self, employee):
        return employee.contract_id.hr_responsible_id or self.env.user
