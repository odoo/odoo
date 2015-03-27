# -*- coding: utf-8 -*-

from datetime import datetime
from dateutil.relativedelta import relativedelta
import time
import math

from openerp.osv import expression
from openerp.tools.float_utils import float_round as round
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.exceptions import AccessError, UserError
import openerp.addons.decimal_precision as dp
from openerp import api, fields, models, _


class ResCompany(models.Model):
    _inherit = "res.company"

    currency_exchange_journal_id = fields.Many2one('account.journal', string="Currency Adjustments Journal", domain=[('type', '=', 'general')])
    income_currency_exchange_account_id = fields.Many2one('account.account', related='currency_exchange_journal_id.default_credit_account_id',
        string="Gain Exchange Rate Account", domain=[('internal_type', '=', 'other'), ('deprecated', '=', False)])
    expense_currency_exchange_account_id = fields.Many2one('account.account', related='currency_exchange_journal_id.default_debit_account_id',
        string="Loss Exchange Rate Account", domain=[('internal_type', '=', 'other'), ('deprecated', '=', False)])
    anglo_saxon_accounting = fields.Boolean(string="Use anglo-saxon accounting")


class AccountPaymentTerm(models.Model):
    _name = "account.payment.term"
    _description = "Payment Term"
    _order = "name"

    name = fields.Char(string='Payment Term', translate=True, required=True)
    active = fields.Boolean(default=True, help="If the active field is set to False, it will allow you to hide the payment term without removing it.")
    note = fields.Text(string='Description', translate=True)
    line_ids = fields.One2many('account.payment.term.line', 'payment_id', string='Terms', copy=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)

    @api.one
    def compute(self, value, date_ref=False):
        date_ref = date_ref or datetime.now().strftime('%Y-%m-%d')
        amount = value
        result = []
        prec = self.company_id.currency_id.decimal_places
        for line in self.line_ids:
            if line.value == 'fixed':
                amt = round(line.value_amount, prec)
            elif line.value == 'percent':
                amt = round(value * (line.value_amount / 100.0), prec)
            elif line.value == 'balance':
                amt = round(amount, prec)
            if amt:
                next_date = (datetime.strptime(date_ref, '%Y-%m-%d') + relativedelta(days=line.days))
                if line.days2 < 0:
                    next_first_date = next_date + relativedelta(day=1, months=1)  # Getting 1st of next month
                    next_date = next_first_date + relativedelta(days=line.days2)
                if line.days2 > 0:
                    next_date += relativedelta(day=line.days2, months=1)
                result.append((next_date.strftime('%Y-%m-%d'), amt))
                amount -= amt

        amount = reduce(lambda x, y: x + y[1], result, 0.0)
        dist = round(value - amount, prec)
        if dist:
            last_date = result and result[-1][0] or time.strftime('%Y-%m-%d')
            result.append((last_date, dist))
        return result


class AccountPaymentTermLine(models.Model):
    _name = "account.payment.term.line"
    _description = "Payment Term Line"
    _order = "days"

    value = fields.Selection([
            ('balance', 'Balance'),
            ('percent', 'Percent'),
            ('fixed', 'Fixed Amount')
        ], string='Computation', required=True, default='balance',
        help="Select here the kind of valuation related to this payment term line.")
    value_amount = fields.Float(string='Amount To Pay', digits=dp.get_precision('Payment Term'), help="For percent enter a ratio between 0-100.")
    days = fields.Integer(string='Number of Days', required=True, default=30, help="Number of days to add before computing the day of the month.")
    days2 = fields.Integer(string='Day of the Month', required=True, default='0',
        help="Day of the month \n\n Set : \n1)-1 for the last day of the current month. \n2) 0 for net days\n3) A positive number for the specific day of the next month.\n\nExample : if Date=15/01, Number of Days=22, Day of Month=-1, then the due date is 28/02.")
    payment_id = fields.Many2one('account.payment.term', string='Payment Term', required=True, index=True, ondelete='cascade')

    @api.one
    @api.constrains('value', 'value_amount')
    def _check_percent(self):
        if self.value == 'percent' and (self.value_amount < 0.0 or self.value_amount > 100.0):
            raise UserError(_('Percentages for Payment Term Line must be between 0 and 100.'))


class AccountAccountType(models.Model):
    _name = "account.account.type"
    _description = "Account Type"

    name = fields.Char(string='Account Type', required=True, translate=True)
    include_initial_balance = fields.Boolean()
    type = fields.Selection([
        ('other', 'Regular'),
        ('receivable', 'Receivable'),
        ('payable', 'Payable'),
        ('liquidity', 'Liquidity'),
        ('consolidation', 'Consolidation'),
    ], required=True, default='other',
        help="The 'Internal Type' is used for features available on "\
        "different types of accounts: consolidation are accounts that "\
        "can have children accounts for multi-company consolidations, payable/receivable are for "\
        "partners accounts (for debit/credit computations).")
    note = fields.Text(string='Description')


class AccountAccountTag(models.Model):
    _name = 'account.account.tag'
    _description = 'Account Tag'

    name = fields.Char()

#----------------------------------------------------------
# Accounts
#----------------------------------------------------------


class AccountAccount(models.Model):
    _name = "account.account"
    _description = "Account"

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        context = self._context or {}
        if context.get('journal_id', False):
            jour = self.env['account.journal'].browse(context['journal_id'])
            if jour.account_control_ids:
                args.append(('id', 'in', map(lambda x: x.id, jour.account_control_ids)))
            if jour.type_control_ids:
                args.append(('user_type', 'in', map(lambda x: x.id, jour.type_control_ids)))
        return super(AccountAccount, self).search(args, offset, limit, order, count=count)

    @api.multi
    def _get_children_and_consol(self):
        #this function search for all the consolidated children (recursively) of the given account ids
        children_ids = set(self.ids)
        for rec in self:
            this_rec_children = []
            if rec.child_consol_ids:
                this_rec_children = rec.child_consol_ids._get_children_and_consol()
            children_ids |= set(this_rec_children)
        return list(children_ids)

    name = fields.Char(required=True, index=True)
    currency_id = fields.Many2one('res.currency', string='Secondary Currency',
        help="Forces all moves for this account to have this secondary currency.")
    code = fields.Char(size=64, required=True, index=True)
    deprecated = fields.Boolean(index=True, default=False)
    user_type = fields.Many2one('account.account.type', string='Type', required=True,
        help="Account Type is used for information purpose, to generate country-specific legal reports, and set the rules to close a fiscal year and generate opening entries.")
    internal_type = fields.Selection(related='user_type.type', store=True)
    child_consol_ids = fields.Many2many('account.account', 'account_account_consol_rel', 'child_id', 'parent_id', string='Consolidated Children', domain=[('deprecated', '=', False)])
    last_time_entries_checked = fields.Datetime(string='Latest Invoices & Payments Matching Date', readonly=True, copy=False,
        help='Last time the invoices & payments matching was performed on this account. It is set either if there\'s not at least '\
        'an unreconciled debit and an unreconciled credit Or if you click the "Done" button.')

    reconcile = fields.Boolean(string='Allow Invoices & Payments Matching', default=False,
        help="Check this box if this account allows invoices & payments matching of journal items.")
    tax_ids = fields.Many2many('account.tax', 'account_account_tax_default_rel',
        'account_id', 'tax_id', string='Default Taxes')
    note = fields.Text('Internal Notes')
    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env['res.company']._company_default_get('account.account'))
    tag_ids = fields.Many2many('account.account.tag', string='Account tag')

    _sql_constraints = [
        ('code_company_uniq', 'unique (code,company_id)', 'The code of the account must be unique per company !')
    ]

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', '=ilike', name+'%'), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&'] + domain
        accounts = self.search(domain+args, limit=limit)
        return accounts.name_get()

    @api.multi
    @api.depends('name', 'code')
    def name_get(self):
        result = []
        for account in self:
            name = account.code + ' ' + account.name
            result.append((account.id, name))
        return result

    @api.one
    def copy(self, default=None):
        default = dict(default or {})
        default.update(code=_("%s (copy)") % (self.code or ''))
        return super(AccountAccount, self).copy(default)

    @api.multi
    def write(self, vals):
        # Dont allow changing the company_id when account_move_line already exist
        if vals.get('company_id', False):
            move_lines = self.env['account.move.line'].search([('account_id', 'in', self.ids)], limit=1)
            for account in self:
                if (account.company_id.id <> vals['company_id']) and move_lines:
                    raise UserError(_('You cannot change the owner company of an account that already contains journal items.'))
        return super(AccountAccount, self).write(vals)

    @api.multi
    def unlink(self):
        if self.env['account.move.line'].search([('account_id', 'in', self.ids)], limit=1):
            raise UserError(_('You cannot do that on an account that contains journal items.'))
        #Checking whether the account is set as a property to any Partner or not
        values = ['account.account,%s' % (account_id,) for account_id in self.ids]
        partner_prop_acc = self.env['ir.property'].search([('value_reference', 'in', values)], limit=1)
        if partner_prop_acc:
            raise UserError(_('You cannot remove/deactivate an account which is set on a customer or supplier.'))
        return super(AccountAccount, self).unlink()

    @api.multi
    def mark_as_reconciled(self):
        return self.write({'last_time_entries_checked': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})


