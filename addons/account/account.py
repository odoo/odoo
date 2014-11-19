# -*- coding: utf-8 -*-

import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time

import openerp
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.osv import expression
from openerp.tools.float_utils import float_round as round
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT

import openerp.addons.decimal_precision as dp

from openerp import models, fields, api, _
from openerp.exceptions import Warning, RedirectWarning

_logger = logging.getLogger(__name__)

class res_company(models.Model):
    _inherit = "res.company"

    income_currency_exchange_account_id = fields.Many2one('account.account',
        string="Gain Exchange Rate Account", domain=[('type', '=', 'other'), ('deprecated', '=', False)])
    expense_currency_exchange_account_id = fields.Many2one('account.account',
        string="Loss Exchange Rate Account", domain=[('type', '=', 'other'), ('deprecated', '=', False)])


class account_payment_term(models.Model):
    _name = "account.payment.term"
    _description = "Payment Term"
    _order = "name"

    name = fields.Char(string='Payment Term', translate=True, required=True)
    active = fields.Boolean(string='Active', default=True,
        help="If the active field is set to False, it will allow you to hide the payment term without removing it.")
    note = fields.Text(string='Description', translate=True)
    line_ids = fields.One2many('account.payment.term.line', 'payment_id', string='Terms', copy=True)

    @api.one
    def compute(self, value, date_ref=False):
        date_ref = date_ref or datetime.now().strftime('%Y-%m-%d')
        amount = value
        result = []
        prec = self.env['decimal.precision'].precision_get('Account')
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
                    next_first_date = next_date + relativedelta(day=1, months=1) #Getting 1st of next month
                    next_date = next_first_date + relativedelta(days=line.days2)
                if line.days2 > 0:
                    next_date += relativedelta(day=line.days2, months=1)
                result.append( (next_date.strftime('%Y-%m-%d'), amt) )
                amount -= amt

        amount = reduce(lambda x,y: x+y[1], result, 0.0)
        dist = round(value-amount, prec)
        if dist:
            last_date = result and result[-1][0] or time.strftime('%Y-%m-%d')
            result.append( (last_date, dist) )
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
        help="""Select here the kind of valuation related to this payment term line. Note that you should have your last line with the type 'Balance' to ensure that the whole amount will be treated.""")
    value_amount = fields.Float(string='Amount To Pay', digits=dp.get_precision('Payment Term'), help="For percent enter a ratio between 0-100.")
    days = fields.Integer(string='Number of Days', required=True, default=30, help="Number of days to add before computation of the day of month." \
        "If Date=15/01, Number of Days=22, Day of Month=-1, then the due date is 28/02.")
    days2 = fields.Integer(string='Day of the Month', required=True, default='0',
        help="Day of the month, set -1 for the last day of the current month. If it's positive, it gives the day of the next month. Set 0 for net days (otherwise it's based on the beginning of the month).")
    payment_id = fields.Many2one('account.payment.term', string='Payment Term', required=True, index=True, ondelete='cascade')

    @api.one
    @api.constrains('value', 'value_amount')
    def _check_percent(self):
        if self.value == 'percent' and (self.value_amount < 0.0 or self.value_amount > 100.0):
            raise Warning(_('Percentages for Payment Term Line must be between 0 and 100.'))


class account_account_type(models.Model):
    _name = "account.account.type"
    _description = "Account Type"
    _order = "code"

    name = fields.Char(string='Account Type', required=True, translate=True)
    code = fields.Char(string='Code', size=32, required=True, index=True)
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
                args.append(('user_type', 'in',  map(lambda x: x.id, jour.type_control_ids)))
        return super(account_account, self).search(args, offset, limit, order, count=count)

    @api.multi
    def _get_children_and_consol(self):
        #this function search for all the consolidated children (recursively) of the given account ids
        ids3 = []
        for rec in self:
            ids3 = [child.id for child in rec.child_consol_ids]
        if ids3:
            ids3 = self._get_children_and_consol(ids3)
        return ids3

    @api.multi
    def _compute(self, query='', query_params=()):
        """ compute the balance, debit and/or credit for the provided
        Arguments:
        `query`: additional query filter (as a string)
        `query_params`: parameters for the provided query string
                        (__compute will handle their escaping) as a
                        tuple
        """
        field_names = ['balance', 'credit', 'debit', 'foreign_balance', 'adjusted_balance', 'unrealized_gain_loss']
        mapping = {
            'balance': "COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) as balance",
            'debit': "COALESCE(SUM(l.debit), 0) as debit",
            'credit': "COALESCE(SUM(l.credit), 0) as credit",
            # by convention, foreign_balance is 0 when the account has no secondary currency, because the amounts may be in different currencies
            'foreign_balance': "(SELECT CASE WHEN currency_id IS NULL THEN 0 ELSE COALESCE(SUM(l.amount_currency), 0) END FROM account_account WHERE id IN (l.account_id)) as foreign_balance",
        }
        #get all the necessary accounts
        children_and_consolidated = self._get_children_and_consol()
        #compute for each account the balance/debit/credit from the move lines
        accounts = {}
        res = {}
        for account in self:
            account.balance = 0.0
            account.credit = 0.0
            account.debit = 0.0
            account.foreign_balance = 0.0
            account.adjusted_balance = 0.0
            account.unrealized_gain_loss = 0.0
        if children_and_consolidated:
            aml_query = self.env['account.move.line']._query_get()
 
            wheres = [""]
            if query.strip():
                wheres.append(query.strip())
            if aml_query.strip():
                wheres.append(aml_query.strip())
            filters = " AND ".join(wheres)
            # IN might not work ideally in case there are too many
            # children_and_consolidated, in that case join on a
            # values() e.g.:
            # SELECT l.account_id as id FROM account_move_line l
            # INNER JOIN (VALUES (id1), (id2), (id3), ...) AS tmp (id)
            # ON l.account_id = tmp.id
            # or make _get_children_and_consol return a query and join on that
            request = ("SELECT l.account_id as id, " +\
                       ', '.join(mapping.values()) +
                       " FROM account_move_line l" \
                       " WHERE l.account_id IN %s " \
                            + filters +
                       " GROUP BY l.account_id")
            params = (tuple(children_and_consolidated),) + query_params
            cr.execute(request, params)
 
            for row in cr.dictfetchall():
                accounts[row['id']] = row
 
            # consolidate accounts with direct children
            children_and_consolidated.reverse()
            brs = list(self.browse(children_and_consolidated))
            sums = {}
            while brs:
                current = brs.pop(0)
