# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.tools import format_date


class L10nHkIr56e(models.Model):
    _name = 'l10n_hk.ir56e'
    _inherit = 'l10n_hk.ird'
    _description = 'IR56E Sheet'
    _order = 'submission_date'

    @api.depends('submission_date')
    def _compute_display_name(self):
        for sheet in self:
            sheet.display_name = format_date(self.env, sheet.submission_date, date_format="MMMM y", lang_code=self.env.user.lang)

    def _get_rendering_data(self, employees):
        self.ensure_one()

        employees_error = self._check_employees(employees)
        if employees_error:
            return {'error': employees_error}

        main_data = self._get_main_data()
        employees_data = []
        for employee in employees:
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

            sheet_values = {
                'employee': employee,
                'employee_id': employee.id,
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
                'employee_address': employee_address,
                'Capacity': employee.job_title,
                'date_of_commencement': employee.first_contract_date,
                'monthly_salary': employee.contract_id.wage,
                'PlaceOfResInd': int(bool(employee.l10n_hk_rental_id)),
            }

            if employee.l10n_hk_rental_id:
                sheet_values.update({
                    'AddrOfPlace': employee.l10n_hk_rental_id.address,
                    'NatureOfPlace': employee.l10n_hk_rental_id.nature,
                    'RentPaidEe': employee.l10n_hk_rental_id.amount,
                    'RentRefund': employee.l10n_hk_rental_id.amount,
                })

            employees_data.append(sheet_values)

        return {'data': main_data, 'employees_data': employees_data}

    def _get_pdf_report(self):
        return self.env.ref('l10n_hk_hr_payroll.action_report_employee_ir56e')

    def _get_pdf_filename(self, employee):
        self.ensure_one()
        return _('%s_-_IR56E-%s', employee.name, self.submission_date)

    def _post_process_rendering_data_pdf(self, rendering_data):
        result = {}
        for sheet_values in rendering_data['employees_data']:
            result[sheet_values['employee']] = {**sheet_values, **rendering_data['data']}
        return result

    def _get_posted_document_owner(self, employee):
        return employee.contract_id.hr_responsible_id or self.env.user