class AccountJournal(models.Model):
    _name = "account.journal"
    _description = "Journal"
    _order = 'sequence, code'

    def _default_inbound_payment_methods(self):
        return [(4, self.env.ref('account.account_payment_method_manual_in').id, None)]

    def _default_outbound_payment_methods(self):
        return [(4, self.env.ref('account.account_payment_method_manual_out').id, None)]

    name = fields.Char(string='Journal Name', required=True)
    code = fields.Char(size=5, required=True, help="The code will be displayed on reports.")
    type = fields.Selection([
            ('sale', 'Sale'),
            ('purchase', 'Purchase'),
            ('cash', 'Cash'),
            ('bank', 'Bank'),
            ('general', 'General'),
        ], required=True,
        help="Select 'Sale' for customer invoices journals."\
        " Select 'Purchase' for supplier bills journals."\
        " Select 'Cash' or 'Bank' for journals that are used in customer or supplier payments."\
        " Select 'General' for miscellaneous operations journals."\
        " Select 'Opening/Closing Situation' for entries generated for new fiscal years.")
    type_control_ids = fields.Many2many('account.account.type', 'account_journal_type_rel', 'journal_id', 'type_id', string='Type Controls')
    account_control_ids = fields.Many2many('account.account', 'account_account_type_rel', 'journal_id', 'account_id', string='Account',
        domain=[('deprecated', '=', False)])
    default_credit_account_id = fields.Many2one('account.account', string='Default Credit Account',
        domain=[('deprecated', '=', False)], help="It acts as a default account for credit amount")
    default_debit_account_id = fields.Many2one('account.account', string='Default Debit Account',
        domain=[('deprecated', '=', False)], help="It acts as a default account for debit amount")
    update_posted = fields.Boolean(string='Allow Cancelling Entries',
        help="Check this box if you want to allow the cancellation the entries related to this journal or of the invoice related to this journal")
    group_invoice_lines = fields.Boolean(string='Group Invoice Lines',
        help="If this box is checked, the system will try to group the accounting lines when generating them from invoices.")
    sequence_id = fields.Many2one('ir.sequence', string='Entry Sequence',
        help="This field contains the information related to the numbering of the journal entries of this journal.", required=True, copy=False)
    refund_sequence_id = fields.Many2one('ir.sequence', string='Refund Entry Sequence',
        help="This field contains the information related to the numbering of the refund entries of this journal.", copy=False)
    sequence = fields.Integer(help='Used to order Journals')

    groups_id = fields.Many2many('res.groups', 'account_journal_group_rel', 'journal_id', 'group_id', string='Groups')
    currency = fields.Many2one('res.currency', help='The currency used to enter statement')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=1, default=lambda self: self.env.user.company_id,
        help="Company related to this journal")

    analytic_journal_id = fields.Many2one('account.analytic.journal', string='Analytic Journal', help="Journal for analytic entries")
    refund_sequence = fields.Boolean(string='Dedicated Refund Sequence', help="Check this box if you don't want to share the same sequence for invoices and refunds made from this journal")

    inbound_payment_methods = fields.Many2many('account.payment.method', 'account_journal_inbound_payment_method_rel', 'journal_id', 'inbound_payment_method',
        domain=[('payment_type', '=', 'inbound')], string='Inbound Payment Methods', default=lambda self: self._default_inbound_payment_methods())
    outbound_payment_methods = fields.Many2many('account.payment.method', 'account_journal_outbound_payment_method_rel', 'journal_id', 'outbound_payment_method',
        domain=[('payment_type', '=', 'outbound')], string='Outbound Payment Methods', default=lambda self: self._default_outbound_payment_methods())
    at_least_one_inbound = fields.Boolean(compute='_methods_compute', store=True)
    at_least_one_outbound = fields.Boolean(compute='_methods_compute', store=True)

    _sql_constraints = [
        ('code_company_uniq', 'unique (code, name, company_id)', 'The code and name of the journal must be unique per company !'),
    ]

    @api.one
    @api.constrains('currency', 'default_credit_account_id', 'default_debit_account_id')
    def _check_currency(self):
        if self.currency:
            if self.default_credit_account_id and not self.default_credit_account_id.currency_id.id == self.currency.id:
                raise UserError(_('Configuration error!\nThe currency of the journal should be the same than the default credit account.'))
            if self.default_debit_account_id and not self.default_debit_account_id.currency_id.id == self.currency.id:
                raise UserError(_('Configuration error!\nThe currency of the journal should be the same than the default debit account.'))

    @api.one
    def copy(self, default=None):
        default = dict(default or {})
        default.update(
            code=_("%s (copy)") % (self.code or ''),
            name=_("%s (copy)") % (self.name or ''))
        return super(AccountJournal, self).copy(default)

    @api.multi
    def write(self, vals):
        for journal in self:
            if 'company_id' in vals and journal.company_id.id != vals['company_id']:
                if self.env['account.move.line'].search([('journal_id', 'in', self.ids)], limit=1):
                    raise UserError(_('This journal already contains items, therefore you cannot modify its company field.'))
        return super(AccountJournal, self).write(vals)

    @api.model
    def _create_sequence(self, vals, refund=False):
        """ Create new no_gap entry sequence for every new Joural
        """
        prefix = vals['code'].upper()
        if refund:
            prefix = 'R' + prefix
        seq = {
            'name': vals['name'],
            'implementation': 'no_gap',
            'prefix': prefix + '/%(year)s/',
            'padding': 4,
            'number_increment': 1,
            'use_date_range': True,
        }

        if 'company_id' in vals:
            seq['company_id'] = vals['company_id']
        return self.env['ir.sequence'].create(seq)

    @api.model
    def create(self, vals):
        # We just need to create the relevant sequences according to the chosen options
        if not vals.get('sequence_id'):
            vals.update({'sequence_id': self.sudo()._create_sequence(vals).id})
        if vals.get('refund_sequence') and not vals.get('refund_sequence_id'):
            vals.update({'refund_sequence_id': self.sudo()._create_sequence(vals, refund=True).id})
        return super(AccountJournal, self).create(vals)

    @api.multi
    @api.depends('name', 'currency', 'company_id', 'company_id.currency_id')
    def name_get(self):
        res = []
        for journal in self:
            currency = journal.currency or journal.company_id.currency_id
            name = "%s (%s)" % (journal.name, currency.name)
            res += [(journal.id, name)]
        return res

    @api.multi
    @api.depends('inbound_payment_methods', 'outbound_payment_methods')
    def _methods_compute(self):
        for journal in self:
            journal.at_least_one_inbound = bool(len(self.inbound_payment_methods))
            journal.at_least_one_outbound = bool(len(self.outbound_payment_methods))


#----------------------------------------------------------
# Entries
#----------------------------------------------------------