#                can_compute = True
#                for child in current.child_id:
#                    if child.id not in sums:
#                        can_compute = False
#                        try:
#                            brs.insert(0, brs.pop(brs.index(child)))
#                        except ValueError:
#                            brs.insert(0, child)
#                if can_compute:
                for fn in field_names:
                    sums.setdefault(current.id, {})[fn] = accounts.get(current.id, {}).get(fn, 0.0)
                    for child in current.child_id:
                        if child.company_id.currency_id.id == current.company_id.currency_id.id:
                            sums[current.id][fn] += sums[child.id][fn]
                        else:
                            sums[current.id][fn] += child.company_id.currency_id.compute(current.company_id.currency_id.id, sums[child.id][fn])
 
                # as we have to relay on values computed before this is calculated separately than previous fields
                if current.currency_id and current.exchange_rate and \
                            ('adjusted_balance' in field_names or 'unrealized_gain_loss' in field_names):
                    # Computing Adjusted Balance and Unrealized Gains and losses
                    # Adjusted Balance = Foreign Balance / Exchange Rate
                    # Unrealized Gains and losses = Adjusted Balance - Balance
                    adj_bal = sums[current.id].get('foreign_balance', 0.0) / current.exchange_rate
                    sums[current.id].update({'adjusted_balance': adj_bal, 'unrealized_gain_loss': adj_bal - sums[current.id].get('balance', 0.0)})
 
            for account in self:
                if sums.get(account.id):
                    account.balance = sums[account.id][balance]
                    account.credit = sums[account.id][credit]
                    account.debit = sums[account.id][debit]
                    account.foreign_balance = sums[account.id][foreign_balance]
                    account.adjusted_balance = sums[account.id][adjusted_balance]
                    account.unrealized_gain_loss = sums[account.id][unrealized_gain_loss]

    @api.one
    def _set_credit_debit(self, name, value):
        if self._context.get('config_invisible', True):
            return True

        journal = self.env['account.journal'].search([('type', '=', 'situation'), ('company_id', '=', self.company_id.id)], limit=1)
        if not journal:
            raise Warning(_("You need an Opening journal to set the initial balance."))

        move_obj = self.env['account.move.line']
        move = move_obj.search([
            ('journal_id', '=', journal.id),
            ('date', '=', time.strftime('%Y-%m-%d')),
            ('account_id', '=', self.id),
            (name,'>', 0.0),
            ('name','=', _('Opening Balance'))
        ])
        if move:
            move.write({name: value})
        else:
            if value < 0.0:
                raise Warning(_("Unable to adapt the initial balance (negative value)."))
            nameinv = (name == 'credit' and 'debit') or 'credit'
            move_id = move_obj.create({
                'name': _('Opening Balance'),
                'account_id': self.id,
                'journal_id': journal.id,
                name: value,
                nameinv: 0.0
            })
        return True

    @api.one
    def _set_credit(self):
        self._set_credit_debit('credit', self.credit)

    @api.one
    def _set_debit(self):
        self._set_credit_debit('debit', self.debit)

    @api.multi
    def _get_company_currency(self):
        for account in self:
            account.company_currency_id = (account.company_id.currency_id.id, account.company_id.currency_id.symbol)

    name = fields.Char(required=True, index=True)
    currency_id = fields.Many2one('res.currency', string='Secondary Currency',
        help="Forces all moves for this account to have this secondary currency.")
    code = fields.Char(size=64, required=True, index=True)
    deprecated = fields.Boolean(index=True, default=False)
    user_type = fields.Many2one('account.account.type', string='Type', required=True,
        help="Account Type is used for information purpose, to generate "\
        "country-specific legal reports, and set the rules to close a fiscal year and generate opening entries.")
    child_consol_ids = fields.Many2many('account.account', 'account_account_consol_rel', 'child_id', 'parent_id', string='Consolidated Children', domain=[('deprecated', '=', False)])
    balance = fields.Float(compute='_compute', digits=dp.get_precision('Account'))
    credit = fields.Float(compute='_compute', inverse='_set_credit', digits=dp.get_precision('Account'))
    debit = fields.Float(compute='_compute', inverse='_set_debit', digits=dp.get_precision('Account'))
    foreign_balance = fields.Float(compute='_compute', digits=dp.get_precision('Account'), string='Foreign Balance',
        help="Total amount (in Secondary currency) for transactions held in secondary currency for this account.")

    adjusted_balance = fields.Float(compute='_compute', digits=dp.get_precision('Account'), string='Adjusted Balance',
        help="Total amount (in Company currency) for transactions held in secondary currency for this account.")
    unrealized_gain_loss = fields.Float(compute='_compute', digits=dp.get_precision('Account'), string='Unrealized Gain or Loss',
        help="Value of Loss or Gain due to changes in exchange rate when doing multi-currency transactions.")
    exchange_rate = fields.Float(related='currency_id.rate', string='Exchange Rate', digits=(12,6))
    last_time_entries_checked = fields.Datetime(string='Latest Manual Reconciliation Date', readonly=True, copy=False,
        help='Last time the manual reconciliation was performed on this account. It is set either if there\'s not at least '\
        'an unreconciled debit and an unreconciled credit Or if you click the "Done" button.'),

    reconcile = fields.Boolean(string='Allow Reconciliation', default=False,
        help="Check this box if this account allows reconciliation of journal items.")
    tax_ids = fields.Many2many('account.tax', 'account_account_tax_default_rel',
        'account_id', 'tax_id', string='Default Taxes')
    note = fields.Text('Internal Notes')
    company_currency_id = fields.Many2one('res.currency', string='Company Currency', compute='_get_company_currency')
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
                domain = ['!'] + domain
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

    @api.one
    def has_something_to_reconcile(self):
        ''' at least a debit, a credit and a line older than the last reconciliation date of the account '''
        self.env.cr.execute('''
            SELECT l.account_id, SUM(l.debit) AS debit, SUM(l.credit) AS credit
            FROM account_move_line l
            RIGHT JOIN account_account a ON (a.id = l.account_id)
            WHERE a.reconcile IS TRUE
            AND a.id = %s
            AND l.reconcile_id IS NULL
            AND (a.last_time_entries_checked IS NULL OR l.date > a.last_time_entries_checked)
            AND l.state <> 'draft'
            GROUP BY l.account_id''', (self.id,))
        res = self.env.cr.dictfetchone()
        if res:
            return bool(res['debit'] and res['credit'])
        return False

    @api.multi
    def mark_as_reconciled(self):
        return self.write({'last_time_entries_checked': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})


