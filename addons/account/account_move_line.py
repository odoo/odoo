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

from openerp import workflow
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp import tools
from openerp.report import report_sxw
import openerp

class account_move_line(osv.osv):
    _name = "account.move.line"
    _description = "Journal Items"

    def _query_get(self, cr, uid, obj='l', context=None):
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        fiscalperiod_obj = self.pool.get('account.period')
        account_obj = self.pool.get('account.account')
        fiscalyear_ids = []
        context = dict(context or {})
        initial_bal = context.get('initial_bal', False)
        company_clause = " "
        query = ''
        query_params = {}
        if context.get('company_id'):
            company_clause = " AND " +obj+".company_id = %(company_id)s"
            query_params['company_id'] = context['company_id']
        if not context.get('fiscalyear'):
            if context.get('all_fiscalyear'):
                #this option is needed by the aged balance report because otherwise, if we search only the draft ones, an open invoice of a closed fiscalyear won't be displayed
                fiscalyear_ids = fiscalyear_obj.search(cr, uid, [])
            else:
                fiscalyear_ids = fiscalyear_obj.search(cr, uid, [('state', '=', 'draft')])
        else:
            #for initial balance as well as for normal query, we check only the selected FY because the best practice is to generate the FY opening entries
            fiscalyear_ids = context['fiscalyear']
            if isinstance(context['fiscalyear'], (int, long)):
                fiscalyear_ids = [fiscalyear_ids]

        query_params['fiscalyear_ids'] = tuple(fiscalyear_ids) or (0,)
        state = context.get('state', False)
        where_move_state = ''
        where_move_lines_by_date = ''

        if context.get('date_from') and context.get('date_to'):
            query_params['date_from'] = context['date_from']
            query_params['date_to'] = context['date_to']
            if initial_bal:
                where_move_lines_by_date = " AND " +obj+".move_id IN (SELECT id FROM account_move WHERE date < %(date_from)s)"
            else:
                where_move_lines_by_date = " AND " +obj+".move_id IN (SELECT id FROM account_move WHERE date >= %(date_from)s AND date <= %(date_to)s)"

        if state:
            if state.lower() not in ['all']:
                query_params['state'] = state
                where_move_state= " AND "+obj+".move_id IN (SELECT id FROM account_move WHERE account_move.state = %(state)s)"
        if context.get('period_from') and context.get('period_to') and not context.get('periods'):
            if initial_bal:
                period_company_id = fiscalperiod_obj.browse(cr, uid, context['period_from'], context=context).company_id.id
                first_period = fiscalperiod_obj.search(cr, uid, [('company_id', '=', period_company_id)], order='date_start', limit=1)[0]
                context['periods'] = fiscalperiod_obj.build_ctx_periods(cr, uid, first_period, context['period_from'])
            else:
                context['periods'] = fiscalperiod_obj.build_ctx_periods(cr, uid, context['period_from'], context['period_to'])
        if context.get('periods'):
            query_params['period_ids'] = tuple(context['periods'])
            if initial_bal:
                query = obj+".state <> 'draft' AND "+obj+".period_id IN (SELECT id FROM account_period WHERE fiscalyear_id IN %(fiscalyear_ids)s)" + where_move_state + where_move_lines_by_date
                period_ids = fiscalperiod_obj.search(cr, uid, [('id', 'in', context['periods'])], order='date_start', limit=1)
                if period_ids and period_ids[0]:
                    first_period = fiscalperiod_obj.browse(cr, uid, period_ids[0], context=context)
                    query_params['date_start'] = first_period.date_start
                    query = obj+".state <> 'draft' AND "+obj+".period_id IN (SELECT id FROM account_period WHERE fiscalyear_id IN %(fiscalyear_ids)s AND date_start <= %(date_start)s AND id NOT IN %(period_ids)s)" + where_move_state + where_move_lines_by_date
            else:
                query = obj+".state <> 'draft' AND "+obj+".period_id IN (SELECT id FROM account_period WHERE fiscalyear_id IN %(fiscalyear_ids)s AND id IN %(period_ids)s)" + where_move_state + where_move_lines_by_date
        else:
            query = obj+".state <> 'draft' AND "+obj+".period_id IN (SELECT id FROM account_period WHERE fiscalyear_id IN %(fiscalyear_ids)s)" + where_move_state + where_move_lines_by_date

        if initial_bal and not context.get('periods') and not where_move_lines_by_date:
            #we didn't pass any filter in the context, and the initial balance can't be computed using only the fiscalyear otherwise entries will be summed twice
            #so we have to invalidate this query
            raise osv.except_osv(_('Warning!'),_("You have not supplied enough arguments to compute the initial balance, please select a period and a journal in the context."))

        if context.get('journal_ids'):
            query_params['journal_ids'] = tuple(context['journal_ids'])
            query += ' AND '+obj+'.journal_id IN %(journal_ids)s'

        if context.get('chart_account_id'):
            child_ids = account_obj._get_children_and_consol(cr, uid, [context['chart_account_id']], context=context)
            query_params['child_ids'] = tuple(child_ids)
            query += ' AND '+obj+'.account_id IN %(child_ids)s'

        query += company_clause
        return cr.mogrify(query, query_params)

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
            if not move_line.account_id.reconcile:
                #this function does not suport to be used on move lines not related to a reconcilable account
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

    def _prepare_analytic_line(self, cr, uid, obj_line, context=None):
        """
        Prepare the values given at the create() of account.analytic.line upon the validation of a journal item having
        an analytic account. This method is intended to be extended in other modules.

        :param obj_line: browse record of the account.move.line that triggered the analytic line creation
        """
        return {'name': obj_line.name,
                'date': obj_line.date,
                'account_id': obj_line.analytic_account_id.id,
                'unit_amount': obj_line.quantity,
                'product_id': obj_line.product_id and obj_line.product_id.id or False,
                'product_uom_id': obj_line.product_uom_id and obj_line.product_uom_id.id or False,
                'amount': (obj_line.credit or  0.0) - (obj_line.debit or 0.0),
                'general_account_id': obj_line.account_id.id,
                'journal_id': obj_line.journal_id.analytic_journal_id.id,
                'ref': obj_line.ref,
                'move_id': obj_line.id,
                'user_id': obj_line.invoice.user_id.id or uid,
               }

    def create_analytic_lines(self, cr, uid, ids, context=None):
        acc_ana_line_obj = self.pool.get('account.analytic.line')
        for obj_line in self.browse(cr, uid, ids, context=context):
            if obj_line.analytic_lines:
                acc_ana_line_obj.unlink(cr,uid,[obj.id for obj in obj_line.analytic_lines])
            if obj_line.analytic_account_id:
                if not obj_line.journal_id.analytic_journal_id:
                    raise osv.except_osv(_('No Analytic Journal!'),_("You have to define an analytic journal on the '%s' journal!") % (obj_line.journal_id.name, ))
                vals_line = self._prepare_analytic_line(cr, uid, obj_line, context=context)
                acc_ana_line_obj.create(cr, uid, vals_line)
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
                context = dict(context, period_id=ids and ids[0] or False)
        return context

    def _default_get(self, cr, uid, fields, context=None):
        #default_get should only do the following:
        #   -propose the next amount in debit/credit in order to balance the move
        #   -propose the next account from the journal (default debit/credit account) accordingly
        context = dict(context or {})
        account_obj = self.pool.get('account.account')
        period_obj = self.pool.get('account.period')
        journal_obj = self.pool.get('account.journal')
        move_obj = self.pool.get('account.move')
        tax_obj = self.pool.get('account.tax')
        fiscal_pos_obj = self.pool.get('account.fiscal.position')
        partner_obj = self.pool.get('res.partner')
        currency_obj = self.pool.get('res.currency')

        if not context.get('journal_id', False):
            context['journal_id'] = context.get('search_default_journal_id', False)
        if not context.get('period_id', False):
            context['period_id'] = context.get('search_default_period_id', False)
        context = self.convert_to_period(cr, uid, context)

        # Compute simple values
        data = super(account_move_line, self).default_get(cr, uid, fields, context=context)
        if context.get('journal_id'):
            total = 0.0
            #in account.move form view, it is not possible to compute total debit and credit using
            #a browse record. So we must use the context to pass the whole one2many field and compute the total
            if context.get('line_id'):
                for move_line_dict in move_obj.resolve_2many_commands(cr, uid, 'line_id', context.get('line_id'), context=context):
                    data['name'] = data.get('name') or move_line_dict.get('name')
                    data['partner_id'] = data.get('partner_id') or move_line_dict.get('partner_id')
                    total += move_line_dict.get('debit', 0.0) - move_line_dict.get('credit', 0.0)
            elif context.get('period_id'):
                #find the date and the ID of the last unbalanced account.move encoded by the current user in that journal and period
                move_id = False
                cr.execute('''SELECT move_id, date FROM account_move_line
                    WHERE journal_id = %s AND period_id = %s AND create_uid = %s AND state = %s
                    ORDER BY id DESC limit 1''', (context['journal_id'], context['period_id'], uid, 'draft'))
                res = cr.fetchone()
                move_id = res and res[0] or False
                data['date'] = res and res[1] or period_obj.browse(cr, uid, context['period_id'], context=context).date_start
                data['move_id'] = move_id
                if move_id:
                    #if there exist some unbalanced accounting entries that match the journal and the period,
                    #we propose to continue the same move by copying the ref, the name, the partner...
                    move = move_obj.browse(cr, uid, move_id, context=context)
                    data.setdefault('name', move.line_id[-1].name)
                    for l in move.line_id:
                        data['partner_id'] = data.get('partner_id') or l.partner_id.id
                        data['ref'] = data.get('ref') or l.ref
                        total += (l.debit or 0.0) - (l.credit or 0.0)

            #compute the total of current move
            data['debit'] = total < 0 and -total or 0.0
            data['credit'] = total > 0 and total or 0.0
            #pick the good account on the journal accordingly if the next proposed line will be a debit or a credit
            journal_data = journal_obj.browse(cr, uid, context['journal_id'], context=context)
            account = total > 0 and journal_data.default_credit_account_id or journal_data.default_debit_account_id
            #map the account using the fiscal position of the partner, if needed
            if isinstance(data.get('partner_id'), (int, long)):
                part = partner_obj.browse(cr, uid, data['partner_id'], context=context)
            elif isinstance(data.get('partner_id'), (tuple, list)):
                part = partner_obj.browse(cr, uid, data['partner_id'][0], context=context)
            else:
                part = False
            if account and part:
                account = fiscal_pos_obj.map_account(cr, uid, part and part.property_account_position or False, account.id)
                account = account_obj.browse(cr, uid, account, context=context)
            data['account_id'] =  account and account.id or False
            #compute the amount in secondary currency of the account, if needed
            if account and account.currency_id:
                data['currency_id'] = account.currency_id.id
                #set the context for the multi currency change
                compute_ctx = context.copy()
                compute_ctx.update({
                        #the following 2 parameters are used to choose the currency rate, in case where the account
                        #doesn't work with an outgoing currency rate method 'at date' but 'average'
                        'res.currency.compute.account': account,
                        'res.currency.compute.account_invert': True,
                    })
                if data.get('date'):
                    compute_ctx.update({'date': data['date']})
                data['amount_currency'] = currency_obj.compute(cr, uid, account.company_id.currency_id.id, data['currency_id'], -total, context=compute_ctx)
        data = self._default_get_move_form_hook(cr, uid, data)
        return data

    def on_create_write(self, cr, uid, id, context=None):
        if not id:
            return []
        ml = self.browse(cr, uid, id, context=context)
        domain = (context or {}).get('on_write_domain', [])
        return self.pool.get('account.move.line').search(cr, uid, domain + [['id', 'in', [l.id for l in ml.move_id.line_id]]], context=context)

    def _balance(self, cr, uid, ids, name, arg, context=None):
        if context is None:
            context = {}
        c = context.copy()
        c['initital_bal'] = True
        sql = """SELECT l1.id, COALESCE(SUM(l2.debit-l2.credit), 0)
                    FROM account_move_line l1 LEFT JOIN account_move_line l2
                    ON (l1.account_id = l2.account_id
                      AND l2.id <= l1.id
                      AND """ + \
                self._query_get(cr, uid, obj='l2', context=c) + \
                ") WHERE l1.id IN %s GROUP BY l1.id"

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
        invoice_names = {}
        for invoice_id, name in invoice_obj.name_get(cursor, user, invoice_ids, context=context):
            invoice_names[invoice_id] = name
        for line_id in res.keys():
            invoice_id = res[line_id]
            res[line_id] = invoice_id and (invoice_id, invoice_names[invoice_id]) or False
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

    def _get_reconcile(self, cr, uid, ids,name, unknow_none, context=None):
        res = dict.fromkeys(ids, False)
        for line in self.browse(cr, uid, ids, context=context):
            if line.reconcile_id:
                res[line.id] = str(line.reconcile_id.name)
            elif line.reconcile_partial_id:
                res[line.id] = str(line.reconcile_partial_id.name)
        return res

    def _get_move_from_reconcile(self, cr, uid, ids, context=None):
        move = {}
        for r in self.pool.get('account.move.reconcile').browse(cr, uid, ids, context=context):
            for line in r.line_partial_ids:
                move[line.move_id.id] = True
            for line in r.line_id:
                move[line.move_id.id] = True
        move_line_ids = []
        if move:
            move_line_ids = self.pool.get('account.move.line').search(cr, uid, [('move_id','in',move.keys())], context=context)
        return move_line_ids


    _columns = {
        'name': fields.char('Name', required=True),
        'quantity': fields.float('Quantity', digits=(16,2), help="The optional quantity expressed by this line, eg: number of product sold. The quantity is not a legal requirement but is very useful for some reports."),
        'product_uom_id': fields.many2one('product.uom', 'Unit of Measure'),
        'product_id': fields.many2one('product.product', 'Product'),
        'debit': fields.float('Debit', digits_compute=dp.get_precision('Account')),
        'credit': fields.float('Credit', digits_compute=dp.get_precision('Account')),
        'account_id': fields.many2one('account.account', 'Account', required=True, ondelete="cascade", domain=[('type','<>','view'), ('type', '<>', 'closed')], select=2),
        'move_id': fields.many2one('account.move', 'Journal Entry', ondelete="cascade", help="The move of this entry line.", select=2, required=True, auto_join=True),
        'narration': fields.related('move_id','narration', type='text', relation='account.move', string='Internal Note'),
        'ref': fields.related('move_id', 'ref', string='Reference', type='char', store=True),
        'statement_id': fields.many2one('account.bank.statement', 'Statement', help="The bank statement used for bank reconciliation", select=1, copy=False),
        'reconcile_id': fields.many2one('account.move.reconcile', 'Reconcile', readonly=True, ondelete='set null', select=2, copy=False),
        'reconcile_partial_id': fields.many2one('account.move.reconcile', 'Partial Reconcile', readonly=True, ondelete='set null', select=2, copy=False),
        'reconcile_ref': fields.function(_get_reconcile, type='char', string='Reconcile Ref', oldname='reconcile', store={
                    'account.move.line': (lambda self, cr, uid, ids, c={}: ids, ['reconcile_id','reconcile_partial_id'], 50),'account.move.reconcile': (_get_move_from_reconcile, None, 50)}),
        'amount_currency': fields.float('Amount Currency', help="The amount expressed in an optional other currency if it is a multi-currency entry.", digits_compute=dp.get_precision('Account')),
        'amount_residual_currency': fields.function(_amount_residual, string='Residual Amount in Currency', multi="residual", help="The residual amount on a receivable or payable of a journal entry expressed in its currency (maybe different of the company currency)."),
        'amount_residual': fields.function(_amount_residual, string='Residual Amount', multi="residual", help="The residual amount on a receivable or payable of a journal entry expressed in the company currency."),
        'currency_id': fields.many2one('res.currency', 'Currency', help="The optional other currency if it is a multi-currency entry."),
        'journal_id': fields.related('move_id', 'journal_id', string='Journal', type='many2one', relation='account.journal', required=True, select=True,
                                store = {
                                    'account.move': (_get_move_lines, ['journal_id'], 20)
                                }),
        'period_id': fields.related('move_id', 'period_id', string='Period', type='many2one', relation='account.period', required=True, select=True,
                                store = {
                                    'account.move': (_get_move_lines, ['period_id'], 20)
                                }),
        'blocked': fields.boolean('No Follow-up', help="You can check this box to mark this journal item as a litigation with the associated partner"),
        'partner_id': fields.many2one('res.partner', 'Partner', select=1, ondelete='restrict'),
        'date_maturity': fields.date('Due date', select=True ,help="This field is used for payable and receivable journal entries. You can put the limit date for the payment of this line."),
        'date': fields.related('move_id','date', string='Effective date', type='date', required=True, select=True,
                                store = {
                                    'account.move': (_get_move_lines, ['date'], 20)
                                }),
        'date_created': fields.date('Creation date', select=True),
        'analytic_lines': fields.one2many('account.analytic.line', 'move_id', 'Analytic lines'),
        'centralisation': fields.selection([('normal','Normal'),('credit','Credit Centralisation'),('debit','Debit Centralisation'),('currency','Currency Adjustment')], 'Centralisation', size=8),
        'balance': fields.function(_balance, fnct_search=_balance_search, string='Balance'),
        'state': fields.selection([('draft','Unbalanced'), ('valid','Balanced')], 'Status', readonly=True, copy=False),
        'tax_code_id': fields.many2one('account.tax.code', 'Tax Account', help="The Account can either be a base tax code or a tax code account."),
        'tax_amount': fields.float('Tax/Base Amount', digits_compute=dp.get_precision('Account'), select=True, help="If the Tax account is a tax code account, this field will contain the taxed amount.If the tax account is base tax code, "\
                    "this field will contain the basic amount(without tax)."),
        'invoice': fields.function(_invoice, string='Invoice',
            type='many2one', relation='account.invoice', fnct_search=_invoice_search),
        'account_tax_id':fields.many2one('account.tax', 'Tax', copy=False),
        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic Account'),
        'company_id': fields.related('account_id', 'company_id', type='many2one', relation='res.company',
                            string='Company', store=True, readonly=True)
    }

    def _get_date(self, cr, uid, context=None):
        if context is None:
            context or {}
        period_obj = self.pool.get('account.period')
        dt = time.strftime('%Y-%m-%d')
        if context.get('journal_id') and context.get('period_id'):
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

    def _get_period(self, cr, uid, context=None):
        """
        Return  default account period value
        """
        context = context or {}
        if context.get('period_id', False):
            return context['period_id']
        account_period_obj = self.pool.get('account.period')
        ids = account_period_obj.find(cr, uid, context=context)
        period_id = False
        if ids:
            period_id = ids[0]
        return period_id

    def _get_journal(self, cr, uid, context=None):
        """
        Return journal based on the journal type
        """
        context = context or {}
        if context.get('journal_id', False):
            return context['journal_id']
        journal_id = False

        journal_pool = self.pool.get('account.journal')
        if context.get('journal_type', False):
            jids = journal_pool.search(cr, uid, [('type','=', context.get('journal_type'))])
            if not jids:
                model, action_id = self.pool['ir.model.data'].get_object_reference(cr, uid, 'account', 'action_account_journal_form')
                msg = _("""Cannot find any account journal of "%s" type for this company, You should create one.\n Please go to Journal Configuration""") % context.get('journal_type').replace('_', ' ').title()
                raise openerp.exceptions.RedirectWarning(msg, action_id, _('Go to the configuration panel'))
            journal_id = jids[0]
        return journal_id


    _defaults = {
        'blocked': False,
        'centralisation': 'normal',
        'date': _get_date,
        'date_created': fields.date.context_today,
        'state': 'draft',
        'currency_id': _get_currency,
        'journal_id': _get_journal,
        'credit': 0.0,
        'debit': 0.0,
        'amount_currency': 0.0,
        'account_id': lambda self, cr, uid, c: c.get('account_id', False),
        'period_id': _get_period,
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'account.move.line', context=c)
    }
    _order = "date desc, id desc"
    _sql_constraints = [
        ('credit_debit1', 'CHECK (credit*debit=0)',  'Wrong credit or debit value in accounting entry !'),
        ('credit_debit2', 'CHECK (credit+debit>=0)', 'Wrong credit or debit value in accounting entry !'),
    ]

    def _auto_init(self, cr, context=None):
        res = super(account_move_line, self)._auto_init(cr, context=context)
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = \'account_move_line_journal_id_period_id_index\'')
        if not cr.fetchone():
            cr.execute('CREATE INDEX account_move_line_journal_id_period_id_index '
                       'ON account_move_line (journal_id, period_id, state, create_uid, id DESC)')
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('account_move_line_date_id_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX account_move_line_date_id_index ON account_move_line (date DESC, id desc)')
        return res

    def _check_no_view(self, cr, uid, ids, context=None):
        lines = self.browse(cr, uid, ids, context=context)
        for l in lines:
            if l.account_id.type in ('view', 'consolidation'):
                return False
        return True

    def _check_no_closed(self, cr, uid, ids, context=None):
        lines = self.browse(cr, uid, ids, context=context)
        for l in lines:
            if l.account_id.type == 'closed':
                raise osv.except_osv(_('Error!'), _('You cannot create journal items on a closed account %s %s.') % (l.account_id.code, l.account_id.name))
        return True

    def _check_company_id(self, cr, uid, ids, context=None):
        lines = self.browse(cr, uid, ids, context=context)
        for l in lines:
            if l.company_id != l.account_id.company_id or l.company_id != l.period_id.company_id:
                return False
        return True

    def _check_date(self, cr, uid, ids, context=None):
        for l in self.browse(cr, uid, ids, context=context):
            if l.journal_id.allow_date:
                if not time.strptime(l.date[:10],'%Y-%m-%d') >= time.strptime(l.period_id.date_start, '%Y-%m-%d') or not time.strptime(l.date[:10], '%Y-%m-%d') <= time.strptime(l.period_id.date_stop, '%Y-%m-%d'):
                    return False
        return True

    def _check_currency(self, cr, uid, ids, context=None):
        for l in self.browse(cr, uid, ids, context=context):
            if l.account_id.currency_id:
                if not l.currency_id or not l.currency_id.id == l.account_id.currency_id.id:
                    return False
        return True

    def _check_currency_and_amount(self, cr, uid, ids, context=None):
        for l in self.browse(cr, uid, ids, context=context):
            if (l.amount_currency and not l.currency_id):
                return False
        return True

    def _check_currency_amount(self, cr, uid, ids, context=None):
        for l in self.browse(cr, uid, ids, context=context):
            if l.amount_currency:
                if (l.amount_currency > 0.0 and l.credit > 0.0) or (l.amount_currency < 0.0 and l.debit > 0.0):
                    return False
        return True

    def _check_currency_company(self, cr, uid, ids, context=None):
        for l in self.browse(cr, uid, ids, context=context):
            if l.currency_id.id == l.company_id.currency_id.id:
                return False
        return True

    _constraints = [
        (_check_no_view, 'You cannot create journal items on an account of type view or consolidation.', ['account_id']),
        (_check_no_closed, 'You cannot create journal items on closed account.', ['account_id']),
        (_check_company_id, 'Account and Period must belong to the same company.', ['company_id']),
        (_check_date, 'The date of your Journal Entry is not in the defined period! You should change the date or remove this constraint from the journal.', ['date']),
        (_check_currency, 'The selected account of your Journal Entry forces to provide a secondary currency. You should remove the secondary currency on the account or select a multi-currency view on the journal.', ['currency_id']),
        (_check_currency_and_amount, "You cannot create journal items with a secondary currency without recording both 'currency' and 'amount currency' field.", ['currency_id','amount_currency']),
        (_check_currency_amount, 'The amount expressed in the secondary currency must be positive when account is debited and negative when account is credited.', ['amount_currency']),
        (_check_currency_company, "You cannot provide a secondary currency if it is the same than the company one." , ['currency_id']),
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
        context = dict(context)
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

    def onchange_partner_id(self, cr, uid, ids, move_id, partner_id, account_id=None, debit=0, credit=0, date=False, journal=False, context=None):
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
        jt = False
        if journal:
            jt = journal_obj.browse(cr, uid, journal, context=context).type
        part = partner_obj.browse(cr, uid, partner_id, context=context)

        payment_term_id = False
        if jt and jt in ('purchase', 'purchase_refund') and part.property_supplier_payment_term:
            payment_term_id = part.property_supplier_payment_term.id
        elif jt and part.property_payment_term:
            payment_term_id = part.property_payment_term.id
        if payment_term_id:
            res = payment_term_obj.compute(cr, uid, payment_term_id, 100, date)
            if res:
                val['date_maturity'] = res[0][0]
        if not account_id:
            id1 = part.property_account_payable.id
            id2 =  part.property_account_receivable.id
            if jt:
                if jt in ('sale', 'purchase_refund'):
                    val['account_id'] = fiscal_pos_obj.map_account(cr, uid, part and part.property_account_position or False, id2)
                elif jt in ('purchase', 'sale_refund'):
                    val['account_id'] = fiscal_pos_obj.map_account(cr, uid, part and part.property_account_position or False, id1)
                elif jt in ('general', 'bank', 'cash'):
                    if part.customer:
                        val['account_id'] = fiscal_pos_obj.map_account(cr, uid, part and part.property_account_position or False, id2)
                    elif part.supplier:
                        val['account_id'] = fiscal_pos_obj.map_account(cr, uid, part and part.property_account_position or False, id1)
                if val.get('account_id', False):
                    d = self.onchange_account_id(cr, uid, ids, account_id=val['account_id'], partner_id=part.id, context=context)
                    val.update(d['value'])
        return {'value':val}

    def onchange_account_id(self, cr, uid, ids, account_id=False, partner_id=False, context=None):
        account_obj = self.pool.get('account.account')
        partner_obj = self.pool.get('res.partner')
        fiscal_pos_obj = self.pool.get('account.fiscal.position')
        val = {}
        if account_id:
            res = account_obj.browse(cr, uid, account_id, context=context)
            tax_ids = res.tax_ids
            if tax_ids and partner_id:
                part = partner_obj.browse(cr, uid, partner_id, context=context)
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
        if context.get('fiscalyear'):
            args.append(('period_id.fiscalyear_id', '=', context.get('fiscalyear', False)))
        if context and context.get('next_partner_only', False):
            if not context.get('partner_id', False):
                partner = self.list_partners_to_reconcile(cr, uid, context=context)
                if partner:
                    partner = partner[0]
            else:
                partner = context.get('partner_id', False)
            if not partner:
                return []
            args.append(('partner_id', '=', partner[0]))
        return super(account_move_line, self).search(cr, uid, args, offset, limit, order, context, count)

    def prepare_move_lines_for_reconciliation_widget(self, cr, uid, lines, target_currency=False, target_date=False, context=None):
        """ Returns move lines formatted for the manual/bank reconciliation widget

            :param target_currency: curreny you want the move line debit/credit converted into
            :param target_date: date to use for the monetary conversion
        """
        if not lines:
            return []
        if context is None:
            context = {}
        ctx = context.copy()
        currency_obj = self.pool.get('res.currency')
        company_currency = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.currency_id
        rml_parser = report_sxw.rml_parse(cr, uid, 'reconciliation_widget_aml', context=context)
        ret = []

        for line in lines:
            partial_reconciliation_siblings_ids = []
            if line.reconcile_partial_id:
                partial_reconciliation_siblings_ids = self.search(cr, uid, [('reconcile_partial_id', '=', line.reconcile_partial_id.id)], context=context)
                partial_reconciliation_siblings_ids.remove(line.id)

            ret_line = {
                'id': line.id,
                'name': line.name != '/' and line.move_id.name + ': ' + line.name or line.move_id.name,
                'ref': line.move_id.ref or '',
                'account_code': line.account_id.code,
                'account_name': line.account_id.name,
                'account_type': line.account_id.type,
                'date_maturity': line.date_maturity,
                'date': line.date,
                'period_name': line.period_id.name,
                'journal_name': line.journal_id.name,
                'partner_id': line.partner_id.id,
                'partner_name': line.partner_id.name,
                'is_partially_reconciled': bool(line.reconcile_partial_id),
                'partial_reconciliation_siblings_ids': partial_reconciliation_siblings_ids,
            }

            # Amount residual can be negative
            debit = line.debit
            credit = line.credit
            amount = line.amount_residual
            amount_currency = line.amount_residual_currency
            if line.amount_residual < 0:
                debit, credit = credit, debit
                amount = -amount
                amount_currency = -amount_currency

            # Get right debit / credit:
            target_currency = target_currency or company_currency
            line_currency = line.currency_id or company_currency
            amount_currency_str = ""
            total_amount_currency_str = ""
            if line_currency != company_currency:
                total_amount = line.amount_currency
                actual_debit = debit > 0 and amount_currency or 0.0
                actual_credit = credit > 0 and amount_currency or 0.0
            else:
                total_amount = abs(debit - credit)
                actual_debit = debit > 0 and amount or 0.0
                actual_credit = credit > 0 and amount or 0.0
            if line_currency != target_currency:
                amount_currency_str = rml_parser.formatLang(actual_debit or actual_credit, currency_obj=line_currency)
                total_amount_currency_str = rml_parser.formatLang(total_amount, currency_obj=line_currency)
                ret_line['credit_currency'] = actual_credit
                ret_line['debit_currency'] = actual_debit
                if target_currency == company_currency:
                    actual_debit = debit
                    actual_credit = credit
                    total_amount = debit or credit
                else:
                    ctx = context.copy()
                    ctx.update({'date': line.date})
                    total_amount = currency_obj.compute(cr, uid, line_currency.id, target_currency.id, total_amount, context=ctx)
                    actual_debit = currency_obj.compute(cr, uid, line_currency.id, target_currency.id, actual_debit, context=ctx)
                    actual_credit = currency_obj.compute(cr, uid, line_currency.id, target_currency.id, actual_credit, context=ctx)
            amount_str = rml_parser.formatLang(actual_debit or actual_credit, currency_obj=target_currency)
            total_amount_str = rml_parser.formatLang(total_amount, currency_obj=target_currency)

            ret_line['debit'] = actual_debit
            ret_line['credit'] = actual_credit
            ret_line['amount_str'] = amount_str
            ret_line['total_amount_str'] = total_amount_str
            ret_line['amount_currency_str'] = amount_currency_str
            ret_line['total_amount_currency_str'] = total_amount_currency_str
            ret.append(ret_line)
        return ret


    def list_partners_to_reconcile(self, cr, uid, context=None, filter_domain=False):
        line_ids = []
        if filter_domain:
            line_ids = self.search(cr, uid, filter_domain, context=context)
        where_clause = filter_domain and "AND l.id = ANY(%s)" or ""
        cr.execute(
             """SELECT partner_id FROM (
                SELECT l.partner_id, p.last_reconciliation_date, SUM(l.debit) AS debit, SUM(l.credit) AS credit, MAX(l.create_date) AS max_date
                FROM account_move_line l
                RIGHT JOIN account_account a ON (a.id = l.account_id)
                RIGHT JOIN res_partner p ON (l.partner_id = p.id)
                    WHERE a.reconcile IS TRUE
                    AND l.reconcile_id IS NULL
                    AND l.state <> 'draft'
                    %s
                    GROUP BY l.partner_id, p.last_reconciliation_date
                ) AS s
                WHERE debit > 0 AND credit > 0 AND (last_reconciliation_date IS NULL OR max_date > last_reconciliation_date)
                ORDER BY last_reconciliation_date"""
            % where_clause, (line_ids,))
        ids = [x[0] for x in cr.fetchall()]
        if not ids:
            return []

        # To apply the ir_rules
        partner_obj = self.pool.get('res.partner')
        ids = partner_obj.search(cr, uid, [('id', 'in', ids)], context=context)
        return partner_obj.name_get(cr, uid, ids, context=context)

    def reconcile_partial(self, cr, uid, ids, type='auto', context=None, writeoff_acc_id=False, writeoff_period_id=False, writeoff_journal_id=False):
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
                raise osv.except_osv(_('Warning!'), _('To reconcile the entries company should be the same for all entries.'))
            company_list.append(line.company_id.id)

        for line in self.browse(cr, uid, ids, context=context):
            if line.account_id.currency_id:
                currency_id = line.account_id.currency_id
            else:
                currency_id = line.company_id.currency_id
            if line.reconcile_id:
                raise osv.except_osv(_('Warning'), _("Journal Item '%s' (id: %s), Move '%s' is already reconciled!") % (line.name, line.id, line.move_id.name))
            if line.reconcile_partial_id:
                for line2 in line.reconcile_partial_id.line_partial_ids:
                    if line2.state != 'valid':
                        raise osv.except_osv(_('Warning'), _("Journal Item '%s' (id: %s) cannot be used in a reconciliation as it is not balanced!") % (line2.name, line2.id))
                    if not line2.reconcile_id:
                        if line2.id not in merges:
                            merges.append(line2.id)
                        if line2.account_id.currency_id:
                            total += line2.amount_currency
                        else:
                            total += (line2.debit or 0.0) - (line2.credit or 0.0)
                merges_rec.append(line.reconcile_partial_id.id)
            else:
                unmerge.append(line.id)
                if line.account_id.currency_id:
                    total += line.amount_currency
                else:
                    total += (line.debit or 0.0) - (line.credit or 0.0)
        if self.pool.get('res.currency').is_zero(cr, uid, currency_id, total):
            res = self.reconcile(cr, uid, merges+unmerge, context=context, writeoff_acc_id=writeoff_acc_id, writeoff_period_id=writeoff_period_id, writeoff_journal_id=writeoff_journal_id)
            return res
        # marking the lines as reconciled does not change their validity, so there is no need
        # to revalidate their moves completely.
        reconcile_context = dict(context, novalidate=True)
        r_id = move_rec_obj.create(cr, uid, {
            'type': type,
            'line_partial_ids': map(lambda x: (4,x,False), merges+unmerge)
        }, context=reconcile_context)
        move_rec_obj.reconcile_partial_check(cr, uid, [r_id] + merges_rec, context=reconcile_context)
        return r_id

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
        for line in lines:
            if company_list and not line.company_id.id in company_list:
                raise osv.except_osv(_('Warning!'), _('To reconcile the entries company should be the same for all entries.'))
            company_list.append(line.company_id.id)
        for line in unrec_lines:
            if line.state <> 'valid':
                raise osv.except_osv(_('Error!'),
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
        if len(r) != 1:
            raise osv.except_osv(_('Error'), _('Entries are not of the same account or already reconciled ! '))
        if not unrec_lines:
            raise osv.except_osv(_('Error!'), _('Entry is already reconciled.'))
        account = account_obj.browse(cr, uid, account_id, context=context)
        if not account.reconcile:
            raise osv.except_osv(_('Error'), _('The account is not defined to be reconciled !'))
        if r[0][1] != None:
            raise osv.except_osv(_('Error!'), _('Some entries are already reconciled.'))

        if (not currency_obj.is_zero(cr, uid, account.company_id.currency_id, writeoff)) or \
           (account.currency_id and (not currency_obj.is_zero(cr, uid, account.currency_id, currency))):
            if not writeoff_acc_id:
                raise osv.except_osv(_('Warning!'), _('You have to provide an account for the write off/exchange difference entry.'))
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

        # marking the lines as reconciled does not change their validity, so there is no need
        # to revalidate their moves completely.
        reconcile_context = dict(context, novalidate=True)
        r_id = move_rec_obj.create(cr, uid, {
            'type': type,
            'line_id': map(lambda x: (4, x, False), ids),
            'line_partial_ids': map(lambda x: (3, x, False), ids)
        }, context=reconcile_context)
        # the id of the move.reconcile is written in the move.line (self) by the create method above
        # because of the way the line_id are defined: (4, x, False)
        for id in ids:
            workflow.trg_trigger(uid, 'account.move.line', id, cr)

        if lines and lines[0]:
            partner_id = lines[0].partner_id and lines[0].partner_id.id or False
            if partner_id and not partner_obj.has_something_to_reconcile(cr, uid, partner_id, context=context):
                partner_obj.mark_as_reconciled(cr, uid, [partner_id], context=context)
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
        if context.get('search_default_journal_id', False):
            context['journal_id'] = context.get('search_default_journal_id')
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
        pids = period_pool.find(cr, user, date, context=context)
        if pids:
            res.update({'period_id':pids[0]})
            context = dict(context, period_id=pids[0])
        return {
            'value':res,
            'context':context,
        }

    def _check_moves(self, cr, uid, context=None):
        # use the first move ever created for this journal and period
        if context is None:
            context = {}
        cr.execute('SELECT id, state, name FROM account_move WHERE journal_id = %s AND period_id = %s ORDER BY id limit 1', (context['journal_id'],context['period_id']))
        res = cr.fetchone()
        if res:
            if res[1] != 'draft':
                raise osv.except_osv(_('User Error!'),
                       _('The account move (%s) for centralisation ' \
                                'has been confirmed.') % res[2])
        return res

    def _remove_move_reconcile(self, cr, uid, move_ids=None, opening_reconciliation=False, context=None):
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
        all_moves = obj_move_line.search(cr, uid, ['|',('reconcile_id', 'in', unlink_ids),('reconcile_partial_id', 'in', unlink_ids)])
        all_moves = list(set(all_moves) - set(move_ids))
        if unlink_ids:
            if opening_reconciliation:
                raise osv.except_osv(_('Warning!'),
                    _('Opening Entries have already been generated.  Please run "Cancel Closing Entries" wizard to cancel those entries and then run this wizard.'))
                obj_move_rec.write(cr, uid, unlink_ids, {'opening_reconciliation': False})
            obj_move_rec.unlink(cr, uid, unlink_ids)
            if len(all_moves) >= 2:
                obj_move_line.reconcile_partial(cr, uid, all_moves, 'auto',context=context)
        return True

    def unlink(self, cr, uid, ids, context=None, check=True):
        if context is None:
            context = {}
        move_obj = self.pool.get('account.move')
        self._update_check(cr, uid, ids, context)
        result = False
        move_ids = set()
        for line in self.browse(cr, uid, ids, context=context):
            move_ids.add(line.move_id.id)
            localcontext = dict(context)
            localcontext['journal_id'] = line.journal_id.id
            localcontext['period_id'] = line.period_id.id
            result = super(account_move_line, self).unlink(cr, uid, [line.id], context=localcontext)
        move_ids = list(move_ids)
        if check and move_ids:
            move_obj.validate(cr, uid, move_ids, context=context)
        return result

    def write(self, cr, uid, ids, vals, context=None, check=True, update_check=True):
        if context is None:
            context={}
        move_obj = self.pool.get('account.move')
        account_obj = self.pool.get('account.account')
        journal_obj = self.pool.get('account.journal')
        if isinstance(ids, (int, long)):
            ids = [ids]
        if vals.get('account_tax_id', False):
            raise osv.except_osv(_('Unable to change tax!'), _('You cannot change the tax, you should remove and recreate lines.'))
        if ('account_id' in vals) and not account_obj.read(cr, uid, vals['account_id'], ['active'])['active']:
            raise osv.except_osv(_('Bad Account!'), _('You cannot use an inactive account.'))

        affects_move = any(f in vals for f in ('account_id', 'journal_id', 'period_id', 'move_id', 'debit', 'credit', 'date'))

        if update_check and affects_move:
            self._update_check(cr, uid, ids, context)

        todo_date = None
        if vals.get('date', False):
            todo_date = vals['date']
            del vals['date']

        for line in self.browse(cr, uid, ids, context=context):
            ctx = context.copy()
            if not ctx.get('journal_id'):
                if line.move_id:
                   ctx['journal_id'] = line.move_id.journal_id.id
                else:
                    ctx['journal_id'] = line.journal_id.id
            if not ctx.get('period_id'):
                if line.move_id:
                    ctx['period_id'] = line.move_id.period_id.id
                else:
                    ctx['period_id'] = line.period_id.id
            #Check for centralisation
            journal = journal_obj.browse(cr, uid, ctx['journal_id'], context=ctx)
            if journal.centralisation:
                self._check_moves(cr, uid, context=ctx)
        result = super(account_move_line, self).write(cr, uid, ids, vals, context)

        if affects_move and check and not context.get('novalidate'):
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
        journal = journal_obj.browse(cr, uid, journal_id, context=context)
        period = period_obj.browse(cr, uid, period_id, context=context)
        for (state,) in result:
            if state == 'done':
                raise osv.except_osv(_('Error!'), _('You can not add/modify entries in a closed period %s of journal %s.') % (period.name, journal.name))
        if not result:
            jour_period_obj.create(cr, uid, {
                'name': (journal.code or journal.name)+':'+(period.name or ''),
                'journal_id': journal.id,
                'period_id': period.id
            })
        return True

    def _update_check(self, cr, uid, ids, context=None):
        done = {}
        for line in self.browse(cr, uid, ids, context=context):
            err_msg = _('Move name (id): %s (%s)') % (line.move_id.name, str(line.move_id.id))
            if line.move_id.state <> 'draft' and (not line.journal_id.entry_posted):
                raise osv.except_osv(_('Error!'), _('You cannot do this modification on a confirmed entry. You can just change some non legal fields or you must unconfirm the journal entry first.\n%s.') % err_msg)
            if line.reconcile_id:
                raise osv.except_osv(_('Error!'), _('You cannot do this modification on a reconciled entry. You can just change some non legal fields or you must unreconcile first.\n%s.') % err_msg)
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
        context = dict(context or {})
        if vals.get('move_id', False):
            move = self.pool.get('account.move').browse(cr, uid, vals['move_id'], context=context)
            if move.company_id:
                vals['company_id'] = move.company_id.id
            if move.date and not vals.get('date'):
                vals['date'] = move.date
        if ('account_id' in vals) and not account_obj.read(cr, uid, [vals['account_id']], ['active'])[0]['active']:
            raise osv.except_osv(_('Bad Account!'), _('You cannot use an inactive account.'))
        if 'journal_id' in vals and vals['journal_id']:
            context['journal_id'] = vals['journal_id']
        if 'period_id' in vals and vals['period_id']:
            context['period_id'] = vals['period_id']
        if ('journal_id' not in context) and ('move_id' in vals) and vals['move_id']:
            m = move_obj.browse(cr, uid, vals['move_id'])
            context['journal_id'] = m.journal_id.id
            context['period_id'] = m.period_id.id
        #we need to treat the case where a value is given in the context for period_id as a string
        if 'period_id' in context and not isinstance(context.get('period_id', ''), (int, long)):
            period_candidate_ids = self.pool.get('account.period').name_search(cr, uid, name=context.get('period_id',''))
            if len(period_candidate_ids) != 1:
                raise osv.except_osv(_('Error!'), _('No period found or more than one period found for the given date.'))
            context['period_id'] = period_candidate_ids[0][0]
        if not context.get('journal_id', False) and context.get('search_default_journal_id', False):
            context['journal_id'] = context.get('search_default_journal_id')
        self._update_journal_check(cr, uid, context['journal_id'], context['period_id'], context)
        move_id = vals.get('move_id', False)
        journal = journal_obj.browse(cr, uid, context['journal_id'], context=context)
        vals['journal_id'] = vals.get('journal_id') or context.get('journal_id')
        vals['period_id'] = vals.get('period_id') or context.get('period_id')
        vals['date'] = vals.get('date') or context.get('date')
        if not move_id:
            if journal.centralisation:
                #Check for centralisation
                res = self._check_moves(cr, uid, context)
                if res:
                    vals['move_id'] = res[0]
            if not vals.get('move_id', False):
                if journal.sequence_id:
                    #name = self.pool.get('ir.sequence').next_by_id(cr, uid, journal.sequence_id.id)
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
                    raise osv.except_osv(_('No Piece Number!'), _('Cannot create an automatic sequence for this piece.\nPut a sequence in the journal definition for automatic numbering or create a sequence manually for this piece.'))
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
            raise osv.except_osv(_('Bad Account!'), _('You cannot use this general account in this journal, check the tab \'Entry Controls\' on the related journal.'))

        result = super(account_move_line, self).create(cr, uid, vals, context=context)
        # CREATE Taxes
        if vals.get('account_tax_id', False):
            tax_id = tax_obj.browse(cr, uid, vals['account_tax_id'])
            total = vals['debit'] - vals['credit']
            base_code = 'base_code_id'
            tax_code = 'tax_code_id'
            account_id = 'account_collected_id'
            base_sign = 'base_sign'
            tax_sign = 'tax_sign'
            if journal.type in ('purchase_refund', 'sale_refund') or (journal.type in ('cash', 'bank') and total < 0):
                base_code = 'ref_base_code_id'
                tax_code = 'ref_tax_code_id'
                account_id = 'account_paid_id'
                base_sign = 'ref_base_sign'
                tax_sign = 'ref_tax_sign'
            base_adjusted = False
            for tax in tax_obj.compute_all(cr, uid, [tax_id], total, 1.00, force_excluded=False).get('taxes'):
                #create the base movement
                if base_adjusted == False:
                    base_adjusted = True
                    if tax_id.price_include:
                        total = tax['price_unit']
                    newvals = {
                        'tax_code_id': tax[base_code],
                        'tax_amount': tax[base_sign] * abs(total),
                    }
                    if tax_id.price_include:
                        if tax['price_unit'] < 0:
                            newvals['credit'] = abs(tax['price_unit'])
                        else:
                            newvals['debit'] = tax['price_unit']
                    self.write(cr, uid, [result], newvals, context=context)
                else:
                    data = {
                        'move_id': vals['move_id'],
                        'name': tools.ustr(vals['name'] or '') + ' ' + tools.ustr(tax['name'] or ''),
                        'date': vals['date'],
                        'partner_id': vals.get('partner_id', False),
                        'ref': vals.get('ref', False),
                        'statement_id': vals.get('statement_id', False),
                        'account_tax_id': False,
                        'tax_code_id': tax[base_code],
                        'tax_amount': tax[base_sign] * abs(total),
                        'account_id': vals['account_id'],
                        'credit': 0.0,
                        'debit': 0.0,
                    }
                    self.create(cr, uid, data, context)
                #create the Tax movement
                if not tax['amount'] and not tax[tax_code]:
                    continue
                data = {
                    'move_id': vals['move_id'],
                    'name': tools.ustr(vals['name'] or '') + ' ' + tools.ustr(tax['name'] or ''),
                    'date': vals['date'],
                    'partner_id': vals.get('partner_id',False),
                    'ref': vals.get('ref',False),
                    'statement_id': vals.get('statement_id', False),
                    'account_tax_id': False,
                    'tax_code_id': tax[tax_code],
                    'tax_amount': tax[tax_sign] * abs(tax['amount']),
                    'account_id': tax[account_id] or vals['account_id'],
                    'credit': tax['amount']<0 and -tax['amount'] or 0.0,
                    'debit': tax['amount']>0 and tax['amount'] or 0.0,
                }
                self.create(cr, uid, data, context)
            del vals['account_tax_id']

        recompute = journal.env.recompute and context.get('recompute', True)
        if check and not context.get('novalidate') and (recompute or journal.entry_posted):
            tmp = move_obj.validate(cr, uid, [vals['move_id']], context)
            if journal.entry_posted and tmp:
                move_obj.button_validate(cr,uid, [vals['move_id']], context)
        return result

    def list_periods(self, cr, uid, context=None):
        ids = self.pool.get('account.period').search(cr,uid,[])
        return self.pool.get('account.period').name_get(cr, uid, ids, context=context)

    def list_journals(self, cr, uid, context=None):
        ng = dict(self.pool.get('account.journal').name_search(cr,uid,'',[]))
        ids = ng.keys()
        result = []
        for journal in self.pool.get('account.journal').browse(cr, uid, ids, context=context):
            result.append((journal.id,ng[journal.id],journal.type,
                bool(journal.currency),bool(journal.analytic_journal_id)))
        return result


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
