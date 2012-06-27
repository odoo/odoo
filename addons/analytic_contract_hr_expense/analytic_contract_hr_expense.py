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

    def _get_total_toinvoice(self, account):
        total_toinvoice = super(account_analytic_account, self)._get_total_toinvoice(account)
        if account.charge_expenses:
            total_toinvoice += account.expense_to_invoice
        return total_toinvoice

    def _remaining_expnse_calc(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for account in self.browse(cr, uid, ids, context=context):
            if account.est_expenses != 0:
                res[account.id] = max(account.est_expenses - account.expense_invoiced, account.expense_to_invoice)
            else:
                res[account.id]=0.0
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
            cr.execute("""SELECT account_analytic_account.id, \
                                COALESCE(SUM (product_template.list_price * \
                                    account_analytic_line.unit_amount * \
                                    ((100-hr_timesheet_invoice_factor.factor)/100)), 0.0) \
                                    AS ca_to_invoice \
                            FROM product_template \
                            JOIN product_product \
                                ON product_template.id = product_product.product_tmpl_id \
                            JOIN account_analytic_line \
                                ON account_analytic_line.product_id = product_product.id \
                            JOIN account_analytic_journal \
                                ON account_analytic_line.journal_id = account_analytic_journal.id \
                            JOIN account_analytic_account \
                                ON account_analytic_account.id = account_analytic_line.account_id \
                            JOIN hr_timesheet_invoice_factor \
                                ON hr_timesheet_invoice_factor.id = account_analytic_account.to_invoice \
                            WHERE account_analytic_account.id IN %s \
                                AND account_analytic_line.invoice_id IS NULL \
                                AND account_analytic_line.to_invoice IS NOT NULL \
                                AND account_analytic_journal.type = 'purchase' \
                            GROUP BY account_analytic_account.id;""",(child_ids,))
            for account_id, sum in cr.fetchall():
                res[account_id] = sum
        res_final = res
        return res_final

    def _expense_invoiced_calc(self, cr, uid, ids, name, arg, context=None):
        lines_obj = self.pool.get('account.analytic.line')
        res = {}
        for account in self.browse(cr, uid, ids, context=context):
            res[account.id] = 0.0
            line_ids = lines_obj.search(cr, uid, [('account_id','=', account.id), ('invoice_id','!=',False), ('to_invoice','!=', False), ('journal_id.type', '=', 'purchase')], context=context)
            for line in lines_obj.browse(cr, uid, line_ids, context=context):
                res[account.id] += line.invoice_id.amount_untaxed
        return res


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
            res['value']['est_expenses'] = template.est_expenses
        return res

    def open_hr_expense(self, cr, uid, ids, context=None):
        line_ids = self.pool.get('hr.expense.line').search(cr,uid,[('analytic_account', 'in', ids)])
        domain = [('line_ids', 'in', line_ids)]
        names = [record.name for record in self.browse(cr, uid, ids, context=context)]
        name = _('Expenses of %s') % ','.join(names)
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'view_type': 'form',
            'view_mode': 'tree,form',
            'domain' : domain,
            'res_model': 'hr.expense.expense',
            'nodestroy': True,
        }

    def hr_to_invoice_expense(self, cr, uid, ids, context=None):
        domain = [('invoice_id','=',False),('to_invoice','!=',False), ('journal_id.type', '=', 'purchase'), ('account_id', 'in', ids)]
        names = [record.name for record in self.browse(cr, uid, ids, context=context)]
        name = _('Expenses to Invoice of %s') % ','.join(names)
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'view_type': 'form',
            'view_mode': 'tree,form',
            'domain' : domain,
            'res_model': 'account.analytic.line',
            'nodestroy': True,
        }

account_analytic_account()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
