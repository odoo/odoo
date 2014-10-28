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

from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

class account_bank_statement(osv.osv):
    def create(self, cr, uid, vals, context=None):
        if 'line_ids' in vals:
            for idx, line in enumerate(vals['line_ids']):
                line[2]['sequence'] = idx + 1
        return super(account_bank_statement, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        res = super(account_bank_statement, self).write(cr, uid, ids, vals, context=context)
        account_bank_statement_line_obj = self.pool.get('account.bank.statement.line')
        for statement in self.browse(cr, uid, ids, context):
            for idx, line in enumerate(statement.line_ids):
                account_bank_statement_line_obj.write(cr, uid, [line.id], {'sequence': idx + 1}, context=context)
        return res

    def _default_journal_id(self, cr, uid, context=None):
        if context is None:
            context = {}
        journal_pool = self.pool.get('account.journal')
        journal_type = context.get('journal_type', False)
        company_id = self.pool.get('res.company')._company_default_get(cr, uid, 'account.bank.statement',context=context)
        if journal_type:
            ids = journal_pool.search(cr, uid, [('type', '=', journal_type),('company_id','=',company_id)])
            if ids:
                return ids[0]
        return False

    def _end_balance(self, cursor, user, ids, name, attr, context=None):
        res = {}
        for statement in self.browse(cursor, user, ids, context=context):
            res[statement.id] = statement.balance_start
            for line in statement.line_ids:
                res[statement.id] += line.amount
        return res

    def _get_period(self, cr, uid, context=None):
        ctx = dict(context or {}, account_period_prefer_normal=True)
        periods = self.pool.get('account.period').find(cr, uid, context=ctx)
        if periods:
            return periods[0]
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

    def _get_statement(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('account.bank.statement.line').browse(cr, uid, ids, context=context):
            result[line.statement_id.id] = True
        return result.keys()

    _order = "date desc, id desc"
    _name = "account.bank.statement"
    _description = "Bank Statement"
    _inherit = ['mail.thread']
    _columns = {
        'name': fields.char('Reference', size=64, required=True, states={'draft': [('readonly', False)]}, readonly=True, help='if you give the Name other then /, its created Accounting Entries Move will be with same name as statement name. This allows the statement entries to have the same references than the statement itself'), # readonly for account_cash_statement
        'date': fields.date('Date', required=True, states={'confirm': [('readonly', True)]}, select=True),
        'journal_id': fields.many2one('account.journal', 'Journal', required=True,
            readonly=True, states={'draft':[('readonly',False)]}),
        'period_id': fields.many2one('account.period', 'Period', required=True,
            states={'confirm':[('readonly', True)]}),
        'balance_start': fields.float('Starting Balance', digits_compute=dp.get_precision('Account'),
            states={'confirm':[('readonly',True)]}),
        'balance_end_real': fields.float('Ending Balance', digits_compute=dp.get_precision('Account'),
            states={'confirm': [('readonly', True)]}),
        'balance_end': fields.function(_end_balance,
            store = {
                'account.bank.statement': (lambda self, cr, uid, ids, c={}: ids, ['line_ids','move_line_ids','balance_start'], 10),
                'account.bank.statement.line': (_get_statement, ['amount'], 10),
            },
            string="Computed Balance", help='Balance as calculated based on Starting Balance and transaction lines'),
        'company_id': fields.related('journal_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True),
        'line_ids': fields.one2many('account.bank.statement.line',
            'statement_id', 'Statement lines',
            states={'confirm':[('readonly', True)]}),
        'move_line_ids': fields.one2many('account.move.line', 'statement_id',
            'Entry lines', states={'confirm':[('readonly',True)]}),
        'state': fields.selection([('draft', 'New'),
                                   ('open','Open'), # used by cash statements
                                   ('confirm', 'Closed')],
                                   'Status', required=True, readonly="1",
                                   help='When new statement is created the status will be \'Draft\'.\n'
                                        'And after getting confirmation from the bank it will be in \'Confirmed\' status.'),
        'currency': fields.function(_currency, string='Currency',
            type='many2one', relation='res.currency'),
        'account_id': fields.related('journal_id', 'default_debit_account_id', type='many2one', relation='account.account', string='Account used in this journal', readonly=True, help='used in statement reconciliation domain, but shouldn\'t be used elswhere.'),
    }

    _defaults = {
        'name': "/",
        'date': fields.date.context_today,
        'state': 'draft',
        'journal_id': _default_journal_id,
        'period_id': _get_period,
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'account.bank.statement',context=c),
    }

    def _check_company_id(self, cr, uid, ids, context=None):
        for statement in self.browse(cr, uid, ids, context=context):
            if statement.company_id.id != statement.period_id.company_id.id:
                return False
        return True

    _constraints = [
        (_check_company_id, 'The journal and period chosen have to belong to the same company.', ['journal_id','period_id']),
    ]

    def onchange_date(self, cr, uid, ids, date, company_id, context=None):
        """
            Find the correct period to use for the given date and company_id, return it and set it in the context
        """
        res = {}
        period_pool = self.pool.get('account.period')

        if context is None:
            context = {}
        ctx = context.copy()
        ctx.update({'company_id': company_id, 'account_period_prefer_normal': True})
        pids = period_pool.find(cr, uid, dt=date, context=ctx)
        if pids:
            res.update({'period_id': pids[0]})
            context.update({'period_id': pids[0]})

        return {
            'value':res,
            'context':context,
        }

    def button_dummy(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {}, context=context)

    def _prepare_move(self, cr, uid, st_line, st_line_number, context=None):
        """Prepare the dict of values to create the move from a
           statement line. This method may be overridden to implement custom
           move generation (making sure to call super() to establish
           a clean extension chain).

           :param browse_record st_line: account.bank.statement.line record to
                  create the move from.
           :param char st_line_number: will be used as the name of the generated account move
           :return: dict of value to create() the account.move
        """
        return {
            'journal_id': st_line.statement_id.journal_id.id,
            'period_id': st_line.statement_id.period_id.id,
            'date': st_line.date,
            'name': st_line_number,
            'ref': st_line.ref,
        }

    def _prepare_bank_move_line(self, cr, uid, st_line, move_id, amount, company_currency_id,
        context=None):
        """Compute the args to build the dict of values to create the bank move line from a
           statement line by calling the _prepare_move_line_vals. This method may be
           overridden to implement custom move generation (making sure to call super() to
           establish a clean extension chain).

           :param browse_record st_line: account.bank.statement.line record to
                  create the move from.
           :param int/long move_id: ID of the account.move to link the move line
           :param float amount: amount of the move line
           :param int/long company_currency_id: ID of currency of the concerned company
           :return: dict of value to create() the bank account.move.line
        """
        anl_id = st_line.analytic_account_id and st_line.analytic_account_id.id or False
        debit = ((amount<0) and -amount) or 0.0
        credit =  ((amount>0) and amount) or 0.0
        cur_id = False
        amt_cur = False
        if st_line.statement_id.currency.id <> company_currency_id:
            cur_id = st_line.statement_id.currency.id
        if st_line.account_id and st_line.account_id.currency_id and st_line.account_id.currency_id.id <> company_currency_id:
            cur_id = st_line.account_id.currency_id.id
        if cur_id:
            res_currency_obj = self.pool.get('res.currency')
            amt_cur = -res_currency_obj.compute(cr, uid, company_currency_id, cur_id, amount, context=context)

        res = self._prepare_move_line_vals(cr, uid, st_line, move_id, debit, credit,
            amount_currency=amt_cur, currency_id=cur_id, analytic_id=anl_id, context=context)
        return res

    def _get_counter_part_account(self, cr, uid, st_line, context=None):
        """Retrieve the account to use in the counterpart move.
           This method may be overridden to implement custom move generation (making sure to
           call super() to establish a clean extension chain).

           :param browse_record st_line: account.bank.statement.line record to
                  create the move from.
           :return: int/long of the account.account to use as counterpart
        """
        if st_line.amount >= 0:
            return st_line.statement_id.journal_id.default_credit_account_id.id
        return st_line.statement_id.journal_id.default_debit_account_id.id

    def _get_counter_part_partner(self, cr, uid, st_line, context=None):
        """Retrieve the partner to use in the counterpart move.
           This method may be overridden to implement custom move generation (making sure to
           call super() to establish a clean extension chain).

           :param browse_record st_line: account.bank.statement.line record to
                  create the move from.
           :return: int/long of the res.partner to use as counterpart
        """
        return st_line.partner_id and st_line.partner_id.id or False

    def _prepare_counterpart_move_line(self, cr, uid, st_line, move_id, amount, company_currency_id,
        context=None):
        """Compute the args to build the dict of values to create the counter part move line from a
           statement line by calling the _prepare_move_line_vals. This method may be
           overridden to implement custom move generation (making sure to call super() to
           establish a clean extension chain).

           :param browse_record st_line: account.bank.statement.line record to
                  create the move from.
           :param int/long move_id: ID of the account.move to link the move line
           :param float amount: amount of the move line
           :param int/long account_id: ID of account to use as counter part
           :param int/long company_currency_id: ID of currency of the concerned company
           :return: dict of value to create() the bank account.move.line
        """
        account_id = self._get_counter_part_account(cr, uid, st_line, context=context)
        partner_id = self._get_counter_part_partner(cr, uid, st_line, context=context)
        debit = ((amount > 0) and amount) or 0.0
        credit =  ((amount < 0) and -amount) or 0.0
        cur_id = False
        amt_cur = False
        if st_line.statement_id.currency.id <> company_currency_id:
            amt_cur = st_line.amount
            cur_id = st_line.statement_id.currency.id
        return self._prepare_move_line_vals(cr, uid, st_line, move_id, debit, credit,
            amount_currency = amt_cur, currency_id = cur_id, account_id = account_id,
            partner_id = partner_id, context=context)

    def _prepare_move_line_vals(self, cr, uid, st_line, move_id, debit, credit, currency_id = False,
                amount_currency= False, account_id = False, analytic_id = False,
                partner_id = False, context=None):
        """Prepare the dict of values to create the move line from a
           statement line. All non-mandatory args will replace the default computed one.
           This method may be overridden to implement custom move generation (making sure to
           call super() to establish a clean extension chain).

           :param browse_record st_line: account.bank.statement.line record to
                  create the move from.
           :param int/long move_id: ID of the account.move to link the move line
           :param float debit: debit amount of the move line
           :param float credit: credit amount of the move line
           :param int/long currency_id: ID of currency of the move line to create
           :param float amount_currency: amount of the debit/credit expressed in the currency_id
           :param int/long account_id: ID of the account to use in the move line if different
                  from the statement line account ID
           :param int/long analytic_id: ID of analytic account to put on the move line
           :param int/long partner_id: ID of the partner to put on the move line
           :return: dict of value to create() the account.move.line
        """
        acc_id = account_id or st_line.account_id.id
        cur_id = currency_id or st_line.statement_id.currency.id
        par_id = partner_id or (((st_line.partner_id) and st_line.partner_id.id) or False)
        return {
            'name': st_line.name,
            'date': st_line.date,
            'ref': st_line.ref,
            'move_id': move_id,
            'partner_id': par_id,
            'account_id': acc_id,
            'credit': credit,
            'debit': debit,
            'statement_id': st_line.statement_id.id,
            'journal_id': st_line.statement_id.journal_id.id,
            'period_id': st_line.statement_id.period_id.id,
            'currency_id': amount_currency and cur_id,
            'amount_currency': amount_currency,
            'analytic_account_id': analytic_id,
        }

    def create_move_from_st_line(self, cr, uid, st_line_id, company_currency_id, st_line_number, context=None):
        """Create the account move from the statement line.

           :param int/long st_line_id: ID of the account.bank.statement.line to create the move from.
           :param int/long company_currency_id: ID of the res.currency of the company
           :param char st_line_number: will be used as the name of the generated account move
           :return: ID of the account.move created
        """

        if context is None:
            context = {}
        res_currency_obj = self.pool.get('res.currency')
        account_move_obj = self.pool.get('account.move')
        account_move_line_obj = self.pool.get('account.move.line')
        account_bank_statement_line_obj = self.pool.get('account.bank.statement.line')
        st_line = account_bank_statement_line_obj.browse(cr, uid, st_line_id, context=context)
        st = st_line.statement_id

        context.update({'date': st_line.date})

        move_vals = self._prepare_move(cr, uid, st_line, st_line_number, context=context)
        move_id = account_move_obj.create(cr, uid, move_vals, context=context)
        account_bank_statement_line_obj.write(cr, uid, [st_line.id], {
            'move_ids': [(4, move_id, False)]
        })
        torec = []
        acc_cur = ((st_line.amount<=0) and st.journal_id.default_debit_account_id) or st_line.account_id

        context.update({
                'res.currency.compute.account': acc_cur,
            })
        amount = res_currency_obj.compute(cr, uid, st.currency.id,
                company_currency_id, st_line.amount, context=context)

        bank_move_vals = self._prepare_bank_move_line(cr, uid, st_line, move_id, amount,
            company_currency_id, context=context)
        move_line_id = account_move_line_obj.create(cr, uid, bank_move_vals, context=context)
        torec.append(move_line_id)

        counterpart_move_vals = self._prepare_counterpart_move_line(cr, uid, st_line, move_id,
            amount, company_currency_id, context=context)
        account_move_line_obj.create(cr, uid, counterpart_move_vals, context=context)

        for line in account_move_line_obj.browse(cr, uid, [x.id for x in
                account_move_obj.browse(cr, uid, move_id,
                    context=context).line_id],
                context=context):
            if line.state <> 'valid':
                raise osv.except_osv(_('Error!'),
                        _('Journal item "%s" is not valid.') % line.name)

        # Bank statements will not consider boolean on journal entry_posted
        account_move_obj.post(cr, uid, [move_id], context=context)
        return move_id

    def get_next_st_line_number(self, cr, uid, st_number, st_line, context=None):
        return st_number + '/' + str(st_line.sequence)

    def balance_check(self, cr, uid, st_id, journal_type='bank', context=None):
        st = self.browse(cr, uid, st_id, context=context)
        if not ((abs((st.balance_end or 0.0) - st.balance_end_real) < 0.0001) or (abs((st.balance_end or 0.0) - st.balance_end_real) < 0.0001)):
            raise osv.except_osv(_('Error!'),
                    _('The statement balance is incorrect !\nThe expected balance (%.2f) is different than the computed one. (%.2f)') % (st.balance_end_real, st.balance_end))
        return True

    def statement_close(self, cr, uid, ids, journal_type='bank', context=None):
        return self.write(cr, uid, ids, {'state':'confirm'}, context=context)

    def check_status_condition(self, cr, uid, state, journal_type='bank'):
        return state in ('draft','open')

    def button_confirm_bank(self, cr, uid, ids, context=None):
        obj_seq = self.pool.get('ir.sequence')
        if context is None:
            context = {}

        for st in self.browse(cr, uid, ids, context=context):
            j_type = st.journal_id.type
            company_currency_id = st.journal_id.company_id.currency_id.id
            if not self.check_status_condition(cr, uid, st.state, journal_type=j_type):
                continue

            self.balance_check(cr, uid, st.id, journal_type=j_type, context=context)
            if (not st.journal_id.default_credit_account_id) \
                    or (not st.journal_id.default_debit_account_id):
                raise osv.except_osv(_('Configuration Error!'),
                        _('Please verify that an account is defined in the journal.'))

            if not st.name == '/':
                st_number = st.name
            else:
                c = {'fiscalyear_id': st.period_id.fiscalyear_id.id}
                if st.journal_id.sequence_id:
                    st_number = obj_seq.next_by_id(cr, uid, st.journal_id.sequence_id.id, context=c)
                else:
                    st_number = obj_seq.next_by_code(cr, uid, 'account.bank.statement', context=c)

            for line in st.move_line_ids:
                if line.state <> 'valid':
                    raise osv.except_osv(_('Error!'),
                            _('The account entries lines are not in valid state.'))
            for st_line in st.line_ids:
                if st_line.analytic_account_id:
                    if not st.journal_id.analytic_journal_id:
                        raise osv.except_osv(_('No Analytic Journal!'),_("You have to assign an analytic journal on the '%s' journal!") % (st.journal_id.name,))
                if not st_line.amount:
                    continue
                st_line_number = self.get_next_st_line_number(cr, uid, st_number, st_line, context)
                self.create_move_from_st_line(cr, uid, st_line.id, company_currency_id, st_line_number, context)

            self.write(cr, uid, [st.id], {
                    'name': st_number,
                    'balance_end_real': st.balance_end
            }, context=context)
            self.message_post(cr, uid, [st.id], body=_('Statement %s confirmed, journal items were created.') % (st_number,), context=context)
        return self.write(cr, uid, ids, {'state':'confirm'}, context=context)

    def button_cancel(self, cr, uid, ids, context=None):
        done = []
        account_move_obj = self.pool.get('account.move')
        for st in self.browse(cr, uid, ids, context=context):
            if st.state=='draft':
                continue
            move_ids = []
            for line in st.line_ids:
                move_ids += [x.id for x in line.move_ids]
            account_move_obj.button_cancel(cr, uid, move_ids, context=context)
            account_move_obj.unlink(cr, uid, move_ids, context)
            done.append(st.id)
        return self.write(cr, uid, done, {'state':'draft'}, context=context)

    def _compute_balance_end_real(self, cr, uid, journal_id, context=None):
        res = False
        if journal_id:
            cr.execute('SELECT balance_end_real \
                    FROM account_bank_statement \
                    WHERE journal_id = %s AND NOT state = %s \
                    ORDER BY date DESC,id DESC LIMIT 1', (journal_id, 'draft'))
            res = cr.fetchone()
        return res and res[0] or 0.0

    def onchange_journal_id(self, cr, uid, statement_id, journal_id, context=None):
        if not journal_id:
            return {}
        balance_start = self._compute_balance_end_real(cr, uid, journal_id, context=context)

        journal_data = self.pool.get('account.journal').read(cr, uid, journal_id, ['company_id', 'currency'], context=context)
        company_id = journal_data['company_id']
        currency_id = journal_data['currency'] or self.pool.get('res.company').browse(cr, uid, company_id[0], context=context).currency_id.id
        return {'value': {'balance_start': balance_start, 'company_id': company_id, 'currency': currency_id}}

    def unlink(self, cr, uid, ids, context=None):
        stat = self.read(cr, uid, ids, ['state'], context=context)
        unlink_ids = []
        for t in stat:
            if t['state'] in ('draft'):
                unlink_ids.append(t['id'])
            else:
                raise osv.except_osv(_('Invalid Action!'), _('In order to delete a bank statement, you must first cancel it to delete related journal items.'))
        osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
        return True

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        if context is None:
            context = {}
        default = default.copy()
        default['move_line_ids'] = []
        return super(account_bank_statement, self).copy(cr, uid, id, default, context=context)

    def button_journal_entries(self, cr, uid, ids, context=None):
      ctx = (context or {}).copy()
      ctx['journal_id'] = self.browse(cr, uid, ids[0], context=context).journal_id.id
      return {
        'view_type':'form',
        'view_mode':'tree',
        'res_model':'account.move.line',
        'view_id':False,
        'type':'ir.actions.act_window',
        'domain':[('statement_id','in',ids)],
        'context':ctx,
      }

account_bank_statement()

class account_bank_statement_line(osv.osv):

    def onchange_partner_id(self, cr, uid, ids, partner_id, context=None):
        obj_partner = self.pool.get('res.partner')
        if context is None:
            context = {}
        if not partner_id:
            return {}
        part = obj_partner.browse(cr, uid, partner_id, context=context)
        if not part.supplier and not part.customer:
            type = 'general'
        elif part.supplier and part.customer:
            type = 'general'
        else:
            if part.supplier == True:
                type = 'supplier'
            if part.customer == True:
                type = 'customer'
        res_type = self.onchange_type(cr, uid, ids, partner_id=partner_id, type=type, context=context)
        if res_type['value'] and res_type['value'].get('account_id', False):
            return {'value': {'type': type, 'account_id': res_type['value']['account_id']}}
        return {'value': {'type': type}}

    def onchange_type(self, cr, uid, line_id, partner_id, type, context=None):
        res = {'value': {}}
        obj_partner = self.pool.get('res.partner')
        if context is None:
            context = {}
        if not partner_id:
            return res
        account_id = False
        line = self.browse(cr, uid, line_id, context=context)
        if not line or (line and not line[0].account_id):
            part = obj_partner.browse(cr, uid, partner_id, context=context)
            if type == 'supplier':
                account_id = part.property_account_payable.id
            else:
                account_id = part.property_account_receivable.id
            res['value']['account_id'] = account_id
        return res

    _order = "statement_id desc, sequence"
    _name = "account.bank.statement.line"
    _description = "Bank Statement Line"
    _columns = {
        'name': fields.char('OBI', required=True, help="Originator to Beneficiary Information"),
        'date': fields.date('Date', required=True),
        'amount': fields.float('Amount', digits_compute=dp.get_precision('Account')),
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
        'journal_id': fields.related('statement_id', 'journal_id', type='many2one', relation='account.journal', string='Journal', store=True, readonly=True),
        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic Account'),
        'move_ids': fields.many2many('account.move',
            'account_bank_statement_line_move_rel', 'statement_line_id','move_id',
            'Moves'),
        'ref': fields.char('Reference', size=32),
        'note': fields.text('Notes'),
        'sequence': fields.integer('Sequence', select=True, help="Gives the sequence order when displaying a list of bank statement lines."),
        'company_id': fields.related('statement_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True),
    }
    _defaults = {
        'name': lambda self,cr,uid,context={}: self.pool.get('ir.sequence').get(cr, uid, 'account.bank.statement.line'),
        'date': lambda self,cr,uid,context={}: context.get('date', fields.date.context_today(self,cr,uid,context=context)),
        'type': 'general',
    }

account_bank_statement_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
