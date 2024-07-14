# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from collections import defaultdict

from odoo import _, api, fields, models


class L10nHkIr56g(models.Model):
    _name = 'l10n_hk.ir56g'
    _inherit = 'l10n_hk.ird'
    _description = 'IR56G Sheet'
    _order = 'start_period'

    appendice_line_ids = fields.One2many('l10n_hk.ir56g.line', 'sheet_id', string="Appendices")

    @api.depends('start_year', 'start_month', 'end_year', 'end_month')
    def _compute_period(self):
        super()._compute_period()
        for record in self:
            record.end_period = date(record.start_year + 1, int(record.end_month), 31)

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
            end_date = employee.contract_id.date_end if employee.contract_id.date_end else self.end_period

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
                'EndDateOfEmp': end_date,
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

    def _get_pdf_report(self):
        return self.env.ref('l10n_hk_hr_payroll.action_report_employee_ir56g')

    def _get_pdf_filename(self, employee):
        self.ensure_one()
        return _('%s_-_IR56G_-_%s', employee.name, self.start_year)

    def _post_process_rendering_data_pdf(self, rendering_data):
        result = {}
        for sheet_values in rendering_data['employees_data']:
            appendice_line = self.appendice_line_ids.filtered(lambda l: l.employee_id == sheet_values['employee'])
            line_values = appendice_line._get_line_details() if appendice_line else {}
            result[sheet_values['employee']] = {**sheet_values, **rendering_data['data'], **line_values}
        return result

    def _get_posted_document_owner(self, employee):
        return employee.contract_id.hr_responsible_id or self.env.user


class L10nHkIr56bLine(models.Model):
    _name = 'l10n_hk.ir56g.line'
    _description = 'IR56G Line'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    sheet_id = fields.Many2one('l10n_hk.ir56g', string='IR56G', required=True, ondelete='cascade')

    leave_hk_date = fields.Date(string='Leave HK Date')
    is_salary_tax_borne = fields.Boolean(string='Salary Tax Borne By Employer')
    has_money_payable_held_under_ird = fields.Boolean(string='Has Money Payable Held Under IRD')
    amount_money_payable = fields.Float(string='Amount of Money Payable')
    reason_no_money_payable = fields.Char(string='Reason of No Money Payable')
    reason_departure = fields.Selection([
        ('homeland', 'Return to homeland'),
        ('secondment', 'Secondment'),
        ('emigration', 'Emigration'),
        ('other', 'Other')
    ], string='Reason of Departure')
    other_reason_departure = fields.Char(string='Other Reason of Departure')
    will_return_hk = fields.Boolean(string='Will Return to HK')
    date_return = fields.Date(string='Date of Return')
    has_non_exercised_stock_options = fields.Boolean(string='Has Non-Exercised Stock Options')
    amount_non_exercised_stock_options = fields.Float(string='Amount of Non-Exercised Stock Options')
    date_grant = fields.Date(string='Date of Grant')

    _sql_constraints = [
        ('unique_employee', 'unique(employee_id, sheet_id)', 'An employee can only have one IR56G line per sheet.'),
    ]

    def _get_line_details(self):
        self.ensure_one()
        return {
            'leave_hk_date': self.leave_hk_date,
            'is_salary_tax_borne': self.is_salary_tax_borne,
            'has_money_payable_held_under_ird': self.has_money_payable_held_under_ird,
            'amount_money_payable': self.amount_money_payable,
            'reason_no_money_payable': self.reason_no_money_payable,
            'reason_departure': self.reason_departure,
            'other_reason_departure': self.other_reason_departure,
            'will_return_hk': self.will_return_hk,
            'date_return': self.date_return,
            'has_non_exercised_stock_options': self.has_non_exercised_stock_options,
            'amount_non_exercised_stock_options': self.amount_non_exercised_stock_options,
            'date_grant': self.date_grant,
        }
