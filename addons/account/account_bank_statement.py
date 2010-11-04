# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import time
import netsvc
from osv import fields, osv

from tools.misc import currency
from tools.translate import _

import mx.DateTime
from mx.DateTime import RelativeDateTime, now, DateTime, localtime


class account_bank_statement(osv.osv):
    def _default_journal_id(self, cr, uid, context={}):
        if context.get('journal_id', False):
            return context['journal_id']
        return False

    def _default_balance_start(self, cr, uid, context={}):
        cr.execute('select id from account_bank_statement where journal_id=%s order by date desc limit 1', (1,))
        res = cr.fetchone()
        if res:
            return self.browse(cr, uid, [res[0]], context)[0].balance_end
        return 0.0

    def _end_balance(self, cursor, user, ids, name, attr, context=None):
        res_currency_obj = self.pool.get('res.currency')
        res_users_obj = self.pool.get('res.users')

        res = {}

        company_currency_id = res_users_obj.browse(cursor, user, user,
                context=context).company_id.currency_id.id

        statements = self.browse(cursor, user, ids, context=context)
        for statement in statements:
            res[statement.id] = statement.balance_start
            currency_id = statement.currency.id
            for line in statement.move_line_ids:
                if line.debit > 0:
                    if line.account_id.id == \
                            statement.journal_id.default_debit_account_id.id:
                        res[statement.id] += res_currency_obj.compute(cursor,
                                user, company_currency_id, currency_id,
                                line.debit, context=context)
                else:
                    if line.account_id.id == \
                            statement.journal_id.default_credit_account_id.id:
                        res[statement.id] -= res_currency_obj.compute(cursor,
                                user, company_currency_id, currency_id,
                                line.credit, context=context)
            if statement.state == 'draft':
                for line in statement.line_ids:
                    res[statement.id] += line.amount
        for r in res:
            res[r] = round(res[r], 2)
        return res

    def _get_period(self, cr, uid, context={}):
        periods = self.pool.get('account.period').find(cr, uid)
        if periods:
            return periods[0]
        else:
            return False

    def _currency(self, cursor, user, ids, name, args, context=None):
        res = {}
        res_currency_obj = self.pool.get('res.currency')
        res_users_obj = self.pool.get('res.users')
        default_currency = res_users_obj.browse(cursor, user,
                user, context=context).company_id.currency_id
        for statement in self.browse(cursor, user, ids, context=context):
            currency = statement.journal_id.currency
            if not currency:
                currency = default_currency
            res[statement.id] = currency.id
        currency_names = {}
        for currency_id, currency_name in res_currency_obj.name_get(cursor,
                user, [x for x in res.values()], context=context):
            currency_names[currency_id] = currency_name
        for statement_id in res.keys():
            currency_id = res[statement_id]
            res[statement_id] = (currency_id, currency_names[currency_id])
        return res

    _order = "date desc"
    _name = "account.bank.statement"
    _description = "Bank Statement"
    _columns = {
        'name': fields.char('Name', size=64, required=True, states={'confirm': [('readonly', True)]}),
        'date': fields.date('Date', required=True,
            states={'confirm': [('readonly', True)]}),
        'journal_id': fields.many2one('account.journal', 'Journal', required=True,
            states={'confirm': [('readonly', True)]}, domain=[('type', '=', 'cash')]),
        'period_id': fields.many2one('account.period', 'Period', required=True,
            states={'confirm':[('readonly', True)]}),
        'balance_start': fields.float('Starting Balance', digits=(16,2),
            states={'confirm':[('readonly',True)]}),
        'balance_end_real': fields.float('Ending Balance', digits=(16,2),
            states={'confirm':[('readonly', True)]}),
        'balance_end': fields.function(_end_balance, method=True, string='Balance'),
        'line_ids': fields.one2many('account.bank.statement.line',
            'statement_id', 'Statement lines',
            states={'confirm':[('readonly', True)]}),
        'move_line_ids': fields.one2many('account.move.line', 'statement_id',
            'Entry lines', states={'confirm':[('readonly',True)]}),
        'state': fields.selection([('draft', 'Draft'),('confirm', 'Confirm')],
            'State', required=True,
            states={'confirm': [('readonly', True)]}, readonly="1"),
        'currency': fields.function(_currency, method=True, string='Currency',
            type='many2one', relation='res.currency'),
    }

    _defaults = {
        'name': lambda self, cr, uid, context=None: \
                self.pool.get('ir.sequence').get(cr, uid, 'account.bank.statement'),
        'date': lambda *a: time.strftime('%Y-%m-%d'),
        'state': lambda *a: 'draft',
        'balance_start': _default_balance_start,
        'journal_id': _default_journal_id,
        'period_id': _get_period,
    }

    def button_confirm(self, cr, uid, ids, context={}):
        done = []
        res_currency_obj = self.pool.get('res.currency')
        res_users_obj = self.pool.get('res.users')
        account_move_obj = self.pool.get('account.move')
        account_move_line_obj = self.pool.get('account.move.line')
        account_bank_statement_line_obj = \
                self.pool.get('account.bank.statement.line')

        company_currency_id = res_users_obj.browse(cr, uid, uid,
                context=context).company_id.currency_id.id

        for st in self.browse(cr, uid, ids, context):
            if not st.state=='draft':
                continue

            if not (abs(st.balance_end - st.balance_end_real) < 0.0001):
                raise osv.except_osv(_('Error !'),
                        _('The statement balance is incorrect !\n') +
                        _('The expected balance (%.2f) is different than the computed one. (%.2f)') % (st.balance_end_real, st.balance_end))
            if (not st.journal_id.default_credit_account_id) \
                    or (not st.journal_id.default_debit_account_id):
                raise osv.except_osv(_('Configuration Error !'),
                        _('Please verify that an account is defined in the journal.'))

            for line in st.move_line_ids:
                if line.state <> 'valid':
                    raise osv.except_osv(_('Error !'),
                            _('The account entries lines are not in valid state.'))
            # for bank.statement.lines
            # In line we get reconcile_id on bank.ste.rec.
            # in bank stat.rec we get line_new_ids on bank.stat.rec.line
            for move in st.line_ids:
                context.update({'date':move.date})
                move_id = account_move_obj.create(cr, uid, {
                    'journal_id': st.journal_id.id,
                    'period_id': st.period_id.id,
                    'date': move.date,
                }, context=context)
                account_bank_statement_line_obj.write(cr, uid, [move.id], {
                    'move_ids': [(4,move_id, False)]
                })
                if not move.amount:
                    continue

                torec = []
                if move.amount >= 0:
                    account_id = st.journal_id.default_credit_account_id.id
                else:
                    account_id = st.journal_id.default_debit_account_id.id
                acc_cur = ((move.amount<=0) and st.journal_id.default_debit_account_id) or move.account_id
                amount = res_currency_obj.compute(cr, uid, st.currency.id,
                        company_currency_id, move.amount, context=context,
                        account=acc_cur)
                if move.reconcile_id and move.reconcile_id.line_new_ids:
                    for newline in move.reconcile_id.line_new_ids:
                        amount += newline.amount

                val = {
                    'name': move.name,
                    'date': move.date,
                    'ref': move.ref,
                    'move_id': move_id,
                    'partner_id': ((move.partner_id) and move.partner_id.id) or False,
                    'account_id': (move.account_id) and move.account_id.id,
                    'credit': ((amount>0) and amount) or 0.0,
                    'debit': ((amount<0) and -amount) or 0.0,
                    'statement_id': st.id,
                    'journal_id': st.journal_id.id,
                    'period_id': st.period_id.id,
                    'currency_id': st.currency.id,
                }
                
                amount = res_currency_obj.compute(cr, uid, st.currency.id,
                        company_currency_id, move.amount, context=context,
                        account=acc_cur)
                if st.currency.id <> company_currency_id:
                    amount_cur = res_currency_obj.compute(cr, uid, company_currency_id,
                                st.currency.id, amount, context=context,
                                account=acc_cur)
                    val['amount_currency'] = -amount_cur

                if move.account_id and move.account_id.currency_id and move.account_id.currency_id.id <> company_currency_id:
                    val['currency_id'] = move.account_id.currency_id.id
                    amount_cur = res_currency_obj.compute(cr, uid, company_currency_id,
                            move.account_id.currency_id.id, amount, context=context,
                            account=acc_cur)
                    val['amount_currency'] = -amount_cur

                torec.append(account_move_line_obj.create(cr, uid, val , context=context))

                if move.reconcile_id and move.reconcile_id.line_new_ids:
                    for newline in move.reconcile_id.line_new_ids:
                        account_move_line_obj.create(cr, uid, {
                            'name': newline.name or move.name,
                            'date': move.date,
                            'ref': move.ref,
                            'move_id': move_id,
                            'partner_id': ((move.partner_id) and move.partner_id.id) or False,
                            'account_id': (newline.account_id) and newline.account_id.id,
                            'debit': newline.amount>0 and newline.amount or 0.0,
                            'credit': newline.amount<0 and -newline.amount or 0.0,
                            'statement_id': st.id,
                            'journal_id': st.journal_id.id,
                            'period_id': st.period_id.id,

                        }, context=context)

                # Fill the secondary amount/currency
                # if currency is not the same than the company
                amount_currency = False
                currency_id = False
                if st.currency.id <> company_currency_id:
                    amount_currency = move.amount
                    currency_id = st.currency.id
                account_move_line_obj.create(cr, uid, {
                    'name': move.name,
                    'date': move.date,
                    'ref': move.ref,
                    'move_id': move_id,
                    'partner_id': ((move.partner_id) and move.partner_id.id) or False,
                    'account_id': account_id,
                    'credit': ((amount < 0) and -amount) or 0.0,
                    'debit': ((amount > 0) and amount) or 0.0,
                    'statement_id': st.id,
                    'journal_id': st.journal_id.id,
                    'period_id': st.period_id.id,
                    'amount_currency': amount_currency,
                    'currency_id': currency_id,
                    }, context=context)

                for line in account_move_line_obj.browse(cr, uid, [x.id for x in
                        account_move_obj.browse(cr, uid, move_id,
                            context=context).line_id],
                        context=context):
                    if line.state <> 'valid':
                        raise osv.except_osv(_('Error !'),
                                _('Account move line "%s" is not valid') % line.name)

                if move.reconcile_id and move.reconcile_id.line_ids:
                    ## Search if move has already a partial reconciliation
                    previous_partial = False
                    for line_reconcile_move in move.reconcile_id.line_ids:
                        if line_reconcile_move.reconcile_partial_id:
                            previous_partial = True
                            break
                    ##
                    torec += map(lambda x: x.id, move.reconcile_id.line_ids)
                    #try:
                    if abs(move.reconcile_amount-move.amount)<0.0001:

                        writeoff_acc_id = False
                        #There should only be one write-off account!
                        for entry in move.reconcile_id.line_new_ids:
                            writeoff_acc_id = entry.account_id.id
                            break
                        ## If we have already a partial reconciliation
                        ## We need to make a partial reconciliation
                        ## To add this amount to previous paid amount
                        if previous_partial:
                            account_move_line_obj.reconcile_partial(cr, uid, torec, 'statement', context)
                        ## If it's the first reconciliation, we do a full reconciliation as regular
                        else:
                            account_move_line_obj.reconcile(cr, uid, torec, 'statement', writeoff_acc_id=writeoff_acc_id, writeoff_period_id=st.period_id.id, writeoff_journal_id=st.journal_id.id, context=context)

                    else:
                        account_move_line_obj.reconcile_partial(cr, uid, torec, 'statement', context)
                    #except:
                    #    raise osv.except_osv(_('Error !'), _('Unable to reconcile entry "%s": %.2f') % (move.name, move.amount))

                if st.journal_id.entry_posted:
                    account_move_obj.write(cr, uid, [move_id], {'state':'posted'})
            done.append(st.id)
        self.write(cr, uid, done, {'state':'confirm'}, context=context)
        return True

    def button_cancel(self, cr, uid, ids, context={}):
        done = []
        for st in self.browse(cr, uid, ids, context):
            if st.state=='draft':
                continue
            ids = []
            for line in st.line_ids:
                ids += [x.id for x in line.move_ids]
            self.pool.get('account.move').unlink(cr, uid, ids, context)
            done.append(st.id)
        self.write(cr, uid, done, {'state':'draft'}, context=context)
        return True

    def onchange_journal_id(self, cursor, user, statement_id, journal_id, context=None):
        if not journal_id:
            return {'value': {'currency': False}}

        account_journal_obj = self.pool.get('account.journal')
        res_users_obj = self.pool.get('res.users')
        res_currency_obj = self.pool.get('res.currency')

        cursor.execute('SELECT balance_end_real \
                FROM account_bank_statement \
                WHERE journal_id = %s \
                ORDER BY date DESC,id DESC LIMIT 1', (journal_id,))
        res = cursor.fetchone()
        balance_start = res and res[0] or 0.0

        currency_id = account_journal_obj.browse(cursor, user, journal_id,
                context=context).currency.id
        if not currency_id:
            currency_id = res_users_obj.browse(cursor, user, user,
                    context=context).company_id.currency_id.id
        currency = res_currency_obj.name_get(cursor, user, [currency_id],
                context=context)[0]
        return {'value': {'balance_start': balance_start, 'currency': currency}}

    def unlink(self, cr, uid, ids, context=None):
        stat = self.read(cr, uid, ids, ['state'])
        unlink_ids = []
        for t in stat:
            if t['state'] in ('draft'):
                unlink_ids.append(t['id'])
            else:
                raise osv.except_osv(_('Invalid action !'), _('Cannot delete bank statement which are already confirmed !'))
        osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
        return True
    
    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        if context is None:
            context = {}    
        default = default.copy()
        default['move_line_ids'] = []
        return super(account_bank_statement, self).copy(cr, uid, id, default, context)
    
