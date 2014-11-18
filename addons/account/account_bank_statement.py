# -*- coding: utf-8 -*-

import time

from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import Warning
from openerp.report import report_sxw


class account_bank_statement(models.Model):

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            journal_id = vals.get('journal_id', self._default_journal_id().id)
            vals['name'] = self._compute_default_statement_name(journal_id)
        if 'line_ids' in vals:
            for index, line in enumerate(vals['line_ids']):
                line[2]['sequence'] = index + 1
        return super(account_bank_statement, self).create(vals)

    @api.multi
    def write(self, vals):
        res = super(account_bank_statement, self).write(vals)
        for statement in self:
            for index, line in enumerate(statement.line_ids):
                line.sequence = index + 1
        return res

    @api.model
    def _default_journal_id(self):
        journal_type = self._context.get('journal_type', False)
        company_id = self.env['res.company']._company_default_get('account.bank.statement')
        Journal = False
        if journal_type:
            Journal = self.env['account.journal'].search([('type', '=', journal_type), ('company_id', '=', company_id)], limit=1)
        return Journal

    @api.multi
    @api.depends('line_ids', 'move_line_ids', 'balance_start', 'line_ids.amount')
    def _end_balance(self):
        for statement in self:
            total = statement.balance_start
            for line in statement.line_ids:
                total += line.amount
            statement.balance_end = total

    @api.model
    def _compute_default_statement_name(self, journal_id):
        context = dict(self._context or {})
        journal = self.env['account.journal'].browse(journal_id)
        return self.env['ir.sequence'].with_context(context).next_by_id(journal.sequence_id.id)

    @api.multi
    @api.depends('journal_id')
    def _currency(self):
        for statement in self:
            currency = statement.journal_id.currency or self.env.user.company_id.currency_id
            currency_name = currency.name_get()
            # TODO: simplified old code as it was useless but not getting significance
            # of this name get and passing tuple. we can set directly 
            # statement.currency = currency.id
            statement.currency = (currency.id, currency_name[0][1])

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

    @api.onchange('date')
    def onchange_date(self):
        """
            Find the correct period to use for the given date and company_id, return it and set it in the context
        """
        ctx = dict(self._context or {})
        ctx['company_id'] = self.company_id.id
        self.date = self.date

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
        currency_id = False
        amount_currency = False
        if st_line.statement_id.currency.id != company_currency_id:
            amount_currency = st_line.amount
            currency_id = st_line.statement_id.currency.id
        elif st_line.currency_id and st_line.amount_currency:
            amount_currency = st_line.amount_currency
            currency_id = st_line.currency_id.id
        return self._prepare_move_line_vals(st_line, move_id, debit, credit,
            amount_currency=amount_currency, currency_id=currency_id, account_id=account_id,
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
        cur_id = currency_id or st_line.statement_id.currency.id
        return {
            'name': st_line.name,
            'date': st_line.date,
            'ref': st_line.ref,
            'move_id': move_id,
            'partner_id': partner_id or (((st_line.partner_id) and st_line.partner_id.id) or False),
            'account_id': account_id or st_line.account_id.id,
            'credit': credit,
            'debit': debit,
            'statement_id': st_line.statement_id.id,
            'journal_id': st_line.statement_id.journal_id.id,
            'currency_id': amount_currency and cur_id,
            'amount_currency': amount_currency,
        }

    @api.one
    def balance_check(self, journal_type='bank'):
        if not ((abs((self.balance_end or 0.0) - self.balance_end_real) < 0.0001) or (abs((self.balance_end or 0.0) - self.balance_end_real) < 0.0001)):
            raise Warning(_('The statement balance is incorrect !\nThe expected balance (%.2f) is different than the computed one. (%.2f)') % (self.balance_end_real, self.balance_end))
        return True

    @api.multi
    def statement_close(self, journal_type='bank'):
        return self.write({'state':'confirm'})

    @api.model
    def check_status_condition(self, state, journal_type='bank'):
        return state in ('draft','open')

    @api.multi
    def button_confirm_bank(self):
        for statement in self:
            journal_type = statement.journal_id.type
            if not self.check_status_condition(statement.state, journal_type=journal_type):
                continue

            statement.balance_check(journal_type=journal_type)
            if (not statement.journal_id.default_credit_account_id) \
                    or (not statement.journal_id.default_debit_account_id):
                raise Warning(_('Please verify that an account is defined in the journal.'))
            for line in statement.move_line_ids:
                if line.state != 'valid':
                    raise Warning(_('The account entries lines are not in valid state.'))
            moves = []
            for st_line in statement.line_ids:
                if not st_line.amount:
                    continue
                if st_line.account_id and not st_line.journal_entry_id:
                    #make an account move as before
                    vals = {
                        'debit': st_line.amount < 0 and -st_line.amount or 0.0,
                        'credit': st_line.amount > 0 and st_line.amount or 0.0,
                        'account_id': st_line.account_id.id,
                        'name': st_line.name
                    }
                    st_line.process_reconciliation([vals])
                elif not st_line.journal_entry_id:
                    raise Warning(_('All the account entries lines must be processed in order to close the statement.'))
                moves.append(st_line.journal_entry_id)
            if moves:
                moves.post()
            statement.message_post(body=_('Statement %s confirmed, journal items were created.') % (statement.name,))
        self.link_bank_to_partner()
        return self.write({'state': 'confirm', 'closing_date': time.strftime("%Y-%m-%d %H:%M:%S")})

    @api.multi
    def button_cancel(self):
        for statement in self:
            statement.line_ids.cancel()
        self.state = 'draft'

    @api.model
    def _compute_balance_end_real(self, journal_id):
        res = 0.0
        if journal_id:
            if self.env['account.journal'].browse(journal_id).with_last_closing_balance:
                statement = self.search([('journal_id', '=', journal_id), ('state', '!=', 'draft')], limit=1, order='date DESC,id DESC')
                if statement:
                    res = statement.balance_end_real
        return res

    @api.onchange('journal_id')
    def onchange_journal_id(self):
        balance_start = self._compute_balance_end_real(self.journal_id.id)
        currency = self.journal_id.currency or self.journal_id.company_id.currency_id
        self.balance_start = balance_start
        self.company_id = self.journal_id.company_id.id
        self.currency = currency.id
        if self.journal_id.type == 'cash':
            self.cash_control = self.journal_id.cash_control

    @api.multi
    def unlink(self):
        for statement in self:
            if statement.state != 'draft':
                raise Warning(_('In order to delete a bank statement, you must first cancel it to delete related journal items.'))
        return super(account_bank_statement, self).unlink()

    @api.multi
    def button_journal_entries(self):
        context = dict(self._context or {})
        context['journal_id'] = self.journal_id.id
        return {
            'name': _('Journal Items'),
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'account.move.line',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('statement_id', 'in', self.ids)],
            'context': context,
        }

    @api.multi
    def number_of_lines_reconciled(self):
        return self.env['account.bank.statement.line'].search_count([('statement_id', 'in', self.ids), ('journal_entry_id', '!=', False)])

    @api.multi
    def link_bank_to_partner(self):
        for statement in self:
            for st_line in statement.line_ids:
                if st_line.bank_account_id and st_line.partner_id and st_line.bank_account_id.partner_id.id != st_line.partner_id.id:
                    st_line.bank_account_id.write({'partner_id': st_line.partner_id.id})

