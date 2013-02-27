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
import datetime
import logging
import time

from openerp.osv import osv, fields
from openerp.osv.orm import intersect, except_orm
import openerp.tools
from openerp import tools
from openerp.tools.translate import _

from dateutil.relativedelta import relativedelta

from openerp.addons.decimal_precision import decimal_precision as dp

_logger = logging.getLogger(__name__)

class account_analytic_invoice_line(osv.osv):
    _name = "account.analytic.invoice.line"

    def _amount_line(self, cr, uid, ids, prop, unknow_none, unknow_dict):
        res = {}
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        for line in self.browse(cr, uid, ids):
            price = line.price_unit
            taxes = tax_obj.compute_all(cr, uid, line.tax_ids, price, line.quantity, product=line.product_id, partner=line.analytic_account_id.partner_id)
            res[line.id] = taxes['total']
            if line.analytic_account_id:
                cur = line.analytic_account_id.currency_id
                res[line.id] = cur_obj.round(cr, uid, cur, res[line.id])
        return res

    def _get_uom_id(self, cr, uid, *args):
        try:
            proxy = self.pool.get('ir.model.data')
            result = proxy.get_object_reference(cr, uid, 'product', 'product_uom_unit')
            return result[1]
        except Exception, ex:
            return False


    def _get_tax_lines(self, cr, uid, ids,name, arg, context=None):
        res = {}
        product_ids = []
        product_obj = self.pool.get('product.product')
        account_obj = self.pool.get('account.account')
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = []
            if not line.product_id:
                continue
            product = product_obj.browse(cr, uid, line.product_id.id, context=context)
            a = product.property_account_income.id
            if not a:
                a = product.categ_id.property_account_income_categ.id
            taxes = product.taxes_id and product.taxes_id or (a and account_obj.browse(cr, uid, a, context=context).tax_ids or False)
            res[line.id] = [x.id for x in taxes]
        return res

    _columns = {
        'product_id': fields.many2one('product.product','Product'),
        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic Account'),
        'name': fields.char('Description', size=64),
        'quantity': fields.float('Quantity'),
        'uom_id': fields.many2one('product.uom', 'Unit of Measure', required=True),
        'price_unit': fields.float('Unit Price'),
        'price_subtotal': fields.function(_amount_line, string='Amount', type="float",
            digits_compute= dp.get_precision('Account')),
        'tax_ids':fields.function(_get_tax_lines, type='many2many', relation='account.tax', string='Taxes'),
        'invoice_id': fields.many2one('account.invoice', 'Invoice Reference', ondelete='cascade', select=True),
    }
    _order = 'name desc'

    _defaults = {
        'uom_id' : _get_uom_id,
        'quantity' : 1,
        'price_unit': 0.0,
        }


    def product_id_change(self, cr, uid, ids, product, uom_id, qty=0, name='', partner_id=False, price_unit=False, currency_id=False, company_id=None, context=None):
        if context is None:
            context = {}
        uom_obj = self.pool.get('product.uom')
        
        company_id = company_id or False
        context.update({'company_id': company_id, 'force_company': company_id})
        
        if not product:
            return {'value': {'price_unit': 0.0}, 'domain':{'product_uom':[]}}
        if not partner_id:
            raise osv.except_osv(_('No Partner Defined !'),_("You must first select a Customer !") )
        part = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
        
        if part.lang:
            context.update({'lang': part.lang})
        result = {}
        res = self.pool.get('product.product').browse(cr, uid, product, context=context)

        a = res.property_account_income.id
        if not a:
            a = res.categ_id.property_account_income_categ.id
        if a:
            result['account_id'] = a

        taxes = res.taxes_id and res.taxes_id or (a and self.pool.get('account.account').browse(cr, uid, a, context=context).tax_ids or False)
        result.update({'name':res.partner_ref,'uom_id': uom_id or res.uom_id.id, 'price_unit': res.list_price or res.standard_price,'tax_ids': [x.id for x in taxes]})
        if res.description:
            result['name'] += '\n'+res.description

        res_final = {'value':result}
        if not company_id or not currency_id:
            return res_final

        company = self.pool.get('res.company').browse(cr, uid, company_id, context=context)
        currency = self.pool.get('res.currency').browse(cr, uid, currency_id, context=context)

        if company.currency_id.id != currency.id:
            new_price = res_final['value']['price_unit'] * currency.rate
            res_final['value']['price_unit'] = new_price
        
        if result['uom_id'] != res.uom_id.id:
            selected_uom = uom_obj.browse(cr, uid, result['uom_id'], context=context)
            new_price = uom_obj._compute_price(cr, uid, res.uom_id.id, res_final['value']['price_unit'], result['uom_id'])
            res_final['value']['price_unit'] = new_price
        return res_final

