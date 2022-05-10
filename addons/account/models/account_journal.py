# -*- coding: utf-8 -*-
from odoo import api, Command, fields, models, _
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
from odoo.addons.base.models.res_bank import sanitize_account_number
from odoo.tools import remove_accents
import logging
import re
import warnings

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
        inverse='_inverse_type',
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
    suspense_account_id = fields.Many2one(
        comodel_name='account.account', check_company=True, ondelete='restrict', readonly=False, store=True,
        compute='_compute_suspense_account_id',
        help="Bank statements transactions will be posted on the suspense account until the final reconciliation "
             "allowing finding the right account.", string='Suspense Account',
        domain=lambda self: "[('deprecated', '=', False), ('company_id', '=', company_id), \
                             ('user_type_id.type', 'not in', ('receivable', 'payable')), \
                             ('user_type_id', '=', %s)]" % self.env.ref('account.data_account_type_current_assets').id)
    restrict_mode_hash_table = fields.Boolean(string="Lock Posted Entries with Hash",
        help="If ticked, the accounting entry or invoice receives a hash as soon as it is posted and cannot be modified anymore.")
    sequence = fields.Integer(help='Used to order Journals in the dashboard view', default=10)

    invoice_reference_type = fields.Selection(string='Communication Type', required=True, selection=[('none', 'Open'), ('partner', 'Based on Customer'), ('invoice', 'Based on Invoice')], default='invoice', help='You can set here the default communication that will appear on customer invoices, once validated, to help the customer to refer to that particular invoice when making the payment.')
    invoice_reference_model = fields.Selection(string='Communication Standard', required=True, selection=[('odoo', 'Odoo'), ('euro', 'European')], default=_default_invoice_reference_model, help="You can choose different models for each type of reference. The default one is the Odoo reference.")

    #groups_id = fields.Many2many('res.groups', 'account_journal_group_rel', 'journal_id', 'group_id', string='Groups')
    currency_id = fields.Many2one('res.currency', help='The currency used to enter statement', string="Currency")
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, index=True, default=lambda self: self.env.company,
        help="Company related to this journal")
    country_code = fields.Char(related='company_id.account_fiscal_country_id.code', readonly=True)

    refund_sequence = fields.Boolean(string='Dedicated Credit Note Sequence', help="Check this box if you don't want to share the same sequence for invoices and credit notes made from this journal", default=False)
    sequence_override_regex = fields.Text(help="Technical field used to enforce complex sequence composition that the system would normally misunderstand.\n"\
                                          "This is a regex that can include all the following capture groups: prefix1, year, prefix2, month, prefix3, seq, suffix.\n"\
                                          "The prefix* groups are the separators between the year, month and the actual increasing sequence number (seq).\n"\

                                          "e.g: ^(?P<prefix1>.*?)(?P<year>\d{4})(?P<prefix2>\D*?)(?P<month>\d{2})(?P<prefix3>\D+?)(?P<seq>\d+)(?P<suffix>\D*?)$")

    inbound_payment_method_line_ids = fields.One2many(
        comodel_name='account.payment.method.line',
        domain=[('payment_type', '=', 'inbound')],
        compute='_compute_inbound_payment_method_line_ids',
        store=True,
        readonly=False,
        string='Inbound Payment Methods',
        inverse_name='journal_id',
        copy=False,
        check_company=True,
        help="Manual: Get paid by any method outside of Odoo.\n"
        "Payment Acquirers: Each payment acquirer has its own Payment Method. Request a transaction on/to a card thanks to a payment token saved by the partner when buying or subscribing online.\n"
        "Batch Deposit: Collect several customer checks at once generating and submitting a batch deposit to your bank. Module account_batch_payment is necessary.\n"
        "SEPA Direct Debit: Get paid in the SEPA zone thanks to a mandate your partner will have granted to you. Module account_sepa is necessary.\n"
    )
    outbound_payment_method_line_ids = fields.One2many(
        comodel_name='account.payment.method.line',
        domain=[('payment_type', '=', 'outbound')],
        compute='_compute_outbound_payment_method_line_ids',
        store=True,
        readonly=False,
        string='Outbound Payment Methods',
        inverse_name='journal_id',
        copy=False,
        check_company=True,
        help="Manual: Pay by any method outside of Odoo.\n"
        "Check: Pay bills by check and print it from Odoo.\n"
        "SEPA Credit Transfer: Pay in the SEPA zone by submitting a SEPA Credit Transfer file to your bank. Module account_sepa is necessary.\n"
    )
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
    alias_domain = fields.Char('Alias domain', compute='_compute_alias_domain')
    alias_name = fields.Char('Alias Name', copy=False, compute='_compute_alias_name', inverse='_inverse_type', help="It creates draft invoices and bills by sending an email.", readonly=False)

    journal_group_ids = fields.Many2many('account.journal.group',
        domain="[('company_id', '=', company_id)]",
        check_company=True,
        string="Journal Groups")

    secure_sequence_id = fields.Many2one('ir.sequence',
        help='Sequence to use to ensure the securisation of data',
        check_company=True,
        readonly=True, copy=False)

    available_payment_method_ids = fields.Many2many(
        comodel_name='account.payment.method',
        compute='_compute_available_payment_method_ids'
    )

    selected_payment_method_codes = fields.Char(
        compute='_compute_selected_payment_method_codes',
        help='Technical field used to hide or show payment method options if needed.'
    )

    _sql_constraints = [
        ('code_company_uniq', 'unique (code, company_id)', 'Journal codes must be unique per company.'),
    ]

    @api.depends('outbound_payment_method_line_ids', 'inbound_payment_method_line_ids')
    def _compute_available_payment_method_ids(self):
        """
        Compute the available payment methods id by respecting the following rules:
            Methods of mode 'unique' cannot be used twice on the same company
            Methods of mode 'multi' cannot be used twice on the same journal
        """
        method_information = self.env['account.payment.method']._get_payment_method_information()
        pay_methods = self.env['account.payment.method'].search([('code', 'in', list(method_information.keys()))])
        pay_method_by_code = {x.code + x.payment_type: x for x in pay_methods}
        unique_pay_methods = [k for k, v in method_information.items() if v['mode'] == 'unique']

        pay_methods_by_company = {}
        pay_methods_by_journal = {}
        if unique_pay_methods:
            self._cr.execute('''
                SELECT
                    journal.id,
                    journal.company_id,
                    ARRAY_AGG(DISTINCT apm.id)
                FROM account_payment_method_line apml
                JOIN account_journal journal ON journal.id = apml.journal_id
                JOIN account_payment_method apm ON apm.id = apml.payment_method_id
                WHERE apm.code IN %s
                GROUP BY
                    journal.id,
                    journal.company_id
            ''', [tuple(unique_pay_methods)])
            for journal_id, company_id, payment_method_ids in self._cr.fetchall():
                pay_methods_by_company[company_id] = set(payment_method_ids)
                pay_methods_by_journal[journal_id] = set(payment_method_ids)

        pay_method_ids_commands_x_journal = {j: [Command.clear()] for j in self}
        for payment_type in ('inbound', 'outbound'):
            for code, vals in method_information.items():
                payment_method = pay_method_by_code.get(code + payment_type)

                if not payment_method:
                    continue

                # Get the domain of the journals on which the current method is usable.
                method_domain = payment_method._get_payment_method_domain()

                for journal in self.filtered_domain(method_domain):
                    protected_pay_method_ids = pay_methods_by_company.get(journal.company_id._origin.id, set()) \
                                               - pay_methods_by_journal.get(journal._origin.id, set())

                    if payment_type == 'inbound':
                        lines = journal.inbound_payment_method_line_ids
                    else:
                        lines = journal.outbound_payment_method_line_ids

                    already_used = payment_method in lines.payment_method_id
                    is_protected = payment_method.id in protected_pay_method_ids
                    if vals['mode'] == 'unique' and (already_used or is_protected):
                        continue

                    # Only the manual payment method can be used multiple time on a single journal.
                    if payment_method.code != "manual" and already_used:
                        continue

                    pay_method_ids_commands_x_journal[journal].append(Command.link(payment_method.id))

        for journal, pay_method_ids_commands in pay_method_ids_commands_x_journal.items():
            journal.available_payment_method_ids = pay_method_ids_commands

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

    @api.depends('type', 'currency_id')
    def _compute_inbound_payment_method_line_ids(self):
        for journal in self:
            pay_method_line_ids_commands = [Command.clear()]
            if journal.type in ('bank', 'cash'):
                default_methods = journal._default_inbound_payment_methods()
                pay_method_line_ids_commands += [Command.create({
                    'name': pay_method.name,
                    'payment_method_id': pay_method.id,
                }) for pay_method in default_methods]
            journal.inbound_payment_method_line_ids = pay_method_line_ids_commands

    @api.depends('type', 'currency_id')
    def _compute_outbound_payment_method_line_ids(self):
        for journal in self:
            pay_method_line_ids_commands = [Command.clear()]
            if journal.type in ('bank', 'cash'):
                default_methods = journal._default_outbound_payment_methods()
                pay_method_line_ids_commands += [Command.create({
                    'name': pay_method.name,
                    'payment_method_id': pay_method.id,
                }) for pay_method in default_methods]
            journal.outbound_payment_method_line_ids = pay_method_line_ids_commands

    @api.depends('outbound_payment_method_line_ids', 'inbound_payment_method_line_ids')
    def _compute_selected_payment_method_codes(self):
        """
        Set the selected payment method as a list of comma separated codes like: ,manual,check_printing,...
        These will be then used to display or not payment method specific fields in the view.
        """
        for journal in self:
            codes = [line.code for line in journal.inbound_payment_method_line_ids + journal.outbound_payment_method_line_ids]
            journal.selected_payment_method_codes = ',' + ','.join(codes) + ','

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

    def _inverse_type(self):
        for record in self:
            record._update_mail_alias()

    @api.depends('name')
    def _compute_alias_domain(self):
        self.alias_domain = self.env["ir.config_parameter"].sudo().get_param("mail.catchall.domain")

    @api.depends('alias_id')
    def _compute_alias_name(self):
        for record in self:
            record.alias_name = record.alias_id.alias_name

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
            AND aml.display_type IS NULL
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

    @api.constrains('inbound_payment_method_line_ids', 'outbound_payment_method_line_ids')
    def _check_payment_method_line_ids_multiplicity(self):
        """
        Check and ensure that the payment method lines multiplicity is respected.
        """
        method_info = self.env['account.payment.method']._get_payment_method_information()
        unique_codes = tuple(code for code, info in method_info.items() if info.get('mode') == 'unique')

        if not unique_codes:
            return

        self.flush(['inbound_payment_method_line_ids', 'outbound_payment_method_line_ids', 'company_id'])
        self.env['account.payment.method.line'].flush(['payment_method_id', 'journal_id'])
        self.env['account.payment.method'].flush(['code'])

        if unique_codes:
            self._cr.execute('''
                SELECT apm.id
                FROM account_payment_method apm
                JOIN account_payment_method_line apml on apm.id = apml.payment_method_id
                JOIN account_journal journal on journal.id = apml.journal_id
                JOIN res_company company on journal.company_id = company.id
                WHERE apm.code in %s
                GROUP BY
                    company.id,
                    apm.id
                HAVING array_length(array_agg(journal.id), 1) > 1;
            ''', [unique_codes])

        method_ids = [res[0] for res in self._cr.fetchall()]
        if method_ids:
            methods = self.env['account.payment.method'].browse(method_ids)
            raise ValidationError(_("Some payment methods supposed to be unique already exists somewhere else.\n"
                                    "(%s)", ', '.join([method.display_name for method in methods])))

    @api.constrains('active')
    def _check_auto_post_draft_entries(self):
        # constraint should be tested just after archiving a journal, but shouldn't be raised when unarchiving a journal containing draft entries
        for journal in self.filtered(lambda j: not j.active):
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
        """ This function verifies that the user-given mail alias (or its fallback) doesn't contain non-ascii chars.
            The fallbacks are the journal's name, code, or type - these are suffixed with the
            company's name or id (in case the company's name is not ascii either).
        """
        def get_company_suffix():
            if self.company_id != self.env.ref('base.main_company'):
                try:
                    remove_accents(self.company_id.name).encode('ascii')
                    return '-' + str(self.company_id.name)
                except UnicodeEncodeError:
                    return '-' + str(self.company_id.id)
            return ''

        if not alias_name:
            alias_name = self.name
            alias_name += get_company_suffix()
        try:
            remove_accents(alias_name).encode('ascii')
        except UnicodeEncodeError:
            try:
                remove_accents(self.code).encode('ascii')
                safe_alias_name = self.code
            except UnicodeEncodeError:
                safe_alias_name = self.type
            safe_alias_name += get_company_suffix()
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

        # Find a unique code for the copied journal
        read_codes = self.env['account.journal'].with_context(active_test=False).search_read([('company_id', '=', self.company_id.id)], ['code'])
        all_journal_codes = {code_data['code'] for code_data in read_codes}

        copy_code = self.code
        code_prefix = re.sub(r'\d+', '', self.code).strip()
        counter = 1
        while counter <= len(all_journal_codes) and  copy_code in all_journal_codes:
            counter_str = str(counter)
            copy_prefix = code_prefix[:self._fields['code'].size - len(counter_str)]
            copy_code = ("%s%s" % (copy_prefix, counter_str))

            counter += 1

        if counter > len(all_journal_codes):
            # Should never happen, but put there just in case.
            raise UserError(_("Could not compute any code for the copy automatically. Please create it manually."))

        default.update(
            code=copy_code,
            name=_("%s (copy)") % (self.name or ''))

        return super(AccountJournal, self).copy(default)

    def _update_mail_alias(self, vals=None):
        if vals is not None:
            warnings.warn(
                '`vals` is a deprecated argument of `_update_mail_alias`',
                DeprecationWarning,
                stacklevel=2
            )
        self.ensure_one()
        if self.type in ('purchase', 'sale'):
            alias_values = self._get_alias_values(type=self.type, alias_name=self.alias_name)
            if self.alias_id:
                self.alias_id.sudo().write(alias_values)
            else:
                alias_values['alias_model_id'] = self.env['ir.model']._get('account.move').id
                alias_values['alias_parent_model_id'] = self.env['ir.model']._get('account.journal').id
                self.alias_id = self.env['mail.alias'].sudo().create(alias_values)
        elif self.alias_id:
            self.alias_id.unlink()

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
            if journal_type in ('cash', 'bank') and not has_profit_account:
                vals['profit_account_id'] = company.default_cash_difference_income_account_id.id
            if journal_type in ('cash', 'bank') and not has_loss_account:
                vals['loss_account_id'] = company.default_cash_difference_expense_account_id.id

        # === Fill missing refund_sequence ===
        if 'refund_sequence' not in vals:
            vals['refund_sequence'] = vals['type'] in ('sale', 'purchase')

    @api.model
    def create(self, vals):
        # OVERRIDE
        self._fill_missing_values(vals)

        journal = super(AccountJournal, self.with_context(mail_create_nolog=True)).create(vals)

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
            'type': 'ir.actions.act_window',
            'context': self._context
        }
        if len(invoices) == 1:
            action_vals.update({
                'views': [[False, "form"]],
                'view_mode': 'form',
                'res_id': invoices[0].id,
            })
        else:
            action_vals.update({
                'views': [[False, "tree"], [False, "kanban"], [False, "form"]],
                'view_mode': 'tree, kanban, form',
            })
        return action_vals

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
            ('parent_state', '!=', 'cancel'),
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

    def _get_journal_inbound_outstanding_payment_accounts(self):
        """
        :return: A recordset with all the account.account used by this journal for inbound transactions.
        """
        self.ensure_one()
        account_ids = set()
        for line in self.inbound_payment_method_line_ids:
            account_ids.add(line.payment_account_id.id or self.company_id.account_journal_payment_debit_account_id.id)
        return self.env['account.account'].browse(account_ids)

    def _get_journal_outbound_outstanding_payment_accounts(self):
        """
        :return: A recordset with all the account.account used by this journal for outbound transactions.
        """
        self.ensure_one()
        account_ids = set()
        for line in self.outbound_payment_method_line_ids:
            account_ids.add(line.payment_account_id.id or self.company_id.account_journal_payment_credit_account_id.id)
        return self.env['account.account'].browse(account_ids)

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

        accounts = self._get_journal_inbound_outstanding_payment_accounts().union(self._get_journal_outbound_outstanding_payment_accounts())
        if not accounts:
            return 0.0, 0

        # Allow user managing payments without any statement lines.
        # In that case, the user manages transactions only using the register payment wizard.
        if self.default_account_id in accounts:
            return 0.0, 0

        domain = (domain or []) + [
            ('account_id', 'in', tuple(accounts.ids)),
            ('display_type', 'not in', ('line_section', 'line_note')),
            ('parent_state', '!=', 'cancel'),
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

    def _get_available_payment_method_lines(self, payment_type):
        """
        This getter is here to allow filtering the payment method lines if needed in other modules.
        It does NOT serve as a general getter to get the lines.

        For example, it'll be extended to filter out lines from inactive payment acquirers in the payment module.
        :param payment_type: either inbound or outbound, used to know which lines to return
        :return: Either the inbound or outbound payment method lines
        """
        if not self:
            return self.env['account.payment.method.line']
        self.ensure_one()
        if payment_type == 'inbound':
            return self.inbound_payment_method_line_ids
        else:
            return self.outbound_payment_method_line_ids

    def _is_payment_method_available(self, payment_method_code):
        """ Check if the payment method is available on this journal. """
        self.ensure_one()
        pm_info = self.env['account.payment.method']._get_payment_method_information().get(payment_method_code)
        if not pm_info:
            return False
        currency_ids = pm_info.get('currency_ids')
        country_id = pm_info.get('country_id')
        domain = pm_info.get('domain', [('type', 'in', ('bank', 'cash'))])
        journal_types = next(right for left, operator, right in domain if left == 'type' and operator in ('in', '='))

        journal_currency_id = self.currency_id.id or self.company_id.currency_id.id
        if currency_ids and journal_currency_id not in currency_ids:
            return False
        if country_id and self.company_id.account_fiscal_country_id.id != country_id:
            return False
        if self.type not in journal_types:
            return False
        return True
