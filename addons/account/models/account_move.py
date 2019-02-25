# -*- coding: utf-8 -*-

import time
from datetime import date
from collections import OrderedDict
from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.tools.misc import formatLang, format_date
from odoo.tools import float_is_zero, float_compare
from odoo.tools.safe_eval import safe_eval
from odoo.addons import decimal_precision as dp
from lxml import etree

#----------------------------------------------------------
# Entries
#----------------------------------------------------------

class AccountMove(models.Model):
    _name = "account.move"
    _description = "Journal Entries"
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
            precision_currency = move.currency_id or move.company_id.currency_id
            if float_is_zero(total_amount, precision_rounding=precision_currency.rounding):
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
            return self.env['account.journal'].search([('company_id', '=', self.env.user.company_id.id), ('type', '=', self.env.context['default_journal_type'])], limit=1).id

    @api.multi
    @api.depends('line_ids.partner_id')
    def _compute_partner_id(self):
        for move in self:
            partner = move.line_ids.mapped('partner_id')
            move.partner_id = partner.id if len(partner) == 1 else False

    @api.onchange('date')
    def _onchange_date(self):
        '''On the form view, a change on the date will trigger onchange() on account.move
        but not on account.move.line even the date field is related to account.move.
        Then, trigger the _onchange_amount_currency manually.
        '''
        self.line_ids._onchange_amount_currency()

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
    company_id = fields.Many2one('res.company', related='journal_id.company_id', string='Company', store=True, readonly=True)
    matched_percentage = fields.Float('Percentage Matched', compute='_compute_matched_percentage', digits=0, store=True, readonly=True, help="Technical field used in cash basis method")
    # Dummy Account field to search on account.move by account_id
    dummy_account_id = fields.Many2one('account.account', related='line_ids.account_id', string='Account', store=False, readonly=True)
    tax_cash_basis_rec_id = fields.Many2one(
        'account.partial.reconcile',
        string='Tax Cash Basis Entry of',
        help="Technical field used to keep track of the tax cash basis reconciliation. "
        "This is needed when cancelling the source: it will post the inverse journal entry to cancel that part too.")
    auto_reverse = fields.Boolean(string='Reverse Automatically', default=False, help='If this checkbox is ticked, this entry will be automatically reversed at the reversal date you defined.')
    reverse_date = fields.Date(string='Reversal Date', help='Date of the reverse accounting entry.')
    reverse_entry_id = fields.Many2one('account.move', String="Reverse entry", store=True, readonly=True)
    tax_type_domain = fields.Char(store=False, help='Technical field used to have a dynamic taxes domain on the form view.')

    @api.constrains('line_ids', 'journal_id', 'auto_reverse', 'reverse_date')
    def _validate_move_modification(self):
        if 'posted' in self.mapped('line_ids.payment_id.state'):
            raise ValidationError(_("You cannot modify a journal entry linked to a posted payment."))

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        self.tax_type_domain = self.journal_id.type if self.journal_id.type in ('sale', 'purchase') else None

    @api.onchange('line_ids')
    def _onchange_line_ids(self):
        '''Compute additional lines corresponding to the taxes set on the line_ids.

        For example, add a line with 1000 debit and 15% tax, this onchange will add a new
        line with 150 debit.
        '''
        def _str_to_list(string):
            #remove heading and trailing brackets and return a list of int. This avoid calling safe_eval on untrusted field content
            string = string[1:-1]
            if string:
                return [int(x) for x in string.split(',')]
            return []

        def _build_grouping_key(line):
            #build a string containing all values used to create the tax line
            return str(line.tax_ids.ids) + '-' + str(line.analytic_tag_ids.ids) + '-' + (line.analytic_account_id and str(line.analytic_account_id.id) or '')

        def _parse_grouping_key(line):
            # Retrieve values computed the last time this method has been run.
            if not line.tax_line_grouping_key:
                return {'tax_ids': [], 'tag_ids': [], 'analytic_account_id': False}
            tax_str, tags_str, analytic_account_str = line.tax_line_grouping_key.split('-')
            return {
                'tax_ids': _str_to_list(tax_str),
                'tag_ids': _str_to_list(tags_str),
                'analytic_account_id': analytic_account_str and int(analytic_account_str) or False,
            }

        def _find_existing_tax_line(line_ids, tax, tag_ids, analytic_account_id):
            if tax.analytic:
                return line_ids.filtered(lambda x: x.tax_line_id == tax and x.analytic_tag_ids.ids == tag_ids and x.analytic_account_id.id == analytic_account_id)
            return line_ids.filtered(lambda x: x.tax_line_id == tax)

        def _get_lines_to_sum(line_ids, tax, tag_ids, analytic_account_id):
            if tax.analytic:
                return line_ids.filtered(lambda x: tax in x.tax_ids and x.analytic_tag_ids.ids == tag_ids and x.analytic_account_id.id == analytic_account_id)
            return line_ids.filtered(lambda x: tax in x.tax_ids)

        def _get_tax_account(tax, amount):
            if tax.tax_exigibility == 'on_payment' and tax.cash_basis_account_id:
                return tax.cash_basis_account_id
            if tax.type_tax_use == 'purchase':
                return tax.refund_account_id if amount < 0 else tax.account_id
            return tax.refund_account_id if amount >= 0 else tax.account_id

        # Cache the already computed tax to avoid useless recalculation.
        processed_taxes = self.env['account.tax']

        self.ensure_one()
        for line in self.line_ids.filtered(lambda x: x.recompute_tax_line):
            # Retrieve old field values.
            parsed_key = _parse_grouping_key(line)

            # Unmark the line.
            line.recompute_tax_line = False

            # Manage group of taxes.
            group_taxes = line.tax_ids.filtered(lambda t: t.amount_type == 'group')
            children_taxes = group_taxes.mapped('children_tax_ids')
            if children_taxes:
                line.tax_ids += children_taxes - line.tax_ids
                # Because the taxes on the line changed, we need to recompute them.
                processed_taxes -= children_taxes

            # Get the taxes to process.
            taxes = self.env['account.tax'].browse(parsed_key['tax_ids'])
            taxes += line.tax_ids.filtered(lambda t: t not in taxes)
            taxes += children_taxes.filtered(lambda t: t not in taxes)
            to_process_taxes = (taxes - processed_taxes).filtered(lambda t: t.amount_type != 'group')
            processed_taxes += to_process_taxes

            # Process taxes.
            for tax in to_process_taxes:
                tax_line = _find_existing_tax_line(self.line_ids, tax, parsed_key['tag_ids'], parsed_key['analytic_account_id'])
                lines_to_sum = _get_lines_to_sum(self.line_ids, tax, parsed_key['tag_ids'], parsed_key['analytic_account_id'])

                if not lines_to_sum:
                    # Drop tax line because the originator tax is no longer used.
                    self.line_ids -= tax_line
                    continue

                balance = sum([l.balance for l in lines_to_sum])

                # Compute the tax amount one by one.
                quantity = len(lines_to_sum) if tax.amount_type == 'fixed' else 1
                taxes_vals = tax.compute_all(balance,
                    quantity=quantity, currency=line.currency_id, product=line.product_id, partner=line.partner_id)

                if tax_line:
                    # Update the existing tax_line.
                    if balance:
                        # Update the debit/credit amount according to the new balance.
                        if taxes_vals.get('taxes'):
                            amount = taxes_vals['taxes'][0]['amount']
                            account = _get_tax_account(tax, amount) or line.account_id
                            tax_line.debit = amount > 0 and amount or 0.0
                            tax_line.credit = amount < 0 and -amount or 0.0
                            tax_line.account_id = account
                    else:
                        # Reset debit/credit in case of the originator line is temporary set to 0 in both debit/credit.
                        tax_line.debit = tax_line.credit = 0.0
                elif taxes_vals.get('taxes'):
                    # Create a new tax_line.

                    amount = taxes_vals['taxes'][0]['amount']
                    account = _get_tax_account(tax, amount) or line.account_id
                    tax_vals = taxes_vals['taxes'][0]

                    name = tax_vals['name']
                    line_vals = {
                        'account_id': account.id,
                        'name': name,
                        'tax_line_id': tax_vals['id'],
                        'partner_id': line.partner_id.id,
                        'debit': amount > 0 and amount or 0.0,
                        'credit': amount < 0 and -amount or 0.0,
                        'analytic_account_id': line.analytic_account_id.id if tax.analytic else False,
                        'analytic_tag_ids': line.analytic_tag_ids.ids if tax.analytic else False,
                        'move_id': self.id,
                        'tax_exigible': tax.tax_exigibility == 'on_invoice',
                        'company_id': self.company_id.id,
                        'company_currency_id': self.company_id.currency_id.id,
                    }
                    # N.B. currency_id/amount_currency are not set because if we have two lines with the same tax
                    # and different currencies, we have no idea which currency set on this line.
                    self.env['account.move.line'].new(line_vals)

            # Keep record of the values used as taxes the last time this method has been run.
            line.tax_line_grouping_key = _build_grouping_key(line)

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
    def post(self, invoice=False):
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
                                raise UserError(_('Please define a sequence for the credit notes'))
                            sequence = journal.refund_sequence_id

                        new_name = sequence.with_context(ir_sequence_date=move.date).next_by_id()
                    else:
                        raise UserError(_('Please define a sequence on the journal.'))

                if new_name:
                    move.name = new_name

            if move == move.company_id.account_opening_move_id and not move.company_id.account_bank_reconciliation_start:
                # For opening moves, we set the reconciliation date threshold
                # to the move's date if it wasn't already set (we don't want
                # to have to reconcile all the older payments -made before
                # installing Accounting- with bank statements)
                move.company_id.account_bank_reconciliation_start = move.date

        return self.write({'state': 'posted'})

    @api.multi
    def action_post(self):
        if self.mapped('line_ids.payment_id'):
            if any(self.mapped('journal_id.post_at_bank_rec')):
                raise UserError(_("A payment journal entry generated in a journal configured to post entries only when payments are reconciled with a bank statement cannot be manually posted. Those will be posted automatically after performing the bank reconciliation."))
        return self.post()

    @api.multi
    def button_cancel(self):
        for move in self:
            if not move.journal_id.update_posted:
                raise UserError(_('You cannot modify a posted entry of this journal.\nFirst you should set the journal to allow cancelling entries.'))
            # We remove all the analytics entries for this journal
            move.mapped('line_ids.analytic_line_ids').unlink()
        if self.ids:
            self.check_access_rights('write')
            self.check_access_rule('write')
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
            lock_date = max(move.company_id.period_lock_date or date.min, move.company_id.fiscalyear_lock_date or date.min)
            if self.user_has_groups('account.group_account_manager'):
                lock_date = move.company_id.fiscalyear_lock_date
            if move.date <= (lock_date or date.min):
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
        prec = self.env.user.company_id.currency_id.decimal_places

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
    def _reverse_move(self, date=None, journal_id=None, auto=False):
        self.ensure_one()
        with self.env.norecompute():
            reversed_move = self.copy(default={
                'date': date,
                'journal_id': journal_id.id if journal_id else self.journal_id.id,
                'ref': (_('Automatic reversal of: %s') if auto else _('Reversal of: %s')) % (self.name),
                'auto_reverse': False})
            for acm_line in reversed_move.line_ids.with_context(check_move_validity=False):
                acm_line.write({
                    'debit': acm_line.credit,
                    'credit': acm_line.debit,
                    'amount_currency': -acm_line.amount_currency
                })
            self.reverse_entry_id = reversed_move
        self.recompute()
        return reversed_move

    @api.multi
    def reverse_moves(self, date=None, journal_id=None, auto=False):
        date = date or fields.Date.today()
        reversed_moves = self.env['account.move']
        for ac_move in self:
            #unreconcile all lines reversed
            aml = ac_move.line_ids.filtered(lambda x: x.account_id.reconcile or x.account_id.internal_type == 'liquidity')
            aml.remove_move_reconcile()
            reversed_move = ac_move._reverse_move(date=date,
                                                  journal_id=journal_id,
                                                  auto=auto)
            reversed_moves |= reversed_move
            #reconcile together the reconcilable (or the liquidity aml) and their newly created counterpart
            for account in set([x.account_id for x in aml]):
                to_rec = aml.filtered(lambda y: y.account_id == account)
                to_rec |= reversed_move.line_ids.filtered(lambda y: y.account_id == account)
                #reconciliation will be full, so speed up the computation by using skip_full_reconcile_check in the context
                to_rec.reconcile()
        if reversed_moves:
            reversed_moves._post_validate()
            reversed_moves.post()
            return [x.id for x in reversed_moves]
        return []

    @api.multi
    def open_reconcile_view(self):
        return self.line_ids.open_reconcile_view()

    # FIXME: Clarify me and change me in master
    @api.multi
    def action_duplicate(self):
        self.ensure_one()
        action = self.env.ref('account.action_move_journal_line').read()[0]
        action['target'] = 'inline'
        action['context'] = dict(self.env.context)
        action['context']['view_no_maturity'] = False
        action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
        action['res_id'] = self.copy().id
        return action

    @api.model
    def _run_reverses_entries(self):
        ''' This method is called from a cron job. '''
        records = self.search([
            ('state', '=', 'posted'),
            ('auto_reverse', '=', True),
            ('reverse_date', '<=', fields.Date.today()),
            ('reverse_entry_id', '=', False)])
        for move in records:
            date = None
            if move.reverse_date and (not self.env.user.company_id.period_lock_date or move.reverse_date > self.env.user.company_id.period_lock_date):
                date = move.reverse_date
            move.reverse_moves(date=date, auto=True)

    @api.multi
    def action_view_reverse_entry(self):
        action = self.env.ref('account.action_move_journal_line').read()[0]
        action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
        action['res_id'] = self.reverse_entry_id.id
        return action

