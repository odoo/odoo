# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.tools import float_is_zero
from odoo.tools import float_compare, float_round, float_repr
from odoo.tools.misc import formatLang
from odoo.exceptions import UserError, ValidationError

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
    cashbox_id = fields.Many2one('account.bank.statement.cashbox', string="Cashbox")


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

    @api.multi
    def _is_difference_zero(self):
        for bank_stmt in self:
            bank_stmt.is_difference_zero = float_is_zero(bank_stmt.difference, precision_digits=bank_stmt.currency_id.decimal_places)

    @api.one
    @api.depends('journal_id')
    def _compute_currency(self):
        self.currency_id = self.journal_id.currency_id or self.company_id.currency_id

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
        return self.env['account.journal']

    @api.multi
    def _get_opening_balance(self, journal_id):
        last_bnk_stmt = self.search([('journal_id', '=', journal_id)], limit=1)
        if last_bnk_stmt:
            return last_bnk_stmt.balance_end
        return 0

    @api.multi
    def _set_opening_balance(self, journal_id):
        self.balance_start = self._get_opening_balance(journal_id)

    @api.model
    def _default_opening_balance(self):
        #Search last bank statement and set current opening balance as closing balance of previous one
        journal_id = self._context.get('default_journal_id', False) or self._context.get('journal_id', False)
        if journal_id:
            return self._get_opening_balance(journal_id)
        return 0

    _name = "account.bank.statement"
    _description = "Bank Statement"
    _order = "date desc, id desc"
    _inherit = ['mail.thread']

    name = fields.Char(string='Reference', states={'open': [('readonly', False)]}, copy=False, readonly=True)
    reference = fields.Char(string='External Reference', states={'open': [('readonly', False)]}, copy=False, readonly=True, help="Used to hold the reference of the external mean that created this statement (name of imported file, reference of online synchronization...)")
    date = fields.Date(required=True, states={'confirm': [('readonly', True)]}, index=True, copy=False, default=fields.Date.context_today)
    date_done = fields.Datetime(string="Closed On")
    balance_start = fields.Monetary(string='Starting Balance', states={'confirm': [('readonly', True)]}, default=_default_opening_balance)
    balance_end_real = fields.Monetary('Ending Balance', states={'confirm': [('readonly', True)]})
    state = fields.Selection([('open', 'New'), ('confirm', 'Validated')], string='Status', required=True, readonly=True, copy=False, default='open')
    currency_id = fields.Many2one('res.currency', compute='_compute_currency', oldname='currency', string="Currency")
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
    cashbox_start_id = fields.Many2one('account.bank.statement.cashbox', string="Starting Cashbox")
    cashbox_end_id = fields.Many2one('account.bank.statement.cashbox', string="Ending Cashbox")
    is_difference_zero = fields.Boolean(compute='_is_difference_zero', string='Is zero', help="Check if difference is zero.")

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
            'name': _('Journal Entries'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.mapped('move_line_ids').mapped('move_id').ids)],
            'context': context,
        }

    @api.multi
    def button_open(self):
        """ Changes statement state to Running."""
        for statement in self:
            if not statement.name:
                context = {'ir_sequence_date': statement.date}
                if statement.journal_id.sequence_id:
                    st_number = statement.journal_id.sequence_id.with_context(**context).next_by_id()
                else:
                    SequenceObj = self.env['ir.sequence']
                    st_number = SequenceObj.with_context(**context).next_by_code('account.bank.statement')
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

        sql_query = """SELECT stl.id 
                        FROM account_bank_statement_line stl  
                        WHERE account_id IS NULL AND not exists (select 1 from account_move m where m.statement_line_id = stl.id)
                            AND company_id = %s
                """
        params = (self.env.user.company_id.id,)
        if statements:
            sql_query += ' AND stl.statement_id IN %s'
            params += (tuple(statements.ids),)
        sql_query += ' ORDER BY stl.id'
        self.env.cr.execute(sql_query, params)
        st_lines_left = self.env['account.bank.statement.line'].browse([line.get('id') for line in self.env.cr.dictfetchall()])

        #try to assign partner to bank_statement_line
        stl_to_assign_partner = [stl.id for stl in st_lines_left if not stl.partner_id]
        refs = list(set([st.name for st in st_lines_left if not stl.partner_id]))
        if st_lines_left and stl_to_assign_partner and refs\
           and st_lines_left[0].journal_id.default_credit_account_id\
           and st_lines_left[0].journal_id.default_debit_account_id:

            sql_query = """SELECT aml.partner_id, aml.ref, stl.id
                            FROM account_move_line aml
                                JOIN account_account acc ON acc.id = aml.account_id
                                JOIN account_bank_statement_line stl ON aml.ref = stl.name
                            WHERE (aml.company_id = %s 
                                AND aml.partner_id IS NOT NULL) 
                                AND (
                                    (aml.statement_id IS NULL AND aml.account_id IN %s) 
                                    OR 
                                    (acc.internal_type IN ('payable', 'receivable') AND aml.reconciled = false)
                                    )
                                AND aml.ref IN %s
                                """
            params = (self.env.user.company_id.id, (st_lines_left[0].journal_id.default_credit_account_id.id, st_lines_left[0].journal_id.default_debit_account_id.id), tuple(refs))
            if statements:
                sql_query += 'AND stl.id IN %s'
                params += (tuple(stl_to_assign_partner),)
            self.env.cr.execute(sql_query, params)
            results = self.env.cr.dictfetchall()
            st_line = self.env['account.bank.statement.line']
            for line in results:
                st_line.browse(line.get('id')).write({'partner_id': line.get('partner_id')})

        return {
            'st_lines_ids': st_lines_left.ids,
            'notifications': [],
            'statement_name': len(statements) == 1 and statements[0].name or False,
            'num_already_reconciled_lines': 0,
        }

    @api.multi
    def link_bank_to_partner(self):
        for statement in self:
            for st_line in statement.line_ids:
                if st_line.bank_account_id and st_line.partner_id and st_line.bank_account_id.partner_id != st_line.partner_id:
                    st_line.bank_account_id.partner_id = st_line.partner_id


