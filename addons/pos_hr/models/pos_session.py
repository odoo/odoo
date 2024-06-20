# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class PosSession(models.Model):
    _inherit = 'pos.session'

<<<<<<< saas-17.4
    @api.model
    def _load_pos_data_models(self, config_id):
        data = super()._load_pos_data_models(config_id)
        config_id = self.env['pos.config'].browse(config_id)
        if config_id.module_pos_hr:
            data += ['hr.employee']
        return data
||||||| 4dadd6ebc14338231f6ee1e8cb87423a0119e028

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
            employees = response['data']['hr.employee']
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
                    'id': employee['id'],
                    'name': employee['name'],
                }

            response['data']['hr.employee'] = employees

        return response
=======
    def _domain_hr_employee(self):
        domain = self.config_id._employee_domain(self.user_id.id)

        return domain

    def _load_data_params(self, config_id):
        params = super()._load_data_params(config_id)
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
            employees = response['data']['hr.employee']
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
                    'id': employee['id'],
                    'name': employee['name'],
                }

            response['data']['hr.employee'] = employees

        return response
>>>>>>> 966f31cb2cd3407653a2e508c366d2be7c01d559
