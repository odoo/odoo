# -*- coding: utf-8 -*-

import time
import math

from odoo.osv import expression
from odoo.tools.float_utils import float_round as round
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, _


class AccountAccountType(models.Model):
    _name = "account.account.type"
    _description = "Account Type"

    name = fields.Char(string='Account Type', required=True, translate=True)
    include_initial_balance = fields.Boolean(string="Bring Accounts Balance Forward", help="Used in reports to know if we should consider journal items from the beginning of time instead of from the fiscal year only. Account types that should be reset to zero at each new fiscal year (like expenses, revenue..) should not have this option set.")
    type = fields.Selection([
        ('other', 'Regular'),
        ('receivable', 'Receivable'),
        ('payable', 'Payable'),
        ('liquidity', 'Liquidity'),
    ], required=True, default='other',
        help="The 'Internal Type' is used for features available on "\
        "different types of accounts: liquidity type is for cash or bank accounts"\
        ", payable/receivable is for vendor/customer accounts.")
    note = fields.Text(string='Description')


class AccountAccountTag(models.Model):
    _name = 'account.account.tag'
    _description = 'Account Tag'

    name = fields.Char(required=True)
    applicability = fields.Selection([('accounts', 'Accounts'), ('taxes', 'Taxes')], required=True, default='accounts')
    color = fields.Integer('Color Index', default=10)

#----------------------------------------------------------
# Accounts
#----------------------------------------------------------


class AccountAccount(models.Model):
    _name = "account.account"
    _description = "Account"
    _order = "code"

    @api.multi
    @api.constrains('internal_type', 'reconcile')
    def _check_reconcile(self):
        for account in self:
            if account.internal_type in ('receivable', 'payable') and account.reconcile == False:
                raise ValidationError(_('You cannot have a receivable/payable account that is not reconciliable. (account code: %s)') % account.code)

    name = fields.Char(required=True, index=True)
    currency_id = fields.Many2one('res.currency', string='Account Currency',
        help="Forces all moves for this account to have this account currency.")
    code = fields.Char(size=64, required=True, index=True)
    deprecated = fields.Boolean(index=True, default=False)
    user_type_id = fields.Many2one('account.account.type', string='Type', required=True, oldname="user_type",
        help="Account Type is used for information purpose, to generate country-specific legal reports, and set the rules to close a fiscal year and generate opening entries.")
    internal_type = fields.Selection(related='user_type_id.type', string="Internal Type", store=True, readonly=True)
    #has_unreconciled_entries = fields.Boolean(compute='_compute_has_unreconciled_entries',
    #    help="The account has at least one unreconciled debit and credit since last time the invoices & payments matching was performed.")
    last_time_entries_checked = fields.Datetime(string='Latest Invoices & Payments Matching Date', readonly=True, copy=False,
        help='Last time the invoices & payments matching was performed on this account. It is set either if there\'s not at least '\
        'an unreconciled debit and an unreconciled credit Or if you click the "Done" button.')
    reconcile = fields.Boolean(string='Allow Reconciliation', default=False,
        help="Check this box if this account allows invoices & payments matching of journal items.")
    tax_ids = fields.Many2many('account.tax', 'account_account_tax_default_rel',
        'account_id', 'tax_id', string='Default Taxes')
    note = fields.Text('Internal Notes')
    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env['res.company']._company_default_get('account.account'))
    tag_ids = fields.Many2many('account.account.tag', 'account_account_account_tag', string='Tags', help="Optional tags you may want to assign for custom reporting")

    _sql_constraints = [
        ('code_company_uniq', 'unique (code,company_id)', 'The code of the account must be unique per company !')
    ]

    @api.model
    def default_get(self, default_fields):
        """If we're creating a new account through a many2one, there are chances that we typed the account code
        instead of its name. In that case, switch both fields values.
        """
        default_name = self._context.get('default_name')
        default_code = self._context.get('default_code')
        if default_name and not default_code:
            try:
                default_code = int(default_name)
            except ValueError:
                pass
            if default_code:
                default_name = False
        contextual_self = self.with_context(default_name=default_name, default_code=default_code)
        return super(AccountAccount, contextual_self).default_get(default_fields)

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', '=ilike', name + '%'), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        accounts = self.search(domain + args, limit=limit)
        return accounts.name_get()

    @api.onchange('internal_type')
    def onchange_internal_type(self):
        if self.internal_type in ('receivable', 'payable'):
            self.reconcile = True

    @api.multi
    @api.depends('name', 'code')
    def name_get(self):
        result = []
        for account in self:
            name = account.code + ' ' + account.name
            result.append((account.id, name))
        return result

    @api.one
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        default.setdefault('code', _("%s (copy)") % (self.code or ''))
        return super(AccountAccount, self).copy(default)

    @api.multi
    def write(self, vals):
        # Dont allow changing the company_id when account_move_line already exist
        if vals.get('company_id', False):
            move_lines = self.env['account.move.line'].search([('account_id', 'in', self.ids)], limit=1)
            for account in self:
                if (account.company_id.id != vals['company_id']) and move_lines:
                    raise UserError(_('You cannot change the owner company of an account that already contains journal items.'))
        # If user change the reconcile flag, all aml should be recomputed for that account and this is very costly.
        # So to prevent some bugs we add a constraint saying that you cannot change the reconcile field if there is any aml existing
        # for that account.
        if vals.get('reconcile'):
            move_lines = self.env['account.move.line'].search([('account_id', 'in', self.ids)], limit=1)
            if len(move_lines):
                raise UserError(_('You cannot change the value of the reconciliation on this account as it already has some moves'))
        return super(AccountAccount, self).write(vals)

    @api.multi
    def unlink(self):
        if self.env['account.move.line'].search([('account_id', 'in', self.ids)], limit=1):
            raise UserError(_('You cannot do that on an account that contains journal items.'))
        #Checking whether the account is set as a property to any Partner or not
        values = ['account.account,%s' % (account_id,) for account_id in self.ids]
        partner_prop_acc = self.env['ir.property'].search([('value_reference', 'in', values)], limit=1)
        if partner_prop_acc:
            raise UserError(_('You cannot remove/deactivate an account which is set on a customer or vendor.'))
        return super(AccountAccount, self).unlink()

    @api.multi
    def mark_as_reconciled(self):
        return self.write({'last_time_entries_checked': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})

    @api.multi
    def action_open_reconcile(self):
        self.ensure_one()
        # Open reconciliation view for this account
        if self.internal_type == 'payable':
            action_context = {'show_mode_selector': False, 'mode': 'suppliers'}
        elif self.internal_type == 'receivable':
            action_context = {'show_mode_selector': False, 'mode': 'customers'}
        else:
            action_context = {'show_mode_selector': False, 'account_ids': [self.id,]}
        return {
            'type': 'ir.actions.client',
            'tag': 'manual_reconciliation_view',
            'context': action_context,
        }


