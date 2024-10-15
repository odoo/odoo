# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.addons import point_of_sale, hr


class ResConfigSettings(point_of_sale.ResConfigSettings, hr.ResConfigSettings):

    # pos.config fields
    pos_basic_employee_ids = fields.Many2many(related='pos_config_id.basic_employee_ids', readonly=False,
        help='If left empty, all employees can log in to PoS')
    pos_advanced_employee_ids = fields.Many2many(related='pos_config_id.advanced_employee_ids', readonly=False,
        help='If left empty, only Odoo users have extended rights in PoS')

    @api.onchange('pos_basic_employee_ids')
    def _onchange_basic_employee_ids(self):
        for employee in self.pos_basic_employee_ids:
            if employee in self.pos_advanced_employee_ids:
                self.pos_advanced_employee_ids -= employee

    @api.onchange('pos_advanced_employee_ids')
    def _onchange_advanced_employee_ids(self):
        for employee in self.pos_advanced_employee_ids:
            if employee in self.pos_basic_employee_ids:
                self.pos_basic_employee_ids -= employee
