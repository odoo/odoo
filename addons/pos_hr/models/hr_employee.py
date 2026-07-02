# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib

from odoo import api, models, _
from odoo.exceptions import UserError


class HrEmployee(models.Model):
    _name = 'hr.employee'
    _inherit = ['hr.employee', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data, config):
        return config._employee_domain(config.current_user_id.id)

    @api.model
    def _load_pos_data_fields(self, config):
        return ['name', 'user_id', 'work_contact_id']

    def _server_date_to_domain(self, domain):
        return domain

    @api.model
    def _load_pos_data_read(self, records, config):
        # NOTE:
        # hr.employee have a public fallback mechanism
        # where users without read access may still receive records from
        # the corresponding public model (hr.employee.public) so thats why we are bypassing
        # the access right.
        fields = self._load_pos_data_fields(config)
        read_records = records.read(fields, load=False)
        manager_ids = records.filtered(lambda emp: config.group_pos_manager_id.id in emp.user_id.all_group_ids.ids).ids

        employees_barcode_pin = records.get_barcodes_and_pin_hashed()
        bp_per_employee_id = {bp_e['id']: bp_e for bp_e in employees_barcode_pin}

        for employee in read_records:
            if employee['id'] in manager_ids:
                role = 'manager'
                employee['_user_role'] = 'admin'
            elif employee['id'] in config.manager_employee_ids.ids:
                role = 'manager'
            elif employee['id'] in config.restrictive_employee_ids.ids:
                role = 'restrictive'
            elif employee['id'] in config.cashier_employee_ids.ids:
                role = 'cashier'
            elif employee['id'] in config.supervised_employee_ids.ids:
                role = 'supervised'
            else:
                role = 'none'
            employee['_role'] = role
            employee['_barcode'] = bp_per_employee_id[employee['id']]['barcode']
            employee['_pin'] = bp_per_employee_id[employee['id']]['pin']

        return read_records

    def get_barcodes_and_pin_hashed(self):
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            return []
        # Apply visibility filters (record rules)
        visible_emp_ids = self.search([('id', 'in', self.ids)])
        employees_data = self.sudo().search_read([('id', 'in', visible_emp_ids.ids)], ['barcode', 'pin'])

        for e in employees_data:
            e['barcode'] = hashlib.sha1(e['barcode'].encode('utf8')).hexdigest() if e['barcode'] else False
            e['pin'] = hashlib.sha1(e['pin'].encode('utf8')).hexdigest() if e['pin'] else False
        return employees_data

    @api.ondelete(at_uninstall=False)
    def _unlink_except_active_pos_session(self):
        configs = self.env['pos.config'].sudo().search([
            ('module_pos_hr', '=', True),
            ('current_session_id', '!=', False),
        ])
        for employee in self:
            linked_configs = configs.filtered(
                lambda c: employee in (
                    c.cashier_employee_ids
                    | c.manager_employee_ids
                    | c.supervised_employee_ids
                    | c.restrictive_employee_ids
                )
            )
            if linked_configs:
                raise UserError(_(
                    "You cannot delete an employee that may be used in an active PoS session. "
                    "Close the session(s) first:\n"
                    "Employee: %(employee)s - PoS Config(s): %(config_list)s",
                    employee=employee.name,
                    config_list=", ".join(linked_configs.mapped("name")),
                ))
