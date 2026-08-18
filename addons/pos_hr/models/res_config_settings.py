# -*- coding: utf-8 -*-

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # pos.config fields
    pos_supervised_employee_ids = fields.Many2many(related='pos_config_id.supervised_employee_ids', readonly=False,
        help='Can process sales, but a higher level must approve before payment is closed.')
    pos_restrictive_employee_ids = fields.Many2many(related='pos_config_id.restrictive_employee_ids', readonly=False,
        help='Can process sales and close payments, but not apply discounts, refunds, or cancel orders.')
    pos_cashier_employee_ids = fields.Many2many(related='pos_config_id.cashier_employee_ids', readonly=False,
        help=' Full register access. Can process sales, discounts, refunds, and close out payments.')
    pos_manager_employee_ids = fields.Many2many(related='pos_config_id.manager_employee_ids', readonly=False,
        help=' Full access, including reporting, cash management, and session close.')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            pos_config_id = vals.get('pos_config_id')
            if pos_config_id:
                vals['pos_manager_employee_ids'] = vals.get('pos_manager_employee_ids', []) + [[4, emp_id] for emp_id in self.env['pos.config'].browse(pos_config_id)._get_group_pos_manager().user_ids.employee_id.ids]
        return super().create(vals_list)

    def _remove_pos_employee_from_fields(self, employee, field_list):
        for field in field_list:
            if employee in self[field]:
                self[field] -= employee
                break

    @api.onchange('pos_supervised_employee_ids')
    def _onchange_pos_supervised_employee_ids(self):
        role_fields = [
            'pos_cashier_employee_ids',
            'pos_manager_employee_ids',
            'pos_restrictive_employee_ids',
        ]
        for employee in self.pos_supervised_employee_ids:
            if employee.user_id._has_group('point_of_sale.group_pos_manager'):
                self.pos_supervised_employee_ids -= employee
            else:
                self._remove_pos_employee_from_fields(employee, role_fields)

    @api.onchange('pos_restrictive_employee_ids')
    def _onchange_pos_restrictive_employee_ids(self):
        role_fields = [
            'pos_cashier_employee_ids',
            'pos_manager_employee_ids',
            'pos_supervised_employee_ids',
        ]
        for employee in self.pos_restrictive_employee_ids:
            if employee.user_id._has_group('point_of_sale.group_pos_manager'):
                self.pos_restrictive_employee_ids -= employee
            else:
                self._remove_pos_employee_from_fields(employee, role_fields)

    @api.onchange('pos_cashier_employee_ids')
    def _onchange_pos_cashier_employee_ids(self):
        role_fields = [
            'pos_manager_employee_ids',
            'pos_restrictive_employee_ids',
            'pos_supervised_employee_ids',
        ]
        for employee in self.pos_cashier_employee_ids:
            if employee.user_id._has_group('point_of_sale.group_pos_manager'):
                self.pos_cashier_employee_ids -= employee
            else:
                self._remove_pos_employee_from_fields(employee, role_fields)

    @api.onchange('pos_manager_employee_ids')
    def _onchange_pos_manager_employee_ids(self):
        role_fields = [
            'pos_cashier_employee_ids',
            'pos_restrictive_employee_ids',
            'pos_supervised_employee_ids',
        ]
        for employee in self.pos_manager_employee_ids:
            self._remove_pos_employee_from_fields(employee, role_fields)