account_bank_statement()


class account_bank_statement_reconcile(osv.osv):
    _name = "account.bank.statement.reconcile"
    _description = "Statement reconcile"

    def _total_entry(self, cursor, user, ids, name, attr, context=None):
        result = {}
        for o in self.browse(cursor, user, ids, context=context):
            result[o.id] = 0.0
            for line in o.line_ids:
                result[o.id] += line.debit - line.credit
        return result

    def _total_new(self, cursor, user, ids, name, attr, context=None):
        result = {}
        for o in self.browse(cursor, user, ids, context=context):
            result[o.id] = 0.0
            for line in o.line_new_ids:
                result[o.id] += line.amount
        return result

    def _total_balance(self, cursor, user, ids, name, attr, context=None):
        result = {}
        for o in self.browse(cursor, user, ids, context=context):
            result[o.id] = o.total_new - o.total_entry + o.total_amount
        return result

    def _total_amount(self, cursor, user, ids, name, attr, context=None):
        res = {}
        res_currency_obj = self.pool.get('res.currency')
        res_users_obj = self.pool.get('res.users')

        company_currency_id = res_users_obj.browse(cursor, user, user,
                context=context).company_id.currency_id.id
        currency_id = context.get('currency_id', company_currency_id)

        acc_cur = None
        if context.get('journal_id', False) and context.get('account_id',False):
            st =self.pool.get('account.journal').browse(cursor, user, context['journal_id'])
            acc = self.pool.get('account.account').browse(cursor, user, context['account_id'])
            acc_cur = (( context.get('amount',0.0)<=0) and st.default_debit_account_id) or acc

        for reconcile_id in ids:
            res[reconcile_id] = res_currency_obj.compute(cursor, user,
                    currency_id, company_currency_id,
                    context.get('amount', 0.0), context=context, account=acc_cur)
        return res

    def _default_amount(self, cursor, user, context=None):
        if context is None:
            context = {}
        res_currency_obj = self.pool.get('res.currency')
        res_users_obj = self.pool.get('res.users')

        company_currency_id = res_users_obj.browse(cursor, user, user,
                context=context).company_id.currency_id.id
        currency_id = context.get('currency_id', company_currency_id)

        acc_cur = None
        if context.get('journal_id', False) and context.get('account_id',False):
            st =self.pool.get('account.journal').browse(cursor, user, context['journal_id'])
            acc = self.pool.get('account.account').browse(cursor, user, context['account_id'])
            acc_cur = (( context.get('amount',0.0)<=0) and st.default_debit_account_id) or acc

        return res_currency_obj.compute(cursor, user,
                currency_id, company_currency_id,
                context.get('amount', 0.0), context=context, account=acc_cur)

    def _total_currency(self, cursor, user, ids, name, attrs, context=None):
        res = {}
        res_users_obj = self.pool.get('res.users')

        company_currency_id = res_users_obj.browse(cursor, user, user,
                context=context).company_id.currency_id.id

        for reconcile_id in ids:
            res[reconcile_id] = company_currency_id
        return res

    def _default_currency(self, cursor, user, context=None):
        res_users_obj = self.pool.get('res.users')

        return res_users_obj.browse(cursor, user, user,
                context=context).company_id.currency_id.id


    def _total_second_amount(self, cursor, user, ids, name, attr,
            context=None):
        res = {}
        for reconcile_id in ids:
            res[reconcile_id] = context.get('amount', 0.0)
        return res

    def _total_second_currency(self, cursor, user, ids, name, attr, context=None):
        res = {}
        for reconcile_id in ids:
            res[reconcile_id] = context.get('currency_id', False)
        return res

    def name_get(self, cursor, user, ids, context=None):
        res= []
        for o in self.browse(cursor, user, ids, context=context):
            result = 0.0
            res_currency = ''
            for line in o.line_ids:
                if line.amount_currency and line.currency_id:
                    result += line.amount_currency
                    res_currency = line.currency_id.code
                else:
                    result += line.debit - line.credit
            if res_currency:
                res_currency = ' ' + res_currency
            res.append((o.id, '[%.2f'% (result - o.total_new,) + res_currency + ']' ))
        return res

    _columns = {
        'name': fields.char('Date', size=64, required=True),
        'partner_id': fields.many2one('res.partner', 'Partner', readonly=True),
        'line_new_ids': fields.one2many('account.bank.statement.reconcile.line',
            'line_id', 'Write-Off'),
        'total_entry': fields.function(_total_entry, method=True,
            string='Total entries'),
        'total_new': fields.function(_total_new, method=True,
            string='Total write-off'),
        'total_second_amount': fields.function(_total_second_amount,
            method=True, string='Payment amount',
            help='The amount in the currency of the journal'),
        'total_second_currency': fields.function(_total_second_currency, method=True,
            string='Currency', type='many2one', relation='res.currency',
            help='The currency of the journal'),
        'total_amount': fields.function(_total_amount, method=True,
            string='Payment amount'),
        'total_currency': fields.function(_total_currency, method=True,
            string='Currency', type='many2one', relation='res.currency'),
        'total_balance': fields.function(_total_balance, method=True,
            string='Balance'),
        #line_ids define in account.py
        'statement_line': fields.one2many('account.bank.statement.line',
             'reconcile_id', 'Bank Statement Line'),
    }
    _defaults = {
        'name': lambda *a: time.strftime('%Y-%m-%d'),
        'partner_id': lambda obj, cursor, user, context=None: \
                context.get('partner', False),
        'total_amount': _default_amount,
        'total_currency': _default_currency,
        'total_second_amount':  lambda obj, cursor, user, context=None: \
                context.get('amount', 0.0),
        'total_second_currency': lambda obj, cursor, user, context=None: \
                context.get('currency_id', False),
        'total_balance': _default_amount,
    }