class account_journal(models.Model):
    _name = "account.journal"
    _description = "Journal"
    _order = 'code'

    name = fields.Char(string='Journal Name', required=True)
    code = fields.Char(string='Code', size=5, required=True, help="The code will be displayed on reports.")
    type = fields.Selection([
            ('sale', 'Sale'),
            ('sale_refund','Sale Refund'),
            ('purchase', 'Purchase'),
            ('purchase_refund','Purchase Refund'),
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
    type_control_ids = fields.Many2many('account.account.type', 'account_journal_type_rel', 'journal_id', 'type_id', string='Type Controls',
        domain=[('code', '!=', 'view'), ('code', '!=', 'closed')])
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
    sequence_refund_id = fields.Many2one('ir.sequence', string='Refund Entry Sequence',
        help="This field contains the information related to the numbering of the refund entries of this journal.", copy=False)

    groups_id = fields.Many2many('res.groups', 'account_journal_group_rel', 'journal_id', 'group_id', string='Groups')
    currency = fields.Many2one('res.currency', string='Currency', help='The currency used to enter statement')
    entry_posted = fields.Boolean(string='Autopost Created Moves',
        help='Check this box to automatically post entries of this journal. Note that legally, some entries may be automatically posted when the source document is validated (Invoices), whatever the status of this field.')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=1, default=lambda self: self.env.user.company_id,
        help="Company related to this journal")

    analytic_journal_id = fields.Many2one('account.analytic.journal', string='Analytic Journal', help="Journal for analytic entries")

    # Fields related to bank or cash registers
    profit_account_id = fields.Many2one('account.account', string='Profit Account', domain=[('deprecated', '=', False)])
    loss_account_id = fields.Many2one('account.account', string='Loss Account', domain=[('deprecated', '=', False)])
    internal_account_id = fields.Many2one('account.account', string='Internal Transfers Account', index=True, domain=[('deprecated', '=', False)])
    cash_control = fields.Boolean(string='Cash Control', default=False,
        help='If you want the journal should be control at opening/closing, check this option')
    with_last_closing_balance = fields.Boolean(string='Opening With Last Closing Balance', default=True,
        help="For cash or bank journal, this option should be unchecked when the starting balance should always set to 0 for new documents.")

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
    def _create_sequence(self, vals, prefix=False):
        """ Create new no_gap entry sequence for every new Joural
        """
        prefix = prefix or vals['code'].upper()
        seq = {
            'name': vals['name'],
            'implementation':'no_gap',
            'prefix': prefix + "/%(year)s/",
            'padding': 4,
            'number_increment': 1
        }
        if 'company_id' in vals:
            seq['company_id'] = vals['company_id']
        return self.env['ir.sequence'].create(seq)

    @api.model
    def create(self, vals):
        if not vals.get('sequence_id', False):
            vals.update({'sequence_id': self.sudo()._create_sequence(vals).id})
        if type in ('sale','sale_refund','purchase','purchase_refund'):
            # If False, accepted has this field is not required
            if 'sequence_refund_id' not in vals:
                prefix = 'RF/'+vals.get('code', '')
                vals.update({'sequence_refund_id': self.sudo()._create_sequence(vals, prefix=prefix).id})
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
    amount = fields.Float(compute='_amount_compute', string='Amount', digits=dp.get_precision('Account'), store=True)
    narration = fields.Text(string='Internal Note')
    company_id = fields.Many2one('res.company', related='journal_id.company_id', string='Company', store=True, readonly=True,
        default=lambda self: self.env.user.company_id)

    # TODO: improve and use a refund sequence according to context
    @api.multi
    def post(self):
        SequenceObj = self.env['ir.sequence']
        invoice = self._context.get('invoice', False)
        self._post_validate()

        for move in self:
            move.line_id.state = 'valid'
            move.line_id.create_analytic_lines()
            if move.name =='/':
                new_name = False
                journal = move.journal_id

                if invoice and invoice.internal_number:
                    new_name = invoice.internal_number
                else:
                    if journal.sequence_id:
                        new_name = SequenceObj.next_by_id(journal.sequence_id.id)
                    else:
                        raise Warning(_('Please define a sequence on the journal.'))

                if new_name:
                    move.name = new_name

        self._cr.execute('UPDATE account_move '\
                   'SET state=%s '\
                   'WHERE id IN %s',
                   ('posted', tuple(valid_moves),))
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
        if ids:
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
            move_lines._update_check()
            move_lines.unlink()
        return super(account_move, self).unlink()

    # TODO: check if date is not closed, otherwise raise exception
    @api.multi
    def _post_validate(self):
        for move in self:
            amount = 0
            for line in move.line_id:
                amount += line.debit - line.credit
            if abs(amount) > 10 ** -4:
                raise Warning(_('You cannot validate a non-balanced entry.'))
            if not move.company_id.id == line.account_id.company_id.id:
                raise Warning(_("Cannot create moves for different companies."))
            if line.account_id.currency_id and line.currency_id:
                if line.account_id.currency_id.id != line.currency_id.id and (line.account_id.currency_id.id != line.account_id.company_id.currency_id.id):
                    raise Warning(_("""Cannot create move with currency different from ..""") % (line.account_id.code, line.account_id.name))
        return True

class account_move_reconcile(models.Model):
    _name = "account.move.reconcile"
    _description = "Account Reconciliation"

    name = fields.Char(string='Reconciliation Ref', required=True, default=lambda self: self.env['ir.sequence'].get('account.reconcile') or '/')
    line_id = fields.One2many('account.move.line', 'reconcile_id', string='Journal Items')

    @api.one
    @api.constrains('line_id')
    def _check_same_partner(self):
        first_partner = self.line_id and self.line_id[0].partner_id.id or False
        if any([(line.partner_id.id != first_partner) for line in move_lines]):
            raise Warning(_('You can only reconcile journal items with the same partner.'))


#----------------------------------------------------------
# Tax
#----------------------------------------------------------
"""
a documenter
child_depend: la taxe depend des taxes filles
"""
class account_tax_code(models.Model):
    """
    A code for the tax object.

    This code is used for some tax declarations.
    """
    @api.multi
    def _sum(self, name, where ='', where_params=()):
        parent_ids = tuple(self.search([('parent_id', 'child_of', self.ids)]).ids)
        if self._context.get('based_on', 'invoices') == 'payments':
            self._cr.execute('SELECT line.tax_code_id, sum(line.tax_amount) \
                    FROM account_move_line AS line, \
                        account_move AS move \
                        LEFT JOIN account_invoice invoice ON \
                            (invoice.move_id = move.id) \
                    WHERE line.tax_code_id IN %s '+where+' \
                        AND move.id = line.move_id \
                        AND ((invoice.state = \'paid\') \
                            OR (invoice.id IS NULL)) \
                            GROUP BY line.tax_code_id',
                                (parent_ids,) + where_params)
        else:
            self._cr.execute('SELECT line.tax_code_id, sum(line.tax_amount) \
                    FROM account_move_line AS line, \
                    account_move AS move \
                    WHERE line.tax_code_id IN %s '+where+' \
                    AND move.id = line.move_id \
                    GROUP BY line.tax_code_id',
                       (parent_ids,) + where_params)
        res=dict(self._cr.fetchall())
        res2 = {}
        for record in self:
            def _rec_get(record):
                amount = res.get(record.id, 0.0)
                for rec in record.child_ids:
                    amount += _rec_get(rec) * rec.sign
                return amount
            amount = round(_rec_get(record), self.env['decimal.precision'].precision_get('Account'))
            if name == 'sum':
                record.sum = amount
            elif name == 'sum_period':
                record.sum_period = amount

    @api.multi
    def _sum_year(self):
        if not self:
            return True
        move_state = ('posted', )
        FiscalyearObj = self.env['account.fiscalyear']
        if self._context.get('state', 'all') == 'all':
            move_state = ('draft', 'posted', )
        if self._context.get('fiscalyear_id', False):
            fiscalyear_id = [self._context['fiscalyear_id']]
        else:
            dt = fields.Date.context_today(self)
            fiscalyear_id = FiscalyearObj.search([('date_start', '<=' ,dt), ('date_stop', '>=', dt)], limit=1).id
        where = ''
        where_params = ()
        if fiscalyear_id:
            for fiscalyear in FiscalyearObj.browse(fiscalyear_id):
                date_start = fiscalyear.date_start
                date_stop = fiscalyear.date_stop
                where = ' AND line.date >= %s AND line.date <= %s AND move.state IN %s '
                where_params = (date_start, date_stop, move_state)
        self._sum(name='sum', where=where, where_params=where_params)


    _name = 'account.tax.code'
    _description = 'Tax Code'
    _rec_name = 'code'
    _order = 'sequence, code'

    name = fields.Char(string='Tax Case Name', required=True, translate=True)
    code = fields.Char(string='Case Code', size=64)
    info = fields.Text(string='Description')
    sum = fields.Float(compute='_sum_year', string='Year Sum')
    parent_id = fields.Many2one('account.tax.code', string='Parent Code', index=True)
    child_ids = fields.One2many('account.tax.code', 'parent_id', string='Child Codes')
    line_ids = fields.One2many('account.move.line', 'tax_code_id', string='Lines')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    sign = fields.Float(string='Coefficent for parent', required=True, default=1.0,
        help='You can specify here the coefficient that will be used when consolidating the amount of this case into its parent. For example, set 1/-1 if you want to add/substract it.')
    notprintable = fields.Boolean(string='Not Printable in Invoice', default=False,
        help="Check this box if you don't want any tax related to this tax code to appear on invoices")
    sequence = fields.Integer(string='Sequence',
        help="Determine the display order in the report 'Accounting \ Reporting \ Generic Reporting \ Taxes \ Taxes Report'")

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=80):
        args = args or []
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            domain = [('code', operator, name), ('name', operator, name)]
        else:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
        recs = self.search(expression.AND([domain, args]), limit=limit)
        return recs.name_get()

    @api.multi
    @api.depends('name', 'code')
    def name_get(self):
        return [(x.id, (x.code and (x.code + ' - ') or '') + x.name) for x in self]

    _constraints = [
        (models.Model._check_recursion, 'Error!\nYou cannot create recursive accounts.', ['parent_id'])
    ]

def get_precision_tax():
    def change_digit_tax(cr):
        res = openerp.registry(cr.dbname)['decimal.precision'].precision_get(cr, SUPERUSER_ID, 'Account')
        return (16, res+3)
    return change_digit_tax


