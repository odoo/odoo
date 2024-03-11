# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _pos_data_process(self, loaded_data):
        super()._pos_data_process(loaded_data)
        if self.config_id.module_pos_hr:
            loaded_data['employee_by_id'] = {employee['id']: employee for employee in loaded_data['hr.employee']}

    def _pos_ui_models_to_load(self):
        result = super()._pos_ui_models_to_load()
        if self.config_id.module_pos_hr:
            new_model = 'hr.employee'
            if new_model not in result:
                result.append(new_model)
        return result

    def _loader_params_hr_employee(self):
        if len(self.config_id.employee_ids) > 0:
            domain = ['&', ('company_id', '=', self.config_id.company_id.id), '|', ('user_id', '=', self.user_id.id), ('id', 'in', self.config_id.employee_ids.ids)]
        else:
            domain = [('company_id', '=', self.config_id.company_id.id)]
        return {'search_params': {'domain': domain, 'fields': ['name', 'id', 'user_id'], 'load': False}}

    def _get_pos_ui_hr_employee(self, params):
        employees = self.env['hr.employee'].search_read(**params['search_params'])
        employee_ids = [employee['id'] for employee in employees]
        user_ids = [employee['user_id'] for employee in employees if employee['user_id']]
        manager_ids = self.env['res.users'].browse(user_ids).filtered(lambda user: self.config_id.group_pos_manager_id in user.groups_id).mapped('id')

        employees_barcode_pin = self.env['hr.employee'].browse(employee_ids).get_barcodes_and_pin_hashed()
        bp_per_employee_id = {bp_e['id']: bp_e for bp_e in employees_barcode_pin}
        for employee in employees:
            employee['role'] = 'manager' if employee['user_id'] and employee['user_id'] in manager_ids else 'cashier'
            employee['barcode'] = bp_per_employee_id[employee['id']]['barcode']
            employee['pin'] = bp_per_employee_id[employee['id']]['pin']

        return employees