account_analytic_invoice_line()

class account_analytic_account(osv.osv):
    _name = "account.analytic.account"
    _inherit = "account.analytic.account"
    
    def button_reset_taxes(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        ctx = context.copy()
        total_tax_amount = 0.0
        for id in ids:
            partner = self.browse(cr, uid, id, context=ctx).partner_id
            if partner.lang:
                ctx.update({'lang': partner.lang})
            for taxe in self.compute_tax(cr, uid, [id], context=ctx).values():
                total_tax_amount += taxe["tax_amount"]
        return total_tax_amount
    
    def button_compute(self, cr, uid, ids, context=None, set_total=False):
        total_tax_amount = self.button_reset_taxes(cr, uid, ids, context)
        for inv in self.browse(cr, uid, ids, context=context):
            if set_total:
                self.write(cr, uid, [inv.id], {'check_total': inv.amount_total})
        return True
    
    def compute_tax(self, cr, uid, ids, context=None):
        tax_grouped = {}
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        inv = self.browse(cr, uid, ids[0], context=context)
        cur = inv.currency_id
        company_currency = inv.company_id.currency_id.id

        for line in inv.invoice_line_ids:
            for tax in tax_obj.compute_all(cr, uid, line.tax_ids, (line.price_unit), line.quantity, line.product_id, inv.partner_id)['taxes']:
                val={}
                val['invoice_id'] = inv.id
                val['name'] = tax['name']
                val['amount'] = tax['amount']
                val['manual'] = False
                val['sequence'] = tax['sequence']
                val['base'] = cur_obj.round(cr, uid, cur, tax['price_unit'] * line['quantity'])

                val['base_code_id'] = tax['base_code_id']
                val['tax_code_id'] = tax['tax_code_id']
                val['base_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['base'] * tax['base_sign'], context={'date': inv.last_invoice_date or time.strftime('%Y-%m-%d')}, round=False)
                val['tax_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['amount'] * tax['tax_sign'], context={'date': inv.last_invoice_date or time.strftime('%Y-%m-%d')}, round=False)
                val['account_id'] = tax['account_collected_id'] or line.account_id.id
                val['account_analytic_id'] = tax['account_analytic_collected_id']

                key = (val['tax_code_id'], val['base_code_id'], val['account_id'], val['account_analytic_id'])
                if not key in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += val['base']
                    tax_grouped[key]['base_amount'] += val['base_amount']
                    tax_grouped[key]['tax_amount'] += val['tax_amount']

        for t in tax_grouped.values():
            t['base'] = cur_obj.round(cr, uid, cur, t['base'])
            t['amount'] = cur_obj.round(cr, uid, cur, t['amount'])
            t['base_amount'] = cur_obj.round(cr, uid, cur, t['base_amount'])
            t['tax_amount'] = cur_obj.round(cr, uid, cur, t['tax_amount'])
        return tax_grouped

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
            cr.execute("SELECT account_analytic_line.account_id, COALESCE(SUM(amount), 0.0) \
                    FROM account_analytic_line \
                    JOIN account_analytic_journal \
                        ON account_analytic_line.journal_id = account_analytic_journal.id  \
                    WHERE account_analytic_line.account_id IN %s \
                        AND account_analytic_journal.type = 'sale' \
                    GROUP BY account_analytic_line.account_id", (child_ids,))
            for account_id, sum in cr.fetchall():
                res[account_id] = round(sum,2)
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
            sale_ids = sale_obj.search(cr, uid, [('project_id','=', account.id), ('partner_id', '=', account.partner_id.id)], context=context)
            for sale in sale_obj.browse(cr, uid, sale_ids, context=context):
                if not sale.invoiced:
                    res[account.id] += sale.amount_untaxed
                    for invoice in sale.invoice_ids:
                        if invoice.state not in ('draft', 'cancel'):
                            res[account.id] -= invoice.amount_untaxed
        return res

    def _timesheet_ca_invoiced_calc(self, cr, uid, ids, name, arg, context=None):
        lines_obj = self.pool.get('account.analytic.line')
        res = {}
        inv_ids = []
        for account in self.browse(cr, uid, ids, context=context):
            res[account.id] = 0.0
            line_ids = lines_obj.search(cr, uid, [('account_id','=', account.id), ('invoice_id','!=',False), ('to_invoice','!=', False), ('journal_id.type', '=', 'general')], context=context)
            for line in lines_obj.browse(cr, uid, line_ids, context=context):
                if line.invoice_id not in inv_ids:
                    inv_ids.append(line.invoice_id)
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
                result[record.id] = int(record.hours_quantity >= record.quantity_max)
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
  
    def _amount_all(self, cr, uid, ids, name, args, context=None):
        res = {}
        tax = 0.0
        for account in self.browse(cr, uid, ids, context=context):
            res[account.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0
            }
            for line in account.invoice_line_ids:
                tax = self.button_reset_taxes(cr, uid, ids, context)
                res[account.id]['amount_untaxed'] += line.price_subtotal
            res[account.id]['amount_tax'] = tax
            res[account.id]['amount_total'] = res[account.id]['amount_tax'] + res[account.id]['amount_untaxed']
        return res

    _columns = {
        'is_overdue_quantity' : fields.function(_is_overdue_quantity, method=True, type='boolean', string='Overdue Quantity',
                                                store={
                                                    'account.analytic.line' : (_get_analytic_account, None, 20),
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
            help="Computed using the formula: Maximum Time - Total Invoiced Time"),
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
        'invoice_line_ids': fields.one2many('account.analytic.invoice.line', 'analytic_account_id'),
        'recurring_invoices' : fields.boolean('Recurring Invoices'),
        'rrule_type': fields.selection([
            ('daily', 'Day(s)'),
            ('weekly', 'Week(s)'),
            ('monthly', 'Month(s)')
            ], 'Recurrency', help="Let the event automatically repeat at that interval"),
        'interval': fields.integer('Repeat Every', help="Repeat every (Days/Week/Month/Year)"),
        'next_date': fields.date('Next Date'),
        'amount_untaxed': fields.function(_amount_all, type='float', string='Total tax excluded', multi="vinvline"),
        'amount_tax': fields.function(_amount_all, type='float', string='Taxes', multi="vinvline"),
        'amount_total': fields.function(_amount_all, type='float', string='Total', multi="vinvline"),
    }

    _defaults = {
        'interval': 1,
        'next_date': lambda *a: time.strftime('%Y-%m-%d'),
        'rrule_type':'monthly'
    }

    def open_sale_order_lines(self,cr,uid,ids,context=None):
        if context is None:
            context = {}
        sale_ids = self.pool.get('sale.order').search(cr,uid,[('project_id','=',context.get('search_default_project_id',False)),('partner_id','in',context.get('search_default_partner_id',False))])
        names = [record.name for record in self.browse(cr, uid, ids, context=context)]
        name = _('Sales Order Lines of %s') % ','.join(names)
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

    def on_change_template(self, cr, uid, ids, template_id, context=None):
        if not template_id:
            return {}
        res = super(account_analytic_account, self).on_change_template(cr, uid, ids, template_id, context=context)
        if template_id and 'value' in res:
            template = self.browse(cr, uid, template_id, context=context)
            res['value']['fix_price_invoices'] = template.fix_price_invoices
            res['value']['invoice_on_timesheets'] = template.invoice_on_timesheets
            res['value']['hours_qtt_est'] = template.hours_qtt_est
            res['value']['amount_max'] = template.amount_max
            res['value']['to_invoice'] = template.to_invoice.id
            res['value']['pricelist_id'] = template.pricelist_id.id
        return res

    def onchange_next_date(self, cr, uid, ids, next_date,context=None):
        value = {}
        current_date = time.strftime('%Y-%m-%d')
        if next_date and next_date < current_date:
            value = {'value':{'next_date': self.browse(cr, uid,ids[0]).next_date}}
            raise osv.except_osv(_('Warning!'), _("Define Next Date Greater or Same as Current Date."))
        return {'value':value}

    def onchange_recurring_invoices(self, cr, uid, ids, recurring_invoices, date_start=False, context=None):
        value = {}
        if ids and date_start and recurring_invoices == True:
            value = {'value': {
                    'next_date': date_start,
                    'rrule_type':'monthly'
                    }
                }
        return {'value':value}

    def cron_account_analytic_account(self, cr, ids, uid, context=None):
        if context is None:
            context = {}
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
                    account.write({'state' : 'pending'}, context=context)
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
            self.pool.get('email.template').send_mail(cr, uid, template_id, user_id, context=context)

        return True

    def _prepare_invoice_line(self, cr, uid, contract, contract_line_ids, invoice_id,context=None):
        if context is None:
            context = {}
        inv_line_id = []
        obj_invoice_line = self.pool.get('account.invoice.line')
        obj_contract_line = self.pool.get('account.analytic.invoice.line')
        for line in obj_contract_line.browse(cr, uid, contract_line_ids):
            invoice_line_vals = {
                'name': line.name,
                'origin': line.analytic_account_id.name,
                'account_id': contract.id,
                'price_unit': line.price_unit,
                'quantity': line.quantity,
                'invoice_id': invoice_id,
                'uos_id': line.uom_id.id or False,
                'product_id': line.product_id.id or False,
                'invoice_line_tax_id': [(6, 0, [x.id for x in line.tax_ids])],
            }
            line_id = obj_invoice_line.create(cr, uid, invoice_line_vals, context=context)
            inv_line_id.append(line_id)
        return inv_line_id

    def cron_create_invoice(self, cr, uid, automatic=False, use_new_cursor=False, context=None):
        inv_obj = self.pool.get('account.invoice')
        obj_invoice_line = self.pool.get('account.invoice.line')
        journal_obj = self.pool.get('account.journal')
        if context is None:
            context = {}
        contract_ids = self.search(cr, uid, [('next_date','=',time.strftime("%Y-%m-%d")), ('state','=', 'open'), ('recurring_invoices','=', True)])
        if contract_ids:
            for contract in self.browse(cr, uid, contract_ids):
                if not contract.partner_id:
                    raise osv.except_osv(_('No Customer Defined !'),_("You must first select a Customer for Contract %s!") % contract.name )
                journal_ids = journal_obj.search(cr, uid, [('type', '=','sale'),('company_id', '=', contract.company_id.id)], limit=1)
                if not journal_ids:
                    raise osv.except_osv(_('Error!'),
                    _('Define sale journal for this company: "%s" (id:%d).') % (contract.company_id.name, contract.company_id.id))
                inv_data = {
                       'name': contract.name,
                       'reference': contract.code,
                       'account_id': contract.partner_id.property_account_receivable.id or contract.partner_id.property_account_receivable or False,
                       'type': 'out_invoice',
                       'partner_id': contract.partner_id.id,
                       'currency_id': contract.partner_id.property_product_pricelist.id,
                       'journal_id': len(journal_ids) and journal_ids[0] or False,
                       'date_invoice': contract.next_date,
                       'origin': contract.name,
                       'company_id': contract.company_id.id,
                       'contract_id': contract.id,
                    }
                contract_line_ids = self.pool.get('account.analytic.invoice.line').search(cr, uid, [('analytic_account_id', '=', contract.id)], context=context)
                if contract_line_ids:
                    invoice_id = inv_obj.create(cr, uid, inv_data, context=context)
                    self._prepare_invoice_line(cr, uid, contract, contract_line_ids, invoice_id,context=context)
                    inv_obj.button_compute(cr, uid, [invoice_id])
                    
                    next_date = datetime.datetime.strptime(contract.next_date, "%Y-%m-%d")
                    interval = contract.interval
        
                    if contract.rrule_type == 'monthly':
                        new_date = next_date+relativedelta(months=+interval)
                    if contract.rrule_type == 'daily':
                        new_date = next_date+relativedelta(days=+interval)
                    if contract.rrule_type == 'weekly':
                        new_date = next_date+relativedelta(weeks=+interval)
                    contract.write({'next_date':new_date}, context=context)
        return True

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
            select (lu.account_id * mu.max_user) + lu.user_id as id,
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