account_bank_statement_reconcile()

class account_bank_statement_reconcile_line(osv.osv):
    _name = "account.bank.statement.reconcile.line"
    _description = "Statement reconcile line"
    _columns = {
        'name': fields.char('Description', size=64, required=True),
        'account_id': fields.many2one('account.account', 'Account', required=True),
        'line_id': fields.many2one('account.bank.statement.reconcile', 'Reconcile'),
        'amount': fields.float('Amount', required=True),
    }
    _defaults = {
        'name': lambda *a: 'Write-Off',
    }
account_bank_statement_reconcile_line()


class account_bank_statement_line(osv.osv):

    def onchange_partner_id(self, cursor, user, line_id, partner_id, type, currency_id,
            context={}):
        res = {'value': {}}
        if not partner_id:
            return res
        line = self.browse(cursor, user, line_id)
  
        if not line or (line and not line[0].account_id):
            part = self.pool.get('res.partner').browse(cursor, user, partner_id,
                context=context)
            if type == 'supplier':
                account_id = part.property_account_payable.id
            else:
                account_id =  part.property_account_receivable.id
            res['value']['account_id'] = account_id

        if not line or (line and not line[0].amount):
            res_users_obj = self.pool.get('res.users')
            res_currency_obj = self.pool.get('res.currency')
            company_currency_id = res_users_obj.browse(cursor, user, user,
                    context=context).company_id.currency_id.id
            if not currency_id:
                currency_id = company_currency_id

            cursor.execute('SELECT sum(debit-credit) \
                FROM account_move_line \
                WHERE (reconcile_id is null) \
                    AND partner_id = %s \
                    AND account_id=%s', (partner_id, account_id))
            pgres = cursor.fetchone()
            balance = pgres and pgres[0] or 0.0

            balance = res_currency_obj.compute(cursor, user, company_currency_id,
                currency_id, balance, context=context)
            res['value']['amount'] = balance
        return res

    def _reconcile_amount(self, cursor, user, ids, name, args, context=None):
        if not ids:
            return {}
        res_currency_obj = self.pool.get('res.currency')
        res_users_obj = self.pool.get('res.users')

        res = {}
        company_currency_id = res_users_obj.browse(cursor, user, user,
                context=context).company_id.currency_id.id

        for line in self.browse(cursor, user, ids, context=context):
            if line.reconcile_id:
                res[line.id] = res_currency_obj.compute(cursor, user,
                        company_currency_id, line.statement_id.currency.id,
                        line.reconcile_id.total_entry, context=context)
            else:
                res[line.id] = 0.0
        return res

    _order = "date,name desc"
    _name = "account.bank.statement.line"
    _description = "Bank Statement Line"
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'date': fields.date('Date', required=True),
        'amount': fields.float('Amount'),
        'type': fields.selection([
            ('supplier','Supplier'),
            ('customer','Customer'),
            ('general','General')
            ], 'Type', required=True),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'account_id': fields.many2one('account.account','Account',
            required=True),
        'statement_id': fields.many2one('account.bank.statement', 'Statement',
            select=True, required=True, ondelete='cascade'),
        'reconcile_id': fields.many2one('account.bank.statement.reconcile',
            'Reconcile', states={'confirm':[('readonly',True)]}),
        'move_ids': fields.many2many('account.move',
            'account_bank_statement_line_move_rel', 'move_id','statement_id',
            'Moves'),
        'ref': fields.char('Ref.', size=32),
        'note': fields.text('Notes'),
        'reconcile_amount': fields.function(_reconcile_amount,
            string='Amount reconciled', method=True, type='float'),
    }
    _defaults = {
        'name': lambda self,cr,uid,context={}: self.pool.get('ir.sequence').get(cr, uid, 'account.bank.statement.line'),
        'date': lambda *a: time.strftime('%Y-%m-%d'),
        'type': lambda *a: 'general',
    }

account_bank_statement_line()



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

