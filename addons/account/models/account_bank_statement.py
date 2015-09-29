# -*- coding: utf-8 -*-

from openerp import api, fields, models, _
from openerp.osv import expression
from openerp.tools import float_is_zero
from openerp.tools import float_compare, float_round
from openerp.tools.misc import formatLang
from openerp.exceptions import UserError, ValidationError

import time
import math

class AccountCashboxLine(models.Model):
    """ Cash Box Details """
    _name = 'account.cashbox.line'
    _description = 'CashBox Line'
    _rec_name = 'coin_value'
    _order = 'coin_value'

    @api.one
    @api.depends('coin_value', 'number')
    def _sub_total(self):
        """ Calculates Sub total"""
        self.subtotal = self.coin_value * self.number

    coin_value = fields.Float(string='Coin/Bill Value', required=True, digits=0)
    number = fields.Integer(string='Number of Coins/Bills', help='Opening Unit Numbers')
    subtotal = fields.Float(compute='_sub_total', string='Subtotal', digits=0, readonly=True)
    cashbox_id = fields.Many2one('account.bank.statement.cashbox')


class AccountBankStmtCashWizard(models.Model):
    """
    Account Bank Statement popup that allows entering cash details.
    """
    _name = 'account.bank.statement.cashbox'
    _description = 'Account Bank Statement Cashbox Details'

    cashbox_lines_ids = fields.One2many('account.cashbox.line', 'cashbox_id', string='Cashbox Lines')

    @api.multi
    def validate(self):
        bnk_stmt_id = self.env.context.get('bank_statement_id', False) or self.env.context.get('active_id', False)
        bnk_stmt = self.env['account.bank.statement'].browse(bnk_stmt_id)
        total = 0.0
        for lines in self.cashbox_lines_ids:
            total += lines.subtotal
        if self.env.context.get('balance', False) == 'start':
            #starting balance
            bnk_stmt.write({'balance_start': total, 'cashbox_start_id': self.id})
        else:
            #closing balance
            bnk_stmt.write({'balance_end_real': total, 'cashbox_end_id': self.id})
        return {'type': 'ir.actions.act_window_close'}


class AccountBankStmtCloseCheck(models.TransientModel):
    """
    Account Bank Statement wizard that check that closing balance is correct.
    """
    _name = 'account.bank.statement.closebalance'
    _description = 'Account Bank Statement closing balance'

    @api.multi
    def validate(self):
        bnk_stmt_id = self.env.context.get('active_id', False)
        if bnk_stmt_id:
            self.env['account.bank.statement'].browse(bnk_stmt_id).button_confirm_bank()
        return {'type': 'ir.actions.act_window_close'}