class AccountMove(models.Model):
    _name = "account.move"
    _description = "Account Entry"
    _order = 'id desc'

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
    @api.depends('line_id.debit', 'line_id.credit')
    def _amount_compute(self):
        for move in self:
            total = 0.0
            for line in move.line_id:
                total += line.debit
            move.amount = total

    @api.depends('line_id.debit', 'line_id.credit', 'line_id.matched_debit_ids.amount', 'line_id.matched_credit_ids.amount', 'line_id.account_id.user_type.type')
    def _compute_matched_percentage(self):
        for move in self:
            total_amount = 0.0
            total_reconciled = 0.0
            for line in move.line_id:
                if line.account_id.user_type.type in ('receivable', 'payable'):
                    amount = abs(line.debit - line.credit)
                    total_amount += amount
                    for partial_line in (line.matched_debit_ids + line.matched_credit_ids):
                        total_reconciled += partial_line.amount
            if total_amount == 0.0:
                move.matched_percentage = 100.0
            else:
                move.matched_percentage = total_reconciled / total_amount

    name = fields.Char(string='Number', required=True, copy=False, default='/')
    ref = fields.Char(string='Reference', copy=False)
    date = fields.Date(required=True, states={'posted': [('readonly', True)]}, index=True, default=fields.Date.context_today)
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, states={'posted': [('readonly', True)]})
    rate_diff_partial_rec_id = fields.Many2one('account.partial.reconcile', string='Exchange Rate Entry of')
    state = fields.Selection([('draft', 'Unposted'), ('posted', 'Posted')], string='Status',
      required=True, readonly=True, copy=False, default='draft',
      help='All manually created new journal entries are usually in the status \'Unposted\', '
           'but you can set the option to skip that status on the related journal. '
           'In that case, they will behave as journal entries automatically created by the '
           'system on document validation (invoices, bank statements...) and will be created '
           'in \'Posted\' status.')
    line_id = fields.One2many('account.move.line', 'move_id', string='Journal Items',
        states={'posted': [('readonly', True)]}, copy=True)
    partner_id = fields.Many2one('res.partner', related='line_id.partner_id', string="Partner", store=True)
    amount = fields.Float(compute='_amount_compute', digits=0, store=True)
    narration = fields.Text(string='Internal Note')
    company_id = fields.Many2one('res.company', related='journal_id.company_id', string='Company', store=True, readonly=True,
        default=lambda self: self.env.user.company_id)
    matched_percentage = fields.Float('Percentage Matched', compute='_compute_matched_percentage', digits=0, store=True, readonly=True)
    statement_line_id = fields.Many2one('account.bank.statement.line', string='Bank statement line reconciled with this entry', copy=False, readonly=True)
    to_check = fields.Boolean('To Review', help='Check this box if you are unsure of that journal entry and if you want to note it as \'to be reviewed\' by an accounting expert.')

    @api.model
    def create(self, vals):
        move = super(AccountMove, self.with_context(check_move_validity=False)).create(vals)
        move.assert_balanced()
        return move

    @api.multi
    def write(self, vals):
        if 'line_id' in vals:
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
            move.line_id.create_analytic_lines()
            if move.name == '/':
                new_name = False
                journal = move.journal_id

                if invoice and invoice.internal_number:
                    new_name = invoice.internal_number
                else:
                    if journal.sequence_id:
                        # If invoice is actually refund and journal has a refund_sequence then use that one or use the regular one
                        sequence = journal.sequence_id
                        if invoice and invoice.type in ['out_refund', 'in_refund'] and journal.refund_sequence:
                            sequence = journal.refund_sequence_id
                        new_name = sequence.with_context(ir_sequence_date=move.date).next_by_id()
                    else:
                        raise UserError(_('Please define a sequence on the journal.'))

                if new_name:
                    move.name = new_name

        self._cr.execute('UPDATE account_move '\
                   'SET state=%s '\
                   'WHERE id IN %s',
                   ('posted', tuple(self.ids),))
        self.invalidate_cache()
        return True

    @api.multi
    def button_validate(self):
        return self.post()

    @api.multi
    def button_cancel(self):
        for move in self:
            if not move.journal_id.update_posted:
                raise UserError(_('You cannot modify a posted entry of this journal.\nFirst you should set the journal to allow cancelling entries.'))
        if self.ids:
            self._cr.execute('UPDATE account_move '\
                       'SET state=%s '\
                       'WHERE id IN %s', ('draft', tuple(self.ids),))
            self.invalidate_cache()
        return True

    @api.multi
    def unlink(self):
        for move in self:
            #check the lock date + check if some entries are reconciled
            move.line_id._update_check()
            move.line_id.unlink()
        return super(AccountMove, self).unlink()

    @api.multi
    def _post_validate(self):
        for move in self:
            for line in move.line_id:
                if not move.company_id.id == line.account_id.company_id.id:
                    raise UserError(_("Cannot create moves for different companies."))
                if line.account_id.currency_id and line.currency_id:
                    if line.account_id.currency_id.id != line.currency_id.id and (line.account_id.currency_id.id != line.account_id.company_id.currency_id.id):
                        raise UserError(_("""Cannot create move with currency different from ..""") % (line.account_id.code, line.account_id.name))
        self.assert_balanced()
        return self._check_lock_date()

    @api.multi
    def _check_lock_date(self):
        for move in self:
            lock_date = move.company_id.period_lock_date
            if self.user_has_groups('account.group_account_manager'):
                lock_date = move.company_id.fiscalyear_lock_date
            if move.date <= lock_date:
                raise UserError(_("You cannot add/modify entries prior to and inclusive of the lock date %s. Check the company settings or ask someone with the 'Adviser' role" % (lock_date)))
        return True

    @api.multi
    def assert_balanced(self):
        if not self.ids:
            return True
        self._cr.execute("""\
            SELECT      move_id
            FROM        account_move_line
            WHERE       move_id in %s
            GROUP BY    move_id
            HAVING      abs(sum(debit) - sum(credit)) > 0.00001
            """, (tuple(self.ids),))
        if len(self._cr.fetchall()) != 0:
            raise UserError(_("Cannot create unbalanced journal entry."))
        return True

    @api.multi
    def reverse_moves(self, date=None, journal_id=None):
        date = date or fields.Date.today()
        for ac_move in self:
            reversed_move = ac_move.copy(default={'date': date,
                'journal_id': journal_id.id if journal_id else ac_move.journal_id.id,
                'ref': _('reversal of: ') + ac_move.name})
            for acm_line in reversed_move.line_id:
                acm_line.with_context(check_move_validity=False).write({
                    'debit': acm_line.credit,
                    'credit': acm_line.debit,
                    'amount_currency': -acm_line.amount_currency
                    })
            reversed_move._post_validate()
            reversed_move.post()
        return True

#----------------------------------------------------------
# Tax
#----------------------------------------------------------


class AccountTax(models.Model):
    _name = 'account.tax'
    _description = 'Tax'
    _order = 'sequence'

    name = fields.Char(string='Tax Name', required=True, translate=True)
    type_tax_use = fields.Selection([('sale', 'Sales'), ('purchase', 'Purchases'), ('none', 'None')], string='Tax Scope', required=True, default="sale",
        help="Determines where the tax is selectable. Note : 'None' means a tax can't be used by itself, however it can still be used in a group.")
    amount_type = fields.Selection(default='percent', string="Tax Computation", required=True,
        selection=[('group', 'Group of Taxes'), ('fixed', 'Fixed'), ('percent', 'Percentage of Price'), ('division', 'Percentage of Price Tax Included')])
    active = fields.Boolean(default=True, help="Set active to false to hide the tax without removing it.")
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    children_tax_ids = fields.Many2many('account.tax', 'account_tax_filiation_rel', 'parent_tax', 'child_tax', string='Children Taxes')
    sequence = fields.Integer(required=True, default=1,
        help="The sequence field is used to define order in which the tax lines are applied.")
    amount = fields.Float(required=True, digits=(16, 3))
    account_id = fields.Many2one('account.account', domain=[('deprecated', '=', False)], string='Tax Account', ondelete='restrict',
        help="Account that will be set on invoice tax lines for invoices. Leave empty to use the expense account.")
    refund_account_id = fields.Many2one('account.account', domain=[('deprecated', '=', False)], string='Tax Account on Refunds', ondelete='restrict',
        help="Account that will be set on invoice tax lines for refunds. Leave empty to use the expense account.")
    description = fields.Char(string='Display on Invoices')
    price_include = fields.Boolean(string='Included in Price', default=False,
        help="Check this if the price you use on the product and invoices includes this tax.")
    include_base_amount = fields.Boolean(string='Affect Subsequent Taxes', default=False,
        help="If set, taxes which are computed after this one will be computed based on the price tax included.")
    analytic = fields.Boolean(string="Analytic Cost", help="If set, the amount computed by this tax will be assigned to the same analytic account as the invoice line (if any)")

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 'Tax names must be unique !'),
    ]

    @api.one
    @api.constrains('children_tax_ids', 'type_tax_use')
    def _check_children_scope(self):
        if not all(child.type_tax_use in ('none', self.type_tax_use) for child in self.children_tax_ids):
            raise UserError(_('The application scope of taxes in a group must be either the same as the group or "None".'))

    @api.one
    def copy(self, default=None):
        default = dict(default or {}, name=_("%s (Copy)") % self.name)
        return super(AccountTax, self).copy(default=default)

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=80):
        """ Returns a list of tupples containing id, name, as internally it is called {def name_get}
            result format: {[(id, name), (id, name), ...]}
        """
        args = args or []
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            domain = [('description', operator, name), ('name', operator, name)]
        else:
            domain = ['|', ('description', operator, name), ('name', operator, name)]
        taxes = self.search(expression.AND([domain, args]), limit=limit)
        return taxes.name_get()

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        context = self._context or {}

        if context.get('type'):
            if context.get('type') in ('out_invoice', 'out_refund'):
                args += [('type_tax_use', '=', 'sale')]
            elif context.get('type') in ('in_invoice', 'in_refund'):
                args += [('type_tax_use', '=', 'purchase')]

        if context.get('journal_id'):
            journal = self.env['account.journal'].browse(context.get('journal_id'))
            if journal.type in ('sale', 'purchase'):
                args += [('type_tax_use', '=', journal.type)]

        return super(AccountTax, self).search(args, offset, limit, order, count=count)

    @api.multi
    @api.depends('name', 'description')
    def name_get(self):
        res = []
        for record in self:
            name = record.description and record.description or record.name
            res.append((record.id, name))
        return res

    @api.onchange('amount')
    def onchange_amount(self):
        if self.amount_type in ('percent', 'division') and self.amount != 0.0:
            self.description = "{0:.4g}%".format(self.amount)

    @api.onchange('account_id')
    def onchange_account_id(self):
        self.refund_account_id = self.account_id

    @api.onchange('price_include')
    def onchange_price_include(self):
        if self.price_include:
            self.include_base_amount = True

    @api.multi
    def normalized_set(self):
        """ Returns a recordset where groups are replaced by their children and each tax appears only once sorted by default sort order (sequence).
            Warning : It might make more sense to first filter out first-level taxes that appear in groups.
            Eg. considering letters as taxes and alphabetic order as sequence :
            [G, B([A, D, F]), E, C] sould become [A, C, D, E, F, G] or [A, D, F, C, E, G] ? """
        return self.mapped(lambda r: r.amount_type == 'group' and r.children_tax_ids or r).sorted()

    def _compute_amount(self, base_amount, price_unit, quantity=1.0, product=None, partner=None):
        """ Returns the amount of a single tax. base_amount is the actual amount on which the tax is applied, which is
            price_unit * quantity eventually affected by previous taxes (if tax is include_base_amount XOR price_include)
        """
        self.ensure_one()
        if self.amount_type == 'fixed':
            return math.copysign(self.amount, base_amount) * quantity
        if (self.amount_type == 'percent' and not self.price_include) or (self.amount_type == 'division' and self.price_include):
            return base_amount * self.amount / 100
        if self.amount_type == 'percent' and self.price_include:
            return base_amount - (base_amount / (1 + self.amount / 100))
        if self.amount_type == 'division' and not self.price_include:
            return base_amount / (1 - self.amount / 100) - base_amount

    @api.v8
    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None):
        """ Returns all information required to apply taxes (in self + their children in case of a tax goup).

        RETURN: {
            'total_excluded': 0.0,    # Total without taxes
            'total_included': 0.0,    # Total with taxes
            'taxes': [{               # One dict for each tax in self and their children
                'id': int,
                'name': str,
                'amount': float,
                'sequence': int,
                'account_id': int,
                'refund_account_id': int,
                'analytic': boolean,
            }]
        } """
        if not currency:
            currency = self[0].company_id.currency_id
        taxes = []
        prec = currency.decimal_places
        total_excluded = total_included = base = round(price_unit * quantity, prec)

        for tax in self:
            if tax.amount_type == 'group':
                ret = tax.children_tax_ids.compute_all(price_unit, currency, quantity, product, partner)
                total_excluded = ret['total_excluded']
                base = ret['total_excluded']
                total_included = ret['total_included']
                tax_amount = total_included - total_excluded
                taxes += ret['taxes']
                continue

            tax_amount = tax._compute_amount(base, price_unit, quantity, product, partner)
            tax_amount = currency.round(tax_amount)

            if tax.price_include:
                total_excluded -= tax_amount
                base -= tax_amount
            else:
                total_included += tax_amount

            if tax.include_base_amount:
                base += tax_amount

            taxes.append({
                'id': tax.id,
                'name': tax.name,
                'amount': tax_amount,
                'sequence': tax.sequence,
                'account_id': tax.account_id.id,
                'refund_account_id': tax.refund_account_id.id,
                'analytic': tax.analytic,
            })

        return {
            'taxes': taxes,
            'total_excluded': currency.round(total_excluded),
            'total_included': currency.round(total_included),
        }

    @api.v7
    def compute_all(self, cr, uid, ids, price_unit, currency_id=None, quantity=1.0, product_id=None, partner_id=None, context=None):
        currency = currency_id and self.pool.get('res.currency').browse(cr, uid, currency_id, context=context) or None
        product = product_id and self.pool.get('product.product').browse(cr, uid, product_id, context=context) or None
        partner = partner_id and self.pool.get('res.partner').browse(cr, uid, partner_id, context=context) or None
        ids = isinstance(ids, (int, long)) and [ids] or ids
        recs = self.browse(cr, uid, ids, context=context)
        return recs.compute_all(price_unit, currency, quantity, product, partner)

