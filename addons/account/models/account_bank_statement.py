# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools import float_is_zero, pycompat
from odoo.tools import float_compare, float_round, float_repr
from odoo.tools.misc import formatLang
from odoo.exceptions import UserError, ValidationError

from itertools import groupby

import time

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
        self.all_lines_reconciled = all([line.journal_entry_ids.ids or line.account_id.id for line in self.line_ids if not self.currency_id.is_zero(line.amount)])

    @api.depends('move_line_ids')
    def _get_move_line_count(self):
        for payment in self:
            payment.move_line_count = len(payment.move_line_ids)

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
    accounting_date = fields.Date(string="Accounting Date", help="If set, the accounting entries created during the bank statement reconciliation process will be created at this date.\n"
        "This is useful if the accounting period in which the entries should normally be booked is already closed.")
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
    move_line_count = fields.Integer(compute="_get_move_line_count")

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
                #upon bank statement confirmation, look if some lines have the account_id set. It would trigger a journal entry
                #creation towards that account, with the wanted side-effect to skip that line in the bank reconciliation widget.
                st_line.fast_counterpart_creation()
                if not st_line.account_id and not st_line.journal_entry_ids.ids and not st_line.statement_id.currency_id.is_zero(st_line.amount):
                    raise UserError(_('All the account entries lines must be processed in order to close the statement.'))
                for aml in st_line.journal_entry_ids:
                    moves |= aml.move_id
            if moves:
                moves.filtered(lambda m: m.state != 'posted').post()
            statement.message_post(body=_('Statement %s confirmed, journal items were created.') % (statement.name,))
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


