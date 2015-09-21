#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class hr_salary_rule(osv.osv):
    _inherit = 'hr.salary.rule'
    _columns = {
        'analytic_account_id':fields.many2one('account.analytic.account', 'Analytic Account'),
        'account_tax_id':fields.many2one('account.tax', 'Tax'),
        'account_debit': fields.many2one('account.account', 'Debit Account', domain=[('deprecated', '=', False)]),
        'account_credit': fields.many2one('account.account', 'Credit Account', domain=[('deprecated', '=', False)]),
    }
