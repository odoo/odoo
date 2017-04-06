# -*- coding: utf-8 -*-

import time
from collections import OrderedDict
from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.tools.misc import formatLang
from odoo.tools import float_is_zero, float_compare
from odoo.tools.safe_eval import safe_eval
from lxml import etree

#----------------------------------------------------------
# Entries
#----------------------------------------------------------


class AccountMove(models.Model):
    _name = "account.move"
    _description = "Account Entry"
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    @api.multi
    @api.depends('name', 'state')
    def name_get(self):
        result = []
        for move in self:
            if move.state == 'draft':
                name = '* ' + str(move.id)
            else:
                name = move.name
            result.append((move.id, name))
        return result

    @api.multi
    @api.depends('line_ids.debit', 'line_ids.credit')
    def _amount_compute(self):
        for move in self:
            total = 0.0
            for line in move.line_ids:
                total += line.debit
            move.amount = total

    @api.depends('line_ids.debit', 'line_ids.credit', 'line_ids.matched_debit_ids.amount', 'line_ids.matched_credit_ids.amount', 'line_ids.account_id.user_type_id.type')
    def _compute_matched_percentage(self):
        """Compute the percentage to apply for cash basis method. This value is relevant only for moves that
        involve journal items on receivable or payable accounts.
        """
        for move in self:
            total_amount = 0.0
            total_reconciled = 0.0
            for line in move.line_ids:
                if line.account_id.user_type_id.type in ('receivable', 'payable'):
                    amount = abs(line.debit - line.credit)
                    total_amount += amount
                    for partial_line in (line.matched_debit_ids + line.matched_credit_ids):
                        total_reconciled += partial_line.amount
            if float_is_zero(total_amount, precision_rounding=move.currency_id.rounding):
                move.matched_percentage = 1.0
            else:
                move.matched_percentage = total_reconciled / total_amount

    @api.one
    @api.depends('company_id')
    def _compute_currency(self):
        self.currency_id = self.company_id.currency_id or self.env.user.company_id.currency_id

    @api.multi
    def _get_default_journal(self):
        if self.env.context.get('default_journal_type'):
            return self.env['account.journal'].search([('type', '=', self.env.context['default_journal_type'])], limit=1).id

    @api.multi
    @api.depends('line_ids.partner_id')
    def _compute_partner_id(self):
        for move in self:
            partner = move.line_ids.mapped('partner_id')
            move.partner_id = partner.id if len(partner) == 1 else False

    name = fields.Char(string='Number', required=True, copy=False, default='/')
    ref = fields.Char(string='Reference', copy=False)
    date = fields.Date(required=True, states={'posted': [('readonly', True)]}, index=True, default=fields.Date.context_today)
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, states={'posted': [('readonly', True)]}, default=_get_default_journal)
    currency_id = fields.Many2one('res.currency', compute='_compute_currency', store=True, string="Currency")
    state = fields.Selection([('draft', 'Unposted'), ('posted', 'Posted')], string='Status',
      required=True, readonly=True, copy=False, default='draft',
      help='All manually created new journal entries are usually in the status \'Unposted\', '
           'but you can set the option to skip that status on the related journal. '
           'In that case, they will behave as journal entries automatically created by the '
           'system on document validation (invoices, bank statements...) and will be created '
           'in \'Posted\' status.')
    line_ids = fields.One2many('account.move.line', 'move_id', string='Journal Items',
        states={'posted': [('readonly', True)]}, copy=True)
    partner_id = fields.Many2one('res.partner', compute='_compute_partner_id', string="Partner", store=True, readonly=True)
    amount = fields.Monetary(compute='_amount_compute', store=True)
    narration = fields.Text(string='Internal Note')
    company_id = fields.Many2one('res.company', related='journal_id.company_id', string='Company', store=True, readonly=True,
        default=lambda self: self.env.user.company_id)
    matched_percentage = fields.Float('Percentage Matched', compute='_compute_matched_percentage', digits=0, store=True, readonly=True, help="Technical field used in cash basis method")
    # Dummy Account field to search on account.move by account_id
    dummy_account_id = fields.Many2one('account.account', related='line_ids.account_id', string='Account', store=False)
    tax_cash_basis_rec_id = fields.Many2one(
        'account.partial.reconcile',
        string='Tax Cash Basis Entry of',
        help="Technical field used to keep track of the tax cash basis reconciliation."
        "This is needed when cancelling the source: it will post the inverse journal entry to cancel that part too.")

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(AccountMove, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if self._context.get('vat_domain'):
            res['fields']['line_ids']['views']['tree']['fields']['tax_line_id']['domain'] = [('tag_ids', 'in', [self.env.ref(self._context.get('vat_domain')).id])]
        return res

    @api.model
    def create(self, vals):
        move = super(AccountMove, self.with_context(check_move_validity=False, partner_id=vals.get('partner_id'))).create(vals)
        move.assert_balanced()
        return move

    @api.multi
    def write(self, vals):
        if 'line_ids' in vals:
            res = super(AccountMove, self.with_context(check_move_validity=False)).write(vals)
            self.assert_balanced()
        else:
            res = super(AccountMove, self).write(vals)
        return res

    @api.multi
    def post(self):
        invoice = self._context.get('invoice', False)
        self._post_validate()
        for move in self:
            move.line_ids.create_analytic_lines()
            if move.name == '/':
                new_name = False
                journal = move.journal_id

                if invoice and invoice.move_name and invoice.move_name != '/':
                    new_name = invoice.move_name
                else:
                    if journal.sequence_id:
                        # If invoice is actually refund and journal has a refund_sequence then use that one or use the regular one
                        sequence = journal.sequence_id
                        if invoice and invoice.type in ['out_refund', 'in_refund'] and journal.refund_sequence:
                            if not journal.refund_sequence_id:
                                raise UserError(_('Please define a sequence for the refunds'))
                            sequence = journal.refund_sequence_id
                                                            
                        new_name = sequence.with_context(ir_sequence_date=move.date).next_by_id()
                    else:
                        raise UserError(_('Please define a sequence on the journal.'))

                if new_name:
                    move.name = new_name
        return self.write({'state': 'posted'})

    @api.multi
    def button_cancel(self):
        for move in self:
            if not move.journal_id.update_posted:
                raise UserError(_('You cannot modify a posted entry of this journal.\nFirst you should set the journal to allow cancelling entries.'))
        if self.ids:
            self._check_lock_date()
            self._cr.execute('UPDATE account_move '\
                       'SET state=%s '\
                       'WHERE id IN %s', ('draft', tuple(self.ids),))
            self.invalidate_cache()
        self._check_lock_date()
        return True

    @api.multi
    def unlink(self):
        for move in self:
            #check the lock date + check if some entries are reconciled
            move.line_ids._update_check()
            move.line_ids.unlink()
        return super(AccountMove, self).unlink()

    @api.multi
    def _post_validate(self):
        for move in self:
            if move.line_ids:
                if not all([x.company_id.id == move.company_id.id for x in move.line_ids]):
                    raise UserError(_("Cannot create moves for different companies."))
        self.assert_balanced()
        return self._check_lock_date()

    @api.multi
    def _check_lock_date(self):
        for move in self:
            lock_date = max(move.company_id.period_lock_date, move.company_id.fiscalyear_lock_date)
            if self.user_has_groups('account.group_account_manager'):
                lock_date = move.company_id.fiscalyear_lock_date
            if move.date <= lock_date:
                if self.user_has_groups('account.group_account_manager'):
                    message = _("You cannot add/modify entries prior to and inclusive of the lock date %s") % (lock_date)
                else:
                    message = _("You cannot add/modify entries prior to and inclusive of the lock date %s. Check the company settings or ask someone with the 'Adviser' role") % (lock_date)
                raise UserError(message)
        return True

    @api.multi
    def assert_balanced(self):
        if not self.ids:
            return True
        prec = self.env['decimal.precision'].precision_get('Account')

        self._cr.execute("""\
            SELECT      move_id
            FROM        account_move_line
            WHERE       move_id in %s
            GROUP BY    move_id
            HAVING      abs(sum(debit) - sum(credit)) > %s
            """, (tuple(self.ids), 10 ** (-max(5, prec))))
        if len(self._cr.fetchall()) != 0:
            raise UserError(_("Cannot create unbalanced journal entry."))
        return True

    @api.multi
    def _reverse_move(self, date=None, journal_id=None):
        self.ensure_one()
        reversed_move = self.copy(default={
            'date': date,
            'journal_id': journal_id.id if journal_id else self.journal_id.id,
            'ref': _('reversal of: ') + self.name})
        for acm_line in reversed_move.line_ids:
            acm_line.with_context(check_move_validity=False).write({
                'debit': acm_line.credit,
                'credit': acm_line.debit,
                'amount_currency': -acm_line.amount_currency
            })
        return reversed_move

    @api.multi
    def reverse_moves(self, date=None, journal_id=None):
        date = date or fields.Date.today()
        reversed_moves = self.env['account.move']
        for ac_move in self:
            reversed_move = ac_move._reverse_move(date=date,
                                                  journal_id=journal_id)
            reversed_moves |= reversed_move
            #unreconcile all lines reversed
            aml = ac_move.line_ids.filtered(lambda x: x.account_id.reconcile)
            aml.remove_move_reconcile()
            #reconcile together the reconciliable aml and their newly created counterpart
            for account in [x.account_id for x in aml]:
                to_rec = aml.filtered(lambda y: y.account_id == account)
                to_rec |= reversed_move.line_ids.filtered(lambda y: y.account_id == account)
                to_rec.reconcile()
        if reversed_moves:
            reversed_moves._post_validate()
            reversed_moves.post()
            return [x.id for x in reversed_moves]
        return []

    @api.multi
    def open_reconcile_view(self):
        return self.line_ids.open_reconcile_view()


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _description = "Journal Item"
    _order = "date desc, id desc"

    @api.model_cr
    def init(self):
        """ change index on partner_id to a multi-column index on (partner_id, ref), the new index will behave in the
            same way when we search on partner_id, with the addition of being optimal when having a query that will
            search on partner_id and ref at the same time (which is the case when we open the bank reconciliation widget)
        """
        cr = self._cr
        cr.execute('DROP INDEX IF EXISTS account_move_line_partner_id_index')
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('account_move_line_partner_id_ref_idx',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX account_move_line_partner_id_ref_idx ON account_move_line (partner_id, ref)')

    @api.depends('debit', 'credit', 'amount_currency', 'currency_id', 'matched_debit_ids', 'matched_credit_ids', 'matched_debit_ids.amount', 'matched_credit_ids.amount', 'account_id.currency_id', 'move_id.state')
    def _amount_residual(self):
        """ Computes the residual amount of a move line from a reconciliable account in the company currency and the line's currency.
            This amount will be 0 for fully reconciled lines or lines from a non-reconciliable account, the original line amount
            for unreconciled lines, and something in-between for partially reconciled lines.
        """
        for line in self:
            if not line.account_id.reconcile:
                line.reconciled = False
                line.amount_residual = 0
                line.amount_residual_currency = 0
                continue
            #amounts in the partial reconcile table aren't signed, so we need to use abs()
            amount = abs(line.debit - line.credit)
            amount_residual_currency = abs(line.amount_currency) or 0.0
            sign = 1 if (line.debit - line.credit) > 0 else -1
            if not line.debit and not line.credit and line.amount_currency and line.currency_id:
                #residual for exchange rate entries
                sign = 1 if float_compare(line.amount_currency, 0, precision_rounding=line.currency_id.rounding) == 1 else -1

            for partial_line in (line.matched_debit_ids + line.matched_credit_ids):
                # If line is a credit (sign = -1) we:
                #  - subtract matched_debit_ids (partial_line.credit_move_id == line)
                #  - add matched_credit_ids (partial_line.credit_move_id != line)
                # If line is a debit (sign = 1), do the opposite.
                sign_partial_line = sign if partial_line.credit_move_id == line else (-1 * sign)

                amount += sign_partial_line * partial_line.amount
                #getting the date of the matched item to compute the amount_residual in currency
                if line.currency_id:
                    if partial_line.currency_id and partial_line.currency_id == line.currency_id:
                        amount_residual_currency += sign_partial_line * partial_line.amount_currency
                    else:
                        if line.balance and line.amount_currency:
                            rate = line.amount_currency / line.balance
                        else:
                            date = partial_line.credit_move_id.date if partial_line.debit_move_id == line else partial_line.debit_move_id.date
                            rate = line.currency_id.with_context(date=date).rate
                        amount_residual_currency += sign_partial_line * line.currency_id.round(partial_line.amount * rate)

            #computing the `reconciled` field. As we book exchange rate difference on each partial matching,
            #we can only check the amount in company currency
            reconciled = False
            digits_rounding_precision = line.company_id.currency_id.rounding
            if float_is_zero(amount, precision_rounding=digits_rounding_precision):
                if line.currency_id and line.amount_currency:
                    if float_is_zero(amount_residual_currency, precision_rounding=line.currency_id.rounding):
                        reconciled = True
                else:
                    reconciled = True
            line.reconciled = reconciled

            line.amount_residual = line.company_id.currency_id.round(amount * sign)
            line.amount_residual_currency = line.currency_id and line.currency_id.round(amount_residual_currency * sign) or 0.0

    @api.depends('debit', 'credit')
    def _store_balance(self):
        for line in self:
            line.balance = line.debit - line.credit

    @api.model
    def _get_currency(self):
        currency = False
        context = self._context or {}
        if context.get('default_journal_id', False):
            currency = self.env['account.journal'].browse(context['default_journal_id']).currency_id
        return currency

    @api.depends('debit', 'credit', 'move_id.matched_percentage', 'move_id.journal_id')
    def _compute_cash_basis(self):
        for move_line in self:
            if move_line.journal_id.type in ('sale', 'purchase'):
                move_line.debit_cash_basis = move_line.debit * move_line.move_id.matched_percentage
                move_line.credit_cash_basis = move_line.credit * move_line.move_id.matched_percentage
            else:
                move_line.debit_cash_basis = move_line.debit
                move_line.credit_cash_basis = move_line.credit
            move_line.balance_cash_basis = move_line.debit_cash_basis - move_line.credit_cash_basis

    @api.one
    @api.depends('move_id.line_ids')
    def _get_counterpart(self):
        counterpart = set()
        for line in self.move_id.line_ids:
            if (line.account_id.code != self.account_id.code):
                counterpart.add(line.account_id.code)
        if len(counterpart) > 2:
            counterpart = list(counterpart)[0:2] + ["..."]
        self.counterpart = ",".join(counterpart)

    name = fields.Char(string="Label")
    quantity = fields.Float(digits=(16, 2),
        help="The optional quantity expressed by this line, eg: number of product sold. The quantity is not a legal requirement but is very useful for some reports.")
    product_uom_id = fields.Many2one('product.uom', string='Unit of Measure')
    product_id = fields.Many2one('product.product', string='Product')
    debit = fields.Monetary(default=0.0, currency_field='company_currency_id')
    credit = fields.Monetary(default=0.0, currency_field='company_currency_id')
    balance = fields.Monetary(compute='_store_balance', store=True, currency_field='company_currency_id',
        help="Technical field holding the debit - credit in order to open meaningful graph views from reports")
    debit_cash_basis = fields.Monetary(currency_field='company_currency_id', compute='_compute_cash_basis', store=True)
    credit_cash_basis = fields.Monetary(currency_field='company_currency_id', compute='_compute_cash_basis', store=True)
    balance_cash_basis = fields.Monetary(compute='_compute_cash_basis', store=True, currency_field='company_currency_id',
        help="Technical field holding the debit_cash_basis - credit_cash_basis in order to open meaningful graph views from reports")
    amount_currency = fields.Monetary(default=0.0, help="The amount expressed in an optional other currency if it is a multi-currency entry.")
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string="Company Currency", readonly=True,
        help='Utility field to express amount currency', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=_get_currency,
        help="The optional other currency if it is a multi-currency entry.")
    amount_residual = fields.Monetary(compute='_amount_residual', string='Residual Amount', store=True, currency_field='company_currency_id',
        help="The residual amount on a journal item expressed in the company currency.")
    amount_residual_currency = fields.Monetary(compute='_amount_residual', string='Residual Amount in Currency', store=True,
        help="The residual amount on a journal item expressed in its currency (possibly not the company currency).")
    account_id = fields.Many2one('account.account', string='Account', required=True, index=True,
        ondelete="cascade", domain=[('deprecated', '=', False)], default=lambda self: self._context.get('account_id', False))
    move_id = fields.Many2one('account.move', string='Journal Entry', ondelete="cascade",
        help="The move of this entry line.", index=True, required=True, auto_join=True)
    narration = fields.Text(related='move_id.narration', string='Narration')
    ref = fields.Char(related='move_id.ref', string='Reference', store=True, copy=False, index=True)
    payment_id = fields.Many2one('account.payment', string="Originator Payment", help="Payment that created this entry")
    statement_line_id = fields.Many2one('account.bank.statement.line', index=True, string='Bank statement line reconciled with this entry', copy=False, readonly=True)
    statement_id = fields.Many2one('account.bank.statement', related='statement_line_id.statement_id', string='Statement', store=True,
        help="The bank statement used for bank reconciliation", index=True, copy=False)
    reconciled = fields.Boolean(compute='_amount_residual', store=True)
    full_reconcile_id = fields.Many2one('account.full.reconcile', string="Matching Number", copy=False)
    matched_debit_ids = fields.One2many('account.partial.reconcile', 'credit_move_id', String='Matched Debits',
        help='Debit journal items that are matched with this journal item.')
    matched_credit_ids = fields.One2many('account.partial.reconcile', 'debit_move_id', String='Matched Credits',
        help='Credit journal items that are matched with this journal item.')
    journal_id = fields.Many2one('account.journal', related='move_id.journal_id', string='Journal',
        index=True, store=True, copy=False)  # related is required
    blocked = fields.Boolean(string='No Follow-up', default=False,
        help="You can check this box to mark this journal item as a litigation with the associated partner")
    date_maturity = fields.Date(string='Due date', index=True, required=True,
        help="This field is used for payable and receivable journal entries. You can put the limit date for the payment of this line.")
    date = fields.Date(related='move_id.date', string='Date', index=True, store=True, copy=False)  # related is required
    analytic_line_ids = fields.One2many('account.analytic.line', 'move_id', string='Analytic lines', oldname="analytic_lines")
    tax_ids = fields.Many2many('account.tax', string='Taxes')
    tax_line_id = fields.Many2one('account.tax', string='Originator tax', ondelete='restrict')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic tags')
    company_id = fields.Many2one('res.company', related='account_id.company_id', string='Company', store=True)
    counterpart = fields.Char("Counterpart", compute='_get_counterpart', help="Compute the counter part accounts of this journal item for this journal entry. This can be needed in reports.")

    # TODO: put the invoice link and partner_id on the account_move
    invoice_id = fields.Many2one('account.invoice', oldname="invoice")
    partner_id = fields.Many2one('res.partner', string='Partner', ondelete='restrict')
    user_type_id = fields.Many2one('account.account.type', related='account_id.user_type_id', index=True, store=True, oldname="user_type")
    tax_exigible = fields.Boolean(string='Appears in VAT report', default=True,
        help="Technical field used to mark a tax line as exigible in the vat report or not (only exigible journal items are displayed). By default all new journal items are directly exigible, but with the feature cash_basis on taxes, some will become exigible only when the payment is recorded.")

    _sql_constraints = [
        ('credit_debit1', 'CHECK (credit*debit=0)', 'Wrong credit or debit value in accounting entry !'),
        ('credit_debit2', 'CHECK (credit+debit>=0)', 'Wrong credit or debit value in accounting entry !'),
    ]

    @api.model
    def default_get(self, fields):
        rec = super(AccountMoveLine, self).default_get(fields)
        if 'line_ids' not in self._context:
            return rec

        #compute the default credit/debit of the next line in case of a manual entry
        balance = 0
        for line in self._context['line_ids']:
            if line[2]:
                balance += line[2]['debit'] - line[2]['credit']
        if balance < 0:
            rec.update({'debit': -balance})
        if balance > 0:
            rec.update({'credit': balance})
        return rec

    @api.multi
    @api.constrains('currency_id', 'account_id')
    def _check_currency(self):
        for line in self:
            if line.account_id.currency_id:
                if not line.currency_id or line.currency_id.id != line.account_id.currency_id.id:
                    raise ValidationError(_('The selected account of your Journal Entry forces to provide a secondary currency. You should remove the secondary currency on the account.'))

    @api.multi
    @api.constrains('currency_id', 'amount_currency')
    def _check_currency_and_amount(self):
        for line in self:
            if (line.amount_currency and not line.currency_id):
                raise ValidationError(_("You cannot create journal items with a secondary currency without filling both 'currency' and 'amount currency' field."))

    @api.multi
    @api.constrains('amount_currency')
    def _check_currency_amount(self):
        for line in self:
            if line.amount_currency:
                if (line.amount_currency > 0.0 and line.credit > 0.0) or (line.amount_currency < 0.0 and line.debit > 0.0):
                    raise ValidationError(_('The amount expressed in the secondary currency must be positive when account is debited and negative when account is credited.'))

    ####################################################
    # Reconciliation interface methods
    ####################################################

    @api.model
    def get_data_for_manual_reconciliation_widget(self, partner_ids, account_ids):
        """ Returns the data required for the invoices & payments matching of partners/accounts.
            If an argument is None, fetch all related reconciliations. Use [] to fetch nothing.
        """
        return {
            'customers': self.get_data_for_manual_reconciliation('partner', partner_ids, 'receivable'),
            'suppliers': self.get_data_for_manual_reconciliation('partner', partner_ids, 'payable'),
            'accounts': self.get_data_for_manual_reconciliation('account', account_ids),
        }

    @api.model
    def get_data_for_manual_reconciliation(self, res_type, res_ids=None, account_type=None):
        """ Returns the data required for the invoices & payments matching of partners/accounts (list of dicts).
            If no res_ids is passed, returns data for all partners/accounts that can be reconciled.

            :param res_type: either 'partner' or 'account'
            :param res_ids: ids of the partners/accounts to reconcile, use None to fetch data indiscriminately
                of the id, use [] to prevent from fetching any data at all.
            :param account_type: if a partner is both customer and vendor, you can use 'payable' to reconcile
                the vendor-related journal entries and 'receivable' for the customer-related entries.
        """
        if res_ids is not None and len(res_ids) == 0:
            # Note : this short-circuiting is better for performances, but also required
            # since postgresql doesn't implement empty list (so 'AND id in ()' is useless)
            return []
        res_ids = res_ids and tuple(res_ids)

        assert res_type in ('partner', 'account')
        assert account_type in ('payable', 'receivable', None)
        is_partner = res_type == 'partner'
        res_alias = is_partner and 'p' or 'a'

        query = ("""
            SELECT {0} account_id, account_name, account_code, max_date,
                   to_char(last_time_entries_checked, 'YYYY-MM-DD') AS last_time_entries_checked
            FROM (
                    SELECT {1}
                        {res_alias}.last_time_entries_checked AS last_time_entries_checked,
                        a.id AS account_id,
                        a.name AS account_name,
                        a.code AS account_code,
                        MAX(l.write_date) AS max_date
                    FROM
                        account_move_line l
                        RIGHT JOIN account_account a ON (a.id = l.account_id)
                        RIGHT JOIN account_account_type at ON (at.id = a.user_type_id)
                        {2}
                    WHERE
                        a.reconcile IS TRUE
                        {3}
                        {4}
                        {5}
                        AND l.company_id = {6}
                        AND EXISTS (
                            SELECT NULL
                            FROM account_move_line l
                            WHERE l.account_id = a.id
                            {7}
                            AND l.amount_residual > 0
                        )
                        AND EXISTS (
                            SELECT NULL
                            FROM account_move_line l
                            WHERE l.account_id = a.id
                            {7}
                            AND l.amount_residual < 0
                        )
                    GROUP BY {8} a.id, a.name, a.code, {res_alias}.last_time_entries_checked
                    ORDER BY {res_alias}.last_time_entries_checked
                ) as s
            WHERE (last_time_entries_checked IS NULL OR max_date > last_time_entries_checked)
        """.format(
                is_partner and 'partner_id, partner_name,' or ' ',
                is_partner and 'p.id AS partner_id, p.name AS partner_name,' or ' ',
                is_partner and 'RIGHT JOIN res_partner p ON (l.partner_id = p.id)' or ' ',
                is_partner and ' ' or "AND at.type <> 'payable' AND at.type <> 'receivable'",
                account_type and "AND at.type = %(account_type)s" or '',
                res_ids and 'AND ' + res_alias + '.id in %(res_ids)s' or '',
                self.env.user.company_id.id,
                is_partner and 'AND l.partner_id = p.id' or ' ',
                is_partner and 'l.partner_id, p.id,' or ' ',
                res_alias=res_alias
            ))
        self.env.cr.execute(query, locals())

        # Apply ir_rules by filtering out
        rows = self.env.cr.dictfetchall()
        ids = [x['account_id'] for x in rows]
        allowed_ids = set(self.env['account.account'].browse(ids).ids)
        rows = [row for row in rows if row['account_id'] in allowed_ids]
        if is_partner:
            ids = [x['partner_id'] for x in rows]
            allowed_ids = set(self.env['res.partner'].browse(ids).ids)
            rows = [row for row in rows if row['partner_id'] in allowed_ids]

        # Fetch other data
        for row in rows:
            account = self.env['account.account'].browse(row['account_id'])
            row['currency_id'] = account.currency_id.id or account.company_id.currency_id.id
            partner_id = is_partner and row['partner_id'] or None
            row['reconciliation_proposition'] = self.get_reconciliation_proposition(account.id, partner_id)
        return rows

    @api.model
    def get_reconciliation_proposition(self, account_id, partner_id=False):
        """ Returns two lines whose amount are opposite """

        # Get pairs
        partner_id_condition = partner_id and 'AND a.partner_id = %(partner_id)s AND b.partner_id = %(partner_id)s' or ''
        query = """
                SELECT a.id, b.id
                FROM account_move_line a, account_move_line b
                WHERE a.amount_residual = -b.amount_residual
                AND NOT a.reconciled AND NOT b.reconciled
                AND a.account_id = %(account_id)s AND b.account_id = %(account_id)s
                {partner_id_condition}
                ORDER BY a.date asc
                LIMIT 10
            """.format(**locals())
        self.env.cr.execute(query, locals())
        pairs = self.env.cr.fetchall()

        # Apply ir_rules by filtering out
        all_pair_ids = [element for tupl in pairs for element in tupl]
        allowed_ids = set(self.env['account.move.line'].browse(all_pair_ids).ids)
        pairs = [pair for pair in pairs if pair[0] in allowed_ids and pair[1] in allowed_ids]

        # Return lines formatted
        if len(pairs) > 0:
            target_currency = (self.currency_id and self.amount_currency) and self.currency_id or self.company_id.currency_id
            lines = self.browse(list(pairs[0]))
            return lines.prepare_move_lines_for_reconciliation_widget(target_currency=target_currency)
        return []

    @api.model
    def domain_move_lines_for_reconciliation(self, excluded_ids=None, str=False):
        """ Returns the domain which is common to both manual and bank statement reconciliation.

            :param excluded_ids: list of ids of move lines that should not be fetched
            :param str: search string
        """
        context = (self._context or {})
        if excluded_ids is None:
            excluded_ids = []
        domain = []

        if excluded_ids:
            domain = expression.AND([domain, [('id', 'not in', excluded_ids)]])
        if str:
            str_domain = [
                '|', ('move_id.name', 'ilike', str),
                '|', ('move_id.ref', 'ilike', str),
                '|', ('date_maturity', 'like', str),
                '&', ('name', '!=', '/'), ('name', 'ilike', str)
            ]
            try:
                amount = float(str)
                amount_domain = [
                    '|', ('amount_residual', '=', amount),
                    '|', ('amount_residual_currency', '=', amount),
                    '|', ('amount_residual', '=', -amount),
                    '|', ('amount_residual_currency', '=', -amount),
                    '&', ('account_id.internal_type', '=', 'liquidity'),
                    '|', '|', ('debit', '=', amount), ('credit', '=', amount), ('amount_currency', '=', amount),
                ]
                str_domain = expression.OR([str_domain, amount_domain])
            except:
                pass

            # When building a domain for the bank statement reconciliation, if there's no partner
            # and a search string, search also a match in the partner names
            if 'bank_statement_line' in context and not context['bank_statement_line'].partner_id.id:
                str_domain = expression.OR([str_domain, [('partner_id.name', 'ilike', str)]])

            domain = expression.AND([domain, str_domain])
        return domain

    def _domain_move_lines_for_manual_reconciliation(self, account_id, partner_id=False, excluded_ids=None, str=False):
        """ Create domain criteria that are relevant to manual reconciliation. """
        domain = ['&', ('reconciled', '=', False), ('account_id', '=', account_id)]
        if partner_id:
            domain = expression.AND([domain, [('partner_id', '=', partner_id)]])
        generic_domain = self.domain_move_lines_for_reconciliation(excluded_ids=excluded_ids, str=str)

        return expression.AND([generic_domain, domain])

    @api.model
    def get_move_lines_for_manual_reconciliation(self, account_id, partner_id=False, excluded_ids=None, str=False, offset=0, limit=None, target_currency_id=False):
        """ Returns unreconciled move lines for an account or a partner+account, formatted for the manual reconciliation widget """
        domain = self._domain_move_lines_for_manual_reconciliation(account_id, partner_id, excluded_ids, str)
        lines = self.search(domain, offset=offset, limit=limit, order="date_maturity asc, id asc")
        if target_currency_id:
            target_currency = self.env['res.currency'].browse(target_currency_id)
        else:
            account = self.env['account.account'].browse(account_id)
            target_currency = account.currency_id or account.company_id.currency_id
        return lines.prepare_move_lines_for_reconciliation_widget(target_currency=target_currency)

    @api.multi
    def prepare_move_lines_for_reconciliation_widget(self, target_currency=False, target_date=False):
        """ Returns move lines formatted for the manual/bank reconciliation widget

            :param target_currency: currency (browse_record or ID) you want the move line debit/credit converted into
            :param target_date: date to use for the monetary conversion
        """
        context = dict(self._context or {})
        ret = []

        if target_currency:
            # re-browse in case we were passed a currency ID via RPC call
            target_currency = self.env['res.currency'].browse(int(target_currency))

        for line in self:
            company_currency = line.account_id.company_id.currency_id
            ret_line = {
                'id': line.id,
                'name': line.name != '/' and line.move_id.name + ': ' + line.name or line.move_id.name,
                'ref': line.move_id.ref or '',
                # For reconciliation between statement transactions and already registered payments (eg. checks)
                # NB : we don't use the 'reconciled' field because the line we're selecting is not the one that gets reconciled
                'already_paid': line.account_id.internal_type == 'liquidity',
                'account_code': line.account_id.code,
                'account_name': line.account_id.name,
                'account_type': line.account_id.internal_type,
                'date_maturity': line.date_maturity,
                'date': line.date,
                'journal_name': line.journal_id.name,
                'partner_id': line.partner_id.id,
                'partner_name': line.partner_id.name,
                'currency_id': (line.currency_id and line.amount_currency) and line.currency_id.id or False,
            }

            debit = line.debit
            credit = line.credit
            amount = line.amount_residual
            amount_currency = line.amount_residual_currency

            # For already reconciled lines, don't use amount_residual(_currency)
            if line.account_id.internal_type == 'liquidity':
                amount = abs(debit - credit)
                amount_currency = abs(line.amount_currency)

            # Get right debit / credit:
            target_currency = target_currency or company_currency
            line_currency = (line.currency_id and line.amount_currency) and line.currency_id or company_currency
            amount_currency_str = ""
            total_amount_currency_str = ""
            if line_currency != company_currency and target_currency == line_currency:
                # The payment currency is the invoice currency, but they are different than the company currency
                # We use the `amount_currency` computed during the invoice validation, at the invoice date
                # to avoid exchange gain/loss
                # e.g. an invoice of 100€ must be paid with 100€, whatever the company currency and the exchange rates
                total_amount = line.amount_currency
                actual_debit = debit > 0 and amount_currency or 0.0
                actual_credit = credit > 0 and -amount_currency or 0.0
                currency = line_currency
            else:
                # Either:
                #  - the invoice, payment, company currencies are all the same,
                #  - the payment currency is the company currency, but the invoice currency is different,
                #  - the invoice currency is the company currency, but the payment currency is different,
                #  - the invoice, payment and company currencies are all different.
                # For the two first cases, we can simply use the debit/credit of the invoice move line, which are always in the company currency,
                # and this is what the target need.
                # For the two last cases, we can use the debit/credit which are in the company currency, and then change them to the target currency
                total_amount = abs(debit - credit)
                actual_debit = debit > 0 and amount or 0.0
                actual_credit = credit > 0 and -amount or 0.0
                currency = company_currency
            if line_currency != target_currency:
                amount_currency_str = formatLang(self.env, abs(actual_debit or actual_credit), currency_obj=line_currency)
                total_amount_currency_str = formatLang(self.env, total_amount, currency_obj=line_currency)
            if currency != target_currency:
                ctx = context.copy()
                ctx.update({'date': target_date or line.date})
                total_amount = currency.with_context(ctx).compute(total_amount, target_currency)
                actual_debit = currency.with_context(ctx).compute(actual_debit, target_currency)
                actual_credit = currency.with_context(ctx).compute(actual_credit, target_currency)
            amount_str = formatLang(self.env, abs(actual_debit or actual_credit), currency_obj=target_currency)
            total_amount_str = formatLang(self.env, total_amount, currency_obj=target_currency)

            ret_line['debit'] = abs(actual_debit)
            ret_line['credit'] = abs(actual_credit)
            ret_line['amount_str'] = amount_str
            ret_line['total_amount_str'] = total_amount_str
            ret_line['amount_currency_str'] = amount_currency_str
            ret_line['total_amount_currency_str'] = total_amount_currency_str
            ret.append(ret_line)
        return ret

    @api.model
    def process_reconciliations(self, data):
        """ Used to validate a batch of reconciliations in a single call
            :param data: list of dicts containing:
                - 'type': either 'partner' or 'account'
                - 'id': id of the affected res.partner or account.account
                - 'mv_line_ids': ids of exisiting account.move.line to reconcile
                - 'new_mv_line_dicts': list of dicts containing values suitable for account_move_line.create()
        """
        for datum in data:
            if len(datum['mv_line_ids']) >= 1 or len(datum['mv_line_ids']) + len(datum['new_mv_line_dicts']) >= 2:
                self.process_reconciliation(datum['mv_line_ids'], datum['new_mv_line_dicts'])

            if datum['type'] == 'partner':
                partners = self.env['res.partner'].browse(datum['id'])
                partners.mark_as_reconciled()
            if datum['type'] == 'account':
                accounts = self.env['account.account'].browse(datum['id'])
                accounts.mark_as_reconciled()

    @api.multi
    def process_reconciliation(self, new_mv_line_dicts):
        """ Create new move lines from new_mv_line_dicts (if not empty) then call reconcile_partial on self and new move lines

            :param new_mv_line_dicts: list of dicts containing values suitable fot account_move_line.create()
        """
        if len(self) < 1 or len(self) + len(new_mv_line_dicts) < 2:
            raise UserError(_('A reconciliation must involve at least 2 move lines.'))

        # Create writeoff move lines
        if len(new_mv_line_dicts) > 0:
            writeoff_lines = self.env['account.move.line']
            company_currency = self[0].account_id.company_id.currency_id
            writeoff_currency = self[0].currency_id or company_currency
            for mv_line_dict in new_mv_line_dicts:
                if writeoff_currency != company_currency:
                    mv_line_dict['debit'] = writeoff_currency.compute(mv_line_dict['debit'], company_currency)
                    mv_line_dict['credit'] = writeoff_currency.compute(mv_line_dict['credit'], company_currency)
                writeoff_lines += self._create_writeoff(mv_line_dict)

            (self + writeoff_lines).reconcile()
        else:
            self.reconcile()

    ####################################################
    # Reconciliation methods
    ####################################################

    def _get_pair_to_reconcile(self):
        #field is either 'amount_residual' or 'amount_residual_currency' (if the reconciled account has a secondary currency set)
        field = self[0].account_id.currency_id and 'amount_residual_currency' or 'amount_residual'
        rounding = self[0].company_id.currency_id.rounding
        if self[0].currency_id and all([x.amount_currency and x.currency_id == self[0].currency_id for x in self]):
            #or if all lines share the same currency
            field = 'amount_residual_currency'
            rounding = self[0].currency_id.rounding
        if self._context.get('skip_full_reconcile_check') == 'amount_currency_excluded':
            field = 'amount_residual'
        elif self._context.get('skip_full_reconcile_check') == 'amount_currency_only':
            field = 'amount_residual_currency'
        #target the pair of move in self that are the oldest
        sorted_moves = sorted(self, key=lambda a: a.date)
        debit = credit = False
        for aml in sorted_moves:
            if credit and debit:
                break
            if float_compare(aml[field], 0, precision_rounding=rounding) == 1 and not debit:
                debit = aml
            elif float_compare(aml[field], 0, precision_rounding=rounding) == -1 and not credit:
                credit = aml
        return debit, credit

    def auto_reconcile_lines(self):
        """ This function iterates recursively on the recordset given as parameter as long as it
            can find a debit and a credit to reconcile together. It returns the recordset of the
            account move lines that were not reconciled during the process.
        """
        if not self.ids:
            return self
        sm_debit_move, sm_credit_move = self._get_pair_to_reconcile()
        #there is no more pair to reconcile so return what move_line are left
        if not sm_credit_move or not sm_debit_move:
            return self

        field = self[0].account_id.currency_id and 'amount_residual_currency' or 'amount_residual'
        if not sm_debit_move.debit and not sm_debit_move.credit:
            #both debit and credit field are 0, consider the amount_residual_currency field because it's an exchange difference entry
            field = 'amount_residual_currency'
        if self[0].currency_id and all([x.currency_id == self[0].currency_id for x in self]):
            #all the lines have the same currency, so we consider the amount_residual_currency field
            field = 'amount_residual_currency'
        if self._context.get('skip_full_reconcile_check') == 'amount_currency_excluded':
            field = 'amount_residual'
        elif self._context.get('skip_full_reconcile_check') == 'amount_currency_only':
            field = 'amount_residual_currency'
        #Reconcile the pair together
        amount_reconcile = min(sm_debit_move[field], -sm_credit_move[field])
        #Remove from recordset the one(s) that will be totally reconciled
        if amount_reconcile == sm_debit_move[field]:
            self -= sm_debit_move
        if amount_reconcile == -sm_credit_move[field]:
            self -= sm_credit_move

        #Check for the currency and amount_currency we can set
        currency = False
        amount_reconcile_currency = 0
        if sm_debit_move.currency_id == sm_credit_move.currency_id and sm_debit_move.currency_id.id:
            currency = sm_credit_move.currency_id.id
            amount_reconcile_currency = min(sm_debit_move.amount_residual_currency, -sm_credit_move.amount_residual_currency)

        amount_reconcile = min(sm_debit_move.amount_residual, -sm_credit_move.amount_residual)

        if self._context.get('skip_full_reconcile_check') == 'amount_currency_excluded':
            amount_reconcile_currency = 0.0
            currency = self._context.get('manual_full_reconcile_currency')
        elif self._context.get('skip_full_reconcile_check') == 'amount_currency_only':
            currency = self._context.get('manual_full_reconcile_currency')

        self.env['account.partial.reconcile'].create({
            'debit_move_id': sm_debit_move.id,
            'credit_move_id': sm_credit_move.id,
            'amount': amount_reconcile,
            'amount_currency': amount_reconcile_currency,
            'currency_id': currency,
        })

        #Iterate process again on self
        return self.auto_reconcile_lines()

    @api.multi
    def reconcile(self, writeoff_acc_id=False, writeoff_journal_id=False):
        #Perform all checks on lines
        company_ids = set()
        all_accounts = []
        partners = set()
        for line in self:
            company_ids.add(line.company_id.id)
            all_accounts.append(line.account_id)
            if (line.account_id.internal_type in ('receivable', 'payable')):
                partners.add(line.partner_id.id)
            if line.reconciled:
                raise UserError(_('You are trying to reconcile some entries that are already reconciled!'))
        if len(company_ids) > 1:
            raise UserError(_('To reconcile the entries company should be the same for all entries!'))
        if len(set(all_accounts)) > 1:
            raise UserError(_('Entries are not of the same account!'))
        if not all_accounts[0].reconcile:
            raise UserError(_('The account %s (%s) is not marked as reconciliable !') % (all_accounts[0].name, all_accounts[0].code))
        if len(partners) > 1:
            raise UserError(_('The partner has to be the same on all lines for receivable and payable accounts!'))

        #reconcile everything that can be
        remaining_moves = self.auto_reconcile_lines()

        #if writeoff_acc_id specified, then create write-off move with value the remaining amount from move in self
        if writeoff_acc_id and writeoff_journal_id and remaining_moves:
            all_aml_share_same_currency = all([x.currency_id == self[0].currency_id for x in self])
            writeoff_vals = {
                'account_id': writeoff_acc_id.id,
                'journal_id': writeoff_journal_id.id
            }
            if not all_aml_share_same_currency:
                writeoff_vals['amount_currency'] = False
            writeoff_to_reconcile = remaining_moves._create_writeoff(writeoff_vals)
            #add writeoff line to reconcile algo and finish the reconciliation
            remaining_moves = (remaining_moves + writeoff_to_reconcile).auto_reconcile_lines()
            return writeoff_to_reconcile
        return True

    def _create_writeoff(self, vals):
        """ Create a writeoff move for the account.move.lines in self. If debit/credit is not specified in vals,
            the writeoff amount will be computed as the sum of amount_residual of the given recordset.

            :param vals: dict containing values suitable fot account_move_line.create(). The data in vals will
                be processed to create bot writeoff acount.move.line and their enclosing account.move.
        """
        # Check and complete vals
        if 'account_id' not in vals or 'journal_id' not in vals:
            raise UserError(_("It is mandatory to specify an account and a journal to create a write-off."))
        if ('debit' in vals) ^ ('credit' in vals):
            raise UserError(_("Either pass both debit and credit or none."))
        if 'date' not in vals:
            vals['date'] = self._context.get('date_p') or time.strftime('%Y-%m-%d')
        if 'name' not in vals:
            vals['name'] = self._context.get('comment') or _('Write-Off')
        if 'analytic_account_id' not in vals:
            vals['analytic_account_id'] = self.env.context.get('analytic_id', False)
        #compute the writeoff amount if not given
        if 'credit' not in vals and 'debit' not in vals:
            amount = sum([r.amount_residual for r in self])
            vals['credit'] = amount > 0 and amount or 0.0
            vals['debit'] = amount < 0 and abs(amount) or 0.0
        vals['partner_id'] = self.env['res.partner']._find_accounting_partner(self[0].partner_id).id
        company_currency = self[0].account_id.company_id.currency_id
        writeoff_currency = self[0].currency_id or company_currency
        if not self._context.get('skip_full_reconcile_check') == 'amount_currency_excluded' and 'amount_currency' not in vals and writeoff_currency != company_currency:
            vals['currency_id'] = writeoff_currency.id
            sign = 1 if vals['debit'] > 0 else -1
            vals['amount_currency'] = sign * abs(sum([r.amount_residual_currency for r in self]))

        # Writeoff line in the account of self
        first_line_dict = vals.copy()
        first_line_dict['account_id'] = self[0].account_id.id
        if 'analytic_account_id' in first_line_dict:
            del first_line_dict['analytic_account_id']
        if 'tax_ids' in first_line_dict:
            tax_ids = []
            #vals['tax_ids'] is a list of commands [[4, tax_id, None], ...]
            for tax_id in vals['tax_ids']:
                tax_ids.append(tax_id[1])
            amount = first_line_dict['credit'] - first_line_dict['debit']
            amount_tax = self.env['account.tax'].browse(tax_ids).compute_all(amount)['total_included']
            first_line_dict['credit'] = amount_tax > 0 and amount_tax or 0.0
            first_line_dict['debit'] = amount_tax < 0 and abs(amount_tax) or 0.0
            del first_line_dict['tax_ids']

        # Writeoff line in specified writeoff account
        second_line_dict = vals.copy()
        second_line_dict['debit'], second_line_dict['credit'] = second_line_dict['credit'], second_line_dict['debit']
        if 'amount_currency' in vals:
            second_line_dict['amount_currency'] = -second_line_dict['amount_currency']

        # Create the move
        writeoff_move = self.env['account.move'].create({
            'journal_id': vals['journal_id'],
            'date': vals['date'],
            'state': 'draft',
            'line_ids': [(0, 0, first_line_dict), (0, 0, second_line_dict)],
        })
        writeoff_move.post()

        # Return the writeoff move.line which is to be reconciled
        return writeoff_move.line_ids.filtered(lambda r: r.account_id == self[0].account_id)

    @api.model
    def compute_full_after_batch_reconcile(self):
        """ After running the manual reconciliation wizard and making full reconciliation, we need to run this method to create
            potentially an exchange rate entry that will balance the remaining amount_residual_currency (possibly several aml).

            This ensure that all aml in the full reconciliation are reconciled (amount_residual = amount_residual_currency = 0).
        """
        total_debit = 0
        total_credit = 0
        total_amount_currency = 0
        currency = False
        aml_to_balance_currency = self.env['account.move.line']
        partial_rec_set = self.env['account.partial.reconcile']
        aml_id = False
        partial_rec_id = False
        maxdate = None
        for aml in self:
            total_debit += aml.debit
            total_credit += aml.credit
            if aml.amount_residual_currency:
                aml_to_balance_currency |= aml
            maxdate = max(aml.date, maxdate)
            if not currency and aml.currency_id:
                currency = aml.currency_id
            if aml.currency_id and aml.currency_id == currency:
                total_amount_currency += aml.amount_currency
            partial_rec_set |= aml.matched_debit_ids | aml.matched_credit_ids

        if currency and aml_to_balance_currency:
            aml = aml_to_balance_currency[0]
            #eventually create journal entries to book the difference due to foreign currency's exchange rate that fluctuates
            partial_rec = aml.credit and aml.matched_debit_ids[0] or aml.matched_credit_ids[0]
            aml_id, partial_rec_id = partial_rec.with_context(skip_full_reconcile_check=True).create_exchange_rate_entry(aml_to_balance_currency, 0.0, total_amount_currency, currency, maxdate)
            self |= aml_id
            partial_rec_set |= partial_rec_id
            total_amount_currency += aml_id.amount_currency

        partial_rec_ids = [x.id for x in list(partial_rec_set)]
        #if the total debit and credit are equal, and the total amount in currency is 0, the reconciliation is full
        digits_rounding_precision = self[0].company_id.currency_id.rounding
        if float_compare(total_debit, total_credit, precision_rounding=digits_rounding_precision) == 0 \
          and (not currency or float_is_zero(total_amount_currency, precision_rounding=currency.rounding)):
            #in that case, mark the reference on the partial reconciliations and the entries
            self.env['account.full.reconcile'].with_context(check_move_validity=False).create({
                'partial_reconcile_ids': [(6, 0, partial_rec_ids)],
                'reconciled_line_ids': [(6, 0, self.ids)],
                'exchange_move_id': aml_id.move_id.id if aml_id else False,
                'exchange_partial_rec_id': partial_rec_id.id if partial_rec_id else False})

    @api.multi
    def remove_move_reconcile(self):
        """ Undo a reconciliation """
        if not self:
            return True
        rec_move_ids = self.env['account.partial.reconcile']
        for account_move_line in self:
            for invoice in account_move_line.payment_id.invoice_ids:
                if invoice.id == self.env.context.get('invoice_id') and account_move_line in invoice.payment_move_line_ids:
                    account_move_line.payment_id.write({'invoice_ids': [(3, invoice.id, None)]})
            rec_move_ids += account_move_line.matched_debit_ids
            rec_move_ids += account_move_line.matched_credit_ids
        return rec_move_ids.unlink()

    ####################################################
    # CRUD methods
    ####################################################

    #TODO: to check/refactor
    @api.model
    def create(self, vals):
        """ :context's key apply_taxes: set to True if you want vals['tax_ids'] to result in the creation of move lines for taxes and eventual
                adjustment of the line amount (in case of a tax included in price).

            :context's key `check_move_validity`: check data consistency after move line creation. Eg. set to false to disable verification that the move
                debit-credit == 0 while creating the move lines composing the move.

        """
        context = dict(self._context or {})
        amount = vals.get('debit', 0.0) - vals.get('credit', 0.0)
        if not vals.get('partner_id') and context.get('partner_id'):
            vals['partner_id'] = context.get('partner_id')
        move = self.env['account.move'].browse(vals['move_id'])
        account = self.env['account.account'].browse(vals['account_id'])
        if account.deprecated:
            raise UserError(_('You cannot use deprecated account.'))
        if 'journal_id' in vals and vals['journal_id']:
            context['journal_id'] = vals['journal_id']
        if 'date' in vals and vals['date']:
            context['date'] = vals['date']
        if 'journal_id' not in context:
            context['journal_id'] = move.journal_id.id
            context['date'] = move.date
        #we need to treat the case where a value is given in the context for period_id as a string
        if not context.get('journal_id', False) and context.get('search_default_journal_id', False):
            context['journal_id'] = context.get('search_default_journal_id')
        if 'date' not in context:
            context['date'] = fields.Date.context_today(self)
        journal = vals.get('journal_id') and self.env['account.journal'].browse(vals['journal_id']) or move.journal_id
        vals['date_maturity'] = vals.get('date_maturity') or vals.get('date') or move.date
        ok = not (journal.type_control_ids or journal.account_control_ids)

        if journal.type_control_ids:
            type = account.user_type_id
            for t in journal.type_control_ids:
                if type == t:
                    ok = True
                    break
        if journal.account_control_ids and not ok:
            for a in journal.account_control_ids:
                if a.id == vals['account_id']:
                    ok = True
                    break
        # Automatically convert in the account's secondary currency if there is one and
        # the provided values were not already multi-currency
        if account.currency_id and 'amount_currency' not in vals and account.currency_id.id != account.company_id.currency_id.id:
            vals['currency_id'] = account.currency_id.id
            if self._context.get('skip_full_reconcile_check') == 'amount_currency_excluded':
                vals['amount_currency'] = 0.0
            else:
                ctx = {}
                if 'date' in vals:
                    ctx['date'] = vals['date']
                vals['amount_currency'] = account.company_id.currency_id.with_context(ctx).compute(amount, account.currency_id)

        if not ok:
            raise UserError(_('You cannot use this general account in this journal, check the tab \'Entry Controls\' on the related journal.'))

        # Create tax lines
        tax_lines_vals = []
        if context.get('apply_taxes') and vals.get('tax_ids'):
            # Get ids from triplets : https://www.odoo.com/documentation/10.0/reference/orm.html#odoo.models.Model.write
            tax_ids = [tax['id'] for tax in self.resolve_2many_commands('tax_ids', vals['tax_ids']) if tax.get('id')]
            # Since create() receives ids instead of recordset, let's just use the old-api bridge
            taxes = self.env['account.tax'].browse(tax_ids)
            currency = self.env['res.currency'].browse(vals.get('currency_id'))
            partner = self.env['res.partner'].browse(vals.get('partner_id'))
            res = taxes.with_context(round=True).compute_all(amount,
                currency, 1, vals.get('product_id'), partner)
            # Adjust line amount if any tax is price_include
            if abs(res['total_excluded']) < abs(amount):
                if vals['debit'] != 0.0: vals['debit'] = res['total_excluded']
                if vals['credit'] != 0.0: vals['credit'] = -res['total_excluded']
                if vals.get('amount_currency'):
                    vals['amount_currency'] = self.env['res.currency'].browse(vals['currency_id']).round(vals['amount_currency'] * (res['total_excluded']/amount))
            # Create tax lines
            for tax_vals in res['taxes']:
                if tax_vals['amount']:
                    tax = self.env['account.tax'].browse([tax_vals['id']])
                    account_id = (amount > 0 and tax_vals['account_id'] or tax_vals['refund_account_id'])
                    if not account_id: account_id = vals['account_id']
                    temp = {
                        'account_id': account_id,
                        'name': vals['name'] + ' ' + tax_vals['name'],
                        'tax_line_id': tax_vals['id'],
                        'move_id': vals['move_id'],
                        'partner_id': vals.get('partner_id'),
                        'statement_id': vals.get('statement_id'),
                        'debit': tax_vals['amount'] > 0 and tax_vals['amount'] or 0.0,
                        'credit': tax_vals['amount'] < 0 and -tax_vals['amount'] or 0.0,
                        'analytic_account_id': vals.get('analytic_account_id') if tax.analytic else False,
                    }
                    bank = self.env["account.bank.statement"].browse(vals.get('statement_id'))
                    if bank.currency_id != bank.company_id.currency_id:
                        ctx = {}
                        if 'date' in vals:
                            ctx['date'] = vals['date']
                        temp['currency_id'] = bank.currency_id.id
                        temp['amount_currency'] = bank.company_id.currency_id.with_context(ctx).compute(tax_vals['amount'], bank.currency_id, round=True)
                    tax_lines_vals.append(temp)

        #Toggle the 'tax_exigible' field to False in case it is not yet given and the tax in 'tax_line_id' or one of
        #the 'tax_ids' is a cash based tax.
        taxes = False
        if vals.get('tax_line_id'):
            taxes = [{'use_cash_basis': self.env['account.tax'].browse(vals['tax_line_id']).use_cash_basis}]
        if vals.get('tax_ids'):
            taxes = self.env['account.move.line'].resolve_2many_commands('tax_ids', vals['tax_ids'])
        if taxes and any([tax['use_cash_basis'] for tax in taxes]) and not vals.get('tax_exigible'):
            vals['tax_exigible'] = False

        new_line = super(AccountMoveLine, self).create(vals)
        for tax_line_vals in tax_lines_vals:
            # TODO: remove .with_context(context) once this context nonsense is solved
            self.with_context(context).create(tax_line_vals)

        if self._context.get('check_move_validity', True):
            move.with_context(context)._post_validate()

        return new_line

    @api.multi
    def unlink(self):
        self._update_check()
        move_ids = set()
        for line in self:
            if line.move_id.id not in move_ids:
                move_ids.add(line.move_id.id)
        result = super(AccountMoveLine, self).unlink()
        if self._context.get('check_move_validity', True) and move_ids:
            self.env['account.move'].browse(list(move_ids))._post_validate()
        return result

    @api.multi
    def write(self, vals):
        if ('account_id' in vals) and self.env['account.account'].browse(vals['account_id']).deprecated:
            raise UserError(_('You cannot use deprecated account.'))
        if any(key in vals for key in ('account_id', 'journal_id', 'date', 'move_id', 'debit', 'credit')):
            self._update_check()
        if not self._context.get('allow_amount_currency') and any(key in vals for key in ('amount_currency', 'currency_id')):
            #hackish workaround to write the amount_currency when assigning a payment to an invoice through the 'add' button
            #this is needed to compute the correct amount_residual_currency and potentially create an exchange difference entry
            self._update_check()
        #when we set the expected payment date, log a note on the invoice_id related (if any)
        if vals.get('expected_pay_date') and self.invoice_id:
            msg = _('New expected payment date: ') + vals['expected_pay_date'] + '.\n' + vals.get('internal_note', '')
            self.invoice_id.message_post(body=msg) #TODO: check it is an internal note (not a regular email)!
        #when making a reconciliation on an existing liquidity journal item, mark the payment as reconciled
        for record in self:
            if 'statement_line_id' in vals and record.payment_id:
                # In case of an internal transfer, there are 2 liquidity move lines to match with a bank statement
                if all(line.statement_id for line in record.payment_id.move_line_ids.filtered(lambda r: r.id != record.id and r.account_id.internal_type=='liquidity')):
                    record.payment_id.state = 'reconciled'

        result = super(AccountMoveLine, self).write(vals)
        if self._context.get('check_move_validity', True):
            move_ids = set()
            for line in self:
                if line.move_id.id not in move_ids:
                    move_ids.add(line.move_id.id)
            self.env['account.move'].browse(list(move_ids))._post_validate()
        return result

    @api.multi
    def _update_check(self):
        """ Raise Warning to cause rollback if the move is posted, some entries are reconciled or the move is older than the lock date"""
        move_ids = set()
        for line in self:
            err_msg = _('Move name (id): %s (%s)') % (line.move_id.name, str(line.move_id.id))
            if line.move_id.state != 'draft':
                raise UserError(_('You cannot do this modification on a posted journal entry, you can just change some non legal fields. You must revert the journal entry to cancel it.\n%s.') % err_msg)
            if line.reconciled and not (line.debit == 0 and line.credit == 0):
                raise UserError(_('You cannot do this modification on a reconciled entry. You can just change some non legal fields or you must unreconcile first.\n%s.') % err_msg)
            if line.move_id.id not in move_ids:
                move_ids.add(line.move_id.id)
            self.env['account.move'].browse(list(move_ids))._check_lock_date()
        return True

    ####################################################
    # Misc / utility methods
    ####################################################

    @api.multi
    @api.depends('ref', 'move_id')
    def name_get(self):
        result = []
        for line in self:
            if line.ref:
                result.append((line.id, (line.move_id.name or '') + '(' + line.ref + ')'))
            else:
                result.append((line.id, line.move_id.name))
        return result

    def _get_matched_percentage(self):
        """ This function returns a dictionary giving for each move_id of self, the percentage to consider as cash basis factor.
        This is actuallty computing the same as the matched_percentage field of account.move, except in case of multi-currencies
        where we recompute the matched percentage based on the amount_currency fields.
        Note that this function is used only by the tax cash basis module since we want to consider the matched_percentage only
        based on the company currency amounts in reports.
        """
        matched_percentage_per_move = {}
        for line in self:
            if not matched_percentage_per_move.get(line.move_id.id, False):
                lines_to_consider = line.move_id.line_ids.filtered(lambda x: x.account_id.internal_type in ('receivable', 'payable'))
                total_amount_currency = 0.0
                total_reconciled_currency = 0.0
                all_same_currency = False
                #if all receivable/payable aml and their payments have the same currency, we can safely consider
                #the amount_currency fields to avoid including the exchange rate difference in the matched_percentage
                if lines_to_consider and all([x.currency_id.id == lines_to_consider[0].currency_id.id for x in lines_to_consider]):
                    all_same_currency = lines_to_consider[0].currency_id.id
                    for line in lines_to_consider:
                        if all_same_currency:
                            total_amount_currency += abs(line.amount_currency)
                            for partial_line in (line.matched_debit_ids + line.matched_credit_ids):
                                if partial_line.currency_id and partial_line.currency_id.id == all_same_currency:
                                    total_reconciled_currency += partial_line.amount_currency
                                else:
                                    all_same_currency = False
                                    break
                if not all_same_currency:
                    #we cannot rely on amount_currency fields as it is not present on all partial reconciliation
                    matched_percentage_per_move[line.move_id.id] = line.move_id.matched_percentage
                else:
                    #we can rely on amount_currency fields, which allow us to post a tax cash basis move at the initial rate
                    #to avoid currency rate difference issues.
                    if total_amount_currency == 0.0:
                        matched_percentage_per_move[line.move_id.id] = 1.0
                    else:
                        matched_percentage_per_move[line.move_id.id] = total_reconciled_currency / total_amount_currency
        return matched_percentage_per_move

    @api.model
    def compute_amount_fields(self, amount, src_currency, company_currency, invoice_currency=False):
        """ Helper function to compute value for fields debit/credit/amount_currency based on an amount and the currencies given in parameter"""
        amount_currency = False
        currency_id = False
        if src_currency and src_currency != company_currency:
            amount_currency = amount
            amount = src_currency.with_context(self._context).compute(amount, company_currency)
            currency_id = src_currency.id
        debit = amount > 0 and amount or 0.0
        credit = amount < 0 and -amount or 0.0
        if invoice_currency and invoice_currency != company_currency and not amount_currency:
            amount_currency = src_currency.with_context(self._context).compute(amount, invoice_currency)
            currency_id = invoice_currency.id
        return debit, credit, amount_currency, currency_id

    @api.multi
    def create_analytic_lines(self):
        """ Create analytic items upon validation of an account.move.line having an analytic account. This
            method first remove any existing analytic item related to the line before creating any new one.
        """
        for obj_line in self:
            if obj_line.analytic_line_ids:
                obj_line.analytic_line_ids.unlink()
            if obj_line.analytic_account_id:
                vals_line = obj_line._prepare_analytic_line()[0]
                self.env['account.analytic.line'].create(vals_line)

    @api.one
    def _prepare_analytic_line(self):
        """ Prepare the values used to create() an account.analytic.line upon validation of an account.move.line having
            an analytic account. This method is intended to be extended in other modules.
        """
        amount = (self.credit or 0.0) - (self.debit or 0.0)
        return {
            'name': self.name,
            'date': self.date,
            'account_id': self.analytic_account_id.id,
            'tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
            'unit_amount': self.quantity,
            'product_id': self.product_id and self.product_id.id or False,
            'product_uom_id': self.product_uom_id and self.product_uom_id.id or False,
            'amount': self.company_currency_id.with_context(date=self.date or fields.Date.context_today(self)).compute(amount, self.analytic_account_id.currency_id) if self.analytic_account_id.currency_id else amount,
            'general_account_id': self.account_id.id,
            'ref': self.ref,
            'move_id': self.id,
            'user_id': self.invoice_id.user_id.id or self._uid,
        }

    @api.model
    def _query_get(self, domain=None):
        context = dict(self._context or {})
        domain = domain and safe_eval(str(domain)) or []

        date_field = 'date'
        if context.get('aged_balance'):
            date_field = 'date_maturity'
        if context.get('date_to'):
            domain += [(date_field, '<=', context['date_to'])]
        if context.get('date_from'):
            if not context.get('strict_range'):
                domain += ['|', (date_field, '>=', context['date_from']), ('account_id.user_type_id.include_initial_balance', '=', True)]
            elif context.get('initial_bal'):
                domain += [(date_field, '<', context['date_from'])]
            else:
                domain += [(date_field, '>=', context['date_from'])]

        if context.get('journal_ids'):
            domain += [('journal_id', 'in', context['journal_ids'])]

        state = context.get('state')
        if state and state.lower() != 'all':
            domain += [('move_id.state', '=', state)]

        if context.get('company_id'):
            domain += [('company_id', '=', context['company_id'])]

        if 'company_ids' in context:
            domain += [('company_id', 'in', context['company_ids'])]

        if context.get('reconcile_date'):
            domain += ['|', ('reconciled', '=', False), '|', ('matched_debit_ids.create_date', '>', context['reconcile_date']), ('matched_credit_ids.create_date', '>', context['reconcile_date'])]

        if context.get('account_tag_ids'):
            domain += [('account_id.tag_ids', 'in', context['account_tag_ids'].ids)]

        if context.get('analytic_tag_ids'):
            domain += ['|', ('analytic_account_id.tag_ids', 'in', context['analytic_tag_ids'].ids), ('analytic_tag_ids', 'in', context['analytic_tag_ids'].ids)]

        if context.get('analytic_account_ids'):
            domain += [('analytic_account_id', 'in', context['analytic_account_ids'].ids)]

        where_clause = ""
        where_clause_params = []
        tables = ''
        if domain:
            query = self._where_calc(domain)
            tables, where_clause, where_clause_params = query.get_sql()
        return tables, where_clause, where_clause_params

    @api.multi
    def open_reconcile_view(self):
        [action] = self.env.ref('account.action_account_moves_all_a').read()
        ids = []
        for aml in self:
            if aml.account_id.reconcile:
                ids.extend([r.debit_move_id.id for r in aml.matched_debit_ids] if aml.credit > 0 else [r.credit_move_id.id for r in aml.matched_credit_ids])
                ids.append(aml.id)
        action['domain'] = [('id', 'in', ids)]
        return action


class AccountPartialReconcile(models.Model):
    _name = "account.partial.reconcile"
    _description = "Partial Reconcile"

    debit_move_id = fields.Many2one('account.move.line', index=True, required=True)
    credit_move_id = fields.Many2one('account.move.line', index=True, required=True)
    amount = fields.Monetary(currency_field='company_currency_id', help="Amount concerned by this matching. Assumed to be always positive")
    amount_currency = fields.Monetary(string="Amount in Currency")
    currency_id = fields.Many2one('res.currency', string='Currency')
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True,
        help='Utility field to express amount currency')
    company_id = fields.Many2one('res.company', related='debit_move_id.company_id', store=True, string='Currency')
    full_reconcile_id = fields.Many2one('account.full.reconcile', string="Full Reconcile", copy=False)

    @api.multi
    def _prepare_exchange_diff_line_to_reconcile(self, amount_diff, currency, diff_in_currency, move):
        self.ensure_one()
        return {
            'name': _('Currency exchange rate difference'),
            'debit': amount_diff < 0 and -amount_diff or 0.0,
            'credit': amount_diff > 0 and amount_diff or 0.0,
            'account_id': self.debit_move_id.account_id.id,
            'move_id': move.id,
            'currency_id': currency.id,
            'amount_currency': -diff_in_currency,
            'partner_id': self.debit_move_id.partner_id.id,
        }

    @api.multi
    def _prepare_exchange_diff_move_line(self, amount_diff, currency, diff_in_currency, move):
        self.ensure_one()
        exchange_journal = self.company_id.currency_exchange_journal_id
        return {
            'name': _('Currency exchange rate difference'),
            'debit': amount_diff > 0 and amount_diff or 0.0,
            'credit': amount_diff < 0 and -amount_diff or 0.0,
            'account_id':  amount_diff > 0 and exchange_journal.default_debit_account_id.id or exchange_journal.default_credit_account_id.id,
            'move_id': move.id,
            'currency_id': currency.id,
            'amount_currency': diff_in_currency,
            'partner_id': self.debit_move_id.partner_id.id,
        }

    @api.multi
    def _prepare_exchange_diff_move(self, move_date):
        self.ensure_one()
        res = {'journal_id': self.company_id.currency_exchange_journal_id.id}
        # The move date should be the maximum date between payment and invoice
        # (in case of payment in advance). However, we should make sure the
        # move date is not recorded after the end of year closing.
        if move_date > self.company_id.fiscalyear_lock_date:
            res['date'] = move_date
        return res

    @api.multi
    def _prepare_exchange_diff_partial_reconcile(self, aml, line_to_reconcile, currency):
        self.ensure_one()
        return {
            'debit_move_id': aml.credit and line_to_reconcile.id or aml.id,
            'credit_move_id': aml.debit and line_to_reconcile.id or aml.id,
            'amount': abs(aml.amount_residual),
            'amount_currency': abs(aml.amount_residual_currency),
            'currency_id': currency.id,
        }

    def create_exchange_rate_entry(self, aml_to_fix, amount_diff, diff_in_currency, currency, move_date):
        """
        Automatically create a journal entry to book the exchange rate
        difference. That new journal entry is made in the company
        `currency_exchange_journal_id` and one of its journal items is
        matched with the other lines to balance the full reconciliation.
        :param aml_to_fix: account.move.line
        :param amount_diff: float
        :param diff_in_currency: float
        :param currency: res.currency
        :param move_date: date
        :return: account.move.line to reconcile and account.partial.reconcile
        """
        for rec in self:
            if not rec.company_id.currency_exchange_journal_id:
                raise UserError(_("You should configure the 'Exchange Rate Journal' in the accounting settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
            if not self.company_id.income_currency_exchange_account_id.id:
                raise UserError(_("You should configure the 'Gain Exchange Rate Account' in the accounting settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
            if not self.company_id.expense_currency_exchange_account_id.id:
                raise UserError(_("You should configure the 'Loss Exchange Rate Account' in the accounting settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))

            move = rec.env['account.move'].create(
                rec._prepare_exchange_diff_move(move_date=move_date))

            amount_diff = rec.company_id.currency_id.round(amount_diff)
            diff_in_currency = currency.round(diff_in_currency)
            aml_model = rec.env['account.move.line']
            aml_model.with_context(check_move_validity=False).create(
                rec._prepare_exchange_diff_move_line(
                    amount_diff=amount_diff,
                    currency=currency,
                    diff_in_currency=diff_in_currency,
                    move=move))

            line_to_reconcile = aml_model.create(
                rec._prepare_exchange_diff_line_to_reconcile(
                    amount_diff=amount_diff,
                    currency=currency,
                    diff_in_currency=diff_in_currency,
                    move=move))

            for aml in aml_to_fix:
                partial_rec = rec.env['account.partial.reconcile'].create(
                    rec._prepare_exchange_diff_partial_reconcile(
                        aml=aml,
                        line_to_reconcile=line_to_reconcile,
                        currency=currency)
                )
            move.post()
        return line_to_reconcile, partial_rec

    def create_tax_cash_basis_entry(self, percentage_before_rec):
        self.ensure_one()
        move_date = self.debit_move_id.date
        newly_created_move = self.env['account.move']
        for move in (self.debit_move_id.move_id, self.credit_move_id.move_id):
            #move_date is the max of the 2 reconciled items
            if move_date < move.date:
                move_date = move.date
            for line in move.line_ids:
                #TOCHECK: normal and cash basis taxes shoudn't be mixed together (on the same invoice line for example) as it will
                # create reporting issues. Not sure of the behavior to implement in that case, though.
                if not line.tax_exigible:
                    percentage_before = percentage_before_rec[move.id]
                    percentage_after = line._get_matched_percentage()[move.id]
                    #amount is the current cash_basis amount minus the one before the reconciliation
                    amount = line.balance * percentage_after - line.balance * percentage_before
                    rounded_amt = line.company_id.currency_id.round(amount)
                    if line.tax_line_id and line.tax_line_id.use_cash_basis:
                        if not newly_created_move:
                            newly_created_move = self._create_tax_basis_move()
                        #create cash basis entry for the tax line
                        to_clear_aml = self.env['account.move.line'].with_context(check_move_validity=False).create({
                            'name': line.move_id.name,
                            'debit': abs(rounded_amt) if rounded_amt < 0 else 0.0,
                            'credit': rounded_amt if rounded_amt > 0 else 0.0,
                            'account_id': line.account_id.id,
                            'tax_exigible': True,
                            'amount_currency': self.amount_currency and line.currency_id.round(-line.amount_currency * amount / line.balance) or 0.0,
                            'currency_id': line.currency_id.id,
                            'move_id': newly_created_move.id,
                            'partner_id': line.partner_id.id,
                            })
                        # Group by cash basis account and tax
                        self.env['account.move.line'].with_context(check_move_validity=False).create({
                            'name': line.name,
                            'debit': rounded_amt if rounded_amt > 0 else 0.0,
                            'credit': abs(rounded_amt) if rounded_amt < 0 else 0.0,
                            'account_id': line.tax_line_id.cash_basis_account.id,
                            'tax_line_id': line.tax_line_id.id,
                            'tax_exigible': True,
                            'amount_currency': self.amount_currency and line.currency_id.round(line.amount_currency * amount / line.balance) or 0.0,
                            'currency_id': line.currency_id.id,
                            'move_id': newly_created_move.id,
                            'partner_id': line.partner_id.id,
                        })
                        if line.account_id.reconcile:
                            #setting the account to allow reconciliation will help to fix rounding errors
                            to_clear_aml |= line
                            to_clear_aml.reconcile()

                    if any([tax.use_cash_basis for tax in line.tax_ids]):
                        if not newly_created_move:
                            newly_created_move = self._create_tax_basis_move()
                        #create cash basis entry for the base
                        for tax in line.tax_ids:
                            self.env['account.move.line'].with_context(check_move_validity=False).create({
                                'name': line.name,
                                'debit': rounded_amt > 0 and rounded_amt or 0.0,
                                'credit': rounded_amt < 0 and abs(rounded_amt) or 0.0,
                                'account_id': line.account_id.id,
                                'tax_exigible': True,
                                'tax_ids': [(6, 0, [tax.id])],
                                'move_id': newly_created_move.id,
                                'currency_id': line.currency_id.id,
                                'amount_currency': self.amount_currency and line.currency_id.round(line.amount_currency * amount / line.balance) or 0.0,
                                'partner_id': line.partner_id.id,
                            })
                            self.env['account.move.line'].with_context(check_move_validity=False).create({
                                'name': line.name,
                                'credit': rounded_amt > 0 and rounded_amt or 0.0,
                                'debit': rounded_amt < 0 and abs(rounded_amt) or 0.0,
                                'account_id': line.account_id.id,
                                'tax_exigible': True,
                                'move_id': newly_created_move.id,
                                'currency_id': line.currency_id.id,
                                'amount_currency': self.amount_currency and line.currency_id.round(-line.amount_currency * amount / line.balance) or 0.0,
                                'partner_id': line.partner_id.id,
                            })
            if newly_created_move:
                if move_date > self.company_id.period_lock_date and newly_created_move.date != move_date:
                    # The move date should be the maximum date between payment and invoice (in case
                    # of payment in advance). However, we should make sure the move date is not
                    # recorded before the period lock date as the tax statement for this period is
                    # probably already sent to the estate.
                    newly_created_move.write({'date': move_date})
                # post move
                newly_created_move.post()

    def _create_tax_basis_move(self):
        # Check if company_journal for cash basis is set if not, raise exception
        if not self.company_id.tax_cash_basis_journal_id:
            raise UserError(_('There is no tax cash basis journal defined '
                              'for this company: "%s" \nConfigure it in Accounting/Configuration/Settings') %
                            (self.company_id.name))
        move_vals = {
            'journal_id': self.company_id.tax_cash_basis_journal_id.id,
            'tax_cash_basis_rec_id': self.id,
        }
        return self.env['account.move'].create(move_vals)

    @api.model
    def create(self, vals):
        aml = []
        if vals.get('debit_move_id', False):
            aml.append(vals['debit_move_id'])
        if vals.get('credit_move_id', False):
            aml.append(vals['credit_move_id'])
        # Get value of matched percentage from both move before reconciliating
        lines = self.env['account.move.line'].browse(aml)
        if lines[0].account_id.internal_type in ('receivable', 'payable'):
            percentage_before_rec = lines._get_matched_percentage()
        # Reconcile
        res = super(AccountPartialReconcile, self).create(vals)
        # if the reconciliation is a matching on a receivable or payable account, eventually create a tax cash basis entry
        if lines[0].account_id.internal_type in ('receivable', 'payable'):
            res.create_tax_cash_basis_entry(percentage_before_rec)
        if self._context.get('skip_full_reconcile_check'):
            #when running the manual reconciliation wizard, don't check the partials separately for full
            #reconciliation or exchange rate because it is handled manually after the whole processing
            return res
        #check if the reconcilation is full
        #first, gather all journal items involved in the reconciliation just created
        partial_rec_set = OrderedDict.fromkeys([x for x in res])
        aml_set = self.env['account.move.line']
        total_debit = 0
        total_credit = 0
        total_amount_currency = 0
        #make sure that all partial reconciliations share the same secondary currency otherwise it's not
        #possible to compute the exchange difference entry and it has to be done manually.
        currency = list(partial_rec_set)[0].currency_id
        maxdate = None
        aml_to_balance = None
        for partial_rec in partial_rec_set:
            if partial_rec.currency_id != currency:
                #no exchange rate entry will be created
                currency = None
            for aml in [partial_rec.debit_move_id, partial_rec.credit_move_id]:
                if aml not in aml_set:
                    if aml.amount_residual or aml.amount_residual_currency:
                        aml_to_balance = aml
                    maxdate = max(aml.date, maxdate)
                    total_debit += aml.debit
                    total_credit += aml.credit
                    aml_set |= aml
                    if aml.currency_id and aml.currency_id == currency:
                        total_amount_currency += aml.amount_currency
                    elif partial_rec.currency_id and partial_rec.currency_id == currency:
                        #if the aml has no secondary currency but is reconciled with other journal item(s) in secondary currency, the amount
                        #currency is recorded on the partial rec and in order to check if the reconciliation is total, we need to convert the
                        #aml.balance in that foreign currency
                        total_amount_currency += aml.company_id.currency_id.with_context(date=aml.date).compute(aml.balance, partial_rec.currency_id)
                for x in aml.matched_debit_ids | aml.matched_credit_ids:
                    partial_rec_set[x] = None
        partial_rec_ids = [x.id for x in partial_rec_set.keys()]
        aml_ids = aml_set.ids
        #then, if the total debit and credit are equal, or the total amount in currency is 0, the reconciliation is full
        digits_rounding_precision = aml_set[0].company_id.currency_id.rounding
        if (currency and float_is_zero(total_amount_currency, precision_rounding=currency.rounding)) or float_compare(total_debit, total_credit, precision_rounding=digits_rounding_precision) == 0:
            exchange_move_id = False
            exchange_partial_rec_id = False
            if currency and aml_to_balance:
                #eventually create a journal entry to book the difference due to foreign currency's exchange rate that fluctuates
                rate_diff_aml, rate_diff_partial_rec = partial_rec.create_exchange_rate_entry(aml_to_balance, total_debit - total_credit, total_amount_currency, currency, maxdate)
                aml_ids.append(rate_diff_aml.id)
                partial_rec_ids.append(rate_diff_partial_rec.id)
                exchange_move_id = rate_diff_aml.move_id.id
                exchange_partial_rec_id = rate_diff_partial_rec.id
            #mark the reference of the full reconciliation on the partial ones and on the entries
            self.env['account.full.reconcile'].with_context(check_move_validity=False).create({
                'partial_reconcile_ids': [(4, p_id) for p_id in partial_rec_ids],
                'reconciled_line_ids': [(4, a_id) for a_id in aml_ids],
                'exchange_move_id': exchange_move_id,
                'exchange_partial_rec_id': exchange_partial_rec_id,
            })
        return res

    @api.multi
    def unlink(self):
        """ When removing a partial reconciliation, also unlink its full reconciliation if it exists """
        full_to_unlink = self.env['account.full.reconcile']
        for rec in self:
            #without the deleted partial reconciliations, the full reconciliation won't be full anymore
            if rec.full_reconcile_id:
                full_to_unlink |= rec.full_reconcile_id
        #reverse the tax basis move created at the reconciliation time
        move = self.env['account.move'].search([('tax_cash_basis_rec_id', 'in', self._ids)])
        move.reverse_moves()
        res = super(AccountPartialReconcile, self).unlink()
        if full_to_unlink:
            full_to_unlink.unlink()
        return res


class AccountFullReconcile(models.Model):
    _name = "account.full.reconcile"
    _description = "Full Reconcile"

    name = fields.Char(string='Number', required=True, copy=False, default=lambda self: self.env['ir.sequence'].next_by_code('account.reconcile'))
    partial_reconcile_ids = fields.One2many('account.partial.reconcile', 'full_reconcile_id', string='Reconciliation Parts')
    reconciled_line_ids = fields.One2many('account.move.line', 'full_reconcile_id', string='Matched Journal Items')
    exchange_move_id = fields.Many2one('account.move')
    exchange_partial_rec_id = fields.Many2one('account.partial.reconcile')

    @api.multi
    def unlink(self):
        """ When removing a full reconciliation, we need to revert the eventual journal entries we created to book the
            fluctuation of the foreign currency's exchange rate.
            We need also to reconcile together the origin currency difference line and its reversal in order to completly
            cancel the currency difference entry on the partner account (otherwise it will still appear on the aged balance
            for example).
        """
        for rec in self:
            if rec.exchange_move_id:
                # reverse the exchange rate entry after de-referencing it to avoid looping
                # (reversing will cause a nested attempt to drop the full reconciliation)
                to_reverse = rec.exchange_move_id
                rec.exchange_move_id = False
                to_reverse.reverse_moves()
        return super(AccountFullReconcile, self).unlink()