class account_tax(models.Model):
    """
    A tax object.

    Type: percent, fixed, none, code
        PERCENT: tax = price * amount
        FIXED: tax = price + amount
        NONE: no tax line
        CODE: execute python code. localcontext = {'price_unit':pu}
            return result in the context
            Ex: result=round(price_unit*0.21,4)
    """
    @api.one
    def copy_data(self, default=None):
        if default is None:
            default = {}
        default = dict(default, name=_("%s (Copy)") % self.name)
        return super(account_tax, self).copy_data(default=default)

    _name = 'account.tax'
    _description = 'Tax'
    _order = 'sequence'

    name = fields.Char(string='Tax Name', required=True, translate=True, help="This name will be displayed on reports")
    sequence = fields.Integer(string='Sequence', required=True, default=1,
        help="The sequence field is used to order the tax lines from the lowest sequences to the higher ones. The order is important if you have a tax with several tax children. In this case, the evaluation order is important.")
    amount = fields.Float(string='Amount', required=True, digits=get_precision_tax(), default=0,
        help="For taxes of type percentage, enter % ratio between 0-1.")
    active = fields.Boolean(string='Active', default=True,
        help="If the active field is set to False, it will allow you to hide the tax without removing it.")
    type = fields.Selection([('percent', 'Percentage'), ('fixed', 'Fixed Amount'), ('none', 'None'), ('code', 'Python Code'), ('balance', 'Balance')],
        default='percent', string='Tax Type', required=True, help="The computation method for the tax amount.")
    applicable_type = fields.Selection([('true', 'Always'), ('code', 'Given by Python Code')], string='Applicability', required=True, default='true',
        help="If not applicable (computed through a Python code), the tax won't appear on the invoice.")
    domain = fields.Char(string='Domain',
        help="This field is only used if you develop your own module allowing developers to create specific taxes in a custom domain.")
    account_collected_id = fields.Many2one('account.account', string='Invoice Tax Account', domain=[('deprecated', '=', False)],
        help="Set the account that will be set by default on invoice tax lines for invoices. Leave empty to use the expense account.")
    account_paid_id = fields.Many2one('account.account', string='Refund Tax Account', domain=[('deprecated', '=', False)],
        help="Set the account that will be set by default on invoice tax lines for refunds. Leave empty to use the expense account.")
    account_analytic_collected_id = fields.Many2one('account.analytic.account', 'Invoice Tax Analytic Account',
        help="Set the analytic account that will be used by default on the invoice tax lines for invoices. Leave empty if you don't want to use an analytic account on the invoice tax lines by default.")
    account_analytic_paid_id = fields.Many2one('account.analytic.account', string='Refund Tax Analytic Account',
        help="Set the analytic account that will be used by default on the invoice tax lines for refunds. Leave empty if you don't want to use an analytic account on the invoice tax lines by default.")
    parent_id = fields.Many2one('account.tax', string='Parent Tax Account', index=True)
    child_ids = fields.One2many('account.tax', 'parent_id', string='Child Tax Accounts')
    child_depend = fields.Boolean(string='Tax on Children',
        help="Set if the tax computation is based on the computation of child taxes rather than on the total amount.")
    python_compute = fields.Text(string='Python Code',
        default='''# price_unit\n# or False\n# product: product.product object or None\n# partner: res.partner object or None\n\nresult = price_unit * 0.10''')
    python_compute_inv = fields.Text(string='Python Code (reverse)',
        default='''# price_unit\n# product: product.product object or False\n\nresult = price_unit * 0.10''')
    python_applicable = fields.Text(string='Applicable Code')

    #
    # Fields used for the Tax declaration
    #
    base_code_id = fields.Many2one('account.tax.code', string='Account Base Code', help="Use this code for the tax declaration.")
    tax_code_id = fields.Many2one('account.tax.code', string='Account Tax Code', help="Use this code for the tax declaration.")
    base_sign = fields.Float(string='Base Code Sign', help="Usually 1 or -1.", digits=get_precision_tax(), default=1)
    tax_sign = fields.Float(string='Tax Code Sign', help="Usually 1 or -1.", digits=get_precision_tax(), default=1)

    # Same fields for refund invoices

    ref_base_code_id = fields.Many2one('account.tax.code', string='Refund Base Code', help="Use this code for the tax declaration.")
    ref_tax_code_id = fields.Many2one('account.tax.code', string='Refund Tax Code', help="Use this code for the tax declaration.")
    ref_base_sign = fields.Float(string='Refund Base Code Sign', help="Usually 1 or -1.", digits=get_precision_tax(), default=1)
    ref_tax_sign = fields.Float(string='Refund Tax Code Sign', help="Usually 1 or -1.", digits=get_precision_tax(), default=1)
    include_base_amount = fields.Boolean(string='Included in base amount', default=False,
        help="Indicates if the amount of tax must be included in the base amount for the computation of the next taxes")
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    description = fields.Char(string='Tax Code')
    price_include = fields.Boolean(string='Tax Included in Price', default=False,
        help="Check this if the price you use on the product and invoices includes this tax.")
    type_tax_use = fields.Selection([('sale', 'Sale'), ('purchase', 'Purchase'), ('all', 'All')], string='Tax Application', required=True, default='all')

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 'Tax Name must be unique per company!'),
    ]

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=80):
        """
        Returns a list of tupples containing id, name, as internally it is called {def name_get}
        result format: {[(id, name), (id, name), ...]}

        @param cr: A database cursor
        @param user: ID of the user currently logged in
        @param name: name to search
        @param args: other arguments
        @param operator: default operator is 'ilike', it can be changed
        @param context: context arguments, like lang, time zone
        @param limit: Returns first 'n' ids of complete result, default is 80.

        @return: Returns a list of tupples containing id and name
        """
        if not args:
            args = []
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            domain = [('description', operator, name), ('name', operator, name)]
        else:
            domain = ['|', ('description', operator, name), ('name', operator, name)]
        taxes = self.search(expression.AND([domain, args]), limit=limit)
        return taxes.name_get()

    @api.multi
    def write(self, vals):
        if vals.get('type', False) and vals['type'] in ('none', 'code'):
            vals.update({'amount': 0.0})
        return super(account_tax, self).write(vals)

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        context = dict(self._context or {})

        if context.get('type'):
            if context.get('type') in ('out_invoice', 'out_refund'):
                args += [('type_tax_use', 'in', ['sale', 'all'])]
            elif context.get('type') in ('in_invoice', 'in_refund'):
                args += [('type_tax_use', 'in', ['purchase', 'all'])]

        if context.get('journal_id'):
            journal = self.env['account.journal'].browse(context.get('journal_id'))
            if journal.type in ('sale', 'purchase'):
                args += [('type_tax_use', 'in', [journal.type, 'all'])]

        return super(account_tax, self).search(args, offset, limit, order, count=count)

    @api.multi
    @api.depends('name', 'description')
    def name_get(self):
        res = []
        for record in self:
            name = record.description and record.description or record.name
            res.append((record.id, name ))
        return res

    @api.multi
    def _applicable(self, price_unit, product=None, partner=None):
        res = []
        for tax in self:
            if tax.applicable_type == 'code':
                localdict = {'price_unit': price_unit, 'product': product, 'partner': partner}
                exec tax.python_applicable in localdict
                if localdict.get('result', False):
                    res.append(tax)
            else:
                res.append(tax)
        return res

    @api.multi
    def _unit_compute(self, price_unit, product=None, partner=None, quantity=0):
        taxes = self._applicable(price_unit ,product, partner)
        res = []
        cur_price_unit = price_unit
        for tax in taxes:
            # we compute the amount for the current tax object and append it to the result
            data = {'id': tax.id,
                    'name': tax.description and tax.description + " - " + tax.name or tax.name,
                    'account_collected_id': tax.account_collected_id.id,
                    'account_paid_id': tax.account_paid_id.id,
                    'account_analytic_collected_id': tax.account_analytic_collected_id.id,
                    'account_analytic_paid_id': tax.account_analytic_paid_id.id,
                    'base_code_id': tax.base_code_id.id,
                    'ref_base_code_id': tax.ref_base_code_id.id,
                    'sequence': tax.sequence,
                    'base_sign': tax.base_sign,
                    'tax_sign': tax.tax_sign,
                    'ref_base_sign': tax.ref_base_sign,
                    'ref_tax_sign': tax.ref_tax_sign,
                    'price_unit': cur_price_unit,
                    'tax_code_id': tax.tax_code_id.id,
                    'ref_tax_code_id': tax.ref_tax_code_id.id,
            }
            res.append(data)
            if tax.type == 'percent':
                amount = cur_price_unit * tax.amount
                data['amount'] = amount

            elif tax.type == 'fixed':
                data['amount'] = tax.amount
                data['tax_amount'] = quantity
               # data['amount'] = quantity
            elif tax.type == 'code':
                localdict = {'price_unit': cur_price_unit, 'product': product, 'partner': partner}
                exec tax.python_compute in localdict
                amount = localdict['result']
                data['amount'] = amount
            elif tax.type == 'balance':
                data['amount'] = cur_price_unit - reduce(lambda x, y: y.get('amount', 0.0) + x, res, 0.0)
                data['balance'] = cur_price_unit

            amount2 = data.get('amount', 0.0)
            if tax.child_ids:
                if tax.child_depend:
                    latest = res.pop()
                amount = amount2
                child_tax = tax.child_ids._unit_compute(amount, product, partner, quantity)
                res.extend(child_tax)
                for child in child_tax:
                    amount2 += child.get('amount', 0.0)
                if tax.child_depend:
                    for r in res:
                        for name in ('base', 'ref_base'):
                            if latest[name + '_code_id'] and latest[name + '_sign'] and not r[name + '_code_id']:
                                r[name + '_code_id'] = latest[name + '_code_id']
                                r[name + '_sign'] = latest[name + '_sign']
                                r['price_unit'] = latest['price_unit']
                                latest[name + '_code_id'] = False
                        for name in ('tax', 'ref_tax'):
                            if latest[name + '_code_id'] and latest[name + '_sign'] and not r[name + '_code_id']:
                                r[name + '_code_id'] = latest[name + '_code_id']
                                r[name + '_sign'] = latest[name + '_sign']
                                r['amount'] = data['amount']
                                latest[name + '_code_id'] = False
            if tax.include_base_amount:
                cur_price_unit += amount2
        return res

    @api.one
    def compute_for_bank_reconciliation(self, amount):
        """ Called by RPC by the bank statement reconciliation widget """
        return self.compute_all(amount, 1) # TOCHECK may use force_exclude parameter

    @api.v7
    def compute_all(self, cr, uid, taxes, price_unit, quantity, product=None, partner=None, force_excluded=False):
        """
        :param force_excluded: boolean used to say that we don't want to consider the value of field price_include of
            tax. It's used in encoding by line where you don't matter if you encoded a tax with that boolean to True or
            False
        RETURN: {
                'total': 0.0,                # Total without taxes
                'total_included: 0.0,        # Total with taxes
                'taxes': []                  # List of taxes, see compute for the format
            }
        """

        # By default, for each tax, tax amount will first be computed
        # and rounded at the 'Account' decimal precision for each
        # PO/SO/invoice line and then these rounded amounts will be
        # summed, leading to the total amount for that tax. But, if the
        # company has tax_calculation_rounding_method = round_globally,
        # we still follow the same method, but we use a much larger
        # precision when we round the tax amount for each line (we use
        # the 'Account' decimal precision + 5), and that way it's like
        # rounding after the sum of the tax amounts of each line
        precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
        tax_compute_precision = precision
        if taxes and taxes[0].company_id.tax_calculation_rounding_method == 'round_globally':
            tax_compute_precision += 5
        totalin = totalex = round(price_unit * quantity, precision)
        tin = []
        tex = []
        for tax in taxes:
            if not tax.price_include or force_excluded:
                tex.append(tax)
            else:
                tin.append(tax)
        tin = self.compute_inv(cr, uid, tin, price_unit, quantity, product=product, partner=partner, precision=tax_compute_precision)
        for r in tin:
            totalex -= r.get('amount', 0.0)
        totlex_qty = 0.0
        try:
            totlex_qty = totalex/quantity
        except:
            pass
        tex = self._compute(cr, uid, tex, totlex_qty, quantity, product=product, partner=partner, precision=tax_compute_precision)
        for r in tex:
            totalin += r.get('amount', 0.0)
        return {
            'total': totalex,
            'total_included': totalin,
            'taxes': tin + tex
        }

    @api.v8
    def compute_all(self, price_unit, quantity, product=None, partner=None, force_excluded=False):
        return self._model.compute_all(
            self._cr, self._uid, self, price_unit, quantity,
            product=product, partner=partner, force_excluded=force_excluded)

    @api.multi
    def compute(self, price_unit, quantity,  product=None, partner=None):
        _logger.warning("Deprecated, use compute_all(...)['taxes'] instead of compute(...) to manage prices with tax included.")
        return self._compute(price_unit, quantity, product, partner)

    @api.multi
    def _compute(self, price_unit, quantity, product=None, partner=None, precision=None):
        """
        Compute tax values for given PRICE_UNIT, QUANTITY and a buyer/seller ADDRESS_ID.

        RETURN:
            [ tax ]
            tax = {'name':'', 'amount':0.0, 'account_collected_id':1, 'account_paid_id':2}
            one tax for each tax id in IDS and their children
        """
        if not precision:
            precision = self.env['decimal.precision'].precision_get('Account')
        res = self._unit_compute(price_unit, product, partner, quantity)
        total = 0.0
        for r in res:
            if r.get('balance', False):
                r['amount'] = round(r.get('balance', 0.0) * quantity, precision) - total
            else:
                r['amount'] = round(r.get('amount', 0.0) * quantity, precision)
                total += r['amount']
        return res

    @api.multi
    def _unit_compute_inv(self, price_unit, product=None, partner=None):
        taxes = self._applicable(price_unit,  product, partner)
        res = []
        taxes.reverse()
        cur_price_unit = price_unit

        tax_parent_tot = 0.0
        for tax in taxes:
            if (tax.type == 'percent') and not tax.include_base_amount:
                tax_parent_tot += tax.amount

        for tax in taxes:
            if (tax.type == 'fixed') and not tax.include_base_amount:
                cur_price_unit -= tax.amount

        for tax in taxes:
            if tax.type == 'percent':
                if tax.include_base_amount:
                    amount = cur_price_unit - (cur_price_unit / (1 + tax.amount))
                else:
                    amount = (cur_price_unit / (1 + tax_parent_tot)) * tax.amount

            elif tax.type == 'fixed':
                amount = tax.amount

            elif tax.type == 'code':
                localdict = {'price_unit': cur_price_unit, 'product': product, 'partner': partner}
                exec tax.python_compute_inv in localdict
                amount = localdict['result']
            elif tax.type == 'balance':
                amount = cur_price_unit - reduce(lambda x, y: y.get('amount', 0.0) + x, res, 0.0)

            if tax.include_base_amount:
                cur_price_unit -= amount
                todo = 0
            else:
                todo = 1
            res.append({
                'id': tax.id,
                'todo': todo,
                'name': tax.name,
                'amount': amount,
                'account_collected_id': tax.account_collected_id.id,
                'account_paid_id': tax.account_paid_id.id,
                'account_analytic_collected_id': tax.account_analytic_collected_id.id,
                'account_analytic_paid_id': tax.account_analytic_paid_id.id,
                'base_code_id': tax.base_code_id.id,
                'ref_base_code_id': tax.ref_base_code_id.id,
                'sequence': tax.sequence,
                'base_sign': tax.base_sign,
                'tax_sign': tax.tax_sign,
                'ref_base_sign': tax.ref_base_sign,
                'ref_tax_sign': tax.ref_tax_sign,
                'price_unit': cur_price_unit,
                'tax_code_id': tax.tax_code_id.id,
                'ref_tax_code_id': tax.ref_tax_code_id.id,
            })
            if tax.child_ids:
                if tax.child_depend:
                    del res[-1]
                    amount = price_unit

            parent_tax = tax.child_ids._unit_compute_inv(amount, product, partner)
            res.extend(parent_tax)

        total = 0.0
        for r in res:
            if r['todo']:
                total += r['amount']
        for r in res:
            r['price_unit'] -= total
            r['todo'] = 0
        return res

    @api.multi
    def compute_inv(self, price_unit, quantity, product=None, partner=None, precision=None):
        """
        Compute tax values for given PRICE_UNIT, QUANTITY and a buyer/seller ADDRESS_ID.
        Price Unit is a Tax included price

        RETURN:
            [ tax ]
            tax = {'name':'', 'amount':0.0, 'account_collected_id':1, 'account_paid_id':2}
            one tax for each tax id in IDS and their children
        """
        if not precision:
            precision = self.env['decimal.precision'].precision_get('Account')
        res = self._unit_compute_inv(price_unit, product, partner=None)
        total = 0.0
        for r in res:
            if r.get('balance', False):
                r['amount'] = round(r['balance'] * quantity, precision) - total
            else:
                r['amount'] = round(r['amount'] * quantity, precision)
                total += r['amount']
        return res


