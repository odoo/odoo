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

    def _get_counter_part_account(sefl, cr, uid, st_line, context=None):
        """Retrieve the account to use in the counterpart move.

           :param browse_record st_line: account.bank.statement.line record to create the move from.
           :return: int/long of the account.account to use as counterpart
        """
        if st_line.amount >= 0:
            return st_line.statement_id.journal_id.default_credit_account_id.id
        return st_line.statement_id.journal_id.default_debit_account_id.id

    def _get_counter_part_partner(sefl, cr, uid, st_line, context=None):
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
            cur_id = st_line.currency_id or st_line.statement_id.currency.id
        if st_line.currency_id and st_line.amount_currency:
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
                if line.state <> 'valid':
                    raise osv.except_osv(_('Error!'), _('The account entries lines are not in valid state.'))
            move_ids = []
            for st_line in st.line_ids:
                if not st_line.amount:
                    continue
                if not st_line.journal_entry_id.id:
                    raise osv.except_osv(_('Error!'), _('All the account entries lines must be processed in order to close the statement.'))
                move_ids.append(st_line.journal_entry_id.id)
            self.pool.get('account.move').post(cr, uid, move_ids, context=context)
            self.message_post(cr, uid, [st.id], body=_('Statement %s confirmed, journal items were created.') % (st.name,), context=context)
        self.link_bank_to_partner(cr, uid, ids, context=context)
        return self.write(cr, uid, ids, {'state': 'confirm'}, context=context)

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
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(
                    _('Invalid Action!'), 
                    _('In order to delete a bank statement, you must first cancel it to delete related journal items.')
                )
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

    def number_of_lines_reconciled(self, cr, uid, id, context=None):
        bsl_obj = self.pool.get('account.bank.statement.line')
        return bsl_obj.search_count(cr, uid, [('statement_id', '=', id), ('journal_entry_id', '!=', False)], context=context)
        
    def get_format_currency_js_function(self, cr, uid, id, context=None):
        """ Returns a string that can be used to instanciate a javascript function.
            That function formats a number according to the statement line's currency or the statement currency"""
        company_currency = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.currency_id
        st = id and self.browse(cr, uid, id, context=context)
        if not st:
            return
        statement_currency = st.journal_id.currency or company_currency
        digits = 2 # TODO : from currency_obj
        function = ""
        done_currencies = []
        for st_line in st.line_ids:
            st_line_currency = st_line.currency_id or statement_currency
            if st_line_currency.id not in done_currencies:
                if st_line_currency.position == 'after':
                    return_str = "return amount.toFixed(" + str(digits) + ") + ' " + st_line_currency.symbol + "';"
                else:
                    return_str = "return '" + st_line_currency.symbol + " ' + amount.toFixed(" + str(digits) + ");"
                function += "if (currency_id === " + str(st_line_currency.id) + "){ " + return_str + " }"
                done_currencies.append(st_line_currency.id)
        return function

    def link_bank_to_partner(self, cr, uid, ids, context=None):
        for statement in self.browse(cr, uid, ids, context=context):
            for st_line in statement.line_ids:
                if st_line.bank_account_id and st_line.partner_id and st_line.bank_account_id.partner_id.id != st_line.partner_id.id:
                    self.pool.get('res.partner.bank').write(cr, uid, [st_line.bank_account_id.id], {'partner_id': st_line.partner_id.id}, context=context)

