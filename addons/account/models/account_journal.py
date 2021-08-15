# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
from odoo.addons.base.models.res_bank import sanitize_account_number
from odoo.tools import remove_accents
import logging
import re

_logger = logging.getLogger(__name__)


class AccountJournalGroup(models.Model):
    _name = 'account.journal.group'
    _description = "Account Journal Group"
    _check_company_auto = True

    name = fields.Char("Journal Group", required=True, translate=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    excluded_journal_ids = fields.Many2many('account.journal', string="Excluded Journals", domain="[('company_id', '=', company_id)]",
        check_company=True)
    sequence = fields.Integer(default=10)


class AccountJournal(models.Model):
    _name = "account.journal"
    _description = "Journal"
    _order = 'sequence, type, code'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _check_company_auto = True

    def _default_inbound_payment_methods(self):
        return self.env.ref('account.account_payment_method_manual_in')

    def _default_outbound_payment_methods(self):
        return self.env.ref('account.account_payment_method_manual_out')

    def __get_bank_statements_available_sources(self):
        return [('undefined', _('Undefined Yet'))]

    def _get_bank_statements_available_sources(self):
        return self.__get_bank_statements_available_sources()

    def _default_alias_domain(self):
        return self.env["ir.config_parameter"].sudo().get_param("mail.catchall.domain")
    
    def _default_invoice_reference_model(self):
        """Get the invoice reference model according to the company's country."""
        country_code = self.env.company.country_id.code
        country_code = country_code and country_code.lower()
        if country_code:
            for model in self._fields['invoice_reference_model'].get_values(self.env):
                if model.startswith(country_code):
                    return model
        return 'odoo'

    name = fields.Char(string='Journal Name', required=True)
    code = fields.Char(string='Short Code', size=5, required=True, help="Shorter name used for display. The journal entries of this journal will also be named using this prefix by default.")
    active = fields.Boolean(default=True, help="Set active to false to hide the Journal without removing it.")
    type = fields.Selection([
            ('sale', 'Sales'),
            ('purchase', 'Purchase'),
            ('cash', 'Cash'),
            ('bank', 'Bank'),
            ('general', 'Miscellaneous'),
        ], required=True,
        help="Select 'Sale' for customer invoices journals.\n"\
        "Select 'Purchase' for vendor bills journals.\n"\
        "Select 'Cash' or 'Bank' for journals that are used in customer or vendor payments.\n"\
        "Select 'General' for miscellaneous operations journals.")
    type_control_ids = fields.Many2many('account.account.type', 'journal_account_type_control_rel', 'journal_id', 'type_id', string='Allowed account types')
    account_control_ids = fields.Many2many('account.account', 'journal_account_control_rel', 'journal_id', 'account_id', string='Allowed accounts',
        check_company=True,
        domain="[('deprecated', '=', False), ('company_id', '=', company_id), ('is_off_balance', '=', False)]")
    default_account_type = fields.Many2one('account.account.type', compute="_compute_default_account_type")
    default_account_id = fields.Many2one(
        comodel_name='account.account', check_company=True, copy=False, ondelete='restrict',
        string='Default Account',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id),"
               "'|', ('user_type_id', '=', default_account_type), ('user_type_id', 'in', type_control_ids),"
               "('user_type_id.type', 'not in', ('receivable', 'payable'))]")
    payment_debit_account_id = fields.Many2one(
        comodel_name='account.account', check_company=True, copy=False, ondelete='restrict',
        help="Incoming payments entries triggered by invoices/refunds will be posted on the Outstanding Receipts Account "
             "and displayed as blue lines in the bank reconciliation widget. During the reconciliation process, concerned "
             "transactions will be reconciled with entries on the Outstanding Receipts Account instead of the "
             "receivable account.", string='Outstanding Receipts Account',
        domain=lambda self: "[('deprecated', '=', False), ('company_id', '=', company_id), \
                             ('user_type_id.type', 'not in', ('receivable', 'payable')), \
                             '|', ('user_type_id', '=', %s), ('id', '=', default_account_id)]" % self.env.ref('account.data_account_type_current_assets').id)
    payment_credit_account_id = fields.Many2one(
        comodel_name='account.account', check_company=True, copy=False, ondelete='restrict',
        help="Outgoing payments entries triggered by bills/credit notes will be posted on the Outstanding Payments Account "
             "and displayed as blue lines in the bank reconciliation widget. During the reconciliation process, concerned "
             "transactions will be reconciled with entries on the Outstanding Payments Account instead of the "
             "payable account.", string='Outstanding Payments Account',
        domain=lambda self: "[('deprecated', '=', False), ('company_id', '=', company_id), \
                             ('user_type_id.type', 'not in', ('receivable', 'payable')), \
                             '|', ('user_type_id', '=', %s), ('id', '=', default_account_id)]" % self.env.ref('account.data_account_type_current_assets').id)
    suspense_account_id = fields.Many2one(
        comodel_name='account.account', check_company=True, ondelete='restrict', readonly=False, store=True,
        compute='_compute_suspense_account_id',
        help="Bank statements transactions will be posted on the suspense account until the final reconciliation "
             "allowing finding the right account.", string='Suspense Account',
        domain=lambda self: "[('deprecated', '=', False), ('company_id', '=', company_id), \
                             ('user_type_id.type', 'not in', ('receivable', 'payable')), \
                             ('user_type_id', '=', %s)]" % self.env.ref('account.data_account_type_current_liabilities').id)
    restrict_mode_hash_table = fields.Boolean(string="Lock Posted Entries with Hash",
        help="If ticked, the accounting entry or invoice receives a hash as soon as it is posted and cannot be modified anymore.")
    sequence = fields.Integer(help='Used to order Journals in the dashboard view', default=10)

    invoice_reference_type = fields.Selection(string='Communication Type', required=True, selection=[('none', 'Free'), ('partner', 'Based on Customer'), ('invoice', 'Based on Invoice')], default='invoice', help='You can set here the default communication that will appear on customer invoices, once validated, to help the customer to refer to that particular invoice when making the payment.')
    invoice_reference_model = fields.Selection(string='Communication Standard', required=True, selection=[('odoo', 'Odoo'),('euro', 'European')], default=_default_invoice_reference_model, help="You can choose different models for each type of reference. The default one is the Odoo reference.")

    #groups_id = fields.Many2many('res.groups', 'account_journal_group_rel', 'journal_id', 'group_id', string='Groups')
    currency_id = fields.Many2one('res.currency', help='The currency used to enter statement', string="Currency")
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, index=True, default=lambda self: self.env.company,
        help="Company related to this journal")
    country_code = fields.Char(related='company_id.country_id.code', readonly=True)

    refund_sequence = fields.Boolean(string='Dedicated Credit Note Sequence', help="Check this box if you don't want to share the same sequence for invoices and credit notes made from this journal", default=False)
    sequence_override_regex = fields.Text(help="Technical field used to enforce complex sequence composition that the system would normally misunderstand.\n"\
                                          "This is a regex that can include all the following capture groups: prefix1, year, prefix2, month, prefix3, seq, suffix.\n"\
                                          "The prefix* groups are the separators between the year, month and the actual increasing sequence number (seq).\n"\

                                          "e.g: ^(?P<prefix1>.*?)(?P<year>\d{4})(?P<prefix2>\D*?)(?P<month>\d{2})(?P<prefix3>\D+?)(?P<seq>\d+)(?P<suffix>\D*?)$")

    inbound_payment_method_ids = fields.Many2many(
        comodel_name='account.payment.method',
        relation='account_journal_inbound_payment_method_rel',
        column1='journal_id',
        column2='inbound_payment_method',
        domain=[('payment_type', '=', 'inbound')],
        string='Inbound Payment Methods',
        compute='_compute_inbound_payment_method_ids',
        store=True,
        readonly=False,
        help="Manual: Get paid by cash, check or any other method outside of Odoo.\n"
             "Electronic: Get paid automatically through a payment acquirer by requesting a transaction"
             " on a card saved by the customer when buying or subscribing online (payment token).\n"
             "Batch Deposit: Encase several customer checks at once by generating a batch deposit to"
             " submit to your bank. When encoding the bank statement in Odoo,you are suggested to"
             " reconcile the transaction with the batch deposit. Enable this option from the settings."
    )
    outbound_payment_method_ids = fields.Many2many(
        comodel_name='account.payment.method',
        relation='account_journal_outbound_payment_method_rel',
        column1='journal_id',
        column2='outbound_payment_method',
        domain=[('payment_type', '=', 'outbound')],
        string='Outbound Payment Methods',
        compute='_compute_outbound_payment_method_ids',
        store=True,
        readonly=False,
        help="Manual:Pay bill by cash or any other method outside of Odoo.\n"
             "Check:Pay bill by check and print it from Odoo.\n"
             "SEPA Credit Transfer: Pay bill from a SEPA Credit Transfer file you submit to your"
             " bank. Enable this option from the settings."
    )
    at_least_one_inbound = fields.Boolean(compute='_methods_compute', store=True)
    at_least_one_outbound = fields.Boolean(compute='_methods_compute', store=True)
    profit_account_id = fields.Many2one(
        comodel_name='account.account', check_company=True,
        help="Used to register a profit when the ending balance of a cash register differs from what the system computes",
        string='Profit Account',
        domain=lambda self: "[('deprecated', '=', False), ('company_id', '=', company_id), \
                             ('user_type_id.type', 'not in', ('receivable', 'payable')), \
                             ('user_type_id', 'in', %s)]" % [self.env.ref('account.data_account_type_revenue').id,
                                                             self.env.ref('account.data_account_type_other_income').id])
    loss_account_id = fields.Many2one(
        comodel_name='account.account', check_company=True,
        help="Used to register a loss when the ending balance of a cash register differs from what the system computes",
        string='Loss Account',
        domain=lambda self: "[('deprecated', '=', False), ('company_id', '=', company_id), \
                             ('user_type_id.type', 'not in', ('receivable', 'payable')), \
                             ('user_type_id', '=', %s)]" % self.env.ref('account.data_account_type_expenses').id)

    # Bank journals fields
    company_partner_id = fields.Many2one('res.partner', related='company_id.partner_id', string='Account Holder', readonly=True, store=False)
    bank_account_id = fields.Many2one('res.partner.bank',
        string="Bank Account",
        ondelete='restrict', copy=False,
        check_company=True,
        domain="[('partner_id','=', company_partner_id), '|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    bank_statements_source = fields.Selection(selection=_get_bank_statements_available_sources, string='Bank Feeds', default='undefined', help="Defines how the bank statements will be registered")
    bank_acc_number = fields.Char(related='bank_account_id.acc_number', readonly=False)
    bank_id = fields.Many2one('res.bank', related='bank_account_id.bank_id', readonly=False)

    # Sale journals fields
    sale_activity_type_id = fields.Many2one('mail.activity.type', string='Schedule Activity', default=False, help="Activity will be automatically scheduled on payment due date, improving collection process.")
    sale_activity_user_id = fields.Many2one('res.users', string="Activity User", help="Leave empty to assign the Salesperson of the invoice.")
    sale_activity_note = fields.Text('Activity Summary')

    # alias configuration for journals
    alias_id = fields.Many2one('mail.alias', string='Email Alias', help="Send one separate email for each invoice.\n\n"
                                                                  "Any file extension will be accepted.\n\n"
                                                                  "Only PDF and XML files will be interpreted by Odoo", copy=False)
    alias_domain = fields.Char('Alias domain', compute='_compute_alias_domain', default=_default_alias_domain, compute_sudo=True)
    alias_name = fields.Char('Alias Name', copy=False, related='alias_id.alias_name', help="It creates draft invoices and bills by sending an email.", readonly=False)

    journal_group_ids = fields.Many2many('account.journal.group',
        domain="[('company_id', '=', company_id)]",
        check_company=True,
        string="Journal Groups")

    secure_sequence_id = fields.Many2one('ir.sequence',
        help='Sequence to use to ensure the securisation of data',
        check_company=True,
        readonly=True, copy=False)

    _sql_constraints = [
        ('code_company_uniq', 'unique (code, name, company_id)', 'The code and name of the journal must be unique per company !'),
    ]

    @api.depends('type')
    def _compute_default_account_type(self):
        default_account_id_types = {
            'bank': 'account.data_account_type_liquidity',
            'cash': 'account.data_account_type_liquidity',
            'sale': 'account.data_account_type_revenue',
            'purchase': 'account.data_account_type_expenses'
        }

        for journal in self:
            if journal.type in default_account_id_types:
                journal.default_account_type = self.env.ref(default_account_id_types[journal.type]).id
            else:
                journal.default_account_type = False

    @api.depends('type')
    def _compute_outbound_payment_method_ids(self):
        for journal in self:
            if journal.type in ('bank', 'cash'):
                journal.outbound_payment_method_ids = self._default_outbound_payment_methods()
            else:
                journal.outbound_payment_method_ids = False

    @api.depends('type')
    def _compute_inbound_payment_method_ids(self):
        for journal in self:
            if journal.type in ('bank', 'cash'):
                journal.inbound_payment_method_ids = self._default_inbound_payment_methods()
            else:
                journal.inbound_payment_method_ids = False

    @api.depends('company_id', 'type')
    def _compute_suspense_account_id(self):
        for journal in self:
            if journal.type not in ('bank', 'cash'):
                journal.suspense_account_id = False
            elif journal.suspense_account_id:
                journal.suspense_account_id = journal.suspense_account_id
            elif journal.company_id.account_journal_suspense_account_id:
                journal.suspense_account_id = journal.company_id.account_journal_suspense_account_id
            else:
                journal.suspense_account_id = False

    def _compute_alias_domain(self):
        alias_domain = self._default_alias_domain()
        for record in self:
            record.alias_domain = alias_domain

    @api.constrains('type_control_ids')
    def _constrains_type_control_ids(self):
        self.env['account.move.line'].flush(['account_id', 'journal_id'])
        self.flush(['type_control_ids'])
        self._cr.execute("""
            SELECT aml.id
            FROM account_move_line aml
            WHERE aml.journal_id in (%s)
            AND EXISTS (SELECT 1 FROM journal_account_type_control_rel rel WHERE rel.journal_id = aml.journal_id)
            AND NOT EXISTS (SELECT 1 FROM account_account acc
                            JOIN journal_account_type_control_rel rel ON acc.user_type_id = rel.type_id
                            WHERE acc.id = aml.account_id AND rel.journal_id = aml.journal_id)
        """, tuple(self.ids))
        if self._cr.fetchone():
            raise ValidationError(_('Some journal items already exist in this journal but with accounts from different types than the allowed ones.'))

    @api.constrains('account_control_ids')
    def _constrains_account_control_ids(self):
        self.env['account.move.line'].flush(['account_id', 'journal_id'])
        self.flush(['account_control_ids'])
        self._cr.execute("""
            SELECT aml.id
            FROM account_move_line aml
            WHERE aml.journal_id in (%s)
            AND EXISTS (SELECT 1 FROM journal_account_control_rel rel WHERE rel.journal_id = aml.journal_id)
            AND NOT EXISTS (SELECT 1 FROM journal_account_control_rel rel WHERE rel.account_id = aml.account_id AND rel.journal_id = aml.journal_id)
        """, tuple(self.ids))
        if self._cr.fetchone():
            raise ValidationError(_('Some journal items already exist in this journal but with other accounts than the allowed ones.'))

    @api.constrains('type', 'bank_account_id')
    def _check_bank_account(self):
        for journal in self:
            if journal.type == 'bank' and journal.bank_account_id:
                if journal.bank_account_id.company_id and journal.bank_account_id.company_id != journal.company_id:
                    raise ValidationError(_('The bank account of a bank journal must belong to the same company (%s).', journal.company_id.name))
                # A bank account can belong to a customer/supplier, in which case their partner_id is the customer/supplier.
                # Or they are part of a bank journal and their partner_id must be the company's partner_id.
                if journal.bank_account_id.partner_id != journal.company_id.partner_id:
                    raise ValidationError(_('The holder of a journal\'s bank account must be the company (%s).', journal.company_id.name))

    @api.constrains('company_id')
    def _check_company_consistency(self):
        if not self:
            return

        self.flush(['company_id'])
        self._cr.execute('''
            SELECT move.id
            FROM account_move move
            JOIN account_journal journal ON journal.id = move.journal_id
            WHERE move.journal_id IN %s
            AND move.company_id != journal.company_id
        ''', [tuple(self.ids)])
        if self._cr.fetchone():
            raise UserError(_("You can't change the company of your journal since there are some journal entries linked to it."))

    @api.constrains('type', 'default_account_id')
    def _check_type_default_account_id_type(self):
        for journal in self:
            if journal.type in ('sale', 'purchase') and journal.default_account_id.user_type_id.type in ('receivable', 'payable'):
                raise ValidationError(_("The type of the journal's default credit/debit account shouldn't be 'receivable' or 'payable'."))

    @api.constrains('active')
    def _check_auto_post_draft_entries(self):
        for journal in self:
            pending_moves = self.env['account.move'].search([
                ('journal_id', '=', journal.id),
                ('state', '=', 'draft')
            ], limit=1)

            if pending_moves:
                raise ValidationError(_("You can not archive a journal containing draft journal entries.\n\n"
                                        "To proceed:\n"
                                        "1/ click on the top-right button 'Journal Entries' from this journal form\n"
                                        "2/ then filter on 'Draft' entries\n"
                                        "3/ select them all and post or delete them through the action menu"))

    @api.onchange('type')
    def _onchange_type(self):
        self.refund_sequence = self.type in ('sale', 'purchase')

    def _get_alias_values(self, type, alias_name=None):
        if not alias_name:
            alias_name = self.name
            if self.company_id != self.env.ref('base.main_company'):
                alias_name += '-' + str(self.company_id.name)
        try:
            remove_accents(alias_name).encode('ascii')
        except UnicodeEncodeError:
            try:
                remove_accents(self.code).encode('ascii')
                safe_alias_name = self.code
            except UnicodeEncodeError:
                safe_alias_name = self.type
            _logger.warning("Cannot use '%s' as email alias, fallback to '%s'",
                alias_name, safe_alias_name)
            alias_name = safe_alias_name
        return {
            'alias_defaults': {'move_type': type == 'purchase' and 'in_invoice' or 'out_invoice', 'company_id': self.company_id.id, 'journal_id': self.id},
            'alias_parent_thread_id': self.id,
            'alias_name': alias_name,
        }

    def unlink(self):
        bank_accounts = self.env['res.partner.bank'].browse()
        for bank_account in self.mapped('bank_account_id'):
            accounts = self.search([('bank_account_id', '=', bank_account.id)])
            if accounts <= self:
                bank_accounts += bank_account
        self.mapped('alias_id').sudo().unlink()
        ret = super(AccountJournal, self).unlink()
        bank_accounts.unlink()
        return ret

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        default.update(
            code=_("%s (copy)") % (self.code or ''),
            name=_("%s (copy)") % (self.name or ''))
        return super(AccountJournal, self).copy(default)

    def _update_mail_alias(self, vals):
        self.ensure_one()
        alias_values = self._get_alias_values(type=vals.get('type') or self.type, alias_name=vals.get('alias_name'))
        if self.alias_id:
            self.alias_id.sudo().write(alias_values)
        else:
            alias_values['alias_model_id'] = self.env['ir.model']._get('account.move').id
            alias_values['alias_parent_model_id'] = self.env['ir.model']._get('account.journal').id
            self.alias_id = self.env['mail.alias'].sudo().create(alias_values)

        if vals.get('alias_name'):
            # remove alias_name to avoid useless write on alias
            del(vals['alias_name'])

    def write(self, vals):
        for journal in self:
            company = journal.company_id
            if ('company_id' in vals and journal.company_id.id != vals['company_id']):
                if self.env['account.move'].search([('journal_id', '=', journal.id)], limit=1):
                    raise UserError(_('This journal already contains items, therefore you cannot modify its company.'))
                company = self.env['res.company'].browse(vals['company_id'])
                if journal.bank_account_id.company_id and journal.bank_account_id.company_id != company:
                    journal.bank_account_id.write({
                        'company_id': company.id,
                        'partner_id': company.partner_id.id,
                    })
            if 'currency_id' in vals:
                if journal.bank_account_id:
                    journal.bank_account_id.currency_id = vals['currency_id']
            if 'bank_account_id' in vals:
                if not vals.get('bank_account_id'):
                    raise UserError(_('You cannot remove the bank account from the journal once set.'))
                else:
                    bank_account = self.env['res.partner.bank'].browse(vals['bank_account_id'])
                    if bank_account.partner_id != company.partner_id:
                        raise UserError(_("The partners of the journal's company and the related bank account mismatch."))
            if 'alias_name' in vals:
                journal._update_mail_alias(vals)
            if 'restrict_mode_hash_table' in vals and not vals.get('restrict_mode_hash_table'):
                journal_entry = self.env['account.move'].search([('journal_id', '=', self.id), ('state', '=', 'posted'), ('secure_sequence_number', '!=', 0)], limit=1)
                if len(journal_entry) > 0:
                    field_string = self._fields['restrict_mode_hash_table'].get_description(self.env)['string']
                    raise UserError(_("You cannot modify the field %s of a journal that already has accounting entries.", field_string))
        result = super(AccountJournal, self).write(vals)

        # Ensure the liquidity accounts are sharing the same foreign currency.
        if 'currency_id' in vals:
            for journal in self.filtered(lambda journal: journal.type in ('bank', 'cash')):
                journal.default_account_id.currency_id = journal.currency_id

        # Create the bank_account_id if necessary
        if 'bank_acc_number' in vals:
            for journal in self.filtered(lambda r: r.type == 'bank' and not r.bank_account_id):
                journal.set_bank_account(vals.get('bank_acc_number'), vals.get('bank_id'))
        for record in self:
            if record.restrict_mode_hash_table and not record.secure_sequence_id:
                record._create_secure_sequence(['secure_sequence_id'])

        return result

    @api.model
    def get_next_bank_cash_default_code(self, journal_type, company):
        journal_code_base = (journal_type == 'cash' and 'CSH' or 'BNK')
        journals = self.env['account.journal'].search([('code', 'like', journal_code_base + '%'), ('company_id', '=', company.id)])
        for num in range(1, 100):
            # journal_code has a maximal size of 5, hence we can enforce the boundary num < 100
            journal_code = journal_code_base + str(num)
            if journal_code not in journals.mapped('code'):
                return journal_code

    @api.model
    def _prepare_liquidity_account_vals(self, company, code, vals):
        return {
            'name': vals.get('name'),
            'code': code,
            'user_type_id': self.env.ref('account.data_account_type_liquidity').id,
            'currency_id': vals.get('currency_id'),
            'company_id': company.id,
        }

    @api.model
    def _fill_missing_values(self, vals):
        journal_type = vals.get('type')

        # 'type' field is required.
        if not journal_type:
            return

        # === Fill missing company ===
        company = self.env['res.company'].browse(vals['company_id']) if vals.get('company_id') else self.env.company
        vals['company_id'] = company.id

        # Don't get the digits on 'chart_template_id' since the chart template could be a custom one.
        random_account = self.env['account.account'].search([('company_id', '=', company.id)], limit=1)
        digits = len(random_account.code) if random_account else 6

        liquidity_type = self.env.ref('account.data_account_type_liquidity')
        current_assets_type = self.env.ref('account.data_account_type_current_assets')

        if journal_type in ('bank', 'cash'):
            has_liquidity_accounts = vals.get('default_account_id')
            has_payment_accounts = vals.get('payment_debit_account_id') or vals.get('payment_credit_account_id')
            has_profit_account = vals.get('profit_account_id')
            has_loss_account = vals.get('loss_account_id')

            if journal_type == 'bank':
                liquidity_account_prefix = company.bank_account_code_prefix or ''
            else:
                liquidity_account_prefix = company.cash_account_code_prefix or company.bank_account_code_prefix or ''

            # === Fill missing name ===
            vals['name'] = vals.get('name') or vals.get('bank_acc_number')

            # === Fill missing code ===
            if 'code' not in vals:
                vals['code'] = self.get_next_bank_cash_default_code(journal_type, company)
                if not vals['code']:
                    raise UserError(_("Cannot generate an unused journal code. Please fill the 'Shortcode' field."))

            # === Fill missing accounts ===
            if not has_liquidity_accounts:
                default_account_code = self.env['account.account']._search_new_account_code(company, digits, liquidity_account_prefix)
                default_account_vals = self._prepare_liquidity_account_vals(company, default_account_code, vals)
                vals['default_account_id'] = self.env['account.account'].create(default_account_vals).id
            if not has_payment_accounts:
                vals['payment_debit_account_id'] = self.env['account.account'].create({
                    'name': _("Outstanding Receipts"),
                    'code': self.env['account.account']._search_new_account_code(company, digits, liquidity_account_prefix),
                    'reconcile': True,
                    'user_type_id': current_assets_type.id,
                    'company_id': company.id,
                }).id
                vals['payment_credit_account_id'] = self.env['account.account'].create({
                    'name': _("Outstanding Payments"),
                    'code': self.env['account.account']._search_new_account_code(company, digits, liquidity_account_prefix),
                    'reconcile': True,
                    'user_type_id': current_assets_type.id,
                    'company_id': company.id,
                }).id
            if journal_type == 'cash' and not has_profit_account:
                vals['profit_account_id'] = company.default_cash_difference_income_account_id.id
            if journal_type == 'cash' and not has_loss_account:
                vals['loss_account_id'] = company.default_cash_difference_expense_account_id.id

        # === Fill missing refund_sequence ===
        if 'refund_sequence' not in vals:
            vals['refund_sequence'] = vals['type'] in ('sale', 'purchase')

    @api.model
    def create(self, vals):
        # OVERRIDE
        self._fill_missing_values(vals)

        journal = super(AccountJournal, self.with_context(mail_create_nolog=True)).create(vals)

        if 'alias_name' in vals:
            journal._update_mail_alias(vals)

        # Create the bank_account_id if necessary
        if journal.type == 'bank' and not journal.bank_account_id and vals.get('bank_acc_number'):
            journal.set_bank_account(vals.get('bank_acc_number'), vals.get('bank_id'))

        return journal

    def set_bank_account(self, acc_number, bank_id=None):
        """ Create a res.partner.bank (if not exists) and set it as value of the field bank_account_id """
        self.ensure_one()
        res_partner_bank = self.env['res.partner.bank'].search([('sanitized_acc_number', '=', sanitize_account_number(acc_number)),
                                                                ('company_id', '=', self.company_id.id)], limit=1)
        if res_partner_bank:
            self.bank_account_id = res_partner_bank.id
        else:
            self.bank_account_id = self.env['res.partner.bank'].create({
                'acc_number': acc_number,
                'bank_id': bank_id,
                'company_id': self.company_id.id,
                'currency_id': self.currency_id.id,
                'partner_id': self.company_id.partner_id.id,
            }).id

    def name_get(self):
        res = []
        for journal in self:
            name = journal.name
            if journal.currency_id and journal.currency_id != journal.company_id.currency_id:
                name = "%s (%s)" % (name, journal.currency_id.name)
            res += [(journal.id, name)]
        return res

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []

        if operator == 'ilike' and not (name or '').strip():
            domain = []
        else:
            connector = '&' if operator in expression.NEGATIVE_TERM_OPERATORS else '|'
            domain = [connector, ('code', operator, name), ('name', operator, name)]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

    @api.depends('inbound_payment_method_ids', 'outbound_payment_method_ids')
    def _methods_compute(self):
        for journal in self:
            journal.at_least_one_inbound = bool(len(journal.inbound_payment_method_ids))
            journal.at_least_one_outbound = bool(len(journal.outbound_payment_method_ids))

    def action_configure_bank_journal(self):
        """ This function is called by the "configure" button of bank journals,
        visible on dashboard if no bank statement source has been defined yet
        """
        # We simply call the setup bar function.
        return self.env['res.company'].setting_init_bank_account_action()

    def create_invoice_from_attachment(self, attachment_ids=[]):
        ''' Create the invoices from files.
         :return: A action redirecting to account.move tree/form view.
        '''
        attachments = self.env['ir.attachment'].browse(attachment_ids)
        if not attachments:
            raise UserError(_("No attachment was provided"))

        invoices = self.env['account.move']
        for attachment in attachments:
            attachment.write({'res_model': 'mail.compose.message'})
            decoders = self.env['account.move']._get_create_invoice_from_attachment_decoders()
            invoice = False
            for decoder in sorted(decoders, key=lambda d: d[0]):
                invoice = decoder[1](attachment)
                if invoice:
                    break
            if not invoice:
                invoice = self.env['account.move'].create({})
            invoice.with_context(no_new_invoice=True).message_post(attachment_ids=[attachment.id])
            invoices += invoice

        action_vals = {
            'name': _('Generated Documents'),
            'domain': [('id', 'in', invoices.ids)],
            'res_model': 'account.move',
            'views': [[False, "tree"], [False, "form"]],
            'type': 'ir.actions.act_window',
            'context': self._context
        }
        if len(invoices) == 1:
            action_vals.update({'res_id': invoices[0].id, 'view_mode': 'form'})
        else:
            action_vals['view_mode'] = 'tree,form'
        return action_vals

    def _create_invoice_from_single_attachment(self, attachment):
        """ Creates an invoice and post the attachment. If the related modules
            are installed, it will trigger OCR or the import from the EDI.
            DEPRECATED : use create_invoice_from_attachment instead

            :returns: the created invoice.
        """
        invoice_action = self.create_invoice_from_attachment(attachment.ids)
        return self.env['account.move'].browse(invoice_action['res_id'])

    def _create_secure_sequence(self, sequence_fields):
        """This function creates a no_gap sequence on each journal in self that will ensure
        a unique number is given to all posted account.move in such a way that we can always
        find the previous move of a journal entry on a specific journal.
        """
        for journal in self:
            vals_write = {}
            for seq_field in sequence_fields:
                if not journal[seq_field]:
                    vals = {
                        'name': _('Securisation of %s - %s') % (seq_field, journal.name),
                        'code': 'SECUR%s-%s' % (journal.id, seq_field),
                        'implementation': 'no_gap',
                        'prefix': '',
                        'suffix': '',
                        'padding': 0,
                        'company_id': journal.company_id.id}
                    seq = self.env['ir.sequence'].create(vals)
                    vals_write[seq_field] = seq.id
            if vals_write:
                journal.write(vals_write)

    # -------------------------------------------------------------------------
    # REPORTING METHODS
    # -------------------------------------------------------------------------

    def _get_journal_bank_account_balance(self, domain=None):
        ''' Get the bank balance of the current journal by filtering the journal items using the journal's accounts.

        /!\ The current journal is not part of the applied domain. This is the expected behavior since we only want
        a logic based on accounts.

        :param domain:  An additional domain to be applied on the account.move.line model.
        :return:        Tuple having balance expressed in journal's currency
                        along with the total number of move lines having the same account as of the journal's default account.
        '''
        self.ensure_one()
        self.env['account.move.line'].check_access_rights('read')

        if not self.default_account_id:
            return 0.0, 0

        domain = (domain or []) + [
            ('account_id', 'in', tuple(self.default_account_id.ids)),
            ('display_type', 'not in', ('line_section', 'line_note')),
            ('move_id.state', '!=', 'cancel'),
        ]
        query = self.env['account.move.line']._where_calc(domain)
        tables, where_clause, where_params = query.get_sql()

        query = '''
            SELECT
                COUNT(account_move_line.id) AS nb_lines,
                COALESCE(SUM(account_move_line.balance), 0.0),
                COALESCE(SUM(account_move_line.amount_currency), 0.0)
            FROM ''' + tables + '''
            WHERE ''' + where_clause + '''
        '''

        company_currency = self.company_id.currency_id
        journal_currency = self.currency_id if self.currency_id and self.currency_id != company_currency else False

        self._cr.execute(query, where_params)
        nb_lines, balance, amount_currency = self._cr.fetchone()
        return amount_currency if journal_currency else balance, nb_lines

    def _get_journal_outstanding_payments_account_balance(self, domain=None, date=None):
        ''' Get the outstanding payments balance of the current journal by filtering the journal items using the
        journal's accounts.

        :param domain:  An additional domain to be applied on the account.move.line model.
        :param date:    The date to be used when performing the currency conversions.
        :return:        The balance expressed in the journal's currency.
        '''
        self.ensure_one()
        self.env['account.move.line'].check_access_rights('read')
        conversion_date = date or fields.Date.context_today(self)

        accounts = self.payment_debit_account_id + self.payment_credit_account_id
        if not accounts:
            return 0.0, 0

        # Allow user managing payments without any statement lines.
        # In that case, the user manages transactions only using the register payment wizard.
        if self.default_account_id in accounts:
            return 0.0, 0

        domain = (domain or []) + [
            ('account_id', 'in', tuple(accounts.ids)),
            ('display_type', 'not in', ('line_section', 'line_note')),
            ('move_id.state', '!=', 'cancel'),
            ('reconciled', '=', False),
            ('journal_id', '=', self.id),
        ]
        query = self.env['account.move.line']._where_calc(domain)
        tables, where_clause, where_params = query.get_sql()

        self._cr.execute('''
            SELECT
                COUNT(account_move_line.id) AS nb_lines,
                account_move_line.currency_id,
                account.reconcile AS is_account_reconcile,
                SUM(account_move_line.amount_residual) AS amount_residual,
                SUM(account_move_line.balance) AS balance,
                SUM(account_move_line.amount_residual_currency) AS amount_residual_currency,
                SUM(account_move_line.amount_currency) AS amount_currency
            FROM ''' + tables + '''
            JOIN account_account account ON account.id = account_move_line.account_id
            WHERE ''' + where_clause + '''
            GROUP BY account_move_line.currency_id, account.reconcile
        ''', where_params)

        company_currency = self.company_id.currency_id
        journal_currency = self.currency_id if self.currency_id and self.currency_id != company_currency else False
        balance_currency = journal_currency or company_currency

        total_balance = 0.0
        nb_lines = 0
        for res in self._cr.dictfetchall():
            nb_lines += res['nb_lines']

            amount_currency = res['amount_residual_currency'] if res['is_account_reconcile'] else res['amount_currency']
            balance = res['amount_residual'] if res['is_account_reconcile'] else res['balance']

            if res['currency_id'] and journal_currency and res['currency_id'] == journal_currency.id:
                total_balance += amount_currency
            elif journal_currency:
                total_balance += company_currency._convert(balance, balance_currency, self.company_id, conversion_date)
            else:
                total_balance += balance
        return total_balance, nb_lines

    def _get_last_bank_statement(self, domain=None):
        ''' Retrieve the last bank statement created using this journal.
        :param domain:  An additional domain to be applied on the account.bank.statement model.
        :return:        An account.bank.statement record or an empty recordset.
        '''
        self.ensure_one()
        last_statement_domain = (domain or []) + [('journal_id', '=', self.id)]
        last_st_line = self.env['account.bank.statement.line'].search(last_statement_domain, order='date desc, id desc', limit=1)
        return last_st_line.statement_id