#  ---------------------------------------------------------------
#   Account Templates: Account, Tax, Tax Code and chart. + Wizard
#  ---------------------------------------------------------------

class account_tax_template(models.Model):
    _name = 'account.tax.template'

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
    type = fields.Selection(related='user_type.type', string='Type', store=True,
        selection=[('other', 'Regular'), ('receivable', 'Receivable'), ('payable', 'Payable'), ('liquidity','Liquidity'),
        ('consolidation', 'Consolidation')])
    reconcile = fields.Boolean(string='Allow Reconciliation', default=False,
        help="Check this option if you want the user to reconcile entries in this account.")
    note = fields.Text(string='Note')
    tax_ids = fields.Many2many('account.tax.template', 'account_account_template_tax_rel', 'account_id', 'tax_id', string='Default Taxes')
    nocreate = fields.Boolean(string='Optional Create', default=False,
        help="If checked, the new chart of accounts will not contain this by default.")
    chart_template_id = fields.Many2one('account.chart.template', string='Chart Template',
        help="This optional field allow you to link an account template to a specific chart template that may differ from the one its root parent belongs to. This allow you to define chart templates that extend another and complete it with few new accounts (You don't need to define the whole structure that is common to both several times).")

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
                'type': account_template.type,
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
            accounts = self.env['account.account'].search([('code', '=', ptids[0]['code'])], limit=1)
        return account

    cparent_id = fields.Many2one('account.account', string='Parent target', default=lambda self: self._get_def_cparent(),
        help="Creates an account with the selected template under this existing parent.", required=True, domain=[('deprecated', '=', False)])

    @api.multi
    def action_create(self):
        context = dict(self._context or {})
        AccountObj = self.pool.get('account.account')
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


