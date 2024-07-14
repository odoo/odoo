# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from lxml import etree
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import format_date



class L10nHkIr56b(models.Model):
    _name = 'l10n_hk.ir56b'
    _inherit = 'l10n_hk.ird'
    _description = 'IR56B Sheet'
    _order = 'start_period'

    type_of_form = fields.Selection(selection_add=[('S', "Supplementary")], ondelete={'S': 'cascade'})

    @api.depends('xml_file')
    def _compute_validation_state(self):
        annual_xsd_schema_file_path = self._get_xml_resource('ir56b_annual.xsd')
        extra_xsd_schema_file_path = self._get_xml_resource('ir56b_additional_replacement_supplementary.xsd')

        annual_xsd_root = etree.parse(annual_xsd_schema_file_path)
        extra_xsd_root = etree.parse(extra_xsd_schema_file_path)

        annual_schema = etree.XMLSchema(annual_xsd_root)
        extra_schema = etree.XMLSchema(extra_xsd_root)

        no_xml_file_records = self.filtered(lambda record: not record.xml_file)
        no_xml_file_records.update({
            'xml_validation_state': 'normal',
            'error_message': False})
        for record in self - no_xml_file_records:
            xml_root = etree.fromstring(base64.b64decode(record.xml_file))
            schema = annual_schema if record.type_of_form == 'O' else extra_schema
            try:
                schema.assertValid(xml_root)
                record.xml_validation_state = 'done'
            except etree.DocumentInvalid as err:
                record.xml_validation_state = 'invalid'
                record.error_message = str(err)

    def action_generate_declarations(self):
        for sheet in self:
            all_payslips = self.env['hr.payslip'].search([
                ('state', 'in', ['done', 'paid']),
                ('company_id', '=', sheet.company_id.id),
                ('date_from', '>=', sheet.start_period),
                ('date_to', '<=', sheet.end_period),
            ])
            all_employees = all_payslips.employee_id.filtered(lambda e: not e.contract_warning)
            sheet.update({
                'line_ids': [(5, 0, 0)] + [(0, 0, {
                    'employee_id': employee.id,
                    'res_model': 'l10n_hk.ir56b',
                    'res_id': sheet.id,
                }) for employee in all_employees]
            })
        return super().action_generate_declarations()

    @api.depends('start_period', 'end_period')
    def _compute_display_name(self):
        for sheet in self:
            sheet.display_name = _("From %s to %s",
                format_date(self.env, sheet.start_period, date_format="MMMM y", lang_code=self.env.user.lang),
                format_date(self.env, sheet.end_period, date_format="MMMM y", lang_code=self.env.user.lang),
            )

    def _get_rendering_data(self, employees):
        self.ensure_one()
        employees_data = []
        salary_structure = self.env.ref('l10n_hk_hr_payroll.hr_payroll_structure_cap57_employee_salary')
        all_payslips = self.env['hr.payslip'].search([
            ('state', 'in', ['done', 'paid']),
            ('date_from', '>=', self.start_period),
            ('date_to', '<=', self.end_period),
            ('employee_id', 'in', employees.ids),
            ('struct_id', '=', salary_structure.id),
        ])
        if not all_payslips:
            return {'error': _('There are no confirmed payslips for this period.')}
        all_employees = all_payslips.employee_id

        employees_error = self._check_employees(all_employees)
        if employees_error:
            return {'error': employees_error}

        main_data = self._get_main_data()
        employee_payslips = defaultdict(lambda: self.env['hr.payslip'])
        for payslip in all_payslips:
            employee_payslips[payslip.employee_id] |= payslip

        line_codes = ['BASIC', 'COMMISSION', 'REFERRAL_FEE', 'END_OF_YEAR_PAYMENT', 'BACKPAY', 'ALW.INT', 'HRA', 'MPF_GROSS', 'EEMC', 'ERMC', 'EEVC', 'ERVC']
        all_line_values = all_payslips._get_line_values(line_codes, vals_list=['total', 'quantity'])

        sequence = 0
        for employee in employee_payslips:
            payslips = employee_payslips[employee]
            sequence += 1

            mapped_total = {
                code: sum(all_line_values[code][p.id]['total'] for p in payslips)
                for code in line_codes}

            hkid, ppnum = '', ''
            if employee.identification_id:
                hkid = employee.identification_id.strip().upper()
            else:
                ppnum = f'{employee.passport_id}, {employee.l10n_hk_passport_place_of_issue}'

            spouse_name, spouse_hkid, spouse_passport = '', '', ''
            if employee.marital == 'married':
                spouse_name = employee.spouse_complete_name.upper()
                if employee.l10n_hk_spouse_identification_id:
                    spouse_hkid = employee.l10n_hk_spouse_identification_id.strip().upper()
                if employee.l10n_hk_spouse_passport_id or employee.l10n_hk_spouse_passport_place_of_issue:
                    spouse_passport = ', '.join(i for i in [employee.l10n_hk_spouse_passport_id, employee.l10n_hk_spouse_passport_place_of_issue] if i)

            employee_address = ', '.join(i for i in [
                employee.private_street, employee.private_street2, employee.private_city, employee.private_state_id.name, employee.private_country_id.name] if i)

            AREA_CODE_MAP = {
                'HK': 'H',
                'KLN': 'K',
                'NT': 'N',
            }
            area_code = AREA_CODE_MAP.get(employee.private_state_id.code, 'F')

            start_date = self.start_period if self.start_period > employee.first_contract_date else employee.first_contract_date

            rental_ids = employee.l10n_hk_rental_ids.filtered_domain([
                ('state', 'in', ['open', 'close']),
                ('date_start', '<=', self.end_period),
                '|', ('date_end', '>', start_date), ('date_end', '=', False),
            ]).sorted('date_start')

            sheet_values = {
                'employee': employee,
                'employee_id': employee.id,
                'date_from': self.start_period,
                'date_to': self.end_period,
                'SheetNo': sequence,
                'HKID': hkid,
                'TypeOfForm': self.type_of_form,
                'Surname': employee.l10n_hk_surname,
                'GivenName': employee.l10n_hk_given_name,
                'NameInChinese': employee.l10n_hk_name_in_chinese,
                'Sex': 'M' if employee.gender == 'male' else 'F',
                'MaritalStatus': 2 if employee.marital == 'married' else 1,
                'PpNum': ppnum,
                'SpouseName': spouse_name,
                'SpouseHKID': spouse_hkid,
                'SpousePpNum': spouse_passport,
                'RES_ADDR_LINE1': employee.private_street,
                'RES_ADDR_LINE2': employee.private_street2,
                'RES_ADDR_LINE3': employee.private_city,
                'employee_address': employee_address,
                'AreaCodeResAddr': area_code,
                'Capacity': employee.job_title,
                'RTN_ASS_YR': self.end_year,
                'StartDateOfEmp': start_date,
                'EndDateOfEmp': self.end_period,
                'AmtOfSalary': int(mapped_total['BASIC']),
                'AmtOfCommFee': int(mapped_total['COMMISSION']) + int(mapped_total['REFERRAL_FEE']),
                'AmtOfBonus': int(mapped_total['END_OF_YEAR_PAYMENT']),
                'AmtOfBpEtc': int(mapped_total['BACKPAY']),
                'NatureOtherRAP1': 'Internet Allowance' if int(mapped_total['ALW.INT']) else '',
                'AmtOfOtherRAP1': int(mapped_total['ALW.INT']),
                'TotalIncome': int(mapped_total['MPF_GROSS']),
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
            'TotIncomeBatch': int(sum(all_line_values['MPF_GROSS'][p.id]['total'] for p in all_payslips)),
        }

        return {'data': main_data, 'employees_data': employees_data, 'total_data': total_data}

    def action_generate_xml(self):
        self.ensure_one()
        self.xml_filename = 'IR56B_-_%s.xml' % (self.start_year)
        data = self._get_rendering_data(self.line_ids.employee_id)
        if 'error' in data:
            raise UserError(data['error'])
        xml_str = self.env['ir.qweb']._render('l10n_hk_hr_payroll.ir56b_xml_report', data)

        # Prettify xml string
        root = etree.fromstring(xml_str, parser=etree.XMLParser(remove_blank_text=True))
        xml_formatted_str = etree.tostring(root, pretty_print=True, encoding='utf-8', xml_declaration=True, standalone=True)

        self.xml_file = base64.encodebytes(xml_formatted_str)
        self.state = 'waiting'

    def _get_pdf_report(self):
        return self.env.ref('l10n_hk_hr_payroll.action_report_employee_ir56b')

    def _get_pdf_filename(self, employee):
        self.ensure_one()
        return _('%s_-_IR56B_-_%s', employee.name, self.start_year)

    def _post_process_rendering_data_pdf(self, rendering_data):
        result = {}
        for sheet_values in rendering_data['employees_data']:
            result[sheet_values['employee']] = {**sheet_values, **rendering_data['data']}
        return result
