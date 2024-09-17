# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.osv.expression import AND


class PosConfig(models.Model):
    _inherit = 'pos.config'

    minimal_employee_ids = fields.Many2many(
        'hr.employee', 'pos_hr_minimal_employee_hr_employee', string="Employees with minimal access",
        help='If left empty, all employees can log in to PoS')
    basic_employee_ids = fields.Many2many(
        'hr.employee', 'pos_hr_basic_employee_hr_employee', string="Employees with basic access",
        help='If left empty, all employees can log in to PoS')
    advanced_employee_ids = fields.Many2many(
        'hr.employee', 'pos_hr_advanced_employee_hr_employee', string="Employees with manager access",
        help='If left empty, only Odoo users have extended rights in PoS')

    @api.onchange('minimal_employee_ids')
    def _onchange_minimal_employee_ids(self):
        for employee in self.minimal_employee_ids:
            if employee in self.basic_employee_ids:
                self.basic_employee_ids -= employee
            if employee in self.advanced_employee_ids:
                self.advanced_employee_ids -= employee

    @api.onchange('basic_employee_ids')
    def _onchange_basic_employee_ids(self):
        for employee in self.basic_employee_ids:
            if employee in self.advanced_employee_ids:
                self.advanced_employee_ids -= employee
            if employee in self.minimal_employee_ids:
                self.minimal_employee_ids -= employee

    @api.onchange('advanced_employee_ids')
    def _onchange_advanced_employee_ids(self):
        for employee in self.advanced_employee_ids:
            if employee in self.basic_employee_ids:
                self.basic_employee_ids -= employee
<<<<<<< saas-18.1
            if employee in self.minimal_employee_ids:
                self.minimal_employee_ids -= employee
||||||| 69b404c7109ff689381f56520aad758424ec01aa
=======

    def _employee_domain(self, user_id):
        domain = self._check_company_domain(self.company_id)
        if len(self.basic_employee_ids) > 0:
            domain = AND([
                domain,
                ['|', ('user_id', '=', user_id), ('id', 'in', self.basic_employee_ids.ids + self.advanced_employee_ids.ids)]
            ])
        return domain
>>>>>>> f3f07012b8df310db66b3e6cf06ef5598346aadd