#  ---------------------------------------------------------------
#   Account Templates: Account, Tax, Tax Code and chart. + Wizard
#  ---------------------------------------------------------------


class AccountAccountTemplate(models.Model):
    _name = "account.account.template"
    _description = 'Templates for Accounts'
    _order = "code"

    name = fields.Char(required=True, index=True)
    currency_id = fields.Many2one('res.currency', string='Secondary Currency', help="Forces all moves for this account to have this secondary currency.")
    code = fields.Char(size=64, required=True, index=True)
    user_type = fields.Many2one('account.account.type', string='Type', required=True,
        help="These types are defined according to your country. The type contains more information "\
        "about the account and its specificities.")
    reconcile = fields.Boolean(string='Allow Invoices & payments Matching', default=False,
        help="Check this option if you want the user to reconcile entries in this account.")
    note = fields.Text()
    tax_ids = fields.Many2many('account.tax.template', 'account_account_template_tax_rel', 'account_id', 'tax_id', string='Default Taxes')
    nocreate = fields.Boolean(string='Optional Create', default=False,
        help="If checked, the new chart of accounts will not contain this by default.")
    chart_template_id = fields.Many2one('account.chart.template', string='Chart Template',
        help="This optional field allow you to link an account template to a specific chart template that may differ from the one its root parent belongs to. This allow you "
            "to define chart templates that extend another and complete it with few new accounts (You don't need to define the whole structure that is common to both several times).")

    @api.multi
    @api.depends('name', 'code')
    def name_get(self):
        res = []
        for record in self:
            name = record.name
            if record.code:
                name = record.code + ' ' + name
            res.append((record.id, name))
        return res


class AccountAddTmplWizard(models.TransientModel):
    """Add one more account from the template.

    With the 'nocreate' option, some accounts may not be created. Use this to add them later."""
    _name = 'account.addtmpl.wizard'

    @api.model
    def _get_def_cparent(self):
        context = self._context or {}
        tmpl_obj = self.env['account.account.template']

        tids = tmpl_obj.read([context['tmpl_ids']], ['parent_id'])
        if not tids or not tids[0]['parent_id']:
            return False
        ptids = tmpl_obj.read([tids[0]['parent_id'][0]], ['code'])
        account = False
        if not ptids or not ptids[0]['code']:
            raise UserError(_('There is no parent code for the template account.'))
            account = self.env['account.account'].search([('code', '=', ptids[0]['code'])], limit=1)
        return account

    cparent_id = fields.Many2one('account.account', string='Parent target', default=lambda self: self._get_def_cparent(),
        help="Creates an account with the selected template under this existing parent.", required=True, domain=[('deprecated', '=', False)])

    @api.multi
    def action_create(self):
        context = self._context or {}
        AccountObj = self.env['account.account']
        data = self.read()[0]
        company_id = AccountObj.read([data['cparent_id'][0]], ['company_id'])[0]['company_id'][0]
        account_template = self.env['account.account.template'].browse(context['tmpl_ids'])
        vals = {
            'name': account_template.name,
            'currency_id': account_template.currency_id and account_template.currency_id.id or False,
            'code': account_template.code,
            'user_type': account_template.user_type and account_template.user_type.id or False,
            'reconcile': account_template.reconcile,
            'note': account_template.note,
            'parent_id': data['cparent_id'][0],
            'company_id': company_id,
        }
        AccountObj.create(vals)
        return {'type': 'state', 'state': 'end'}

    @api.multi
    def action_cancel(self):
        return {'type': 'state', 'state': 'end'}