class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _description = "Journal Item"
    _order = "date desc, id desc"

    @api.onchange('debit', 'credit', 'tax_ids', 'analytic_account_id', 'analytic_tag_ids')
    def onchange_tax_ids_create_aml(self):
        for line in self:
            line.recompute_tax_line = True

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

    @api.depends('debit', 'credit', 'amount_currency', 'currency_id', 'matched_debit_ids', 'matched_credit_ids', 'matched_debit_ids.amount', 'matched_credit_ids.amount', 'move_id.state')
    def _amount_residual(self):
        """ Computes the residual amount of a move line from a reconcilable account in the company currency and the line's currency.
            This amount will be 0 for fully reconciled lines or lines from a non-reconcilable account, the original line amount
            for unreconciled lines, and something in-between for partially reconciled lines.
        """
        for line in self:
            if not line.account_id.reconcile and line.account_id.internal_type != 'liquidity':
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
                if line.currency_id and line.amount_currency:
                    if partial_line.currency_id and partial_line.currency_id == line.currency_id:
                        amount_residual_currency += sign_partial_line * partial_line.amount_currency
                    else:
                        if line.balance and line.amount_currency:
                            rate = line.amount_currency / line.balance
                        else:
                            date = partial_line.credit_move_id.date if partial_line.debit_move_id == line else partial_line.debit_move_id.date
                            rate = line.currency_id.with_context(date=date).rate
                        amount_residual_currency += sign_partial_line * line.currency_id.round(partial_line.amount * rate)

            #computing the `reconciled` field.
            reconciled = False
            digits_rounding_precision = line.company_id.currency_id.rounding
            if (line.matched_debit_ids or line.matched_credit_ids) and float_is_zero(amount, precision_rounding=digits_rounding_precision):
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

    @api.depends('move_id.line_ids', 'move_id.line_ids.tax_line_id', 'move_id.line_ids.debit', 'move_id.line_ids.credit')
    def _compute_tax_base_amount(self):
        for move_line in self:
            if move_line.tax_line_id:
                base_lines = move_line.move_id.line_ids.filtered(lambda line: move_line.tax_line_id in line.tax_ids)
                move_line.tax_base_amount = abs(sum(base_lines.mapped('balance')))
            else:
                move_line.tax_base_amount = 0

    @api.depends('move_id')
    def _compute_parent_state(self):
        for record in self.filtered('move_id'):
            record.parent_state = record.move_id.state

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
    quantity = fields.Float(digits=dp.get_precision('Product Unit of Measure'),
        help="The optional quantity expressed by this line, eg: number of product sold. The quantity is not a legal requirement but is very useful for some reports.")
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
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
    tax_base_amount = fields.Monetary(string="Base Amount", compute='_compute_tax_base_amount', currency_field='company_currency_id', store=True)
    account_id = fields.Many2one('account.account', string='Account', required=True, index=True,
        ondelete="cascade", domain=[('deprecated', '=', False)], default=lambda self: self._context.get('account_id', False))
    move_id = fields.Many2one('account.move', string='Journal Entry', ondelete="cascade",
        help="The move of this entry line.", index=True, required=True, auto_join=True)
    narration = fields.Text(related='move_id.narration', string='Narration', readonly=False)
    ref = fields.Char(related='move_id.ref', string='Reference', store=True, copy=False, index=True, readonly=False)
    payment_id = fields.Many2one('account.payment', string="Originator Payment", help="Payment that created this entry", copy=False)
    statement_line_id = fields.Many2one('account.bank.statement.line', index=True, string='Bank statement line reconciled with this entry', copy=False, readonly=True)
    statement_id = fields.Many2one('account.bank.statement', related='statement_line_id.statement_id', string='Statement', store=True,
        help="The bank statement used for bank reconciliation", index=True, copy=False)
    reconciled = fields.Boolean(compute='_amount_residual', store=True)
    full_reconcile_id = fields.Many2one('account.full.reconcile', string="Matching Number", copy=False)
    matched_debit_ids = fields.One2many('account.partial.reconcile', 'credit_move_id', String='Matched Debits',
        help='Debit journal items that are matched with this journal item.')
    matched_credit_ids = fields.One2many('account.partial.reconcile', 'debit_move_id', String='Matched Credits',
        help='Credit journal items that are matched with this journal item.')
    journal_id = fields.Many2one('account.journal', related='move_id.journal_id', string='Journal', readonly=False,
        index=True, store=True, copy=False)  # related is required
    blocked = fields.Boolean(string='No Follow-up', default=False,
        help="You can check this box to mark this journal item as a litigation with the associated partner")
    date_maturity = fields.Date(string='Due date', index=True, required=True, copy=False,
        help="This field is used for payable and receivable journal entries. You can put the limit date for the payment of this line.")
    date = fields.Date(related='move_id.date', string='Date', index=True, store=True, copy=False, readonly=False)  # related is required
    analytic_line_ids = fields.One2many('account.analytic.line', 'move_id', string='Analytic lines', oldname="analytic_lines")
    tax_ids = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])
    tax_line_id = fields.Many2one('account.tax', string='Originator tax', ondelete='restrict')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', index=True)
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    company_id = fields.Many2one('res.company', related='account_id.company_id', string='Company', store=True, readonly=True)
    counterpart = fields.Char("Counterpart", compute='_get_counterpart', help="Compute the counter part accounts of this journal item for this journal entry. This can be needed in reports.")

    # TODO: put the invoice link and partner_id on the account_move
    invoice_id = fields.Many2one('account.invoice', oldname="invoice")
    partner_id = fields.Many2one('res.partner', string='Partner', ondelete='restrict')
    user_type_id = fields.Many2one('account.account.type', related='account_id.user_type_id', index=True, store=True, oldname="user_type", readonly=True)
    tax_exigible = fields.Boolean(string='Appears in VAT report', default=True,
        help="Technical field used to mark a tax line as exigible in the vat report or not (only exigible journal items are displayed). By default all new journal items are directly exigible, but with the feature cash_basis on taxes, some will become exigible only when the payment is recorded.")
    parent_state = fields.Char(compute="_compute_parent_state", help="State of the parent account.move")

    recompute_tax_line = fields.Boolean(store=False, help="Technical field used to know if the tax_ids field has been modified in the UI.")
    tax_line_grouping_key = fields.Char(store=False, string='Old Taxes', help="Technical field used to store the old values of fields used to compute tax lines (in account.move form view) between the moment the user changed it and the moment the ORM reflects that change in its one2many")

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
        for line in self.move_id.resolve_2many_commands(
                'line_ids', self._context['line_ids'], fields=['credit', 'debit']):
            balance += line.get('debit', 0) - line.get('credit', 0)
        if balance < 0:
            rec.update({'debit': -balance})
        if balance > 0:
            rec.update({'credit': balance})
        return rec

    @api.multi
    @api.constrains('currency_id', 'account_id')
    def _check_currency(self):
        for line in self:
            account_currency = line.account_id.currency_id
            if account_currency and account_currency != line.company_id.currency_id:
                if not line.currency_id or line.currency_id != account_currency:
                    raise ValidationError(_('The selected account of your Journal Entry forces to provide a secondary currency. You should remove the secondary currency on the account.'))

    @api.multi
    @api.constrains('currency_id', 'amount_currency')
    def _check_currency_and_amount(self):
        for line in self:
            if (line.amount_currency and not line.currency_id):
                raise ValidationError(_("You cannot create journal items with a secondary currency without filling both 'currency' and 'amount currency' fields."))

    @api.multi
    @api.constrains('amount_currency', 'debit', 'credit')
    def _check_currency_amount(self):
        for line in self:
            if line.amount_currency:
                if (line.amount_currency > 0.0 and line.credit > 0.0) or (line.amount_currency < 0.0 and line.debit > 0.0):
                    raise ValidationError(_('The amount expressed in the secondary currency must be positive when account is debited and negative when account is credited.'))

    @api.depends('account_id.user_type_id')
    def _compute_is_unaffected_earnings_line(self):
        for record in self:
            unaffected_earnings_type = self.env.ref("account.data_unaffected_earnings")
            record.is_unaffected_earnings_line = unaffected_earnings_type == record.account_id.user_type_id

    @api.onchange('amount_currency', 'currency_id', 'account_id')
    def _onchange_amount_currency(self):
        '''Recompute the debit/credit based on amount_currency/currency_id and date.
        However, date is a related field on account.move. Then, this onchange will not be triggered
        by the form view by changing the date on the account.move.
        To fix this problem, see _onchange_date method on account.move.
        '''
        for line in self:
            company_currency_id = line.account_id.company_id.currency_id
            amount = line.amount_currency
            if line.currency_id and company_currency_id and line.currency_id != company_currency_id:
                amount = line.currency_id._convert(amount, company_currency_id, line.company_id, line.date or fields.Date.today())
                line.debit = amount > 0 and amount or 0.0
                line.credit = amount < 0 and -amount or 0.0

    ####################################################
    # Reconciliation methods
    ####################################################

    @api.multi
    def check_full_reconcile(self):
        """
        This method check if a move is totally reconciled and if we need to create exchange rate entries for the move.
        In case exchange rate entries needs to be created, one will be created per currency present.
        In case of full reconciliation, all moves belonging to the reconciliation will belong to the same account_full_reconcile object.
        """
        # Get first all aml involved
        part_recs = self.env['account.partial.reconcile'].search(['|', ('debit_move_id', 'in', self.ids), ('credit_move_id', 'in', self.ids)])
        amls = self
        todo = set(part_recs)
        seen = set()
        while todo:
            partial_rec = todo.pop()
            seen.add(partial_rec)
            for aml in [partial_rec.debit_move_id, partial_rec.credit_move_id]:
                if aml not in amls:
                    amls += aml
                    for x in aml.matched_debit_ids | aml.matched_credit_ids:
                        if x not in seen:
                            todo.add(x)
        partial_rec_ids = [x.id for x in seen]
        if not amls:
            return
        # If we have multiple currency, we can only base ourselve on debit-credit to see if it is fully reconciled
        currency = set([a.currency_id for a in amls if a.currency_id.id != False])
        multiple_currency = False
        if len(currency) != 1:
            currency = False
            multiple_currency = True
        else:
            currency = list(currency)[0]
        # Get the sum(debit, credit, amount_currency) of all amls involved
        total_debit = 0
        total_credit = 0
        total_amount_currency = 0
        maxdate = date.min
        to_balance = {}
        for aml in amls:
            total_debit += aml.debit
            total_credit += aml.credit
            maxdate = max(aml.date, maxdate)
            total_amount_currency += aml.amount_currency
            # Convert in currency if we only have one currency and no amount_currency
            if not aml.amount_currency and currency:
                multiple_currency = True
                total_amount_currency += aml.company_id.currency_id._convert(aml.balance, currency, aml.company_id, aml.date)
            # If we still have residual value, it means that this move might need to be balanced using an exchange rate entry
            if aml.amount_residual != 0 or aml.amount_residual_currency != 0:
                if not to_balance.get(aml.currency_id):
                    to_balance[aml.currency_id] = [self.env['account.move.line'], 0]
                to_balance[aml.currency_id][0] += aml
                to_balance[aml.currency_id][1] += aml.amount_residual != 0 and aml.amount_residual or aml.amount_residual_currency
        # Check if reconciliation is total
        # To check if reconciliation is total we have 3 differents use case:
        # 1) There are multiple currency different than company currency, in that case we check using debit-credit
        # 2) We only have one currency which is different than company currency, in that case we check using amount_currency
        # 3) We have only one currency and some entries that don't have a secundary currency, in that case we check debit-credit
        #   or amount_currency.
        digits_rounding_precision = amls[0].company_id.currency_id.rounding
        if (currency and float_is_zero(total_amount_currency, precision_rounding=currency.rounding)) or \
            (multiple_currency and float_compare(total_debit, total_credit, precision_rounding=digits_rounding_precision) == 0):
            exchange_move_id = False
            # Eventually create a journal entry to book the difference due to foreign currency's exchange rate that fluctuates
            if to_balance and any([not float_is_zero(residual, precision_rounding=digits_rounding_precision) for aml, residual in to_balance.values()]):
                exchange_move = self.env['account.move'].create(
                    self.env['account.full.reconcile']._prepare_exchange_diff_move(move_date=maxdate, company=amls[0].company_id))
                part_reconcile = self.env['account.partial.reconcile']
                for aml_to_balance, total in to_balance.values():
                    if total:
                        rate_diff_amls, rate_diff_partial_rec = part_reconcile.create_exchange_rate_entry(aml_to_balance, exchange_move)
                        amls += rate_diff_amls
                        partial_rec_ids += rate_diff_partial_rec.ids
                    else:
                        aml_to_balance.reconcile()
                exchange_move.post()
                exchange_move_id = exchange_move.id
            #mark the reference of the full reconciliation on the exchange rate entries and on the entries
            self.env['account.full.reconcile'].create({
                'partial_reconcile_ids': [(6, 0, partial_rec_ids)],
                'reconciled_line_ids': [(6, 0, amls.ids)],
                'exchange_move_id': exchange_move_id,
            })

    @api.multi
    def _reconcile_lines(self, debit_moves, credit_moves, field):
        """ This function loops on the 2 recordsets given as parameter as long as it
            can find a debit and a credit to reconcile together. It returns the recordset of the
            account move lines that were not reconciled during the process.
        """
        (debit_moves + credit_moves).read([field])
        to_create = []
        cash_basis = debit_moves and debit_moves[0].account_id.internal_type in ('receivable', 'payable') or False
        cash_basis_percentage_before_rec = {}
        dc_vals ={}
        while (debit_moves and credit_moves):
            debit_move = debit_moves[0]
            credit_move = credit_moves[0]
            company_currency = debit_move.company_id.currency_id
            # We need those temporary value otherwise the computation might be wrong below
            temp_amount_residual = min(debit_move.amount_residual, -credit_move.amount_residual)
            temp_amount_residual_currency = min(debit_move.amount_residual_currency, -credit_move.amount_residual_currency)
            dc_vals[(debit_move.id, credit_move.id)] = (debit_move, credit_move, temp_amount_residual_currency)
            amount_reconcile = min(debit_move[field], -credit_move[field])

            #Remove from recordset the one(s) that will be totally reconciled
            # For optimization purpose, the creation of the partial_reconcile are done at the end,
            # therefore during the process of reconciling several move lines, there are actually no recompute performed by the orm
            # and thus the amount_residual are not recomputed, hence we have to do it manually.
            if amount_reconcile == debit_move[field]:
                debit_moves -= debit_move
            else:
                debit_moves[0].amount_residual -= temp_amount_residual
                debit_moves[0].amount_residual_currency -= temp_amount_residual_currency

            if amount_reconcile == -credit_move[field]:
                credit_moves -= credit_move
            else:
                credit_moves[0].amount_residual += temp_amount_residual
                credit_moves[0].amount_residual_currency += temp_amount_residual_currency
            #Check for the currency and amount_currency we can set
            currency = False
            amount_reconcile_currency = 0
            if field == 'amount_residual_currency':
                currency = credit_move.currency_id.id
                amount_reconcile_currency = temp_amount_residual_currency
                amount_reconcile = temp_amount_residual

            if cash_basis:
                tmp_set = debit_move | credit_move
                cash_basis_percentage_before_rec.update(tmp_set._get_matched_percentage())

            to_create.append({
                'debit_move_id': debit_move.id,
                'credit_move_id': credit_move.id,
                'amount': amount_reconcile,
                'amount_currency': amount_reconcile_currency,
                'currency_id': currency,
            })

        cash_basis_subjected = []
        part_rec = self.env['account.partial.reconcile']
        with self.env.norecompute():
            for partial_rec_dict in to_create:
                debit_move, credit_move, amount_residual_currency = dc_vals[partial_rec_dict['debit_move_id'], partial_rec_dict['credit_move_id']]
                # /!\ NOTE: Exchange rate differences shouldn't create cash basis entries
                # i. e: we don't really receive/give money in a customer/provider fashion
                # Since those are not subjected to cash basis computation we process them first
                if not amount_residual_currency and debit_move.currency_id and credit_move.currency_id:
                    part_rec.create(partial_rec_dict)
                else:
                    cash_basis_subjected.append(partial_rec_dict)

            for after_rec_dict in cash_basis_subjected:
                new_rec = part_rec.create(after_rec_dict)
                if cash_basis:
                    new_rec.create_tax_cash_basis_entry(cash_basis_percentage_before_rec)
        self.recompute()

        return debit_moves+credit_moves


    @api.multi
    def auto_reconcile_lines(self):
        # Create list of debit and list of credit move ordered by date-currency
        debit_moves = self.filtered(lambda r: r.debit != 0 or r.amount_currency > 0)
        credit_moves = self.filtered(lambda r: r.credit != 0 or r.amount_currency < 0)
        debit_moves = debit_moves.sorted(key=lambda a: (a.date_maturity or a.date, a.currency_id))
        credit_moves = credit_moves.sorted(key=lambda a: (a.date_maturity or a.date, a.currency_id))
        # Compute on which field reconciliation should be based upon:
        field = self[0].account_id.currency_id and 'amount_residual_currency' or 'amount_residual'
        #if all lines share the same currency, use amount_residual_currency to avoid currency rounding error
        if self[0].currency_id and all([x.amount_currency and x.currency_id == self[0].currency_id for x in self]):
            field = 'amount_residual_currency'
        # Reconcile lines
        ret = self._reconcile_lines(debit_moves, credit_moves, field)
        return ret

    def _check_reconcile_validity(self):
        #Perform all checks on lines
        company_ids = set()
        all_accounts = []
        for line in self:
            company_ids.add(line.company_id.id)
            all_accounts.append(line.account_id)
            if (line.matched_debit_ids or line.matched_credit_ids) and line.reconciled:
                raise UserError(_('You are trying to reconcile some entries that are already reconciled.'))
        if len(company_ids) > 1:
            raise UserError(_('To reconcile the entries company should be the same for all entries.'))
        if len(set(all_accounts)) > 1:
            raise UserError(_('Entries are not from the same account.'))
        if not (all_accounts[0].reconcile or all_accounts[0].internal_type == 'liquidity'):
            raise UserError(_('Account %s (%s) does not allow reconciliation. First change the configuration of this account to allow it.') % (all_accounts[0].name, all_accounts[0].code))

    @api.multi
    def reconcile(self, writeoff_acc_id=False, writeoff_journal_id=False):
        # Empty self can happen if the user tries to reconcile entries which are already reconciled.
        # The calling method might have filtered out reconciled lines.
        if not self:
            return True

        self._check_reconcile_validity()
        #reconcile everything that can be
        remaining_moves = self.auto_reconcile_lines()

        writeoff_to_reconcile = self.env['account.move.line']
        #if writeoff_acc_id specified, then create write-off move with value the remaining amount from move in self
        if writeoff_acc_id and writeoff_journal_id and remaining_moves:
            all_aml_share_same_currency = all([x.currency_id == self[0].currency_id for x in self])
            writeoff_vals = {
                'account_id': writeoff_acc_id.id,
                'journal_id': writeoff_journal_id.id
            }
            if not all_aml_share_same_currency:
                writeoff_vals['amount_currency'] = False
            writeoff_to_reconcile = remaining_moves._create_writeoff([writeoff_vals])
            #add writeoff line to reconcile algorithm and finish the reconciliation
            remaining_moves = (remaining_moves + writeoff_to_reconcile).auto_reconcile_lines()
        # Check if reconciliation is total or needs an exchange rate entry to be created
        (self + writeoff_to_reconcile).check_full_reconcile()
        return True

    def _create_writeoff(self, writeoff_vals):
        """ Create a writeoff move per journal for the account.move.lines in self. If debit/credit is not specified in vals,
            the writeoff amount will be computed as the sum of amount_residual of the given recordset.

            :param writeoff_vals: list of dicts containing values suitable for account_move_line.create(). The data in vals will
                be processed to create bot writeoff acount.move.line and their enclosing account.move.
        """
        def compute_writeoff_counterpart_vals(values):
            line_values = values.copy()
            line_values['debit'], line_values['credit'] = line_values['credit'], line_values['debit']
            if 'amount_currency' in values:
                line_values['amount_currency'] = -line_values['amount_currency']
            return line_values
        # Group writeoff_vals by journals
        writeoff_dict = {}
        for val in writeoff_vals:
            journal_id = val.get('journal_id', False)
            if not writeoff_dict.get(journal_id, False):
                writeoff_dict[journal_id] = [val]
            else:
                writeoff_dict[journal_id].append(val)

        partner_id = self.env['res.partner']._find_accounting_partner(self[0].partner_id).id
        company_currency = self[0].account_id.company_id.currency_id
        writeoff_currency = self[0].currency_id or company_currency
        line_to_reconcile = self.env['account.move.line']
        # Iterate and create one writeoff by journal
        writeoff_moves = self.env['account.move']
        for journal_id, lines in writeoff_dict.items():
            total = 0
            total_currency = 0
            writeoff_lines = []
            date = fields.Date.today()
            for vals in lines:
                # Check and complete vals
                if 'account_id' not in vals or 'journal_id' not in vals:
                    raise UserError(_("It is mandatory to specify an account and a journal to create a write-off."))
                if ('debit' in vals) ^ ('credit' in vals):
                    raise UserError(_("Either pass both debit and credit or none."))
                if 'date' not in vals:
                    vals['date'] = self._context.get('date_p') or fields.Date.today()
                vals['date'] = fields.Date.to_date(vals['date'])
                if vals['date'] and vals['date'] < date:
                    date = vals['date']
                if 'name' not in vals:
                    vals['name'] = self._context.get('comment') or _('Write-Off')
                if 'analytic_account_id' not in vals:
                    vals['analytic_account_id'] = self.env.context.get('analytic_id', False)
                #compute the writeoff amount if not given
                if 'credit' not in vals and 'debit' not in vals:
                    amount = sum([r.amount_residual for r in self])
                    vals['credit'] = amount > 0 and amount or 0.0
                    vals['debit'] = amount < 0 and abs(amount) or 0.0
                vals['partner_id'] = partner_id
                total += vals['debit']-vals['credit']
                if 'amount_currency' not in vals and writeoff_currency != company_currency:
                    vals['currency_id'] = writeoff_currency.id
                    sign = 1 if vals['debit'] > 0 else -1
                    vals['amount_currency'] = sign * abs(sum([r.amount_residual_currency for r in self]))
                    total_currency += vals['amount_currency']

                writeoff_lines.append(compute_writeoff_counterpart_vals(vals))

            # Create balance line
            writeoff_lines.append({
                'name': _('Write-Off'),
                'debit': total > 0 and total or 0.0,
                'credit': total < 0 and -total or 0.0,
                'amount_currency': total_currency,
                'currency_id': total_currency and writeoff_currency.id or False,
                'journal_id': journal_id,
                'account_id': self[0].account_id.id,
                'partner_id': partner_id
                })

            # Create the move
            writeoff_move = self.env['account.move'].create({
                'journal_id': journal_id,
                'date': date,
                'state': 'draft',
                'line_ids': [(0, 0, line) for line in writeoff_lines],
            })
            writeoff_moves += writeoff_move
            # writeoff_move.post()

            line_to_reconcile += writeoff_move.line_ids.filtered(lambda r: r.account_id == self[0].account_id)
        if writeoff_moves:
            writeoff_moves.post()
        # Return the writeoff move.line which is to be reconciled
        return line_to_reconcile

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
        if self.env.context.get('invoice_id'):
            current_invoice = self.env['account.invoice'].browse(self.env.context['invoice_id'])
            aml_to_keep = current_invoice.move_id.line_ids | current_invoice.move_id.line_ids.mapped('full_reconcile_id.exchange_move_id.line_ids')
            rec_move_ids = rec_move_ids.filtered(
                lambda r: (r.debit_move_id + r.credit_move_id) & aml_to_keep
            )
        return rec_move_ids.unlink()

    def _apply_taxes(self, vals, amount):
        tax_lines_vals = []
        # Get ids from triplets : https://www.odoo.com/documentation/10.0/reference/orm.html#odoo.models.Model.write
        tax_ids = [tax['id'] for tax in self.resolve_2many_commands('tax_ids', vals['tax_ids']) if tax.get('id')]
        # Since create() receives ids instead of recordset, let's just use the old-api bridge
        taxes = self.env['account.tax'].browse(tax_ids)
        currency = self.env['res.currency'].browse(vals.get('currency_id'))
        partner = self.env['res.partner'].browse(vals.get('partner_id'))
        ctx = dict(self._context)
        ctx['round'] = ctx.get('round', True)
        res = taxes.with_context(ctx).compute_all(amount,
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
                bank = self.env["account.bank.statement.line"].browse(vals.get('statement_line_id')).statement_id
                if bank.currency_id != bank.company_id.currency_id:
                    ctx = {}
                    if 'date' in vals:
                        ctx['date'] = vals['date']
                    elif 'date_maturity' in vals:
                        ctx['date'] = vals['date_maturity']
                    temp['currency_id'] = bank.currency_id.id
                    temp['amount_currency'] = bank.company_id.currency_id.with_context(ctx).compute(tax_vals['amount'], bank.currency_id, round=True)
                if vals.get('tax_exigible'):
                    temp['tax_exigible'] = True
                    temp['account_id'] = tax.cash_basis_account.id or account_id
                tax_lines_vals.append(temp)
        return tax_lines_vals

    ####################################################
    # CRUD methods
    ####################################################

    @api.model_create_multi
    def create(self, vals_list):
        """ :context's key `check_move_validity`: check data consistency after move line creation. Eg. set to false to disable verification that the move
                debit-credit == 0 while creating the move lines composing the move.
        """
        for vals in vals_list:
            amount = vals.get('debit', 0.0) - vals.get('credit', 0.0)
            move = self.env['account.move'].browse(vals['move_id'])
            account = self.env['account.account'].browse(vals['account_id'])
            if account.deprecated:
                raise UserError(_('The account %s (%s) is deprecated.') %(account.name, account.code))
            journal = vals.get('journal_id') and self.env['account.journal'].browse(vals['journal_id']) or move.journal_id
            vals['date_maturity'] = vals.get('date_maturity') or vals.get('date') or move.date

            ok = (
                (not journal.type_control_ids and not journal.account_control_ids)
                or account.user_type_id in journal.type_control_ids
                or account in journal.account_control_ids
            )
            if not ok:
                raise UserError(_('You cannot use this general account in this journal, check the tab \'Entry Controls\' on the related journal.'))

            # Automatically convert in the account's secondary currency if there is one and
            # the provided values were not already multi-currency
            if account.currency_id and 'amount_currency' not in vals and account.currency_id.id != account.company_id.currency_id.id:
                vals['currency_id'] = account.currency_id.id
                date = vals.get('date') or vals.get('date_maturity') or fields.Date.today()
                vals['amount_currency'] = account.company_id.currency_id._convert(amount, account.currency_id, account.company_id, date)

            #Toggle the 'tax_exigible' field to False in case it is not yet given and the tax in 'tax_line_id' or one of
            #the 'tax_ids' is a cash based tax.
            taxes = False
            if vals.get('tax_line_id'):
                taxes = [{'tax_exigibility': self.env['account.tax'].browse(vals['tax_line_id']).tax_exigibility}]
            if vals.get('tax_ids'):
                taxes = self.env['account.move.line'].resolve_2many_commands('tax_ids', vals['tax_ids'])
            if taxes and any([tax['tax_exigibility'] == 'on_payment' for tax in taxes]) and not vals.get('tax_exigible'):
                vals['tax_exigible'] = False

        lines = super(AccountMoveLine, self).create(vals_list)

        if self._context.get('check_move_validity', True):
            lines.mapped('move_id')._post_validate()

        return lines

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
            raise UserError(_('You cannot use a deprecated account.'))
        if any(key in vals for key in ('account_id', 'journal_id', 'date', 'move_id', 'debit', 'credit')):
            self._update_check()
        if not self._context.get('allow_amount_currency') and any(key in vals for key in ('amount_currency', 'currency_id')):
            #hackish workaround to write the amount_currency when assigning a payment to an invoice through the 'add' button
            #this is needed to compute the correct amount_residual_currency and potentially create an exchange difference entry
            self._update_check()
        #when we set the expected payment date, log a note on the invoice_id related (if any)
        if vals.get('expected_pay_date') and self.invoice_id:
            str_expected_pay_date = vals['expected_pay_date']
            if isinstance(str_expected_pay_date, date):
                str_expected_pay_date = fields.Date.to_string(str_expected_pay_date)
            msg = _('New expected payment date: ') + str_expected_pay_date + '.\n' + vals.get('internal_note', '')
            self.invoice_id.message_post(body=msg) #TODO: check it is an internal note (not a regular email)!
        #when making a reconciliation on an existing liquidity journal item, mark the payment as reconciled
        for record in self:
            if 'statement_line_id' in vals and record.payment_id:
                # In case of an internal transfer, there are 2 liquidity move lines to match with a bank statement
                if all(line.statement_id for line in record.payment_id.move_line_ids.filtered(lambda r: r.id != record.id and r.account_id.internal_type=='liquidity')):
                    record.payment_id.state = 'reconciled'

        result = super(AccountMoveLine, self).write(vals)
        if self._context.get('check_move_validity', True) and any(key in vals for key in ('account_id', 'journal_id', 'date', 'move_id', 'debit', 'credit')):
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
        This is actually computing the same as the matched_percentage field of account.move, except in case of multi-currencies
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
    def _compute_amount_fields(self, amount, src_currency, company_currency):
        """ Helper function to compute value for fields debit/credit/amount_currency based on an amount and the currencies given in parameter"""
        amount_currency = False
        currency_id = False
        date = self.env.context.get('date') or fields.Date.today()
        company = self.env.context.get('company_id')
        company = self.env['res.company'].browse(company) if company else self.env.user.company_id
        if src_currency and src_currency != company_currency:
            amount_currency = amount
            amount = src_currency._convert(amount, company_currency, company, date)
            currency_id = src_currency.id
        debit = amount > 0 and amount or 0.0
        credit = amount < 0 and -amount or 0.0
        return debit, credit, amount_currency, currency_id

    def _get_analytic_tag_ids(self):
        self.ensure_one()
        return self.analytic_tag_ids.filtered(lambda r: not r.active_analytic_distribution).ids

    @api.multi
    def create_analytic_lines(self):
        """ Create analytic items upon validation of an account.move.line having an analytic account or an analytic distribution.
        """
        for obj_line in self:
            for tag in obj_line.analytic_tag_ids.filtered('active_analytic_distribution'):
                for distribution in tag.analytic_distribution_ids:
                    vals_line = obj_line._prepare_analytic_distribution_line(distribution)
                    self.env['account.analytic.line'].create(vals_line)
            if obj_line.analytic_account_id:
                vals_line = obj_line._prepare_analytic_line()[0]
                self.env['account.analytic.line'].create(vals_line)

    @api.one
    def _prepare_analytic_line(self):
        """ Prepare the values used to create() an account.analytic.line upon validation of an account.move.line having
            an analytic account. This method is intended to be extended in other modules.
        """
        amount = (self.credit or 0.0) - (self.debit or 0.0)
        default_name = self.name or (self.ref or '/' + ' -- ' + (self.partner_id and self.partner_id.name or '/'))
        return {
            'name': default_name,
            'date': self.date,
            'account_id': self.analytic_account_id.id,
            'tag_ids': [(6, 0, self._get_analytic_tag_ids())],
            'unit_amount': self.quantity,
            'product_id': self.product_id and self.product_id.id or False,
            'product_uom_id': self.product_uom_id and self.product_uom_id.id or False,
            'amount': amount,
            'general_account_id': self.account_id.id,
            'ref': self.ref,
            'move_id': self.id,
            'user_id': self.invoice_id.user_id.id or self._uid,
            'partner_id': self.partner_id.id,
            'company_id': self.analytic_account_id.company_id.id or self.env.user.company_id.id,
        }

    def _prepare_analytic_distribution_line(self, distribution):
        """ Prepare the values used to create() an account.analytic.line upon validation of an account.move.line having
            analytic tags with analytic distribution.
        """
        self.ensure_one()
        amount = -self.balance * distribution.percentage / 100.0
        default_name = self.name or (self.ref or '/' + ' -- ' + (self.partner_id and self.partner_id.name or '/'))
        return {
            'name': default_name,
            'date': self.date,
            'account_id': distribution.account_id.id,
            'partner_id': self.partner_id.id,
            'tag_ids': [(6, 0, [distribution.tag_id.id] + self._get_analytic_tag_ids())],
            'unit_amount': self.quantity,
            'product_id': self.product_id and self.product_id.id or False,
            'product_uom_id': self.product_uom_id and self.product_uom_id.id or False,
            'amount': amount,
            'general_account_id': self.account_id.id,
            'ref': self.ref,
            'move_id': self.id,
            'user_id': self.invoice_id.user_id.id or self._uid,
            'company_id': distribution.account_id.company_id.id or self.env.user.company_id.id,
        }

    @api.model
    def _query_get(self, domain=None):
        self.check_access_rights('read')

        context = dict(self._context or {})
        domain = domain or []
        if not isinstance(domain, (list, tuple)):
            domain = safe_eval(domain)

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
            domain += ['|', ('reconciled', '=', False), '|', ('matched_debit_ids.max_date', '>', context['reconcile_date']), ('matched_credit_ids.max_date', '>', context['reconcile_date'])]

        if context.get('account_tag_ids'):
            domain += [('account_id.tag_ids', 'in', context['account_tag_ids'].ids)]

        if context.get('account_ids'):
            domain += [('account_id', 'in', context['account_ids'].ids)]

        if context.get('analytic_tag_ids'):
            domain += [('analytic_tag_ids', 'in', context['analytic_tag_ids'].ids)]

        if context.get('analytic_account_ids'):
            domain += [('analytic_account_id', 'in', context['analytic_account_ids'].ids)]

        if context.get('partner_ids'):
            domain += [('partner_id', 'in', context['partner_ids'].ids)]

        if context.get('partner_categories'):
            domain += [('partner_id.category_id', 'in', context['partner_categories'].ids)]

        where_clause = ""
        where_clause_params = []
        tables = ''
        if domain:
            query = self._where_calc(domain)

            # Wrap the query with 'company_id IN (...)' to avoid bypassing company access rights.
            self._apply_ir_rules(query)

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
    company_currency_id = fields.Many2one('res.currency', string="Company Currency", related='company_id.currency_id', readonly=True,
        help='Utility field to express amount currency')
    company_id = fields.Many2one('res.company', related='debit_move_id.company_id', store=True, string='Company', readonly=False)
    full_reconcile_id = fields.Many2one('account.full.reconcile', string="Full Reconcile", copy=False)
    max_date = fields.Date(string='Max Date of Matched Lines', compute='_compute_max_date',
        readonly=True, copy=False, store=True,
        help='Technical field used to determine at which date this reconciliation needs to be shown on the aged receivable/payable reports.')

    @api.multi
    @api.depends('debit_move_id.date', 'credit_move_id.date')
    def _compute_max_date(self):
        for rec in self:
            rec.max_date = max(
                rec.debit_move_id.date,
                rec.credit_move_id.date
            )

    @api.model
    def _prepare_exchange_diff_partial_reconcile(self, aml, line_to_reconcile, currency):
        return {
            'debit_move_id': aml.credit and line_to_reconcile.id or aml.id,
            'credit_move_id': aml.debit and line_to_reconcile.id or aml.id,
            'amount': abs(aml.amount_residual),
            'amount_currency': abs(aml.amount_residual_currency),
            'currency_id': currency and currency.id or False,
        }

    @api.model
    def create_exchange_rate_entry(self, aml_to_fix, move):
        """
        Automatically create a journal items to book the exchange rate
        differences that can occur in multi-currencies environment. That
        new journal item will be made into the given `move` in the company
        `currency_exchange_journal_id`, and one of its journal items is
        matched with the other lines to balance the full reconciliation.

        :param aml_to_fix: recordset of account.move.line (possible several
            but sharing the same currency)
        :param move: account.move
        :return: tuple.
            [0]: account.move.line created to balance the `aml_to_fix`
            [1]: recordset of account.partial.reconcile created between the
                tuple first element and the `aml_to_fix`
        """
        partial_rec = self.env['account.partial.reconcile']
        aml_model = self.env['account.move.line']

        created_lines = self.env['account.move.line']
        for aml in aml_to_fix:
            #create the line that will compensate all the aml_to_fix
            line_to_rec = aml_model.with_context(check_move_validity=False).create({
                'name': _('Currency exchange rate difference'),
                'debit': aml.amount_residual < 0 and -aml.amount_residual or 0.0,
                'credit': aml.amount_residual > 0 and aml.amount_residual or 0.0,
                'account_id': aml.account_id.id,
                'move_id': move.id,
                'currency_id': aml.currency_id.id,
                'amount_currency': aml.amount_residual_currency and -aml.amount_residual_currency or 0.0,
                'partner_id': aml.partner_id.id,
            })
            #create the counterpart on exchange gain/loss account
            exchange_journal = move.company_id.currency_exchange_journal_id
            aml_model.with_context(check_move_validity=False).create({
                'name': _('Currency exchange rate difference'),
                'debit': aml.amount_residual > 0 and aml.amount_residual or 0.0,
                'credit': aml.amount_residual < 0 and -aml.amount_residual or 0.0,
                'account_id': aml.amount_residual > 0 and exchange_journal.default_debit_account_id.id or exchange_journal.default_credit_account_id.id,
                'move_id': move.id,
                'currency_id': aml.currency_id.id,
                'amount_currency': aml.amount_residual_currency and aml.amount_residual_currency or 0.0,
                'partner_id': aml.partner_id.id,
            })

            #reconcile all aml_to_fix
            partial_rec |= self.create(
                self._prepare_exchange_diff_partial_reconcile(
                        aml=aml,
                        line_to_reconcile=line_to_rec,
                        currency=aml.currency_id or False)
            )
            created_lines |= line_to_rec
        return created_lines, partial_rec

    def _get_tax_cash_basis_base_account(self, line, tax):
        ''' Get the account of lines that will contain the base amount of taxes.

        :param line: An account.move.line record
        :param tax: An account.tax record
        :return: An account record
        '''
        return tax.cash_basis_base_account_id or line.account_id

    def _get_amount_tax_cash_basis(self, amount, line):
        return line.company_id.currency_id.round(amount)

    def create_tax_cash_basis_entry(self, percentage_before_rec):
        self.ensure_one()
        move_date = self.debit_move_id.date
        newly_created_move = self.env['account.move']
        with self.env.norecompute():
            for move in (self.debit_move_id.move_id, self.credit_move_id.move_id):
                #move_date is the max of the 2 reconciled items
                if move_date < move.date:
                    move_date = move.date
                percentage_before = percentage_before_rec[move.id]
                percentage_after = move.line_ids[0]._get_matched_percentage()[move.id]
                # update the percentage before as the move can be part of
                # multiple partial reconciliations
                percentage_before_rec[move.id] = percentage_after

                for line in move.line_ids:
                    if not line.tax_exigible:
                        #amount is the current cash_basis amount minus the one before the reconciliation
                        amount = line.balance * percentage_after - line.balance * percentage_before
                        rounded_amt = self._get_amount_tax_cash_basis(amount, line)
                        if float_is_zero(rounded_amt, precision_rounding=line.company_id.currency_id.rounding):
                            continue
                        if line.tax_line_id and line.tax_line_id.tax_exigibility == 'on_payment':
                            if not newly_created_move:
                                newly_created_move = self._create_tax_basis_move()
                            #create cash basis entry for the tax line
                            to_clear_aml = self.env['account.move.line'].with_context(check_move_validity=False).create({
                                'name': line.move_id.name,
                                'debit': abs(rounded_amt) if rounded_amt < 0 else 0.0,
                                'credit': rounded_amt if rounded_amt > 0 else 0.0,
                                'account_id': line.account_id.id,
                                'analytic_account_id': line.analytic_account_id.id,
                                'analytic_tag_ids': line.analytic_tag_ids.ids,
                                'tax_exigible': True,
                                'amount_currency': line.amount_currency and line.currency_id.round(-line.amount_currency * amount / line.balance) or 0.0,
                                'currency_id': line.currency_id.id,
                                'move_id': newly_created_move.id,
                                'partner_id': line.partner_id.id,
                            })
                            # Group by cash basis account and tax
                            self.env['account.move.line'].with_context(check_move_validity=False).create({
                                'name': line.name,
                                'debit': rounded_amt if rounded_amt > 0 else 0.0,
                                'credit': abs(rounded_amt) if rounded_amt < 0 else 0.0,
                                'account_id': line.tax_line_id.cash_basis_account_id.id,
                                'analytic_account_id': line.analytic_account_id.id,
                                'analytic_tag_ids': line.analytic_tag_ids.ids,
                                'tax_line_id': line.tax_line_id.id,
                                'tax_exigible': True,
                                'amount_currency': line.amount_currency and line.currency_id.round(line.amount_currency * amount / line.balance) or 0.0,
                                'currency_id': line.currency_id.id,
                                'move_id': newly_created_move.id,
                                'partner_id': line.partner_id.id,
                            })
                            if line.account_id.reconcile:
                                #setting the account to allow reconciliation will help to fix rounding errors
                                to_clear_aml |= line
                                to_clear_aml.reconcile()

                        if any([tax.tax_exigibility == 'on_payment' for tax in line.tax_ids]):
                            if not newly_created_move:
                                newly_created_move = self._create_tax_basis_move()
                            #create cash basis entry for the base
                            for tax in line.tax_ids.filtered(lambda t: t.tax_exigibility == 'on_payment'):
                                account_id = self._get_tax_cash_basis_base_account(line, tax)
                                self.env['account.move.line'].with_context(check_move_validity=False).create({
                                    'name': line.name,
                                    'debit': rounded_amt > 0 and rounded_amt or 0.0,
                                    'credit': rounded_amt < 0 and abs(rounded_amt) or 0.0,
                                    'account_id': account_id.id,
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
                                    'account_id': account_id.id,
                                    'tax_exigible': True,
                                    'move_id': newly_created_move.id,
                                    'currency_id': line.currency_id.id,
                                    'amount_currency': self.amount_currency and line.currency_id.round(-line.amount_currency * amount / line.balance) or 0.0,
                                    'partner_id': line.partner_id.id,
                                })
        self.recompute()
        if newly_created_move:
            if move_date > (self.company_id.period_lock_date or date.min) and newly_created_move.date != move_date:
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
            'ref': self.credit_move_id.move_id.name if self.credit_move_id.payment_id else self.debit_move_id.move_id.name,
        }
        return self.env['account.move'].create(move_vals)

    @api.multi
    def unlink(self):
        """ When removing a partial reconciliation, also unlink its full reconciliation if it exists """
        full_to_unlink = self.env['account.full.reconcile']
        for rec in self:
            if rec.full_reconcile_id:
                full_to_unlink |= rec.full_reconcile_id
        #reverse the tax basis move created at the reconciliation time
        for move in self.env['account.move'].search([('tax_cash_basis_rec_id', 'in', self._ids)]):
            if move.date > (move.company_id.period_lock_date or date.min):
                move.reverse_moves(date=move.date)
            else:
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

    @api.multi
    def unlink(self):
        """ When removing a full reconciliation, we need to revert the eventual journal entries we created to book the
            fluctuation of the foreign currency's exchange rate.
            We need also to reconcile together the origin currency difference line and its reversal in order to completely
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

    @api.model
    def _prepare_exchange_diff_move(self, move_date, company):
        if not company.currency_exchange_journal_id:
            raise UserError(_("You should configure the 'Exchange Rate Journal' in the accounting settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
        if not company.income_currency_exchange_account_id.id:
            raise UserError(_("You should configure the 'Gain Exchange Rate Account' in the accounting settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
        if not company.expense_currency_exchange_account_id.id:
            raise UserError(_("You should configure the 'Loss Exchange Rate Account' in the accounting settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
        res = {'journal_id': company.currency_exchange_journal_id.id}
        # The move date should be the maximum date between payment and invoice
        # (in case of payment in advance). However, we should make sure the
        # move date is not recorded after the end of year closing.
        if move_date > (company.fiscalyear_lock_date or date.min):
            res['date'] = move_date
        return res
