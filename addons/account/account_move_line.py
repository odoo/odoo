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

import time
from datetime import datetime
from operator import itemgetter

import netsvc
from osv import fields, osv
from tools.translate import _
import decimal_precision as dp
import tools

class account_move_line(osv.osv):
    _name = "account.move.line"
    _description = "Journal Items"

    def _query_get(self, cr, uid, obj='l', context=None):
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        fiscalperiod_obj = self.pool.get('account.period')
        account_obj = self.pool.get('account.account')
        fiscalyear_ids = []
        if context is None:
            context = {}
        initial_bal = context.get('initial_bal', False)
        company_clause = " "
        if context.get('company_id', False):
            company_clause = " AND " +obj+".company_id = %s" % context.get('company_id', False)
        if not context.get('fiscalyear', False):
            if context.get('all_fiscalyear', False):
                #this option is needed by the aged balance report because otherwise, if we search only the draft ones, an open invoice of a closed fiscalyear won't be displayed
                fiscalyear_ids = fiscalyear_obj.search(cr, uid, [])
            else:
                fiscalyear_ids = fiscalyear_obj.search(cr, uid, [('state', '=', 'draft')])
        else:
            #for initial balance as well as for normal query, we check only the selected FY because the best practice is to generate the FY opening entries
            fiscalyear_ids = [context['fiscalyear']]

        fiscalyear_clause = (','.join([str(x) for x in fiscalyear_ids])) or '0'
        state = context.get('state', False)
        where_move_state = ''
        where_move_lines_by_date = ''

        if context.get('date_from', False) and context.get('date_to', False):
            if initial_bal:
                where_move_lines_by_date = " AND " +obj+".move_id IN (SELECT id FROM account_move WHERE date < '" +context['date_from']+"')"
            else:
                where_move_lines_by_date = " AND " +obj+".move_id IN (SELECT id FROM account_move WHERE date >= '" +context['date_from']+"' AND date <= '"+context['date_to']+"')"

        if state:
            if state.lower() not in ['all']:
                where_move_state= " AND "+obj+".move_id IN (SELECT id FROM account_move WHERE account_move.state = '"+state+"')"

        if context.get('period_from', False) and context.get('period_to', False) and not context.get('periods', False):
            if initial_bal:
                period_company_id = fiscalperiod_obj.browse(cr, uid, context['period_from'], context=context).company_id.id
                first_period = fiscalperiod_obj.search(cr, uid, [('company_id', '=', period_company_id)], order='date_start', limit=1)[0]
                context['periods'] = fiscalperiod_obj.build_ctx_periods(cr, uid, first_period, context['period_from'])
            else:
                context['periods'] = fiscalperiod_obj.build_ctx_periods(cr, uid, context['period_from'], context['period_to'])
        if context.get('periods', False):
            if initial_bal:
                query = obj+".state <> 'draft' AND "+obj+".period_id IN (SELECT id FROM account_period WHERE fiscalyear_id IN (%s)) %s %s" % (fiscalyear_clause, where_move_state, where_move_lines_by_date)
                period_ids = fiscalperiod_obj.search(cr, uid, [('id', 'in', context['periods'])], order='date_start', limit=1)
                if period_ids and period_ids[0]:
                    first_period = fiscalperiod_obj.browse(cr, uid, period_ids[0], context=context)
                    # Find the old periods where date start of those periods less then Start period
                    periods = fiscalperiod_obj.search(cr, uid, [('date_start', '<', first_period.date_start)])
                    periods = ','.join([str(x) for x in periods])
                    if periods:
                        query = obj+".state <> 'draft' AND "+obj+".period_id IN (SELECT id FROM account_period WHERE fiscalyear_id IN (%s) AND id IN (%s)) %s %s" % (fiscalyear_clause, periods, where_move_state, where_move_lines_by_date)
            else:
                ids = ','.join([str(x) for x in context['periods']])
                query = obj+".state <> 'draft' AND "+obj+".period_id IN (SELECT id FROM account_period WHERE fiscalyear_id IN (%s) AND id IN (%s)) %s %s" % (fiscalyear_clause, ids, where_move_state, where_move_lines_by_date)
        else:
            query = obj+".state <> 'draft' AND "+obj+".period_id IN (SELECT id FROM account_period WHERE fiscalyear_id IN (%s)) %s %s" % (fiscalyear_clause, where_move_state, where_move_lines_by_date)

        if context.get('journal_ids', False):
            query += ' AND '+obj+'.journal_id IN (%s)' % ','.join(map(str, context['journal_ids']))

        if context.get('chart_account_id', False):
            child_ids = account_obj._get_children_and_consol(cr, uid, [context['chart_account_id']], context=context)
            query += ' AND '+obj+'.account_id IN (%s)' % ','.join(map(str, child_ids))

        query += company_clause
        return query

    def _amount_residual(self, cr, uid, ids, field_names, args, context=None):
        """
           This function returns the residual amount on a receivable or payable account.move.line.
           By default, it returns an amount in the currency of this journal entry (maybe different
           of the company currency), but if you pass 'residual_in_company_currency' = True in the
           context then the returned amount will be in company currency.
        """
        res = {}
        if context is None:
            context = {}
        cur_obj = self.pool.get('res.currency')
        for move_line in self.browse(cr, uid, ids, context=context):
            res[move_line.id] = {
                'amount_residual': 0.0,
                'amount_residual_currency': 0.0,
            }

            if move_line.reconcile_id:
                continue
            if not move_line.account_id.type in ('payable', 'receivable'):
                #this function does not suport to be used on move lines not related to payable or receivable accounts
                continue

            if move_line.currency_id:
                move_line_total = move_line.amount_currency
                sign = move_line.amount_currency < 0 and -1 or 1
            else:
                move_line_total = move_line.debit - move_line.credit
                sign = (move_line.debit - move_line.credit) < 0 and -1 or 1
            line_total_in_company_currency =  move_line.debit - move_line.credit
            context_unreconciled = context.copy()
            if move_line.reconcile_partial_id:
                for payment_line in move_line.reconcile_partial_id.line_partial_ids:
                    if payment_line.id == move_line.id:
                        continue
                    if payment_line.currency_id and move_line.currency_id and payment_line.currency_id.id == move_line.currency_id.id:
                            move_line_total += payment_line.amount_currency
                    else:
                        if move_line.currency_id:
                            context_unreconciled.update({'date': payment_line.date})
                            amount_in_foreign_currency = cur_obj.compute(cr, uid, move_line.company_id.currency_id.id, move_line.currency_id.id, (payment_line.debit - payment_line.credit), round=False, context=context_unreconciled)
                            move_line_total += amount_in_foreign_currency
                        else:
                            move_line_total += (payment_line.debit - payment_line.credit)
                    line_total_in_company_currency += (payment_line.debit - payment_line.credit)

            result = move_line_total
            res[move_line.id]['amount_residual_currency'] =  sign * (move_line.currency_id and self.pool.get('res.currency').round(cr, uid, move_line.currency_id, result) or result)
            res[move_line.id]['amount_residual'] = sign * line_total_in_company_currency
        return res

    def default_get(self, cr, uid, fields, context=None):
        data = self._default_get(cr, uid, fields, context=context)
        for f in data.keys():
            if f not in fields:
                del data[f]
        return data

    def create_analytic_lines(self, cr, uid, ids, context=None):
        acc_ana_line_obj = self.pool.get('account.analytic.line')
        for obj_line in self.browse(cr, uid, ids, context=context):
            if obj_line.analytic_account_id:
                if not obj_line.journal_id.analytic_journal_id:
                    raise osv.except_osv(_('No Analytic Journal !'),_("You have to define an analytic journal on the '%s' journal!") % (obj_line.journal_id.name, ))
                amt = (obj_line.credit or  0.0) - (obj_line.debit or 0.0)
                vals_lines = {
                    'name': obj_line.name,
                    'date': obj_line.date,
                    'account_id': obj_line.analytic_account_id.id,
                    'unit_amount': obj_line.quantity,
                    'product_id': obj_line.product_id and obj_line.product_id.id or False,
                    'product_uom_id': obj_line.product_uom_id and obj_line.product_uom_id.id or False,
                    'amount': amt,
                    'general_account_id': obj_line.account_id.id,
                    'journal_id': obj_line.journal_id.analytic_journal_id.id,
                    'ref': obj_line.ref,
                    'move_id': obj_line.id,
                    'user_id': uid
                }
                acc_ana_line_obj.create(cr, uid, vals_lines)
        return True

    def _default_get_move_form_hook(self, cursor, user, data):
        '''Called in the end of default_get method for manual entry in account_move form'''
        if data.has_key('analytic_account_id'):
            del(data['analytic_account_id'])
        if data.has_key('account_tax_id'):
            del(data['account_tax_id'])
        return data

    def convert_to_period(self, cr, uid, context=None):
        if context is None:
            context = {}
        period_obj = self.pool.get('account.period')
        #check if the period_id changed in the context from client side
        if context.get('period_id', False):
            period_id = context.get('period_id')
            if type(period_id) == str:
                ids = period_obj.search(cr, uid, [('name', 'ilike', period_id)])
                context.update({
                    'period_id': ids[0]
                })
        return context

    def _default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        if not context.get('journal_id', False) and context.get('search_default_journal_id', False):
            context['journal_id'] = context.get('search_default_journal_id')
        account_obj = self.pool.get('account.account')
        period_obj = self.pool.get('account.period')
        journal_obj = self.pool.get('account.journal')
        move_obj = self.pool.get('account.move')
        tax_obj = self.pool.get('account.tax')
        fiscal_pos_obj = self.pool.get('account.fiscal.position')
        partner_obj = self.pool.get('res.partner')
        currency_obj = self.pool.get('res.currency')
        context = self.convert_to_period(cr, uid, context)
        # Compute simple values
        data = super(account_move_line, self).default_get(cr, uid, fields, context=context)
        # Starts: Manual entry from account.move form
        if context.get('lines',[]):
            total_new = 0.00
            for i in context['lines']:
                if i[2]:
                    total_new += (i[2]['debit'] or 0.00)- (i[2]['credit'] or 0.00)
                    for item in i[2]:
                            data[item] = i[2][item]
            if context['journal']:
                journal_data = journal_obj.browse(cr, uid, context['journal'], context=context)
                if journal_data.type == 'purchase':
                    if total_new > 0:
                        account = journal_data.default_credit_account_id
                    else:
                        account = journal_data.default_debit_account_id
                else:
                    if total_new > 0:
                        account = journal_data.default_credit_account_id
                    else:
                        account = journal_data.default_debit_account_id
                if account and ((not fields) or ('debit' in fields) or ('credit' in fields)) and 'partner_id' in data and (data['partner_id']):
                    part = partner_obj.browse(cr, uid, data['partner_id'], context=context)
                    account = fiscal_pos_obj.map_account(cr, uid, part and part.property_account_position or False, account.id)
                    account = account_obj.browse(cr, uid, account, context=context)
                    data['account_id'] =  account.id

            s = -total_new
            data['debit'] = s > 0 and s or 0.0
            data['credit'] = s < 0 and -s or 0.0
            data = self._default_get_move_form_hook(cr, uid, data)
            return data
        # Ends: Manual entry from account.move form
        if not 'move_id' in fields: #we are not in manual entry
            return data
        # Compute the current move
        move_id = False
        partner_id = False
        if context.get('journal_id', False) and context.get('period_id', False):
            if 'move_id' in fields:
                cr.execute('SELECT move_id \
                    FROM \
                        account_move_line \
                    WHERE \
                        journal_id = %s and period_id = %s AND create_uid = %s AND state = %s \
                    ORDER BY id DESC limit 1',
                    (context['journal_id'], context['period_id'], uid, 'draft'))
                res = cr.fetchone()
                move_id = (res and res[0]) or False
                if not move_id:
                    return data
                else:
                    data['move_id'] = move_id
            if 'date' in fields:
                cr.execute('SELECT date \
                    FROM \
                        account_move_line \
                    WHERE \
                        journal_id = %s AND period_id = %s AND create_uid = %s \
                    ORDER BY id DESC',
                    (context['journal_id'], context['period_id'], uid))
                res = cr.fetchone()
                if res:
                    data['date'] = res[0]
                else:
                    period = period_obj.browse(cr, uid, context['period_id'],
                            context=context)
                    data['date'] = period.date_start
        if not move_id:
            return data
        total = 0
        ref_id = False
        move = move_obj.browse(cr, uid, move_id, context=context)
        if 'name' in fields:
            data.setdefault('name', move.line_id[-1].name)
        acc1 = False
        for l in move.line_id:
            acc1 = l.account_id
            partner_id = partner_id or l.partner_id.id
            ref_id = ref_id or l.ref
            total += (l.debit or 0.0) - (l.credit or 0.0)

        if 'ref' in fields:
            data['ref'] = ref_id
        if 'partner_id' in fields:
            data['partner_id'] = partner_id

        if move.journal_id.type == 'purchase':
            if total > 0:
                account = move.journal_id.default_credit_account_id
            else:
                account = move.journal_id.default_debit_account_id
        else:
            if total > 0:
                account = move.journal_id.default_credit_account_id
            else:
                account = move.journal_id.default_debit_account_id
        part = partner_id and partner_obj.browse(cr, uid, partner_id) or False
        # part = False is acceptable for fiscal position.
        account = fiscal_pos_obj.map_account(cr, uid, part and part.property_account_position or False, account.id)
        if account:
            account = account_obj.browse(cr, uid, account, context=context)

        if account and ((not fields) or ('debit' in fields) or ('credit' in fields)):
            data['account_id'] = account.id
            # Propose the price VAT excluded, the VAT will be added when confirming line
            if account.tax_ids:
                taxes = fiscal_pos_obj.map_tax(cr, uid, part and part.property_account_position or False, account.tax_ids)
                tax = tax_obj.browse(cr, uid, taxes)
                for t in tax_obj.compute_inv(cr, uid, tax, total, 1):
                    total -= t['amount']

        s = -total
        data['debit'] = s > 0  and s or 0.0
        data['credit'] = s < 0  and -s or 0.0

        if account and account.currency_id:
            data['currency_id'] = account.currency_id.id
            acc = account
            if s>0:
                acc = acc1
            compute_ctx = context.copy()
            compute_ctx.update({
                    'res.currency.compute.account': acc,
                    'res.currency.compute.account_invert': True,
                })
            v = currency_obj.compute(cr, uid, account.company_id.currency_id.id, data['currency_id'], s, context=compute_ctx)
            data['amount_currency'] = v
        return data

    def on_create_write(self, cr, uid, id, context=None):
        if not id:
            return []
        ml = self.browse(cr, uid, id, context=context)
        return map(lambda x: x.id, ml.move_id.line_id)

    def _balance(self, cr, uid, ids, name, arg, context=None):
        if context is None:
            context = {}
        c = context.copy()
        c['initital_bal'] = True
        sql = """SELECT l2.id, SUM(l1.debit-l1.credit)
                    FROM account_move_line l1, account_move_line l2
                    WHERE l2.account_id = l1.account_id
                      AND l1.id <= l2.id
                      AND l2.id IN %s AND """ + \
                self._query_get(cr, uid, obj='l1', context=c) + \
                " GROUP BY l2.id"

        cr.execute(sql, [tuple(ids)])
        return dict(cr.fetchall())

    def _invoice(self, cursor, user, ids, name, arg, context=None):
        invoice_obj = self.pool.get('account.invoice')
        res = {}
        for line_id in ids:
            res[line_id] = False
        cursor.execute('SELECT l.id, i.id ' \
                        'FROM account_move_line l, account_invoice i ' \
                        'WHERE l.move_id = i.move_id ' \
                        'AND l.id IN %s',
                        (tuple(ids),))
        invoice_ids = []
        for line_id, invoice_id in cursor.fetchall():
            res[line_id] = invoice_id
            invoice_ids.append(invoice_id)
        invoice_names = {False: ''}
        for invoice_id, name in invoice_obj.name_get(cursor, user, invoice_ids, context=context):
            invoice_names[invoice_id] = name
        for line_id in res.keys():
            invoice_id = res[line_id]
            res[line_id] = (invoice_id, invoice_names[invoice_id])
        return res

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        result = []
        for line in self.browse(cr, uid, ids, context=context):
            if line.ref:
                result.append((line.id, (line.move_id.name or '')+' ('+line.ref+')'))
            else:
                result.append((line.id, line.move_id.name))
        return result

    def _balance_search(self, cursor, user, obj, name, args, domain=None, context=None):
        if context is None:
            context = {}
        if not args:
            return []
        where = ' AND '.join(map(lambda x: '(abs(sum(debit-credit))'+x[1]+str(x[2])+')',args))
        cursor.execute('SELECT id, SUM(debit-credit) FROM account_move_line \
                     GROUP BY id, debit, credit having '+where)
        res = cursor.fetchall()
        if not res:
            return [('id', '=', '0')]
        return [('id', 'in', [x[0] for x in res])]

    def _invoice_search(self, cursor, user, obj, name, args, context=None):
        if not args:
            return []
        invoice_obj = self.pool.get('account.invoice')
        i = 0
        while i < len(args):
            fargs = args[i][0].split('.', 1)
            if len(fargs) > 1:
                args[i] = (fargs[0], 'in', invoice_obj.search(cursor, user,
                    [(fargs[1], args[i][1], args[i][2])]))
                i += 1
                continue
            if isinstance(args[i][2], basestring):
                res_ids = invoice_obj.name_search(cursor, user, args[i][2], [],
                        args[i][1])
                args[i] = (args[i][0], 'in', [x[0] for x in res_ids])
            i += 1
        qu1, qu2 = [], []
        for x in args:
            if x[1] != 'in':
                if (x[2] is False) and (x[1] == '='):
                    qu1.append('(i.id IS NULL)')
                elif (x[2] is False) and (x[1] == '<>' or x[1] == '!='):
                    qu1.append('(i.id IS NOT NULL)')
                else:
                    qu1.append('(i.id %s %s)' % (x[1], '%s'))
                    qu2.append(x[2])
            elif x[1] == 'in':
                if len(x[2]) > 0:
                    qu1.append('(i.id IN (%s))' % (','.join(['%s'] * len(x[2]))))
                    qu2 += x[2]
                else:
                    qu1.append(' (False)')
        if qu1:
            qu1 = ' AND' + ' AND'.join(qu1)
        else:
            qu1 = ''
        cursor.execute('SELECT l.id ' \
                'FROM account_move_line l, account_invoice i ' \
                'WHERE l.move_id = i.move_id ' + qu1, qu2)
        res = cursor.fetchall()
        if not res:
            return [('id', '=', '0')]
        return [('id', 'in', [x[0] for x in res])]

    def _get_move_lines(self, cr, uid, ids, context=None):
        result = []
        for move in self.pool.get('account.move').browse(cr, uid, ids, context=context):
            for line in move.line_id:
                result.append(line.id)
        return result

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'quantity': fields.float('Quantity', digits=(16,2), help="The optional quantity expressed by this line, eg: number of product sold. The quantity is not a legal requirement but is very useful for some reports."),
        'product_uom_id': fields.many2one('product.uom', 'UoM'),
        'product_id': fields.many2one('product.product', 'Product'),
        'debit': fields.float('Debit', digits_compute=dp.get_precision('Account')),
        'credit': fields.float('Credit', digits_compute=dp.get_precision('Account')),
        'account_id': fields.many2one('account.account', 'Account', required=True, ondelete="cascade", domain=[('type','<>','view'), ('type', '<>', 'closed')], select=2),
        'move_id': fields.many2one('account.move', 'Move', ondelete="cascade", help="The move of this entry line.", select=2, required=True),
        'narration': fields.related('move_id','narration', type='text', relation='account.move', string='Narration'),
        'ref': fields.related('move_id', 'ref', string='Reference', type='char', size=64, store=True),
        'statement_id': fields.many2one('account.bank.statement', 'Statement', help="The bank statement used for bank reconciliation", select=1),
        'reconcile_id': fields.many2one('account.move.reconcile', 'Reconcile', readonly=True, ondelete='set null', select=2),
        'reconcile_partial_id': fields.many2one('account.move.reconcile', 'Partial Reconcile', readonly=True, ondelete='set null', select=2),
        'amount_currency': fields.float('Amount Currency', help="The amount expressed in an optional other currency if it is a multi-currency entry.", digits_compute=dp.get_precision('Account')),
        'amount_residual_currency': fields.function(_amount_residual, method=True, string='Residual Amount', multi="residual", help="The residual amount on a receivable or payable of a journal entry expressed in its currency (maybe different of the company currency)."),
        'amount_residual': fields.function(_amount_residual, method=True, string='Residual Amount', multi="residual", help="The residual amount on a receivable or payable of a journal entry expressed in the company currency."),
        'currency_id': fields.many2one('res.currency', 'Currency', help="The optional other currency if it is a multi-currency entry."),
        'period_id': fields.many2one('account.period', 'Period', required=True, select=2),
        'journal_id': fields.many2one('account.journal', 'Journal', required=True, select=1),
        'blocked': fields.boolean('Litigation', help="You can check this box to mark this journal item as a litigation with the associated partner"),
        'partner_id': fields.many2one('res.partner', 'Partner', select=1, ondelete='restrict'),
        'date_maturity': fields.date('Due date', select=True ,help="This field is used for payable and receivable journal entries. You can put the limit date for the payment of this line."),
        'date': fields.related('move_id','date', string='Effective date', type='date', required=True, select=True,
                                store = {
                                    'account.move': (_get_move_lines, ['date'], 20)
                                }),
        'date_created': fields.date('Creation date', select=True),
        'analytic_lines': fields.one2many('account.analytic.line', 'move_id', 'Analytic lines'),
        'centralisation': fields.selection([('normal','Normal'),('credit','Credit Centralisation'),('debit','Debit Centralisation')], 'Centralisation', size=6),
        'balance': fields.function(_balance, fnct_search=_balance_search, method=True, string='Balance'),
        'state': fields.selection([('draft','Unbalanced'), ('valid','Valid')], 'State', readonly=True,
                                  help='When new move line is created the state will be \'Draft\'.\n* When all the payments are done it will be in \'Valid\' state.'),
        'tax_code_id': fields.many2one('account.tax.code', 'Tax Account', help="The Account can either be a base tax code or a tax code account."),
        'tax_amount': fields.float('Tax/Base Amount', digits_compute=dp.get_precision('Account'), select=True, help="If the Tax account is a tax code account, this field will contain the taxed amount.If the tax account is base tax code, "\
                    "this field will contain the basic amount(without tax)."),
        'invoice': fields.function(_invoice, method=True, string='Invoice',
            type='many2one', relation='account.invoice', fnct_search=_invoice_search),
        'account_tax_id':fields.many2one('account.tax', 'Tax'),
        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic Account'),
        #TODO: remove this
        #'amount_taxed':fields.float("Taxed Amount", digits_compute=dp.get_precision('Account')),
        'company_id': fields.related('account_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True)
    }

    def _get_date(self, cr, uid, context=None):
        if context is None:
            context or {}
        period_obj = self.pool.get('account.period')
        dt = time.strftime('%Y-%m-%d')
        if ('journal_id' in context) and ('period_id' in context):
            cr.execute('SELECT date FROM account_move_line ' \
                    'WHERE journal_id = %s AND period_id = %s ' \
                    'ORDER BY id DESC limit 1',
                    (context['journal_id'], context['period_id']))
            res = cr.fetchone()
            if res:
                dt = res[0]
            else:
                period = period_obj.browse(cr, uid, context['period_id'], context=context)
                dt = period.date_start
        return dt

    def _get_currency(self, cr, uid, context=None):
        if context is None:
            context = {}
        if not context.get('journal_id', False):
            return False
        cur = self.pool.get('account.journal').browse(cr, uid, context['journal_id']).currency
        return cur and cur.id or False

    _defaults = {
        'blocked': False,
        'centralisation': 'normal',
        'date': _get_date,
        'date_created': lambda *a: time.strftime('%Y-%m-%d'),
        'state': 'draft',
        'currency_id': _get_currency,
        'journal_id': lambda self, cr, uid, c: c.get('journal_id', False),
        'account_id': lambda self, cr, uid, c: c.get('account_id', False),
        'period_id': lambda self, cr, uid, c: c.get('period_id', False),
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'account.move.line', context=c)
    }
    _order = "date desc, id desc"
    _sql_constraints = [
        ('credit_debit1', 'CHECK (credit*debit=0)',  'Wrong credit or debit value in accounting entry !'),
        ('credit_debit2', 'CHECK (credit+debit>=0)', 'Wrong credit or debit value in accounting entry !'),
    ]

    def _auto_init(self, cr, context=None):
        super(account_move_line, self)._auto_init(cr, context=context)
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = \'account_move_line_journal_id_period_id_index\'')
        if not cr.fetchone():
            cr.execute('CREATE INDEX account_move_line_journal_id_period_id_index ON account_move_line (journal_id, period_id)')

    def _check_no_view(self, cr, uid, ids, context=None):
        lines = self.browse(cr, uid, ids, context=context)
        for l in lines:
            if l.account_id.type == 'view':
                return False
        return True

    def _check_no_closed(self, cr, uid, ids, context=None):
        lines = self.browse(cr, uid, ids, context=context)
        for l in lines:
            if l.account_id.type == 'closed':
                return False
        return True

    def _check_company_id(self, cr, uid, ids, context=None):
        lines = self.browse(cr, uid, ids, context=context)
        for l in lines:
            if l.company_id != l.account_id.company_id or l.company_id != l.period_id.company_id:
                return False
        return True

    _constraints = [
        (_check_no_view, 'You can not create move line on view account.', ['account_id']),
        (_check_no_closed, 'You can not create move line on closed account.', ['account_id']),
        (_check_company_id, 'Company must be same for its related account and period.',['company_id'] ),
    ]

    #TODO: ONCHANGE_ACCOUNT_ID: set account_tax_id
    def onchange_currency(self, cr, uid, ids, account_id, amount, currency_id, date=False, journal=False, context=None):
        if context is None:
            context = {}
        account_obj = self.pool.get('account.account')
        journal_obj = self.pool.get('account.journal')
        currency_obj = self.pool.get('res.currency')
        if (not currency_id) or (not account_id):
            return {}
        result = {}
        acc = account_obj.browse(cr, uid, account_id, context=context)
        if (amount>0) and journal:
            x = journal_obj.browse(cr, uid, journal).default_credit_account_id
            if x: acc = x
        context.update({
                'date': date,
                'res.currency.compute.account': acc,
            })
        v = currency_obj.compute(cr, uid, currency_id, acc.company_id.currency_id.id, amount, context=context)
        result['value'] = {
            'debit': v > 0 and v or 0.0,
            'credit': v < 0 and -v or 0.0
        }
        return result

    def onchange_partner_id(self, cr, uid, ids, move_id, partner_id, account_id=None, debit=0, credit=0, date=False, journal=False):
        partner_obj = self.pool.get('res.partner')
        payment_term_obj = self.pool.get('account.payment.term')
        journal_obj = self.pool.get('account.journal')
        fiscal_pos_obj = self.pool.get('account.fiscal.position')
        val = {}
        val['date_maturity'] = False

        if not partner_id:
            return {'value':val}
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        part = partner_obj.browse(cr, uid, partner_id)

        if part.property_payment_term:
            res = payment_term_obj.compute(cr, uid, part.property_payment_term.id, 100, date)
            if res:
                val['date_maturity'] = res[0][0]
        if not account_id:
            id1 = part.property_account_payable.id
            id2 =  part.property_account_receivable.id
            if journal:
                jt = journal_obj.browse(cr, uid, journal).type
                #FIXME: Bank and cash journal are such a journal we can not assume a account based on this 2 journals
                # Bank and cash journal can have a payment or receipt transaction, and in both type partner account
                # will not be same id payment then payable, and if receipt then receivable
                #if jt in ('sale', 'purchase_refund', 'bank', 'cash'):
                if jt in ('sale', 'purchase_refund'):
                    val['account_id'] = fiscal_pos_obj.map_account(cr, uid, part and part.property_account_position or False, id2)
                elif jt in ('purchase', 'sale_refund', 'expense', 'bank', 'cash'):
                    val['account_id'] = fiscal_pos_obj.map_account(cr, uid, part and part.property_account_position or False, id1)
                if val.get('account_id', False):
                    d = self.onchange_account_id(cr, uid, ids, val['account_id'])
                    val.update(d['value'])
        return {'value':val}

    def onchange_account_id(self, cr, uid, ids, account_id=False, partner_id=False):
        account_obj = self.pool.get('account.account')
        partner_obj = self.pool.get('res.partner')
        fiscal_pos_obj = self.pool.get('account.fiscal.position')
        val = {}
        if account_id:
            res = account_obj.browse(cr, uid, account_id)
            tax_ids = res.tax_ids
            if tax_ids and partner_id:
                part = partner_obj.browse(cr, uid, partner_id)
                tax_id = fiscal_pos_obj.map_tax(cr, uid, part and part.property_account_position or False, tax_ids)[0]
            else:
                tax_id = tax_ids and tax_ids[0].id or False
            val['account_tax_id'] = tax_id
        return {'value': val}
    #
    # type: the type if reconciliation (no logic behind this field, for info)
    #
    # writeoff; entry generated for the difference between the lines
    #
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        if context and context.get('next_partner_only', False):
            if not context.get('partner_id', False):
                partner = self.get_next_partner_only(cr, uid, offset, context)
            else:
                partner = context.get('partner_id', False)
            if not partner:
                return []
            args.append(('partner_id', '=', partner[0]))
        return super(account_move_line, self).search(cr, uid, args, offset, limit, order, context, count)

    def get_next_partner_only(self, cr, uid, offset=0, context=None):
        cr.execute(
             """
             SELECT p.id
             FROM res_partner p
             RIGHT JOIN (
                SELECT l.partner_id AS partner_id, SUM(l.debit) AS debit, SUM(l.credit) AS credit
                FROM account_move_line l
                LEFT JOIN account_account a ON (a.id = l.account_id)
                    LEFT JOIN res_partner p ON (l.partner_id = p.id)
                    WHERE a.reconcile IS TRUE
                    AND l.reconcile_id IS NULL
                    AND (p.last_reconciliation_date IS NULL OR l.date > p.last_reconciliation_date)
                    AND l.state <> 'draft'
                    GROUP BY l.partner_id
                ) AS s ON (p.id = s.partner_id)
                WHERE debit > 0 AND credit > 0
                ORDER BY p.last_reconciliation_date LIMIT 1 OFFSET %s""", (offset, )
            )
        return cr.fetchone()

    def reconcile_partial(self, cr, uid, ids, type='auto', context=None):
        move_rec_obj = self.pool.get('account.move.reconcile')
        merges = []
        unmerge = []
        total = 0.0
        merges_rec = []
        company_list = []
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            if company_list and not line.company_id.id in company_list:
                raise osv.except_osv(_('Warning !'), _('To reconcile the entries company should be the same for all entries'))
            company_list.append(line.company_id.id)

        for line in self.browse(cr, uid, ids, context=context):
            company_currency_id = line.company_id.currency_id
            if line.reconcile_id:
                raise osv.except_osv(_('Warning'), _('Already Reconciled!'))
            if line.reconcile_partial_id:
                for line2 in line.reconcile_partial_id.line_partial_ids:
                    if not line2.reconcile_id:
                        if line2.id not in merges:
                            merges.append(line2.id)
                        total += (line2.debit or 0.0) - (line2.credit or 0.0)
                merges_rec.append(line.reconcile_partial_id.id)
            else:
                unmerge.append(line.id)
                total += (line.debit or 0.0) - (line.credit or 0.0)
        if self.pool.get('res.currency').is_zero(cr, uid, company_currency_id, total):
            res = self.reconcile(cr, uid, merges+unmerge, context=context)
            return res
        r_id = move_rec_obj.create(cr, uid, {
            'type': type,
            'line_partial_ids': map(lambda x: (4,x,False), merges+unmerge)
        })
        move_rec_obj.reconcile_partial_check(cr, uid, [r_id] + merges_rec, context=context)
        return True

    def reconcile(self, cr, uid, ids, type='auto', writeoff_acc_id=False, writeoff_period_id=False, writeoff_journal_id=False, context=None):
        account_obj = self.pool.get('account.account')
        move_obj = self.pool.get('account.move')
        move_rec_obj = self.pool.get('account.move.reconcile')
        partner_obj = self.pool.get('res.partner')
        currency_obj = self.pool.get('res.currency')
        lines = self.browse(cr, uid, ids, context=context)
        unrec_lines = filter(lambda x: not x['reconcile_id'], lines)
        credit = debit = 0.0
        currency = 0.0
        account_id = False
        partner_id = False
        if context is None:
            context = {}
        company_list = []
        for line in self.browse(cr, uid, ids, context=context):
            if company_list and not line.company_id.id in company_list:
                raise osv.except_osv(_('Warning !'), _('To reconcile the entries company should be the same for all entries'))
            company_list.append(line.company_id.id)
        for line in unrec_lines:
            if line.state <> 'valid':
                raise osv.except_osv(_('Error'),
                        _('Entry "%s" is not valid !') % line.name)
            credit += line['credit']
            debit += line['debit']
            currency += line['amount_currency'] or 0.0
            account_id = line['account_id']['id']
            partner_id = (line['partner_id'] and line['partner_id']['id']) or False
        writeoff = debit - credit

        # Ifdate_p in context => take this date
        if context.has_key('date_p') and context['date_p']:
            date=context['date_p']
        else:
            date = time.strftime('%Y-%m-%d')

        cr.execute('SELECT account_id, reconcile_id '\
                   'FROM account_move_line '\
                   'WHERE id IN %s '\
                   'GROUP BY account_id,reconcile_id',
                   (tuple(ids), ))
        r = cr.fetchall()
        #TODO: move this check to a constraint in the account_move_reconcile object
        if (len(r) != 1) and not context.get('fy_closing', False):
            raise osv.except_osv(_('Error'), _('Entries are not of the same account or already reconciled ! '))
        if not unrec_lines:
            raise osv.except_osv(_('Error'), _('Entry is already reconciled'))
        account = account_obj.browse(cr, uid, account_id, context=context)
        if not context.get('fy_closing', False) and not account.reconcile:
            raise osv.except_osv(_('Error'), _('The account is not defined to be reconciled !'))
        if r[0][1] != None:
            raise osv.except_osv(_('Error'), _('Some entries are already reconciled !'))

        if (not currency_obj.is_zero(cr, uid, account.company_id.currency_id, writeoff)) or \
           (account.currency_id and (not currency_obj.is_zero(cr, uid, account.currency_id, currency))):
            if not writeoff_acc_id:
                raise osv.except_osv(_('Warning'), _('You have to provide an account for the write off entry !'))
            if writeoff > 0:
                debit = writeoff
                credit = 0.0
                self_credit = writeoff
                self_debit = 0.0
            else:
                debit = 0.0
                credit = -writeoff
                self_credit = 0.0
                self_debit = -writeoff
            # If comment exist in context, take it
            if 'comment' in context and context['comment']:
                libelle = context['comment']
            else:
                libelle = _('Write-Off')

            cur_obj = self.pool.get('res.currency')
            cur_id = False
            amount_currency_writeoff = 0.0
            if context.get('company_currency_id',False) != context.get('currency_id',False):
                cur_id = context.get('currency_id',False)
                for line in unrec_lines:
                    if line.currency_id and line.currency_id.id == context.get('currency_id',False):
                        amount_currency_writeoff += line.amount_currency
                    else:
                        tmp_amount = cur_obj.compute(cr, uid, line.account_id.company_id.currency_id.id, context.get('currency_id',False), abs(line.debit-line.credit), context={'date': line.date})
                        amount_currency_writeoff += (line.debit > 0) and tmp_amount or -tmp_amount

            writeoff_lines = [
                (0, 0, {
                    'name': libelle,
                    'debit': self_debit,
                    'credit': self_credit,
                    'account_id': account_id,
                    'date': date,
                    'partner_id': partner_id,
                    'currency_id': cur_id or (account.currency_id.id or False),
                    'amount_currency': amount_currency_writeoff and -1 * amount_currency_writeoff or (account.currency_id.id and -1 * currency or 0.0)
                }),
                (0, 0, {
                    'name': libelle,
                    'debit': debit,
                    'credit': credit,
                    'account_id': writeoff_acc_id,
                    'analytic_account_id': context.get('analytic_id', False),
                    'date': date,
                    'partner_id': partner_id,
                    'currency_id': cur_id or (account.currency_id.id or False),
                    'amount_currency': amount_currency_writeoff and amount_currency_writeoff or (account.currency_id.id and currency or 0.0)
                })
            ]

            writeoff_move_id = move_obj.create(cr, uid, {
                'period_id': writeoff_period_id,
                'journal_id': writeoff_journal_id,
                'date':date,
                'state': 'draft',
                'line_id': writeoff_lines
            })

            writeoff_line_ids = self.search(cr, uid, [('move_id', '=', writeoff_move_id), ('account_id', '=', account_id)])
            if account_id == writeoff_acc_id:
                writeoff_line_ids = [writeoff_line_ids[1]]
            ids += writeoff_line_ids

        r_id = move_rec_obj.create(cr, uid, {
            'type': type,
            'line_id': map(lambda x: (4, x, False), ids),
            'line_partial_ids': map(lambda x: (3, x, False), ids)
        })
        wf_service = netsvc.LocalService("workflow")
        # the id of the move.reconcile is written in the move.line (self) by the create method above
        # because of the way the line_id are defined: (4, x, False)
        for id in ids:
            wf_service.trg_trigger(uid, 'account.move.line', id, cr)

        if lines and lines[0]:
            partner_id = lines[0].partner_id and lines[0].partner_id.id or False
            if partner_id and context and context.get('stop_reconcile', False):
                partner_obj.write(cr, uid, [partner_id], {'last_reconciliation_date': time.strftime('%Y-%m-%d %H:%M:%S')})
        return r_id

    def view_header_get(self, cr, user, view_id, view_type, context=None):
        if context is None:
            context = {}
        context = self.convert_to_period(cr, user, context=context)
        if context.get('account_id', False):
            cr.execute('SELECT code FROM account_account WHERE id = %s', (context['account_id'], ))
            res = cr.fetchone()
            if res:
                res = _('Entries: ')+ (res[0] or '')
            return res
        if (not context.get('journal_id', False)) or (not context.get('period_id', False)):
            return False
        cr.execute('SELECT code FROM account_journal WHERE id = %s', (context['journal_id'], ))
        j = cr.fetchone()[0] or ''
        cr.execute('SELECT code FROM account_period WHERE id = %s', (context['period_id'], ))
        p = cr.fetchone()[0] or ''
        if j or p:
            return j + (p and (':' + p) or '')
        return False

    def onchange_date(self, cr, user, ids, date, context=None):
        """
        Returns a dict that contains new values and context
        @param cr: A database cursor
        @param user: ID of the user currently logged in
        @param date: latest value from user input for field date
        @param args: other arguments
        @param context: context arguments, like lang, time zone
        @return: Returns a dict which contains new values, and context
        """
        res = {}
        if context is None:
            context = {}
        period_pool = self.pool.get('account.period')
        pids = period_pool.search(cr, user, [('date_start','<=',date), ('date_stop','>=',date)])
        if pids:
            res.update({
                'period_id':pids[0]
            })
            context.update({
                'period_id':pids[0]
            })
        return {
            'value':res,
            'context':context,
        }

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        journal_pool = self.pool.get('account.journal')
        if context is None:
            context = {}
        result = super(account_move_line, self).fields_view_get(cr, uid, view_id, view_type, context=context, toolbar=toolbar, submenu=submenu)
        if view_type != 'tree':
            #Remove the toolbar from the form view
            if view_type == 'form':
                if result.get('toolbar', False):
                    result['toolbar']['action'] = []
            #Restrict the list of journal view in search view
            if view_type == 'search' and result['fields'].get('journal_id', False):
                result['fields']['journal_id']['selection'] = journal_pool.name_search(cr, uid, '', [], context=context)
                ctx = context.copy()
                #we add the refunds journal in the selection field of journal
                if context.get('journal_type', False) == 'sale':
                    ctx.update({'journal_type': 'sale_refund'})
                    result['fields']['journal_id']['selection'] += journal_pool.name_search(cr, uid, '', [], context=ctx)
                elif context.get('journal_type', False) == 'purchase':
                    ctx.update({'journal_type': 'purchase_refund'})
                    result['fields']['journal_id']['selection'] += journal_pool.name_search(cr, uid, '', [], context=ctx)
            return result
        if context.get('view_mode', False):
            return result
        fld = []
        fields = {}
        flds = []
        title = _("Accounting Entries") #self.view_header_get(cr, uid, view_id, view_type, context)
        xml = '''<?xml version="1.0"?>\n<tree string="%s" editable="top" refresh="5" on_write="on_create_write" colors="red:state==\'draft\';black:state==\'valid\'">\n\t''' % (title)

        ids = journal_pool.search(cr, uid, [])
        journals = journal_pool.browse(cr, uid, ids, context=context)
        all_journal = [None]
        common_fields = {}
        total = len(journals)
        for journal in journals:
            all_journal.append(journal.id)
            for field in journal.view_id.columns_id:
                if not field.field in fields:
                    fields[field.field] = [journal.id]
                    fld.append((field.field, field.sequence, field.name))
                    flds.append(field.field)
                    common_fields[field.field] = 1
                else:
                    fields.get(field.field).append(journal.id)
                    common_fields[field.field] = common_fields[field.field] + 1
        fld.append(('period_id', 3, _('Period')))
        fld.append(('journal_id', 10, _('Journal')))
        flds.append('period_id')
        flds.append('journal_id')
        fields['period_id'] = all_journal
        fields['journal_id'] = all_journal
        fld = sorted(fld, key=itemgetter(1))
        widths = {
            'statement_id': 50,
            'state': 60,
            'tax_code_id': 50,
            'move_id': 40,
        }
        for field_it in fld:
            field = field_it[0]
            if common_fields.get(field) == total:
                fields.get(field).append(None)