class account_tax_code_template(models.Model):
    _name = 'account.tax.code.template'
    _description = 'Tax Code Template'
    _order = 'sequence, code'
    _rec_name = 'code'

    name = fields.Char(string='Tax Case Name', required=True)
    code = fields.Char(string='Case Code', size=64)
    info = fields.Text(string='Description')
    parent_id = fields.Many2one('account.tax.code.template', string='Parent Code', index=True)
    child_ids = fields.One2many('account.tax.code.template', 'parent_id', string='Child Codes')
    sign = fields.Float(string='Sign For Parent', required=True, default=1.0)
    notprintable = fields.Boolean(string='Not Printable in Invoice', default=False,
        help="Check this box if you don't want any tax related to this tax Code to appear on invoices.")
    sequence = fields.Integer(string='Sequence', help=(
            "Determine the display order in the report 'Accounting "
            "\ Reporting \ Generic Reporting \ Taxes \ Taxes Report'"),
        )

    @api.one
    def generate_tax_code(self, company_id):
        '''
        This function generates the tax codes from the templates of tax code that are children of the given one passed
        in argument. Then it returns a dictionary with the mappping between the templates and the real objects.

        :param company_id: id of the company the wizard is running for
        :returns: dictionary with the mappping between the templates and the real objects.
        :rtype: dict
        '''
        obj_tax_code = self.env['account.tax.code']
        tax_code_template_ref = {}
        company = self.env['res.company'].browse(company_id)

        #find all the children
        children_tax_code_template = self.search([('parent_id', 'child_of', self.ids)], order='id') or []
        for tax_code_template in children_tax_code_template:
            vals = {
                'name': (self.id == tax_code_template.id) and company.name or tax_code_template.name,
                'code': tax_code_template.code,
                'info': tax_code_template.info,
                'parent_id': tax_code_template.parent_id and ((tax_code_template.parent_id.id in tax_code_template_ref) and tax_code_template_ref[tax_code_template.parent_id.id]) or False,
                'company_id': company_id,
                'sign': tax_code_template.sign,
                'sequence': tax_code_template.sequence,
            }
            #check if this tax code already exists
            rec_list = obj_tax_code.search([('name', '=', vals['name']), ('code', '=', vals['code']), ('company_id', '=', vals['company_id'])], limit=1)
            if not rec_list:
                #if not yet, create it
                new_tax_code = obj_tax_code.create(vals)
                #recording the new tax code to do the mapping
                tax_code_template_ref[tax_code_template.id] = new_tax_code.id
        return tax_code_template_ref

    @api.multi
    @api.depends('name', 'code')
    def name_get(self):
        return [(record.id, (record.code and record.code + ' - ' or '') + record.name) for record in self]

    _constraints = [
        (models.Model._check_recursion, 'Error!\nYou cannot create recursive Tax Codes.', ['parent_id'])
    ]