class account_bank_statement_line(osv.osv):

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

    def get_data_for_reconciliations(self, cr, uid, ids, context=None):
        """ Used to instanciate a batch of reconciliations in a single request """
        # Build a list of reconciliations data
        ret = []
        statement_line_done = {}
        mv_line_ids_selected = []
        for st_line in self.browse(cr, uid, ids, context=context):
            # look for structured communication first
            exact_match_id = self.search_structured_com(cr, uid, st_line, context=context)
            if exact_match_id:
                reconciliation_data = {
                    'st_line': self.get_statement_line_for_reconciliation(cr, uid, st_line.id, context),
                    'reconciliation_proposition': self.make_counter_part_lines(cr, uid, st_line, [exact_match_id], context=context)
                }
                for mv_line in reconciliation_data['reconciliation_proposition']:
                    mv_line_ids_selected.append(mv_line['id'])
                statement_line_done[st_line.id] = reconciliation_data
                
        for st_line_id in ids:
            if statement_line_done.get(st_line_id):
                ret.append(statement_line_done.get(st_line_id))
            else:
                reconciliation_data = {
                    'st_line': self.get_statement_line_for_reconciliation(cr, uid, st_line_id, context),
                    'reconciliation_proposition': self.get_reconciliation_proposition(cr, uid, st_line_id, mv_line_ids_selected, context)
                }
                for mv_line in reconciliation_data['reconciliation_proposition']:
                    mv_line_ids_selected.append(mv_line['id'])
                ret.append(reconciliation_data)

        # Check if, now that 'candidate' move lines were selected, there are moves left for statement lines
        #for reconciliation_data in ret:
        #    if not reconciliation_data['st_line']['has_no_partner']:
        #        st_line = self.browse(cr, uid, reconciliation_data['st_line']['id'], context=context)
        #        if not self.get_move_lines_counterparts(cr, uid, st_line, excluded_ids=mv_line_ids_selected, count=True, context=context):
        #            reconciliation_data['st_line']['no_match'] = True
        return ret

    def get_statement_line_for_reconciliation(self, cr, uid, id, context=None):
        """ Returns the data required by the bank statement reconciliation use case """
        line = self.browse(cr, uid, id, context=context)
        statement_currency = line.journal_id.currency or line.journal_id.company_id.currency_id
        amount = line.amount
        rml_parser = report_sxw.rml_parse(cr, uid, 'statement_line_widget', context=context)
        amount_str = line.amount > 0 and line.amount or -line.amount
        amount_str = rml_parser.formatLang(amount_str, currency_obj=statement_currency)
        amount_currency_str = ""
        if line.amount_currency and line.currency_id:
            amount_currency_str = amount_str
            amount_str = rml_parser.formatLang(line.amount_currency, currency_obj=line.currency_id)
            amount = line.amount_currency

        data = {
            'id': line.id,
            'ref': line.ref,
            'note': line.note or "",
            'name': line.name,
            'date': line.date,
            'amount': amount,
            'amount_str': amount_str,
            'currency_id': line.currency_id.id or statement_currency.id,
            'no_match': self.get_move_lines_counterparts(cr, uid, line, count=True, context=context) == 0,
            'partner_id': line.partner_id.id,
            'statement_id': line.statement_id.id,
            'account_code': line.journal_id.default_debit_account_id.code,
            'account_name': line.journal_id.default_debit_account_id.name,
            'partner_name': line.partner_id.name,
            'amount_currency_str': amount_currency_str,
            'has_no_partner': not line.partner_id.id,
        }
        if line.partner_id.id:
            data['open_balance_account_id'] = line.partner_id.property_account_payable.id
            if amount > 0:
                data['open_balance_account_id'] = line.partner_id.property_account_receivable.id
        return data

    def search_structured_com(self, cr, uid, st_line, context=None):
        if not st_line.ref:
            return
        domain = [('ref', '=', st_line.ref)]
        if st_line.partner_id:
            domain += [('partner_id', '=', st_line.partner_id.id)]
        ids = self.pool.get('account.move.line').search(cr, uid, domain, limit=1, context=context)
        return ids and ids[0] or False

    def get_reconciliation_proposition(self, cr, uid, id, excluded_ids=[], context=None):
        """ Returns move lines that constitute the best guess to reconcile a statement line. """
        st_line = self.browse(cr, uid, id, context=context)
        company_currency = st_line.journal_id.company_id.currency_id.id
        statement_currency = st_line.journal_id.currency.id or company_currency
        # either use the unsigned debit/credit fields or the signed amount_currency field
        sign = 1
        if statement_currency == company_currency:
            amount_field = 'credit'
            if st_line.amount > 0:
                amount_field = 'debit'
        else:
            amount_field = 'amount_currency'
            if st_line.amount < 0:
                sign = -1

        #we don't propose anything if there is no partner detected
        if not st_line.partner_id.id:
            return []
        # look for exact match
        exact_match_id = self.get_move_lines_counterparts(cr, uid, st_line, excluded_ids=excluded_ids, additional_domain=[(amount_field, '=', (sign * st_line.amount))])
        if exact_match_id:
            return exact_match_id

        # select oldest move lines
        if sign == -1:
            mv_lines = self.get_move_lines_counterparts(cr, uid, st_line, excluded_ids=excluded_ids, additional_domain=[(amount_field, '<', 0)])
        else:
            mv_lines = self.get_move_lines_counterparts(cr, uid, st_line, excluded_ids=excluded_ids, additional_domain=[(amount_field, '>', 0)])
        ret = []
        total = 0
        # get_move_lines_counterparts inverts debit and credit
        amount_field = 'debit' if amount_field == 'credit' else 'credit'
        for line in mv_lines:
            if total + line[amount_field] <= abs(st_line.amount):
                ret.append(line)
                total += line[amount_field]
            if total >= abs(st_line.amount):
                break
        return ret

    def get_move_lines_counterparts_id(self, cr, uid, st_line_id, excluded_ids=[], additional_domain=[], count=False, context=None):
        st_line = self.browse(cr, uid, st_line_id, context=context)
        return self.get_move_lines_counterparts(cr, uid, st_line, excluded_ids, additional_domain, count, context=context)

    def get_move_lines_counterparts(self, cr, uid, st_line, excluded_ids=[], additional_domain=[], count=False, context=None):
        """ Find the move lines that could be used to reconcile a statement line and returns the counterpart that could be created to reconcile them
            If count is true, only returns the count.

            :param st_line: the browse record of the statement line
            :param integers list excluded_ids: ids of move lines that should not be fetched
            :param string filter_str: string to filter lines
            :param integer offset: offset of the request
            :param integer limit: number of lines to fetch
            :param boolean count: just return the number of records
            :param tuples list domain: additional domain restrictions
        """
        mv_line_pool = self.pool.get('account.move.line')

        domain = additional_domain + [('reconcile_id', '=', False),('state', '=', 'valid')]
        if st_line.partner_id.id:
            domain += [('partner_id', '=', st_line.partner_id.id),
                '|', ('account_id.type', '=', 'receivable'),
                ('account_id.type', '=', 'payable')]
        else:
            domain += [('account_id.reconcile', '=', True)]
            #domain += [('account_id.reconcile', '=', True), ('account_id.type', '=', 'other')]
        if excluded_ids:
            domain.append(('id', 'not in', excluded_ids))
        line_ids = mv_line_pool.search(cr, uid, domain, order="date_maturity asc, id asc", context=context)
        return self.make_counter_part_lines(cr, uid, st_line, line_ids, count=count, context=context)

    def make_counter_part_lines(self, cr, uid, st_line, line_ids, count=False, context=None):
        if context is None:
            context = {}
        mv_line_pool = self.pool.get('account.move.line')
        currency_obj = self.pool.get('res.currency')
        company_currency = st_line.journal_id.company_id.currency_id
        statement_currency = st_line.journal_id.currency or company_currency
        rml_parser = report_sxw.rml_parse(cr, uid, 'statement_line_counterpart_widget', context=context)
        #partially reconciled lines can be displayed only once
        reconcile_partial_ids = []
        if count:
            nb_lines = 0
            for line in mv_line_pool.browse(cr, uid, line_ids, context=context):
                if line.reconcile_partial_id and line.reconcile_partial_id.id in reconcile_partial_ids:
                    continue
                nb_lines += 1
                if line.reconcile_partial_id:
                    reconcile_partial_ids.append(line.reconcile_partial_id.id)
            return nb_lines
        else:
            ret = []
            for line in mv_line_pool.browse(cr, uid, line_ids, context=context):
                if line.reconcile_partial_id and line.reconcile_partial_id.id in reconcile_partial_ids:
                    continue
                amount_currency_str = ""
                if line.currency_id and line.amount_currency:
                    amount_currency_str = rml_parser.formatLang(line.amount_currency, currency_obj=line.currency_id)
                ret_line = {
                    'id': line.id,
                    'name': line.move_id.name,
                    'ref': line.move_id.ref,
                    'account_code': line.account_id.code,
                    'account_name': line.account_id.name,
                    'account_type': line.account_id.type,
                    'date_maturity': line.date_maturity,
                    'date': line.date,
                    'period_name': line.period_id.name,
                    'journal_name': line.journal_id.name,
                    'amount_currency_str': amount_currency_str,
                    'partner_id': line.partner_id.id,
                    'partner_name': line.partner_id.name,
                    'has_no_partner': not bool(st_line.partner_id.id),
                }
                st_line_currency = st_line.currency_id or statement_currency
                if st_line.currency_id and line.currency_id and line.currency_id.id == st_line.currency_id.id:
                    if line.amount_residual_currency < 0:
                        ret_line['debit'] = 0
                        ret_line['credit'] = -line.amount_residual_currency
                    else:
                        ret_line['debit'] = line.amount_residual_currency if line.credit != 0 else 0
                        ret_line['credit'] = line.amount_residual_currency if line.debit != 0 else 0
                    ret_line['amount_currency_str'] = rml_parser.formatLang(line.amount_residual, currency_obj=company_currency)
                else:
                    if line.amount_residual < 0:
                        ret_line['debit'] = 0
                        ret_line['credit'] = -line.amount_residual
                    else:
                        ret_line['debit'] = line.amount_residual if line.credit != 0 else 0
                        ret_line['credit'] = line.amount_residual if line.debit != 0 else 0
                    ctx = context.copy()
                    ctx.update({'date': st_line.date})
                    ret_line['debit'] = currency_obj.compute(cr, uid, st_line_currency.id, company_currency.id, ret_line['debit'], context=ctx)
                    ret_line['credit'] = currency_obj.compute(cr, uid, st_line_currency.id, company_currency.id, ret_line['credit'], context=ctx)
                ret_line['debit_str'] = rml_parser.formatLang(ret_line['debit'], currency_obj=st_line_currency)
                ret_line['credit_str'] = rml_parser.formatLang(ret_line['credit'], currency_obj=st_line_currency)
                ret.append(ret_line)
                if line.reconcile_partial_id:
                    reconcile_partial_ids.append(line.reconcile_partial_id.id)
            return ret

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
            'date': st_line.date,
            'account_id': account_id
            }

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
        move_name = st_line.statement_id.name + "/" + str(st_line.sequence)
        move_vals = bs_obj._prepare_move(cr, uid, st_line, move_name, context=context)
        move_id = am_obj.create(cr, uid, move_vals, context=context)

        # Create the move line for the statement line
        amount = currency_obj.compute(cr, uid, st_line.statement_id.currency.id, company_currency.id, st_line.amount, context=context)
        bank_st_move_vals = bs_obj._prepare_bank_move_line(cr, uid, st_line, move_id, amount, company_currency.id, context=context)
        aml_obj.create(cr, uid, bank_st_move_vals, context=context)
        # Complete the dicts
        st_line_currency = st_line.currency_id or statement_currency
        st_line_currency_rate = st_line.currency_id and statement_currency.id == company_currency.id and (st_line.amount_currency / st_line.amount) or False
        to_create = []
        for mv_line_dict in mv_line_dicts:
            mv_line_dict['ref'] = move_name
            mv_line_dict['move_id'] = move_id
            mv_line_dict['period_id'] = st_line.statement_id.period_id.id
            mv_line_dict['journal_id'] = st_line.journal_id.id
            mv_line_dict['company_id'] = st_line.company_id.id
            mv_line_dict['statement_id'] = st_line.statement_id.id
            if mv_line_dict.get('counterpart_move_line_id'):
                mv_line = aml_obj.browse(cr, uid, mv_line_dict['counterpart_move_line_id'], context=context)
                mv_line_dict['account_id'] = mv_line.account_id.id
            if st_line_currency.id != company_currency.id:
                mv_line_dict['amount_currency'] = mv_line_dict['debit'] - mv_line_dict['credit']
                mv_line_dict['currency_id'] = st_line_currency.id
                if st_line.currency_id and statement_currency.id == company_currency.id and st_line_currency_rate:
                    debit_at_current_rate = self.pool.get('res.currency').round(cr, uid, company_currency, mv_line_dict['debit'] / st_line_currency_rate)
                    credit_at_current_rate = self.pool.get('res.currency').round(cr, uid, company_currency, mv_line_dict['credit'] / st_line_currency_rate)
                else:
                    debit_at_current_rate = currency_obj.compute(cr, uid, st_line_currency.id, company_currency.id, mv_line_dict['debit'], context=context)
                    credit_at_current_rate = currency_obj.compute(cr, uid, st_line_currency.id, company_currency.id, mv_line_dict['credit'], context=context)
                if mv_line_dict.get('counterpart_move_line_id'):
                    #post an account line that use the same currency rate than the counterpart (to balance the account) and post the difference in another line
                    ctx = context.copy()
                    ctx['date'] = mv_line.date
                    debit_at_old_rate = currency_obj.compute(cr, uid, st_line_currency.id, company_currency.id, mv_line_dict['debit'], context=ctx)
                    credit_at_old_rate = currency_obj.compute(cr, uid, st_line_currency.id, company_currency.id, mv_line_dict['credit'], context=ctx)
                    mv_line_dict['credit'] = credit_at_old_rate
                    mv_line_dict['debit'] = debit_at_old_rate
                    if debit_at_old_rate - debit_at_current_rate:
                        currency_diff = debit_at_current_rate - debit_at_old_rate
                        to_create.append(self.get_currency_rate_line(cr, uid, st_line, currency_diff, move_id, context=context))
                    if credit_at_old_rate - credit_at_current_rate:
                        currency_diff = credit_at_current_rate - credit_at_old_rate
                        to_create.append(self.get_currency_rate_line(cr, uid, st_line, currency_diff, move_id, context=context))
                else:
                    mv_line_dict['debit'] = debit_at_current_rate
                    mv_line_dict['credit'] = credit_at_current_rate
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
            # TODO : too slow
            aml_obj.reconcile_partial(cr, uid, pair, context=context)

        # Mark the statement line as reconciled
        self.write(cr, uid, id, {'journal_entry_id': move_id}, context=context)

    # FIXME : if it wasn't for the multicompany security settings in account_security.xml, the method would just
    # return [('journal_entry_id', '=', False)]
    # Unfortunately, that spawns a "no access rights" error ; it shouldn't.
    def _needaction_domain_get(self, cr, uid, context=None):
        user = self.pool.get("res.users").browse(cr, uid, uid)
        return ['|',('company_id','=',False),('company_id','child_of',[user.company_id.id]),('journal_entry_id', '=', False)]

    _order = "statement_id desc, sequence"
    _name = "account.bank.statement.line"
    _description = "Bank Statement Line"
    _inherit = ['ir.needaction_mixin']
    _columns = {
        'name': fields.char('Description', required=True, copy=False),
        'date': fields.date('Date', required=True, copy=False),
        'amount': fields.float('Amount', digits_compute=dp.get_precision('Account')),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'bank_account_id': fields.many2one('res.partner.bank','Bank Account'),
        'statement_id': fields.many2one('account.bank.statement', 'Statement', select=True, required=True, ondelete='cascade'),
        'journal_id': fields.related('statement_id', 'journal_id', type='many2one', relation='account.journal', string='Journal', store=True, readonly=True),
        'ref': fields.char('Structured Communication'),
        'note': fields.text('Notes'),
        'sequence': fields.integer('Sequence', select=True, help="Gives the sequence order when displaying a list of bank statement lines."),
        'company_id': fields.related('statement_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True),
        'journal_entry_id': fields.many2one('account.move', 'Journal Entry'),
        'amount_currency': fields.float('Amount Currency', help="The amount expressed in an optional other currency if it is a multi-currency entry.", digits_compute=dp.get_precision('Account')),
        'currency_id': fields.many2one('res.currency', 'Currency', help="The optional other currency if it is a multi-currency entry."),
    }
    _defaults = {
        'name': lambda self,cr,uid,context={}: self.pool.get('ir.sequence').get(cr, uid, 'account.bank.statement.line'),
        'date': lambda self,cr,uid,context={}: context.get('date', fields.date.context_today(self,cr,uid,context=context)),
    }

class account_statement_operation_template(osv.osv):
    _name = "account.statement.operation.template"
    _description = "Preset for the lines that can be created in a bank statement reconciliation"
    _columns = {
        'name': fields.char('Button Label', required=True),
        'account_id': fields.many2one('account.account', 'Account', ondelete='cascade', domain=[('type','!=','view')]),
        'label': fields.char('Label'),
        'amount_type': fields.selection([('fixed', 'Fixed'),('percentage_of_total','Percentage of total amount'),('percentage_of_balance', 'Percentage of open balance')],
                                   'Amount type', required=True),
        'amount': fields.float('Amount', digits_compute=dp.get_precision('Account'), help="Leave to 0 to ignore."),
        'tax_id': fields.many2one('account.tax', 'Tax', ondelete='cascade'),
        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic Account', ondelete='cascade'),
    }
    _defaults = {
        'amount_type': 'fixed',
        'amount': 0.0
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
