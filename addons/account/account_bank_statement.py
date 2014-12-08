# -*- coding: utf-8 -*-

import time

from openerp import api, fields, models, _
from openerp.osv import osv, expression
import openerp.addons.decimal_precision as dp
from openerp.exceptions import Warning
from openerp.report import report_sxw
from openerp.tools import float_compare, float_round


class account_bank_statement(models.Model):
    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            journal_id = vals.get('journal_id', self._context.get('default_journal_id', False))
            journal = self.env['account.journal'].browse(journal_id)
            vals['name'] = journal.sequence_id.with_context(self._context).next_by_id()
        return super(account_bank_statement, self).create(vals)

    @api.one
    @api.depends('line_ids', 'move_line_ids', 'balance_start', 'line_ids.amount', 'balance_end_real')
    def _end_balance(self):
        total = 0
        for line in self.line_ids:
            total += line.amount
        self.total_entry_encoding = total
        self.difference = self.balance_end_real - (self.balance_start + total)
        self.balance_end = self.balance_start + total

    @api.multi
    def button_cancel(self):
        for statement in self:
            for line in statement.line_ids:
                if line.journal_entry_id:
                    raise Warning(_('Cannot cancel a statement that already created journal items.'))
        self.state = 'open'

    @api.one
    @api.depends('journal_id')
    def _currency(self):
        self.currency = self.journal_id.currency or self.env.user.company_id.currency_id

    @api.one
    @api.depends('line_ids.journal_entry_id')
    def _check_lines_reconciled(self):
        self.all_lines_reconciled = all([line.journal_entry_id.id for line in self.line_ids])

    _order = "date desc, id desc"
    _name = "account.bank.statement"
    _description = "Bank Statement"
    _inherit = ['mail.thread']

    name = fields.Char(string='Reference', states={'open': [('readonly', False)]},
        readonly=True, # readonly for account_cash_statement
        copy=False, default='/',
        help='if you give the Name other then /, its created Accounting Entries Move '
             'will be with same name as statement name. '
             'This allows the statement entries to have the same references than the '
             'statement itself')
    date_done = fields.Datetime(string="Closed On")
    date = fields.Date(string='Date', required=True, states={'confirm': [('readonly', True)]},
        select=True, copy=False, default=fields.Date.context_today)
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, states={'confirm':[('readonly',True)]})
    balance_start = fields.Float(string='Starting Balance', digits=0, states={'confirm':[('readonly',True)]})
    balance_end_real = fields.Float('Ending Balance', digits=0,
        states={'confirm': [('readonly', True)]})
    balance_end = fields.Float(compute='_end_balance', store=True,
        string="Computed Balance", help='Balance as calculated based on Opening Balance and transaction lines')
    total_entry_encoding = fields.Float(compute='_end_balance', string="Total Transactions", store=True, help="Total of transaction lines.")
    difference = fields.Float(compute='_end_balance', string="Difference", help="Difference between the theoretical closing balance and the real closing balance.")
    company_id = fields.Many2one('res.company', related='journal_id.company_id', string='Company', store=True, readonly=True,
        default=lambda self: self.env['res.company']._company_default_get('account.bank.statement'))
    line_ids = fields.One2many('account.bank.statement.line', 'statement_id', string='Statement lines',
        states={'confirm':[('readonly', True)]}, copy=True)
    move_line_ids = fields.One2many('account.move.line', 'statement_id',
        string='Entry lines', states={'confirm':[('readonly',True)]})
    state = fields.Selection([
            ('open', 'New'),
            ('confirm', 'Closed')
        ],
        string='Status', required=True, readonly=True, copy=False, default='open')
    currency = fields.Many2one('res.currency', compute='_currency', string='Currency')
    account_id = fields.Many2one('account.account', related='journal_id.default_debit_account_id', string='Account used in this journal',
        readonly=True, help='used in statement reconciliation domain, but shouldn\'t be used elswhere.')
    all_lines_reconciled = fields.Boolean(compute='_check_lines_reconciled', string='All lines reconciled')

    @api.one
    @api.constrains('state', 'balance_end', 'balance_end_real')
    def _balance_check(self, journal_type='bank'):
        if self.state == 'confirmed' and float_compare(self.difference, 0.0, precision_digits=dp.get('Account')) != 0:
            raise ValidationError(_('The ending balance is incorrect !\nThe expected balance (%.2f) is different than the computed one. (%.2f)') % (self.balance_end_real, self.balance_end))
        return True

    @api.multi
    def button_confirm_bank(self):
        for statement in self:
            if statement.state in ('open'):
                continue
            journal_type = statement.journal_id.type

            if (not statement.journal_id.default_credit_account_id) or (not statement.journal_id.default_debit_account_id):
                raise Warning(_('Please verify that a credit and a debit account is defined in the journal.'))

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
        return self.write({'state': 'confirm', 'date_done': time.strftime("%Y-%m-%d %H:%M:%S")})

    @api.multi
    def unlink(self):
        for statement in self:
            if statement.state != 'open':
                raise Warning(_('In order to delete a bank statement, you must first cancel it to delete related journal items.'))
            # Explicitly unlink bank statement lines so it will check that
            # the related journal entries have been deleted first
            statement.line_ids.unlink()
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

    @api.v7
    def reconciliation_widget_preprocess(self, cr, uid, statement_ids, context=None):
        return self.browse(cr, uid, statement_ids, context).reconciliation_widget_preprocess()

    @api.v8
    def reconciliation_widget_preprocess(self):
        """ Get statement lines of the specified statements or all unreconciled statement lines and try to automatically reconcile them / find them a partner.
            Return ids of statement lines left to reconcile and other data for the reconciliation widget. """
        statements = self
        bsl_obj = self.env['account.bank.statement.line']

        # NB : The field account_id can be used at the statement line creation/import to avoid the reconciliation process on it later on,
        # this is why we filter out statements lines where account_id is set
        st_lines_filter = [('journal_entry_id', '=', False), ('account_id', '=', False)]
        if statements:
            st_lines_filter += [('statement_id', 'in', statements.ids)]

        # Try to automatically reconcile statement lines
        automatic_reconciliation_entries = []
        st_lines_left = []
        for st_line in bsl_obj.search(st_lines_filter, order='statement_id, id'):
            counterpart = st_line.get_unambiguous_reconciliation_proposition()
            counterpart_amount = sum(line['debit'] for line in counterpart) - sum(line['credit'] for line in counterpart)
            st_line_amount = st_line.amount_currency if st_line.currency_id else st_line.amount
            if counterpart and counterpart_amount == st_line_amount:
                operation = counterpart[0]['is_reconciled'] and 'rapprochement' or 'reconciliation'
                if operation == 'reconciliation':
                    # get_reconciliation_proposition() returns informations about move lines whereas process_reconciliation() expects informations
                    # about how to create new move lines to reconcile existing ones. So, if get_reconciliation_proposition() gives us a move line
                    # whose id is 7 and debit is 500, and we want to totally reconcile it, we need to feed process_reconciliation() with :
                    # 'counterpart_move_line_id': 7,
                    # 'credit': 500
                    # This is what the reconciliation widget does.
                    counterpart = map(lambda l: {
                        'name': l['name'],
                        'debit': l['credit'],
                        'credit': l['debit'],
                        'counterpart_move_line_id': l['id'],
                    }, counterpart)
                else:
                    counterpart = [line['id'] for line in counterpart]
                try:
                    if operation == 'reconciliation': 
                        st_line.process_reconciliation(counterpart)
                    else:
                        st_line.process_rapprochement(counterpart)
                    automatic_reconciliation_entries.append(st_line.journal_entry_id.id)
                except:
                    st_lines_left.append(st_line)
            else:
                st_lines_left.append(st_line)

        # Try to set statement line's partner
        for st_line in st_lines_left:
            if st_line.name and not st_line.partner_id.id:
                additional_domain = [('ref', '=', st_line.name)]
                match_ids = st_line.get_move_lines_for_bank_reconciliation(limit=1, additional_domain=additional_domain, overlook_partner=True)
                if match_ids and match_ids[0]['partner_id']:
                    st_line.write({'partner_id': match_ids[0]['partner_id']})

        # Collect various informations for the reconciliation widget
        notifications = []
        num_auto_reconciled = len(automatic_reconciliation_entries)
        if num_auto_reconciled > 0:
            notifications += [{
                'type': 'info',
                'message': _("%d transactions were automatically reconciled.") % num_auto_reconciled if num_auto_reconciled > 1 else _("1 transaction was automatically reconciled."),
                'details': {
                    'name': _("Automatically reconciled items"),
                    'model': 'account.move',
                    'ids': automatic_reconciliation_entries
                }
            }]

        return {
            'st_lines_ids': bsl_obj.search(st_lines_filter, order='statement_id, id').ids,
            'notifications': notifications,
            'statement_name': len(statements) == 1 and statements[0].name or False,
            'num_already_reconciled_lines': statements and statements.line_ids.search_count([('journal_entry_id', '!=', False)]) or 0,
        }

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

    @api.v7
    def get_data_for_reconciliations(self, cr, uid, ids, excluded_ids=None, context=None):
        return self.browse(cr, uid, ids, context).get_data_for_reconciliations(excluded_ids)

    @api.v8
    def get_data_for_reconciliations(self, excluded_ids=None):
        """ Returns the data required to display a reconciliation widget, for each statement line in self """
        excluded_ids = excluded_ids or []
        ret = []

        for st_line in self:
            sl = st_line.get_statement_line_for_reconciliation()
            rp = st_line.get_reconciliation_proposition(excluded_ids=excluded_ids)
            excluded_ids += [move_line['id'] for move_line in rp]
            ret.append({
                'st_line': sl,
                'reconciliation_proposition': rp
            })

        return ret

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
            'communication_partner_name': self.partner_name,
            'amount_currency_str': amount_currency_str, # Amount in the statement currency
            'has_no_partner': not self.partner_id.id,
        }
        if self.partner_id:
            if amount > 0:
                data['open_balance_account_id'] = self.partner_id.property_account_receivable.id
            else:
                data['open_balance_account_id'] = self.partner_id.property_account_payable.id

        return data

    def _get_domain_maker_move_line_amount(self):
        """ Returns a function that can create the appropriate domain to search on move.line amount based on statement.line currency/amount """
        currency = self.currency_id or self.journal_id.currency
        field = currency and 'amount_residual_currency' or 'amount_residual'
        precision = currency and currency.decimal_places or self.journal_id.company_id.currency_id.decimal_places

        def ret(comparator, amount, p=precision, f=field, c=currency.id):
            if comparator == '<':
                if amount < 0:
                    domain = [(f, '<', 0), (f, '>', amount)]
                else:
                    domain = [(f, '>', 0), (f, '<', amount)]
            elif comparator == '=':
                domain = [(f, '=', float_round(amount, precision_digits=p))]
            else:
                raise osv.except_osv(_("Programmation error : domain_maker_move_line_amount requires comparator '=' or '<'"))
            domain += [('currency_id', '=', c)]
            return domain

        return ret

    def get_unambiguous_reconciliation_proposition(self, excluded_ids=None):
        """ Returns move lines that can without doubt be used to reconcile a statement line """

        # How to compare statement line amount and move lines amount
        amount_domain_maker = self._get_domain_maker_move_line_amount()
        equal_amount_domain = amount_domain_maker('=', self.amount_currency or self.amount)

        # Look for structured communication match
        if self.name:
            overlook_partner = not self.partner_id # If the transaction has no partner, look for match in payable and receivable account anyway
            domain = equal_amount_domain + [('ref', '=', self.name)]
            match_ids = self.get_move_lines_for_bank_reconciliation(excluded_ids=excluded_ids, limit=2, additional_domain=domain, overlook_partner=overlook_partner)
            if match_ids and len(match_ids) == 1:
                return match_ids

        # Look for a single move line with the same partner, the same amount
        if self.partner_id:
            match_ids = self.get_move_lines_for_bank_reconciliation(excluded_ids=excluded_ids, limit=2, additional_domain=equal_amount_domain)
            if match_ids and len(match_ids) == 1:
                return match_ids

        return []

    @api.v7
    def get_reconciliation_proposition(self, cr, uid, id, excluded_ids=None, context=None):
        return self.browse(cr, uid, id, context).get_reconciliation_proposition(excluded_ids)

    @api.v8
    def get_reconciliation_proposition(self, excluded_ids=None):
        """ Returns move lines that constitute the best guess to reconcile a statement line """

        # Look for structured communication match
        if self.name:
            overlook_partner = not self.partner_id # If the transaction has no partner, look for match in payable and receivable account anyway
            domain = [('ref', '=', self.name)]
            match_ids = self.get_move_lines_for_bank_reconciliation(excluded_ids=excluded_ids, limit=1, additional_domain=domain, overlook_partner=overlook_partner)
            if match_ids:
                return match_ids

        # How to compare statement line amount and move lines amount
        amount_domain_maker = self._get_domain_maker_move_line_amount()
        amount = self.amount_currency or self.amount

        # Look for a single move line with the same amount
        match_ids = self.get_move_lines_for_bank_reconciliation(excluded_ids=excluded_ids, limit=1, additional_domain=amount_domain_maker('=', amount))
        if match_ids:
            return match_ids

        if not self.partner_id:
            return []

        # Look for a set of move line whose amount is <= to the line's amount
        domain = [('reconciled', '=', False)] # Make sure we can't mix reconciliation and 'rapprochement'
        domain += [('account_id.internal_type', '=', amount > 0 and 'receivable' or 'payable')] # Make sure we can't mix receivable and payable
        domain += amount_domain_maker('<', amount) # Will also enforce > 0
        mv_lines = self.get_move_lines_for_bank_reconciliation(excluded_ids=excluded_ids, limit=5, additional_domain=domain)
        currency = self.currency_id or self.journal_id.currency or self.journal_id.company_id.currency_id
        precision = currency.rounding
        ret = []
        total = 0
        for line in mv_lines:
            total += abs(line['debit'] - line['credit'])
            if float_compare(total, abs(amount), precision_digits=precision) != 1:
                ret.append(line)
            else:
                break
        return ret

    def _domain_move_lines_for_bank_reconciliation(self, excluded_ids=None, str=False, additional_domain=None, overlook_partner=False):
        """ Create domain criteria that are relevant to bank statement reconciliation. """

        # Domain to fetch reconciled move lines (use case where you register a payment before you get the bank statement)
        domain_rapprochement = ['&', ('statement_id', '=', False), ('account_id', 'in', [self.journal_id.default_credit_account_id.id, self.journal_id.default_debit_account_id.id])]

        # Domain for classic reconciliation
        domain_reconciliation = [('reconciled', '=', False)]
        if self.partner_id.id or overlook_partner:
            domain_reconciliation = expression.AND([domain_reconciliation, [('account_id.internal_type', 'in', ['payable', 'receivable'])]])
        else:
            domain_reconciliation = expression.AND([domain_reconciliation, [('account_id.reconcile', '=', True)]])

        # Let's add what applies to both
        domain = expression.OR([domain_rapprochement, domain_reconciliation])
        if self.partner_id.id and not overlook_partner:
            domain = expression.AND([domain, [('partner_id', '=', self.partner_id.id)]])

        # Domain factorized for all reconciliation use cases
        ctx = dict(self._context or {})
        ctx['bank_statement_line'] = self
        generic_domain = self.env['account.move.line'].with_context(ctx).domain_move_lines_for_reconciliation(excluded_ids=excluded_ids, str=str)
        domain = expression.AND([domain, generic_domain])

        # Domain from caller
        if additional_domain is None:
            additional_domain = []
        else:
            additional_domain = expression.normalize_domain(additional_domain)
        domain = expression.AND([domain, additional_domain])

        return domain

    @api.v7
    def get_move_lines_for_bank_reconciliation(self, cr, uid, st_line_id, excluded_ids=None, str=False, offset=0, limit=None, context=None):
        return self.browse(cr, uid, st_line_id, context).get_move_lines_for_bank_reconciliation(excluded_ids=excluded_ids, str=str, offset=offset, limit=limit)

    @api.v8
    def get_move_lines_for_bank_reconciliation(self, excluded_ids=None, str=False, offset=0, limit=None, additional_domain=None, overlook_partner=False):
        """ Returns move lines for the bank statement reconciliation, prepared as a list of dicts """
        domain = self._domain_move_lines_for_bank_reconciliation(excluded_ids=excluded_ids, str=str, additional_domain=additional_domain, overlook_partner=overlook_partner)
        move_lines = self.env['account.move.line'].search(domain, offset=offset, limit=limit, order="date_maturity asc, id asc")
        target_currency = self.currency_id or self.journal_id.currency or self.journal_id.company_id.currency_id
        ret_data = move_lines.prepare_move_lines_for_reconciliation_widget(target_currency=target_currency, target_date=self.date)
        has_no_partner = not bool(self.partner_id.id)
        for line in ret_data:
            line['has_no_partner'] = has_no_partner
        return ret_data

    @api.v7
    def process_reconciliations(self, cr, uid, data, context=None):
        """ Handles data sent from the bank statement reconciliation widget """
        for datum in data:
            st_line = self.browse(cr, uid, datum['st_line_id'], context)
            if datum['type'] == 'reconciliation':
                st_line.process_reconciliation(datum['mv_line_dicts'])
            elif datum['type'] == 'rapprochement':
                st_line.process_rapprochement(datum['mv_line_ids'])

    def process_rapprochement(self, mv_line_ids):
        """ Reconcile the statement.line with already reconciled move.line (fr: rapprochement bancaire) """
        move_lines = self.env['account.move.line'].browse(mv_line_ids)
        # Check only using already reconciled entries
        for move_line in move_lines:
            if move_line.move_id.line_id.filtered(lambda l: l.account_id.reconcile).reconciled == False:
                raise Warning(_('Error!'), _('You cannot mix reconciled and unreconciled items.'))
        # Check all move lines are from the same move
        move = move_lines[0].move_id
        if any([move_line.move_id != move for move_line in move_lines]):
            raise Warning(_('Error!'), _('You cannot mix items from different journal entries.'))
        # Link move lines to the bank statement
        move_lines.write({'statement_id': self.statement_id.id})
        # Mark the statement line as reconciled
        self.journal_entry_id = move

    def _prepare_move(self, move_name):
        """ Prepare the dict of values to create the move from a statement line. This method may be overridden to adapt domain logic
            through model inheritance (make sure to call super() to establish a clean extension chain).

           :param char st_line_number: will be used as the name of the generated account move
           :return: dict of value to create() the account.move
        """
        return {
            'journal_id': self.statement_id.journal_id.id,
            'date': self.date,
            'name': move_name,
            'ref': self.ref,
        }

    def _prepare_move_line(self, move, company_currency):
        """ Prepare the dict of values to create the move line from a statement line.

            :param recordset move: the account.move to link the move line
            :param float amount: amount of the move line
            :param recordset company_currency: currency of the concerned company
        """
        if self.amount >= 0:
            account_id = self.statement_id.journal_id.default_credit_account_id.id
        else:
            account_id = self.statement_id.journal_id.default_debit_account_id.id
        partner_id = self.partner_id and self.partner_id.id or False
        # TODO : can certainly be better formulated
        amount = self.amount
        amount_currency = False
        currency_id = self.statement_id.currency.id
        if self.statement_id.currency != company_currency:
            amount_currency = self.amount
            if self.currency_id == company_currency:
                amount = self.amount_currency
            else:
                ctx = dict(self._context or {})
                ctx['date'] = self.date
                amount = self.statement_id.currency.with_context(ctx).compute(self.amount, company_currency)
        elif self.currency_id and self.amount_currency:
            amount_currency = self.amount_currency
            currency_id = self.currency_id.id
        debit = amount > 0 and amount or 0.0
        credit = amount < 0 and -amount or 0.0

        return {
            'name': self.name,
            'date': self.date,
            'ref': self.ref,
            'move_id': move.id,
            'partner_id': partner_id,
            'account_id': account_id,
            'credit': credit,
            'debit': debit,
            'statement_id': self.statement_id.id,
            'journal_id': self.statement_id.journal_id.id,
            'currency_id': amount_currency and currency_id,
            'amount_currency': amount_currency,
        }

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

    def process_reconciliation(self, mv_line_dicts):
        """ Create a move line for the statement line and for each item in mv_line_dicts. Reconcile a new move line with its counterpart_move_line_id if specified.
            Finally, mark the statement line as reconciled by putting the newly created move id in the field journal_entry_id.

            :param dict[] mv_line_dicts: move lines to create. The expected keys are :
                - 'name'
                - 'debit'
                - 'credit'
                # Only to reconcile existing move lines :
                - 'counterpart_move_line_id'
                    # ID of the move line to reconcile (partially if specified debit/credit is lower than move line's credit/debit)
                # Only to create new journal items
                - 'account_id'
                - 'tax_ids'
                - Possibly other account.move.line fields like analytic_account_id or analytics_id
            }
        """
        company_currency = self.journal_id.company_id.currency_id
        statement_currency = self.journal_id.currency or company_currency
        aml_obj = self.env['account.move.line']

        # Check and prepare received data
        if self.journal_entry_id.id:
            raise Warning(_('The bank statement line was already reconciled.'))
        for mv_line_dict in mv_line_dicts:
            if mv_line_dict.get('counterpart_move_line_id'):
                mv_line_dict['move_line'] = aml_obj.browse(mv_line_dict['counterpart_move_line_id'])
                del mv_line_dict['counterpart_move_line_id']
                if mv_line_dict['move_line'].reconciled:
                    raise Warning(_('A selected move line was already reconciled.'))

        # Create the move
        move_name = (self.statement_id.name or self.name) + "/" + str(self.sequence)
        move_vals = self._prepare_move(move_name)
        move = self.env['account.move'].create(move_vals)

        # Create the move line for the statement line
        st_line_move_line_vals = self._prepare_move_line(move, company_currency)
        aml_obj.create(st_line_move_line_vals)
        
        # Complete the dicts
        # TODO : factorize with aml.process_reconciliation
        st_line_currency = self.currency_id or statement_currency
        st_line_currency_rate = self.currency_id and (self.amount_currency / self.amount) or False
        to_create = []
        for mv_line_dict in mv_line_dicts:
            mv_line_dict['ref'] = move_name
            mv_line_dict['move_id'] = move.id
            mv_line_dict['date'] = self.statement_id.date
            mv_line_dict['partner_id'] = self.partner_id.id
            mv_line_dict['journal_id'] = self.journal_id.id
            mv_line_dict['company_id'] = self.company_id.id
            mv_line_dict['statement_id'] = self.statement_id.id
            if mv_line_dict.get('move_line'):
                if mv_line_dict['move_line'].partner_id.id: mv_line_dict['partner_id'] = mv_line_dict['move_line'].partner_id.id
                mv_line_dict['account_id'] = mv_line_dict['move_line'].account_id.id
            if st_line_currency.id != company_currency.id:
                ctx = self._context.copy()
                ctx['date'] = self.date
                mv_line_dict['amount_currency'] = mv_line_dict['debit'] - mv_line_dict['credit']
                mv_line_dict['currency_id'] = st_line_currency.id
                if self.currency_id and statement_currency.id == company_currency.id and st_line_currency_rate:
                    debit_at_current_rate = company_currency.round(mv_line_dict['debit'] / st_line_currency_rate)
                    credit_at_current_rate = company_currency.round(mv_line_dict['credit'] / st_line_currency_rate)
                elif self.currency_id and st_line_currency_rate:
                    debit_at_current_rate = statement_currency.with_context(ctx).compute(mv_line_dict['debit'] / st_line_currency_rate, company_currency)
                    credit_at_current_rate = statement_currency.with_context(ctx).compute(mv_line_dict['credit'] / st_line_currency_rate, company_currency)
                else:
                    debit_at_current_rate = st_line_currency.with_context(ctx).compute(mv_line_dict['debit'], company_currency)
                    credit_at_current_rate = st_line_currency.with_context(ctx).compute(mv_line_dict['credit'], company_currency)
                if mv_line_dict.get('move_line'):
                    #post an account line that use the same currency rate than the counterpart (to balance the account) and post the difference in another line
                    ctx['date'] = mv_line.date
                    debit_at_old_rate = st_line_currency.with_context(ctx).compute(mv_line_dict['debit'], company_currency)
                    credit_at_old_rate = st_line_currency.with_context(ctx).compute(mv_line_dict['credit'], company_currency)
                    mv_line_dict['credit'] = credit_at_old_rate
                    mv_line_dict['debit'] = debit_at_old_rate
                    if debit_at_old_rate - debit_at_current_rate:
                        currency_diff = debit_at_current_rate - debit_at_old_rate
                        to_create.append(self.get_currency_rate_line(self, -currency_diff, move.id))
                    if credit_at_old_rate - credit_at_current_rate:
                        currency_diff = credit_at_current_rate - credit_at_old_rate
                        to_create.append(self.get_currency_rate_line(self, currency_diff, move.id))
                else:
                    mv_line_dict['debit'] = debit_at_current_rate
                    mv_line_dict['credit'] = credit_at_current_rate
            elif statement_currency.id != company_currency.id:
                #statement is in foreign currency but the transaction is in company currency
                prorata_factor = (mv_line_dict['debit'] - mv_line_dict['credit']) / self.amount_currency
                mv_line_dict['amount_currency'] = prorata_factor * self.amount
            to_create.append(mv_line_dict)
        
        # Create move lines and reconcile when relevant
        for mv_line_dict in to_create:
            if mv_line_dict.get('move_line'):
                counterpart_move_line = mv_line_dict['move_line']
                del mv_line_dict['move_line']
                new_aml = aml_obj.create(mv_line_dict)
                (new_aml|counterpart_move_line).reconcile()
            else:
                aml_obj.create(mv_line_dict)
        
        # Mark the statement line as reconciled
        self.journal_entry_id = move.id

    @api.model
    def _needaction_domain_get(self):
        return [('journal_entry_id', '=', False)]

    _order = "statement_id desc, sequence"
    _name = "account.bank.statement.line"
    _description = "Bank Statement Line"
    _inherit = ['ir.needaction_mixin']

    name = fields.Char(string='Communication', required=True, default=lambda self: self.env['ir.sequence'].get('account.bank.statement.line'))
    date = fields.Date(required=True, default=lambda self: self._context.get('date', fields.Date.context_today(self)))
    amount = fields.Float(digits=0)
    partner_id = fields.Many2one('res.partner', string='Partner')
    bank_account_id = fields.Many2one('res.partner.bank', string='Bank Account')
    account_id = fields.Many2one('account.account', string='Counterpart Account', domain=[('deprecated', '=', False)],
        help="This technical field can be used at the statement line creation/import time in order to avoid the reconciliation process on it later on. The statement line will simply create a counterpart on this account")
    statement_id = fields.Many2one('account.bank.statement', string='Statement', index=True, required=True, ondelete='cascade')
    journal_id = fields.Many2one('account.journal', related='statement_id.journal_id', string='Journal', store=True, readonly=True)
    partner_name = fields.Char(string='Partner Name',
        help="This field is used to record the third party name when importing bank statement in electronic format, when the partner doesn't exist yet in the database (or cannot be found).")
    ref = fields.Char(string='Reference')
    note = fields.Text(string='Notes')
    sequence = fields.Integer(index=True, help="Gives the sequence order when displaying a list of bank statement lines.")
    company_id = fields.Many2one('res.company', related='statement_id.company_id', string='Company', store=True, readonly=True)
    journal_entry_id = fields.Many2one('account.move', string='Journal Entry', copy=False)
    amount_currency = fields.Float(string='Amount Currency', help="The amount expressed in an optional other currency if it is a multi-currency entry.", digits=0)
    currency_id = fields.Many2one('res.currency', string='Currency', help="The optional other currency if it is a multi-currency entry.")