class account_chart_template(models.Model):
    _name="account.chart.template"
    _description= "Templates for Account Chart"

    name = fields.Char(string='Name', required=True)
    parent_id = fields.Many2one('account.chart.template', string='Parent Chart Template')
    code_digits = fields.Integer(string='# of Digits', required=True, default=6, help="No. of Digits to use for account code")
    visible = fields.Boolean(string='Can be Visible?', default=True,
        help="Set this to False if you don't want this template to be used actively in the wizard that generate Chart of Accounts from templates, this is useful when you want to generate accounts of this template only when loading its child template.")
    currency_id = fields.Many2one('res.currency', string='Currency')
    complete_tax_set = fields.Boolean(string='Complete Set of Taxes', default=True,
        help='This boolean helps you to choose if you want to propose to the user to encode the sale and purchase rates or choose from list of taxes. This last choice assumes that the set of tax defined on this template is complete')
    account_root_id = fields.Many2one('account.account.template', string='Root Account', domain=[('parent_id','=',False)])
    tax_code_root_id = fields.Many2one('account.tax.code.template', string='Root Tax Code', domain=[('parent_id','=',False)])
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
    _order = 'sequence'

    chart_template_id = fields.Many2one('account.chart.template', string='Chart Template', required=True)
    name = fields.Char(string='Tax Name', required=True)
    sequence = fields.Integer(string='Sequence', required=True, default=1,
        help="The sequence field is used to order the taxes lines from lower sequences to higher ones. The order is important if you have a tax that has several tax children. In this case, the evaluation order is important.")
    amount = fields.Float(string='Amount', required=True, digits=get_precision_tax(), default=0, help="For Tax Type percent enter % ratio between 0-1.")
    type = fields.Selection([('percent', 'Percent'), ('fixed', 'Fixed'), ('none', 'None'), ('code', 'Python Code'), ('balance', 'Balance')],
        string='Tax Type', default='percent', required=True)
    applicable_type = fields.Selection([('true', 'True'), ('code', 'Python Code')], string='Applicable Type', required=True,
        default='true', help="If not applicable (computed through a Python code), the tax won't appear on the invoice.")
    domain = fields.Char(string='Domain',
        help="This field is only used if you develop your own module allowing developers to create specific taxes in a custom domain.")
    account_collected_id = fields.Many2one('account.account.template', string='Invoice Tax Account')
    account_paid_id = fields.Many2one('account.account.template', string='Refund Tax Account')
    parent_id = fields.Many2one('account.tax.template', string='Parent Tax Account', index=True)
    child_depend = fields.Boolean(string='Tax on Children', help="Set if the tax computation is based on the computation of child taxes rather than on the total amount.")
    python_compute = fields.Text(string='Python Code',
        default='''# price_unit\n# product: product.product object or None\n# partner: res.partner object or None\n\nresult = price_unit * 0.10''')
    python_compute_inv = fields.Text(string='Python Code (reverse)',
        default='''# price_unit\n# product: product.product object or False\n\nresult = price_unit * 0.10''')
    python_applicable = fields.Text(string='Applicable Code')

    #
    # Fields used for the Tax declaration
    #
    base_code_id = fields.Many2one('account.tax.code.template', string='Base Code', help="Use this code for the tax declaration.")
    tax_code_id = fields.Many2one('account.tax.code.template', string='Tax Code', help="Use this code for the tax declaration.")
    base_sign = fields.Float(string='Base Code Sign', default=1, help="Usually 1 or -1.")
    tax_sign = fields.Float(string='Tax Code Sign', default=1, help="Usually 1 or -1.")

    # Same fields for refund invoices

    ref_base_code_id = fields.Many2one('account.tax.code.template', string='Refund Base Code', help="Use this code for the tax declaration.")
    ref_tax_code_id = fields.Many2one('account.tax.code.template', string='Refund Tax Code', help="Use this code for the tax declaration.")
    ref_base_sign = fields.Float(string='Refund Base Code Sign', default=1, help="Usually 1 or -1.")
    ref_tax_sign = fields.Float(string='Refund Tax Code Sign', default=1, help="Usually 1 or -1.")
    include_base_amount = fields.Boolean(string='Include in Base Amount', default=False,
        help="Set if the amount of tax must be included in the base amount before computing the next taxes.")
    description = fields.Char(string='Internal Name')
    type_tax_use = fields.Selection([('sale', 'Sale'), ('purchase', 'Purchase'), ('all', 'All')], default='all',
        string='Tax Use In', required=True)
    price_include = fields.Boolean(string='Tax Included in Price', default=False,
        help="Check this if the price you use on the product and invoices includes this tax.")

    @api.multi
    @api.depends('name', 'description')
    def name_get(self):
        res = []
        for record in self:
            name = record.description and record.description or record.name
            res.append((record.id, name))
        return res

    @api.model
    def _default_company(self):
        return self.env.user.comapny_id.id

    @api.multi
    def _generate_tax(self, tax_code_template_ref, company_id):
        """
        This method generate taxes from templates.

        :param tax_code_template_ref: Taxcode templates reference.
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
                'sequence': tax.sequence,
                'amount': tax.amount,
                'type': tax.type,
                'applicable_type': tax.applicable_type,
                'domain': tax.domain,
                'parent_id': tax.parent_id and ((tax.parent_id.id in tax_template_to_tax) and tax_template_to_tax[tax.parent_id.id]) or False,
                'child_depend': tax.child_depend,
                'python_compute': tax.python_compute,
                'python_compute_inv': tax.python_compute_inv,
                'python_applicable': tax.python_applicable,
                'base_code_id': tax.base_code_id and ((tax.base_code_id.id in tax_code_template_ref) and tax_code_template_ref[tax.base_code_id.id]) or False,
                'tax_code_id': tax.tax_code_id and ((tax.tax_code_id.id in tax_code_template_ref) and tax_code_template_ref[tax.tax_code_id.id]) or False,
                'base_sign': tax.base_sign,
                'tax_sign': tax.tax_sign,
                'ref_base_code_id': tax.ref_base_code_id and ((tax.ref_base_code_id.id in tax_code_template_ref) and tax_code_template_ref[tax.ref_base_code_id.id]) or False,
                'ref_tax_code_id': tax.ref_tax_code_id and ((tax.ref_tax_code_id.id in tax_code_template_ref) and tax_code_template_ref[tax.ref_tax_code_id.id]) or False,
                'ref_base_sign': tax.ref_base_sign,
                'ref_tax_sign': tax.ref_tax_sign,
                'include_base_amount': tax.include_base_amount,
                'description': tax.description,
                'company_id': company_id,
                'type_tax_use': tax.type_tax_use,
                'price_include': tax.price_include
            }
            new_tax = self.env['account.tax'].create(vals_tax)
            tax_template_to_tax[tax.id] = new_tax.id
            #as the accounts have not been created yet, we have to wait before filling these fields
            todo_dict[new_tax.id] = {
                'account_collected_id': tax.account_collected_id and tax.account_collected_id.id or False,
                'account_paid_id': tax.account_paid_id and tax.account_paid_id.id or False,
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
        help='This boolean helps you to choose if you want to propose to the user to encode the sales and purchase rates or use the usual m2o fields. This last choice assumes that the set of tax defined for the chosen template is complete')

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
        return {'value': {'purchase_tax_rate': self.sale_tax_rate or False}}

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
                sale_tax_domain = base_tax_domain + [('type_tax_use', 'in', ('sale', 'all'))]
                purchase_tax_domain = base_tax_domain + [('type_tax_use', 'in', ('purchase', 'all'))]
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
                                                              ('type_tax_use', 'in', ('sale', 'all'))], limit=1, order='sequence')
                res.update({'sale_tax': sale_tax and sale_tax.id or False})
            if 'purchase_tax' in fields:
                purchase_tax = tax_templ_obj.search([('chart_template_id', 'in', chart_hierarchy_ids),
                                                                  ('type_tax_use', 'in', ('purchase', 'all'))], limit=1, order='sequence')
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
                if journal_type in ('sale', 'sale_refund'):
                    data = self.env.ref('account.analytic_journal_sale')
                elif journal_type in ('purchase', 'purchase_refund'):
                    data = self.env.ref('account.exp')
                elif journal_type == 'general':
                    pass
            except ValueError:
                pass
            return data and data.id or False

        def _get_default_account(journal_type, type='debit'):
            # Get the default accounts
            default_account = False
            if journal_type in ('sale', 'sale_refund'):
                default_account = acc_template_ref.get(template.property_account_income_categ.id)
            elif journal_type in ('purchase', 'purchase_refund'):
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
            'sale_refund': _('Sales Refund Journal'),
            'purchase_refund': _('Purchase Refund Journal'),
            'general': _('Miscellaneous Journal'),
            'situation': _('Opening Entries Journal'),
        }
        journal_codes = {
            'sale': _('SAJ'),
            'purchase': _('EXJ'),
            'sale_refund': _('SCNJ'),
            'purchase_refund': _('ECNJ'),
            'general': _('MISC'),
            'situation': _('OPEJ'),
        }

        template = self.env['account.chart.template'].browse(chart_template_id)

        journal_data = []
        for journal_type in ['sale', 'purchase', 'sale_refund', 'purchase_refund', 'general', 'situation']:
            vals = {
                'type': journal_type,
                'name': journal_names[journal_type],
                'code': journal_codes[journal_type],
                'company_id': company_id,
                'analytic_journal_id': _get_analytic_journal(journal_type),
                'default_credit_account_id': _get_default_account(journal_type, 'credit'),
                'default_debit_account_id': _get_default_account(journal_type, 'debit'),
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
    def _install_template(self, template_id, company_id, code_digits=None, obj_wizard=None, acc_ref=None, taxes_ref=None, tax_code_ref=None):
        '''
        This function recursively loads the template objects and create the real objects from them.

        :param template_id: id of the chart template to load
        :param company_id: id of the company the wizard is running for
        :param code_digits: integer that depicts the number of digits the accounts code should have in the COA
        :param obj_wizard: the current wizard for generating the COA from the templates
        :param acc_ref: Mapping between ids of account templates and real accounts created from them
        :param taxes_ref: Mapping between ids of tax templates and real taxes created from them
        :param tax_code_ref: Mapping between ids of tax code templates and real tax codes created from them
        :returns: return a tuple with a dictionary containing
            * the mapping between the account template ids and the ids of the real accounts that have been generated
              from them, as first item,
            * a similar dictionary for mapping the tax templates and taxes, as second item,
            * a last identical containing the mapping of tax code templates and tax codes
        :rtype: tuple(dict, dict, dict)
        '''
        if acc_ref is None:
            acc_ref = {}
        if taxes_ref is None:
            taxes_ref = {}
        if tax_code_ref is None:
            tax_code_ref = {}
        template = self.env['account.chart.template'].browse(template_id)
        if template.parent_id:
            tmp1, tmp2, tmp3 = self._install_template(template.parent_id.id, company_id, code_digits=code_digits, acc_ref=acc_ref, taxes_ref=taxes_ref, tax_code_ref=tax_code_ref)
            acc_ref.update(tmp1)
            taxes_ref.update(tmp2)
            tax_code_ref.update(tmp3)
        tmp1, tmp2, tmp3 = self._load_template(template_id, company_id, code_digits=code_digits, obj_wizard=obj_wizard, account_ref=acc_ref, taxes_ref=taxes_ref, tax_code_ref=tax_code_ref)
        acc_ref.update(tmp1)
        taxes_ref.update(tmp2)
        tax_code_ref.update(tmp3)
        return acc_ref, taxes_ref, tax_code_ref

    @api.model
    def _load_template(self, template_id, company_id, code_digits=None, obj_wizard=None, account_ref=None, taxes_ref=None, tax_code_ref=None):
        '''
        This function generates all the objects from the templates

        :param template_id: id of the chart template to load
        :param company_id: id of the company the wizard is running for
        :param code_digits: integer that depicts the number of digits the accounts code should have in the COA
        :param obj_wizard: the current wizard for generating the COA from the templates
        :param acc_ref: Mapping between ids of account templates and real accounts created from them
        :param taxes_ref: Mapping between ids of tax templates and real taxes created from them
        :param tax_code_ref: Mapping between ids of tax code templates and real tax codes created from them
        :returns: return a tuple with a dictionary containing
            * the mapping between the account template ids and the ids of the real accounts that have been generated
              from them, as first item,
            * a similar dictionary for mapping the tax templates and taxes, as second item,
            * a last identical containing the mapping of tax code templates and tax codes
        :rtype: tuple(dict, dict, dict)
        '''
        if account_ref is None:
            account_ref = {}
        if taxes_ref is None:
            taxes_ref = {}
        if tax_code_ref is None:
            tax_code_ref = {}
        template = self.env['account.chart.template'].browse(template_id)
        AccountTaxObj = self.env['account.tax']

        # create all the tax code.
        tax_code_ref.update(self.env['account.tax.code.template'].generate_tax_code(template.tax_code_root_id.id, company_id))

        # Generate taxes from templates.
        generated_tax_res = template.tax_template_ids._generate_tax(tax_code_ref, company_id)
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

        return account_ref, taxes_ref, tax_code_ref

    @api.one
    def _create_tax_templates_from_rates(self, company_id):
        '''
        This function checks if the chosen chart template is configured as containing a full set of taxes, and if
        it's not the case, it creates the templates for account.tax.code and for account.account.tax objects accordingly
        to the provided sale/purchase rates. Then it saves the new tax templates as default taxes to use for this chart
        template.

        :param company_id: id of the company for wich the wizard is running
        :return: True
        '''
        obj_tax_temp = self.env['account.tax.template']
        all_parents = self._get_chart_parent_ids(self.chart_template_id)
        # create tax templates and tax code templates from purchase_tax_rate and sale_tax_rate fields
        if not self.chart_template_id.complete_tax_set:
            value = self.sale_tax_rate
            ref_tax_ids = obj_tax_temp.search([('type_tax_use','in', ('sale','all')), ('chart_template_id', 'in', all_parents)], order="sequence, id desc", limit=1)
            ref_tax_ids.write({'amount': value/100.0, 'name': _('Tax %.2f%%') % value})
            value = self.purchase_tax_rate
            ref_tax_ids = obj_tax_temp.search([('type_tax_use','in', ('purchase','all')), ('chart_template_id', 'in', all_parents)], order="sequence, id desc", limit=1)
            ref_tax_ids.write({'amount': value/100.0, 'name': _('Purchase Tax %.2f%%') % value})
        return True

    @api.multi
    def execute(self):
        '''
        This function is called at the confirmation of the wizard to generate the COA from the templates. It will read
        all the provided information to create the accounts, the banks, the journals, the taxes, the tax codes, the
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
        acc_template_ref, taxes_ref, tax_code_ref = self._install_template(self.chart_template_id.id, company_id, code_digits=self.code_digits, obj_wizard=self)

        # write values of default taxes for product as super user
        if self.sale_tax and taxes_ref:
            ir_values_obj.sudo().set_default('product.product', "taxes_id", [taxes_ref[self.sale_tax.id]], for_all_users=True, company_id=company_id)
        if self.purchase_tax and taxes_ref:
            ir_values_obj.sudo().set_default('product.product', "supplier_taxes_id", [taxes_ref[self.purchase_tax.id]], for_all_users=True, company_id=company_id)

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
        available_digits = code_digits - len(bank_account_code_char)
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
        company = self.env['res.company'].search(company_id)

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

    name = fields.Char(string='Button Label', required=True)
    sequence = fields.Integer(required=True, default=10)
    account_id = fields.Many2one('account.account', string='Account', ondelete='cascade', domain=[('deprecated', '=', False)])
    journal_id = fields.Many2one('account.journal', string='Journal', ondelete='cascade', help="This field is ignored in a bank statement reconciliation.")
    label = fields.Char(string='Journal Item Label')
    amount_type = fields.Selection(selection=[('fixed', 'Fixed'),('percentage','Percentage of amount')], string='Amount type', required=True, default='percentage')
    amount = fields.Float(digits=dp.get_precision('Account'), required=True, default=100.0, help="Fixed amount will count as a debit if it is negative, as a credit if it is positive.")
    tax_id = fields.Many2one('account.tax', string='Tax', ondelete='cascade')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', ondelete='cascade')
    has_second_line = fields.boolean(string='Second line', default=False)
    second_account_id = fields.Many2one('account.account', string='Account', ondelete='cascade', domain=[('deprecated', '=', False)])
    second_journal_id = fields.Many2one('account.journal', string='Journal', ondelete='cascade', help="This field is ignored in a bank statement reconciliation.")
    second_label = fields.Char(string='Label')
    second_amount_type = fields.Selection(selection=[('fixed', 'Fixed'),('percentage','Percentage of amount')], string='Amount type', required=True, default='percentage')
    second_amount = fields.Float(string='Amount', digits=dp.get_precision('Account'), required=True, default=100.0, help="Fixed amount will count as a debit if it is negative, as a credit if it is positive.")
    second_tax_id = fields.Many2one('account.tax', string='Tax', ondelete='cascade')
    second_analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', ondelete='cascade')
