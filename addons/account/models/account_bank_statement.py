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

from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import Warning
from openerp.report import report_sxw
from openerp.osv import osv


class account_bank_statement(models.Model):

    @api.model
    @api.returns('self')
    def create(self, vals):
        if vals.get('name', '/') == '/':
            journal_id = vals.get('journal_id', self._default_journal_id().id)
            vals['name'] = self._compute_default_statement_name(journal_id)
        if 'line_ids' in vals:
            for idx, line in enumerate(vals['line_ids']):
                line[2]['sequence'] = idx + 1
        return super(account_bank_statement, self).create(vals)

    @api.multi
    def write(self, vals):
        res = super(account_bank_statement, self).write(vals)
        for statement in self:
            for idx, line in enumerate(statement.line_ids):
                line.write({'sequence': idx + 1})
        return res

    @api.model
    def _default_journal_id(self):
        context = dict(self._context or {})
        JournalObj = self.env['account.journal']
        journal_type = context.get('journal_type', False)
        company_id = self.env['res.company']._company_default_get('account.bank.statement')
        if journal_type:
            Journals = JournalObj.search([('type', '=', journal_type), ('company_id', '=', company_id)])
            if Journals:
                return Journals[0]
        return False

    @api.multi
    @api.depends('line_ids','move_line_ids','balance_start', 'line_ids.amount')
    def _end_balance(self):
        for statement in self:
            total = statement.balance_start
            for line in statement.line_ids:
                total += line.amount
            statement.balance_end = total

    @api.model
    def _get_period(self):
        periods = self.env['account.period'].find()
        if periods:
            return periods[0]
        return False

    @api.model
    def _compute_default_statement_name(self, journal_id):
        context = dict(self._context or {})
        period = self._get_period()
        context['fiscalyear_id'] = period.fiscalyear_id.id
        journal = self.env['account.journal'].browse(journal_id)
        return self.env['ir.sequence'].with_context(context).next_by_id(journal.sequence_id.id)

    @api.multi
    @api.depends('journal_id')
    def _currency(self):
#         res = {}
#         res_currency_obj = self.pool.get('res.currency')
        default_currency = self.env.user.company_id.currency_id
        for statement in self:
            currency = statement.journal_id.currency
            if not currency:
                currency = default_currency
#             res[statement.id] = currency.id
            statement.currency = currency.id
