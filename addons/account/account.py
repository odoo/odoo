# -*- coding: utf-8 -*-

import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time

import openerp
from openerp import SUPERUSER_ID
from openerp.osv import expression
from openerp.tools.float_utils import float_round as round
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT

import openerp.addons.decimal_precision as dp

from openerp import api, fields, models, _
from openerp.exceptions import Warning

_logger = logging.getLogger(__name__)


class res_company(models.Model):
    _inherit = "res.company"

    income_currency_exchange_account_id = fields.Many2one('account.account',
        string="Gain Exchange Rate Account", domain=[('internal_type', '=', 'other'), ('deprecated', '=', False)])
    expense_currency_exchange_account_id = fields.Many2one('account.account',
        string="Loss Exchange Rate Account", domain=[('internal_type', '=', 'other'), ('deprecated', '=', False)])


class account_payment_term(models.Model):
    _name = "account.payment.term"
    _description = "Payment Term"
    _order = "name"

    name = fields.Char(string='Payment Term', translate=True, required=True)
    active = fields.Boolean(string='Active', default=True,
        help="If the active field is set to False, it will allow you to hide the payment term without removing it.")
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

        amount = reduce(lambda x,y: x + y[1], result, 0.0)
        dist = round(value - amount, prec)
        if dist:
            last_date = result and result[-1][0] or time.strftime('%Y-%m-%d')
            result.append((last_date, dist))
        return result


class account_payment_term_line(models.Model):
    _name = "account.payment.term.line"
    _description = "Payment Term Line"
    _order = "days"

    value = fields.Selection([
            ('balance', 'Balance'),
            ('percent', 'Percent'),
            ('fixed', 'Fixed Amount')
        ], string='Computation', required=True, default='balance',
        help="Select here the kind of valuation related to this payment term line. Note that you should have your last "
            "line with the type 'Balance' to ensure that the whole amount will be treated.")
    value_amount = fields.Float(string='Amount To Pay', digits=dp.get_precision('Payment Term'), help="For percent enter a ratio between 0-100.")
    days = fields.Integer(string='Number of Days', required=True, default=30, help="Number of days to add before computation of the day of month." \
        "If Date=15/01, Number of Days=22, Day of Month=-1, then the due date is 28/02.")
    days2 = fields.Integer(string='Day of the Month', required=True, default='0',
        help="Day of the month, set -1 for the last day of the current month. If it's positive, it gives the day of the next month. "
            "Set 0 for net days (otherwise it's based on the beginning of the month).")
    payment_id = fields.Many2one('account.payment.term', string='Payment Term', required=True, index=True, ondelete='cascade')

    @api.one
    @api.constrains('value', 'value_amount')
    def _check_percent(self):
        if self.value == 'percent' and (self.value_amount < 0.0 or self.value_amount > 100.0):
            raise Warning(_('Percentages for Payment Term Line must be between 0 and 100.'))


class account_account_type(models.Model):
    _name = "account.account.type"
    _description = "Account Type"

    name = fields.Char(string='Account Type', required=True, translate=True)
    close_method = fields.Selection([('none', 'None'), ('balance', 'Balance')],
        string='Deferral Method', required=True, default='none')
    report_type = fields.Selection([
        ('none','/'),
        ('income', _('Profit & Loss (Income account)')),
        ('expense', _('Profit & Loss (Expense account)')),
        ('asset', _('Balance Sheet (Asset account)')),
        ('liability', _('Balance Sheet (Liability account)'))
        ],
        default='none',string='P&L / BS Category', help="This field is used to generate legal reports: profit and loss, balance sheet.", required=True)
    type = fields.Selection([
        ('other', 'Regular'),
        ('receivable', 'Receivable'),
        ('payable', 'Payable'),
        ('liquidity','Liquidity'),
        ('consolidation', 'Consolidation'),
        ], string='Type', required=True, default='other',
        help="The 'Internal Type' is used for features available on "\
        "different types of accounts: consolidation are accounts that "\
        "can have children accounts for multi-company consolidations, payable/receivable are for "\
        "partners accounts (for debit/credit computations).")
    note = fields.Text(string='Description')


#----------------------------------------------------------
# Accounts
#----------------------------------------------------------
class account_account(models.Model):
    _name = "account.account"
    _description = "Account"

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        context = dict(self._context or {})
        if context.get('journal_id', False):
            jour = self.env['account.journal'].browse(context['journal_id'])
            if jour.account_control_ids:
                args.append(('id', 'in', map(lambda x: x.id, jour.account_control_ids)))
            if jour.type_control_ids:
                args.append(('user_type', 'in', map(lambda x: x.id, jour.type_control_ids)))
        return super(account_account, self).search(args, offset, limit, order, count=count)

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
    last_time_entries_checked = fields.Datetime(string='Latest Manual Reconciliation Date', readonly=True, copy=False,
        help='Last time the manual reconciliation was performed on this account. It is set either if there\'s not at least '\
        'an unreconciled debit and an unreconciled credit Or if you click the "Done" button.')

    reconcile = fields.Boolean(string='Allow Reconciliation', default=False,
        help="Check this box if this account allows reconciliation of journal items.")
    tax_ids = fields.Many2many('account.tax', 'account_account_tax_default_rel',
        'account_id', 'tax_id', string='Default Taxes')
    note = fields.Text('Internal Notes')
    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env['res.company']._company_default_get('account.account'))

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
        return super(account_account, self).copy(default)

    @api.multi
    def write(self, vals):
        # Dont allow changing the company_id when account_move_line already exist
        if vals.get('company_id', False):
            move_lines = self.env['account.move.line'].search([('account_id', 'in', self.ids)], limit=1)
            for account in self:
                if (account.company_id.id <> vals['company_id']) and move_lines:
                    raise Warning(_('You cannot change the owner company of an account that already contains journal items.'))
        return super(account_account, self).write(vals)

    @api.multi
    def unlink(self):
        if self.env['account.move.line'].search([('account_id', 'in', self.ids)], limit=1):
            raise Warning(_('You cannot do that on an account that contains journal items.'))
        #Checking whether the account is set as a property to any Partner or not
        values = ['account.account,%s' % (account_id,) for account_id in self.ids]
        partner_prop_acc = self.env['ir.property'].search([('value_reference','in', values)], limit=1)
        if partner_prop_acc:
            raise Warning(_('You cannot remove/deactivate an account which is set on a customer or supplier.'))
        return super(account_account, self).unlink()

    @api.multi
    def mark_as_reconciled(self):
        return self.write({'last_time_entries_checked': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})