class AccountBankStatementLine(models.Model):
    _name = "account.bank.statement.line"
    _description = "Bank Statement Line"
    _order = "statement_id desc, date desc, sequence, id desc"

    name = fields.Char(string='Label', required=True)
    ref = fields.Char(string='Reference')
    invoice_reference = fields.Char(string='Invoice Reference', store=True,
        help='Decode the label to find an invoice having this reference or number')
    note = fields.Text(string='Notes')
    date = fields.Date(required=True, default=lambda self: self._context.get('date', fields.Date.context_today(self)))
    sequence = fields.Integer(index=True, help="Gives the sequence order when displaying a list of bank statement lines.", default=1)
    amount = fields.Monetary(digits=0, currency_field='journal_currency_id')
    journal_currency_id = fields.Many2one('res.currency', string="Journal's Currency", related='statement_id.currency_id',
        help='Utility field to express amount currency', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    account_number = fields.Char(string='Bank Account Number', help="Technical field used to store the bank account number before its creation, upon the line's processing")
    bank_account_id = fields.Many2one('res.partner.bank', string='Bank Account', help="Bank account that was used in this transaction.")
    account_id = fields.Many2one('account.account', string='Counterpart Account', domain=[('deprecated', '=', False)],
        help="This technical field can be used at the statement line creation/import time in order to avoid the reconciliation"
             " process on it later on. The statement line will simply create a counterpart on this account")
    statement_id = fields.Many2one('account.bank.statement', string='Statement', index=True, required=True, ondelete='cascade')
    journal_id = fields.Many2one('account.journal', related='statement_id.journal_id', string='Journal', store=True, readonly=True)
    partner_name = fields.Char(help="This field is used to record the third party name when importing bank statement in electronic format,"
             " when the partner doesn't exist yet in the database (or cannot be found).")
    company_id = fields.Many2one('res.company', related='statement_id.company_id', string='Company', store=True, readonly=True)
    journal_entry_ids = fields.One2many('account.move.line', 'statement_line_id', 'Journal Items', copy=False, readonly=True)
    amount_currency = fields.Monetary(help="The amount expressed in an optional other currency if it is a multi-currency entry.")
    currency_id = fields.Many2one('res.currency', string='Currency', help="The optional other currency if it is a multi-currency entry.")
    state = fields.Selection(related='statement_id.state', string='Status', readonly=True)
    move_name = fields.Char(string='Journal Entry Name', readonly=True,
        default=False, copy=False,
        help="Technical field holding the number given to the journal entry, automatically set when the statement line is reconciled then stored to set the same number again if the line is cancelled, set to draft and re-processed again.")

    @api.one
    @api.constrains('amount')
    def _check_amount(self):
        # Allow to enter bank statement line with an amount of 0,
        # so that user can enter/import the exact bank statement they have received from their bank in Odoo
        if self.journal_id.type != 'bank' and self.currency_id.is_zero(self.amount):
            raise ValidationError(_('The amount of a cash transaction cannot be 0.'))

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

        # Search some useful data to get a good reconciliation process like partner or invoice_reference.
        if not self._context.get('skip_search_values_for_reconciliation'):
            line.with_context(skip_search_values_for_reconciliation=True)._search_values_for_reconciliation()
        return line

    @api.multi
    def write(self, vals):
        res = super(AccountBankStatementLine, self).write(vals)

        # Search some useful data to get a good reconciliation process like partner or invoice_reference.
        if not self._context.get('skip_search_values_for_reconciliation'):
            self.with_context(skip_search_values_for_reconciliation=True)._search_values_for_reconciliation()
        return res

    @api.multi
    def unlink(self):
        for line in self:
            if line.journal_entry_ids.ids:
                raise UserError(_('In order to delete a bank statement line, you must first cancel it to delete related journal items.'))
        return super(AccountBankStatementLine, self).unlink()

    @api.multi
    def button_cancel_reconciliation(self):
        aml_to_unbind = self.env['account.move.line']
        aml_to_cancel = self.env['account.move.line']
        payment_to_unreconcile = self.env['account.payment']
        payment_to_cancel = self.env['account.payment']
        for st_line in self:
            aml_to_unbind |= st_line.journal_entry_ids
            for line in st_line.journal_entry_ids:
                payment_to_unreconcile |= line.payment_id
                if st_line.move_name and line.payment_id.payment_reference == st_line.move_name:
                    #there can be several moves linked to a statement line but maximum one created by the line itself
                    aml_to_cancel |= line
                    payment_to_cancel |= line.payment_id
        aml_to_unbind = aml_to_unbind - aml_to_cancel

        if aml_to_unbind:
            aml_to_unbind.write({'statement_line_id': False})

        payment_to_unreconcile = payment_to_unreconcile - payment_to_cancel
        if payment_to_unreconcile:
            payment_to_unreconcile.unreconcile()

        if aml_to_cancel:
            aml_to_cancel.remove_move_reconcile()
            moves_to_cancel = aml_to_cancel.mapped('move_id')
            moves_to_cancel.button_cancel()
            moves_to_cancel.unlink()
        if payment_to_cancel:
            payment_to_cancel.unlink()

    @api.multi
    def _search_values_for_reconciliation(self):
        ''' The aim of this method is to fill the partner on the bank statement line if it is missing.
        The search is done through three ways:
        - Try to match a partner using the bank account number (account_number field).
        - Try to match a partner using its name (partner_name field).
        - Try to get the partner is the matching invoice (invoice_reference field).
        '''
        if not self:
            return

        mapping_records = dict((r.id, r) for r in self)

        # Search for matching partners based on partner_name & account_number fields.
        bank_statement_lines_wo_partner = self.filtered(lambda r: not r.partner_id)
        if bank_statement_lines_wo_partner:
            query = '''
                    SELECT
                        st_line.id          AS id,
                        partner.id          AS partner_id,
                        bank.id             AS bank_id,
                        bank.partner_id     AS bank_partner_id
                    FROM account_bank_statement_line st_line
                    LEFT JOIN res_partner partner ON partner.name ILIKE st_line.partner_name
                    LEFT JOIN res_partner_bank bank ON bank.id = st_line.bank_account_id OR bank.acc_number = st_line.account_number
                    WHERE st_line.id IN %s
                '''
            self._cr.execute(query, [tuple(bank_statement_lines_wo_partner.ids)])

            for res in self._cr.dictfetchall():
                line = mapping_records[res['id']]
                vals = {}

                if res['bank_partner_id']:
                    # Found a res.partner.bank record.
                    vals['partner_id'] = res['bank_partner_id']
                    if not line.bank_account_id:
                        vals['bank_account_id'] = res['bank_id']
                elif res['partner_id']:
                    # Found a res.partner record.
                    vals['partner_id'] = res['partner_id']

                if vals:
                    line.write(vals)

        # Clear previous invoice_reference.
        self.write({'invoice_reference': None})

        # Try to retrieve a matching invoice using its number/reference.
        # To do so, the join to the account.invoice is done with 3 conditions:
        # - On the partner_id (if set).
        # - On the string similarity between name and number/reference
        # (e.g. 'inv 2018 - 0042' is similar to 'INV/2018/0042' because the REGEXP_REPLACE result is '20180042').
        # - On the invoice type depending of the statement line amount (cash in or cash out).
        # N.B: '~' means 'Matches regular expression, case sensitive'.
        # N.B2: 'g' in REGEXP_REPLACE is the flag to apply the regex in the whole string.
        # N.B3: We need to join on the statement because the related fields are not yet computed and stored and we need
        # the value of the company_id field.
        query = '''
            SELECT
                st_line.id                  AS id,
                JSON_AGG((
                    invoice.reference,             
                    invoice.number,
                    invoice.partner_id
                ))                          AS agg_invoices
            FROM account_bank_statement_line st_line
            LEFT JOIN account_bank_statement st ON st.id = st_line.statement_id
            LEFT JOIN account_invoice invoice ON (
    
                CASE WHEN st_line.partner_id IS NULL THEN
                    invoice.partner_id IS NOT NULL
                ELSE
                    st_line.partner_id = invoice.partner_id
                END
    
                AND (
                    REGEXP_REPLACE(st_line.name, '[^0-9]', '', 'g') ~ REGEXP_REPLACE(invoice.number, '[^0-9]', '', 'g')
                    OR (
                        invoice.reference IS NOT NULL
                        AND
                        REGEXP_REPLACE(st_line.name, '[^0-9]', '', 'g') ~ REGEXP_REPLACE(invoice.reference, '[^0-9]', '', 'g')                            
                    )
                )
    
                AND CASE WHEN st_line.amount >= 0.0 THEN
                        invoice.type IN ('out_invoice', 'in_refund')
                    ELSE
                        invoice.type IN ('in_invoice', 'out_refund')
                    END                    
            )
            WHERE st_line.id IN %s
            AND invoice.state = 'open'
            AND invoice.company_id = st.company_id
            GROUP BY st_line.id
    
        '''
        self._cr.execute(query, [tuple(self.ids)])

        for res in self._cr.dictfetchall():
            line = mapping_records[res['id']]
            invoices = res['agg_invoices']

            if not invoices:
                continue

            invoice_reference = ','.join(inv['f1'] or inv['f2'] for inv in invoices)

            vals = {
                'invoice_reference': invoice_reference,
                'partner_id': invoices[0]['f3'],
            }

            line.write(vals)

    ####################################################
    # Reconciliation methods
    ####################################################

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

    @api.model
    def _get_matching_amls_query(self, excluded_ids=None):
        ''' Base query used by the matching rules.

        :param excluded_ids:    Account.move.lines to exclude.
        :return:                (query, params)
        '''
        params = [tuple(self.ids)]

        # N.B: The first part of the CASE is about 'blue lines' while the second part is about 'black lines'.
        query = '''
            SELECT
                st_line.id                          AS id,
                aml.id                              AS aml_id,
                aml.currency_id                     AS aml_currency_id,
                aml.amount_residual                 AS aml_amount_residual,
                aml.amount_residual_currency        AS aml_amount_residual_currency
            FROM account_bank_statement_line st_line
            LEFT JOIN account_journal journal       ON journal.id = st_line.journal_id
            LEFT JOIN res_company company           ON company.id = st_line.company_id
            , account_move_line aml
            LEFT JOIN res_company aml_company       ON aml_company.id = aml.company_id
            LEFT JOIN account_account aml_account   ON aml_account.id = aml.account_id
            WHERE st_line.id IN %s
                AND aml.company_id = st_line.company_id
                AND aml.partner_id = st_line.partner_id
                AND aml.statement_id IS NULL
                AND (
                    company.account_bank_reconciliation_start IS NULL
                    OR
                    aml.date > company.account_bank_reconciliation_start
                )
                AND
                (
                    CASE WHEN journal.default_credit_account_id IS NOT NULL
                    AND journal.default_debit_account_id IS NOT NULL
                    THEN
                        (
                            aml.account_id IN (journal.default_credit_account_id, journal.default_debit_account_id)
                            AND aml.payment_id IS NOT NULL
                        )
                        OR
                        (
                            aml_account.reconcile IS TRUE
                            AND aml.reconciled IS FALSE
                        )
                    END
                )
        '''

        if excluded_ids:
            query += 'AND aml.id NOT IN %s'
            params.append(tuple(excluded_ids))
        return query, params

    @api.model
    def _get_matching_amls_invoice_rule(self, excluded_ids=None):
        ''' RULE 1: Match an account.move.line automatically if linked to an invoice having a number or reference quite
        similar.

        To be very useful, the account.bank.statement.lines should be pre-processed in _search_values_for_reconciliation
        to retrieve the right partner and also the matching invoice reference/number.

        This rule automatically match when invoice_reference match when:
        - matching only one invoice.
        - matching multiple invoices but having the same total amount residual.

        :param excluded_ids:    Account.move.lines to exclude.
        :return:                (query, params, automatic_match_func)
        '''

        def automatic_match_func(st_line, fetched_amls):
            # Match only one invoice.
            if len(fetched_amls) == 1:
                return True

            # Match multiple invoices but having the same total amount residual.
            total_residual = sum(aml['aml_currency_id'] and aml['aml_amount_residual_currency'] or aml['aml_amount_residual'] for aml in fetched_amls)
            line_residual = st_line.currency_id and st_line.amount_currency or st_line.amount
            line_currency = st_line.currency_id or st_line.journal_id.currency_id or st_line.company_id.currency_id
            return float_is_zero(total_residual - line_residual, precision_rounding=line_currency.rounding)

        query, params = self._get_matching_amls_query(excluded_ids=excluded_ids)

        # Join the account_invoice table.
        query = query.replace(
            'account_move_line aml',
            '''
            account_move_line aml
            LEFT JOIN account_move move                 ON move.id = aml.move_id
            LEFT JOIN account_invoice invoice           ON invoice.move_name = move.name
            '''
        )

        # Add where clause.
        # N.B: invoice_reference could be a list of invoice reference/number (e.g. 'INV/2018/0001,INV/2018/0002').
        query += '''
            AND CASE WHEN st_line.amount >= 0.0 THEN
                    invoice.type IN ('out_invoice', 'in_refund')
                ELSE
                    invoice.type IN ('in_invoice', 'out_refund')
                END   
            AND invoice.state = 'open'
            AND (
                st_line.invoice_reference LIKE '%%' || invoice.number || '%%'
                OR (
                    invoice.reference IS NOT NULL
                    AND
                    st_line.invoice_reference LIKE '%%' || invoice.reference || '%%'
                )                            
            )
        '''
        return query, params, automatic_match_func

    @api.model
    def _get_matching_amls_amount_rule(self, excluded_ids=None):
        ''' RULE 2: Match one or more account.move.lines automatically if either the statement line has exactly the same amount
        or either the statement line matchs a single line having a greater or equals amount.

        :param excluded_ids:    Account.move.lines to exclude.
        :return:                (query, params, automatic_match_func)
        '''

        def automatic_match_func(st_line, fetched_amls):
            total_residual = sum(aml['aml_currency_id'] and aml['aml_amount_residual_currency'] or aml['aml_amount_residual'] for aml in fetched_amls)
            line_residual = st_line.currency_id and st_line.amount_currency or st_line.amount
            line_currency = st_line.currency_id or st_line.journal_id.currency_id or st_line.company_id.currency_id

            # Match the total residual amount.
            if float_is_zero(total_residual - line_residual, precision_rounding = line_currency.rounding):
                return True

            # Match only one line having a greater residual amount.
            return len(fetched_amls) == 1 and line_residual < total_residual

        query, params = self._get_matching_amls_query(excluded_ids=excluded_ids)

        # Add where clause.
        # N.B: move.line currency_id is either set or either got from the company.
        # N.B2: statement.line currency_id is either set, either got from the journal or either got from the company.
        query += '''
            AND (
                CASE WHEN st_line.currency_id IS NOT NULL AND st_line.currency_id != aml_company.currency_id THEN
                    aml.currency_id = st_line.currency_id
                WHEN journal.currency_id IS NOT NULL AND journal.currency_id != aml_company.currency_id THEN
                    aml.currency_id = journal.currency_id
                ELSE
                    aml.currency_id IS NULL
                END
            )
        '''
        return query, params, automatic_match_func

    @api.multi
    def _get_matching_amls(self, excluded_ids=None):
        ''' Apply reconciliation matching rules in order to find matching account.move.lines.

        :param excluded_ids:    Account.move.lines to exclude.
        :return:                A dictionnary mapping each id with:
            * line:     The account.bank.statement.line record.
            * aml_ids:  The matching account.move.line ids.
        '''
        results = dict((r.id, {'line': r, 'aml_ids': []}) for r in self)

        rules = [
            self._get_matching_amls_invoice_rule,
            self._get_matching_amls_amount_rule,
        ]
        for rule in rules:
            query, params, automatic_match_func = rule(excluded_ids=excluded_ids)
            self._cr.execute(query, params)
            query_res = self._cr.dictfetchall()

            # Map statement line with candidates.
            candidates_map = {}
            for res in query_res:
                candidates_map.setdefault(res['id'], [])
                candidates_map[res['id']].append(res)

            for line_id, fetched_amls in candidates_map.items():
                if automatic_match_func(results[line_id]['line'], fetched_amls):
                    results[line_id]['aml_ids'] = [aml['aml_id'] for aml in fetched_amls]
                    excluded_ids = (excluded_ids or []) + [line_id]
        return results

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
            'journal_id': self.statement_id.journal_id.id,
            'date': self.statement_id.accounting_date or self.date,
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
        # We have several use case here to compare the currency and amount currency of counterpart line to balance the move:
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
            'statement_line_id': self.id,
            'currency_id': statement_currency != company_currency and statement_currency.id or (st_line_currency != company_currency and st_line_currency.id or False),
            'amount_currency': amount_currency,
        }

    def fast_counterpart_creation(self):
        """This function is called when confirming a bank statement and will allow to automatically process lines without
        going in the bank reconciliation widget. By setting an account_id on bank statement lines, it will create a journal
        entry using that account to counterpart the bank account
        """
        for st_line in self:
            # Technical functionality to automatically reconcile by creating a new move line
            if st_line.account_id and not st_line.journal_entry_ids.ids:
                vals = {
                    'name': st_line.name,
                    'debit': st_line.amount < 0 and -st_line.amount or 0.0,
                    'credit': st_line.amount > 0 and st_line.amount or 0.0,
                    'account_id': st_line.account_id.id,
                }
                st_line.process_reconciliation(new_aml_dicts=[vals])

    def _get_communication(self, payment_method_id):
        return self.name or ''

    def process_reconciliation(self, counterpart_aml_dicts=None, payment_aml_rec=None, new_aml_dicts=None):
        """ Match statement lines with existing payments (eg. checks) and/or payables/receivables (eg. invoices and credit notes) and/or new move lines (eg. write-offs).
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
            if isinstance(aml_dict['move_line'], pycompat.integer_types):
                aml_dict['move_line'] = aml_obj.browse(aml_dict['move_line'])
        for aml_dict in (counterpart_aml_dicts + new_aml_dicts):
            if aml_dict.get('tax_ids') and isinstance(aml_dict['tax_ids'][0], pycompat.integer_types):
                # Transform the value in the format required for One2many and Many2many fields
                aml_dict['tax_ids'] = [(4, id, None) for id in aml_dict['tax_ids']]
        if any(line.journal_entry_ids for line in self):
            raise UserError(_('A selected statement line was already reconciled with an account move.'))

        # Fully reconciled moves are just linked to the bank statement
        total = self.amount
        for aml_rec in payment_aml_rec:
            total -= aml_rec.debit - aml_rec.credit
            aml_rec.with_context(check_move_validity=False).write({'statement_line_id': self.id})
            counterpart_moves = (counterpart_moves | aml_rec.move_id)
            if aml_rec.journal_id.post_at_bank_rec and aml_rec.payment_id and aml_rec.move_id.state == 'draft':
                # In case the journal is set to only post payments when performing bank
                # reconciliation, we modify its date and post it.
                aml_rec.move_id.date = self.date
                aml_rec.payment_id.payment_date = self.date
                aml_rec.move_id.post()
                # We check the paid status of the invoices reconciled with this payment
                aml_rec.payment_id.reconciled_invoice_ids.filtered(lambda x: x.state == 'in_payment').write({'state': 'paid'})

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
                    'communication': self._get_communication(payment_methods[0] if payment_methods else False),
                    'name': self.statement_id.name or _("Bank Statement %s") %  self.date,
                })

            # Complete dicts to create both counterpart move lines and write-offs
            to_create = (counterpart_aml_dicts + new_aml_dicts)
            company = self.company_id
            date = self.date or fields.Date.today()
            for aml_dict in to_create:
                aml_dict['move_id'] = move.id
                aml_dict['partner_id'] = self.partner_id.id
                aml_dict['statement_line_id'] = self.id
                if st_line_currency.id != company_currency.id:
                    aml_dict['amount_currency'] = aml_dict['debit'] - aml_dict['credit']
                    aml_dict['currency_id'] = st_line_currency.id
                    if self.currency_id and statement_currency.id == company_currency.id and st_line_currency_rate:
                        # Statement is in company currency but the transaction is in foreign currency
                        aml_dict['debit'] = company_currency.round(aml_dict['debit'] / st_line_currency_rate)
                        aml_dict['credit'] = company_currency.round(aml_dict['credit'] / st_line_currency_rate)
                    elif self.currency_id and st_line_currency_rate:
                        # Statement is in foreign currency and the transaction is in another one
                        aml_dict['debit'] = statement_currency._convert(aml_dict['debit'] / st_line_currency_rate, company_currency, company, date)
                        aml_dict['credit'] = statement_currency._convert(aml_dict['credit'] / st_line_currency_rate, company_currency, company, date)
                    else:
                        # Statement is in foreign currency and no extra currency is given for the transaction
                        aml_dict['debit'] = st_line_currency._convert(aml_dict['debit'], company_currency, company, date)
                        aml_dict['credit'] = st_line_currency._convert(aml_dict['credit'], company_currency, company, date)
                elif statement_currency.id != company_currency.id:
                    # Statement is in foreign currency but the transaction is in company currency
                    prorata_factor = (aml_dict['debit'] - aml_dict['credit']) / self.amount_currency
                    aml_dict['amount_currency'] = prorata_factor * self.amount
                    aml_dict['currency_id'] = statement_currency.id

            # Create write-offs
            for aml_dict in new_aml_dicts:
                aml_dict['payment_id'] = payment and payment.id or False
                aml_obj.with_context(check_move_validity=False).create(aml_dict)

            # Create counterpart move lines and reconcile them
            for aml_dict in counterpart_aml_dicts:
                if aml_dict['move_line'].payment_id:
                    aml_dict['move_line'].write({'statement_line_id': self.id})
                if aml_dict['move_line'].partner_id.id:
                    aml_dict['partner_id'] = aml_dict['move_line'].partner_id.id
                aml_dict['account_id'] = aml_dict['move_line'].account_id.id
                aml_dict['payment_id'] = payment and payment.id or False

                counterpart_move_line = aml_dict.pop('move_line')
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
            payment and payment.write({'payment_reference': move.name})
        elif self.move_name:
            raise UserError(_('Operation not allowed. Since your statement line already received a number (%s), you cannot reconcile it entirely with existing journal entries otherwise it would make a gap in the numbering. You should book an entry and make a regular revert of it in case you want to cancel it.') % (self.move_name))

        #create the res.partner.bank if needed
        if self.account_number and self.partner_id and not self.bank_account_id:
            self.bank_account_id = self.env['res.partner.bank'].create({'acc_number': self.account_number, 'partner_id': self.partner_id.id}).id

        counterpart_moves.assert_balanced()
        return counterpart_moves
