# encoding: utf-8
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2008 PC Solutions (<http://pcsol.be>). All Rights Reserved
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

from osv import osv, fields
import time
from mx import DateTime
from decimal import Decimal
from tools.translate import _
import decimal_precision as dp

class account_cashbox_line(osv.osv):

    """ Cash Box Details """

    _name = 'account.cashbox.line'
    _description = 'CashBox Line'

    def _sub_total(self, cr, uid, ids, name, arg, context=None):

        """ Calculates Sub total
        @param name: Names of fields.
        @param arg: User defined arguments
        @return: Dictionary of values.
        """
        res = {}
        for obj in self.browse(cr, uid, ids):
            res[obj.id] = obj.pieces * obj.number
        return res

    def on_change_sub(self, cr, uid, ids, pieces, number,*a):

        """ Calculates Sub total on change of number
        @param pieces: Names of fields.
        @param number:
        """
        sub=pieces*number
        return {'value':{'subtotal': sub or 0.0}}

    _columns = {
        'pieces': fields.float('Values', digits_compute=dp.get_precision('Account')),
        'number': fields.integer('Number'),
        'subtotal': fields.function(_sub_total, method=True, string='Sub Total', type='float', digits_compute=dp.get_precision('Account')),
        'starting_id': fields.many2one('account.bank.statement',ondelete='cascade'),
        'ending_id': fields.many2one('account.bank.statement',ondelete='cascade'),
     }
account_cashbox_line()

class account_cash_statement(osv.osv):

    _inherit = 'account.bank.statement'

    def _get_starting_balance(self, cr, uid, ids, context=None):

        """ Find starting balance
        @param name: Names of fields.
        @param arg: User defined arguments
        @return: Dictionary of values.
        """
        res ={}
        for statement in self.browse(cr, uid, ids):
            amount_total = 0.0

            if statement.journal_id.type not in('cash'):
                continue

            for line in statement.starting_details_ids:
                amount_total+= line.pieces * line.number
            res[statement.id] = {
                'balance_start':amount_total
            }
        return res

    def _balance_end_cash(self, cr, uid, ids, name, arg, context=None):
        """ Find ending balance  "
        @param name: Names of fields.
        @param arg: User defined arguments
        @return: Dictionary of values.
        """
        res ={}
        for statement in self.browse(cr, uid, ids):
            amount_total=0.0
            for line in statement.ending_details_ids:
                amount_total+= line.pieces * line.number
            res[statement.id]=amount_total
        return res

    def _get_sum_entry_encoding(self, cr, uid, ids, name, arg, context=None):

        """ Find encoding total of statements "
        @param name: Names of fields.
        @param arg: User defined arguments
        @return: Dictionary of values.
        """
        res2={}
        for statement in self.browse(cr, uid, ids):
            encoding_total=0.0
            for line in statement.line_ids:
               encoding_total+= line.amount
            res2[statement.id]=encoding_total
        return res2

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
            if statement.state in ('draft', 'open'):
                for line in statement.line_ids:
                    res[statement.id] += line.amount
        for r in res:
            res[r] = round(res[r], 2)
        return res

    def _get_company(self, cr, uid, context={}):
        user_pool = self.pool.get('res.users')
        company_pool = self.pool.get('res.company')
        user = user_pool.browse(cr, uid, uid, context)
        company_id = user.company_id and user.company_id.id
        if not company_id:
            company_id = company_pool.search(cr, uid, [])[0]

        return company_id

    def _get_cash_open_box_lines(self, cr, uid, context={}):
        res = []
        curr = [1, 2, 5, 10, 20, 50, 100, 500]
        for rs in curr:
            dct = {
                'pieces':rs,
                'number':0
            }
            res.append(dct)
        journal_ids = self.pool.get('account.journal').search(cr, uid, [('type','=','cash')], context=context)
        if journal_ids:
            results = self.search(cr, uid, [('journal_id','in',journal_ids),('state','=','confirm')],context=context)
            if results:
                cash_st = self.browse(cr, uid, results, context)[0]
                for cash_line in cash_st.ending_details_ids:
                    for r in res:
                        if cash_line.pieces == r['pieces']:
                            r['number'] = cash_line.number
        return res

    def _get_default_cash_close_box_lines(self, cr, uid, context={}):
        res = []
        curr = [1, 2, 5, 10, 20, 50, 100, 500]
        for rs in curr:
            dct = {
                'pieces':rs,
                'number':0
            }
            res.append(dct)
        return res

    def _get_cash_close_box_lines(self, cr, ids, uid, context={}):
        res = []
        curr = [1, 2, 5, 10, 20, 50, 100, 500]
        for rs in curr:
            dct = {
                'pieces':rs,
                'number':0
            }
            res.append((0,0,dct))
        return res

    _columns = {
        'journal_id': fields.many2one('account.journal', 'Journal', required=True, states={'draft': [('readonly', False)]}, readonly=True, domain=[('type', '=', 'cash')]),
        'balance_end_real': fields.float('Closing Balance', digits_compute=dp.get_precision('Account'), states={'confirm':[('readonly', True)]}, help="closing balance entered by the cashbox verifier"),
        'state': fields.selection(
            [('draft', 'Draft'),
            ('confirm', 'Closed'),
            ('open','Open')], 'State', required=True, states={'confirm': [('readonly', True)]}, readonly="1"),
        'total_entry_encoding':fields.function(_get_sum_entry_encoding, method=True, store=True, string="Cash Transaction", help="Total cash transactions"),
        'closing_date':fields.datetime("Closed On"),
        'balance_end': fields.function(_end_balance, method=True, store=True, string='Balance', help="Closing balance based on Starting Balance and Cash Transactions"),
        'balance_end_cash': fields.function(_balance_end_cash, method=True, store=True, string='Balance', help="Closing balance based on cashBox"),
        'starting_details_ids': fields.one2many('account.cashbox.line', 'starting_id', string='Opening Cashbox'),
        'ending_details_ids': fields.one2many('account.cashbox.line', 'ending_id', string='Closing Cashbox'),
        'name': fields.char('Name', size=64, required=True, states={'draft': [('readonly', False)]}, readonly=True, help='if you give the Name other then / , its created Accounting Entries Move will be with same name as statement name. This allows the statement entries to have the same references than the statement itself'),
        'user_id':fields.many2one('res.users', 'Responsible', required=False),
    }
    _defaults = {
        'state': lambda *a: 'draft',
        'date': lambda *a:time.strftime("%Y-%m-%d %H:%M:%S"),
        'user_id': lambda self, cr, uid, context=None: uid,
        'starting_details_ids':_get_cash_open_box_lines,
        'ending_details_ids':_get_default_cash_close_box_lines
     }

    def create(self, cr, uid, vals, context=None):
        sql = [
                ('journal_id', '=', vals['journal_id']),
                ('state', '=', 'open')
        ]
        open_jrnl = self.search(cr, uid, sql)
        if open_jrnl:
            raise osv.except_osv('Error', _('You can not have two open register for the same journal'))

        if self.pool.get('account.journal').browse(cr, uid, vals['journal_id']).type == 'cash':
            lines = end_lines = self._get_cash_close_box_lines(cr, uid, [], context)
            vals.update({
                'ending_details_ids':lines
            })
        else:
            vals.update({
                'ending_details_ids':False,
                'starting_details_ids':False
            })
        res_id = super(account_cash_statement, self).create(cr, uid, vals, context=context)
        #self.write(cr, uid, [res_id], {})
        return res_id

    def write(self, cr, uid, ids, vals, context=None):
        """
        Update redord(s) comes in {ids}, with new value comes as {vals}
        return True on success, False otherwise

        @param cr: cursor to database
        @param user: id of current user
        @param ids: list of record ids to be update
        @param vals: dict of new values to be set
        @param context: context arguments, like lang, time zone

        @return: True on success, False otherwise
        """

        super(account_cash_statement, self).write(cr, uid, ids, vals)
        res = self._get_starting_balance(cr, uid, ids)
        for rs in res:
            super(account_cash_statement, self).write(cr, uid, rs, res.get(rs))
        return True

    def onchange_journal_id(self, cr, uid, statement_id, journal_id, context={}):
        """ Changes balance start and starting details if journal_id changes"
        @param statement_id: Changed statement_id
        @param journal_id: Changed journal_id
        @return:  Dictionary of changed values
        """

        cash_pool = self.pool.get('account.cashbox.line')
        statement_pool = self.pool.get('account.bank.statement')

        res = {}
        balance_start = 0.0

        if not journal_id:
            res.update({
                'balance_start': balance_start
            })
            return res
        res = super(account_cash_statement, self).onchange_journal_id(cr, uid, statement_id, journal_id, context)
        return res

    def _equal_balance(self, cr, uid, ids, statement, context={}):
        if statement.balance_end != statement.balance_end_cash:
            return False
        else:
            return True

    def _user_allow(self, cr, uid, ids, statement, context={}):
        return True

    def button_open(self, cr, uid, ids, context=None):

        """ Changes statement state to Running.
        @return: True
        """
        cash_pool = self.pool.get('account.cashbox.line')
        statement_pool = self.pool.get('account.bank.statement')

        statement = statement_pool.browse(cr, uid, ids[0])
        vals = {}

        if not self._user_allow(cr, uid, ids, statement, context={}):
            raise osv.except_osv(_('Error !'), _('User %s does not have rights to access %s journal !' % (statement.user_id.name, statement.journal_id.name)))

        if statement.name and statement.name == '/':
            number = self.pool.get('ir.sequence').get(cr, uid, 'account.cash.statement')
            vals.update({
                'name': number
            })

#        cr.execute("select id from account_bank_statement where journal_id=%s and user_id=%s and state=%s order by id desc limit 1", (statement.journal_id.id, uid, 'confirm'))
#        rs = cr.fetchone()
#        rs = rs and rs[0] or None
#        if rs:
#            if len(statement.starting_details_ids) > 0:
#                sid = []
#                for line in statement.starting_details_ids:
#                    sid.append(line.id)
#                cash_pool.unlink(cr, uid, sid)
#
#            statement = statement_pool.browse(cr, uid, rs)
#            balance_start = statement.balance_end_real or 0.0
#            open_ids = cash_pool.search(cr, uid, [('ending_id','=',statement.id)])
#            for sid in open_ids:
#                default = {
#                    'ending_id': False,
#                    'starting_id':ids[0]
#                }
#                cash_pool.copy(cr, uid, sid, default)

        vals.update({
            'date':time.strftime("%Y-%m-%d %H:%M:%S"),
            'state':'open',

        })

        self.write(cr, uid, ids, vals)
        return True

    def button_confirm_cash(self, cr, uid, ids, context={}):

        """ Check the starting and ending detail of  statement
        @return: True
        """
        done = []
        res_currency_obj = self.pool.get('res.currency')
        res_users_obj = self.pool.get('res.users')
        account_move_obj = self.pool.get('account.move')
        account_move_line_obj = self.pool.get('account.move.line')
        account_analytic_line_obj = self.pool.get('account.analytic.line')
        account_bank_statement_line_obj = self.pool.get('account.bank.statement.line')

        company_currency_id = res_users_obj.browse(cr, uid, uid, context=context).company_id.currency_id.id

        for st in self.browse(cr, uid, ids, context):

            self.write(cr, uid, [st.id], {'balance_end_real':st.balance_end})
            st.balance_end_real = st.balance_end

            if not st.state == 'open':
                continue

            if not self._equal_balance(cr, uid, ids, st, context):
                raise osv.except_osv(_('Error !'), _('CashBox Balance is not matching with Calculated Balance !'))

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
                if move.analytic_account_id:
                    if not st.journal_id.analytic_journal_id:
                        raise osv.except_osv(_('No Analytic Journal !'),_("You have to define an analytic journal on the '%s' journal!") % (st.journal_id.name,))

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
                    'analytic_account_id': move.analytic_account_id and move.analytic_account_id.id or False
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
                    if company_currency_id==move.account_id.currency_id.id:
                        amount_cur = move.amount
                    else:
                        amount_cur = res_currency_obj.compute(cr, uid, company_currency_id,
                                move.account_id.currency_id.id, amount, context=context,
                                account=acc_cur)
                    val['amount_currency'] = amount_cur
                move_line_id = account_move_line_obj.create(cr, uid, val , context=context)
                torec.append(move_line_id)

                if move.analytic_account_id:
                    anal_val = {}
                    amt = (val['credit'] or  0.0) - (val['debit'] or 0.0)
                    anal_val = {
                        'name': val['name'],
                        'ref': val['ref'],
                        'date': val['date'],
                        'amount': amt,
                        'account_id': val['analytic_account_id'],
                        'currency_id': val['currency_id'],
                        'general_account_id': val['account_id'],
                        'journal_id': st.journal_id.analytic_journal_id.id,
                        'period_id': val['period_id'],
                        'user_id': uid,
                        'move_id': move_line_id
                                }
                    if val.get('amount_currency', False):
                        anal_val['amount_currency'] = val['amount_currency']
                    account_analytic_line_obj.create(cr, uid, anal_val, context=context)

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
                            'analytic_account_id':newline.analytic_id and newline.analytic_id.id or False,

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
                                _('Journal Item "%s" is not valid') % line.name)

                if move.reconcile_id and move.reconcile_id.line_ids:
                    torec += map(lambda x: x.id, move.reconcile_id.line_ids)

                    if abs(move.reconcile_amount-move.amount)<0.0001:

                        writeoff_acc_id = False
                        #There should only be one write-off account!
                        for entry in move.reconcile_id.line_new_ids:
                            writeoff_acc_id = entry.account_id.id
                            break

                        account_move_line_obj.reconcile(cr, uid, torec, 'statement', writeoff_acc_id=writeoff_acc_id, writeoff_period_id=st.period_id.id, writeoff_journal_id=st.journal_id.id, context=context)
                    else:
                        account_move_line_obj.reconcile_partial(cr, uid, torec, 'statement', context)
                move_name = st.name + ' - ' + str(move.sequence)
                account_move_obj.write(cr, uid, [move_id], {'state':'posted', 'name': move_name})
            done.append(st.id)

        vals = {
            'state':'confirm',
            'closing_date':time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.write(cr, uid, done, vals, context=context)
        return True

    def button_cancel(self, cr, uid, ids, context={}):
        done = []
        for st in self.browse(cr, uid, ids, context):
            ids = []
            for line in st.line_ids:
                ids += [x.id for x in line.move_ids]
            self.pool.get('account.move').unlink(cr, uid, ids, context)
            done.append(st.id)
        self.write(cr, uid, done, {'state':'draft'}, context=context)
        return True

account_cash_statement()

