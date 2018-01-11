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
from openerp.osv import fields, osv
from openerp.tools.translate import _

from openerp.addons.decimal_precision import decimal_precision as dp

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
        #We don't want consolidation for each of these fields because those complex computation is resource-greedy.
        for account in self.pool.get('account.analytic.account').browse(cr, uid, ids, context=context):
            cr.execute("""
                SELECT product_id, sum(amount), user_id, to_invoice, sum(unit_amount), product_uom_id, line.name
                FROM account_analytic_line line
                    LEFT JOIN account_analytic_journal journal ON (journal.id = line.journal_id)
                WHERE account_id = %s
                    AND journal.type = 'purchase'
                    AND invoice_id IS NULL
                    AND to_invoice IS NOT NULL
                GROUP BY product_id, user_id, to_invoice, product_uom_id, line.name""", (account.id,))

            res[account.id] = 0.0
            for product_id, total_amount, user_id, factor_id, qty, uom, line_name in cr.fetchall():
                #the amount to reinvoice is the real cost. We don't use the pricelist
                total_amount = -total_amount
                factor = self.pool.get('hr_timesheet_invoice.factor').browse(cr, uid, factor_id, context=context)
                res[account.id] += total_amount * (100 - factor.factor or 0.0) / 100.0
        return res

    def _expense_invoiced_calc(self, cr, uid, ids, name, arg, context=None):
        lines_obj = self.pool.get('account.analytic.line')
        res = {}
        for account in self.browse(cr, uid, ids, context=context):
            res[account.id] = 0.0
            line_ids = lines_obj.search(cr, uid, [('account_id','=', account.id), ('invoice_id','!=',False), ('to_invoice','!=', False), ('journal_id.type', '=', 'purchase')], context=context)
            #Put invoices in separate array in order not to calculate them double
            invoices = []
            for line in lines_obj.browse(cr, uid, line_ids, context=context):
                if line.invoice_id not in invoices:
                    invoices.append(line.invoice_id)
            for invoice in invoices:
                res[account.id] += invoice.amount_untaxed
        return res

    def _ca_invoiced_calc(self, cr, uid, ids, name, arg, context=None):
        result = super(account_analytic_account, self)._ca_invoiced_calc(cr, uid, ids, name, arg, context=context)
        for acc in self.browse(cr, uid, result.keys(), context=context):
            result[acc.id] = result[acc.id] - (acc.expense_invoiced or 0.0)
        return result

    _columns = {
        'charge_expenses' : fields.boolean('Charge Expenses'),
        'expense_invoiced' : fields.function(_expense_invoiced_calc, type="float"),
        'expense_to_invoice' : fields.function(_expense_to_invoice_calc, type='float'),
        'remaining_expense' : fields.function(_remaining_expnse_calc, type="float"), 
        'est_expenses': fields.float('Estimation of Expenses to Invoice'),
        'ca_invoiced': fields.function(_ca_invoiced_calc, type='float', string='Invoiced Amount',
            help="Total customer invoiced amount for this account.",
            digits_compute=dp.get_precision('Account')),
    }

    def on_change_template(self, cr, uid, ids, template_id, date_start=False, context=None):
        res = super(account_analytic_account, self).on_change_template(cr, uid, ids, template_id, date_start=date_start, context=context)
        if template_id and 'value' in res:
            template = self.browse(cr, uid, template_id, context=context)
            res['value']['charge_expenses'] = template.charge_expenses
            res['value']['est_expenses'] = template.est_expenses
        return res

    def open_hr_expense(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')

        dummy, act_window_id = mod_obj.get_object_reference(cr, uid, 'hr_expense', 'expense_all')
        result = act_obj.read(cr, uid, [act_window_id], context=context)[0]

        line_ids = self.pool.get('hr.expense.line').search(cr,uid,[('analytic_account', 'in', ids)])
        result['domain'] = [('line_ids', 'in', line_ids)]
        names = [account.name for account in self.browse(cr, uid, ids, context=context)]
        result['name'] = _('Expenses of %s') % ','.join(names)
        result['context'] = {'analytic_account': ids[0]}
        result['view_type'] = 'form'
        return result

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


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