#            if field=='state':
#                state = 'colors="red:state==\'draft\'"'
            attrs = []
            if field == 'debit':
                attrs.append('sum = "%s"' % _("Total debit"))

            elif field == 'credit':
                attrs.append('sum = "%s"' % _("Total credit"))

            elif field == 'move_id':
                attrs.append('required = "False"')

            elif field == 'account_tax_id':
                attrs.append('domain="[(\'parent_id\', \'=\' ,False)]"')
                attrs.append("context=\"{'journal_id': journal_id}\"")

            elif field == 'account_id' and journal.id:
                attrs.append('domain="[(\'journal_id\', \'=\', '+str(journal.id)+'),(\'type\',\'&lt;&gt;\',\'view\'), (\'type\',\'&lt;&gt;\',\'closed\')]" on_change="onchange_account_id(account_id, partner_id)"')

            elif field == 'partner_id':
                attrs.append('on_change="onchange_partner_id(move_id, partner_id, account_id, debit, credit, date, journal_id)"')

            elif field == 'journal_id':
                attrs.append("context=\"{'journal_id': journal_id}\"")

            elif field == 'statement_id':
                attrs.append("domain=\"[('state', '!=', 'confirm'),('journal_id.type', '=', 'bank')]\"")

            elif field == 'date':
                attrs.append('on_change="onchange_date(date)"')

            elif field == 'analytic_account_id':
                attrs.append('''groups="analytic.group_analytic_accounting"''') # Currently it is not working due to framework problem may be ..

            if field in ('amount_currency', 'currency_id'):
                attrs.append('on_change="onchange_currency(account_id, amount_currency, currency_id, date, journal_id)"')
                attrs.append('''attrs="{'readonly': [('state', '=', 'valid')]}"''')

            if field in widths:
                attrs.append('width="'+str(widths[field])+'"')

            if field in ('journal_id',):
                attrs.append("invisible=\"context.get('journal_id', False)\"")
            elif field in ('period_id',):
                attrs.append("invisible=\"context.get('period_id', False)\"")
            else:
                attrs.append("invisible=\"context.get('visible_id') not in %s\"" % (fields.get(field)))
            xml += '''<field name="%s" %s/>\n''' % (field,' '.join(attrs))

        xml += '''</tree>'''
        result['arch'] = xml
        result['fields'] = self.fields_get(cr, uid, flds, context)
        return result

    def _check_moves(self, cr, uid, context=None):
        # use the first move ever created for this journal and period
        if context is None:
            context = {}
        cr.execute('SELECT id, state, name FROM account_move WHERE journal_id = %s AND period_id = %s ORDER BY id limit 1', (context['journal_id'],context['period_id']))
        res = cr.fetchone()
        if res:
            if res[1] != 'draft':
                raise osv.except_osv(_('UserError'),
                       _('The account move (%s) for centralisation ' \
                                'has been confirmed!') % res[2])
        return res

    def _remove_move_reconcile(self, cr, uid, move_ids=[], context=None):
        # Function remove move rencocile ids related with moves
        obj_move_line = self.pool.get('account.move.line')
        obj_move_rec = self.pool.get('account.move.reconcile')
        unlink_ids = []
        if not move_ids:
            return True
        recs = obj_move_line.read(cr, uid, move_ids, ['reconcile_id', 'reconcile_partial_id'])
        full_recs = filter(lambda x: x['reconcile_id'], recs)
        rec_ids = [rec['reconcile_id'][0] for rec in full_recs]
        part_recs = filter(lambda x: x['reconcile_partial_id'], recs)
        part_rec_ids = [rec['reconcile_partial_id'][0] for rec in part_recs]
        unlink_ids += rec_ids
        unlink_ids += part_rec_ids
        if unlink_ids:
            obj_move_rec.unlink(cr, uid, unlink_ids)
        return True

    def unlink(self, cr, uid, ids, context=None, check=True):
        if context is None:
            context = {}
        move_obj = self.pool.get('account.move')
        analytic_obj = self.pool.get('account.analytic.line')
        self._update_check(cr, uid, ids, context)
        result = False
        move_ids = set()
        analytic_ids = set()
        move_line_ids = set()
        for line in self.browse(cr, uid, ids, context=context):
            move_ids.add(line.move_id.id)
            move_line_ids.add(line.id)
            for analytic in line.analytic_lines:
                analytic_ids.add(analytic.id)

        analytic_ids = list(analytic_ids)
        move_ids = list(move_ids)

        if analytic_ids:
            analytic_obj.unlink(cr,uid, analytic_ids, context=context)
        result = super(account_move_line, self).unlink(cr, uid, list(move_line_ids), context=context)
        if check and move_ids:
            move_obj.validate(cr, uid, move_ids, context=context)
        return result

    def _check_date(self, cr, uid, vals, context=None, check=True):
        if context is None:
            context = {}
        move_obj = self.pool.get('account.move')
        journal_obj = self.pool.get('account.journal')
        period_obj = self.pool.get('account.period')
        journal_id = False
        if 'date' in vals.keys():
            if 'journal_id' in vals and 'journal_id' not in context:
                journal_id = vals['journal_id']
            if 'period_id' in vals and 'period_id' not in context:
                period_id = vals['period_id']
            elif 'journal_id' not in context and 'move_id' in vals:
                if vals.get('move_id', False):
                    m = move_obj.browse(cr, uid, vals['move_id'])
                    journal_id = m.journal_id.id
                    period_id = m.period_id.id
            else:
                journal_id = context.get('journal_id', False)
                period_id = context.get('period_id', False)
            if journal_id:
                journal = journal_obj.browse(cr, uid, journal_id, context=context)
                if journal.allow_date and period_id:
                    period = period_obj.browse(cr, uid, period_id, context=context)
                    if not time.strptime(vals['date'][:10],'%Y-%m-%d') >= time.strptime(period.date_start, '%Y-%m-%d') or not time.strptime(vals['date'][:10], '%Y-%m-%d') <= time.strptime(period.date_stop, '%Y-%m-%d'):
                        raise osv.except_osv(_('Error'),_('The date of your Journal Entry is not in the defined period!'))
        else:
            return True

    def write(self, cr, uid, ids, vals, context=None, check=True, update_check=True):
        if context is None:
            context={}
        move_obj = self.pool.get('account.move')
        account_obj = self.pool.get('account.account')
        journal_obj = self.pool.get('account.journal')
        if isinstance(ids, (int, long)):
            ids = [ids]
        if vals.get('account_tax_id', False):
            raise osv.except_osv(_('Unable to change tax !'), _('You can not change the tax, you should remove and recreate lines !'))
        self._check_date(cr, uid, vals, context, check)
        if ('account_id' in vals) and not account_obj.read(cr, uid, vals['account_id'], ['active'])['active']:
            raise osv.except_osv(_('Bad account!'), _('You can not use an inactive account!'))
        if update_check:
            if ('account_id' in vals) or ('journal_id' in vals) or ('period_id' in vals) or ('move_id' in vals) or ('debit' in vals) or ('credit' in vals) or ('date' in vals):
                self._update_check(cr, uid, ids, context)

        todo_date = None
        if vals.get('date', False):
            todo_date = vals['date']
            del vals['date']

        for line in self.browse(cr, uid, ids, context=context):
            ctx = context.copy()
            if ('journal_id' not in ctx):
                if line.move_id:
                   ctx['journal_id'] = line.move_id.journal_id.id
                else:
                    ctx['journal_id'] = line.journal_id.id
            if ('period_id' not in ctx):
                if line.move_id:
                    ctx['period_id'] = line.move_id.period_id.id
                else:
                    ctx['period_id'] = line.period_id.id
            #Check for centralisation
            journal = journal_obj.browse(cr, uid, ctx['journal_id'], context=ctx)
            if journal.centralisation:
                self._check_moves(cr, uid, context=ctx)
        result = super(account_move_line, self).write(cr, uid, ids, vals, context)
        if check:
            done = []
            for line in self.browse(cr, uid, ids):
                if line.move_id.id not in done:
                    done.append(line.move_id.id)
                    move_obj.validate(cr, uid, [line.move_id.id], context)
                    if todo_date:
                        move_obj.write(cr, uid, [line.move_id.id], {'date': todo_date}, context=context)
        return result

    def _update_journal_check(self, cr, uid, journal_id, period_id, context=None):
        journal_obj = self.pool.get('account.journal')
        period_obj = self.pool.get('account.period')
        jour_period_obj = self.pool.get('account.journal.period')
        cr.execute('SELECT state FROM account_journal_period WHERE journal_id = %s AND period_id = %s', (journal_id, period_id))
        result = cr.fetchall()
        for (state,) in result:
            if state == 'done':
                raise osv.except_osv(_('Error !'), _('You can not add/modify entries in a closed journal.'))
        if not result:
            journal = journal_obj.browse(cr, uid, journal_id, context=context)
            period = period_obj.browse(cr, uid, period_id, context=context)
            jour_period_obj.create(cr, uid, {
                'name': (journal.code or journal.name)+':'+(period.name or ''),
                'journal_id': journal.id,
                'period_id': period.id
            })
        return True

    def _update_check(self, cr, uid, ids, context=None):
        done = {}
        for line in self.browse(cr, uid, ids, context=context):
            if line.move_id.state <> 'draft' and (not line.journal_id.entry_posted):
                raise osv.except_osv(_('Error !'), _('You can not do this modification on a confirmed entry ! Please note that you can just change some non important fields !'))
            if line.reconcile_id:
                raise osv.except_osv(_('Error !'), _('You can not do this modification on a reconciled entry ! Please note that you can just change some non important fields !'))
            t = (line.journal_id.id, line.period_id.id)
            if t not in done:
                self._update_journal_check(cr, uid, line.journal_id.id, line.period_id.id, context)
                done[t] = True
        return True

    def create(self, cr, uid, vals, context=None, check=True):
        account_obj = self.pool.get('account.account')
        tax_obj = self.pool.get('account.tax')
        move_obj = self.pool.get('account.move')
        cur_obj = self.pool.get('res.currency')
        journal_obj = self.pool.get('account.journal')
        if context is None:
            context = {}
        if vals.get('move_id', False):
            company_id = self.pool.get('account.move').read(cr, uid, vals['move_id'], ['company_id']).get('company_id', False)
            if company_id:
                vals['company_id'] = company_id[0]
        self._check_date(cr, uid, vals, context, check)
        if ('account_id' in vals) and not account_obj.read(cr, uid, vals['account_id'], ['active'])['active']:
            raise osv.except_osv(_('Bad account!'), _('You can not use an inactive account!'))
        if 'journal_id' in vals:
            context['journal_id'] = vals['journal_id']
        if 'period_id' in vals:
            context['period_id'] = vals['period_id']
        if ('journal_id' not in context) and ('move_id' in vals) and vals['move_id']:
            m = move_obj.browse(cr, uid, vals['move_id'])
            context['journal_id'] = m.journal_id.id
            context['period_id'] = m.period_id.id

        self._update_journal_check(cr, uid, context['journal_id'], context['period_id'], context)
        move_id = vals.get('move_id', False)
        journal = journal_obj.browse(cr, uid, context['journal_id'], context=context)
        if not move_id:
            if journal.centralisation:
                #Check for centralisation
                res = self._check_moves(cr, uid, context)
                if res:
                    vals['move_id'] = res[0]
            if not vals.get('move_id', False):
                if journal.sequence_id:
                    #name = self.pool.get('ir.sequence').get_id(cr, uid, journal.sequence_id.id)
                    v = {
                        'date': vals.get('date', time.strftime('%Y-%m-%d')),
                        'period_id': context['period_id'],
                        'journal_id': context['journal_id']
                    }
                    if vals.get('ref', ''):
                        v.update({'ref': vals['ref']})
                    move_id = move_obj.create(cr, uid, v, context)
                    vals['move_id'] = move_id
                else:
                    raise osv.except_osv(_('No piece number !'), _('Can not create an automatic sequence for this piece !\n\nPut a sequence in the journal definition for automatic numbering or create a sequence manually for this piece.'))
        ok = not (journal.type_control_ids or journal.account_control_ids)
        if ('account_id' in vals):
            account = account_obj.browse(cr, uid, vals['account_id'], context=context)
            if journal.type_control_ids:
                type = account.user_type
                for t in journal.type_control_ids:
                    if type.code == t.code:
                        ok = True
                        break
            if journal.account_control_ids and not ok:
                for a in journal.account_control_ids:
                    if a.id == vals['account_id']:
                        ok = True
                        break
            # Automatically convert in the account's secondary currency if there is one and
            # the provided values were not already multi-currency
            if account.currency_id and 'amount_currency' not in vals and account.currency_id.id != account.company_id.currency_id.id:
                vals['currency_id'] = account.currency_id.id
                ctx = {}
                if 'date' in vals:
                    ctx['date'] = vals['date']
                vals['amount_currency'] = cur_obj.compute(cr, uid, account.company_id.currency_id.id,
                    account.currency_id.id, vals.get('debit', 0.0)-vals.get('credit', 0.0), context=ctx)
        if not ok:
            raise osv.except_osv(_('Bad account !'), _('You can not use this general account in this journal !'))

        if vals.get('analytic_account_id',False):
            if journal.analytic_journal_id:
                vals['analytic_lines'] = [(0,0, {
                        'name': vals['name'],
                        'date': vals.get('date', time.strftime('%Y-%m-%d')),
                        'account_id': vals.get('analytic_account_id', False),
                        'unit_amount': vals.get('quantity', 1.0),
                        'amount': vals.get('debit', 0.0) or vals.get('credit', 0.0),
                        'general_account_id': vals.get('account_id', False),
                        'journal_id': journal.analytic_journal_id.id,
                        'ref': vals.get('ref', False),
                        'user_id': uid
            })]

        result = super(osv.osv, self).create(cr, uid, vals, context=context)
        # CREATE Taxes
        if vals.get('account_tax_id', False):
            tax_id = tax_obj.browse(cr, uid, vals['account_tax_id'])
            total = vals['debit'] - vals['credit']
            if journal.type in ('purchase_refund', 'sale_refund'):
                base_code = 'ref_base_code_id'
                tax_code = 'ref_tax_code_id'
                account_id = 'account_paid_id'
                base_sign = 'ref_base_sign'
                tax_sign = 'ref_tax_sign'
            else:
                base_code = 'base_code_id'
                tax_code = 'tax_code_id'
                account_id = 'account_collected_id'
                base_sign = 'base_sign'
                tax_sign = 'tax_sign'
            tmp_cnt = 0
            for tax in tax_obj.compute_all(cr, uid, [tax_id], total, 1.00).get('taxes'):
                #create the base movement
                if tmp_cnt == 0:
                    if tax[base_code]:
                        tmp_cnt += 1
                        self.write(cr, uid,[result], {
                            'tax_code_id': tax[base_code],
                            'tax_amount': tax[base_sign] * abs(total)
                        })
                else:
                    data = {
                        'move_id': vals['move_id'],
                        'journal_id': vals['journal_id'],
                        'period_id': vals['period_id'],
                        'name': tools.ustr(vals['name'] or '') + ' ' + tools.ustr(tax['name'] or ''),
                        'date': vals['date'],
                        'partner_id': vals.get('partner_id',False),
                        'ref': vals.get('ref',False),
                        'account_tax_id': False,
                        'tax_code_id': tax[base_code],
                        'tax_amount': tax[base_sign] * abs(total),
                        'account_id': vals['account_id'],
                        'credit': 0.0,
                        'debit': 0.0,
                    }
                    if data['tax_code_id']:
                        self.create(cr, uid, data, context)
                #create the VAT movement
                data = {
                    'move_id': vals['move_id'],
                    'journal_id': vals['journal_id'],
                    'period_id': vals['period_id'],
                    'name': tools.ustr(vals['name'] or '') + ' ' + tools.ustr(tax['name'] or ''),
                    'date': vals['date'],
                    'partner_id': vals.get('partner_id',False),
                    'ref': vals.get('ref',False),
                    'account_tax_id': False,
                    'tax_code_id': tax[tax_code],
                    'tax_amount': tax[tax_sign] * abs(tax['amount']),
                    'account_id': tax[account_id] or vals['account_id'],
                    'credit': tax['amount']<0 and -tax['amount'] or 0.0,
                    'debit': tax['amount']>0 and tax['amount'] or 0.0,
                }
                if data['tax_code_id']:
                    self.create(cr, uid, data, context)
            del vals['account_tax_id']

        if check and ((not context.get('no_store_function')) or journal.entry_posted):
            tmp = move_obj.validate(cr, uid, [vals['move_id']], context)
            if journal.entry_posted and tmp:
                move_obj.button_validate(cr,uid, [vals['move_id']], context)
        return result

account_move_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