class account_journal(models.Model):
    _name = "account.journal"
    _description = "Journal"
    _order = 'sequence, code'

    name = fields.Char(string='Journal Name', required=True)
    code = fields.Char(string='Code', size=5, required=True, help="The code will be displayed on reports.")
    type = fields.Selection([
            ('sale', 'Sale'),
            ('purchase', 'Purchase'),
            ('cash', 'Cash'),
            ('bank', 'Bank and Checks'),
            ('general', 'General'),
            ('situation', 'Opening/Closing Situation')
        ], string='Type', required=True,
        help="Select 'Sale' for customer invoices journals."\
        " Select 'Purchase' for supplier invoices journals."\
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
    sequence= fields.Integer(string='Sequence', help='Used to order Journals')

    groups_id = fields.Many2many('res.groups', 'account_journal_group_rel', 'journal_id', 'group_id', string='Groups')
    currency = fields.Many2one('res.currency', string='Currency', help='The currency used to enter statement')
    entry_posted = fields.Boolean(string='Autopost Created Moves',
        help="Check this box to automatically post entries of this journal. Note that legally, some entries may be automatically posted when the "
            "source document is validated (Invoices), whatever the status of this field.")
    company_id = fields.Many2one('res.company', string='Company', required=True, index=1, default=lambda self: self.env.user.company_id,
        help="Company related to this journal")

    analytic_journal_id = fields.Many2one('account.analytic.journal', string='Analytic Journal', help="Journal for analytic entries")
    refund_sequence = fields.Boolean(string='Dedicated Refund Sequence', help="Check this box if you don't want to share the same sequence for invoices and refunds made from this journal")

    _sql_constraints = [
        ('code_company_uniq', 'unique (code, name, company_id)', 'The code and name of the journal must be unique per company !'),
    ]

    @api.one
    @api.constrains('currency', 'default_credit_account_id', 'default_debit_account_id')
    def _check_currency(self):
        if self.currency:
            if self.default_credit_account_id and not self.default_credit_account_id.currency_id.id == self.currency.id:
                raise Warning(_('Configuration error!\nThe currency of the journal should be the same than the default credit account.'))
            if self.default_debit_account_id and not self.default_debit_account_id.currency_id.id == self.currency.id:
                raise Warning(_('Configuration error!\nThe currency of the journal should be the same than the default debit account.'))

    @api.one
    def copy(self, default=None):
        default = dict(default or {})
        default.update(
            code=_("%s (copy)") % (self.code or ''),
            name=_("%s (copy)") % (self.name or ''))
        return super(account_journal, self).copy(default)

    @api.multi
    def write(self, vals):
        for journal in self:
            if 'company_id' in vals and journal.company_id.id != vals['company_id']:
                if self.env['account.move.line'].search([('journal_id', 'in', self.ids)], limit=1):
                    raise Warning(_('This journal already contains items, therefore you cannot modify its company field.'))
        return super(account_journal, self).write(vals)

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
        return super(account_journal, self).create(vals)

    @api.multi
    @api.depends('name', 'currency', 'company_id', 'company_id.currency_id')
    def name_get(self):
        res = []
        for journal in self:
            currency = journal.currency or journal.company_id.currency_id
            name = "%s (%s)" % (journal.name, currency.name)
            res += [(journal.id, name)]
        return res


class account_fiscalyear(models.Model):
    _name = "account.fiscalyear"
    _description = "Fiscal Year"
    _order = "date_start, id"

    name = fields.Char(string='Fiscal Year', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    date_start = fields.Date(string='Start Date', required=True)
    date_stop = fields.Date(string='End Date', required=True)
    state = fields.Selection([('draft','Open'), ('done','Closed')], string='Status', readonly=True, copy=False, default='draft')
    freeze_date = fields.Date(string='Freeze Date')

    @api.one
    @api.constrains('date_start', 'date_stop')
    def _check_duration(self):
        if self.date_stop < self.date_start:
            raise Warning(_('Error!\nThe start date of a fiscal year must precede its end date.'))


#----------------------------------------------------------
# Entries
#----------------------------------------------------------
class account_move(models.Model):
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
    @api.depends('line_id.debit','line_id.credit')
    def _amount_compute(self):
        for move in self:
            total = 0.0
            for line in move.line_id:
                total += line.debit
            move.amount = total

    name = fields.Char(string='Number', required=True, copy=False, default='/')
    ref = fields.Char(string='Reference', copy=False)
    date = fields.Date(string='Date', required=True, states={'posted': [('readonly', True)]}, index=True, default=fields.Date.context_today)
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, states={'posted': [('readonly', True)]})
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
    amount = fields.Float(compute='_amount_compute', string='Amount', digits=0, store=True)
    narration = fields.Text(string='Internal Note')
    company_id = fields.Many2one('res.company', related='journal_id.company_id', string='Company', store=True, readonly=True,
        default=lambda self: self.env.user.company_id)

    @api.multi
    def post(self):
        invoice = self._context.get('invoice', False)
        self._post_validate()

        for move in self:
            move.line_id.create_analytic_lines()
            if move.name =='/':
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
                        raise Warning(_('Please define a sequence on the journal.'))

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
                raise Warning(_('You cannot modify a posted entry of this journal.\nFirst you should set the journal to allow cancelling entries.'))
        if self.ids:
            self._cr.execute('UPDATE account_move '\
                       'SET state=%s '\
                       'WHERE id IN %s', ('draft', tuple(self.ids),))
            self.invalidate_cache()
        return True

    @api.multi
    def unlink(self, check=True):
        for move in self:
            if move['state'] != 'draft':
                raise Warning(_('You cannot delete a posted journal entry "%s".') % move['name'])
            move.line_id._update_check()
            move.line_id.unlink()
        return super(account_move, self).unlink()

    # TODO: check if date is not closed, otherwise raise exception
    @api.multi
    def _post_validate(self):
        for move in self:
            amount = 0
            for line in move.line_id:
                amount += line.debit - line.credit
                if not move.company_id.id == line.account_id.company_id.id:
                    raise Warning(_("Cannot create moves for different companies."))
                if line.account_id.currency_id and line.currency_id:
                    if line.account_id.currency_id.id != line.currency_id.id and (line.account_id.currency_id.id != line.account_id.company_id.currency_id.id):
                        raise Warning(_("""Cannot create move with currency different from ..""") % (line.account_id.code, line.account_id.name))
            if abs(amount) > 10 ** -4:
                raise Warning(_('You cannot validate a non-balanced entry.'))
        return True

    @api.model
    def account_assert_balanced(self):
        self._cr.execute("""\
            SELECT      move_id
            FROM        account_move_line
            GROUP BY    move_id
            HAVING      abs(sum(debit) - sum(credit)) > 0.00001
            """)
        assert len(self._cr.fetchall()) == 0, \
            "For all Journal Items, the state is valid implies that the sum " \
            "of credits equals the sum of debits"
        return True

    @api.model
    def get_centralisation_move(self, period, journal):
        """ We use a single centralisation move by period - journal couple """
        # TODO : Since we remove the concept of period in favor of a freezing date, this
        # method will have to be written while doing this task. It probably should :
        # - return the move (of course)
        # - raise a warning if the centralisation move is posted (and offer to create it ?)

#----------------------------------------------------------
# Tax
#----------------------------------------------------------

class account_tax(models.Model):
    _name = 'account.tax'
    _description = 'Tax'
    _order = 'sequence'

    name = fields.Char(string='Tax Name', required=True, translate=True)
    type_tax_use = fields.Selection([('sale', 'Sales'), ('purchase', 'Purchases'), ('as_child', 'Only in Tax Group')], string='Tax Scope', required=True, default="sale",
        help="Determines where the tax is selectable. Choose 'Only in Tax Group' if it shouldn't be used outside a group of tax.")
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
        if not all(child.type_tax_use in ('as_child', self.type_tax_use) for child in self.children_tax_ids):
            raise Warning(_('The application scope of taxes in a group must be either the same as the group or "Only in Tax Group".'))

    @api.one
    def copy(self, default=None):
        default = dict(default or {}, name=_("%s (Copy)") % self.name)
        return super(account_tax, self).copy(default=default)

    #@api.model
    #def name_search(self, name, args=None, operator='ilike', limit=80):
    #    """
    #    Returns a list of tupples containing id, name, as internally it is called {def name_get}
    #    result format: {[(id, name), (id, name), ...]}
    #    """
    #    args = args or []
    #    if operator in expression.NEGATIVE_TERM_OPERATORS:
    #        domain = [('description', operator, name), ('name', operator, name)]
    #    else:
    #        domain = ['|', ('description', operator, name), ('name', operator, name)]
    #    taxes = self.search(expression.AND([domain, args]), limit=limit)
    #    return taxes.name_get()

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        context = dict(self._context or {})

        if context.get('type'):
            if context.get('type') in ('out_invoice', 'out_refund'):
                args += [('type_tax_use', '=', 'sale')]
            elif context.get('type') in ('in_invoice', 'in_refund'):
                args += [('type_tax_use', '=', 'purchase')]

        if context.get('journal_id'):
            journal = self.env['account.journal'].browse(context.get('journal_id'))
            if journal.type in ('sale', 'purchase'):
                args += [('type_tax_use', '=', journal.type)]

        return super(account_tax, self).search(args, offset, limit, order, count=count)

    #@api.multi
    #@api.depends('name', 'description')
    #def name_get(self):
    #    res = []
    #    for record in self:
    #        name = record.description and record.description or record.name
    #        res.append((record.id, name))
    #    return res

    @api.onchange('amount')
    def onchange_amount(self):
        if not self.description and self.amount_type in ('percent', 'division') and self.amount != 0.0:
            self.description = "{0:.4g} %".format(self.amount)

    @api.onchange('account_id')
    def onchange_account_id(self):
        self.refund_account_id = self.account_id

    @api.onchange('price_include')
    def onchange_price_include(self):
        if self.price_include == True:
            self.include_base_amount = True

    @api.multi
    def normalized_set(self):
        """ Returns a recordset where groups are replaced by their children and each tax appears only once sorted by default sort order (sequence).
            NB : It might make more sense to first filter out first-level taxes that appear in groups. """
        return self.mapped(lambda r: r.amount_type == 'group' and r.children_tax_ids or r).sorted()

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
            currency = self.company_id.currency_id
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

            if tax.amount_type == 'fixed':
                tax_amount = tax.amount
            elif (tax.amount_type == 'percent' and not tax.price_include) or (tax.amount_type == 'division' and tax.price_include):
                tax_amount = base * tax.amount / 100
            elif tax.amount_type == 'percent' and tax.price_include:
                tax_amount = base - (base / (1 + tax.amount / 100))
            elif tax.amount_type == 'division' and not tax.price_include:
                tax_amount = base / (1 - tax.amount / 100) - base
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

class account_account_template(models.Model):
    _name = "account.account.template"
    _description ='Templates for Accounts'
    _order = "code"

    name = fields.Char(string='Name', required=True, index=True)
    currency_id = fields.Many2one('res.currency', string='Secondary Currency', help="Forces all moves for this account to have this secondary currency.")
    code = fields.Char(string='Code', size=64, required=True, index=True)
    user_type = fields.Many2one('account.account.type', string='Type', required=True,
        help="These types are defined according to your country. The type contains more information "\
        "about the account and its specificities.")
    reconcile = fields.Boolean(string='Allow Reconciliation', default=False,
        help="Check this option if you want the user to reconcile entries in this account.")
    note = fields.Text(string='Note')
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

    @api.model
    def generate_account(self, chart_template_id, tax_template_ref, acc_template_ref, code_digits, company_id):
        """
        This method for generating accounts from templates.

        :param chart_template_id: id of the chart template chosen in the wizard
        :param tax_template_ref: Taxes templates reference for write taxes_id in account_account.
        :paramacc_template_ref: dictionary with the mappping between the account templates and the real accounts.
        :param code_digits: number of digits got from wizard.multi.charts.accounts, this is use for account code.
        :param company_id: company_id selected from wizard.multi.charts.accounts.
        :returns: return acc_template_ref for reference purpose.
        :rtype: dict
        """

        company_name = self.env['res.company'].browse(company_id).name
        template = self.env['account.chart.template'].browse(chart_template_id)
        acc_template = self.search([('nocreate', '!=', True), '|', ('chart_template_id', '=', chart_template_id), ('chart_template_id', '=', False)], order='id')
        for account_template in acc_template:
            tax_ids = []
            for tax in account_template.tax_ids:
                tax_ids.append(tax_template_ref[tax.id])

            code_main = account_template.code and len(account_template.code) or 0
            code_acc = account_template.code or ''
            if code_main > 0 and code_main <= code_digits:
                code_acc = str(code_acc) + (str('0'*(code_digits-code_main)))
            vals={
                'name': company_name or account_template.name,
                'currency_id': account_template.currency_id and account_template.currency_id.id or False,
                'code': code_acc,
                'user_type': account_template.user_type and account_template.user_type.id or False,
                'reconcile': account_template.reconcile,
                'note': account_template.note,
                'tax_ids': [(6,0,tax_ids)],
                'company_id': company_id,
            }
            new_account = self.env['account.account'].create(vals)
            acc_template_ref[account_template.id] = new_account.id

        return acc_template_ref


class account_add_tmpl_wizard(models.TransientModel):
    """Add one more account from the template.

    With the 'nocreate' option, some accounts may not be created. Use this to add them later."""
    _name = 'account.addtmpl.wizard'

    @api.model
    def _get_def_cparent(self):
        context = dict(self._context or {})
        tmpl_obj = self.env['account.account.template']

        tids = tmpl_obj.read([context['tmpl_ids']], ['parent_id'])
        if not tids or not tids[0]['parent_id']:
            return False
        ptids = tmpl_obj.read([tids[0]['parent_id'][0]], ['code'])
        account = False
        if not ptids or not ptids[0]['code']:
            raise Warning(_('There is no parent code for the template account.'))
            account = self.env['account.account'].search([('code', '=', ptids[0]['code'])], limit=1)
        return account

    cparent_id = fields.Many2one('account.account', string='Parent target', default=lambda self: self._get_def_cparent(),
        help="Creates an account with the selected template under this existing parent.", required=True, domain=[('deprecated', '=', False)])

    @api.multi
    def action_create(self):
        context = dict(self._context or {})
        AccountObj = self.env['account.account']
        data = self.read()[0]
        company_id = AccountObj.read([data['cparent_id'][0]], ['company_id'])[0]['company_id'][0]
        account_template = self.env['account.account.template'].browse(context['tmpl_ids'])
        vals = {
            'name': account_template.name,
            'currency_id': account_template.currency_id and account_template.currency_id.id or False,
            'code': account_template.code,
            'type': account_template.type,
            'user_type': account_template.user_type and account_template.user_type.id or False,
            'reconcile': account_template.reconcile,
            'note': account_template.note,
            'parent_id': data['cparent_id'][0],
            'company_id': company_id,
            }
        AccountObj.create(vals)
        return {'type':'state', 'state': 'end' }

    @api.multi
    def action_cancel(self):
        return { 'type': 'state', 'state': 'end' }


class account_chart_template(models.Model):
    _name="account.chart.template"
    _description= "Templates for Account Chart"

    name = fields.Char(string='Name', required=True)
    company_id = fields.Many2one('res.company', string='Root Tax Code')
    parent_id = fields.Many2one('account.chart.template', string='Parent Chart Template')
    code_digits = fields.Integer(string='# of Digits', required=True, default=6, help="No. of Digits to use for account code")
    visible = fields.Boolean(string='Can be Visible?', default=True,
        help="Set this to False if you don't want this template to be used actively in the wizard that generate Chart of Accounts from "
            "templates, this is useful when you want to generate accounts of this template only when loading its child template.")
    currency_id = fields.Many2one('res.currency', string='Currency')
    complete_tax_set = fields.Boolean(string='Complete Set of Taxes', default=True,
        help="This boolean helps you to choose if you want to propose to the user to encode the sale and purchase rates or choose from list "
            "of taxes. This last choice assumes that the set of tax defined on this template is complete")
    account_root_id = fields.Many2one('account.account.template', string='Root Account')
    tax_template_ids = fields.One2many('account.tax.template', 'chart_template_id', string='Tax Template List',
        help='List of all the taxes that have to be installed by the wizard')
    bank_account_view_id = fields.Many2one('account.account.template', string='Bank Account')
    property_account_receivable = fields.Many2one('account.account.template', string='Receivable Account')
    property_account_payable = fields.Many2one('account.account.template', string='Payable Account')
    property_account_expense_categ = fields.Many2one('account.account.template', string='Expense Category Account')
    property_account_income_categ = fields.Many2one('account.account.template', string='Income Category Account')
    property_account_expense = fields.Many2one('account.account.template', string='Expense Account on Product Template')
    property_account_income = fields.Many2one('account.account.template', string='Income Account on Product Template')
    property_account_income_opening = fields.Many2one('account.account.template', string='Opening Entries Income Account')
    property_account_expense_opening = fields.Many2one('account.account.template', string='Opening Entries Expense Account')


class account_tax_template(models.Model):
    _name = 'account.tax.template'
    _description = 'Templates for Taxes'
    _order = 'id'

    chart_template_id = fields.Many2one('account.chart.template', string='Chart Template', required=True)
    name = fields.Char(string='Tax Name', required=True, translate=True)
    type_tax_use = fields.Selection([('sale', 'Sales'), ('purchase', 'Purchases'), ('as_child', 'Only in Tax Group')], string='Tax Scope', required=True, default="sale",
        help="Determines where the tax is selectable. Choose 'Only in Tax Group' if it shouldn't be used outside a group of tax.")
    amount_type = fields.Selection(default='percent', string="Tax Computation", required=True,
        selection=[('group', 'Group of Taxes'), ('fixed', 'Fixed'), ('percent', 'Percentage of Price'), ('division', 'Percentage of Price Tax Included')])
    active = fields.Boolean(default=True,
        help="Set active to false to hide the tax without removing it.")
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)

    children_tax_ids = fields.Many2many('account.tax', 'account_tax_filiation_rel', 'parent_tax', 'child_tax', string='Children Taxes')

    sequence = fields.Integer(required=True, default=1,
        help="The sequence field is used to define order in which the tax lines are applied.")
    amount = fields.Float(required=True, digits=(16, 3))
    account_id = fields.Many2one('account.account', domain=[('deprecated', '=', False)], string='Tax Account',
        help="Account that will be set on invoice tax lines for invoices or refund. Leave empty to use the expense account.")
    refund_account_id = fields.Many2one('account.account', domain=[('deprecated', '=', False)], string='Tax Account on Refunds',
        help="Account that will be set on invoice tax lines for invoices or refund. Leave empty to use the expense account.")
    description = fields.Char(string='Display on Invoices')
    price_include = fields.Boolean(string='Included in Price', default=False,
        help="Check this if the price you use on the product and invoices includes this tax.")
    include_base_amount = fields.Boolean(string='Affect subsequent taxes', default=False,
        help="If set, taxes which are computed after this one will be computed based on the price tax included.")
    analytic_cost = fields.Boolean(string="Analytic Cost")

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
    def _generate_tax(self, company_id):
        """
        This method generate taxes from templates.

        :param company_id: id of the company the wizard is running for
        :returns:
            {
            'tax_template_to_tax': mapping between tax template and the newly generated taxes corresponding,
            'account_dict': dictionary containing a to-do list with all the accounts to assign on new taxes
            }
        """
        res = {}
        todo_dict = {}
        tax_template_to_tax = {}
        for tax in self:
            vals_tax = {
                'name': tax.name,
                'type_tax_use': tax.type_tax_use,
                'amount_type': tax.amount_type,
                'active': tax.active,
                'company_id': tax.company_id,
                'children_tax_ids': tax.children_tax_ids,
                'sequence': tax.sequence,
                'amount': tax.amount,
                'description': tax.description,
                'price_include': tax.price_include,
                'include_base_amount': tax.include_base_amount,
                'analytic_cost': tax.analytic_cost,
            }
            new_tax = self.env['account.tax'].create(vals_tax)
            tax_template_to_tax[tax.id] = new_tax.id
            # Since the accounts have not been created yet, we have to wait before filling these fields
            todo_dict[new_tax.id] = {
                'account_id': tax.account_id,
                'refund_account_id': tax.refund_account_id,
            }
        res.update({'tax_template_to_tax': tax_template_to_tax, 'account_dict': todo_dict})
        return res


