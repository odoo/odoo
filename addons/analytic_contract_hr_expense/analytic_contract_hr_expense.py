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

from osv import osv, fields
from osv.orm import intersect, except_orm
import tools.sql
from tools.translate import _
from decimal_precision import decimal_precision as dp


class account_analytic_account(osv.osv):
    _name = "account.analytic.account"
    _inherit = "account.analytic.account"

    def _get_total_estimation(self, account):
        tot_est = super(account_analytic_account, self)._get_total_estimation(account)
        if account.charge_expenses:
            tot_est += account.est_expenses
        return tot_est

    def _get_total_invoiced(self, account):
        total_invoiced = super(account_analytic_account, self)._get_total_invoiced(account)
        if account.charge_expenses:
            total_invoiced += account.expense_invoiced
        return total_invoiced

    def _get_total_remaining(self, account):
        total_remaining = super(account_analytic_account, self)._get_total_remaining(account)
        if account.charge_expenses:
            total_remaining += account.remaining_expense
        return total_remaining

    def _get_total_remaining(self, account):
        total_toinvoice = super(account_analytic_account, self)._get_total_toinvoice(account)
        if account.charge_expenses:
            total_toinvoice += account.expense_to_invoice
        return total_toinvoice

    def _remaining_expnse_calc(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for account in self.browse(cr, uid, ids, context=context):
            if account.est_expenses != 0:
                res[account.id] = account.est_expenses - account.expense_invoiced
            else:
                res[account.id]=0.0
        for id in ids:
            res[id] = round(res.get(id, 0.0),2)
        return res

    def _expense_to_invoice_calc(self, cr, uid, ids, name, arg, context=None):
        res = {}
        res_final = {}
        child_ids = tuple(ids) #We don't want consolidation for each of these fields because those complex computation is resource-greedy.
        for i in child_ids:
            res[i] =  0.0
        if not child_ids:
            return res

        if child_ids:
            cr.execute("SELECT hel.analytic_account, SUM(hel.unit_amount*hel.unit_quantity) \
                    FROM hr_expense_line AS hel\
                    LEFT JOIN hr_expense_expense AS he \
                        ON he.id = hel.expense_id\
                    WHERE he.state = 'invoiced' \
                        AND hel.analytic_account IN %s \
                    GROUP BY hel.analytic_account",(child_ids,))
            for account_id, sum in cr.fetchall():
                res[account_id] = sum
        res_final = res
        return res_final

    def _expense_invoiced_calc(self, cr, uid, ids, name, arg, context=None):
        res = {}
        res_final = {}
        child_ids = tuple(ids) #We don't want consolidation for each of these fields because those complex computation is resource-greedy.
        for i in child_ids:
            res[i] =  0.0
        if not child_ids:
            return res

        if child_ids:
            cr.execute("SELECT hel.analytic_account,SUM(hel.unit_amount*hel.unit_quantity)\
                    FROM hr_expense_line AS hel\
                    LEFT JOIN hr_expense_expense AS he \
                        ON he.id = hel.expense_id\
                    WHERE he.state = 'paid' \
                         AND hel.analytic_account IN %s \
                    GROUP BY hel.analytic_account",(child_ids,))
            for account_id, sum in cr.fetchall():
                res[account_id] = sum
        res_final = res
        return res_final

    _columns = {
        'charge_expenses' : fields.boolean('Charge Expenses'),
        'expense_invoiced' : fields.function(_expense_invoiced_calc, type="float"),
        'expense_to_invoice' : fields.function(_expense_to_invoice_calc, type='float'),
        'remaining_expense' : fields.function(_remaining_expnse_calc, type="float"), 
        'est_expenses': fields.float('Estimation of Expenses to Invoice'),
    }

    def on_change_template(self, cr, uid, id, template_id, context=None):
        res = super(account_analytic_account, self).on_change_template(cr, uid, id, template_id, context=context)
        if template_id and 'value' in res:
            template = self.browse(cr, uid, template_id, context=context)
            res['value']['charge_expenses'] = template.charge_expenses
            res['value']['expense_max'] = template.expense_max
        return res

    def open_hr_expense(self, cr, uid, ids, context=None):
        account = self.browse(cr, uid, ids[0], context)
        data_obj = self.pool.get('ir.model.data')
        try:
            journal_id = data_obj.get_object(cr, uid, 'hr_timesheet', 'analytic_journal').id
        except ValueError:
            journal_id = False
        line_ids = self.pool.get('hr.expense.line').search(cr,uid,[('analytic_account','=',account.id)])
        id2 = data_obj._get_id(cr, uid, 'hr_expense', 'view_expenses_form')
        id3 = data_obj._get_id(cr, uid, 'hr_expense', 'view_expenses_tree')
        if id2:
            id2 = data_obj.browse(cr, uid, id2, context=context).res_id
        if id3:
            id3 = data_obj.browse(cr, uid, id3, context=context).res_id
        domain = [('line_ids','in',line_ids)]
        return {
            'type': 'ir.actions.act_window',
            'name': _('Expenses'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'views': [(id3,'tree'),(id2,'form')],
            'domain' : domain,
            'res_model': 'hr.expense.expense',
            'nodestroy': True,
        }

    def hr_to_invoiced_expense(self, cr, uid, ids, context=None):
         res = self.open_hr_expense(cr,uid,ids,context)
         account = self.browse(cr, uid, ids[0], context)
         line_ids = self.pool.get('hr.expense.line').search(cr,uid,[('analytic_account','=',account.id)])
         res['domain'] = [('line_ids','in',line_ids),('state','=','invoiced')]
         return res

account_analytic_account()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