class AccountChartTemplate(models.Model):
    _name = "account.chart.template"
    _description = "Templates for Account Chart"

    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company', string='Root Tax Code')
    parent_id = fields.Many2one('account.chart.template', string='Parent Chart Template')
    code_digits = fields.Integer(string='# of Digits', required=True, default=6, help="No. of Digits to use for account code")
    visible = fields.Boolean(string='Can be Visible?', default=True,
        help="Set this to False if you don't want this template to be used actively in the wizard that generate Chart of Accounts from "
            "templates, this is useful when you want to generate accounts of this template only when loading its child template.")
    currency_id = fields.Many2one('res.currency', string='Currency')
    use_anglo_saxon = fields.Boolean(string="Use Anglo-Saxon accounting", default=False)
    complete_tax_set = fields.Boolean(string='Complete Set of Taxes', default=True,
        help="This boolean helps you to choose if you want to propose to the user to encode the sale and purchase rates or choose from list "
            "of taxes. This last choice assumes that the set of tax defined on this template is complete")
    account_ids = fields.One2many('account.account.template', 'chart_template_id', string='Associated Account Templates')
    tax_template_ids = fields.One2many('account.tax.template', 'chart_template_id', string='Tax Template List',
        help='List of all the taxes that have to be installed by the wizard')
    bank_account_code_char = fields.Char(string='Code of the main bank account')
    transfer_account_id = fields.Many2one('account.account.template', string='Transfer Account',
        domain=lambda self: [('reconcile', '=', True), ('user_type.id', '=', self.env.ref('account.data_account_type_current_assets').id)],
        help="Intermediary account used when moving money from a liquidity account to another")
    property_account_receivable = fields.Many2one('account.account.template', string='Receivable Account')
    property_account_payable = fields.Many2one('account.account.template', string='Payable Account')
    property_account_expense_categ = fields.Many2one('account.account.template', string='Expense Category Account')
    property_account_income_categ = fields.Many2one('account.account.template', string='Income Category Account')
    property_account_expense = fields.Many2one('account.account.template', string='Expense Account on Product Template')
    property_account_income = fields.Many2one('account.account.template', string='Income Account on Product Template')
    property_account_income_opening = fields.Many2one('account.account.template', string='Opening Entries Income Account')
    property_account_expense_opening = fields.Many2one('account.account.template', string='Opening Entries Expense Account')

    @api.one
    def try_loading_for_current_company(self):
        self.ensure_one()
        company = self.env.user.company_id
        accounts = self.env['account.account'].search([('company_id', '=', company.id), ('deprecated', '=', False), ('name', 'not ilike', 'Automated Test'),
            ('name', 'not ilike', '(test)')], limit=1)
        # If we don't have any accounts, install this chart of account
        if not accounts:
            self._load_template(company)
            # Create account and journal for cash
            company.write({'bank_account_code_char': self.bank_account_code_char, 'accounts_code_digits': self.code_digits})
            wiz_obj = self.env['wizard.multi.charts.accounts']
            acc_obj = self.env['account.account']
            line = {'acc_name': 'cash', 'account_type': 'cash', 'currency_id': False}
            vals = wiz_obj._prepare_bank_account(company, line)
            cash_account = acc_obj.create(vals)
            vals = wiz_obj._prepare_bank_journal(company, line, cash_account.id)
            self.env['account.journal'].create(vals)

    @api.model
    def check_created_journals(self, vals_journal, company):
        """
        This method used for checking journals already created or not. If not then create new journal.
        """
        JournalObj = self.env['account.journal']
        rec_list = JournalObj.search([('name', '=', vals_journal['name']), ('company_id', '=', company.id)], limit=1)
        if not rec_list:
            JournalObj.create(vals_journal)
        return True

    @api.model
    def generate_journals(self, acc_template_ref, company):
        """
        This method is used for creating journals.

        :param chart_temp_id: Chart Template Id.
        :param acc_template_ref: Account templates reference.
        :param company_id: company_id selected from wizard.multi.charts.accounts.
        :returns: True
        """
        journal_data = self._prepare_all_journals(acc_template_ref, company)
        for vals_journal in journal_data:
            self.check_created_journals(vals_journal, company)
        return True

    @api.multi
    def _prepare_all_journals(self, acc_template_ref, company):
        def _get_analytic_journal(journal_type):
            # Get the analytic journal
            data = False
            try:
                if journal_type == 'sale':
                    data = self.env.ref('account.analytic_journal_sale')
                elif journal_type == 'purchase':
                    data = self.env.ref('account.exp')
                elif journal_type == 'general':
                    pass
            except ValueError:
                pass
            return data and data.id or False

        def _get_default_account(journal_type, type='debit'):
            # Get the default accounts
            default_account = False
            if journal_type == 'sale':
                default_account = acc_template_ref.get(self.property_account_income_categ.id)
            elif journal_type == 'purchase':
                default_account = acc_template_ref.get(self.property_account_expense_categ.id)
            return default_account

        journal_names = {
            'sale': _('Sales Journal'),
            'purchase': _('Purchase Journal'),
            'general': _('Miscellaneous Journal'),
        }
        journal_codes = {
            'sale': _('SAJ'),
            'purchase': _('EXJ'),
            'general': _('MISC'),
        }

        self.ensure_one()
        journal_data = []
        for journal_type in ['sale', 'purchase', 'general']:
            vals = {
                'type': journal_type,
                'name': journal_names[journal_type],
                'code': journal_codes[journal_type],
                'company_id': company.id,
                'analytic_journal_id': _get_analytic_journal(journal_type),
                'default_credit_account_id': _get_default_account(journal_type, 'credit'),
                'default_debit_account_id': _get_default_account(journal_type, 'debit'),
                'refund_sequence': True,
            }
            journal_data.append(vals)
        return journal_data

    @api.multi
    def generate_properties(self, acc_template_ref, company):
        """
        This method used for creating properties.

        :param self: chart templates for which we need to create properties
        :param acc_template_ref: Mapping between ids of account templates and real accounts created from them
        :param company_id: company_id selected from wizard.multi.charts.accounts.
        :returns: True
        """
        self.ensure_one()
        PropertyObj = self.env['ir.property']
        todo_list = [
            ('property_account_receivable', 'res.partner', 'account.account'),
            ('property_account_payable', 'res.partner', 'account.account'),
            ('property_account_expense_categ', 'product.category', 'account.account'),
            ('property_account_income_categ', 'product.category', 'account.account'),
            ('property_account_expense', 'product.template', 'account.account'),
            ('property_account_income', 'product.template', 'account.account'),
        ]
        for record in todo_list:
            account = getattr(self, record[0])
            value = account and 'account.account,' + str(acc_template_ref[account.id]) or False
            if value:
                field = self.env['ir.model.fields'].search([('name', '=', record[0]), ('model', '=', record[1]), ('relation', '=', record[2])], limit=1)
                vals = {
                    'name': record[0],
                    'company_id': company.id,
                    'fields_id': field.id,
                    'value': value,
                }
                properties = PropertyObj.search([('name', '=', record[0]), ('company_id', '=', company.id)])
                if properties:
                    #the property exist: modify it
                    properties.write(vals)
                else:
                    #create the property
                    PropertyObj.create(vals)
        return True

    @api.multi
    def _install_template(self, company, code_digits=None, transfer_account_id=None, obj_wizard=None, acc_ref=None, taxes_ref=None):
        """ Recursively load the template objects and create the real objects from them.

            :param company: company the wizard is running for
            :param code_digits: number of digits the accounts code should have in the COA
            :param transfer_account_id: reference to the account template that will be used as intermediary account for transfers between 2 liquidity accounts
            :param obj_wizard: the current wizard for generating the COA from the templates
            :param acc_ref: Mapping between ids of account templates and real accounts created from them
            :param taxes_ref: Mapping between ids of tax templates and real taxes created from them
            :returns: tuple with a dictionary containing
                * the mapping between the account template ids and the ids of the real accounts that have been generated
                  from them, as first item,
                * a similar dictionary for mapping the tax templates and taxes, as second item,
            :rtype: tuple(dict, dict, dict)
        """
        self.ensure_one()
        if acc_ref is None:
            acc_ref = {}
        if taxes_ref is None:
            taxes_ref = {}
        if self.parent_id:
            tmp1, tmp2 = self.parent_id._install_template(company, code_digits=code_digits, transfer_account_id=transfer_account_id, acc_ref=acc_ref, taxes_ref=taxes_ref)
            acc_ref.update(tmp1)
            taxes_ref.update(tmp2)
        tmp1, tmp2 = self._load_template(company, code_digits=code_digits, transfer_account_id=transfer_account_id, account_ref=acc_ref, taxes_ref=taxes_ref)
        acc_ref.update(tmp1)
        taxes_ref.update(tmp2)
        return acc_ref, taxes_ref

    @api.multi
    def _load_template(self, company, code_digits=None, transfer_account_id=None, account_ref=None, taxes_ref=None):
        """ Generate all the objects from the templates

            :param company: company the wizard is running for
            :param code_digits: number of digits the accounts code should have in the COA
            :param transfer_account_id: reference to the account template that will be used as intermediary account for transfers between 2 liquidity accounts
            :param acc_ref: Mapping between ids of account templates and real accounts created from them
            :param taxes_ref: Mapping between ids of tax templates and real taxes created from them
            :returns: tuple with a dictionary containing
                * the mapping between the account template ids and the ids of the real accounts that have been generated
                  from them, as first item,
                * a similar dictionary for mapping the tax templates and taxes, as second item,
            :rtype: tuple(dict, dict, dict)
        """
        self.ensure_one()
        if account_ref is None:
            account_ref = {}
        if taxes_ref is None:
            taxes_ref = {}
        if not code_digits:
            code_digits = self.code_digits
        if not transfer_account_id:
            transfer_account_id = self.transfer_account_id
        AccountTaxObj = self.env['account.tax']

        # Generate taxes from templates.
        generated_tax_res = self.tax_template_ids._generate_tax(company)
        taxes_ref.update(generated_tax_res['tax_template_to_tax'])

        # Generating Accounts from templates.
        account_template_ref = self.generate_account(taxes_ref, account_ref, code_digits, company)
        account_ref.update(account_template_ref)

        # writing account values after creation of accounts
        company.transfer_account_id = account_template_ref[transfer_account_id.id]
        for key, value in generated_tax_res['account_dict'].items():
            if value['refund_account_id'] or value['account_id']:
                AccountTaxObj.browse(key).write({
                    'refund_account_id': account_ref.get(value['refund_account_id'], False),
                    'account_id': account_ref.get(value['account_id'], False),
                })

        # Create Journals
        self.generate_journals(account_ref, company)

        # generate properties function
        self.generate_properties(account_ref, company)

        # Generate Fiscal Position , Fiscal Position Accounts and Fiscal Position Taxes from templates
        self.generate_fiscal_position(taxes_ref, account_ref, company)

        return account_ref, taxes_ref

    @api.multi
    def generate_account(self, tax_template_ref, acc_template_ref, code_digits, company):
        """ This method for generating accounts from templates.

            :param tax_template_ref: Taxes templates reference for write taxes_id in account_account.
            :param acc_template_ref: dictionary with the mappping between the account templates and the real accounts.
            :param code_digits: number of digits got from wizard.multi.charts.accounts, this is use for account code.
            :param company_id: company_id selected from wizard.multi.charts.accounts.
            :returns: return acc_template_ref for reference purpose.
            :rtype: dict
        """
        self.ensure_one()
        company_name = company.name
        account_tmpl_obj = self.env['account.account.template']
        acc_template = account_tmpl_obj.search([('nocreate', '!=', True), ('chart_template_id', '=', self.id)], order='id')
        for account_template in acc_template:
            tax_ids = []
            for tax in account_template.tax_ids:
                tax_ids.append(tax_template_ref[tax.id])

            code_main = account_template.code and len(account_template.code) or 0
            code_acc = account_template.code or ''
            if code_main > 0 and code_main <= code_digits:
                code_acc = str(code_acc) + (str('0'*(code_digits-code_main)))
            vals = {
                'name': account_template.name,
                'currency_id': account_template.currency_id and account_template.currency_id.id or False,
                'code': code_acc,
                'user_type': account_template.user_type and account_template.user_type.id or False,
                'reconcile': account_template.reconcile,
                'note': account_template.note,
                'tax_ids': [(6, 0, tax_ids)],
                'company_id': company.id,
            }
            new_account = self.env['account.account'].create(vals)
            acc_template_ref[account_template.id] = new_account.id
        return acc_template_ref

    @api.multi
    def generate_fiscal_position(self, tax_template_ref, acc_template_ref, company):
        """ This method generate Fiscal Position, Fiscal Position Accounts and Fiscal Position Taxes from templates.

            :param chart_temp_id: Chart Template Id.
            :param taxes_ids: Taxes templates reference for generating account.fiscal.position.tax.
            :param acc_template_ref: Account templates reference for generating account.fiscal.position.account.
            :param company_id: company_id selected from wizard.multi.charts.accounts.
            :returns: True
        """
        self.ensure_one()
        positions = self.env['account.fiscal.position.template'].search([('chart_template_id', '=', self.id)])
        for position in positions:
            new_fp = self.env['account.fiscal.position'].create({'company_id': company.id, 'name': position.name, 'note': position.note})
            for tax in position.tax_ids:
                self.env['account.fiscal.position.tax'].create({
                    'tax_src_id': tax_template_ref[tax.tax_src_id.id],
                    'tax_dest_id': tax.tax_dest_id and tax_template_ref[tax.tax_dest_id.id] or False,
                    'position_id': new_fp.id
                })
            for acc in position.account_ids:
                self.env['account.fiscal.position.account'].create({
                    'account_src_id': acc_template_ref[acc.account_src_id.id],
                    'account_dest_id': acc_template_ref[acc.account_dest_id.id],
                    'position_id': new_fp.id
                })
        return True