# Fiscal Position Templates

class account_fiscal_position_template(models.Model):
    _name = 'account.fiscal.position.template'
    _description = 'Template for Fiscal Position'

    name = fields.Char(string='Fiscal Position Template', required=True)
    chart_template_id = fields.Many2one('account.chart.template', string='Chart Template', required=True)
    account_ids = fields.One2many('account.fiscal.position.account.template', 'position_id', string='Account Mapping')
    tax_ids = fields.One2many('account.fiscal.position.tax.template', 'position_id', string='Tax Mapping')
    note = fields.Text(string='Notes')

    @api.model
    def generate_fiscal_position(self, chart_temp_id, tax_template_ref, acc_template_ref, company_id):
        """
        This method generate Fiscal Position, Fiscal Position Accounts and Fiscal Position Taxes from templates.

        :param chart_temp_id: Chart Template Id.
        :param taxes_ids: Taxes templates reference for generating account.fiscal.position.tax.
        :param acc_template_ref: Account templates reference for generating account.fiscal.position.account.
        :param company_id: company_id selected from wizard.multi.charts.accounts.
        :returns: True
        """
        positions = self.search([('chart_template_id', '=', chart_temp_id)])
        for position in positions:
            new_fp = self.env['account.fiscal.position'].create({'company_id': company_id, 'name': position.name, 'note': position.note})
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