class AccountJournal(models.Model):
    _name = "account.journal"
    _description = "Journal"
    _order = 'sequence, type, code'

    def _default_inbound_payment_methods(self):
        return self.env.ref('account.account_payment_method_manual_in')

    def _default_outbound_payment_methods(self):
        return self.env.ref('account.account_payment_method_manual_out')

    name = fields.Char(string='Journal Name', required=True)
    code = fields.Char(string='Short Code', size=5, required=True, help="The journal entries of this journal will be named using this prefix.")
    type = fields.Selection([
            ('sale', 'Sale'),
            ('purchase', 'Purchase'),
            ('cash', 'Cash'),
            ('bank', 'Bank'),
            ('general', 'Miscellaneous'),
        ], required=True,
        help="Select 'Sale' for customer invoices journals.\n"\
        "Select 'Purchase' for vendor bills journals.\n"\
        "Select 'Cash' or 'Bank' for journals that are used in customer or vendor payments.\n"\
        "Select 'General' for miscellaneous operations journals.")
    type_control_ids = fields.Many2many('account.account.type', 'account_journal_type_rel', 'journal_id', 'type_id', string='Account Types Allowed')
    account_control_ids = fields.Many2many('account.account', 'account_account_type_rel', 'journal_id', 'account_id', string='Accounts Allowed',
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
    sequence = fields.Integer(help='Used to order Journals in the dashboard view', default=10)

    #groups_id = fields.Many2many('res.groups', 'account_journal_group_rel', 'journal_id', 'group_id', string='Groups')
    currency_id = fields.Many2one('res.currency', help='The currency used to enter statement', string="Currency", oldname='currency')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.user.company_id,
        help="Company related to this journal")

    refund_sequence = fields.Boolean(string='Dedicated Refund Sequence', help="Check this box if you don't want to share the same sequence for invoices and refunds made from this journal", default=False)

    inbound_payment_method_ids = fields.Many2many('account.payment.method', 'account_journal_inbound_payment_method_rel', 'journal_id', 'inbound_payment_method',
        domain=[('payment_type', '=', 'inbound')], string='Debit Methods', default=lambda self: self._default_inbound_payment_methods(),
        help="Means of payment for collecting money. Odoo modules offer various payments handling facilities, "
             "but you can always use the 'Manual' payment method in order to manage payments outside of the software.")
    outbound_payment_method_ids = fields.Many2many('account.payment.method', 'account_journal_outbound_payment_method_rel', 'journal_id', 'outbound_payment_method',
        domain=[('payment_type', '=', 'outbound')], string='Payment Methods', default=lambda self: self._default_outbound_payment_methods(),
        help="Means of payment for sending money. Odoo modules offer various payments handling facilities, "
             "but you can always use the 'Manual' payment method in order to manage payments outside of the software.")
    at_least_one_inbound = fields.Boolean(compute='_methods_compute', store=True)
    at_least_one_outbound = fields.Boolean(compute='_methods_compute', store=True)
    profit_account_id = fields.Many2one('account.account', string='Profit Account', domain=[('deprecated', '=', False)], help="Used to register a profit when the ending balance of a cash register differs from what the system computes")
    loss_account_id = fields.Many2one('account.account', string='Loss Account', domain=[('deprecated', '=', False)], help="Used to register a loss when the ending balance of a cash register differs from what the system computes")

    belongs_to_company = fields.Boolean('Belong to the user\'s current company', compute="_belong_to_company", search="_search_company_journals",)

    # Bank journals fields
    bank_account_id = fields.Many2one('res.partner.bank', string="Bank Account", ondelete='restrict', copy=False)
    bank_statements_source = fields.Selection([('undefined', 'Undefined Yet'),('manual', 'Record Manually')], string='Bank Feeds', default='undefined')
    bank_acc_number = fields.Char(related='bank_account_id.acc_number')
    bank_id = fields.Many2one('res.bank', related='bank_account_id.bank_id')

    _sql_constraints = [
        ('code_company_uniq', 'unique (code, name, company_id)', 'The code and name of the journal must be unique per company !'),
    ]

    @api.one
    @api.constrains('currency_id', 'default_credit_account_id', 'default_debit_account_id')
    def _check_currency(self):
        if self.currency_id:
            if self.default_credit_account_id and not self.default_credit_account_id.currency_id.id == self.currency_id.id:
                raise ValidationError(_('Configuration error!\nThe currency of the journal should be the same than the default credit account.'))
            if self.default_debit_account_id and not self.default_debit_account_id.currency_id.id == self.currency_id.id:
                raise ValidationError(_('Configuration error!\nThe currency of the journal should be the same than the default debit account.'))

    @api.one
    @api.constrains('type', 'bank_account_id')
    def _check_bank_account(self):
        if self.type == 'bank' and self.bank_account_id:
            if self.bank_account_id.company_id != self.company_id:
                raise ValidationError(_('The bank account of a bank journal must belong to the same company (%s).') % self.company_id.name)
            # A bank account can belong to a customer/supplier, in which case their partner_id is the customer/supplier.
            # Or they are part of a bank journal and their partner_id must be the company's partner_id.
            if self.bank_account_id.partner_id != self.company_id.partner_id:
                raise ValidationError(_('The holder of a journal\'s bank account must be the company (%s).') % self.company_id.name)

    @api.onchange('default_debit_account_id')
    def onchange_debit_account_id(self):
        if not self.default_credit_account_id:
            self.default_credit_account_id = self.default_debit_account_id

    @api.onchange('default_credit_account_id')
    def onchange_credit_account_id(self):
        if not self.default_debit_account_id:
            self.default_debit_account_id = self.default_credit_account_id

    @api.multi
    def unlink(self):
        bank_accounts = self.env['res.partner.bank'].browse()
        for bank_account in self.mapped('bank_account_id'):
            accounts = self.search([('bank_account_id', '=', bank_account.id)])
            if accounts <= self:
                bank_accounts += bank_account
        ret = super(AccountJournal, self).unlink()
        bank_accounts.unlink()
        return ret

    @api.one
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        default.update(
            code=_("%s (copy)") % (self.code or ''),
            name=_("%s (copy)") % (self.name or ''))
        return super(AccountJournal, self).copy(default)

    @api.multi
    def write(self, vals):
        for journal in self:
            if ('company_id' in vals and journal.company_id.id != vals['company_id']):
                if self.env['account.move'].search([('journal_id', 'in', self.ids)], limit=1):
                    raise UserError(_('This journal already contains items, therefore you cannot modify its company.'))
            if ('code' in vals and journal.code != vals['code']):
                if self.env['account.move'].search([('journal_id', 'in', self.ids)], limit=1):
                    raise UserError(_('This journal already contains items, therefore you cannot modify its short name.'))
                new_prefix = self._get_sequence_prefix(vals['code'], refund=False)
                journal.sequence_id.write({'prefix': new_prefix})
                if journal.refund_sequence_id:
                    new_prefix = self._get_sequence_prefix(vals['code'], refund=True)
                    journal.refund_sequence_id.write({'prefix': new_prefix})
            if 'currency_id' in vals:
                if not 'default_debit_account_id' in vals and self.default_debit_account_id:
                    self.default_debit_account_id.currency_id = vals['currency_id']
                if not 'default_credit_account_id' in vals and self.default_credit_account_id:
                    self.default_credit_account_id.currency_id = vals['currency_id']
            if 'bank_acc_number' in vals and not vals.get('bank_acc_number') and journal.bank_account_id:
                raise UserError(_('You cannot empty the account number once set.\nIf you would like to delete the account number, you can do it from the Bank Accounts list.'))
        result = super(AccountJournal, self).write(vals)

        # Create the bank_account_id if necessary
        if 'bank_acc_number' in vals:
            for journal in self.filtered(lambda r: r.type == 'bank' and not r.bank_account_id):
                journal.set_bank_account(vals.get('bank_acc_number'), vals.get('bank_id'))
        # create the relevant refund sequence
        if vals.get('refund_sequence'):
            for journal in self.filtered(lambda j: j.type in ('sale', 'purchase') and not j.refund_sequence_id):
                journal_vals = {
                    'name': journal.name,
                    'company_id': journal.company_id.id,
                    'code': journal.code
                }
                journal.refund_sequence_id = self.sudo()._create_sequence(journal_vals, refund=True).id

        return result

    @api.model
    def _get_sequence_prefix(self, code, refund=False):
        prefix = code.upper()
        if refund:
            prefix = 'R' + prefix
        return prefix + '/%(range_year)s/'

    @api.model
    def _create_sequence(self, vals, refund=False):
        """ Create new no_gap entry sequence for every new Journal"""
        prefix = self._get_sequence_prefix(vals['code'], refund)
        seq = {
            'name': refund and vals['name'] + _(': Refund') or vals['name'],
            'implementation': 'no_gap',
            'prefix': prefix,
            'padding': 4,
            'number_increment': 1,
            'use_date_range': True,
        }
        if 'company_id' in vals:
            seq['company_id'] = vals['company_id']
        return self.env['ir.sequence'].create(seq)

    @api.model
    def _prepare_liquidity_account(self, name, company, currency_id, type):
        '''
        This function prepares the value to use for the creation of the default debit and credit accounts of a
        liquidity journal (created through the wizard of generating COA from templates for example).

        :param name: name of the bank account
        :param company: company for which the wizard is running
        :param currency_id: ID of the currency in wich is the bank account
        :param type: either 'cash' or 'bank'
        :return: mapping of field names and values
        :rtype: dict
        '''

        # Seek the next available number for the account code
        code_digits = company.accounts_code_digits or 0
        if type == 'bank':
            account_code_prefix = company.bank_account_code_prefix or ''
        else:
            account_code_prefix = company.cash_account_code_prefix or company.bank_account_code_prefix or ''
        for num in xrange(1, 100):
            new_code = str(account_code_prefix.ljust(code_digits - 1, '0')) + str(num)
            rec = self.env['account.account'].search([('code', '=', new_code), ('company_id', '=', company.id)], limit=1)
            if not rec:
                break
        else:
            raise UserError(_('Cannot generate an unused account code.'))

        liquidity_type = self.env.ref('account.data_account_type_liquidity')
        return {
                'name': name,
                'currency_id': currency_id or False,
                'code': new_code,
                'user_type_id': liquidity_type and liquidity_type.id or False,
                'company_id': company.id,
        }

    @api.model
    def create(self, vals):
        company_id = vals.get('company_id', self.env.user.company_id.id)
        if vals.get('type') in ('bank', 'cash'):
            # For convenience, the name can be inferred from account number
            if not vals.get('name') and 'bank_acc_number' in vals:
                vals['name'] = vals['bank_acc_number']

            # If no code provided, loop to find next available journal code
            if not vals.get('code'):
                journal_code_base = (vals['type'] == 'cash' and 'CSH' or 'BNK')
                journals = self.env['account.journal'].search([('code', 'like', journal_code_base + '%'), ('company_id', '=', company_id)])
                for num in xrange(1, 100):
                    # journal_code has a maximal size of 5, hence we can enforce the boundary num < 100
                    journal_code = journal_code_base + str(num)
                    if journal_code not in journals.mapped('code'):
                        vals['code'] = journal_code
                        break
                else:
                    raise UserError(_("Cannot generate an unused journal code. Please fill the 'Shortcode' field."))

            # Create a default debit/credit account if not given
            default_account = vals.get('default_debit_account_id') or vals.get('default_credit_account_id')
            if not default_account:
                company = self.env['res.company'].browse(company_id)
                account_vals = self._prepare_liquidity_account(vals.get('name'), company, vals.get('currency_id'), vals.get('type'))
                default_account = self.env['account.account'].create(account_vals)
                vals['default_debit_account_id'] = default_account.id
                vals['default_credit_account_id'] = default_account.id

        # We just need to create the relevant sequences according to the chosen options
        if not vals.get('sequence_id'):
            vals.update({'sequence_id': self.sudo()._create_sequence(vals).id})
        if vals.get('type') in ('sale', 'purchase') and vals.get('refund_sequence') and not vals.get('refund_sequence_id'):
            vals.update({'refund_sequence_id': self.sudo()._create_sequence(vals, refund=True).id})

        journal = super(AccountJournal, self).create(vals)

        # Create the bank_account_id if necessary
        if journal.type == 'bank' and not journal.bank_account_id and vals.get('bank_acc_number'):
            journal.set_bank_account(vals.get('bank_acc_number'), vals.get('bank_id'))

        return journal

    def set_bank_account(self, acc_number, bank_id=None):
        """ Create a res.partner.bank and set it as value of the  field bank_account_id """
        self.ensure_one()
        self.bank_account_id = self.env['res.partner.bank'].create({
            'acc_number': acc_number,
            'bank_id': bank_id,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'partner_id': self.company_id.partner_id.id,
        }).id

    @api.multi
    @api.depends('name', 'currency_id', 'company_id', 'company_id.currency_id')
    def name_get(self):
        res = []
        for journal in self:
            currency = journal.currency_id or journal.company_id.currency_id
            name = "%s (%s)" % (journal.name, currency.name)
            res += [(journal.id, name)]
        return res

    @api.multi
    @api.depends('company_id')
    def _belong_to_company(self):
        for journal in self:
            journal.belong_to_company = (journal.company_id.id == self.env.user.company_id.id)

    @api.multi
    def _search_company_journals(self, operator, value):
        if value:
            recs = self.search([('company_id', operator, self.env.user.company_id.id)])
        elif operator == '=':
            recs = self.search([('company_id', '!=', self.env.user.company_id.id)])
        else:
            recs = self.search([('company_id', operator, self.env.user.company_id.id)])
        return [('id', 'in', [x.id for x in recs])]

    @api.multi
    @api.depends('inbound_payment_method_ids', 'outbound_payment_method_ids')
    def _methods_compute(self):
        for journal in self:
            journal.at_least_one_inbound = bool(len(journal.inbound_payment_method_ids))
            journal.at_least_one_outbound = bool(len(journal.outbound_payment_method_ids))


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    journal_id = fields.One2many('account.journal', 'bank_account_id', domain=[('type', '=', 'bank')], string='Account Journal', readonly=True,
        help="The accounting journal corresponding to this bank account.")

    @api.one
    @api.constrains('journal_id')
    def _check_journal_id(self):
        if len(self.journal_id) > 1:
            raise ValidationError(_('A bank account can only belong to one journal.'))