class AccountTaxTemplate(models.Model):
    _name = 'account.tax.template'
    _description = 'Templates for Taxes'
    _order = 'id'

    chart_template_id = fields.Many2one('account.chart.template', string='Chart Template', required=True)

    name = fields.Char(string='Tax Name', required=True, translate=True)
    type_tax_use = fields.Selection([('sale', 'Sales'), ('purchase', 'Purchases'), ('none', 'None')], string='Tax Scope', required=True, default="sale",
        help="Determines where the tax is selectable. Note : 'None' means a tax can't be used by itself, however it can still be used in a group.")
    amount_type = fields.Selection(default='percent', string="Tax Computation", required=True,
        selection=[('group', 'Group of Taxes'), ('fixed', 'Fixed'), ('percent', 'Percentage of Price'), ('division', 'Percentage of Price Tax Included')])
    active = fields.Boolean(default=True, help="Set active to false to hide the tax without removing it.")
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    children_tax_ids = fields.Many2many('account.tax.template', 'account_tax_template_filiation_rel', 'parent_tax', 'child_tax', string='Children Taxes')
    sequence = fields.Integer(required=True, default=1,
        help="The sequence field is used to define order in which the tax lines are applied.")
    amount = fields.Float(required=True, digits=(16, 3))
    account_id = fields.Many2one('account.account.template', string='Tax Account', ondelete='restrict',
        help="Account that will be set on invoice tax lines for invoices. Leave empty to use the expense account.")
    refund_account_id = fields.Many2one('account.account.template', string='Tax Account on Refunds', ondelete='restrict',
        help="Account that will be set on invoice tax lines for refunds. Leave empty to use the expense account.")
    description = fields.Char(string='Display on Invoices')
    price_include = fields.Boolean(string='Included in Price', default=False,
        help="Check this if the price you use on the product and invoices includes this tax.")
    include_base_amount = fields.Boolean(string='Affect Subsequent Taxes', default=False,
        help="If set, taxes which are computed after this one will be computed based on the price tax included.")
    analytic = fields.Boolean(string="Analytic Cost", help="If set, the amount computed by this tax will be assigned to the same analytic account as the invoice line (if any)")

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 'Tax names must be unique !'),
    ]

    @api.multi
    @api.depends('name', 'description')
    def name_get(self):
        res = []
        for record in self:
            name = record.description and record.description or record.name
            res.append((record.id, name))
        return res

    @api.multi
    def _generate_tax(self, company):
        """ This method generate taxes from templates.

            :param company: the company for which the taxes should be created from templates in self
            :returns: {
                'tax_template_to_tax': mapping between tax template and the newly generated taxes corresponding,
                'account_dict': dictionary containing a to-do list with all the accounts to assign on new taxes
            }
        """
        todo_dict = {}
        tax_template_to_tax = {}
        for tax in self:
            # Compute children tax ids
            children_ids = []
            for child_tax in tax.children_tax_ids:
                if tax_template_to_tax.get(child_tax.id):
                    children_ids.append(tax_template_to_tax[child_tax.id])
            vals_tax = {
                'name': tax.name,
                'type_tax_use': tax.type_tax_use,
                'amount_type': tax.amount_type,
                'active': tax.active,
                'company_id': company.id,
                'children_tax_ids': children_ids and [(6, 0, children_ids)] or [],
                'sequence': tax.sequence,
                'amount': tax.amount,
                'description': tax.description,
                'price_include': tax.price_include,
                'include_base_amount': tax.include_base_amount,
                'analytic': tax.analytic,
            }
            new_tax = self.env['account.tax'].create(vals_tax)
            tax_template_to_tax[tax.id] = new_tax.id
            # Since the accounts have not been created yet, we have to wait before filling these fields
            todo_dict[new_tax.id] = {
                'account_id': tax.account_id.id,
                'refund_account_id': tax.refund_account_id.id,
            }

        return {
            'tax_template_to_tax': tax_template_to_tax,
            'account_dict': todo_dict
        }


# Fiscal Position Templates

class AccountFiscalPositionTemplate(models.Model):
    _name = 'account.fiscal.position.template'
    _description = 'Template for Fiscal Position'

    name = fields.Char(string='Fiscal Position Template', required=True)
    chart_template_id = fields.Many2one('account.chart.template', string='Chart Template', required=True)
    account_ids = fields.One2many('account.fiscal.position.account.template', 'position_id', string='Account Mapping')
    tax_ids = fields.One2many('account.fiscal.position.tax.template', 'position_id', string='Tax Mapping')
    note = fields.Text(string='Notes')


class AccountFiscalPositionTaxTemplate(models.Model):
    _name = 'account.fiscal.position.tax.template'
    _description = 'Template Tax Fiscal Position'
    _rec_name = 'position_id'

    position_id = fields.Many2one('account.fiscal.position.template', string='Fiscal Position', required=True, ondelete='cascade')
    tax_src_id = fields.Many2one('account.tax.template', string='Tax Source', required=True)
    tax_dest_id = fields.Many2one('account.tax.template', string='Replacement Tax')


class AccountFiscalPositionAccountTemplate(models.Model):
    _name = 'account.fiscal.position.account.template'
    _description = 'Template Account Fiscal Mapping'
    _rec_name = 'position_id'

    position_id = fields.Many2one('account.fiscal.position.template', string='Fiscal Mapping', required=True, ondelete='cascade')
    account_src_id = fields.Many2one('account.account.template', string='Account Source', required=True)
    account_dest_id = fields.Many2one('account.account.template', string='Account Destination', required=True)

