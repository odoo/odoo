# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from datetime import date, datetime

from openerp.osv import fields, osv
from openerp.tools import ustr, DEFAULT_SERVER_DATE_FORMAT
from openerp.tools.translate import _

import openerp.addons.decimal_precision as dp


# ---------------------------------------------------------
# Utils
# ---------------------------------------------------------
def strToDate(dt):
    return date(int(dt[0:4]), int(dt[5:7]), int(dt[8:10]))

def strToDatetime(strdate):
    return datetime.strptime(strdate, DEFAULT_SERVER_DATE_FORMAT)

# ---------------------------------------------------------
# Budgets
# ---------------------------------------------------------
class account_budget_post(osv.osv):
    _name = "account.budget.post"
    _description = "Budgetary Position"
    _columns = {
        'code': fields.char('Code', size=64, required=True),
        'name': fields.char('Name', required=True),
        'account_ids': fields.many2many('account.account', 'account_budget_rel', 'budget_id', 'account_id', 'Accounts'),
        'crossovered_budget_line': fields.one2many('crossovered.budget.lines', 'general_budget_id', 'Budget Lines'),
        'company_id': fields.many2one('res.company', 'Company', required=True),
    }
    _defaults = {
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'account.budget.post', context=c)
    }
    _order = "name"



class crossovered_budget(osv.osv):
    _name = "crossovered.budget"
    _description = "Budget"

    _columns = {
        'name': fields.char('Name', required=True, states={'done':[('readonly',True)]}),
        'code': fields.char('Code', size=16, required=True, states={'done':[('readonly',True)]}),
        'creating_user_id': fields.many2one('res.users', 'Responsible User'),
        'validating_user_id': fields.many2one('res.users', 'Validate User', readonly=True),
        'date_from': fields.date('Start Date', required=True, states={'done':[('readonly',True)]}),
        'date_to': fields.date('End Date', required=True, states={'done':[('readonly',True)]}),
        'state' : fields.selection([('draft','Draft'),('cancel', 'Cancelled'),('confirm','Confirmed'),('validate','Validated'),('done','Done')], 'Status', select=True, required=True, readonly=True, copy=False),
        'crossovered_budget_line': fields.one2many('crossovered.budget.lines', 'crossovered_budget_id', 'Budget Lines', states={'done':[('readonly',True)]}, copy=True),
        'company_id': fields.many2one('res.company', 'Company', required=True),
    }

    _defaults = {
        'state': 'draft',
        'creating_user_id': lambda self, cr, uid, context: uid,
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'account.budget.post', context=c)
    }

    def budget_confirm(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {
            'state': 'confirm'
        })
        return True

    def budget_draft(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {
            'state': 'draft'
        })
        return True

    def budget_validate(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {
            'state': 'validate',
            'validating_user_id': uid,
        })
        return True

    def budget_cancel(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {
            'state': 'cancel'
        })
        return True

    def budget_done(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {
            'state': 'done'
        })
        return True


class crossovered_budget_lines(osv.osv):

    def _prac_amt(self, cr, uid, ids, context=None):
        res = {}
        result = 0.0
        if context is None: 
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            acc_ids = [x.id for x in line.general_budget_id.account_ids]
            if not acc_ids:
                raise osv.except_osv(_('Error!'),_("The Budget '%s' has no accounts!") % ustr(line.general_budget_id.name))
            date_to = line.date_to
            date_from = line.date_from
            if line.analytic_account_id.id:
                cr.execute("SELECT SUM(amount) FROM account_analytic_line WHERE account_id=%s AND (date "
                       "between to_date(%s,'yyyy-mm-dd') AND to_date(%s,'yyyy-mm-dd')) AND "
                       "general_account_id=ANY(%s)", (line.analytic_account_id.id, date_from, date_to,acc_ids,))
                result = cr.fetchone()[0]
            if result is None:
                result = 0.00
            res[line.id] = result
        return res

    def _prac(self, cr, uid, ids, name, args, context=None):
        res={}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = self._prac_amt(cr, uid, [line.id], context=context)[line.id]
        return res

    def _theo_amt(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            today = datetime.now()

            if line.paid_date:
                if strToDate(line.date_to) <= strToDate(line.paid_date):
                    theo_amt = 0.00
                else:
                    theo_amt = line.planned_amount
            else:
                line_timedelta = strToDatetime(line.date_to) - strToDatetime(line.date_from)
                elapsed_timedelta = today - (strToDatetime(line.date_from))

                if elapsed_timedelta.days < 0:
                    # If the budget line has not started yet, theoretical amount should be zero
                    theo_amt = 0.00
                elif line_timedelta.days > 0 and today < strToDatetime(line.date_to):
                    # If today is between the budget line date_from and date_to
                    theo_amt = (elapsed_timedelta.total_seconds() / line_timedelta.total_seconds()) * line.planned_amount
                else:
                    theo_amt = line.planned_amount

            res[line.id] = theo_amt
        return res

    def _theo(self, cr, uid, ids, name, args, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = self._theo_amt(cr, uid, [line.id], context=context)[line.id]
        return res

    def _perc(self, cr, uid, ids, name, args, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            if line.theoritical_amount <> 0.00:
                res[line.id] = float((line.practical_amount or 0.0) / line.theoritical_amount) * 100
            else:
                res[line.id] = 0.00
        return res

    _name = "crossovered.budget.lines"
    _description = "Budget Line"
    _columns = {
        'crossovered_budget_id': fields.many2one('crossovered.budget', 'Budget', ondelete='cascade', select=True, required=True),
        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic Account'),
        'general_budget_id': fields.many2one('account.budget.post', 'Budgetary Position',required=True),
        'date_from': fields.date('Start Date', required=True),
        'date_to': fields.date('End Date', required=True),
        'paid_date': fields.date('Paid Date'),
        'planned_amount':fields.float('Planned Amount', required=True, digits_compute=dp.get_precision('Account')),
        'practical_amount':fields.function(_prac, string='Practical Amount', type='float', digits_compute=dp.get_precision('Account')),
        'theoritical_amount':fields.function(_theo, string='Theoretical Amount', type='float', digits_compute=dp.get_precision('Account')),
        'percentage':fields.function(_perc, string='Percentage', type='float'),
        'company_id': fields.related('crossovered_budget_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True)
    }


class account_analytic_account(osv.osv):
    _inherit = "account.analytic.account"

    _columns = {
        'crossovered_budget_line': fields.one2many('crossovered.budget.lines', 'analytic_account_id', 'Budget Lines'),
    }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