#----------------------------------------------------------
# Tax
#----------------------------------------------------------

class AccountTaxGroup(models.Model):
    _name = 'account.tax.group'
    _order = 'sequence asc'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)

class AccountTax(models.Model):
    _name = 'account.tax'
    _description = 'Tax'
    _order = 'sequence'

    @api.model
    def _default_tax_group(self):
        return self.env['account.tax.group'].search([], limit=1)

    name = fields.Char(string='Tax Name', required=True, translate=True)
    type_tax_use = fields.Selection([('sale', 'Sales'), ('purchase', 'Purchases'), ('none', 'None')], string='Tax Scope', required=True, default="sale",
        help="Determines where the tax is selectable. Note : 'None' means a tax can't be used by itself, however it can still be used in a group.")
    tax_adjustment = fields.Boolean(help='Set this field to true if this tax can be used in the tax adjustment wizard, used to manually fill some data in the tax declaration')
    amount_type = fields.Selection(default='percent', string="Tax Computation", required=True, oldname='type',
        selection=[('group', 'Group of Taxes'), ('fixed', 'Fixed'), ('percent', 'Percentage of Price'), ('division', 'Percentage of Price Tax Included')])
    active = fields.Boolean(default=True, help="Set active to false to hide the tax without removing it.")
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    children_tax_ids = fields.Many2many('account.tax', 'account_tax_filiation_rel', 'parent_tax', 'child_tax', string='Children Taxes')
    sequence = fields.Integer(required=True, default=1,
        help="The sequence field is used to define order in which the tax lines are applied.")
    amount = fields.Float(required=True, digits=(16, 4))
    account_id = fields.Many2one('account.account', domain=[('deprecated', '=', False)], string='Tax Account', ondelete='restrict',
        help="Account that will be set on invoice tax lines for invoices. Leave empty to use the expense account.", oldname='account_collected_id')
    refund_account_id = fields.Many2one('account.account', domain=[('deprecated', '=', False)], string='Tax Account on Refunds', ondelete='restrict',
        help="Account that will be set on invoice tax lines for refunds. Leave empty to use the expense account.", oldname='account_paid_id')
    description = fields.Char(string='Label on Invoices', translate=True)
    price_include = fields.Boolean(string='Included in Price', default=False,
        help="Check this if the price you use on the product and invoices includes this tax.")
    include_base_amount = fields.Boolean(string='Affect Base of Subsequent Taxes', default=False,
        help="If set, taxes which are computed after this one will be computed based on the price tax included.")
    analytic = fields.Boolean(string="Include in Analytic Cost", help="If set, the amount computed by this tax will be assigned to the same analytic account as the invoice line (if any)")
    tag_ids = fields.Many2many('account.account.tag', 'account_tax_account_tag', string='Tags', help="Optional tags you may want to assign for custom reporting")
    tax_group_id = fields.Many2one('account.tax.group', string="Tax Group", default=_default_tax_group, required=True)
    use_cash_basis = fields.Boolean(
        'Use Cash Basis',
        help="Select this if the tax should use cash basis,"
        "which will create an entry for this tax on a given account during reconciliation")
    cash_basis_account = fields.Many2one(
        'account.account',
        string='Tax Received Account',
        domain=[('deprecated', '=', False)],
        help='Account use when creating entry for tax cash basis')

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id, type_tax_use)', 'Tax names must be unique !'),
    ]

    @api.multi
    def unlink(self):
        company_id = self.env.user.company_id.id
        ir_values = self.env['ir.values']
        supplier_taxes_id = set(ir_values.get_default('product.template', 'supplier_taxes_id', company_id=company_id) or [])
        deleted_sup_tax = self.filtered(lambda tax: tax.id in supplier_taxes_id)
        if deleted_sup_tax:
            ir_values.sudo().set_default('product.template', "supplier_taxes_id", list(supplier_taxes_id - set(deleted_sup_tax.ids)), for_all_users=True, company_id=company_id)
        taxes_id = set(self.env['ir.values'].get_default('product.template', 'taxes_id', company_id=company_id) or [])
        deleted_tax = self.filtered(lambda tax: tax.id in taxes_id)
        if deleted_tax:
            ir_values.sudo().set_default('product.template', "taxes_id", list(taxes_id - set(deleted_tax.ids)), for_all_users=True, company_id=company_id)
        return super(AccountTax, self).unlink()

    @api.one
    @api.constrains('children_tax_ids', 'type_tax_use')
    def _check_children_scope(self):
        if not all(child.type_tax_use in ('none', self.type_tax_use) for child in self.children_tax_ids):
            raise ValidationError(_('The application scope of taxes in a group must be either the same as the group or "None".'))

    @api.one
    @api.returns('self', lambda value: value.id)
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

    @api.onchange('amount')
    def onchange_amount(self):
        if self.amount_type in ('percent', 'division') and self.amount != 0.0 and not self.description:
            self.description = "{0:.4g}%".format(self.amount)

    @api.onchange('account_id')
    def onchange_account_id(self):
        self.refund_account_id = self.account_id

    @api.onchange('price_include')
    def onchange_price_include(self):
        if self.price_include:
            self.include_base_amount = True

    def get_grouping_key(self, invoice_tax_val):
        """ Returns a string that will be used to group account.invoice.tax sharing the same properties"""
        self.ensure_one()
        return str(invoice_tax_val['tax_id']) + '-' + str(invoice_tax_val['account_id']) + '-' + str(invoice_tax_val['account_analytic_id'])

    def _compute_amount(self, base_amount, price_unit, quantity=1.0, product=None, partner=None):
        """ Returns the amount of a single tax. base_amount is the actual amount on which the tax is applied, which is
            price_unit * quantity eventually affected by previous taxes (if tax is include_base_amount XOR price_include)
        """
        self.ensure_one()
        if self.amount_type == 'fixed':
            # Use copysign to take into account the sign of the base amount which includes the sign
            # of the quantity and the sign of the price_unit
            # Amount is the fixed price for the tax, it can be negative
            # Base amount included the sign of the quantity and the sign of the unit price and when
            # a product is returned, it can be done either by changing the sign of quantity or by changing the
            # sign of the price unit.
            # When the price unit is equal to 0, the sign of the quantity is absorbed in base_amount then
            # a "else" case is needed.
            if base_amount:
                return math.copysign(quantity, base_amount) * self.amount
            else:
                return quantity * self.amount
        if (self.amount_type == 'percent' and not self.price_include) or (self.amount_type == 'division' and self.price_include):
            return base_amount * self.amount / 100
        if self.amount_type == 'percent' and self.price_include:
            return base_amount - (base_amount / (1 + self.amount / 100))
        if self.amount_type == 'division' and not self.price_include:
            return base_amount / (1 - self.amount / 100) - base_amount

    @api.multi
    def json_friendly_compute_all(self, price_unit, currency_id=None, quantity=1.0, product_id=None, partner_id=None):
        """ Just converts parameters in browse records and calls for compute_all, because js widgets can't serialize browse records """
        if currency_id:
            currency_id = self.env['res.currency'].browse(currency_id)
        if product_id:
            product_id = self.env['product.product'].browse(product_id)
        if partner_id:
            partner_id = self.env['res.partner'].browse(partner_id)
        return self.compute_all(price_unit, currency=currency_id, quantity=quantity, product=product_id, partner=partner_id)

    @api.multi
    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None):
        """ Returns all information required to apply taxes (in self + their children in case of a tax goup).
            We consider the sequence of the parent for group of taxes.
                Eg. considering letters as taxes and alphabetic order as sequence :
                [G, B([A, D, F]), E, C] will be computed as [A, D, F, C, E, G]

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
        if len(self) == 0:
            company_id = self.env.user.company_id
        else:
            company_id = self[0].company_id
        if not currency:
            currency = company_id.currency_id
        taxes = []
        # By default, for each tax, tax amount will first be computed
        # and rounded at the 'Account' decimal precision for each
        # PO/SO/invoice line and then these rounded amounts will be
        # summed, leading to the total amount for that tax. But, if the
        # company has tax_calculation_rounding_method = round_globally,
        # we still follow the same method, but we use a much larger
        # precision when we round the tax amount for each line (we use
        # the 'Account' decimal precision + 5), and that way it's like
        # rounding after the sum of the tax amounts of each line
        prec = currency.decimal_places

        # In some cases, it is necessary to force/prevent the rounding of the tax and the total
        # amounts. For example, in SO/PO line, we don't want to round the price unit at the
        # precision of the currency.
        # The context key 'round' allows to force the standard behavior.
        round_tax = False if company_id.tax_calculation_rounding_method == 'round_globally' else True
        round_total = True
        if 'round' in self.env.context:
            round_tax = bool(self.env.context['round'])
            round_total = bool(self.env.context['round'])

        if not round_tax:
            prec += 5

        base_values = self.env.context.get('base_values')
        if not base_values:
            total_excluded = total_included = base = round(price_unit * quantity, prec)
        else:
            total_excluded, total_included, base = base_values

        # Sorting key is mandatory in this case. When no key is provided, sorted() will perform a
        # search. However, the search method is overridden in account.tax in order to add a domain
        # depending on the context. This domain might filter out some taxes from self, e.g. in the
        # case of group taxes.
        for tax in self.sorted(key=lambda r: r.sequence):
            if tax.amount_type == 'group':
                children = tax.children_tax_ids.with_context(base_values=(total_excluded, total_included, base))
                ret = children.compute_all(price_unit, currency, quantity, product, partner)
                total_excluded = ret['total_excluded']
                base = ret['base'] if tax.include_base_amount else base
                total_included = ret['total_included']
                tax_amount = total_included - total_excluded
                taxes += ret['taxes']
                continue

            tax_amount = tax._compute_amount(base, price_unit, quantity, product, partner)
            if not round_tax:
                tax_amount = round(tax_amount, prec)
            else:
                tax_amount = currency.round(tax_amount)

            if tax.price_include:
                total_excluded -= tax_amount
                base -= tax_amount
            else:
                total_included += tax_amount

            # Keep base amount used for the current tax
            tax_base = base

            if tax.include_base_amount:
                base += tax_amount

            taxes.append({
                'id': tax.id,
                'name': tax.with_context(**{'lang': partner.lang} if partner else {}).name,
                'amount': tax_amount,
                'base': tax_base,
                'sequence': tax.sequence,
                'account_id': tax.account_id.id,
                'refund_account_id': tax.refund_account_id.id,
                'analytic': tax.analytic,
            })

        return {
            'taxes': sorted(taxes, key=lambda k: k['sequence']),
            'total_excluded': currency.round(total_excluded) if round_total else total_excluded,
            'total_included': currency.round(total_included) if round_total else total_included,
            'base': base,
        }

    @api.model
    def _fix_tax_included_price(self, price, prod_taxes, line_taxes):
        """Subtract tax amount from price when corresponding "price included" taxes do not apply"""
        # FIXME get currency in param?
        incl_tax = prod_taxes.filtered(lambda tax: tax not in line_taxes and tax.price_include)
        if incl_tax:
            return incl_tax.compute_all(price)['total_excluded']
        return price

class AccountReconcileModel(models.Model):
    _name = "account.reconcile.model"
    _description = "Preset to create journal entries during a invoices and payments matching"

    name = fields.Char(string='Button Label', required=True)
    sequence = fields.Integer(required=True, default=10)
    has_second_line = fields.Boolean(string='Add a second line', default=False)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)

    account_id = fields.Many2one('account.account', string='Account', ondelete='cascade', domain=[('deprecated', '=', False)])
    journal_id = fields.Many2one('account.journal', string='Journal', ondelete='cascade', help="This field is ignored in a bank statement reconciliation.")
    label = fields.Char(string='Journal Item Label')
    amount_type = fields.Selection([
        ('fixed', 'Fixed'),
        ('percentage', 'Percentage of balance')
        ], required=True, default='percentage')
    amount = fields.Float(digits=0, required=True, default=100.0, help="Fixed amount will count as a debit if it is negative, as a credit if it is positive.")
    tax_id = fields.Many2one('account.tax', string='Tax', ondelete='restrict', domain=[('type_tax_use', '=', 'purchase')])
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', ondelete='set null')

    second_account_id = fields.Many2one('account.account', string='Second Account', ondelete='cascade', domain=[('deprecated', '=', False)])
    second_journal_id = fields.Many2one('account.journal', string='Second Journal', ondelete='cascade', help="This field is ignored in a bank statement reconciliation.")
    second_label = fields.Char(string='Second Journal Item Label')
    second_amount_type = fields.Selection([
        ('fixed', 'Fixed'),
        ('percentage', 'Percentage of amount')
        ], string="Second Amount type",required=True, default='percentage')
    second_amount = fields.Float(string='Second Amount', digits=0, required=True, default=100.0, help="Fixed amount will count as a debit if it is negative, as a credit if it is positive.")
    second_tax_id = fields.Many2one('account.tax', string='Second Tax', ondelete='restrict', domain=[('type_tax_use', '=', 'purchase')])
    second_analytic_account_id = fields.Many2one('account.analytic.account', string='Second Analytic Account', ondelete='set null')

    @api.onchange('name')
    def onchange_name(self):
        self.label = self.name