#         currency_names = {}
#         for currency_id, currency_name in res_currency_obj.name_get(cursor,
#                 user, [x for x in res.values()], context=context):
#             currency_names[currency_id] = currency_name
#         for statement_id in res.keys():
#             currency_id = res[statement_id]
#             res[statement_id] = (currency_id, currency_names[currency_id])
#         return res

    @api.multi
    @api.depends('line_ids.journal_entry_id')
    def _all_lines_reconciled(self):
        for statement in self:
            statement.all_lines_reconciled = all([line.journal_entry_id.id for line in statement.line_ids])

    _order = "date desc, id desc"
    _name = "account.bank.statement"
    _description = "Bank Statement"
    _inherit = ['mail.thread']

    name = fields.Char(string='Reference', states={'draft': [('readonly', False)]},
        readonly=True, # readonly for account_cash_statement
        copy=False, default='/',
        help='if you give the Name other then /, its created Accounting Entries Move '
             'will be with same name as statement name. '
             'This allows the statement entries to have the same references than the '
             'statement itself')
    date = fields.Date(string='Date', required=True, states={'confirm': [('readonly', True)]},
        select=True, copy=False, default=fields.Date.context_today)
    journal_id = fields.Many2one('account.journal', string='Journal', required=True,
        readonly=True, states={'draft':[('readonly',False)]}, default=lambda self: self._default_journal_id())
    period_id = fields.Many2one('account.period', 'Period', required=True, states={'confirm':[('readonly', True)]},
        default=lambda self: self._get_period())
    balance_start = fields.Float(string='Starting Balance', digits=dp.get_precision('Account'), states={'confirm':[('readonly',True)]})
    balance_end_real = fields.Float('Ending Balance', digits=dp.get_precision('Account'),
        states={'confirm': [('readonly', True)]}, help="Computed using the cash control lines")
    balance_end = fields.Float(compute='_end_balance', store=True,
        string="Computed Balance", help='Balance as calculated based on Opening Balance and transaction lines')
    company_id = fields.Many2one('res.company', related='journal_id.company_id',  string='Company', store=True, readonly=True,
        default=lambda self: self.env['res.company']._company_default_get('account.bank.statement'))
    line_ids = fields.One2many('account.bank.statement.line', 'statement_id', string='Statement lines',
        states={'confirm':[('readonly', True)]}, copy=True)
    move_line_ids = fields.One2many('account.move.line', 'statement_id',
        string='Entry lines', states={'confirm':[('readonly',True)]})
    state = fields.Selection([
            ('draft', 'New'),
            ('open', 'Open'), # used by cash statements
            ('confirm', 'Closed')
        ],
        string='Status', required=True, readonly=True, copy=False, default='draft',
        help='When new statement is created the status will be \'Draft\'.\n'
             'And after getting confirmation from the bank it will be in \'Confirmed\' status.')
    currency = fields.Many2one('res.currency', compute='_currency', string='Currency')
    account_id = fields.Many2one('account.account', related='journal_id.default_debit_account_id', string='Account used in this journal',
        readonly=True, help='used in statement reconciliation domain, but shouldn\'t be used elswhere.')
    cash_control = fields.Boolean(related='journal_id.cash_control', string='Cash control')
    all_lines_reconciled = fields.Boolean(compute='_all_lines_reconciled', string='All lines reconciled')

    @api.one
    @api.constrains('journal_id', 'period_id')
    def _check_company_id(self):
        if self.company_id.id != self.period_id.company_id.id:
            raise Warning(_('The journal and period chosen have to belong to the same company.'))

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

    @api.multi
    def button_dummy(self):
        return self.write({})

    @api.model
    def _prepare_move(self, st_line, st_line_number):
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

    @api.model
    def _get_counter_part_account(self, st_line):
        """Retrieve the account to use in the counterpart move.

           :param browse_record st_line: account.bank.statement.line record to create the move from.
           :return: int/long of the account.account to use as counterpart
        """
        if st_line.amount >= 0:
            return st_line.statement_id.journal_id.default_credit_account_id.id
        return st_line.statement_id.journal_id.default_debit_account_id.id

    @api.model
    def _get_counter_part_partner(self, st_line):
        """Retrieve the partner to use in the counterpart move.

           :param browse_record st_line: account.bank.statement.line record to create the move from.
           :return: int/long of the res.partner to use as counterpart
        """
        return st_line.partner_id and st_line.partner_id.id or False

    @api.model
    def _prepare_bank_move_line(self, st_line, move_id, amount, company_currency_id):
        """Compute the args to build the dict of values to create the counter part move line from a
           statement line by calling the _prepare_move_line_vals. 

           :param browse_record st_line: account.bank.statement.line record to create the move from.
           :param int/long move_id: ID of the account.move to link the move line
           :param float amount: amount of the move line
           :param int/long company_currency_id: ID of currency of the concerned company
           :return: dict of value to create() the bank account.move.line
        """
        account_id = self._get_counter_part_account(st_line)
        partner_id = self._get_counter_part_partner(st_line)
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
        return self._prepare_move_line_vals(st_line, move_id, debit, credit,
            amount_currency=amt_cur, currency_id=cur_id, account_id=account_id,
            partner_id=partner_id)

    @api.model
    def _prepare_move_line_vals(self, st_line, move_id, debit, credit, currency_id=False,
                amount_currency=False, account_id=False, partner_id=False):
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

    @api.one
    def balance_check(self, journal_type='bank'):
        if not ((abs((self.balance_end or 0.0) - self.balance_end_real) < 0.0001) or (abs((self.balance_end or 0.0) - self.balance_end_real) < 0.0001)):
            raise osv.except_osv(_('Error!'),
                    _('The statement balance is incorrect !\nThe expected balance (%.2f) is different than the computed one. (%.2f)') % (self.balance_end_real, self.balance_end))
        return True

    @api.multi
    def statement_close(self, journal_type='bank'):
        return self.write({'state':'confirm'})

    @api.model
    def check_status_condition(self, state, journal_type='bank'):
        return state in ('draft','open')

    @api.model
    def button_confirm_bank(self):
        for st in self:
            j_type = st.journal_id.type
            if not self.check_status_condition(st.state, journal_type=j_type):
                continue

            st.balance_check(journal_type=j_type)
            if (not st.journal_id.default_credit_account_id) \
                    or (not st.journal_id.default_debit_account_id):
                raise osv.except_osv(_('Configuration Error!'), _('Please verify that an account is defined in the journal.'))
            for line in st.move_line_ids:
                if line.state != 'valid':
                    raise osv.except_osv(_('Error!'), _('The account entries lines are not in valid state.'))
            moves = []
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
                    st_line.process_reconciliation([vals])
                elif not st_line.journal_entry_id.id:
                    raise osv.except_osv(_('Error!'), _('All the account entries lines must be processed in order to close the statement.'))
                moves.append(st_line.journal_entry_id)
            if moves:
                moves.post()
            st.message_post(body=_('Statement %s confirmed, journal items were created.') % (st.name,))
        self.link_bank_to_partner()
        return self.write({'state': 'confirm', 'closing_date': time.strftime("%Y-%m-%d %H:%M:%S")})

    @api.multi
    def button_cancel(self):
        bnk_st_lines = []
        for st in self:
            bnk_st_lines += [line.id for line in st.line_ids]
        bnk_st_lines.cancel()
        return self.write({'state': 'draft'})

    @api.model
    def _compute_balance_end_real(self, journal_id):
        res = False
        if journal_id:
            journal = self.env['account.journal'].browse(journal_id)
            if journal.with_last_closing_balance:
                self._cr.execute('SELECT balance_end_real \
                      FROM account_bank_statement \
                      WHERE journal_id = %s AND NOT state = %s \
                      ORDER BY date DESC,id DESC LIMIT 1', (journal_id, 'draft'))
                res = self._cr.fetchone()
        return res and res[0] or 0.0

    @api.multi
    def onchange_journal_id(self, journal_id):
        if not journal_id:
            return {}
        balance_start = self._compute_balance_end_real(journal_id)
        journal = self.env['account.journal'].browse(journal_id)
        currency = journal.currency or journal.company_id.currency_id
        res = {'balance_start': balance_start, 'company_id': journal.company_id.id, 'currency': currency.id}
        if journal.type == 'cash':
            res['cash_control'] = journal.cash_control
        return {'value': res}

    @api.multi
    def unlink(self):
        for item in self:
            if item.state != 'draft':
                raise osv.except_osv(
                    _('Invalid Action!'), 
                    _('In order to delete a bank statement, you must first cancel it to delete related journal items.')
                )
        return super(account_bank_statement, self).unlink()

    @api.multi
    def button_journal_entries(self):
        ctx = dict(self._context or {})
        ctx['journal_id'] = self.journal_id.id
        return {
            'name': _('Journal Items'),
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'account.move.line',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('statement_id', 'in', ids)],
            'context': ctx,
        }

    @api.multi
    def number_of_lines_reconciled(self):
        return self.env['account.bank.statement.line'].search_count([('statement_id', 'in', self.ids), ('journal_entry_id', '!=', False)])

    @api.model
    def link_bank_to_partner(self):
        for statement in self:
            for st_line in statement.line_ids:
                if st_line.bank_account_id and st_line.partner_id and st_line.bank_account_id.partner_id.id != st_line.partner_id.id:
                    st_line.bank_account_id.write({'partner_id': st_line.partner_id.id})