class account_fiscal_position_tax_template(models.Model):
    _name = 'account.fiscal.position.tax.template'
    _description = 'Template Tax Fiscal Position'
    _rec_name = 'position_id'

    position_id = fields.Many2one('account.fiscal.position.template', string='Fiscal Position', required=True, ondelete='cascade')
    tax_src_id = fields.Many2one('account.tax.template', string='Tax Source', required=True)
    tax_dest_id = fields.Many2one('account.tax.template', string='Replacement Tax')


class account_fiscal_position_account_template(models.Model):
    _name = 'account.fiscal.position.account.template'
    _description = 'Template Account Fiscal Mapping'
    _rec_name = 'position_id'

    position_id = fields.Many2one('account.fiscal.position.template', string='Fiscal Mapping', required=True, ondelete='cascade')
    account_src_id = fields.Many2one('account.account.template', string='Account Source', required=True)
    account_dest_id = fields.Many2one('account.account.template', string='Account Destination', required=True)


# ---------------------------------------------------------
# Account generation from template wizards
# ---------------------------------------------------------
class wizard_multi_charts_accounts(models.TransientModel):
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

    _name='wizard.multi.charts.accounts'
    _inherit = 'res.config'

    company_id = fields.Many2one('res.company', string='Company', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', help="Currency as per company's country.")
    only_one_chart_template = fields.Boolean(string='Only One Chart Template Available')
    chart_template_id = fields.Many2one('account.chart.template', string='Chart Template', required=True)
    bank_accounts_id = fields.One2many('account.bank.accounts.wizard', 'bank_account_id', string='Cash and Banks', required=True)
    code_digits = fields.Integer(string='# of Digits', required=True, help="No. of Digits to use for account code")
    sale_tax = fields.Many2one('account.tax.template', string='Default Sale Tax')
    purchase_tax = fields.Many2one('account.tax.template', string='Default Purchase Tax')
    sale_tax_rate = fields.Float(string='Sales Tax(%)')
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
        res['value'] = {'complete_tax_set': False, 'sale_tax': False, 'purchase_tax': False}
        if self.chart_template_id:
            currency_id = self.chart_template_id.currency_id and self.chart_template_id.currency_id.id or self.env.user.company_id.currency_id.id
            res['value'].update({'complete_tax_set': self.chart_template_id.complete_tax_set, 'currency_id': currency_id})
            if self.chart_template_id.complete_tax_set:
            # default tax is given by the lowest sequence. For same sequence we will take the latest created as it will be the case for tax created while isntalling the generic chart of account
                chart_ids = self._get_chart_parent_ids(self.chart_template_id)
                base_tax_domain = [('chart_template_id', 'in', chart_ids), ('parent_id', '=', False)]
                sale_tax_domain = base_tax_domain + [('type_tax_use', '=', 'sale')]
                purchase_tax_domain = base_tax_domain + [('type_tax_use', '=', 'purchase')]
                sale_taxes = tax_templ_obj.search(sale_tax_domain, order="sequence, id desc", limit=1)
                purchase_taxes = tax_templ_obj.search(purchase_tax_domain, order="sequence, id desc", limit=1)
                res['value']['sale_tax'] = sale_taxes.ids and sale_taxes.ids[0] or False
                res['value']['purchase_tax'] = purchase_taxes.ids and purchase_taxes.ids[0] or False
                res.setdefault('domain', {})
                res['domain']['sale_tax'] = repr(sale_tax_domain)
                res['domain']['purchase_tax'] = repr(purchase_tax_domain)
            if self.chart_template_id.code_digits:
               res['value']['code_digits'] = self.chart_template_id.code_digits
        return res

    @api.model
    def default_get(self, fields):
        context = dict(self._context or {})
        res = super(wizard_multi_charts_accounts, self).default_get(fields)
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
        context = dict(self._context or {})
        res = super(wizard_multi_charts_accounts, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=False)
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

    @api.model
    def check_created_journals(self, vals_journal, company_id):
        """
        This method used for checking journals already created or not. If not then create new journal.
        """
        JournalObj = self.env['account.journal']
        rec_list = JournalObj.search([('name', '=', vals_journal['name']), ('company_id', '=', company_id)], limit=1)
        if not rec_list:
            JournalObj.create(vals_journal)
        return True

    @api.model
    def generate_journals(self, chart_template_id, acc_template_ref, company_id):
        """
        This method is used for creating journals.

        :param chart_temp_id: Chart Template Id.
        :param acc_template_ref: Account templates reference.
        :param company_id: company_id selected from wizard.multi.charts.accounts.
        :returns: True
        """
        journal_data = self._prepare_all_journals(chart_template_id, acc_template_ref, company_id)
        for vals_journal in journal_data:
            self.check_created_journals(vals_journal, company_id)
        return True

    @api.model
    def _prepare_all_journals(self, chart_template_id, acc_template_ref, company_id):
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
                default_account = acc_template_ref.get(template.property_account_income_categ.id)
            elif journal_type == 'purchase':
                default_account = acc_template_ref.get(template.property_account_expense_categ.id)
            elif journal_type == 'situation':
                if type == 'debit':
                    default_account = acc_template_ref.get(template.property_account_expense_opening.id)
                else:
                    default_account = acc_template_ref.get(template.property_account_income_opening.id)
            return default_account

        journal_names = {
            'sale': _('Sales Journal'),
            'purchase': _('Purchase Journal'),
            'general': _('Miscellaneous Journal'),
            'situation': _('Opening Entries Journal'),
        }
        journal_codes = {
            'sale': _('SAJ'),
            'purchase': _('EXJ'),
            'general': _('MISC'),
            'situation': _('OPEJ'),
        }

        template = self.env['account.chart.template'].browse(chart_template_id)

        journal_data = []
        for journal_type in ['sale', 'purchase', 'general', 'situation']:
            vals = {
                'type': journal_type,
                'name': journal_names[journal_type],
                'code': journal_codes[journal_type],
                'company_id': company_id,
                'analytic_journal_id': _get_analytic_journal(journal_type),
                'default_credit_account_id': _get_default_account(journal_type, 'credit'),
                'default_debit_account_id': _get_default_account(journal_type, 'debit'),
                'refund_sequence': True,
            }
            journal_data.append(vals)
        return journal_data

    @api.model
    def generate_properties(self, chart_template_id, acc_template_ref, company_id):
        """
        This method used for creating properties.

        :param chart_template_id: id of the current chart template for which we need to create properties
        :param acc_template_ref: Mapping between ids of account templates and real accounts created from them
        :param company_id: company_id selected from wizard.multi.charts.accounts.
        :returns: True
        """
        PropertyObj = self.env['ir.property']
        todo_list = [
            ('property_account_receivable', 'res.partner','account.account'),
            ('property_account_payable', 'res.partner','account.account'),
            ('property_account_expense_categ', 'product.category','account.account'),
            ('property_account_income_categ', 'product.category','account.account'),
            ('property_account_expense', 'product.template','account.account'),
            ('property_account_income', 'product.template','account.account'),
        ]
        template = self.env['account.chart.template'].browse(chart_template_id)
        for record in todo_list:
            account = getattr(template, record[0])
            value = account and 'account.account,' + str(acc_template_ref[account.id]) or False
            if value:
                field = self.env['ir.model.fields'].search([('name', '=', record[0]), ('model', '=', record[1]), ('relation', '=', record[2])], limit=1)
                vals = {
                    'name': record[0],
                    'company_id': company_id,
                    'fields_id': field.id,
                    'value': value,
                }
                property_ids = PropertyObj.search([('name','=', record[0]), ('company_id', '=', company_id)])
                if property_ids:
                    #the property exist: modify it
                    property_ids.write(vals)
                else:
                    #create the property
                    PropertyObj.create(vals)
        return True

    @api.model
    def _install_template(self, template_id, company_id, code_digits=None, obj_wizard=None, acc_ref=None, taxes_ref=None):
        '''
        This function recursively loads the template objects and create the real objects from them.

        :param template_id: id of the chart template to load
        :param company_id: id of the company the wizard is running for
        :param code_digits: integer that depicts the number of digits the accounts code should have in the COA
        :param obj_wizard: the current wizard for generating the COA from the templates
        :param acc_ref: Mapping between ids of account templates and real accounts created from them
        :param taxes_ref: Mapping between ids of tax templates and real taxes created from them
        :returns: return a tuple with a dictionary containing
            * the mapping between the account template ids and the ids of the real accounts that have been generated
              from them, as first item,
            * a similar dictionary for mapping the tax templates and taxes, as second item,
        :rtype: tuple(dict, dict, dict)
        '''
        if acc_ref is None:
            acc_ref = {}
        if taxes_ref is None:
            taxes_ref = {}
        template = self.env['account.chart.template'].browse(template_id)
        if template.parent_id:
            tmp1, tmp2 = self._install_template(template.parent_id.id, company_id, code_digits=code_digits, acc_ref=acc_ref, taxes_ref=taxes_ref)
            acc_ref.update(tmp1)
            taxes_ref.update(tmp2)
        tmp1, tmp2, tmp3 = self._load_template(template_id, company_id, code_digits=code_digits, obj_wizard=obj_wizard, account_ref=acc_ref, taxes_ref=taxes_ref)
        acc_ref.update(tmp1)
        taxes_ref.update(tmp2)
        return acc_ref, taxes_ref

    @api.model
    def _load_template(self, template_id, company_id, code_digits=None, obj_wizard=None, account_ref=None, taxes_ref=None):
        '''
        This function generates all the objects from the templates

        :param template_id: id of the chart template to load
        :param company_id: id of the company the wizard is running for
        :param code_digits: integer that depicts the number of digits the accounts code should have in the COA
        :param obj_wizard: the current wizard for generating the COA from the templates
        :param acc_ref: Mapping between ids of account templates and real accounts created from them
        :param taxes_ref: Mapping between ids of tax templates and real taxes created from them
        :returns: return a tuple with a dictionary containing
            * the mapping between the account template ids and the ids of the real accounts that have been generated
              from them, as first item,
            * a similar dictionary for mapping the tax templates and taxes, as second item,
        :rtype: tuple(dict, dict, dict)
        '''
        if account_ref is None:
            account_ref = {}
        if taxes_ref is None:
            taxes_ref = {}
        template = self.env['account.chart.template'].browse(template_id)
        AccountTaxObj = self.env['account.tax']

        # Generate taxes from templates.
        generated_tax_res = template.tax_template_ids._generate_tax(company_id)
        taxes_ref.update(generated_tax_res['tax_template_to_tax'])

        # Generating Accounts from templates.
        account_template_ref = self.env['account.account.template'].generate_account(template_id, taxes_ref, account_ref, code_digits, company_id)
        account_ref.update(account_template_ref)

        # writing account values on tax after creation of accounts
        for key, value in generated_tax_res['account_dict'].items():
            if value['account_collected_id'] or value['account_paid_id']:
                AccountTaxObj.browse(key).write({
                    'account_collected_id': account_ref.get(value['account_collected_id'], False),
                    'account_paid_id': account_ref.get(value['account_paid_id'], False),
                })

        # Create Journals
        self.generate_journals(template_id, account_ref, company_id)

        # generate properties function
        self.generate_properties(template_id, account_ref, company_id)

        # Generate Fiscal Position , Fiscal Position Accounts and Fiscal Position Taxes from templates
        self.env['account.fiscal.position.template'].generate_fiscal_position(template_id, taxes_ref, account_ref, company_id)

        return account_ref, taxes_ref

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
            ref_tax_ids = obj_tax_temp.search([('type_tax_use','=','sale'), ('chart_template_id', 'in', all_parents)], order="sequence, id desc", limit=1)
            ref_tax_ids.write({'amount': value/100.0, 'name': _('Tax %.2f%%') % value})
            value = self.purchase_tax_rate
            ref_tax_ids = obj_tax_temp.search([('type_tax_use','=','purchase'), ('chart_template_id', 'in', all_parents)], order="sequence, id desc", limit=1)
            ref_tax_ids.write({'amount': value/100.0, 'name': _('Purchase Tax %.2f%%') % value})
        return True

    @api.multi
    def execute(self):
        '''
        This function is called at the confirmation of the wizard to generate the COA from the templates. It will read
        all the provided information to create the accounts, the banks, the journals, the taxes, the
        accounting properties... accordingly for the chosen company.
        '''
        if self._uid != SUPERUSER_ID and not self.env.user.has_group('base.group_erp_manager'):
            raise openerp.exceptions.AccessError(_("Only administrators can change the settings"))
        ir_values_obj = self.env['ir.values']
        company_id = self.company_id.id

        self.company_id.write({'currency_id': self.currency_id.id})
        self.company_id.write({'accounts_code_digits': self.code_digits})

        # When we install the CoA of first company, set the currency to price types and pricelists
        if company_id==1:
            for reference in ['product.list_price', 'product.standard_price', 'product.list0', 'purchase.list0']:
                try:
                    tmp2 = self.env.ref(reference).write({'currency_id': self.currency_id.id})
                except ValueError:
                    pass

        # If the floats for sale/purchase rates have been filled, create templates from them
        self._create_tax_templates_from_rates(company_id)

        # Install all the templates objects and generate the real objects
        acc_template_ref, taxes_ref = self._install_template(self.chart_template_id.id, company_id, code_digits=self.code_digits, obj_wizard=self)

        # write values of default taxes for product as super user
        if self.sale_tax and taxes_ref:
            ir_values_obj.sudo().set_default('product.template', "taxes_id", [taxes_ref[self.sale_tax.id]], for_all_users=True, company_id=company_id)
        if self.purchase_tax and taxes_ref:
            ir_values_obj.sudo().set_default('product.template', "supplier_taxes_id", [taxes_ref[self.purchase_tax.id]], for_all_users=True, company_id=company_id)

        # Create Bank journals
        self._create_bank_journals_from_o2m(company_id, acc_template_ref)
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
            Journals = self.env['account.journal'].search([('code', '=', journal_code), ('company_id', '=', company.id)], limit=1)
            if not Journals:
                break
        else:
            raise Warning(_('Cannot generate an unused journal code.'))

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
        available_digits = abs(code_digits - len(bank_account_code_char))
        for num in xrange(1, pow(10, available_digits)):
            new_code = str(bank_account_code_char.ljust(code_digits-len(str(num)), '0')) + str(num)
            recs = self.env['account.account'].search([('code', '=', new_code), ('company_id', '=', company.id)])
            if not recs:
                break
        else:
            raise Warning(_('Error!'), _('Cannot generate an unused account code.'))

        # Get the id of the user types fr-or cash and bank
        cash_type = self.env.ref('account.data_account_type_cash') or False
        bank_type = self.env.ref('account.data_account_type_bank') or False
        return {
                'name': line['acc_name'],
                'currency_id': line['currency_id'] or False,
                'code': new_code,
                'type': 'liquidity',
                'user_type': line['account_type'] == 'cash' and cash_type.id or bank_type.id,
                'company_id': company.id,
        }

    @api.one
    def _create_bank_journals_from_o2m(self, company_id, acc_template_ref):
        '''
        This function creates bank journals and its accounts for each line encoded in the field bank_accounts_id of the
        wizard.

        :param company_id: the id of the company for which the wizard is running.
        :param acc_template_ref: the dictionary containing the mapping between the ids of account templates and the ids
            of the accounts that have been generated from them.
        :return: True
        '''
        company = self.env['res.company'].browse(company_id)

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
        ref_acc_bank = self.chart_template_id.bank_account_view_id
        if journal_data and not ref_acc_bank.code:
            raise Warning(_('You have to set a code for the bank account defined on the selected chart of accounts.'))
        company.write({'bank_account_code_char': ref_acc_bank.code})

        for line in journal_data:
            # Create the default debit/credit accounts for this bank journal
            vals = self._prepare_bank_account(company, line, acc_template_ref, ref_acc_bank)
            default_account  = self.env['account.account'].create(vals)

            #create the bank journal
            vals_journal = self._prepare_bank_journal(company, line, default_account.id)
            self.env['account.journal'].create(vals_journal)
        return True


class account_bank_accounts_wizard(models.TransientModel):
    _name='account.bank.accounts.wizard'

    acc_name = fields.Char(string='Account Name.', required=True)
    bank_account_id = fields.Many2one('wizard.multi.charts.accounts', string='Bank Account', required=True, ondelete='cascade')
    currency_id = fields.Many2one('res.currency', string='Secondary Currency',
        help="Forces all moves for this account to have this secondary currency.")
    account_type = fields.Selection([('cash', 'Cash'), ('check', 'Check'), ('bank', 'Bank')], string='Account Type')


class account_operation_template(models.Model):
    _name = "account.operation.template"
    _description = "Preset to create journal entries during a reconciliation"

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
        ], string='Amount type', required=True, default='percentage')
    amount = fields.Float(digits=0, required=True, default=100.0, help="Fixed amount will count as a debit if it is negative, as a credit if it is positive.")
    tax_id = fields.Many2one('account.tax', string='Tax', ondelete='restrict', domain=[('type_tax_use','=','purchase')])
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', ondelete='set null', domain=[('state','not in',('close','cancelled'))])

    second_account_id = fields.Many2one('account.account', string='Account', ondelete='cascade', domain=[('deprecated', '=', False), ('internal_type','!=','consolidation')])
    second_journal_id = fields.Many2one('account.journal', string='Journal', ondelete='cascade', help="This field is ignored in a bank statement reconciliation.")
    second_label = fields.Char(string='Journal Item Label')
    second_amount_type = fields.Selection([
        ('fixed', 'Fixed'),
        ('percentage', 'Percentage of amount')
        ], string='Amount type', required=True, default='percentage')
    second_amount = fields.Float(string='Amount', digits=0, required=True, default=100.0, help="Fixed amount will count as a debit if it is negative, as a credit if it is positive.")
    second_tax_id = fields.Many2one('account.tax', string='Tax', ondelete='restrict', domain=[('type_tax_use','=','purchase')])
    second_analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', ondelete='set null', domain=[('state','not in',('close','cancelled'))])