# ---------------------------------------------------------
# Account generation from template wizards
# ---------------------------------------------------------


class WizardMultiChartsAccounts(models.TransientModel):
    """
    Create a new account chart for a company.
    Wizards ask for:
        * a company
        * an account chart template
        * a number of digits for formatting code of non-view accounts
        * a list of bank accounts owned by the company
    Then, the wizard:
        * generates all accounts from the template and assigns them to the right company
        * generates all taxes and tax codes, changing account assignations
        * generates all accounting properties and assigns them correctly
    """

    _name = 'wizard.multi.charts.accounts'
    _inherit = 'res.config'

    company_id = fields.Many2one('res.company', string='Company', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', help="Currency as per company's country.")
    only_one_chart_template = fields.Boolean(string='Only One Chart Template Available')
    chart_template_id = fields.Many2one('account.chart.template', string='Chart Template', required=True)
    bank_accounts_id = fields.One2many('account.bank.accounts.wizard', 'bank_account_id', string='Cash and Banks', required=True)
    bank_account_code_char = fields.Char('Bank Accounts Code')
    code_digits = fields.Integer(string='# of Digits', required=True, help="No. of Digits to use for account code")
    sale_tax = fields.Many2one('account.tax.template', string='Default Sales Tax')
    purchase_tax = fields.Many2one('account.tax.template', string='Default Purchase Tax')
    sale_tax_rate = fields.Float(string='Sales Tax(%)')
    use_anglo_saxon = fields.Boolean(string='Use Anglo-Saxon Accounting', related='chart_template_id.use_anglo_saxon')
    transfer_account_id = fields.Many2one('account.account.template', required=True, string='Transfer Account',
        domain=lambda self: [('reconcile', '=', True), ('user_type.id', '=', self.env.ref('account.data_account_type_current_assets').id)],
        help="Intermediary account used when moving money from a liquidity account to another")
    purchase_tax_rate = fields.Float(string='Purchase Tax(%)')
    complete_tax_set = fields.Boolean('Complete Set of Taxes',
        help="This boolean helps you to choose if you want to propose to the user to encode the sales and purchase rates or use "
            "the usual m2o fields. This last choice assumes that the set of tax defined for the chosen template is complete")

    @api.model
    def _get_chart_parent_ids(self, chart_template):
        """ Returns the IDs of all ancestor charts, including the chart itself.
            (inverse of child_of operator)

            :param browse_record chart_template: the account.chart.template record
            :return: the IDS of all ancestor charts, including the chart itself.
        """
        result = [chart_template.id]
        while chart_template.parent_id:
            chart_template = chart_template.parent_id
            result.append(chart_template.id)
        return result

    @api.onchange('sale_tax_rate')
    def onchange_tax_rate(self):
        self.purchase_tax_rate = self.sale_tax_rate or False

    @api.onchange('chart_template_id')
    def onchange_chart_template_id(self):
        res = {}
        tax_templ_obj = self.env['account.tax.template']
        if self.chart_template_id:
            currency_id = self.chart_template_id.currency_id and self.chart_template_id.currency_id.id or self.env.user.company_id.currency_id.id
            self.complete_tax_set = self.chart_template_id.complete_tax_set
            self.currency_id = currency_id
            if self.chart_template_id.complete_tax_set:
            # default tax is given by the lowest sequence. For same sequence we will take the latest created as it will be the case for tax created while isntalling the generic chart of account
                chart_ids = self._get_chart_parent_ids(self.chart_template_id)
                base_tax_domain = [('chart_template_id', 'in', chart_ids)]
                sale_tax_domain = base_tax_domain + [('type_tax_use', '=', 'sale')]
                purchase_tax_domain = base_tax_domain + [('type_tax_use', '=', 'purchase')]
                sale_tax = tax_templ_obj.search(sale_tax_domain, order="sequence, id desc", limit=1)
                purchase_tax = tax_templ_obj.search(purchase_tax_domain, order="sequence, id desc", limit=1)
                self.sale_tax = sale_tax.id
                self.purchase_tax = purchase_tax.id
                res.setdefault('domain', {})
                res['domain']['sale_tax'] = repr(sale_tax_domain)
                res['domain']['purchase_tax'] = repr(purchase_tax_domain)
            if self.chart_template_id.transfer_account_id:
                self.transfer_account_id = self.chart_template_id.transfer_account_id.id
            if self.chart_template_id.code_digits:
                self.code_digits = self.chart_template_id.code_digits
            if self.chart_template_id.bank_account_code_char:
                self.bank_account_code_char = self.chart_template_id.bank_account_code_char
        return res

    @api.model
    def default_get(self, fields):
        context = self._context or {}
        res = super(WizardMultiChartsAccounts, self).default_get(fields)
        tax_templ_obj = self.env['account.tax.template']
        account_chart_template = self.env['account.chart.template']

        if 'bank_accounts_id' in fields:
            res.update({'bank_accounts_id': [{'acc_name': _('Cash'), 'account_type': 'cash'}, {'acc_name': _('Bank'), 'account_type': 'bank'}]})
        if 'company_id' in fields:
            res.update({'company_id': self.env.user.company_id.id})
        if 'currency_id' in fields:
            company_id = res.get('company_id') or False
            if company_id:
                company = self.env['res.company'].browse(company_id)
                currency_id = company.on_change_country(company.country_id.id)['value']['currency_id']
                res.update({'currency_id': currency_id})

        chart_templates = account_chart_template.search([('visible', '=', True)])
        if chart_templates:
            #in order to set default chart which was last created set max of ids.
            chart_id = max(chart_templates.ids)
            if context.get("default_charts"):
                model_data = self.env['ir.model.data'].search_read([('model', '=', 'account.chart.template'), ('module', '=', context.get("default_charts"))], ['res_id'])
                if model_data:
                    chart_id = model_data[0]['res_id']
            chart = account_chart_template.browse(chart_id)
            chart_hierarchy_ids = self._get_chart_parent_ids(chart)
            if 'chart_template_id' in fields:
                res.update({'only_one_chart_template': len(chart_templates) == 1,
                            'chart_template_id': chart_id})
            if 'sale_tax' in fields:
                sale_tax = tax_templ_obj.search([('chart_template_id', 'in', chart_hierarchy_ids),
                                                              ('type_tax_use', '=', 'sale')], limit=1, order='sequence')
                res.update({'sale_tax': sale_tax and sale_tax.id or False})
            if 'purchase_tax' in fields:
                purchase_tax = tax_templ_obj.search([('chart_template_id', 'in', chart_hierarchy_ids),
                                                                  ('type_tax_use', '=', 'purchase')], limit=1, order='sequence')
                res.update({'purchase_tax': purchase_tax and purchase_tax.id or False})
        res.update({
            'purchase_tax_rate': 15.0,
            'sale_tax_rate': 15.0,
        })
        return res

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        context = self._context or {}
        res = super(WizardMultiChartsAccounts, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=False)
        cmp_select = []
        CompanyObj = self.env['res.company']

        companies = CompanyObj.search([])
        #display in the widget selection of companies, only the companies that haven't been configured yet (but don't care about the demo chart of accounts)
        self._cr.execute("SELECT company_id FROM account_account WHERE deprecated = 'f' AND name != 'Chart For Automated Tests' AND name NOT LIKE '%(test)'")
        configured_cmp = [r[0] for r in self._cr.fetchall()]
        unconfigured_cmp = list(set(companies.ids) - set(configured_cmp))
        for field in res['fields']:
            if field == 'company_id':
                res['fields'][field]['domain'] = [('id', 'in', unconfigured_cmp)]
                res['fields'][field]['selection'] = [('', '')]
                if unconfigured_cmp:
                    cmp_select = [(line.id, line.name) for line in CompanyObj.browse(unconfigured_cmp)]
                    res['fields'][field]['selection'] = cmp_select
        return res

    @api.one
    def _create_tax_templates_from_rates(self, company_id):
        '''
        This function checks if the chosen chart template is configured as containing a full set of taxes, and if
        it's not the case, it creates the templates for account.tax object accordingly to the provided sale/purchase rates.
        Then it saves the new tax templates as default taxes to use for this chart template.

        :param company_id: id of the company for wich the wizard is running
        :return: True
        '''
        obj_tax_temp = self.env['account.tax.template']
        all_parents = self._get_chart_parent_ids(self.chart_template_id)
        # create tax templates from purchase_tax_rate and sale_tax_rate fields
        if not self.chart_template_id.complete_tax_set:
            value = self.sale_tax_rate
            ref_taxs = obj_tax_temp.search([('type_tax_use', '=', 'sale'), ('chart_template_id', 'in', all_parents)], order="sequence, id desc", limit=1)
            ref_taxs.write({'amount': value, 'name': _('Tax %.2f%%') % value})
            value = self.purchase_tax_rate
            ref_taxs = obj_tax_temp.search([('type_tax_use', '=', 'purchase'), ('chart_template_id', 'in', all_parents)], order="sequence, id desc", limit=1)
            ref_taxs.write({'amount': value, 'name': _('Purchase Tax %.2f%%') % value})
        return True

    @api.multi
    def execute(self):
        '''
        This function is called at the confirmation of the wizard to generate the COA from the templates. It will read
        all the provided information to create the accounts, the banks, the journals, the taxes, the
        accounting properties... accordingly for the chosen company.
        '''
        if self._uid != self.sudo()._uid and not self.env.user.has_group('base.group_erp_manager'):
            raise AccessError(_("Only administrators can change the settings"))
        ir_values_obj = self.env['ir.values']
        company = self.company_id
        self.company_id.write({'currency_id': self.currency_id.id,
                               'accounts_code_digits': self.code_digits,
                               'anglo_saxon_accounting': self.use_anglo_saxon,
                               'bank_account_code_char': self.bank_account_code_char})

        # When we install the CoA of first company, set the currency to price types and pricelists
        if company.id == 1:
            for reference in ['product.list_price', 'product.standard_price', 'product.list0', 'purchase.list0']:
                try:
                    tmp2 = self.env.ref(reference).write({'currency_id': self.currency_id.id})
                except ValueError:
                    pass

        # If the floats for sale/purchase rates have been filled, create templates from them
        self._create_tax_templates_from_rates(company.id)

        # Install all the templates objects and generate the real objects

        acc_template_ref, taxes_ref = self.chart_template_id._install_template(company, code_digits=self.code_digits, transfer_account_id=self.transfer_account_id)

        # write values of default taxes for product as super user
        if self.sale_tax and taxes_ref:
            ir_values_obj.sudo().set_default('product.template', "taxes_id", [taxes_ref[self.sale_tax.id]], for_all_users=True, company_id=company.id)
        if self.purchase_tax and taxes_ref:
            ir_values_obj.sudo().set_default('product.template', "supplier_taxes_id", [taxes_ref[self.purchase_tax.id]], for_all_users=True, company_id=company.id)

        # Create Bank journals
        self._create_bank_journals_from_o2m(company, acc_template_ref)
        return {}

    @api.model
    def _prepare_bank_journal(self, company, line, default_account_id):
        '''
        This function prepares the value to use for the creation of a bank journal created through the wizard of
        generating COA from templates.

        :param line: dictionary containing the values encoded by the user related to his bank account
        :param default_account_id: id of the default debit.credit account created before for this journal.
        :param company_id: id of the company for which the wizard is running
        :return: mapping of field names and values
        :rtype: dict
        '''
        # we need to loop to find next number for journal code
        for num in xrange(1, 100):
            # journal_code has a maximal size of 5, hence we can enforce the boundary num < 100
            journal_code = _('BNK')[:3] + str(num)
            journal = self.env['account.journal'].search([('code', '=', journal_code), ('company_id', '=', company.id)], limit=1)
            if not journal:
                break
        else:
            raise UserError(_('Cannot generate an unused journal code.'))

        return {
                'name': line['acc_name'],
                'code': journal_code,
                'type': line['account_type'] == 'cash' and 'cash' or 'bank',
                'company_id': company.id,
                'analytic_journal_id': False,
                'currency': line['currency_id'] or False,
                'default_credit_account_id': default_account_id,
                'default_debit_account_id': default_account_id,
        }

    @api.model
    def _prepare_bank_account(self, company, line, acc_template_ref=False, ref_acc_bank=False):
        '''
        This function prepares the value to use for the creation of the default debit and credit accounts of a
        bank journal created through the wizard of generating COA from templates.

        :param company: company for which the wizard is running
        :param line: dictionary containing the values encoded by the user related to his bank account
        :param acc_template_ref: the dictionary containing the mapping between the ids of account templates and the ids
            of the accounts that have been generated from them.
        :param ref_acc_bank: browse record of the account template set as root of all bank accounts for the chosen
            template
        :return: mapping of field names and values
        :rtype: dict
        '''

        # Seek the next available number for the account code
        code_digits = company.accounts_code_digits or 0
        bank_account_code_char = company.bank_account_code_char or ''
        for num in xrange(1, 100):
            new_code = str(bank_account_code_char.ljust(code_digits - 1, '0')) + str(num)
            rec = self.env['account.account'].search([('code', '=', new_code), ('company_id', '=', company.id)], limit=1)
            if not rec:
                break
        else:
            raise UserError(_('Cannot generate an unused account code.'))

        liquidity_type = self.env.ref('account.data_account_type_liquidity')

        return {
                'name': line['acc_name'],
                'currency_id': line['currency_id'] or False,
                'code': new_code,
                'user_type': liquidity_type and liquidity_type.id or False,
                'company_id': company.id,
        }

    @api.multi
    def _create_bank_journals_from_o2m(self, company, acc_template_ref):
        '''
        This function creates bank journals and its accounts for each line encoded in the field bank_accounts_id of the
        wizard.

        :param company_id: the id of the company for which the wizard is running.
        :param acc_template_ref: the dictionary containing the mapping between the ids of account templates and the ids
            of the accounts that have been generated from them.
        :return: True
        '''
        self.ensure_one()
        # Build a list with all the data to process
        journal_data = []
        if self.bank_accounts_id:
            for acc in self.bank_accounts_id:
                vals = {
                    'acc_name': acc.acc_name,
                    'account_type': acc.account_type,
                    'currency_id': acc.currency_id.id,
                }
                journal_data.append(vals)
        ref_acc_bank = self.bank_account_code_char
        if journal_data and not ref_acc_bank:
            raise UserError(_('You have to set a code for the bank account defined on the selected chart of accounts.'))
        company.write({'bank_account_code_char': ref_acc_bank})

        for line in journal_data:
            # Create the default debit/credit accounts for this bank journal
            vals = self._prepare_bank_account(company, line, acc_template_ref, ref_acc_bank)
            default_account = self.env['account.account'].create(vals)

            #create the bank journal
            vals_journal = self._prepare_bank_journal(company, line, default_account.id)
            self.env['account.journal'].create(vals_journal)
        return True


class AccountBankAccountsWizard(models.TransientModel):
    _name = 'account.bank.accounts.wizard'

    acc_name = fields.Char(string='Account Name.', required=True)
    bank_account_id = fields.Many2one('wizard.multi.charts.accounts', string='Bank Account', required=True, ondelete='cascade')
    currency_id = fields.Many2one('res.currency', string='Secondary Currency',
        help="Forces all moves for this account to have this secondary currency.")
    account_type = fields.Selection([('cash', 'Cash'), ('check', 'Check'), ('bank', 'Bank')])


class AccountOperationTemplate(models.Model):
    _name = "account.operation.template"
    _description = "Preset to create journal entries during a invoices and payments matching"

    # TODO :
    # - wait for account.analytic.account to ckeck that domain=[('state','not in',('close','cancelled'))] is correct

    name = fields.Char(string='Button Label', required=True)
    sequence = fields.Integer(required=True, default=10)
    has_second_line = fields.Boolean(string='Second line', default=False)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)

    account_id = fields.Many2one('account.account', string='Account', ondelete='cascade', domain=[('deprecated', '=', False), ('internal_type', '!=', 'consolidation')])
    journal_id = fields.Many2one('account.journal', string='Journal', ondelete='cascade', help="This field is ignored in a bank statement reconciliation.")
    label = fields.Char(string='Journal Item Label')
    amount_type = fields.Selection([
        ('fixed', 'Fixed'),
        ('percentage', 'Percentage of amount')
        ], required=True, default='percentage')
    amount = fields.Float(digits=0, required=True, default=100.0, help="Fixed amount will count as a debit if it is negative, as a credit if it is positive.")
    tax_id = fields.Many2one('account.tax', string='Tax', ondelete='restrict', domain=[('type_tax_use', '=', 'purchase')])
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', ondelete='set null', domain=[('state', 'not in', ('close', 'cancelled'))])

    second_account_id = fields.Many2one('account.account', string='Account', ondelete='cascade', domain=[('deprecated', '=', False), ('internal_type', '!=', 'consolidation')])
    second_journal_id = fields.Many2one('account.journal', string='Journal', ondelete='cascade', help="This field is ignored in a bank statement reconciliation.")
    second_label = fields.Char(string='Journal Item Label')
    second_amount_type = fields.Selection([
        ('fixed', 'Fixed'),
        ('percentage', 'Percentage of amount')
        ], string='Amount type', required=True, default='percentage')
    second_amount = fields.Float(string='Amount', digits=0, required=True, default=100.0, help="Fixed amount will count as a debit if it is negative, as a credit if it is positive.")
    second_tax_id = fields.Many2one('account.tax', string='Tax', ondelete='restrict', domain=[('type_tax_use', '=', 'purchase')])
    second_analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', ondelete='set null', domain=[('state', 'not in', ('close', 'cancelled'))])
