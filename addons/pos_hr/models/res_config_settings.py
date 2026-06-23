# -*- coding: utf-8 -*-

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # pos.config fields
    pos_cashier_employee_ids = fields.Many2many(related='pos_config_id.cashier_employee_ids', readonly=False,
        help='If left empty, all employees can log in to PoS')
    pos_manager_employee_ids = fields.Many2many(related='pos_config_id.manager_employee_ids', readonly=False,
        help='Employees linked to users with the PoS Manager role are automatically added to this list')
    pos_restrictive_employee_ids = fields.Many2many(related='pos_config_id.restrictive_employee_ids', readonly=False,
        help='If left empty, all employees can log in to PoS')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            pos_config_id = vals.get('pos_config_id')
            if pos_config_id:
                vals['pos_manager_employee_ids'] = vals.get('pos_manager_employee_ids', []) + [[4, emp_id] for emp_id in self.env['pos.config'].browse(pos_config_id)._get_group_pos_manager().user_ids.employee_id.ids]
        return super().create(vals_list)

    @api.onchange('pos_restrictive_employee_ids')
    def _onchange_restrictive_employee_ids(self):
        for employee in self.pos_restrictive_employee_ids:
            if employee.user_id._has_group('point_of_sale.group_pos_manager'):
                self.pos_restrictive_employee_ids -= employee
            elif employee in self.pos_cashier_employee_ids:
                self.pos_cashier_employee_ids -= employee
            elif employee in self.pos_manager_employee_ids:
                self.pos_manager_employee_ids -= employee

    @api.onchange('pos_cashier_employee_ids')
    def _onchange_cashier_employee_ids(self):
        for employee in self.pos_cashier_employee_ids:
            if employee.user_id._has_group('point_of_sale.group_pos_manager'):
                self.pos_cashier_employee_ids -= employee
            elif employee in self.pos_manager_employee_ids:
                self.pos_manager_employee_ids -= employee
            elif employee in self.pos_restrictive_employee_ids:
                self.pos_restrictive_employee_ids -= employee

    @api.onchange('pos_manager_employee_ids')
    def _onchange_manager_employee_ids(self):
        for employee in self.pos_manager_employee_ids:
            if employee in self.pos_cashier_employee_ids:
                self.pos_cashier_employee_ids -= employee
            if employee in self.pos_restrictive_employee_ids:
                self.pos_restrictive_employee_ids -= employee
