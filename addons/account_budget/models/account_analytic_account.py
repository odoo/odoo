# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv

class account_analytic_account(osv.osv):
    _inherit = "account.analytic.account"

    _columns = {
        'crossovered_budget_line': fields.one2many('crossovered.budget.lines', 'analytic_account_id', 'Budget Lines'),
    }
