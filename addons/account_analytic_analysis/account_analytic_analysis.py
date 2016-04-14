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
from dateutil.relativedelta import relativedelta
import datetime
import logging
import time

from openerp.osv import osv, fields
import openerp.tools
from openerp.tools.translate import _

from openerp.addons.decimal_precision import decimal_precision as dp

_logger = logging.getLogger(__name__)

class account_analytic_invoice_line(osv.osv):
    _name = "account.analytic.invoice.line"

    def _amount_line(self, cr, uid, ids, prop, unknow_none, unknow_dict, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = line.quantity * line.price_unit
            if line.analytic_account_id.pricelist_id:
                cur = line.analytic_account_id.pricelist_id.currency_id
                res[line.id] = self.pool.get('res.currency').round(cr, uid, cur, res[line.id])
        return res

    _columns = {
        'product_id': fields.many2one('product.product','Product',required=True),
        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic Account', ondelete='cascade'),
        'name': fields.text('Description', required=True),
        'quantity': fields.float('Quantity', required=True),
        'uom_id': fields.many2one('product.uom', 'Unit of Measure',required=True),
        'price_unit': fields.float('Unit Price', required=True),
        'price_subtotal': fields.function(_amount_line, string='Sub Total', type="float",digits_compute= dp.get_precision('Account')),
    }
    _defaults = {
        'quantity' : 1,
    }

    def product_id_change(self, cr, uid, ids, product, uom_id, qty=0, name='', partner_id=False, price_unit=False, pricelist_id=False, company_id=None, context=None):
        context = context or {}
        uom_obj = self.pool.get('product.uom')
        company_id = company_id or False
        local_context = dict(context, company_id=company_id, force_company=company_id, pricelist=pricelist_id)

        if not product:
            return {'value': {'price_unit': 0.0}, 'domain':{'product_uom':[]}}
        if partner_id:
            part = self.pool.get('res.partner').browse(cr, uid, partner_id, context=local_context)
            if part.lang:
                local_context.update({'lang': part.lang})

        result = {}
        res = self.pool.get('product.product').browse(cr, uid, product, context=local_context)
        price = False
        if price_unit is not False:
            price = price_unit
        elif pricelist_id:
            price = res.price
        if price is False:
            price = res.list_price
        if not name:
            name = self.pool.get('product.product').name_get(cr, uid, [res.id], context=local_context)[0][1]
            if res.description_sale:
                name += '\n'+res.description_sale

        result.update({'name': name or False,'uom_id': uom_id or res.uom_id.id or False, 'price_unit': price})

        res_final = {'value':result}
        if result['uom_id'] != res.uom_id.id:
            selected_uom = uom_obj.browse(cr, uid, result['uom_id'], context=local_context)
            new_price = uom_obj._compute_price(cr, uid, res.uom_id.id, res_final['value']['price_unit'], result['uom_id'])
            res_final['value']['price_unit'] = new_price
        return res_final


class account_analytic_account(osv.osv):
    _name = "account.analytic.account"
    _inherit = "account.analytic.account"

    def _analysis_all(self, cr, uid, ids, fields, arg, context=None):
        dp = 2
        res = dict([(i, {}) for i in ids])
        parent_ids = tuple(ids) #We don't want consolidation for each of these fields because those complex computation is resource-greedy.
        accounts = self.browse(cr, uid, ids, context=context)

        for f in fields:
            if f == 'user_ids':
                cr.execute('SELECT MAX(id) FROM res_users')
                max_user = cr.fetchone()[0]
                if parent_ids:
                    cr.execute('SELECT DISTINCT("user") FROM account_analytic_analysis_summary_user ' \
                               'WHERE account_id IN %s AND unit_amount <> 0.0', (parent_ids,))
                    result = cr.fetchall()
                else:
                    result = []
                for id in ids:
                    res[id][f] = [int((id * max_user) + x[0]) for x in result]
            elif f == 'month_ids':
                if parent_ids:
                    cr.execute('SELECT DISTINCT(month_id) FROM account_analytic_analysis_summary_month ' \
                               'WHERE account_id IN %s AND unit_amount <> 0.0', (parent_ids,))
                    result = cr.fetchall()
                else:
                    result = []
                for id in ids:
                    res[id][f] = [int(id * 1000000 + int(x[0])) for x in result]
            elif f == 'last_worked_invoiced_date':
                for id in ids:
                    res[id][f] = False
                if parent_ids:
                    cr.execute("SELECT account_analytic_line.account_id, MAX(date) \
                            FROM account_analytic_line \
                            WHERE account_id IN %s \
                                AND invoice_id IS NOT NULL \
                            GROUP BY account_analytic_line.account_id;", (parent_ids,))
                    for account_id, sum in cr.fetchall():
                        if account_id not in res:
                            res[account_id] = {}
                        res[account_id][f] = sum
            elif f == 'ca_to_invoice':
                for id in ids:
                    res[id][f] = 0.0
                res2 = {}
                for account in accounts:
                    cr.execute("""
                        SELECT product_id, sum(amount), user_id, to_invoice, sum(unit_amount), product_uom_id, line.name
                        FROM account_analytic_line line
                            LEFT JOIN account_analytic_journal journal ON (journal.id = line.journal_id)
                        WHERE account_id = %s
                            AND journal.type != 'purchase'
                            AND invoice_id IS NULL
                            AND to_invoice IS NOT NULL
                        GROUP BY product_id, user_id, to_invoice, product_uom_id, line.name""", (account.id,))

                    res[account.id][f] = 0.0
                    for product_id, price, user_id, factor_id, qty, uom, line_name in cr.fetchall():
                        price = -price
                        if product_id:
                            price = self.pool.get('account.analytic.line')._get_invoice_price(cr, uid, account, product_id, user_id, qty, context)
                        factor = self.pool.get('hr_timesheet_invoice.factor').browse(cr, uid, factor_id, context=context)
                        res[account.id][f] += price * qty * (100-factor.factor or 0.0) / 100.0

                # sum both result on account_id
                for id in ids:
                    res[id][f] = round(res.get(id, {}).get(f, 0.0), dp) + round(res2.get(id, 0.0), 2)
            elif f == 'last_invoice_date':
                for id in ids:
                    res[id][f] = False
                if parent_ids:
                    cr.execute ("SELECT account_analytic_line.account_id, \
                                DATE(MAX(account_invoice.date_invoice)) \
                            FROM account_analytic_line \
                            JOIN account_invoice \
                                ON account_analytic_line.invoice_id = account_invoice.id \
                            WHERE account_analytic_line.account_id IN %s \
                                AND account_analytic_line.invoice_id IS NOT NULL \
                            GROUP BY account_analytic_line.account_id",(parent_ids,))
                    for account_id, lid in cr.fetchall():
                        res[account_id][f] = lid
            elif f == 'last_worked_date':
                for id in ids:
                    res[id][f] = False
                if parent_ids:
                    cr.execute("SELECT account_analytic_line.account_id, MAX(date) \
                            FROM account_analytic_line \
                            WHERE account_id IN %s \
                                AND invoice_id IS NULL \
                            GROUP BY account_analytic_line.account_id",(parent_ids,))
                    for account_id, lwd in cr.fetchall():
                        if account_id not in res:
                            res[account_id] = {}
                        res[account_id][f] = lwd
            elif f == 'hours_qtt_non_invoiced':
                for id in ids:
                    res[id][f] = 0.0
                if parent_ids:
                    cr.execute("SELECT account_analytic_line.account_id, COALESCE(SUM(unit_amount), 0.0) \
                            FROM account_analytic_line \
                            JOIN account_analytic_journal \
                                ON account_analytic_line.journal_id = account_analytic_journal.id \
                            WHERE account_analytic_line.account_id IN %s \
                                AND account_analytic_journal.type='general' \
                                AND invoice_id IS NULL \
                                AND to_invoice IS NOT NULL \
                            GROUP BY account_analytic_line.account_id;",(parent_ids,))
                    for account_id, sua in cr.fetchall():
                        if account_id not in res:
                            res[account_id] = {}
                        res[account_id][f] = round(sua, dp)
                for id in ids:
                    res[id][f] = round(res[id][f], dp)
            elif f == 'hours_quantity':
                for id in ids:
                    res[id][f] = 0.0
                if parent_ids:
                    cr.execute("SELECT account_analytic_line.account_id, COALESCE(SUM(unit_amount), 0.0) \
                            FROM account_analytic_line \
                            JOIN account_analytic_journal \
                                ON account_analytic_line.journal_id = account_analytic_journal.id \
                            WHERE account_analytic_line.account_id IN %s \
                                AND account_analytic_journal.type='general' \
                            GROUP BY account_analytic_line.account_id",(parent_ids,))
                    ff =  cr.fetchall()
                    for account_id, hq in ff:
                        if account_id not in res:
                            res[account_id] = {}
                        res[account_id][f] = round(hq, dp)
                for id in ids:
                    res[id][f] = round(res[id][f], dp)
            elif f == 'ca_theorical':
                # TODO Take care of pricelist and purchase !
                for id in ids:
                    res[id][f] = 0.0
                # Warning
                # This computation doesn't take care of pricelist !
                # Just consider list_price
                if parent_ids:
                    cr.execute("""SELECT account_analytic_line.account_id AS account_id, \
                                COALESCE(SUM((account_analytic_line.unit_amount * pt.list_price) \
                                    - (account_analytic_line.unit_amount * pt.list_price \
                                        * hr.factor)), 0.0) AS somme
                            FROM account_analytic_line \
                            LEFT JOIN account_analytic_journal \
                                ON (account_analytic_line.journal_id = account_analytic_journal.id) \
                            JOIN product_product pp \
                                ON (account_analytic_line.product_id = pp.id) \
                            JOIN product_template pt \
                                ON (pp.product_tmpl_id = pt.id) \
                            JOIN account_analytic_account a \
                                ON (a.id=account_analytic_line.account_id) \
                            JOIN hr_timesheet_invoice_factor hr \
                                ON (hr.id=a.to_invoice) \
                        WHERE account_analytic_line.account_id IN %s \
                            AND a.to_invoice IS NOT NULL \
                            AND account_analytic_journal.type IN ('purchase', 'general')
                        GROUP BY account_analytic_line.account_id""",(parent_ids,))
                    for account_id, sum in cr.fetchall():
                        res[account_id][f] = round(sum, dp)
        return res

    def _ca_invoiced_calc(self, cr, uid, ids, name, arg, context=None):
        res = {}
        res_final = {}
        child_ids = tuple(ids) #We don't want consolidation for each of these fields because those complex computation is resource-greedy.
        for i in child_ids:
            res[i] =  0.0
        if not child_ids:
            return res

        if child_ids:
            #Search all invoice lines not in cancelled state that refer to this analytic account
            inv_line_obj = self.pool.get("account.invoice.line")
            inv_lines = inv_line_obj.search(cr, uid, ['&', ('account_analytic_id', 'in', child_ids), ('invoice_id.state', 'not in', ['draft', 'cancel']), ('invoice_id.type', 'in', ['out_invoice', 'out_refund'])], context=context)
            for line in inv_line_obj.browse(cr, uid, inv_lines, context=context):
                if line.invoice_id.type == 'out_refund':
                    res[line.account_analytic_id.id] -= line.price_subtotal
                else:
                    res[line.account_analytic_id.id] += line.price_subtotal

        for acc in self.browse(cr, uid, res.keys(), context=context):
            res[acc.id] = res[acc.id] - (acc.timesheet_ca_invoiced or 0.0)

        res_final = res
        return res_final

    def _total_cost_calc(self, cr, uid, ids, name, arg, context=None):
        res = {}
        res_final = {}
        child_ids = tuple(ids) #We don't want consolidation for each of these fields because those complex computation is resource-greedy.
        for i in child_ids:
            res[i] =  0.0
        if not child_ids:
            return res
        if child_ids:
            cr.execute("""SELECT account_analytic_line.account_id, COALESCE(SUM(amount), 0.0) \
                    FROM account_analytic_line \
                    JOIN account_analytic_journal \
                        ON account_analytic_line.journal_id = account_analytic_journal.id \
                    WHERE account_analytic_line.account_id IN %s \
                        AND amount<0 \
                    GROUP BY account_analytic_line.account_id""",(child_ids,))
            for account_id, sum in cr.fetchall():
                res[account_id] = round(sum,2)
        res_final = res
        return res_final

    def _remaining_hours_calc(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for account in self.browse(cr, uid, ids, context=context):
            if account.quantity_max != 0:
                res[account.id] = account.quantity_max - account.hours_quantity
            else:
                res[account.id] = 0.0
        for id in ids:
            res[id] = round(res.get(id, 0.0),2)
        return res

    def _remaining_hours_to_invoice_calc(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for account in self.browse(cr, uid, ids, context=context):
            res[account.id] = max(account.hours_qtt_est - account.timesheet_ca_invoiced, account.ca_to_invoice)
        return res

    def _hours_qtt_invoiced_calc(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for account in self.browse(cr, uid, ids, context=context):
            res[account.id] = account.hours_quantity - account.hours_qtt_non_invoiced
            if res[account.id] < 0:
                res[account.id] = 0.0
        for id in ids:
            res[id] = round(res.get(id, 0.0),2)
        return res

    def _revenue_per_hour_calc(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for account in self.browse(cr, uid, ids, context=context):
            if account.hours_qtt_invoiced == 0:
                res[account.id]=0.0
            else:
                res[account.id] = account.ca_invoiced / account.hours_qtt_invoiced
        for id in ids:
            res[id] = round(res.get(id, 0.0),2)
        return res

    def _real_margin_rate_calc(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for account in self.browse(cr, uid, ids, context=context):
            if account.ca_invoiced == 0:
                res[account.id]=0.0
            elif account.total_cost != 0.0:
                res[account.id] = -(account.real_margin / account.total_cost) * 100
            else:
                res[account.id] = 0.0
        for id in ids:
            res[id] = round(res.get(id, 0.0),2)
        return res

    def _fix_price_to_invoice_calc(self, cr, uid, ids, name, arg, context=None):
        sale_obj = self.pool.get('sale.order')
        res = {}
        for account in self.browse(cr, uid, ids, context=context):
            res[account.id] = 0.0
            sale_ids = sale_obj.search(cr, uid, [('project_id','=', account.id), ('state', '=', 'manual')], context=context)
            for sale in sale_obj.browse(cr, uid, sale_ids, context=context):
                res[account.id] += sale.amount_untaxed
                for invoice in sale.invoice_ids:
                    if invoice.state != 'cancel':
                        res[account.id] -= invoice.amount_untaxed
        return res

    def _timesheet_ca_invoiced_calc(self, cr, uid, ids, name, arg, context=None):
        lines_obj = self.pool.get('account.analytic.line')
        res = {}
        inv_ids = []
        for account in self.browse(cr, uid, ids, context=context):
            res[account.id] = 0.0
            line_ids = lines_obj.search(cr, uid, [('account_id','=', account.id), ('invoice_id','!=',False), ('invoice_id.state', 'not in', ['draft', 'cancel']), ('to_invoice','!=', False), ('journal_id.type', '=', 'general'), ('invoice_id.type', 'in', ['out_invoice', 'out_refund'])], context=context)
            for line in lines_obj.browse(cr, uid, line_ids, context=context):
                if line.invoice_id not in inv_ids:
                    inv_ids.append(line.invoice_id)
                    if line.invoice_id.type == 'out_refund':
                        res[account.id] -= line.invoice_id.amount_untaxed
                    else:
                        res[account.id] += line.invoice_id.amount_untaxed
        return res

    def _remaining_ca_calc(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for account in self.browse(cr, uid, ids, context=context):
            res[account.id] = max(account.amount_max - account.ca_invoiced, account.fix_price_to_invoice)
        return res

    def _real_margin_calc(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for account in self.browse(cr, uid, ids, context=context):
            res[account.id] = account.ca_invoiced + account.total_cost
        for id in ids:
            res[id] = round(res.get(id, 0.0),2)
        return res

    def _theorical_margin_calc(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for account in self.browse(cr, uid, ids, context=context):
            res[account.id] = account.ca_theorical + account.total_cost
        for id in ids:
            res[id] = round(res.get(id, 0.0),2)
        return res

    def _is_overdue_quantity(self, cr, uid, ids, fieldnames, args, context=None):
        result = dict.fromkeys(ids, 0)
        for record in self.browse(cr, uid, ids, context=context):
            if record.quantity_max > 0.0:
                result[record.id] = int(record.hours_quantity > record.quantity_max)
            else:
                result[record.id] = 0
        return result

    def _get_analytic_account(self, cr, uid, ids, context=None):
        result = set()
        for line in self.pool.get('account.analytic.line').browse(cr, uid, ids, context=context):
            result.add(line.account_id.id)
        return list(result)

    def _get_total_estimation(self, account):
        tot_est = 0.0
        if account.fix_price_invoices:
            tot_est += account.amount_max 
        if account.invoice_on_timesheets:
            tot_est += account.hours_qtt_est
        return tot_est

    def _get_total_invoiced(self, account):
        total_invoiced = 0.0
        if account.fix_price_invoices:
            total_invoiced += account.ca_invoiced
        if account.invoice_on_timesheets:
            total_invoiced += account.timesheet_ca_invoiced
        return total_invoiced

    def _get_total_remaining(self, account):
        total_remaining = 0.0
        if account.fix_price_invoices:
            total_remaining += account.remaining_ca
        if account.invoice_on_timesheets:
            total_remaining += account.remaining_hours_to_invoice
        return total_remaining

    def _get_total_toinvoice(self, account):
        total_toinvoice = 0.0
        if account.fix_price_invoices:
            total_toinvoice += account.fix_price_to_invoice
        if account.invoice_on_timesheets:
            total_toinvoice += account.ca_to_invoice
        return total_toinvoice

    def _sum_of_fields(self, cr, uid, ids, name, arg, context=None):
         res = dict([(i, {}) for i in ids])
         for account in self.browse(cr, uid, ids, context=context):
            res[account.id]['est_total'] = self._get_total_estimation(account)
            res[account.id]['invoiced_total'] =  self._get_total_invoiced(account)
            res[account.id]['remaining_total'] = self._get_total_remaining(account)
            res[account.id]['toinvoice_total'] =  self._get_total_toinvoice(account)
         return res

    _columns = {
        'is_overdue_quantity' : fields.function(_is_overdue_quantity, method=True, type='boolean', string='Overdue Quantity',
                                                store={
                                                    'account.analytic.line' : (_get_analytic_account, None, 20),
                                                    'account.analytic.account': (lambda self, cr, uid, ids, c=None: ids, ['quantity_max'], 10),
                                                }),
        'ca_invoiced': fields.function(_ca_invoiced_calc, type='float', string='Invoiced Amount',
            help="Total customer invoiced amount for this account.",
            digits_compute=dp.get_precision('Account')),
        'total_cost': fields.function(_total_cost_calc, type='float', string='Total Costs',
            help="Total of costs for this account. It includes real costs (from invoices) and indirect costs, like time spent on timesheets.",
            digits_compute=dp.get_precision('Account')),
        'ca_to_invoice': fields.function(_analysis_all, multi='analytic_analysis', type='float', string='Uninvoiced Amount',
            help="If invoice from analytic account, the remaining amount you can invoice to the customer based on the total costs.",
            digits_compute=dp.get_precision('Account')),
        'ca_theorical': fields.function(_analysis_all, multi='analytic_analysis', type='float', string='Theoretical Revenue',
            help="Based on the costs you had on the project, what would have been the revenue if all these costs have been invoiced at the normal sale price provided by the pricelist.",
            digits_compute=dp.get_precision('Account')),
        'hours_quantity': fields.function(_analysis_all, multi='analytic_analysis', type='float', string='Total Worked Time',
            help="Number of time you spent on the analytic account (from timesheet). It computes quantities on all journal of type 'general'."),
        'last_invoice_date': fields.function(_analysis_all, multi='analytic_analysis', type='date', string='Last Invoice Date',
            help="If invoice from the costs, this is the date of the latest invoiced."),
        'last_worked_invoiced_date': fields.function(_analysis_all, multi='analytic_analysis', type='date', string='Date of Last Invoiced Cost',
            help="If invoice from the costs, this is the date of the latest work or cost that have been invoiced."),
        'last_worked_date': fields.function(_analysis_all, multi='analytic_analysis', type='date', string='Date of Last Cost/Work',
            help="Date of the latest work done on this account."),
        'hours_qtt_non_invoiced': fields.function(_analysis_all, multi='analytic_analysis', type='float', string='Uninvoiced Time',
            help="Number of time (hours/days) (from journal of type 'general') that can be invoiced if you invoice based on analytic account."),
        'hours_qtt_invoiced': fields.function(_hours_qtt_invoiced_calc, type='float', string='Invoiced Time',
            help="Number of time (hours/days) that can be invoiced plus those that already have been invoiced."),
        'remaining_hours': fields.function(_remaining_hours_calc, type='float', string='Remaining Time',
            help="Computed using the formula: Maximum Time - Total Worked Time"),
        'remaining_hours_to_invoice': fields.function(_remaining_hours_to_invoice_calc, type='float', string='Remaining Time',
            help="Computed using the formula: Expected on timesheets - Total invoiced on timesheets"),
        'fix_price_to_invoice': fields.function(_fix_price_to_invoice_calc, type='float', string='Remaining Time',
            help="Sum of quotations for this contract."),
        'timesheet_ca_invoiced': fields.function(_timesheet_ca_invoiced_calc, type='float', string='Remaining Time',
            help="Sum of timesheet lines invoiced for this contract."),
        'remaining_ca': fields.function(_remaining_ca_calc, type='float', string='Remaining Revenue',
            help="Computed using the formula: Max Invoice Price - Invoiced Amount.",
            digits_compute=dp.get_precision('Account')),
        'revenue_per_hour': fields.function(_revenue_per_hour_calc, type='float', string='Revenue per Time (real)',
            help="Computed using the formula: Invoiced Amount / Total Time",
            digits_compute=dp.get_precision('Account')),
        'real_margin': fields.function(_real_margin_calc, type='float', string='Real Margin',
            help="Computed using the formula: Invoiced Amount - Total Costs.",
            digits_compute=dp.get_precision('Account')),
        'theorical_margin': fields.function(_theorical_margin_calc, type='float', string='Theoretical Margin',
            help="Computed using the formula: Theoretical Revenue - Total Costs",
            digits_compute=dp.get_precision('Account')),
        'real_margin_rate': fields.function(_real_margin_rate_calc, type='float', string='Real Margin Rate (%)',
            help="Computes using the formula: (Real Margin / Total Costs) * 100.",
            digits_compute=dp.get_precision('Account')),
        'fix_price_invoices' : fields.boolean('Fixed Price'),
        'invoice_on_timesheets' : fields.boolean("On Timesheets"),
        'month_ids': fields.function(_analysis_all, multi='analytic_analysis', type='many2many', relation='account_analytic_analysis.summary.month', string='Month'),
        'user_ids': fields.function(_analysis_all, multi='analytic_analysis', type="many2many", relation='account_analytic_analysis.summary.user', string='User'),
        'hours_qtt_est': fields.float('Estimation of Hours to Invoice'),
        'est_total' : fields.function(_sum_of_fields, type="float",multi="sum_of_all", string="Total Estimation"),
        'invoiced_total' : fields.function(_sum_of_fields, type="float",multi="sum_of_all", string="Total Invoiced"),
        'remaining_total' : fields.function(_sum_of_fields, type="float",multi="sum_of_all", string="Total Remaining", help="Expectation of remaining income for this contract. Computed as the sum of remaining subtotals which, in turn, are computed as the maximum between '(Estimation - Invoiced)' and 'To Invoice' amounts"),
        'toinvoice_total' : fields.function(_sum_of_fields, type="float",multi="sum_of_all", string="Total to Invoice", help=" Sum of everything that could be invoiced for this contract."),
        'recurring_invoice_line_ids': fields.one2many('account.analytic.invoice.line', 'analytic_account_id', 'Invoice Lines', copy=True),
        'recurring_invoices' : fields.boolean('Generate recurring invoices automatically'),
        'recurring_rule_type': fields.selection([
            ('daily', 'Day(s)'),
            ('weekly', 'Week(s)'),
            ('monthly', 'Month(s)'),
            ('yearly', 'Year(s)'),
            ], 'Recurrency', help="Invoice automatically repeat at specified interval"),
        'recurring_interval': fields.integer('Repeat Every', help="Repeat every (Days/Week/Month/Year)"),
        'recurring_next_date': fields.date('Date of Next Invoice'),
    }

    _defaults = {
        'recurring_interval': 1,
        'recurring_next_date': lambda *a: time.strftime('%Y-%m-%d'),
        'recurring_rule_type':'monthly'
    }

    def open_sale_order_lines(self,cr,uid,ids,context=None):
        if context is None:
            context = {}
        sale_ids = self.pool.get('sale.order').search(cr,uid,[('project_id','=',context.get('search_default_project_id',False)),('partner_id','in',context.get('search_default_partner_id',False))])
        names = [record.name for record in self.browse(cr, uid, ids, context=context)]
        name = _('Sales Order Lines to Invoice of %s') % ','.join(names)
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'view_type': 'form',
            'view_mode': 'tree,form',
            'context': context,
            'domain' : [('order_id','in',sale_ids)],
            'res_model': 'sale.order.line',
            'nodestroy': True,
        }

    def on_change_template(self, cr, uid, ids, template_id, date_start=False, context=None):
        if not template_id:
            return {}
        res = super(account_analytic_account, self).on_change_template(cr, uid, ids, template_id, date_start=date_start, context=context)

        template = self.browse(cr, uid, template_id, context=context)
        
        if not ids:
            res['value']['fix_price_invoices'] = template.fix_price_invoices
            res['value']['amount_max'] = template.amount_max
        if not ids:
            res['value']['invoice_on_timesheets'] = template.invoice_on_timesheets
            res['value']['hours_qtt_est'] = template.hours_qtt_est
        
        if template.to_invoice.id:
            res['value']['to_invoice'] = template.to_invoice.id
        if template.pricelist_id.id:
            res['value']['pricelist_id'] = template.pricelist_id.id
        if not ids:
            invoice_line_ids = []
            for x in template.recurring_invoice_line_ids:
                invoice_line_ids.append((0, 0, {
                    'product_id': x.product_id.id,
                    'uom_id': x.uom_id.id,
                    'name': x.name,
                    'quantity': x.quantity,
                    'price_unit': x.price_unit,
                    'analytic_account_id': x.analytic_account_id and x.analytic_account_id.id or False,
                }))
            res['value']['recurring_invoices'] = template.recurring_invoices
            res['value']['recurring_interval'] = template.recurring_interval
            res['value']['recurring_rule_type'] = template.recurring_rule_type
            res['value']['recurring_invoice_line_ids'] = invoice_line_ids
        return res

    def onchange_recurring_invoices(self, cr, uid, ids, recurring_invoices, date_start=False, context=None):
        value = {}
        if date_start and recurring_invoices:
            value = {'value': {'recurring_next_date': date_start}}
        return value

    def cron_account_analytic_account(self, cr, uid, context=None):
        context = dict(context or {})
        remind = {}

        def fill_remind(key, domain, write_pending=False):
            base_domain = [
                ('type', '=', 'contract'),
                ('partner_id', '!=', False),
                ('manager_id', '!=', False),
                ('manager_id.email', '!=', False),
            ]
            base_domain.extend(domain)

            accounts_ids = self.search(cr, uid, base_domain, context=context, order='name asc')
            accounts = self.browse(cr, uid, accounts_ids, context=context)
            for account in accounts:
                if write_pending:
                    account.write({'state' : 'pending'})
                remind_user = remind.setdefault(account.manager_id.id, {})
                remind_type = remind_user.setdefault(key, {})
                remind_partner = remind_type.setdefault(account.partner_id, []).append(account)

        # Already expired
        fill_remind("old", [('state', 'in', ['pending'])])

        # Expires now
        fill_remind("new", [('state', 'in', ['draft', 'open']), '|', '&', ('date', '!=', False), ('date', '<=', time.strftime('%Y-%m-%d')), ('is_overdue_quantity', '=', True)], True)

        # Expires in less than 30 days
        fill_remind("future", [('state', 'in', ['draft', 'open']), ('date', '!=', False), ('date', '<', (datetime.datetime.now() + datetime.timedelta(30)).strftime("%Y-%m-%d"))])

        context['base_url'] = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        context['action_id'] = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account_analytic_analysis', 'action_account_analytic_overdue_all')[1]
        template_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account_analytic_analysis', 'account_analytic_cron_email_template')[1]
        for user_id, data in remind.items():
            context["data"] = data
            _logger.debug("Sending reminder to uid %s", user_id)
            self.pool.get('email.template').send_mail(cr, uid, template_id, user_id, force_send=True, context=context)

        return True

    def onchange_invoice_on_timesheets(self, cr, uid, ids, invoice_on_timesheets, context=None):
        if not invoice_on_timesheets:
            return {'value': {'to_invoice': False}}
        result = {'value': {'use_timesheets': True}}
        try:
            to_invoice = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'hr_timesheet_invoice', 'timesheet_invoice_factor1')
            result['value']['to_invoice'] = to_invoice[1]
        except ValueError:
            pass
        return result


    def hr_to_invoice_timesheets(self, cr, uid, ids, context=None):
        domain = [('invoice_id','=',False),('to_invoice','!=',False), ('journal_id.type', '=', 'general'), ('account_id', 'in', ids)]
        names = [record.name for record in self.browse(cr, uid, ids, context=context)]
        name = _('Timesheets to Invoice of %s') % ','.join(names)
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'view_type': 'form',
            'view_mode': 'tree,form',
            'domain' : domain,
            'res_model': 'account.analytic.line',
            'nodestroy': True,
        }

    def _prepare_invoice_data(self, cr, uid, contract, context=None):
        context = context or {}

        journal_obj = self.pool.get('account.journal')
        fpos_obj = self.pool['account.fiscal.position']
        partner = contract.partner_id

        if not partner:
            raise osv.except_osv(_('No Customer Defined!'),_("You must first select a Customer for Contract %s!") % contract.name )

        fpos_id = fpos_obj.get_fiscal_position(cr, uid, partner.company_id.id, partner.id, context=context)
        journal_ids = journal_obj.search(cr, uid, [('type', '=','sale'),('company_id', '=', contract.company_id.id or False)], limit=1)
        if not journal_ids:
            raise osv.except_osv(_('Error!'),
            _('Please define a sale journal for the company "%s".') % (contract.company_id.name or '', ))

        partner_payment_term = partner.property_payment_term and partner.property_payment_term.id or False

        currency_id = False
        if contract.pricelist_id:
            currency_id = contract.pricelist_id.currency_id.id
        elif partner.property_product_pricelist:
            currency_id = partner.property_product_pricelist.currency_id.id
        elif contract.company_id:
            currency_id = contract.company_id.currency_id.id

        invoice = {
           'account_id': partner.property_account_receivable.id,
           'type': 'out_invoice',
           'partner_id': partner.id,
           'currency_id': currency_id,
           'journal_id': len(journal_ids) and journal_ids[0] or False,
           'date_invoice': contract.recurring_next_date,
           'origin': contract.code,
           'fiscal_position': fpos_id,
           'payment_term': partner_payment_term,
           'company_id': contract.company_id.id or False,
           'user_id': contract.manager_id.id or uid,
           'comment': contract.description,
        }
        return invoice

    def _prepare_invoice_line(self, cr, uid, line, fiscal_position, context=None):
        fpos_obj = self.pool.get('account.fiscal.position')
        res = line.product_id
        account_id = res.property_account_income.id
        if not account_id:
            account_id = res.categ_id.property_account_income_categ.id
        account_id = fpos_obj.map_account(cr, uid, fiscal_position, account_id)

        taxes = res.taxes_id or False
        tax_id = fpos_obj.map_tax(cr, uid, fiscal_position, taxes, context=context)
        values = {
            'name': line.name,
            'account_id': account_id,
            'account_analytic_id': line.analytic_account_id.id,
            'price_unit': line.price_unit or 0.0,
            'quantity': line.quantity,
            'uos_id': line.uom_id.id or False,
            'product_id': line.product_id.id or False,
            'invoice_line_tax_id': [(6, 0, tax_id)],
        }
        return values

    def _prepare_invoice_lines(self, cr, uid, contract, fiscal_position_id, context=None):
        fpos_obj = self.pool.get('account.fiscal.position')
        fiscal_position = None
        if fiscal_position_id:
            fiscal_position = fpos_obj.browse(cr, uid,  fiscal_position_id, context=context)
        invoice_lines = []
        for line in contract.recurring_invoice_line_ids:
            values = self._prepare_invoice_line(cr, uid, line, fiscal_position, context=context)
            invoice_lines.append((0, 0, values))
        return invoice_lines

    def _prepare_invoice(self, cr, uid, contract, context=None):
        invoice = self._prepare_invoice_data(cr, uid, contract, context=context)
        invoice['invoice_line'] = self._prepare_invoice_lines(cr, uid, contract, invoice['fiscal_position'], context=context)
        return invoice

    def recurring_create_invoice(self, cr, uid, ids, context=None):
        return self._recurring_create_invoice(cr, uid, ids, context=context)

    def _cron_recurring_create_invoice(self, cr, uid, context=None):
        return self._recurring_create_invoice(cr, uid, [], automatic=True, context=context)

    def _recurring_create_invoice(self, cr, uid, ids, automatic=False, context=None):
        context = context or {}
        invoice_ids = []
        current_date =  time.strftime('%Y-%m-%d')
        if ids:
            contract_ids = ids
        else:
            contract_ids = self.search(cr, uid, [('recurring_next_date','<=', current_date), ('state','=', 'open'), ('recurring_invoices','=', True), ('type', '=', 'contract')])
        if contract_ids:
            cr.execute('SELECT company_id, array_agg(id) as ids FROM account_analytic_account WHERE id IN %s GROUP BY company_id', (tuple(contract_ids),))
            for company_id, ids in cr.fetchall():
                for contract in self.browse(cr, uid, ids, context=dict(context, company_id=company_id, force_company=company_id)):
                    try:
                        invoice_values = self._prepare_invoice(cr, uid, contract, context=context)
                        invoice_ids.append(self.pool['account.invoice'].create(cr, uid, invoice_values, context=context))
                        next_date = datetime.datetime.strptime(contract.recurring_next_date or current_date, "%Y-%m-%d")
                        interval = contract.recurring_interval
                        if contract.recurring_rule_type == 'daily':
                            new_date = next_date+relativedelta(days=+interval)
                        elif contract.recurring_rule_type == 'weekly':
                            new_date = next_date+relativedelta(weeks=+interval)
                        elif contract.recurring_rule_type == 'monthly':
                            new_date = next_date+relativedelta(months=+interval)
                        else:
                            new_date = next_date+relativedelta(years=+interval)
                        self.write(cr, uid, [contract.id], {'recurring_next_date': new_date.strftime('%Y-%m-%d')}, context=context)
                        if automatic:
                            cr.commit()
                    except Exception:
                        if automatic:
                            cr.rollback()
                            _logger.exception('Fail to create recurring invoice for contract %s', contract.code)
                        else:
                            raise
        return invoice_ids

class account_analytic_account_summary_user(osv.osv):
    _name = "account_analytic_analysis.summary.user"
    _description = "Hours Summary by User"
    _order='user'
    _auto = False
    _rec_name = 'user'

    def _unit_amount(self, cr, uid, ids, name, arg, context=None):
        res = {}
        account_obj = self.pool.get('account.analytic.account')
        cr.execute('SELECT MAX(id) FROM res_users')
        max_user = cr.fetchone()[0]
        account_ids = [int(str(x/max_user - (x%max_user == 0 and 1 or 0))) for x in ids]
        user_ids = [int(str(x-((x/max_user - (x%max_user == 0 and 1 or 0)) *max_user))) for x in ids]
        parent_ids = tuple(account_ids) #We don't want consolidation for each of these fields because those complex computation is resource-greedy.
        if parent_ids:
            cr.execute('SELECT id, unit_amount ' \
                    'FROM account_analytic_analysis_summary_user ' \
                    'WHERE account_id IN %s ' \
                        'AND "user" IN %s',(parent_ids, tuple(user_ids),))
            for sum_id, unit_amount in cr.fetchall():
                res[sum_id] = unit_amount
        for id in ids:
            res[id] = round(res.get(id, 0.0), 2)
        return res

    _columns = {
        'account_id': fields.many2one('account.analytic.account', 'Analytic Account', readonly=True),
        'unit_amount': fields.float('Total Time'),
        'user': fields.many2one('res.users', 'User'),
    }

    _depends = {
        'res.users': ['id'],
        'account.analytic.line': ['account_id', 'journal_id', 'unit_amount', 'user_id'],
        'account.analytic.journal': ['type'],
    }

    def init(self, cr):
        openerp.tools.sql.drop_view_if_exists(cr, 'account_analytic_analysis_summary_user')
        cr.execute('''CREATE OR REPLACE VIEW account_analytic_analysis_summary_user AS (
            with mu as
                (select max(id) as max_user from res_users)
            , lu AS
                (SELECT   
                 l.account_id AS account_id,   
                 coalesce(l.user_id, 0) AS user_id,   
                 SUM(l.unit_amount) AS unit_amount   
             FROM account_analytic_line AS l,   
                 account_analytic_journal AS j   
             WHERE (j.type = 'general' ) and (j.id=l.journal_id)   
             GROUP BY l.account_id, l.user_id   
            )
            select (lu.account_id::bigint * mu.max_user) + lu.user_id as id,
                    lu.account_id as account_id,
                    lu.user_id as "user",
                    unit_amount
            from lu, mu)''')

class account_analytic_account_summary_month(osv.osv):
    _name = "account_analytic_analysis.summary.month"
    _description = "Hours summary by month"
    _auto = False
    _rec_name = 'month'

    _columns = {
        'account_id': fields.many2one('account.analytic.account', 'Analytic Account', readonly=True),
        'unit_amount': fields.float('Total Time'),
        'month': fields.char('Month', size=32, readonly=True),
    }

    _depends = {
        'account.analytic.line': ['account_id', 'date', 'journal_id', 'unit_amount'],
        'account.analytic.journal': ['type'],
    }

    def init(self, cr):
        openerp.tools.sql.drop_view_if_exists(cr, 'account_analytic_analysis_summary_month')
        cr.execute('CREATE VIEW account_analytic_analysis_summary_month AS (' \
                'SELECT ' \
                    '(TO_NUMBER(TO_CHAR(d.month, \'YYYYMM\'), \'999999\') + (d.account_id  * 1000000::bigint))::bigint AS id, ' \
                    'd.account_id AS account_id, ' \
                    'TO_CHAR(d.month, \'Mon YYYY\') AS month, ' \
                    'TO_NUMBER(TO_CHAR(d.month, \'YYYYMM\'), \'999999\') AS month_id, ' \
                    'COALESCE(SUM(l.unit_amount), 0.0) AS unit_amount ' \
                'FROM ' \
                    '(SELECT ' \
                        'd2.account_id, ' \
                        'd2.month ' \
                    'FROM ' \
                        '(SELECT ' \
                            'a.id AS account_id, ' \
                            'l.month AS month ' \
                        'FROM ' \
                            '(SELECT ' \
                                'DATE_TRUNC(\'month\', l.date) AS month ' \
                            'FROM account_analytic_line AS l, ' \
                                'account_analytic_journal AS j ' \
                            'WHERE j.type = \'general\' ' \
                            'GROUP BY DATE_TRUNC(\'month\', l.date) ' \
                            ') AS l, ' \
                            'account_analytic_account AS a ' \
                        'GROUP BY l.month, a.id ' \
                        ') AS d2 ' \
                    'GROUP BY d2.account_id, d2.month ' \
                    ') AS d ' \
                'LEFT JOIN ' \
                    '(SELECT ' \
                        'l.account_id AS account_id, ' \
                        'DATE_TRUNC(\'month\', l.date) AS month, ' \
                        'SUM(l.unit_amount) AS unit_amount ' \
                    'FROM account_analytic_line AS l, ' \
                        'account_analytic_journal AS j ' \
                    'WHERE (j.type = \'general\') and (j.id=l.journal_id) ' \
                    'GROUP BY l.account_id, DATE_TRUNC(\'month\', l.date) ' \
                    ') AS l '
                    'ON (' \
                        'd.account_id = l.account_id ' \
                        'AND d.month = l.month' \
                    ') ' \
                'GROUP BY d.month, d.account_id ' \
                ')')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
