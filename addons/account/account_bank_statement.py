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
import openerp.addons.decimal_precision as dp
from openerp.report import report_sxw
from openerp.tools import float_compare, float_round

import time

class account_bank_statement(osv.osv):
    def create(self, cr, uid, vals, context=None):
        if vals.get('name', '/') == '/':
            journal_id = vals.get('journal_id', self._default_journal_id(cr, uid, context=context))
            vals['name'] = self._compute_default_statement_name(cr, uid, journal_id, context=context)
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
        periods = self.pool.get('account.period').find(cr, uid, context=context)
        if periods:
            return periods[0]
        return False

    def _compute_default_statement_name(self, cr, uid, journal_id, context=None):
        context = dict(context or {})
        obj_seq = self.pool.get('ir.sequence')
        period = self.pool.get('account.period').browse(cr, uid, self._get_period(cr, uid, context=context), context=context)
        context['fiscalyear_id'] = period.fiscalyear_id.id
        journal = self.pool.get('account.journal').browse(cr, uid, journal_id, None)
        return obj_seq.next_by_id(cr, uid, journal.sequence_id.id, context=context)

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

    def _all_lines_reconciled(self, cr, uid, ids, name, args, context=None):
        res = {}
        for statement in self.browse(cr, uid, ids, context=context):
            res[statement.id] = all([line.journal_entry_id.id for line in statement.line_ids])
        return res

    _order = "date desc, id desc"
    _name = "account.bank.statement"
    _description = "Bank Statement"
    _inherit = ['mail.thread']
    _columns = {
        'name': fields.char(
            'Reference', states={'draft': [('readonly', False)]},
            readonly=True, # readonly for account_cash_statement
            copy=False,
            help='if you give the Name other then /, its created Accounting Entries Move '
                 'will be with same name as statement name. '
                 'This allows the statement entries to have the same references than the '
                 'statement itself'),
        'date': fields.date('Date', required=True, states={'confirm': [('readonly', True)]},
                            select=True, copy=False),
        'journal_id': fields.many2one('account.journal', 'Journal', required=True,
            readonly=True, states={'draft':[('readonly',False)]}),
        'period_id': fields.many2one('account.period', 'Period', required=True,
            states={'confirm':[('readonly', True)]}),
        'balance_start': fields.float('Starting Balance', digits_compute=dp.get_precision('Account'),
            states={'confirm':[('readonly',True)]}),
        'balance_end_real': fields.float('Ending Balance', digits_compute=dp.get_precision('Account'),
            states={'confirm': [('readonly', True)]}, help="Computed using the cash control lines"),
        'balance_end': fields.function(_end_balance,
            store = {
                'account.bank.statement': (lambda self, cr, uid, ids, c={}: ids, ['line_ids','move_line_ids','balance_start'], 10),
                'account.bank.statement.line': (_get_statement, ['amount'], 10),
            },
            string="Computed Balance", help='Balance as calculated based on Opening Balance and transaction lines'),
        'company_id': fields.related('journal_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True),
        'line_ids': fields.one2many('account.bank.statement.line',
                                    'statement_id', 'Statement lines',
                                    states={'confirm':[('readonly', True)]}, copy=True),
        'move_line_ids': fields.one2many('account.move.line', 'statement_id',
                                         'Entry lines', states={'confirm':[('readonly',True)]}),
        'state': fields.selection([('draft', 'New'),
                                   ('open','Open'), # used by cash statements
                                   ('confirm', 'Closed')],
                                   'Status', required=True, readonly="1",
                                   copy=False,
                                   help='When new statement is created the status will be \'Draft\'.\n'
                                        'And after getting confirmation from the bank it will be in \'Confirmed\' status.'),
        'currency': fields.function(_currency, string='Currency',
            type='many2one', relation='res.currency'),
        'account_id': fields.related('journal_id', 'default_debit_account_id', type='many2one', relation='account.account', string='Account used in this journal', readonly=True, help='used in statement reconciliation domain, but shouldn\'t be used elswhere.'),
        'cash_control': fields.related('journal_id', 'cash_control' , type='boolean', relation='account.journal',string='Cash control'),
        'all_lines_reconciled': fields.function(_all_lines_reconciled, string='All lines reconciled', type='boolean'),
    }

    _defaults = {
        'name': '/', 
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
        ctx.update({'company_id': company_id})
        pids = period_pool.find(cr, uid, dt=date, context=ctx)
        if pids:
            res.update({'period_id': pids[0]})
            context = dict(context, period_id=pids[0])

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

    def _get_counter_part_account(self, cr, uid, st_line, context=None):
        """Retrieve the account to use in the counterpart move.

           :param browse_record st_line: account.bank.statement.line record to create the move from.
           :return: int/long of the account.account to use as counterpart
        """
        if st_line.amount >= 0:
            return st_line.statement_id.journal_id.default_credit_account_id.id
        return st_line.statement_id.journal_id.default_debit_account_id.id

    def _get_counter_part_partner(self, cr, uid, st_line, context=None):
        """Retrieve the partner to use in the counterpart move.

           :param browse_record st_line: account.bank.statement.line record to create the move from.
           :return: int/long of the res.partner to use as counterpart
        """
        return st_line.partner_id and st_line.partner_id.id or False

    def _prepare_bank_move_line(self, cr, uid, st_line, move_id, amount, company_currency_id, context=None):
        """Compute the args to build the dict of values to create the counter part move line from a
           statement line by calling the _prepare_move_line_vals. 

           :param browse_record st_line: account.bank.statement.line record to create the move from.
           :param int/long move_id: ID of the account.move to link the move line
           :param float amount: amount of the move line
           :param int/long company_currency_id: ID of currency of the concerned company
           :return: dict of value to create() the bank account.move.line
        """
        account_id = self._get_counter_part_account(cr, uid, st_line, context=context)
        partner_id = self._get_counter_part_partner(cr, uid, st_line, context=context)
        debit = ((amount > 0) and amount) or 0.0
        credit = ((amount < 0) and -amount) or 0.0
        cur_id = False
        amt_cur = False
        if st_line.statement_id.currency.id != company_currency_id:
            amt_cur = st_line.amount
            cur_id = st_line.statement_id.currency.id
        elif st_line.currency_id and st_line.amount_currency:
            amt_cur = st_line.amount_currency
            cur_id = st_line.currency_id.id
        return self._prepare_move_line_vals(cr, uid, st_line, move_id, debit, credit,
            amount_currency=amt_cur, currency_id=cur_id, account_id=account_id,
            partner_id=partner_id, context=context)

    def _prepare_move_line_vals(self, cr, uid, st_line, move_id, debit, credit, currency_id=False,
                amount_currency=False, account_id=False, partner_id=False, context=None):
        """Prepare the dict of values to create the move line from a
           statement line.

           :param browse_record st_line: account.bank.statement.line record to
                  create the move from.
           :param int/long move_id: ID of the account.move to link the move line
           :param float debit: debit amount of the move line
           :param float credit: credit amount of the move line
           :param int/long currency_id: ID of currency of the move line to create
           :param float amount_currency: amount of the debit/credit expressed in the currency_id
           :param int/long account_id: ID of the account to use in the move line if different
                  from the statement line account ID
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
        }

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
        if context is None:
            context = {}

        for st in self.browse(cr, uid, ids, context=context):
            j_type = st.journal_id.type
            if not self.check_status_condition(cr, uid, st.state, journal_type=j_type):
                continue

            self.balance_check(cr, uid, st.id, journal_type=j_type, context=context)
            if (not st.journal_id.default_credit_account_id) \
                    or (not st.journal_id.default_debit_account_id):
                raise osv.except_osv(_('Configuration Error!'), _('Please verify that an account is defined in the journal.'))
            for line in st.move_line_ids:
                if line.state != 'valid':
                    raise osv.except_osv(_('Error!'), _('The account entries lines are not in valid state.'))
            move_ids = []
            for st_line in st.line_ids:
                if not st_line.amount:
                    continue
                if st_line.account_id and not st_line.journal_entry_id.id:
                    #make an account move as before
                    vals = {
                        'debit': st_line.amount < 0 and -st_line.amount or 0.0,
                        'credit': st_line.amount > 0 and st_line.amount or 0.0,
                        'account_id': st_line.account_id.id,
                        'name': st_line.name
                    }
                    self.pool.get('account.bank.statement.line').process_reconciliation(cr, uid, st_line.id, [vals], context=context)
                elif not st_line.journal_entry_id.id:
                    raise osv.except_osv(_('Error!'), _('All the account entries lines must be processed in order to close the statement.'))
                move_ids.append(st_line.journal_entry_id.id)
            if move_ids:
                self.pool.get('account.move').post(cr, uid, move_ids, context=context)
            self.message_post(cr, uid, [st.id], body=_('Statement %s confirmed, journal items were created.') % (st.name,), context=context)
        self.link_bank_to_partner(cr, uid, ids, context=context)
        return self.write(cr, uid, ids, {'state': 'confirm', 'closing_date': time.strftime("%Y-%m-%d %H:%M:%S")}, context=context)

    def button_cancel(self, cr, uid, ids, context=None):
        bnk_st_line_ids = []
        for st in self.browse(cr, uid, ids, context=context):
            bnk_st_line_ids += [line.id for line in st.line_ids]
        self.pool.get('account.bank.statement.line').cancel(cr, uid, bnk_st_line_ids, context=context)
        return self.write(cr, uid, ids, {'state': 'draft'}, context=context)

    def _compute_balance_end_real(self, cr, uid, journal_id, context=None):
        res = False
        if journal_id:
            journal = self.pool.get('account.journal').browse(cr, uid, journal_id, context=context)
            if journal.with_last_closing_balance:
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
        journal = self.pool.get('account.journal').browse(cr, uid, journal_id, context=context)
        currency = journal.currency or journal.company_id.currency_id
        res = {'balance_start': balance_start, 'company_id': journal.company_id.id, 'currency': currency.id}
        if journal.type == 'cash':
            res['cash_control'] = journal.cash_control
        return {'value': res}

    def unlink(self, cr, uid, ids, context=None):
        statement_line_obj = self.pool['account.bank.statement.line']
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(
                    _('Invalid Action!'), 
                    _('In order to delete a bank statement, you must first cancel it to delete related journal items.')
                )
            # Explicitly unlink bank statement lines
            # so it will check that the related journal entries have
            # been deleted first
            statement_line_obj.unlink(cr, uid, [line.id for line in item.line_ids], context=context)
        return super(account_bank_statement, self).unlink(cr, uid, ids, context=context)

    def button_journal_entries(self, cr, uid, ids, context=None):
        ctx = (context or {}).copy()
        ctx['journal_id'] = self.browse(cr, uid, ids[0], context=context).journal_id.id
        return {
            'name': _('Journal Items'),
            'view_type':'form',
            'view_mode':'tree',
            'res_model':'account.move.line',
            'view_id':False,
            'type':'ir.actions.act_window',
            'domain':[('statement_id','in',ids)],
            'context':ctx,
        }

    def number_of_lines_reconciled(self, cr, uid, ids, context=None):
        bsl_obj = self.pool.get('account.bank.statement.line')
        return bsl_obj.search_count(cr, uid, [('statement_id', 'in', ids), ('journal_entry_id', '!=', False)], context=context)

    def link_bank_to_partner(self, cr, uid, ids, context=None):
        for statement in self.browse(cr, uid, ids, context=context):
            for st_line in statement.line_ids:
                if st_line.bank_account_id and st_line.partner_id and st_line.bank_account_id.partner_id.id != st_line.partner_id.id:
                    self.pool.get('res.partner.bank').write(cr, uid, [st_line.bank_account_id.id], {'partner_id': st_line.partner_id.id}, context=context)

class account_bank_statement_line(osv.osv):

    def create(self, cr, uid, vals, context=None):
        if vals.get('amount_currency', 0) and not vals.get('amount', 0):
            raise osv.except_osv(_('Error!'), _('If "Amount Currency" is specified, then "Amount" must be as well.'))
        return super(account_bank_statement_line, self).create(cr, uid, vals, context=context)

    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.journal_entry_id:
                raise osv.except_osv(
                    _('Invalid Action!'), 
                    _('In order to delete a bank statement line, you must first cancel it to delete related journal items.')
                )
        return super(account_bank_statement_line, self).unlink(cr, uid, ids, context=context)

    def cancel(self, cr, uid, ids, context=None):
        account_move_obj = self.pool.get('account.move')
        move_ids = []
        for line in self.browse(cr, uid, ids, context=context):
            if line.journal_entry_id:
                move_ids.append(line.journal_entry_id.id)
                for aml in line.journal_entry_id.line_id:
                    if aml.reconcile_id:
                        move_lines = [l.id for l in aml.reconcile_id.line_id]
                        move_lines.remove(aml.id)
                        self.pool.get('account.move.reconcile').unlink(cr, uid, [aml.reconcile_id.id], context=context)
                        if len(move_lines) >= 2:
                            self.pool.get('account.move.line').reconcile_partial(cr, uid, move_lines, 'auto', context=context)
        if move_ids:
            account_move_obj.button_cancel(cr, uid, move_ids, context=context)
            account_move_obj.unlink(cr, uid, move_ids, context)

    def get_data_for_reconciliations(self, cr, uid, ids, excluded_ids=None, search_reconciliation_proposition=True, context=None):
        """ Returns the data required to display a reconciliation, for each statement line id in ids """
        ret = []
        if excluded_ids is None:
            excluded_ids = []

        for st_line in self.browse(cr, uid, ids, context=context):
            reconciliation_data = {}
            if search_reconciliation_proposition:
                reconciliation_proposition = self.get_reconciliation_proposition(cr, uid, st_line, excluded_ids=excluded_ids, context=context)
                for mv_line in reconciliation_proposition:
                    excluded_ids.append(mv_line['id'])
                reconciliation_data['reconciliation_proposition'] = reconciliation_proposition
            else:
                reconciliation_data['reconciliation_proposition'] = []
            st_line = self.get_statement_line_for_reconciliation(cr, uid, st_line, context=context)
            reconciliation_data['st_line'] = st_line
            ret.append(reconciliation_data)

        return ret

    def get_statement_line_for_reconciliation(self, cr, uid, st_line, context=None):
        """ Returns the data required by the bank statement reconciliation widget to display a statement line """
        if context is None:
            context = {}
        statement_currency = st_line.journal_id.currency or st_line.journal_id.company_id.currency_id
        rml_parser = report_sxw.rml_parse(cr, uid, 'reconciliation_widget_asl', context=context)

        if st_line.amount_currency and st_line.currency_id:
            amount = st_line.amount_currency
            amount_currency = st_line.amount
            amount_currency_str = amount_currency > 0 and amount_currency or -amount_currency
            amount_currency_str = rml_parser.formatLang(amount_currency_str, currency_obj=statement_currency)
        else:
            amount = st_line.amount
            amount_currency_str = ""
        amount_str = amount > 0 and amount or -amount
        amount_str = rml_parser.formatLang(amount_str, currency_obj=st_line.currency_id or statement_currency)

        data = {
            'id': st_line.id,
            'ref': st_line.ref,
            'note': st_line.note or "",
            'name': st_line.name,
            'date': st_line.date,
            'amount': amount,
            'amount_str': amount_str, # Amount in the statement line currency
            'currency_id': st_line.currency_id.id or statement_currency.id,
            'partner_id': st_line.partner_id.id,
            'statement_id': st_line.statement_id.id,
            'account_code': st_line.journal_id.default_debit_account_id.code,
            'account_name': st_line.journal_id.default_debit_account_id.name,
            'partner_name': st_line.partner_id.name,
            'communication_partner_name': st_line.partner_name,
            'amount_currency_str': amount_currency_str, # Amount in the statement currency
            'has_no_partner': not st_line.partner_id.id,
        }
        if st_line.partner_id.id:
            if amount > 0:
                data['open_balance_account_id'] = st_line.partner_id.property_account_receivable.id
            else:
                data['open_balance_account_id'] = st_line.partner_id.property_account_payable.id

        return data

    def _domain_reconciliation_proposition(self, cr, uid, st_line, excluded_ids=None, context=None):
        if excluded_ids is None:
            excluded_ids = []
        domain = [('ref', '=', st_line.name),
                  ('reconcile_id', '=', False),
                  ('state', '=', 'valid'),
                  ('account_id.reconcile', '=', True),
                  ('id', 'not in', excluded_ids)]
        return domain

    def get_reconciliation_proposition(self, cr, uid, st_line, excluded_ids=None, context=None):
        """ Returns move lines that constitute the best guess to reconcile a statement line. """
        mv_line_pool = self.pool.get('account.move.line')

        # Look for structured communication
        if st_line.name:
            domain = self._domain_reconciliation_proposition(cr, uid, st_line, excluded_ids=excluded_ids, context=context)
            match_id = mv_line_pool.search(cr, uid, domain, offset=0, limit=1, context=context)
            if match_id:
                mv_line_br = mv_line_pool.browse(cr, uid, match_id, context=context)
                target_currency = st_line.currency_id or st_line.journal_id.currency or st_line.journal_id.company_id.currency_id
                mv_line = mv_line_pool.prepare_move_lines_for_reconciliation_widget(cr, uid, mv_line_br, target_currency=target_currency, target_date=st_line.date, context=context)[0]
                mv_line['has_no_partner'] = not bool(st_line.partner_id.id)
                # If the structured communication matches a move line that is associated with a partner, we can safely associate the statement line with the partner
                if (mv_line['partner_id']):
                    self.write(cr, uid, st_line.id, {'partner_id': mv_line['partner_id']}, context=context)
                    mv_line['has_no_partner'] = False
                return [mv_line]

        # How to compare statement line amount and move lines amount
        precision_digits = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
        currency_id = st_line.currency_id.id or st_line.journal_id.currency.id
        # NB : amount can't be == 0 ; so float precision is not an issue for amount > 0 or amount < 0
        amount = st_line.amount_currency or st_line.amount
        domain = [('reconcile_partial_id', '=', False)]
        if currency_id:
            domain += [('currency_id', '=', currency_id)]
        sign = 1 # correct the fact that st_line.amount is signed and debit/credit is not
        amount_field = 'debit'
        if currency_id == False:
            if amount < 0:
                amount_field = 'credit'
                sign = -1
        else:
            amount_field = 'amount_currency'

        # Look for a matching amount
        domain_exact_amount = domain + [(amount_field, '=', float_round(sign * amount, precision_digits=precision_digits))]
        match_id = self.get_move_lines_for_reconciliation(cr, uid, st_line, excluded_ids=excluded_ids, offset=0, limit=1, additional_domain=domain_exact_amount)
        if match_id:
            return match_id

        if not st_line.partner_id.id:
            return []

        # Look for a set of move line whose amount is <= to the line's amount
        if amount > 0: # Make sure we can't mix receivable and payable
            domain += [('account_id.type', '=', 'receivable')]
        else:
            domain += [('account_id.type', '=', 'payable')]
        if amount_field == 'amount_currency' and amount < 0:
            domain += [(amount_field, '<', 0), (amount_field, '>', (sign * amount))]
        else:
            domain += [(amount_field, '>', 0), (amount_field, '<', (sign * amount))]
        mv_lines = self.get_move_lines_for_reconciliation(cr, uid, st_line, excluded_ids=excluded_ids, limit=5, additional_domain=domain)
        ret = []
        total = 0
        for line in mv_lines:
            total += abs(line['debit'] - line['credit'])
            if float_compare(total, abs(amount), precision_digits=precision_digits) != 1:
                ret.append(line)
            else:
                break
        return ret

    def get_move_lines_for_reconciliation_by_statement_line_id(self, cr, uid, st_line_id, excluded_ids=None, str=False, offset=0, limit=None, count=False, additional_domain=None, context=None):
        """ Bridge between the web client reconciliation widget and get_move_lines_for_reconciliation (which expects a browse record) """
        if excluded_ids is None:
            excluded_ids = []
        if additional_domain is None:
            additional_domain = []
        st_line = self.browse(cr, uid, st_line_id, context=context)
        return self.get_move_lines_for_reconciliation(cr, uid, st_line, excluded_ids, str, offset, limit, count, additional_domain, context=context)

    def _domain_move_lines_for_reconciliation(self, cr, uid, st_line, excluded_ids=None, str=False, additional_domain=None, context=None):
        if excluded_ids is None:
            excluded_ids = []
        if additional_domain is None:
            additional_domain = []
        # Make domain
        domain = additional_domain + [
            ('reconcile_id', '=', False),
            ('state', '=', 'valid'),
            ('account_id.reconcile', '=', True)
        ]
        if st_line.partner_id.id:
            domain += [('partner_id', '=', st_line.partner_id.id)]
        if excluded_ids:
            domain.append(('id', 'not in', excluded_ids))
        if str:
            domain += [
                '|', ('move_id.name', 'ilike', str),
                '|', ('move_id.ref', 'ilike', str),
                ('date_maturity', 'like', str),
            ]
            if not st_line.partner_id.id:
                domain.insert(-1, '|', )
                domain.append(('partner_id.name', 'ilike', str))
            if str != '/':
                domain.insert(-1, '|', )
                domain.append(('name', 'ilike', str))
        return domain

    def get_move_lines_for_reconciliation(self, cr, uid, st_line, excluded_ids=None, str=False, offset=0, limit=None, count=False, additional_domain=None, context=None):
        """ Find the move lines that could be used to reconcile a statement line. If count is true, only returns the count.

            :param st_line: the browse record of the statement line
            :param integers list excluded_ids: ids of move lines that should not be fetched
            :param boolean count: just return the number of records
            :param tuples list additional_domain: additional domain restrictions
        """
        mv_line_pool = self.pool.get('account.move.line')
        domain = self._domain_move_lines_for_reconciliation(cr, uid, st_line, excluded_ids=excluded_ids, str=str, additional_domain=additional_domain, context=context)
        
        # Get move lines ; in case of a partial reconciliation, only consider one line
        filtered_lines = []
        reconcile_partial_ids = []
        actual_offset = offset
        while True:
            line_ids = mv_line_pool.search(cr, uid, domain, offset=actual_offset, limit=limit, order="date_maturity asc, id asc", context=context)
            lines = mv_line_pool.browse(cr, uid, line_ids, context=context)
            make_one_more_loop = False
            for line in lines:
                if line.reconcile_partial_id and line.reconcile_partial_id.id in reconcile_partial_ids:
                    #if we filtered a line because it is partially reconciled with an already selected line, we must do one more loop
                    #in order to get the right number of items in the pager
                    make_one_more_loop = True
                    continue
                filtered_lines.append(line)
                if line.reconcile_partial_id:
                    reconcile_partial_ids.append(line.reconcile_partial_id.id)

            if not limit or not make_one_more_loop or len(filtered_lines) >= limit:
                break
            actual_offset = actual_offset + limit
        lines = limit and filtered_lines[:limit] or filtered_lines

        # Either return number of lines
        if count:
            return len(lines)

        # Or return list of dicts representing the formatted move lines
        else:
            target_currency = st_line.currency_id or st_line.journal_id.currency or st_line.journal_id.company_id.currency_id
            mv_lines = mv_line_pool.prepare_move_lines_for_reconciliation_widget(cr, uid, lines, target_currency=target_currency, target_date=st_line.date, context=context)
            has_no_partner = not bool(st_line.partner_id.id)
            for line in mv_lines:
                line['has_no_partner'] = has_no_partner
            return mv_lines

    def get_currency_rate_line(self, cr, uid, st_line, currency_diff, move_id, context=None):
        if currency_diff < 0:
            account_id = st_line.company_id.expense_currency_exchange_account_id.id
            if not account_id:
                raise osv.except_osv(_('Insufficient Configuration!'), _("You should configure the 'Loss Exchange Rate Account' in the accounting settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
        else:
            account_id = st_line.company_id.income_currency_exchange_account_id.id
            if not account_id:
                raise osv.except_osv(_('Insufficient Configuration!'), _("You should configure the 'Gain Exchange Rate Account' in the accounting settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
        return {
            'move_id': move_id,
            'name': _('change') + ': ' + (st_line.name or '/'),
            'period_id': st_line.statement_id.period_id.id,
            'journal_id': st_line.journal_id.id,
            'partner_id': st_line.partner_id.id,
            'company_id': st_line.company_id.id,
            'statement_id': st_line.statement_id.id,
            'debit': currency_diff < 0 and -currency_diff or 0,
            'credit': currency_diff > 0 and currency_diff or 0,
            'amount_currency': 0.0,
            'date': st_line.date,
            'account_id': account_id
            }

    def process_reconciliations(self, cr, uid, data, context=None):
        for datum in data:
            self.process_reconciliation(cr, uid, datum[0], datum[1], context=context)

    def process_reconciliation(self, cr, uid, id, mv_line_dicts, context=None):
        """ Creates a move line for each item of mv_line_dicts and for the statement line. Reconcile a new move line with its counterpart_move_line_id if specified. Finally, mark the statement line as reconciled by putting the newly created move id in the column journal_entry_id.

            :param int id: id of the bank statement line
            :param list of dicts mv_line_dicts: move lines to create. If counterpart_move_line_id is specified, reconcile with it
        """
        if context is None:
            context = {}
        st_line = self.browse(cr, uid, id, context=context)
        company_currency = st_line.journal_id.company_id.currency_id
        statement_currency = st_line.journal_id.currency or company_currency
        bs_obj = self.pool.get('account.bank.statement')
        am_obj = self.pool.get('account.move')
        aml_obj = self.pool.get('account.move.line')
        currency_obj = self.pool.get('res.currency')

        # Checks
        if st_line.journal_entry_id.id:
            raise osv.except_osv(_('Error!'), _('The bank statement line was already reconciled.'))
        for mv_line_dict in mv_line_dicts:
            for field in ['debit', 'credit', 'amount_currency']:
                if field not in mv_line_dict:
                    mv_line_dict[field] = 0.0
            if mv_line_dict.get('counterpart_move_line_id'):
                mv_line = aml_obj.browse(cr, uid, mv_line_dict.get('counterpart_move_line_id'), context=context)
                if mv_line.reconcile_id:
                    raise osv.except_osv(_('Error!'), _('A selected move line was already reconciled.'))

        # Create the move
        move_name = (st_line.statement_id.name or st_line.name) + "/" + str(st_line.sequence)
        move_vals = bs_obj._prepare_move(cr, uid, st_line, move_name, context=context)
        move_id = am_obj.create(cr, uid, move_vals, context=context)

        # Create the move line for the statement line
        if st_line.statement_id.currency.id != company_currency.id:
            if st_line.currency_id == company_currency:
                amount = st_line.amount_currency
            else:
                ctx = context.copy()
                ctx['date'] = st_line.date
                amount = currency_obj.compute(cr, uid, st_line.statement_id.currency.id, company_currency.id, st_line.amount, context=ctx)
        else:
            amount = st_line.amount
        bank_st_move_vals = bs_obj._prepare_bank_move_line(cr, uid, st_line, move_id, amount, company_currency.id, context=context)
        aml_obj.create(cr, uid, bank_st_move_vals, context=context)
        # Complete the dicts
        st_line_currency = st_line.currency_id or statement_currency
        st_line_currency_rate = st_line.currency_id and (st_line.amount_currency / st_line.amount) or False
        to_create = []
        for mv_line_dict in mv_line_dicts:
            if mv_line_dict.get('is_tax_line'):
                continue
            mv_line_dict['ref'] = move_name
            mv_line_dict['move_id'] = move_id
            mv_line_dict['period_id'] = st_line.statement_id.period_id.id
            mv_line_dict['journal_id'] = st_line.journal_id.id
            mv_line_dict['company_id'] = st_line.company_id.id
            mv_line_dict['statement_id'] = st_line.statement_id.id
            if mv_line_dict.get('counterpart_move_line_id'):
                mv_line = aml_obj.browse(cr, uid, mv_line_dict['counterpart_move_line_id'], context=context)
                mv_line_dict['partner_id'] = mv_line.partner_id.id or st_line.partner_id.id
                mv_line_dict['account_id'] = mv_line.account_id.id
            if st_line_currency.id != company_currency.id:
                ctx = context.copy()
                ctx['date'] = st_line.date
                mv_line_dict['amount_currency'] = mv_line_dict['debit'] - mv_line_dict['credit']
                mv_line_dict['currency_id'] = st_line_currency.id
                if st_line.currency_id and statement_currency.id == company_currency.id and st_line_currency_rate:
                    debit_at_current_rate = self.pool.get('res.currency').round(cr, uid, company_currency, mv_line_dict['debit'] / st_line_currency_rate)
                    credit_at_current_rate = self.pool.get('res.currency').round(cr, uid, company_currency, mv_line_dict['credit'] / st_line_currency_rate)
                elif st_line.currency_id and st_line_currency_rate:
                    debit_at_current_rate = currency_obj.compute(cr, uid, statement_currency.id, company_currency.id, mv_line_dict['debit'] / st_line_currency_rate, context=ctx)
                    credit_at_current_rate = currency_obj.compute(cr, uid, statement_currency.id, company_currency.id, mv_line_dict['credit'] / st_line_currency_rate, context=ctx)
                else:
                    debit_at_current_rate = currency_obj.compute(cr, uid, st_line_currency.id, company_currency.id, mv_line_dict['debit'], context=ctx)
                    credit_at_current_rate = currency_obj.compute(cr, uid, st_line_currency.id, company_currency.id, mv_line_dict['credit'], context=ctx)
                if mv_line_dict.get('counterpart_move_line_id'):
                    #post an account line that use the same currency rate than the counterpart (to balance the account) and post the difference in another line
                    ctx['date'] = mv_line.date
                    debit_at_old_rate = currency_obj.compute(cr, uid, st_line_currency.id, company_currency.id, mv_line_dict['debit'], context=ctx)
                    credit_at_old_rate = currency_obj.compute(cr, uid, st_line_currency.id, company_currency.id, mv_line_dict['credit'], context=ctx)
                    mv_line_dict['credit'] = credit_at_old_rate
                    mv_line_dict['debit'] = debit_at_old_rate
                    if debit_at_old_rate - debit_at_current_rate:
                        currency_diff = debit_at_current_rate - debit_at_old_rate
                        to_create.append(self.get_currency_rate_line(cr, uid, st_line, -currency_diff, move_id, context=context))
                    if credit_at_old_rate - credit_at_current_rate:
                        currency_diff = credit_at_current_rate - credit_at_old_rate
                        to_create.append(self.get_currency_rate_line(cr, uid, st_line, currency_diff, move_id, context=context))
                else:
                    mv_line_dict['debit'] = debit_at_current_rate
                    mv_line_dict['credit'] = credit_at_current_rate
            elif statement_currency.id != company_currency.id:
                #statement is in foreign currency but the transaction is in company currency
                prorata_factor = (mv_line_dict['debit'] - mv_line_dict['credit']) / st_line.amount_currency
                mv_line_dict['amount_currency'] = prorata_factor * st_line.amount
            to_create.append(mv_line_dict)
        # Create move lines
        move_line_pairs_to_reconcile = []
        for mv_line_dict in to_create:
            counterpart_move_line_id = None # NB : this attribute is irrelevant for aml_obj.create() and needs to be removed from the dict
            if mv_line_dict.get('counterpart_move_line_id'):
                counterpart_move_line_id = mv_line_dict['counterpart_move_line_id']
                del mv_line_dict['counterpart_move_line_id']
            new_aml_id = aml_obj.create(cr, uid, mv_line_dict, context=context)
            if counterpart_move_line_id != None:
                move_line_pairs_to_reconcile.append([new_aml_id, counterpart_move_line_id])
        # Reconcile
        for pair in move_line_pairs_to_reconcile:
            aml_obj.reconcile_partial(cr, uid, pair, context=context)
        # Mark the statement line as reconciled
        self.write(cr, uid, id, {'journal_entry_id': move_id}, context=context)

    # FIXME : if it wasn't for the multicompany security settings in account_security.xml, the method would just
    # return [('journal_entry_id', '=', False)]
    # Unfortunately, that spawns a "no access rights" error ; it shouldn't.
    def _needaction_domain_get(self, cr, uid, context=None):
        user = self.pool.get("res.users").browse(cr, uid, uid)
        return ['|', ('company_id', '=', False), ('company_id', 'child_of', [user.company_id.id]), ('journal_entry_id', '=', False)]

    _order = "statement_id desc, sequence"
    _name = "account.bank.statement.line"
    _description = "Bank Statement Line"
    _inherit = ['ir.needaction_mixin']
    _columns = {
        'name': fields.char('Communication', required=True),
        'date': fields.date('Date', required=True),
        'amount': fields.float('Amount', digits_compute=dp.get_precision('Account')),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'bank_account_id': fields.many2one('res.partner.bank','Bank Account'),
        'account_id': fields.many2one('account.account', 'Account', help="This technical field can be used at the statement line creation/import time in order to avoid the reconciliation process on it later on. The statement line will simply create a counterpart on this account"),
        'statement_id': fields.many2one('account.bank.statement', 'Statement', select=True, required=True, ondelete='restrict'),
        'journal_id': fields.related('statement_id', 'journal_id', type='many2one', relation='account.journal', string='Journal', store=True, readonly=True),
        'partner_name': fields.char('Partner Name', help="This field is used to record the third party name when importing bank statement in electronic format, when the partner doesn't exist yet in the database (or cannot be found)."),
        'ref': fields.char('Reference'),
        'note': fields.text('Notes'),
        'sequence': fields.integer('Sequence', select=True, help="Gives the sequence order when displaying a list of bank statement lines."),
        'company_id': fields.related('statement_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True),
        'journal_entry_id': fields.many2one('account.move', 'Journal Entry', copy=False),
        'amount_currency': fields.float('Amount Currency', help="The amount expressed in an optional other currency if it is a multi-currency entry.", digits_compute=dp.get_precision('Account')),
        'currency_id': fields.many2one('res.currency', 'Currency', help="The optional other currency if it is a multi-currency entry."),
    }
    _defaults = {
        'date': lambda self,cr,uid,context={}: context.get('date', fields.date.context_today(self,cr,uid,context=context)),
    }

class account_statement_operation_template(osv.osv):
    _name = "account.statement.operation.template"
    _description = "Preset for the lines that can be created in a bank statement reconciliation"
    _columns = {
        'name': fields.char('Button Label', required=True),
        'account_id': fields.many2one('account.account', 'Account', ondelete='cascade', domain=[('type', 'not in', ('view', 'closed', 'consolidation'))]),
        'label': fields.char('Journal Item Label'),
        'amount_type': fields.selection([('fixed', 'Fixed'),('percentage_of_total','Percentage of total amount'),('percentage_of_balance', 'Percentage of open balance')], 'Amount type', required=True),
        'amount': fields.float('Amount', digits_compute=dp.get_precision('Account'), required=True, help="The amount will count as a debit if it is negative, as a credit if it is positive (except if amount type is 'Percentage of open balance')."),
        'tax_id': fields.many2one('account.tax', 'Tax', ondelete='restrict', domain=[('type_tax_use','in',('purchase','all')), ('parent_id','=',False)]),
        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic Account', ondelete='set null', domain=[('type','!=','view'), ('state','not in',('close','cancelled'))]),
        'company_id': fields.many2one('res.company', 'Company', required=True),
    }
    _defaults = {
        'amount_type': 'percentage_of_balance',
        'amount': 100.0,
        'company_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
