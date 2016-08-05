# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import decimal_precision as dp


class HrContract(models.Model):
    _inherit = 'hr.contract'

    travel_reimbursement_amount = fields.Float(string='Reimbursement of travel expenses', digits=dp.get_precision('Payroll'))
    car_company_amount = fields.Float(string='Company car employer', digits=dp.get_precision('Payroll'))
    car_employee_deduction = fields.Float(string='Company Car Deduction for Worker', digits=dp.get_precision('Payroll'))
    misc_onss_deduction = fields.Float(string='Miscellaneous exempt ONSS', digits=dp.get_precision('Payroll'))
    meal_voucher_amount = fields.Float(string='Check Value Meal', digits=dp.get_precision('Payroll'))
    meal_voucher_employee_deduction = fields.Float(string='Check Value Meal - by worker', digits=dp.get_precision('Payroll'))
    insurance_employee_deduction = fields.Float(string='Insurance Group - by worker', digits=dp.get_precision('Payroll'))
    misc_advantage_amount = fields.Float(string='Benefits of various nature', digits=dp.get_precision('Payroll'))
    additional_net_amount = fields.Float(string='Net supplements', digits=dp.get_precision('Payroll'))
    retained_net_amount = fields.Float('Net retained ', digits=dp.get_precision('Payroll'))


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    spouse_fiscal_status = fields.Selection([('without income','Without Income'),('with income','With Income')], string='Tax status for spouse')
    disabled_spouse_bool = fields.Boolean(string='Disabled Spouse', help='if recipient spouse is declared disabled by law')
    disabled_children_bool = fields.Boolean(string='Disabled Children', help='if recipient children is/are declared disabled by law')
    resident_bool = fields.Boolean(string='Nonresident', help='if recipient lives in a foreign country')
    disabled_children_number = fields.Integer('Number of disabled children')
