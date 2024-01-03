# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'


    def _domain_hr_employee(self):
        if len(self.config_id.basic_employee_ids) > 0:
            domain = [
                '&', ('company_id', '=', self.config_id.company_id.id),
                '|', ('user_id', '=', self.user_id.id), ('id', 'in', self.config_id.basic_employee_ids.ids + self.config_id.advanced_employee_ids.ids)]
        else:
            domain = [('company_id', '=', self.config_id.company_id.id)]

        return domain


    def _load_data_params(self, config_id):
        params = super()._load_data_params(config_id)

        if config_id.module_pos_hr:
            params['product.product']['fields'].append('all_product_tag_ids')
            params.update({
                'hr.employee': {
                    'domain': self._domain_hr_employee(),
                    'fields': ['name', 'id', 'user_id', 'work_contact_id'],
                },
            })

        return params

    def load_data(self, models_to_load, only_data=False):
        response = super().load_data(models_to_load, only_data)

        if len(models_to_load) == 0 or 'hr.employee' in models_to_load:
            employees = response['data'].get('hr.employee') or []
            employee_ids = [employee['id'] for employee in employees]
            user_ids = [employee['user_id'] for employee in employees if employee['user_id']]
            manager_ids = self.env['res.users'].browse(user_ids).filtered(lambda user: self.config_id.group_pos_manager_id in user.groups_id).mapped('id')

            employees_barcode_pin = self.env['hr.employee'].browse(employee_ids).get_barcodes_and_pin_hashed()
            bp_per_employee_id = {bp_e['id']: bp_e for bp_e in employees_barcode_pin}

            response['custom']['employee_security'] = {}
            for employee in employees:
                if employee['user_id'] and employee['user_id'] in manager_ids or employee['id'] in self.config_id.advanced_employee_ids.ids:
                    role = 'manager'
                else:
                    role = 'cashier'

                response['custom']['employee_security'][employee['id']] = {
                    'role': role,
                    'barcode': bp_per_employee_id[employee['id']]['barcode'],
                    'pin': bp_per_employee_id[employee['id']]['pin'],
                }

            response['data']['hr.employee'] = employees

        return response