class account_bank_statement_line(models.Model):

    @api.multi
    def unlink(self):
        for line in self:
            if line.journal_entry_id:
                raise Warning(_('In order to delete a bank statement line, you must first cancel it to delete related journal items.'))
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
        if self.partner_id:
            if amount > 0:
                data['open_balance_account_id'] = self.partner_id.property_account_receivable.id
            else:
                data['open_balance_account_id'] = self.partner_id.property_account_payable.id

        return data

    @api.multi
    def get_reconciliation_proposition(self, excluded_ids=None):
        """ Returns move lines that constitute the best guess to reconcile a statement line. """
        if excluded_ids is None:
            excluded_ids = []

        # Look for structured communication
        if self.name:
            structured_com_match_domain = [('ref', '=', self.name), ('reconcile_id', '=', False),
                ('account_id.reconcile', '=', True), ('id', 'not in', excluded_ids)]
            move_line = self.env['account.move.line'].search(structured_com_match_domain, limit=1)
            if move_line:
                target_currency = self.currency_id or self.journal_id.currency or self.journal_id.company_id.currency_id
                mv_line = move_line.prepare_move_lines_for_reconciliation_widget(target_currency=target_currency, target_date=self.date)[0]
                mv_line['has_no_partner'] = not bool(self.partner_id.id)
                # If the structured communication matches a move line that is associated with a partner, we can safely associate the statement line with the partner
                if (mv_line['partner_id']):
                    self.write({'partner_id': mv_line['partner_id']})
                    mv_line['has_no_partner'] = False
                return [mv_line]

        # If there is no identified partner or structured communication, don't look further
        if not self.partner_id:
            return []

        # Look for a move line whose amount matches the statement line's amount
        sign = 1
        if self.journal_id.currency.id == self.journal_id.company_id.currency_id.id:
            amount_field = 'credit'
            sign = -1
            if self.amount > 0:
                amount_field = 'debit'
        else:
            amount_field = 'amount_currency'
            if self.amount < 0:
                sign = -1

        match_id = self.get_move_lines_for_reconciliation(excluded_ids=excluded_ids, limit=1, additional_domain=[(amount_field, '=', (sign * self.amount))])
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

    @api.multi
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
        domain = additional_domain + [('reconcile_id', '=', False)]
        if self.partner_id:
            domain += [('partner_id', '=', self.partner_id.id),
                '|', ('account_id.user_type.type', '=', 'receivable'),
                ('account_id.user_type.type', '=', 'payable')]
        else:
            domain += [('account_id.reconcile', '=', True), ('account_id.user_type.type', '=', 'other')]
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
                raise Warning(_("You should configure the 'Loss Exchange Rate Account' in the accounting settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
        else:
            account_id = self.company_id.income_currency_exchange_account_id.id
            if not account_id:
                raise Warning(_("You should configure the 'Gain Exchange Rate Account' in the accounting settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
        return {
            'move_id': move_id,
            'name': _('change') + ': ' + (self.name or '/'),
            'date': self.statement_id.date,
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

    @api.one
    def process_reconciliation(self, mv_line_dicts):
        """ Creates a move line for each item of mv_line_dicts and for the statement line. Reconcile a new move line with its counterpart_move_line_id if specified. Finally, mark the statement line as reconciled by putting the newly created move id in the column journal_entry_id.

            :param list of dicts mv_line_dicts: move lines to create. If counterpart_move_line_id is specified, reconcile with it
        """
        company_currency = self.journal_id.company_id.currency_id
        statement_currency = self.journal_id.currency or company_currency
        bs_obj = self.env['account.bank.statement']
        aml_obj = self.env['account.move.line']

        # Checks
        if self.journal_entry_id.id:
            raise Warning(_('The bank statement line was already reconciled.'))
        for mv_line_dict in mv_line_dicts:
            for field in ['debit', 'credit', 'amount_currency']:
                if field not in mv_line_dict:
                    mv_line_dict[field] = 0.0
            if mv_line_dict.get('counterpart_move_line_id'):
                mv_line = aml_obj.browse(mv_line_dict.get('counterpart_move_line_id'))
                if mv_line.reconcile_id:
                    raise Warning(_('A selected move line was already reconciled.'))

        # Create the move
        move_name = (self.statement_id.name or self.name) + "/" + str(self.sequence)
        move_vals = bs_obj._prepare_move(self, move_name)
        move_id = self.env['account.move'].create(move_vals)

        # Create the move line for the statement line
        if self.statement_id.currency != company_currency:
            if self.currency_id == company_currency:
                amount = self.amount_currency
            else:
                ctx = dict(self._context or {})
                ctx['date'] = self.date
                amount = self.statement_id.currency.with_context(ctx).compute(company_currency.id, self.amount)
        else:
            amount = self.amount
        bank_st_move_vals = bs_obj._prepare_bank_move_line(self, move_id.id, amount, company_currency.id)
        aml_obj.create(bank_st_move_vals)
        # Complete the dicts
        st_line_currency = self.currency_id or statement_currency
        st_line_currency_rate = self.currency_id and (self.amount_currency / self.amount) or False
        to_create = []
        for mv_line_dict in mv_line_dicts:
            if mv_line_dict.get('is_tax_line'):
                continue
            mv_line_dict['ref'] = move_name
            mv_line_dict['move_id'] = move_id.id
            mv_line_dict['date'] = self.statement_id.date
            mv_line_dict['journal_id'] = self.journal_id.id
            mv_line_dict['company_id'] = self.company_id.id
            mv_line_dict['statement_id'] = self.statement_id.id
            if mv_line_dict.get('counterpart_move_line_id'):
                mv_line = aml_obj.browse(mv_line_dict['counterpart_move_line_id'])
                mv_line_dict['account_id'] = mv_line.account_id.id
            if st_line_currency.id != company_currency.id:
                ctx = context.copy()
                ctx['date'] = self.date
                mv_line_dict['amount_currency'] = mv_line_dict['debit'] - mv_line_dict['credit']
                mv_line_dict['currency_id'] = st_line_currency.id
                if self.currency_id and statement_currency.id == company_currency.id and st_line_currency_rate:
                    debit_at_current_rate = company_currency.round(mv_line_dict['debit'] / st_line_currency_rate)
                    credit_at_current_rate = company_currency.round(mv_line_dict['credit'] / st_line_currency_rate)
                elif self.currency_id and st_line_currency_rate:
                    debit_at_current_rate = statement_currency.with_context(ctx).compute(company_currency.id, mv_line_dict['debit'] / st_line_currency_rate)
                    credit_at_current_rate = statement_currency.with_context(ctx).compute(company_currency.id, mv_line_dict['credit'] / st_line_currency_rate)
                else:
                    debit_at_current_rate = st_line_currency.with_context(ctx).compute(company_currency.id, mv_line_dict['debit'])
                    credit_at_current_rate = st_line_currency.with_context(ctx).compute(company_currency.id, mv_line_dict['credit'])
                if mv_line_dict.get('counterpart_move_line_id'):
                    #post an account line that use the same currency rate than the counterpart (to balance the account) and post the difference in another line
                    ctx['date'] = mv_line.date
                    debit_at_old_rate = st_line_currency.with_context(ctx).compute(company_currency.id, mv_line_dict['debit'])
                    credit_at_old_rate = st_line_currency.with_context(ctx).compute(company_currency.id, mv_line_dict['credit'])
                    mv_line_dict['credit'] = credit_at_old_rate
                    mv_line_dict['debit'] = debit_at_old_rate
                    if debit_at_old_rate - debit_at_current_rate:
                        currency_diff = debit_at_current_rate - debit_at_old_rate
                        to_create.append(self.get_currency_rate_line(self, -currency_diff, move_id.id))
                    if credit_at_old_rate - credit_at_current_rate:
                        currency_diff = credit_at_current_rate - credit_at_old_rate
                        to_create.append(self.get_currency_rate_line(self, currency_diff, move_id.id))
                else:
                    mv_line_dict['debit'] = debit_at_current_rate
                    mv_line_dict['credit'] = credit_at_current_rate
            elif statement_currency.id != company_currency.id:
                #statement is in foreign currency but the transaction is in company currency
                prorata_factor = (mv_line_dict['debit'] - mv_line_dict['credit']) / self.amount_currency
                mv_line_dict['amount_currency'] = prorata_factor * self.amount
            to_create.append(mv_line_dict)
        # Create move lines
        move_line_pairs_to_reconcile = []
        for mv_line_dict in to_create:
            counterpart_move_line_id = None # NB : this attribute is irrelevant for aml_obj.create() and needs to be removed from the dict
            if mv_line_dict.get('counterpart_move_line_id'):
                counterpart_move_line_id = mv_line_dict['counterpart_move_line_id']
                del mv_line_dict['counterpart_move_line_id']
            new_aml_id = aml_obj.create(mv_line_dict)
            if counterpart_move_line_id != None:
                move_line_pairs_to_reconcile.append([new_aml_id, counterpart_move_line_id])
        # Reconcile
        for pair in move_line_pairs_to_reconcile:
            aml_obj.reconcile_partial(pair)
        # Mark the statement line as reconciled
        self.journal_entry_id = move_id.id

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
    account_id = fields.Many2one('account.account', string='Account', ondelete='cascade',
        domain=[('deprecated', '=', False)])
    label = fields.Char(string='Label')
    amount_type = fields.Selection([
            ('fixed', 'Fixed'),
            ('percentage_of_total', 'Percentage of total amount'),
            ('percentage_of_balance', 'Percentage of open balance')
        ],
        string='Amount type', required=True, default='percentage_of_balance')
    amount = fields.Float(string='Amount', digits=dp.get_precision('Account'),
        help='''The amount will count as a debit if it is negative, as a credit if it is positive 
        (except if amount type is 'Percentage of open balance').''',
        required=True, default=100.0)
    tax_id = fields.Many2one('account.tax', string='Tax', ondelete='cascade')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', ondelete='cascade')