class AccountBankStatementLine(models.Model):
    _name = "account.bank.statement.line"
    _description = "Bank Statement Line"
    _order = "statement_id desc, sequence, id desc"
    _inherit = ['ir.needaction_mixin']

    name = fields.Char(string='Label', required=True)
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
    state = fields.Selection(related='statement_id.state' , string='Status', readonly=True)
    move_name = fields.Char(string='Journal Entry Name', readonly=True,
        default=False, copy=False,
        help="Technical field holding the number given to the journal entry, automatically set when the statement line is reconciled then stored to set the same number again if the line is cancelled, set to draft and re-processed again.")

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

    @api.model
    def create(self, vals):
        line = super(AccountBankStatementLine, self).create(vals)
        # The most awesome fix you will ever see is below.
        # Explanation: during a 'create', the 'convert_to_cache' method is not called. Moreover, at
        # that point 'journal_currency_id' is not yet known since it is a related field. It means
        # that the 'amount' field will not be properly rounded. The line below triggers a write on
        # the 'amount' field, which will trigger the 'convert_to_cache' method, and ultimately round
        # the field correctly.
        # This is obviously an awful workaround, but at the time of writing, the ORM does not
        # provide a clean mechanism to fix the issue.
        line.amount = line.amount
        return line

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
        moves_to_cancel = self.env['account.move']
        payment_to_unreconcile = self.env['account.payment']
        payment_to_cancel = self.env['account.payment']
        for st_line in self:
            moves_to_unbind = st_line.journal_entry_ids
            for move in st_line.journal_entry_ids:
                for line in move.line_ids:
                    payment_to_unreconcile |= line.payment_id
                    if st_line.move_name and line.payment_id.payment_reference == st_line.move_name:
                        #there can be several moves linked to a statement line but maximum one created by the line itself
                        moves_to_cancel |= move
                        payment_to_cancel |= line.payment_id

            moves_to_unbind = moves_to_unbind - moves_to_cancel

            if moves_to_unbind:
                moves_to_unbind.write({'statement_line_id': False})
                for move in moves_to_unbind:
                    move.line_ids.filtered(lambda x: x.statement_id == st_line.statement_id).write({'statement_id': False})

        payment_to_unreconcile = payment_to_unreconcile - payment_to_cancel
        if payment_to_unreconcile:
            payment_to_unreconcile.unreconcile()

        if moves_to_cancel:
            for move in moves_to_cancel:
                move.line_ids.remove_move_reconcile()
            moves_to_cancel.button_cancel()
            moves_to_cancel.unlink()
        if payment_to_cancel:
            payment_to_cancel.unlink()

    ####################################################
    # Reconciliation interface methods
    ####################################################
    @api.multi
    def reconciliation_widget_auto_reconcile(self, num_already_reconciled_lines):
        automatic_reconciliation_entries = self.env['account.bank.statement.line']
        unreconciled = self.env['account.bank.statement.line']
        for stl in self:
            res = stl.auto_reconcile()
            if res:
                automatic_reconciliation_entries += stl
            else:
                unreconciled += stl

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
                    'ids': automatic_reconciliation_entries.mapped('journal_entry_ids').ids
                }
            }]
        return {
            'st_lines_ids': unreconciled.ids,
            'notifications': notifications,
            'statement_name': False,
            'num_already_reconciled_lines': num_auto_reconciled + num_already_reconciled_lines,
        }

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
        # Blue lines = payment on bank account not assigned to a statement yet
        reconciliation_aml_accounts = [self.journal_id.default_credit_account_id.id, self.journal_id.default_debit_account_id.id]
        domain_reconciliation = ['&', '&', ('statement_id', '=', False), ('account_id', 'in', reconciliation_aml_accounts), ('payment_id','<>', False)]

        # Black lines = unreconciled & (not linked to a payment or open balance created by statement
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

    def _get_common_sql_query(self, overlook_partner = False, excluded_ids = None, split = False):
        acc_type = "acc.internal_type IN ('payable', 'receivable')" if (self.partner_id or overlook_partner) else "acc.reconcile = true"
        select_clause = "SELECT aml.id "
        from_clause = "FROM account_move_line aml JOIN account_account acc ON acc.id = aml.account_id "
        account_clause = ''
        if self.journal_id.default_credit_account_id and self.journal_id.default_debit_account_id:
            account_clause = "(aml.statement_id IS NULL AND aml.account_id IN %(account_payable_receivable)s AND aml.payment_id IS NOT NULL) OR"
        where_clause = """WHERE aml.company_id = %(company_id)s
                          AND (
                                    """ + account_clause + """
                                    ("""+acc_type+""" AND aml.reconciled = false)
                          )"""
        where_clause = where_clause + ' AND aml.partner_id = %(partner_id)s' if self.partner_id else where_clause
        where_clause = where_clause + ' AND aml.id NOT IN %(excluded_ids)s' if excluded_ids else where_clause
        if split:
            return select_clause, from_clause, where_clause
        return select_clause + from_clause + where_clause

    def get_reconciliation_proposition(self, excluded_ids=None):
        """ Returns move lines that constitute the best guess to reconcile a statement line
            Note: it only looks for move lines in the same currency as the statement line.
        """
        self.ensure_one()
        if not excluded_ids:
            excluded_ids = []
        amount = self.amount_currency or self.amount
        company_currency = self.journal_id.company_id.currency_id
        st_line_currency = self.currency_id or self.journal_id.currency_id
        currency = (st_line_currency and st_line_currency != company_currency) and st_line_currency.id or False
        precision = st_line_currency and st_line_currency.decimal_places or company_currency.decimal_places
        params = {'company_id': self.env.user.company_id.id,
                    'account_payable_receivable': (self.journal_id.default_credit_account_id.id, self.journal_id.default_debit_account_id.id),
                    'amount': float_repr(float_round(amount, precision_digits=precision), precision_digits=precision),
                    'partner_id': self.partner_id.id,
                    'excluded_ids': tuple(excluded_ids),
                    'ref': self.name,
                    }
        # Look for structured communication match
        if self.name:
            add_to_select = ", CASE WHEN aml.ref = %(ref)s THEN 1 ELSE 2 END as temp_field_order "
            add_to_from = " JOIN account_move m ON m.id = aml.move_id "
            select_clause, from_clause, where_clause = self._get_common_sql_query(overlook_partner=True, excluded_ids=excluded_ids, split=True)
            sql_query = select_clause + add_to_select + from_clause + add_to_from + where_clause
            sql_query += " AND (aml.ref= %(ref)s or m.name = %(ref)s) \
                    ORDER BY temp_field_order, date_maturity asc, aml.id asc"
            self.env.cr.execute(sql_query, params)
            results = self.env.cr.fetchone()
            if results:
                return self.env['account.move.line'].browse(results[0])

        # Look for a single move line with the same amount
        field = currency and 'amount_residual_currency' or 'amount_residual'
        liquidity_field = currency and 'amount_currency' or amount > 0 and 'debit' or 'credit'
        liquidity_amt_clause = currency and '%(amount)s::numeric' or 'abs(%(amount)s::numeric)'
        sql_query = self._get_common_sql_query(excluded_ids=excluded_ids) + \
                " AND ("+field+" = %(amount)s::numeric OR (acc.internal_type = 'liquidity' AND "+liquidity_field+" = " + liquidity_amt_clause + ")) \
                ORDER BY date_maturity asc, aml.id asc LIMIT 1"
        self.env.cr.execute(sql_query, params)
        results = self.env.cr.fetchone()
        if results:
            return self.env['account.move.line'].browse(results[0])

        return self.env['account.move.line']

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

        amount = self.amount_currency or self.amount
        company_currency = self.journal_id.company_id.currency_id
        st_line_currency = self.currency_id or self.journal_id.currency_id
        currency = (st_line_currency and st_line_currency != company_currency) and st_line_currency.id or False
        precision = st_line_currency and st_line_currency.decimal_places or company_currency.decimal_places
        params = {'company_id': self.env.user.company_id.id,
                    'account_payable_receivable': (self.journal_id.default_credit_account_id.id, self.journal_id.default_debit_account_id.id),
                    'amount': float_round(amount, precision_digits=precision),
                    'partner_id': self.partner_id.id,
                    'ref': self.name,
                    }
        field = currency and 'amount_residual_currency' or 'amount_residual'
        liquidity_field = currency and 'amount_currency' or amount > 0 and 'debit' or 'credit'
        # Look for structured communication match
        if self.name:
            sql_query = self._get_common_sql_query() + \
                " AND aml.ref = %(ref)s AND ("+field+" = %(amount)s OR (acc.internal_type = 'liquidity' AND "+liquidity_field+" = %(amount)s)) \
                ORDER BY date_maturity asc, aml.id asc"
            self.env.cr.execute(sql_query, params)
            match_recs = self.env.cr.dictfetchall()
            if len(match_recs) > 1:
                return False

        # Look for a single move line with the same partner, the same amount
        if not match_recs:
            if self.partner_id:
                sql_query = self._get_common_sql_query() + \
                " AND ("+field+" = %(amount)s OR (acc.internal_type = 'liquidity' AND "+liquidity_field+" = %(amount)s)) \
                ORDER BY date_maturity asc, aml.id asc"
                self.env.cr.execute(sql_query, params)
                match_recs = self.env.cr.dictfetchall()
                if len(match_recs) > 1:
                    return False

        if not match_recs:
            return False

        match_recs = self.env['account.move.line'].browse([aml.get('id') for aml in match_recs])
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

    def _prepare_reconciliation_move(self, move_ref):
        """ Prepare the dict of values to create the move from a statement line. This method may be overridden to adapt domain logic
            through model inheritance (make sure to call super() to establish a clean extension chain).

           :param char move_ref: will be used as the reference of the generated account move
           :return: dict of value to create() the account.move
        """
        ref = move_ref or ''
        if self.ref:
            ref = move_ref + ' - ' + self.ref if move_ref else self.ref
        data = {
            'statement_line_id': self.id,
            'journal_id': self.statement_id.journal_id.id,
            'date': self.date,
            'ref': ref,
        }
        if self.move_name:
            data.update(name=self.move_name)
        return data

    def _prepare_reconciliation_move_line(self, move, amount):
        """ Prepare the dict of values to balance the move.

            :param recordset move: the account.move to link the move line
            :param float amount: the amount of transaction that wasn't already reconciled
        """
        company_currency = self.journal_id.company_id.currency_id
        statement_currency = self.journal_id.currency_id or company_currency
        st_line_currency = self.currency_id or statement_currency
        amount_currency = False
        st_line_currency_rate = self.currency_id and (self.amount_currency / self.amount) or False
        # We have several use case here to compure the currency and amount currency of counterpart line to balance the move:
        if st_line_currency != company_currency and st_line_currency == statement_currency:
            # company in currency A, statement in currency B and transaction in currency B
            # counterpart line must have currency B and correct amount is inverse of already existing lines
            amount_currency = -sum([x.amount_currency for x in move.line_ids])
        elif st_line_currency != company_currency and statement_currency == company_currency:
            # company in currency A, statement in currency A and transaction in currency B
            # counterpart line must have currency B and correct amount is inverse of already existing lines
            amount_currency = -sum([x.amount_currency for x in move.line_ids])
        elif st_line_currency != company_currency and st_line_currency != statement_currency:
            # company in currency A, statement in currency B and transaction in currency C
            # counterpart line must have currency B and use rate between B and C to compute correct amount
            amount_currency = -sum([x.amount_currency for x in move.line_ids])/st_line_currency_rate
        elif st_line_currency == company_currency and statement_currency != company_currency:
            # company in currency A, statement in currency B and transaction in currency A
            # counterpart line must have currency B and amount is computed using the rate between A and B
            amount_currency = amount/st_line_currency_rate
        
        # last case is company in currency A, statement in currency A and transaction in currency A
        # and in this case counterpart line does not need any second currency nor amount_currency

        return {
            'name': self.name,
            'move_id': move.id,
            'partner_id': self.partner_id and self.partner_id.id or False,
            'account_id': amount >= 0 \
                and self.statement_id.journal_id.default_credit_account_id.id \
                or self.statement_id.journal_id.default_debit_account_id.id,
            'credit': amount < 0 and -amount or 0.0,
            'debit': amount > 0 and amount or 0.0,
            'statement_id': self.statement_id.id,
            'currency_id': statement_currency != company_currency and statement_currency.id or (st_line_currency != company_currency and st_line_currency.id or False),
            'amount_currency': amount_currency,
        }

    @api.multi
    def process_reconciliations(self, data):
        """ Handles data sent from the bank statement reconciliation widget (and can otherwise serve as an old-API bridge)

            :param list of dicts data: must contains the keys 'counterpart_aml_dicts', 'payment_aml_ids' and 'new_aml_dicts',
                whose value is the same as described in process_reconciliation except that ids are used instead of recordsets.
        """
        AccountMoveLine = self.env['account.move.line']
        for st_line, datum in zip(self, data):
            payment_aml_rec = AccountMoveLine.browse(datum.get('payment_aml_ids', []))
            for aml_dict in datum.get('counterpart_aml_dicts', []):
                aml_dict['move_line'] = AccountMoveLine.browse(aml_dict['counterpart_aml_id'])
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

            :param self: browse collection of records that are supposed to have no accounting entries already linked.
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
        if any(line.journal_entry_ids for line in self):
            raise UserError(_('A selected statement line was already reconciled with an account move.'))

        # Fully reconciled moves are just linked to the bank statement
        total = self.amount
        for aml_rec in payment_aml_rec:
            total -= aml_rec.debit-aml_rec.credit
            aml_rec.write({'statement_id': self.statement_id.id})
            aml_rec.move_id.write({'statement_line_id': self.id})
            counterpart_moves = (counterpart_moves | aml_rec.move_id)

        # Create move line(s). Either matching an existing journal entry (eg. invoice), in which
        # case we reconcile the existing and the new move lines together, or being a write-off.
        if counterpart_aml_dicts or new_aml_dicts:
            st_line_currency = self.currency_id or statement_currency
            st_line_currency_rate = self.currency_id and (self.amount_currency / self.amount) or False

            # Create the move
            self.sequence = self.statement_id.line_ids.ids.index(self.id) + 1
            move_vals = self._prepare_reconciliation_move(self.statement_id.name)
            move = self.env['account.move'].create(move_vals)
            counterpart_moves = (counterpart_moves | move)

            # Create The payment
            payment = self.env['account.payment']
            if abs(total)>0.00001:
                partner_id = self.partner_id and self.partner_id.id or False
                partner_type = False
                if partner_id:
                    if total < 0:
                        partner_type = 'supplier'
                    else:
                        partner_type = 'customer'

                payment_methods = (total>0) and self.journal_id.inbound_payment_method_ids or self.journal_id.outbound_payment_method_ids
                currency = self.journal_id.currency_id or self.company_id.currency_id
                payment = self.env['account.payment'].create({
                    'payment_method_id': payment_methods and payment_methods[0].id or False,
                    'payment_type': total >0 and 'inbound' or 'outbound',
                    'partner_id': self.partner_id and self.partner_id.id or False,
                    'partner_type': partner_type,
                    'journal_id': self.statement_id.journal_id.id,
                    'payment_date': self.date,
                    'state': 'reconciled',
                    'currency_id': currency.id,
                    'amount': abs(total),
                    'communication': self.name or '',
                    'name': self.statement_id.name,
                })

            # Complete dicts to create both counterpart move lines and write-offs
            to_create = (counterpart_aml_dicts + new_aml_dicts)
            ctx = dict(self._context, date=self.date)
            for aml_dict in to_create:
                aml_dict['move_id'] = move.id
                aml_dict['partner_id'] = self.partner_id.id
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

            # Create write-offs
            # When we register a payment on an invoice, the write-off line contains the amount
            # currency if all related invoices have the same currency. We apply the same logic in
            # the manual reconciliation.
            counterpart_aml = self.env['account.move.line']
            for aml_dict in counterpart_aml_dicts:
                counterpart_aml |= aml_dict.get('move_line', self.env['account.move.line'])
            new_aml_currency = False
            if counterpart_aml\
                    and len(counterpart_aml.mapped('currency_id')) == 1\
                    and counterpart_aml[0].currency_id\
                    and counterpart_aml[0].currency_id != company_currency:
                new_aml_currency = counterpart_aml[0].currency_id
            for aml_dict in new_aml_dicts:
                aml_dict['payment_id'] = payment and payment.id or False
                if new_aml_currency and not aml_dict.get('currency_id'):
                    aml_dict['currency_id'] = new_aml_currency.id
                    aml_dict['amount_currency'] = company_currency.with_context(ctx).compute(aml_dict['debit'] - aml_dict['credit'], new_aml_currency)
                aml_obj.with_context(check_move_validity=False, apply_taxes=True).create(aml_dict)

            # Create counterpart move lines and reconcile them
            for aml_dict in counterpart_aml_dicts:
                if aml_dict['move_line'].partner_id.id:
                    aml_dict['partner_id'] = aml_dict['move_line'].partner_id.id
                aml_dict['account_id'] = aml_dict['move_line'].account_id.id
                aml_dict['payment_id'] = payment and payment.id or False

                counterpart_move_line = aml_dict.pop('move_line')
                if counterpart_move_line.currency_id and counterpart_move_line.currency_id != company_currency and not aml_dict.get('currency_id'):
                    aml_dict['currency_id'] = counterpart_move_line.currency_id.id
                    aml_dict['amount_currency'] = company_currency.with_context(ctx).compute(aml_dict['debit'] - aml_dict['credit'], counterpart_move_line.currency_id)
                new_aml = aml_obj.with_context(check_move_validity=False).create(aml_dict)

                (new_aml | counterpart_move_line).reconcile()

            # Balance the move
            st_line_amount = -sum([x.balance for x in move.line_ids])
            aml_dict = self._prepare_reconciliation_move_line(move, st_line_amount)
            aml_dict['payment_id'] = payment and payment.id or False
            aml_obj.with_context(check_move_validity=False).create(aml_dict)

            move.post()
            #record the move name on the statement line to be able to retrieve it in case of unreconciliation
            self.write({'move_name': move.name})
            payment.write({'payment_reference': move.name})
        elif self.move_name:
            raise UserError(_('Operation not allowed. Since your statement line already received a number, you cannot reconcile it entirely with existing journal entries otherwise it would make a gap in the numbering. You should book an entry and make a regular revert of it in case you want to cancel it.'))
        counterpart_moves.assert_balanced()
        return counterpart_moves
