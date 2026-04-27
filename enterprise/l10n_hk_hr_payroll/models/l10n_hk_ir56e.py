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

        report_info = self._get_report_info_data()

        employees_data = []
        for employee in employees:
            sheet_values = {
                **self._get_employee_data(employee),
                **self._get_employee_spouse_data(employee),
                'TypeOfForm': self.type_of_form,
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

        return {'data': report_info, 'employees_data': employees_data}

    def _get_pdf_report(self):
        return self.env.ref('l10n_hk_hr_payroll.action_report_employee_ir56e')

    def _get_pdf_filename(self, employee):
        self.ensure_one()
        return _('%(employee_name)s_-_IR56E-%(submission_date)s', employee_name=employee.name, submission_date=self.submission_date)

    def _post_process_rendering_data_pdf(self, rendering_data):
        result = {}
        for sheet_values in rendering_data['employees_data']:
            result[sheet_values['employee']] = {**sheet_values, **rendering_data['data']}
        return result

    def _get_posted_document_owner(self, employee):
        return employee.contract_id.hr_responsible_id or self.env.user
