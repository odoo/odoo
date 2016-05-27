#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv

import openerp.addons.decimal_precision as dp

class hr_contract_be(osv.osv):
    _inherit = 'hr.contract'

    _columns = {
        'travel_reimbursement_amount': fields.float('Reimbursement of travel expenses', digits_compute=dp.get_precision('Payroll')),
        'car_company_amount': fields.float('Company car employer', digits_compute=dp.get_precision('Payroll')),
        'car_employee_deduction': fields.float('Company Car Deduction for Worker', digits_compute=dp.get_precision('Payroll')),
        'misc_onss_deduction': fields.float('Miscellaneous exempt ONSS ', digits_compute=dp.get_precision('Payroll')),
        'meal_voucher_amount': fields.float('Check Value Meal ', digits_compute=dp.get_precision('Payroll')),
        'meal_voucher_employee_deduction': fields.float('Check Value Meal - by worker ', digits_compute=dp.get_precision('Payroll')),
        'insurance_employee_deduction': fields.float('Insurance Group - by worker ', digits_compute=dp.get_precision('Payroll')),
        'misc_advantage_amount': fields.float('Benefits of various nature ', digits_compute=dp.get_precision('Payroll')),
        'additional_net_amount': fields.float('Net supplements', digits_compute=dp.get_precision('Payroll')),
        'retained_net_amount': fields.float('Net retained ', digits_compute=dp.get_precision('Payroll')),
    }


class hr_employee_be(osv.osv):
    _inherit = 'hr.employee'

    _columns = {
        'spouse_fiscal_status': fields.selection([('without income','Without Income'),('with income','With Income')], 'Tax status for spouse'),
        'disabled_spouse_bool': fields.boolean('Disabled Spouse', help="if recipient spouse is declared disabled by law"),
        'disabled_children_bool': fields.boolean('Disabled Children', help="if recipient children is/are declared disabled by law"),
        'resident_bool': fields.boolean('Nonresident', help="if recipient lives in a foreign country"),
        'disabled_children_number': fields.integer('Number of disabled children'),
    }