class AccountBankStatement(models.Model):

    @api.one
    @api.depends('line_ids', 'balance_start', 'line_ids.amount', 'balance_end_real')
    def _end_balance(self):
        self.total_entry_encoding = sum([line.amount for line in self.line_ids])
        self.balance_end = self.balance_start + self.total_entry_encoding
        self.difference = self.balance_end_real - self.balance_end

    @api.one
    @api.depends('journal_id')
    def _compute_currency(self):
        self.currency_id = self.journal_id.currency_id or self.env.user.company_id.currency_id

    @api.one
    @api.depends('line_ids.journal_entry_ids')
    def _check_lines_reconciled(self):
        self.all_lines_reconciled = all([line.journal_entry_ids.ids or line.account_id.id for line in self.line_ids])

    @api.model
    def _default_journal(self):
        journal_type = self.env.context.get('journal_type', False)
        company_id = self.env['res.company']._company_default_get('account.bank.statement').id
        if journal_type:
            journals = self.env['account.journal'].search([('type', '=', journal_type), ('company_id', '=', company_id)])
            if journals:
                return journals[0]
        return False

    @api.multi
    def _set_opening_balance(self, journal_id):
        last_bnk_stmt = self.search([('journal_id', '=', journal_id), ('state', '=', 'confirm')], order="date_done desc", limit=1)
        for bank_stmt in self:
            if last_bnk_stmt:
                bank_stmt.balance_start = last_bnk_stmt.balance_end
            else:
                bank_stmt.balance_start = 0

    @api.model
    def _default_opening_balance(self):
        #Search last bank statement and set current opening balance as closing balance of previous one
        journal_id = self._context.get('default_journal_id', False) or self._context.get('journal_id', False)
        if journal_id:
            last_bnk_stmt = self.search([('journal_id', '=', journal_id), ('state', '=', 'confirm')], order="date_done desc", limit=1)

            if last_bnk_stmt:
                return last_bnk_stmt.balance_end
            else:
                return 0
        else:
            return 0

    _name = "account.bank.statement"
    _description = "Bank Statement"
    _order = "date desc, id desc"
    _inherit = ['mail.thread']

    name = fields.Char(string='Reference', states={'open': [('readonly', False)]}, copy=False, readonly=True)
    date = fields.Date(required=True, states={'confirm': [('readonly', True)]}, select=True, copy=False, default=fields.Date.context_today)
    date_done = fields.Datetime(string="Closed On")
    balance_start = fields.Monetary(string='Starting Balance', states={'confirm': [('readonly', True)]}, default=_default_opening_balance)
    balance_end_real = fields.Monetary('Ending Balance', states={'confirm': [('readonly', True)]})
    state = fields.Selection([('open', 'New'), ('confirm', 'Validated')], string='Status', required=True, readonly=True, copy=False, default='open')
    currency_id = fields.Many2one('res.currency', compute='_compute_currency', oldname='currency')
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, states={'confirm': [('readonly', True)]}, default=_default_journal)
    journal_type = fields.Selection(related='journal_id.type', help="Technical field used for usability purposes")
    company_id = fields.Many2one('res.company', related='journal_id.company_id', string='Company', store=True, readonly=True,
        default=lambda self: self.env['res.company']._company_default_get('account.bank.statement'))

    total_entry_encoding = fields.Monetary('Transactions Subtotal', compute='_end_balance', store=True, help="Total of transaction lines.")
    balance_end = fields.Monetary('Computed Balance', compute='_end_balance', store=True, help='Balance as calculated based on Opening Balance and transaction lines')
    difference = fields.Monetary(compute='_end_balance', store=True, help="Difference between the computed ending balance and the specified ending balance.")

    line_ids = fields.One2many('account.bank.statement.line', 'statement_id', string='Statement lines', states={'confirm': [('readonly', True)]}, copy=True)
    move_line_ids = fields.One2many('account.move.line', 'statement_id', string='Entry lines', states={'confirm': [('readonly', True)]})
    all_lines_reconciled = fields.Boolean(compute='_check_lines_reconciled')
    user_id = fields.Many2one('res.users', string='Responsible', required=False, default=lambda self: self.env.user)
    cashbox_start_id = fields.Many2one('account.bank.statement.cashbox')
    cashbox_end_id = fields.Many2one('account.bank.statement.cashbox')


    @api.onchange('journal_id')
    def onchange_journal_id(self):
        self._set_opening_balance(self.journal_id.id)

    @api.multi
    def _balance_check(self):
        for stmt in self:
            if not stmt.currency_id.is_zero(stmt.difference):
                if stmt.journal_type == 'cash':
                    if stmt.difference < 0.0:
                        account = stmt.journal_id.loss_account_id
                        name = _('Loss')
                    else:
                        # statement.difference > 0.0
                        account = stmt.journal_id.profit_account_id
                        name = _('Profit')
                    if not account:
                        raise UserError(_('There is no account defined on the journal %s for %s involved in a cash difference.') % (stmt.journal_id.name, name))

                    values = {
                        'statement_id': stmt.id,
                        'account_id': account.id,
                        'amount': stmt.difference,
                        'name': _("Cash difference observed during the counting (%s)") % name,
                    }
                    self.env['account.bank.statement.line'].create(values)
                else:
                    balance_end_real = formatLang(self.env, stmt.balance_end_real, currency_obj=stmt.currency_id)
                    balance_end = formatLang(self.env, stmt.balance_end, currency_obj=stmt.currency_id)
                    raise UserError(_('The ending balance is incorrect !\nThe expected balance (%s) is different from the computed one. (%s)')
                        % (balance_end_real, balance_end))
        return True

    @api.model
    def create(self, vals):
        if not vals.get('name'):
            journal_id = vals.get('journal_id', self._context.get('default_journal_id', False))
            journal = self.env['account.journal'].browse(journal_id)
            vals['name'] = journal.sequence_id.with_context(ir_sequence_date=vals.get('date')).next_by_id()
        return super(AccountBankStatement, self).create(vals)

    @api.multi
    def unlink(self):
        for statement in self:
            if statement.state != 'open':
                raise UserError(_('In order to delete a bank statement, you must first cancel it to delete related journal items.'))
            # Explicitly unlink bank statement lines so it will check that the related journal entries have been deleted first
            statement.line_ids.unlink()
        return super(AccountBankStatement, self).unlink()

    @api.multi
    def open_cashbox_id(self):
        context = dict(self.env.context or {})
        if context.get('cashbox_id'):
            context['active_id'] = self.id
            return {
                'name': _('Cash Control'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'account.bank.statement.cashbox',
                'view_id': self.env.ref('account.view_account_bnk_stmt_cashbox').id,
                'type': 'ir.actions.act_window',
                'res_id': self.env.context.get('cashbox_id'),
                'context': context,
                'target': 'new'
            }

    @api.multi
    def button_cancel(self):
        for statement in self:
            if any(line.journal_entry_ids.ids for line in statement.line_ids):
                raise UserError(_('A statement cannot be canceled when its lines are reconciled.'))
        self.state = 'open'

    @api.multi
    def check_confirm_bank(self):
        if self.journal_type == 'cash' and not self.currency_id.is_zero(self.difference):
            action_rec = self.env['ir.model.data'].xmlid_to_object('account.action_view_account_bnk_stmt_check')
            if action_rec:
                action = action_rec.read([])[0]
                return action
        return self.button_confirm_bank()

    @api.multi
    def button_confirm_bank(self):
        self._balance_check()
        statements = self.filtered(lambda r: r.state == 'open')
        for statement in statements:
            moves = self.env['account.move']
            for st_line in statement.line_ids:
                if st_line.account_id and not st_line.journal_entry_ids.ids:
                    st_line.fast_counterpart_creation()
                elif not st_line.journal_entry_ids.ids:
                    raise UserError(_('All the account entries lines must be processed in order to close the statement.'))
                moves = (moves | st_line.journal_entry_ids)
            if moves:
                moves.post()
            statement.message_post(body=_('Statement %s confirmed, journal items were created.') % (statement.name,))
        statements.link_bank_to_partner()
        statements.write({'state': 'confirm', 'date_done': time.strftime("%Y-%m-%d %H:%M:%S")})

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
    def button_open(self):
        """ Changes statement state to Running."""
        for statement in self:
            if not statement.name:
                context = {'ir_sequence_date', statement.date}
                if statement.journal_id.sequence_id:
                    st_number = statement.journal_id.sequence_id.with_context(context).next_by_id()
                else:
                    SequenceObj = self.env['ir.sequence']
                    st_number = SequenceObj.with_context(context).next_by_code('account.bank.statement')
                statement.name = st_number
            statement.state = 'open'

    @api.multi
    def reconciliation_widget_preprocess(self):
        """ Get statement lines of the specified statements or all unreconciled statement lines and try to automatically reconcile them / find them a partner.
            Return ids of statement lines left to reconcile and other data for the reconciliation widget.
        """
        statements = self
        bsl_obj = self.env['account.bank.statement.line']

        # NB : The field account_id can be used at the statement line creation/import to avoid the reconciliation process on it later on,
        # this is why we filter out statements lines where account_id is set
        st_lines_filter = [('journal_entry_ids', '=', False), ('account_id', '=', False)]
        if statements:
            st_lines_filter += [('statement_id', 'in', statements.ids)]

        # Try to automatically reconcile statement lines
        automatic_reconciliation_entries = []
        st_lines_left = self.env['account.bank.statement.line']
        for st_line in bsl_obj.search(st_lines_filter):
            res = st_line.auto_reconcile()
            if not res:
                st_lines_left = (st_lines_left | st_line)
            else:
                automatic_reconciliation_entries.append(res.ids)

        # Try to set statement line's partner
        for st_line in st_lines_left:
            if st_line.name and not st_line.partner_id:
                additional_domain = [('ref', '=', st_line.name)]
                match_recs = st_line.get_move_lines_for_reconciliation(limit=1, additional_domain=additional_domain, overlook_partner=True)
                if match_recs and match_recs[0].partner_id:
                    st_line.write({'partner_id': match_recs[0].partner_id.id})

        # Collect various informations for the reconciliation widget
        notifications = []
        num_auto_reconciled = len(automatic_reconciliation_entries)
        if num_auto_reconciled > 0:
            auto_reconciled_message = num_auto_reconciled > 1 \
                and _("%d transactions were automatically reconciled.") % num_auto_reconciled \
                or _("1 transaction was automatically reconciled.")
            notifications += [{
                'type': 'info',
                'message': auto_reconciled_message,
                'details': {
                    'name': _("Automatically reconciled items"),
                    'model': 'account.move',
                    'ids': automatic_reconciliation_entries
                }
            }]

        lines = []
        for el in statements:
            lines.extend(el.line_ids.ids)
        lines = list(set(lines))

        return {
            'st_lines_ids': st_lines_left.ids,
            'notifications': notifications,
            'statement_name': len(statements) == 1 and statements[0].name or False,
            'num_already_reconciled_lines': statements and bsl_obj.search_count([('journal_entry_ids', '!=', False), ('id', 'in', lines)]) or 0,
        }

    @api.multi
    def link_bank_to_partner(self):
        for statement in self:
            for st_line in statement.line_ids:
                if st_line.bank_account_id and st_line.partner_id and st_line.bank_account_id.partner_id.id != st_line.partner_id.id:
                    bank_vals = st_line.bank_account_id.onchange_partner_id(st_line.partner_id.id)['value']
                    bank_vals.update({'partner_id': st_line.partner_id.id})
                    st_line.bank_account_id.write(bank_vals)


class AccountBankStatementLine(models.Model):
    _name = "account.bank.statement.line"
    _description = "Bank Statement Line"
    _order = "statement_id desc, sequence"
    _inherit = ['ir.needaction_mixin']

    name = fields.Char(string='Memo', required=True)
    date = fields.Date(required=True, default=lambda self: self._context.get('date', fields.Date.context_today(self)))
    amount = fields.Monetary(digits=0, currency_field='journal_currency_id')
    journal_currency_id = fields.Many2one('res.currency', related='statement_id.currency_id',
        help='Utility field to express amount currency', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    bank_account_id = fields.Many2one('res.partner.bank', string='Bank Account')
    account_id = fields.Many2one('account.account', string='Counterpart Account', domain=[('deprecated', '=', False)],
        help="This technical field can be used at the statement line creation/import time in order to avoid the reconciliation"
             " process on it later on. The statement line will simply create a counterpart on this account")
    statement_id = fields.Many2one('account.bank.statement', string='Statement', index=True, required=True, ondelete='cascade')
    journal_id = fields.Many2one('account.journal', related='statement_id.journal_id', string='Journal', store=True, readonly=True)
    partner_name = fields.Char(help="This field is used to record the third party name when importing bank statement in electronic format,"
             " when the partner doesn't exist yet in the database (or cannot be found).")
    ref = fields.Char(string='Reference')
    note = fields.Text(string='Notes')
    sequence = fields.Integer(index=True, help="Gives the sequence order when displaying a list of bank statement lines.", default=1)
    company_id = fields.Many2one('res.company', related='statement_id.company_id', string='Company', store=True, readonly=True)
    journal_entry_ids = fields.One2many('account.move', 'statement_line_id', 'Journal Entries', copy=False, readonly=True)
    amount_currency = fields.Monetary(help="The amount expressed in an optional other currency if it is a multi-currency entry.")
    currency_id = fields.Many2one('res.currency', string='Currency', help="The optional other currency if it is a multi-currency entry.")

    @api.one
    @api.constrains('amount')
    def _check_amount(self):
        # This constraint could possibly underline flaws in bank statement import (eg. inability to
        # support hacks such as using dummy transactions to give additional informations)
        if self.amount == 0:
            raise ValidationError(_('A transaction can\'t have a 0 amount.'))

    @api.one
    @api.constrains('amount', 'amount_currency')
    def _check_amount_currency(self):
        if self.amount_currency != 0 and self.amount == 0:
            raise ValidationError(_('If "Amount Currency" is specified, then "Amount" must be as well.'))

    @api.multi
    def unlink(self):
        for line in self:
            if line.journal_entry_ids.ids:
                raise UserError(_('In order to delete a bank statement line, you must first cancel it to delete related journal items.'))
        return super(AccountBankStatementLine, self).unlink()

    @api.model
    def _needaction_domain_get(self):
        return [('journal_entry_ids', '=', False), ('account_id', '=', False)]

    @api.multi
    def button_cancel_reconciliation(self):
        # TOCKECK : might not behave as expected in case of reconciliations (match statement line with already
        # registered payment) or partial reconciliations : it will completely remove the existing payment.
        move_recs = self.env['account.move']
        for st_line in self:
            move_recs = (move_recs | st_line.journal_entry_ids)
        if move_recs:
            for move in move_recs:
                move.line_ids.remove_move_reconcile()
            move_recs.write({'statement_line_id': False})
            move_recs.button_cancel()
            move_recs.unlink()

    ####################################################
    # Reconciliation interface methods
    ####################################################

    @api.multi
    def get_data_for_reconciliation_widget(self, excluded_ids=None):
        """ Returns the data required to display a reconciliation widget, for each statement line in self """
        excluded_ids = excluded_ids or []
        ret = []

        for st_line in self:
            aml_recs = st_line.get_reconciliation_proposition(excluded_ids=excluded_ids)
            target_currency = st_line.currency_id or st_line.journal_id.currency_id or st_line.journal_id.company_id.currency_id
            rp = aml_recs.prepare_move_lines_for_reconciliation_widget(target_currency=target_currency, target_date=st_line.date)
            excluded_ids += [move_line['id'] for move_line in rp]
            ret.append({
                'st_line': st_line.get_statement_line_for_reconciliation_widget(),
                'reconciliation_proposition': rp
            })

        return ret

    def get_statement_line_for_reconciliation_widget(self):
        """ Returns the data required by the bank statement reconciliation widget to display a statement line """
        statement_currency = self.journal_id.currency_id or self.journal_id.company_id.currency_id
        if self.amount_currency and self.currency_id:
            amount = self.amount_currency
            amount_currency = self.amount
            amount_currency_str = amount_currency > 0 and amount_currency or -amount_currency
            amount_currency_str = formatLang(self.env, amount_currency_str, currency_obj=statement_currency)
        else:
            amount = self.amount
            amount_currency_str = ""
        amount_str = formatLang(self.env, abs(amount), currency_obj=self.currency_id or statement_currency)

        data = {
            'id': self.id,
            'ref': self.ref,
            'note': self.note or "",
            'name': self.name,
            'date': self.date,
            'amount': amount,
            'amount_str': amount_str,  # Amount in the statement line currency
            'currency_id': self.currency_id.id or statement_currency.id,
            'partner_id': self.partner_id.id,
            'journal_id': self.journal_id.id,
            'statement_id': self.statement_id.id,
            'account_code': self.journal_id.default_debit_account_id.code,
            'account_name': self.journal_id.default_debit_account_id.name,
            'partner_name': self.partner_id.name,
            'communication_partner_name': self.partner_name,
            'amount_currency_str': amount_currency_str,  # Amount in the statement currency
            'has_no_partner': not self.partner_id.id,
        }
        if self.partner_id:
            if amount > 0:
                data['open_balance_account_id'] = self.partner_id.property_account_receivable_id.id
            else:
                data['open_balance_account_id'] = self.partner_id.property_account_payable_id.id

        return data

    @api.multi
    def get_move_lines_for_reconciliation_widget(self, excluded_ids=None, str=False, offset=0, limit=None):
        """ Returns move lines for the bank statement reconciliation widget, formatted as a list of dicts
        """
        aml_recs = self.get_move_lines_for_reconciliation(excluded_ids=excluded_ids, str=str, offset=offset, limit=limit)
        target_currency = self.currency_id or self.journal_id.currency_id or self.journal_id.company_id.currency_id
        return aml_recs.prepare_move_lines_for_reconciliation_widget(target_currency=target_currency, target_date=self.date)

    ####################################################
    # Reconciliation methods
    ####################################################

    def get_move_lines_for_reconciliation(self, excluded_ids=None, str=False, offset=0, limit=None, additional_domain=None, overlook_partner=False):
        """ Return account.move.line records which can be used for bank statement reconciliation.

            :param excluded_ids:
            :param str:
            :param offset:
            :param limit:
            :param additional_domain:
            :param overlook_partner:
        """
        # Domain to fetch registered payments (use case where you encode the payment before you get the bank statement)
        reconciliation_aml_accounts = [self.journal_id.default_credit_account_id.id, self.journal_id.default_debit_account_id.id]
        domain_reconciliation = ['&', ('statement_id', '=', False), ('account_id', 'in', reconciliation_aml_accounts)]

        # Domain to fetch unreconciled payables/receivables (use case where you close invoices/refunds by reconciling your bank statements)
        domain_matching = [('reconciled', '=', False)]
        if self.partner_id.id or overlook_partner:
            domain_matching = expression.AND([domain_matching, [('account_id.internal_type', 'in', ['payable', 'receivable'])]])
        else:
            # TODO : find out what use case this permits (match a check payment, registered on a journal whose account type is other instead of liquidity)
            domain_matching = expression.AND([domain_matching, [('account_id.reconcile', '=', True)]])

        # Let's add what applies to both
        domain = expression.OR([domain_reconciliation, domain_matching])
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

        return self.env['account.move.line'].search(domain, offset=offset, limit=limit, order="date_maturity asc, id asc")

    def _get_domain_maker_move_line_amount(self):
        """ Returns a function that can create the appropriate domain to search on move.line amount based on statement.line currency/amount """
        company_currency = self.journal_id.company_id.currency_id
        st_line_currency = self.currency_id or self.journal_id.currency_id
        currency = (st_line_currency and st_line_currency != company_currency) and st_line_currency.id or False
        field = currency and 'amount_residual_currency' or 'amount_residual'
        precision = st_line_currency and st_line_currency.decimal_places or company_currency.decimal_places

        def ret(comparator, amount, p=precision, f=field, c=currency):
            if comparator == '<':
                if amount < 0:
                    domain = [(f, '<', 0), (f, '>', amount)]
                else:
                    domain = [(f, '>', 0), (f, '<', amount)]
            elif comparator == '=':
                domain = [(f, '=', float_round(amount, precision_digits=p))]
            else:
                raise UserError(_("Programmation error : domain_maker_move_line_amount requires comparator '=' or '<'"))
            domain += [('currency_id', '=', c)]
            return domain

        return ret

    def get_reconciliation_proposition(self, excluded_ids=None):
        """ Returns move lines that constitute the best guess to reconcile a statement line
            Note: it only looks for move lines in the same currency as the statement line.
        """
        # Look for structured communication match
        if self.name:
            overlook_partner = not self.partner_id  # If the transaction has no partner, look for match in payable and receivable account anyway
            domain = [('ref', '=', self.name)]
            match_recs = self.get_move_lines_for_reconciliation(excluded_ids=excluded_ids, limit=2, additional_domain=domain, overlook_partner=overlook_partner)
            if match_recs and len(match_recs) == 1:
                return match_recs

        # How to compare statement line amount and move lines amount
        amount_domain_maker = self._get_domain_maker_move_line_amount()
        amount = self.amount_currency or self.amount

        # Look for a single move line with the same amount
        match_recs = self.get_move_lines_for_reconciliation(excluded_ids=excluded_ids, limit=1, additional_domain=amount_domain_maker('=', amount))
        if match_recs:
            return match_recs

        if not self.partner_id:
            return self.env['account.move.line']

        # Select move lines until their total amount is greater than the statement line amount
        domain = [('reconciled', '=', False)]
        domain += [('account_id.user_type_id.type', '=', amount > 0 and 'receivable' or 'payable')]  # Make sure we can't mix receivable and payable
        domain += amount_domain_maker('<', amount)  # Will also enforce > 0
        mv_lines = self.get_move_lines_for_reconciliation(excluded_ids=excluded_ids, limit=5, additional_domain=domain)
        st_line_currency = self.currency_id or self.journal_id.currency_id or self.journal_id.company_id.currency_id
        ret = self.env['account.move.line']
        total = 0
        for line in mv_lines:
            total += line.currency_id and line.amount_residual_currency or line.amount_residual
            if float_compare(total, abs(amount), precision_digits=st_line_currency.rounding) != -1:
                break
            ret = (ret | line)
        return ret

    def _get_move_lines_for_auto_reconcile(self):
        """ Returns the move lines that the method auto_reconcile can use to try to reconcile the statement line """
        pass

    @api.multi
    def auto_reconcile(self):
        """ Try to automatically reconcile the statement.line ; return the counterpart journal entry/ies if the automatic reconciliation succeeded, False otherwise.
            TODO : this method could be greatly improved and made extensible
        """
        self.ensure_one()
        match_recs = self.env['account.move.line']

        # How to compare statement line amount and move lines amount
        amount_domain_maker = self._get_domain_maker_move_line_amount()
        equal_amount_domain = amount_domain_maker('=', self.amount_currency or self.amount)

        # Look for structured communication match
        if self.name:
            overlook_partner = not self.partner_id  # If the transaction has no partner, look for match in payable and receivable account anyway
            domain = equal_amount_domain + [('ref', '=', self.name)]
            match_recs = self.get_move_lines_for_reconciliation(limit=2, additional_domain=domain, overlook_partner=overlook_partner)
            if match_recs and len(match_recs) != 1:
                return False

        # Look for a single move line with the same partner, the same amount
        if not match_recs:
            if self.partner_id:
                match_recs = self.get_move_lines_for_reconciliation(limit=2, additional_domain=equal_amount_domain)
                if match_recs and len(match_recs) != 1:
                    return False

        if not match_recs:
            return False

        # Now reconcile
        counterpart_aml_dicts = []
        payment_aml_rec = self.env['account.move.line']
        for aml in match_recs:
            if aml.account_id.internal_type == 'liquidity':
                payment_aml_rec = (payment_aml_rec | aml)
            else:
                amount = aml.currency_id and aml.amount_residual_currency or aml.amount_residual
                counterpart_aml_dicts.append({
                    'name': aml.name if aml.name != '/' else aml.move_id.name,
                    'debit': amount < 0 and -amount or 0,
                    'credit': amount > 0 and amount or 0,
                    'move_line': aml
                })

        try:
            with self._cr.savepoint():
                counterpart = self.process_reconciliation(counterpart_aml_dicts=counterpart_aml_dicts, payment_aml_rec=payment_aml_rec)
            return counterpart
        except UserError:
            # A configuration / business logic error that makes it impossible to auto-reconcile should not be raised
            # since automatic reconciliation is just an amenity and the user will get the same exception when manually
            # reconciling. Other types of exception are (hopefully) programmation errors and should cause a stacktrace.
            self.invalidate_cache()
            self.env['account.move'].invalidate_cache()
            self.env['account.move.line'].invalidate_cache()
            return False

    def _prepare_reconciliation_move(self, move_name):
        """ Prepare the dict of values to create the move from a statement line. This method may be overridden to adapt domain logic
            through model inheritance (make sure to call super() to establish a clean extension chain).

           :param char st_line_number: will be used as the name of the generated account move
           :return: dict of value to create() the account.move
        """
        return {
            'statement_line_id': self.id,
            'journal_id': self.statement_id.journal_id.id,
            'date': self.date,
            'name': move_name,
            'ref': self.ref,
        }

    def _prepare_reconciliation_move_line(self, move, amount):
        """ Prepare the dict of values to create the move line from a statement line.

            :param recordset move: the account.move to link the move line
            :param float amount: the amount of transaction that wasn't already reconciled
        """
        company_currency = self.journal_id.company_id.currency_id
        statement_currency = self.journal_id.currency_id or company_currency
        st_line_currency = self.currency_id or statement_currency

        amount_currency = False
        if statement_currency != company_currency or st_line_currency != company_currency:
            # First get the ratio total mount / amount not already reconciled
            if statement_currency == company_currency:
                total_amount = self.amount
            elif st_line_currency == company_currency:
                total_amount = self.amount_currency
            else:
                total_amount = statement_currency.with_context({'date': self.date}).compute(self.amount, company_currency)
            ratio = total_amount / amount
            # Then use it to adjust the statement.line field that correspond to the move.line amount_currency
            if statement_currency != company_currency:
                amount_currency = self.amount * ratio
            elif st_line_currency != company_currency:
                amount_currency = self.amount_currency * ratio
        return {
            'name': self.name,
            'date': self.date,
            'ref': self.ref,
            'move_id': move.id,
            'partner_id': self.partner_id and self.partner_id.id or False,
            'account_id': amount >= 0 \
                and self.statement_id.journal_id.default_credit_account_id.id \
                or self.statement_id.journal_id.default_debit_account_id.id,
            'credit': amount < 0 and -amount or 0.0,
            'debit': amount > 0 and amount or 0.0,
            'statement_id': self.statement_id.id,
            'journal_id': self.statement_id.journal_id.id,
            'currency_id': statement_currency != company_currency and statement_currency.id or (st_line_currency != company_currency and st_line_currency.id or False),
            'amount_currency': amount_currency,
        }

    @api.v7
    def process_reconciliations(self, cr, uid, ids, data, context=None):
        """ Handles data sent from the bank statement reconciliation widget (and can otherwise serve as an old-API bridge)

            :param list of dicts data: must contains the keys 'counterpart_aml_dicts', 'payment_aml_ids' and 'new_aml_dicts',
                whose value is the same as described in process_reconciliation except that ids are used instead of recordsets.
        """
        aml_obj = self.pool['account.move.line']
        for id, datum in zip(ids, data):
            st_line = self.browse(cr, uid, id, context)
            payment_aml_rec = aml_obj.browse(cr, uid, datum.get('payment_aml_ids', []), context)
            for aml_dict in datum.get('counterpart_aml_dicts', []):
                aml_dict['move_line'] = aml_obj.browse(cr, uid, aml_dict['counterpart_aml_id'], context)
                del aml_dict['counterpart_aml_id']
            st_line.process_reconciliation(datum.get('counterpart_aml_dicts', []), payment_aml_rec, datum.get('new_aml_dicts', []))

    def fast_counterpart_creation(self):
        for st_line in self:
            # Technical functionality to automatically reconcile by creating a new move line
            vals = {
                'name': st_line.name,
                'debit': st_line.amount < 0 and -st_line.amount or 0.0,
                'credit': st_line.amount > 0 and st_line.amount or 0.0,
                'account_id': st_line.account_id.id,
            }
            st_line.process_reconciliation(new_aml_dicts=[vals])

    def process_reconciliation(self, counterpart_aml_dicts=None, payment_aml_rec=None, new_aml_dicts=None):
        """ Match statement lines with existing payments (eg. checks) and/or payables/receivables (eg. invoices and refunds) and/or new move lines (eg. write-offs).
            If any new journal item needs to be created (via new_aml_dicts or counterpart_aml_dicts), a new journal entry will be created and will contain those
            items, as well as a journal item for the bank statement line.
            Finally, mark the statement line as reconciled by putting the matched moves ids in the column journal_entry_ids.

            :param (list of dicts) counterpart_aml_dicts: move lines to create to reconcile with existing payables/receivables.
                The expected keys are :
                - 'name'
                - 'debit'
                - 'credit'
                - 'move_line'
                    # The move line to reconcile (partially if specified debit/credit is lower than move line's credit/debit)

            :param (list of recordsets) payment_aml_rec: recordset move lines representing existing payments (which are already fully reconciled)

            :param (list of dicts) new_aml_dicts: move lines to create. The expected keys are :
                - 'name'
                - 'debit'
                - 'credit'
                - 'account_id'
                - (optional) 'tax_ids'
                - (optional) Other account.move.line fields like analytic_account_id or analytics_id

            :returns: The journal entries with which the transaction was matched. If there was at least an entry in counterpart_aml_dicts or new_aml_dicts, this list contains
                the move created by the reconciliation, containing entries for the statement.line (1), the counterpart move lines (0..*) and the new move lines (0..*).
        """
        counterpart_aml_dicts = counterpart_aml_dicts or []
        payment_aml_rec = payment_aml_rec or self.env['account.move.line']
        new_aml_dicts = new_aml_dicts or []

        aml_obj = self.env['account.move.line']

        company_currency = self.journal_id.company_id.currency_id
        statement_currency = self.journal_id.currency_id or company_currency
        st_line_currency = self.currency_id or statement_currency

        counterpart_moves = self.env['account.move']

        # Check and prepare received data
        if self.journal_entry_ids.ids:
            raise UserError(_('The bank statement line was already reconciled.'))
        if any(rec.statement_id for rec in payment_aml_rec):
            raise UserError(_('A selected move line was already reconciled.'))
        for aml_dict in counterpart_aml_dicts:
            if aml_dict['move_line'].reconciled:
                raise UserError(_('A selected move line was already reconciled.'))
            if isinstance(aml_dict['move_line'], (int, long)):
                aml_dict['move_line'] = aml_obj.browse(aml_dict['move_line'])
        for aml_dict in (counterpart_aml_dicts + new_aml_dicts):
            if aml_dict.get('tax_ids') and aml_dict['tax_ids'] and isinstance(aml_dict['tax_ids'][0], (int, long)):
                # Transform the value in the format required for One2many and Many2many fields
                aml_dict['tax_ids'] = map(lambda id: (4, id, None), aml_dict['tax_ids'])

        # Fully reconciled moves are just linked to the bank statement
        for aml_rec in payment_aml_rec:
            aml_rec.write({'statement_id': self.statement_id.id})
            aml_rec.move_id.write({'statement_line_id': self.id})
            counterpart_moves = (counterpart_moves | aml_rec.move_id)

        # Create move line(s). Either matching an existing journal entry (eg. invoice), in which
        # case we reconcile the existing and the new move lines together, or being a write-off.
        if counterpart_aml_dicts or new_aml_dicts:
            st_line_currency = self.currency_id or statement_currency
            st_line_currency_rate = self.currency_id and (self.amount_currency / self.amount) or False

            # Create the move
            move_name = (self.statement_id.name or self.name) + "/" + str(self.sequence)
            move_vals = self._prepare_reconciliation_move(move_name)
            move = self.env['account.move'].create(move_vals)
            move.post()
            counterpart_moves = (counterpart_moves | move)

            # Complete dicts to create both counterpart move lines and write-offs
            to_create = (counterpart_aml_dicts + new_aml_dicts)
            ctx = dict(self._context, date=self.date)
            for aml_dict in to_create:
                aml_dict['move_id'] = move.id
                aml_dict['date'] = self.statement_id.date
                aml_dict['partner_id'] = self.partner_id.id
                aml_dict['journal_id'] = self.journal_id.id
                aml_dict['company_id'] = self.company_id.id
                aml_dict['statement_id'] = self.statement_id.id
                if st_line_currency.id != company_currency.id:
                    aml_dict['amount_currency'] = aml_dict['debit'] - aml_dict['credit']
                    aml_dict['currency_id'] = st_line_currency.id
                    if self.currency_id and statement_currency.id == company_currency.id and st_line_currency_rate:
                        # Statement is in company currency but the transaction is in foreign currency
                        aml_dict['debit'] = company_currency.round(aml_dict['debit'] / st_line_currency_rate)
                        aml_dict['credit'] = company_currency.round(aml_dict['credit'] / st_line_currency_rate)
                    elif self.currency_id and st_line_currency_rate:
                        # Statement is in foreign currency and the transaction is in another one
                        aml_dict['debit'] = statement_currency.with_context(ctx).compute(aml_dict['debit'] / st_line_currency_rate, company_currency)
                        aml_dict['credit'] = statement_currency.with_context(ctx).compute(aml_dict['credit'] / st_line_currency_rate, company_currency)
                    else:
                        # Statement is in foreign currency and no extra currency is given for the transaction
                        aml_dict['debit'] = st_line_currency.with_context(ctx).compute(aml_dict['debit'], company_currency)
                        aml_dict['credit'] = st_line_currency.with_context(ctx).compute(aml_dict['credit'], company_currency)
                elif statement_currency.id != company_currency.id:
                    # Statement is in foreign currency but the transaction is in company currency
                    prorata_factor = (aml_dict['debit'] - aml_dict['credit']) / self.amount_currency
                    aml_dict['amount_currency'] = prorata_factor * self.amount
                    aml_dict['currency_id'] = statement_currency.id

            # Create the move line for the statement line using the total credit/debit of the counterpart
            # This leaves out the amount already reconciled and avoids rounding errors from currency conversion
            st_line_amount = sum(aml_dict['credit'] - aml_dict['debit'] for aml_dict in to_create)
            aml_obj.with_context(check_move_validity=False).create(self._prepare_reconciliation_move_line(move, st_line_amount))

            # Create write-offs
            for aml_dict in new_aml_dicts:
                aml_obj.with_context(check_move_validity=False).create(aml_dict)

            # Create counterpart move lines and reconcile them
            for aml_dict in counterpart_aml_dicts:
                if aml_dict['move_line'].partner_id.id:
                    aml_dict['partner_id'] = aml_dict['move_line'].partner_id.id
                aml_dict['account_id'] = aml_dict['move_line'].account_id.id

                counterpart_move_line = aml_dict.pop('move_line')
                if counterpart_move_line.currency_id and counterpart_move_line.currency_id != company_currency and not aml_dict.get('currency_id'):
                    aml_dict['currency_id'] = counterpart_move_line.currency_id.id
                    aml_dict['amount_currency'] = company_currency.with_context(ctx).compute(aml_dict['debit'] - aml_dict['credit'], counterpart_move_line.currency_id)
                new_aml = aml_obj.with_context(check_move_validity=False).create(aml_dict)
                (new_aml | counterpart_move_line).reconcile()

        counterpart_moves.assert_balanced()
        return counterpart_moves