class account_bank_statement_line(models.Model):

    @api.multi
    def unlink(self):
        for item in self:
            if item.journal_entry_id:
                raise osv.except_osv(
                    _('Invalid Action!'), 
                    _('In order to delete a bank statement line, you must first cancel it to delete related journal items.')
                )
        return super(account_bank_statement_line, self).unlink()

    @api.multi
    def cancel(self):
        moves = []
        for line in self:
            if line.journal_entry_id:
                moves.append(line.journal_entry_id)
                for aml in line.journal_entry_id.line_id:
                    if aml.reconcile_id:
                        move_lines = [l for l in aml.reconcile_id.line_id]
                        move_lines.remove(aml)
                        aml.reconcile_id.unlink()
                        if len(move_lines) >= 2:
                            move_lines.reconcile_partial('auto')
        if moves:
            moves.button_cancel()
            moves.unlink()

    @api.multi
    def get_data_for_reconciliations(self, excluded_ids=None, search_reconciliation_proposition=True):
        """ Returns the data required to display a reconciliation, for each statement line id in ids """
        ret = []
        if excluded_ids is None:
            excluded_ids = []

        for st_line in self:
            reconciliation_data = {}
            if search_reconciliation_proposition:
                reconciliation_proposition = st_line.get_reconciliation_proposition(excluded_ids=excluded_ids)
                for mv_line in reconciliation_proposition:
                    excluded_ids.append(mv_line['id'])
                reconciliation_data['reconciliation_proposition'] = reconciliation_proposition
            else:
                reconciliation_data['reconciliation_proposition'] = []
            st_line = st_line.get_statement_line_for_reconciliation()
            reconciliation_data['st_line'] = st_line
            ret.append(reconciliation_data)

        return ret

    @api.one
    def get_statement_line_for_reconciliation(self):
        """ Returns the data required by the bank statement reconciliation widget to display a statement line """
        statement_currency = self.journal_id.currency or self.journal_id.company_id.currency_id
        rml_parser = report_sxw.rml_parse(self._cr, self._uid, 'reconciliation_widget_asl', context=self._context)

        if self.amount_currency and self.currency_id:
            amount = self.amount_currency
            amount_currency = self.amount
            amount_currency_str = amount_currency > 0 and amount_currency or -amount_currency
            amount_currency_str = rml_parser.formatLang(amount_currency_str, currency_obj=statement_currency)
        else:
            amount = self.amount
            amount_currency_str = ""
        amount_str = amount > 0 and amount or -amount
        amount_str = rml_parser.formatLang(amount_str, currency_obj=self.currency_id or statement_currency)

        data = {
            'id': self.id,
            'ref': self.ref,
            'note': self.note or "",
            'name': self.name,
            'date': self.date,
            'amount': amount,
            'amount_str': amount_str, # Amount in the statement line currency
            'currency_id': self.currency_id.id or statement_currency.id,
            'partner_id': self.partner_id.id,
            'statement_id': self.statement_id.id,
            'account_code': self.journal_id.default_debit_account_id.code,
            'account_name': self.journal_id.default_debit_account_id.name,
            'partner_name': self.partner_id.name,
            'amount_currency_str': amount_currency_str, # Amount in the statement currency
            'has_no_partner': not self.partner_id.id,
        }
        if self.partner_id.id:
            if amount > 0:
                data['open_balance_account_id'] = self.partner_id.property_account_receivable.id
            else:
                data['open_balance_account_id'] = self.partner_id.property_account_payable.id

        return data

    @api.one
    def get_reconciliation_proposition(self, excluded_ids=None):
        """ Returns move lines that constitute the best guess to reconcile a statement line. """
        if excluded_ids is None:
            excluded_ids = []

        # Look for structured communication
        if self.name:
            structured_com_match_domain = [('ref', '=', self.name), ('reconcile_id', '=', False), ('state', '=', 'valid'),
                ('account_id.reconcile', '=', True), ('id', 'not in', excluded_ids)]
            move_lines = self.env['account.move.line'].search(structured_com_match_domain, offset=0, limit=1)
            if move_lines:
                target_currency = self.currency_id or self.journal_id.currency or self.journal_id.company_id.currency_id
                mv_line = move_lines.prepare_move_lines_for_reconciliation_widget(target_currency=target_currency, target_date=self.date)[0]
                mv_line['has_no_partner'] = not bool(self.partner_id.id)
                # If the structured communication matches a move line that is associated with a partner, we can safely associate the statement line with the partner
                if (mv_line['partner_id']):
                    self.write({'partner_id': mv_line['partner_id']})
                    mv_line['has_no_partner'] = False
                return [mv_line]

        # If there is no identified partner or structured communication, don't look further
        if not self.partner_id.id:
            return []

        # Look for a move line whose amount matches the statement line's amount
        company_currency = self.journal_id.company_id.currency_id.id
        statement_currency = self.journal_id.currency.id or company_currency
        sign = 1
        if statement_currency == company_currency:
            amount_field = 'credit'
            sign = -1
            if self.amount > 0:
                amount_field = 'debit'
        else:
            amount_field = 'amount_currency'
            if self.amount < 0:
                sign = -1

        match_id = self.get_move_lines_for_reconciliation(excluded_ids=excluded_ids, offset=0, limit=1, additional_domain=[(amount_field, '=', (sign * self.amount))])
        if match_id:
            return [match_id[0]]

        return []

    @api.one
    def get_move_lines_for_reconciliation_by_statement_line_id(self, excluded_ids=None, str=False, offset=0, limit=None, count=False, additional_domain=None):
        """ Bridge between the web client reconciliation widget and get_move_lines_for_reconciliation (which expects a browse record) """
        if excluded_ids is None:
            excluded_ids = []
        if additional_domain is None:
            additional_domain = []
        return self.get_move_lines_for_reconciliation(excluded_ids, str, offset, limit, count, additional_domain)

    @api.one
    def get_move_lines_for_reconciliation(self, excluded_ids=None, str=False, offset=0, limit=None, count=False, additional_domain=None):
        """ Find the move lines that could be used to reconcile a statement line. If count is true, only returns the count.

            :param integers list excluded_ids: ids of move lines that should not be fetched
            :param boolean count: just return the number of records
            :param tuples list additional_domain: additional domain restrictions
        """
        if excluded_ids is None:
            excluded_ids = []
        if additional_domain is None:
            additional_domain = []

        # Make domain
        domain = additional_domain + [('reconcile_id', '=', False), ('state', '=', 'valid')]
        if self.partner_id.id:
            domain += [('partner_id', '=', self.partner_id.id),
                '|', ('account_id.type', '=', 'receivable'),
                ('account_id.type', '=', 'payable')]
        else:
            domain += [('account_id.reconcile', '=', True), ('account_id.type', '=', 'other')]
            if str:
                domain += [('partner_id.name', 'ilike', str)]
        if excluded_ids:
            domain.append(('id', 'not in', excluded_ids))
        if str:
            domain += ['|', ('move_id.name', 'ilike', str), ('move_id.ref', 'ilike', str)]

        # Get move lines
        lines = self.env['account.move.line'].search(domain, offset=offset, limit=limit, order="date_maturity asc, id asc")
        
        # Either return number of lines
        if count:
            nb_lines = 0
            reconcile_partial_ids = [] # for a partial reconciliation, take only one line
            for line in lines:
                if line.reconcile_partial_id and line.reconcile_partial_id.id in reconcile_partial_ids:
                    continue
                nb_lines += 1
                if line.reconcile_partial_id:
                    reconcile_partial_ids.append(line.reconcile_partial_id.id)
            return nb_lines
        
        # Or return list of dicts representing the formatted move lines
        else:
            target_currency = self.currency_id or self.journal_id.currency or self.journal_id.company_id.currency_id
            mv_lines = lines.prepare_move_lines_for_reconciliation_widget(target_currency=target_currency, target_date=self.date)
            has_no_partner = not bool(self.partner_id.id)
            for line in mv_lines:
                line['has_no_partner'] = has_no_partner
            return mv_lines

    @api.one
    def get_currency_rate_line(self, currency_diff, move_id):
        if currency_diff < 0:
            account_id = self.company_id.expense_currency_exchange_account_id.id
            if not account_id:
                raise osv.except_osv(_('Insufficient Configuration!'), _("You should configure the 'Loss Exchange Rate Account' in the accounting settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
        else:
            account_id = self.company_id.income_currency_exchange_account_id.id
            if not account_id:
                raise osv.except_osv(_('Insufficient Configuration!'), _("You should configure the 'Gain Exchange Rate Account' in the accounting settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
        return {
            'move_id': move_id,
            'name': _('change') + ': ' + (self.name or '/'),
            'period_id': self.statement_id.period_id.id,
            'journal_id': self.journal_id.id,
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
            'statement_id': self.statement_id.id,
            'debit': currency_diff < 0 and -currency_diff or 0,
            'credit': currency_diff > 0 and currency_diff or 0,
            'amount_currency': 0.0,
            'date': self.date,
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
    @api.model
    def _needaction_domain_get(self):
        return ['|', ('company_id', '=', False), ('company_id', 'child_of', [self.env.user.company_id.id]), ('journal_entry_id', '=', False)]

    _order = "statement_id desc, sequence"
    _name = "account.bank.statement.line"
    _description = "Bank Statement Line"
    _inherit = ['ir.needaction_mixin']

    name = fields.Char(string='Communication', required=True, default=lambda self: self.env['ir.sequence'].get('account.bank.statement.line'))
    date = fields.Date(string='Date', required=True, default=lambda self: self._context.get('date', fields.Date.context_today))
    amount = fields.Float(string='Amount', digits=dp.get_precision('Account'))
    partner_id = fields.Many2one('res.partner', string='Partner')
    bank_account_id = fields.Many2one('res.partner.bank', string='Bank Account')
    account_id = fields.Many2one('account.account', string='Account', domain=[('deprecated', '=', False)],
        help="This technical field can be used at the statement line creation/import time in order to avoid the reconciliation process on it later on. The statement line will simply create a counterpart on this account")
    statement_id = fields.Many2one('account.bank.statement', string='Statement', index=True, required=True, ondelete='cascade')
    journal_id = fields.Many2one('account.journal', related='statement_id.journal_id', string='Journal', store=True, readonly=True)
    partner_name = fields.Char(string='Partner Name',
        help="This field is used to record the third party name when importing bank statement in electronic format, when the partner doesn't exist yet in the database (or cannot be found).")
    ref = fields.Char(string='Reference')
    note = fields.Text(string='Notes')
    sequence = fields.Integer(string='Sequence', index=True, help="Gives the sequence order when displaying a list of bank statement lines.")
    company_id = fields.Many2one('res.company', related='statement_id.company_id', string='Company', store=True, readonly=True)
    journal_entry_id = fields.Many2one('account.move', string='Journal Entry', copy=False)
    amount_currency = fields.Float(string='Amount Currency', help="The amount expressed in an optional other currency if it is a multi-currency entry.",
        digits=dp.get_precision('Account'))
    currency_id = fields.Many2one('res.currency', string='Currency', help="The optional other currency if it is a multi-currency entry.")


class account_statement_operation_template(models.Model):
    _name = "account.statement.operation.template"
    _description = "Preset for the lines that can be created in a bank statement reconciliation"

    name = fields.Char(string='Button Label', required=True)
    account_id = fields.Many2one('account.account', string='Account', ondelete='cascade', domain=[('deprecated', '=', False)])
    label = fields.Char(string='Label')
    amount_type = fields.Selection([
            ('fixed', 'Fixed'),
            ('percentage_of_total', 'Percentage of total amount'),
            ('percentage_of_balance', 'Percentage of open balance')
        ],
        string='Amount type', required=True, default='percentage_of_balance')
    amount = fields.Float(string='Amount', digits=dp.get_precision('Account'),
        help="The amount will count as a debit if it is negative, as a credit if it is positive (except if amount type is 'Percentage of open balance').",
        required=True, default=100.0)
    tax_id = fields.Many2one('account.tax', string='Tax', ondelete='cascade')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', ondelete='cascade')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
