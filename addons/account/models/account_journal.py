# -*- coding: utf-8 -*-

from ast import literal_eval

from odoo import api, Command, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.base.models.res_bank import sanitize_account_number
from odoo.tools import remove_accents, groupby
from collections import defaultdict
import logging
import re

_logger = logging.getLogger(__name__)


class AccountJournalGroup(models.Model):
    _name = 'account.journal.group'
    _description = "Account Journal Group"
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of

    name = fields.Char("Journal Group", required=True, translate=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    excluded_journal_ids = fields.Many2many('account.journal', string="Excluded Journals",
        check_company=True)
    sequence = fields.Integer(default=10)

    _sql_constraints = [
        ('uniq_name', 'unique(company_id, name)', 'A journal group name must be unique per company.'),
    ]

class AccountJournal(models.Model):
    _name = "account.journal"
    _description = "Journal"
    _order = 'sequence, type, code'
    _inherit = ['portal.mixin',
                'mail.alias.mixin.optional',
                'mail.thread',
                'mail.activity.mixin',
               ]
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of
    _rec_names_search = ['name', 'code']

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

    name = fields.Char(string='Journal Name', required=True, translate=True)
    code = fields.Char(
        string='Short Code',
        size=5,
        compute='_compute_code', readonly=False, store=True,
        required=True, precompute=True,
        help="Shorter name used for display. "
             "The journal entries of this journal will also be named using this prefix by default."
    )
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
    account_control_ids = fields.Many2many('account.account', 'journal_account_control_rel', 'journal_id', 'account_id', string='Allowed accounts',
        check_company=True,
        domain="[('deprecated', '=', False), ('account_type', '!=', 'off_balance')]")
    default_account_type = fields.Char(string='Default Account Type', compute="_compute_default_account_type")
    default_account_id = fields.Many2one(
        comodel_name='account.account', check_company=True, copy=False, ondelete='restrict',
        string='Default Account',
        domain="[('deprecated', '=', False), ('account_type', '=like', default_account_type)]",
    )

    suspense_account_id = fields.Many2one(
        comodel_name='account.account', check_company=True, ondelete='restrict', readonly=False, store=True,
        compute='_compute_suspense_account_id',
        help="Bank statements transactions will be posted on the suspense account until the final reconciliation "
             "allowing finding the right account.", string='Suspense Account',
        domain="[('deprecated', '=', False), ('account_type', '=', 'asset_current')]",
    )
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
    payment_sequence = fields.Boolean(
        string='Dedicated Payment Sequence',
        compute='_compute_payment_sequence', readonly=False, store=True, precompute=True,
        help="Check this box if you don't want to share the same sequence on payments and bank transactions posted on this journal",
    )
    sequence_override_regex = fields.Text(help="Technical field used to enforce complex sequence composition that the system would normally misunderstand.\n"\
                                          "This is a regex that can include all the following capture groups: prefix1, year, prefix2, month, prefix3, seq, suffix.\n"\
                                          "The prefix* groups are the separators between the year, month and the actual increasing sequence number (seq).\n"\

                                          r"e.g: ^(?P<prefix1>.*?)(?P<year>\d{4})(?P<prefix2>\D*?)(?P<month>\d{2})(?P<prefix3>\D+?)(?P<seq>\d+)(?P<suffix>\D*?)$")

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
        "Payment Providers: Each payment provider has its own Payment Method. Request a transaction on/to a card thanks to a payment token saved by the partner when buying or subscribing online.\n"
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
        domain="[('deprecated', '=', False), \
                ('account_type', 'in', ('income', 'income_other'))]")
    loss_account_id = fields.Many2one(
        comodel_name='account.account', check_company=True,
        help="Used to register a loss when the ending balance of a cash register differs from what the system computes",
        string='Loss Account',
        domain="[('deprecated', '=', False), \
                ('account_type', '=', 'expense')]")

    # Bank journals fields
    company_partner_id = fields.Many2one('res.partner', related='company_id.partner_id', string='Account Holder', readonly=True, store=False)
    bank_account_id = fields.Many2one('res.partner.bank',
        string="Bank Account",
        ondelete='restrict', copy=False,
        check_company=True,
        domain="[('partner_id','=', company_partner_id)]")
    bank_statements_source = fields.Selection(selection=_get_bank_statements_available_sources, string='Bank Feeds', default='undefined', help="Defines how the bank statements will be registered")
    bank_acc_number = fields.Char(related='bank_account_id.acc_number', readonly=False)
    bank_id = fields.Many2one('res.bank', related='bank_account_id.bank_id', readonly=False)

    # Sale journals fields
    sale_activity_type_id = fields.Many2one('mail.activity.type', string='Schedule Activity', default=False, help="Activity will be automatically scheduled on payment due date, improving collection process.")
    sale_activity_user_id = fields.Many2one('res.users', string="Activity User", help="Leave empty to assign the Salesperson of the invoice.")
    sale_activity_note = fields.Text('Activity Summary')

    # alias configuration for journals
    alias_id = fields.Many2one(help="Send one separate email for each invoice.\n\n"
                                    "Any file extension will be accepted.\n\n"
                                    "Only PDF and XML files will be interpreted by Odoo")

    journal_group_ids = fields.Many2many('account.journal.group',
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

    # used to hide or show payment method options if needed
    selected_payment_method_codes = fields.Char(
        compute='_compute_selected_payment_method_codes',
    )
    accounting_date = fields.Date(compute='_compute_accounting_date')

    _sql_constraints = [
        ('code_company_uniq', 'unique (company_id, code)', 'Journal codes must be unique per company.'),
    ]

    @api.depends('type', 'company_id')
    def _compute_code(self):
        cache = defaultdict(list)
        for record in self:
            if not record.code and record.type in ('bank', 'cash'):
                record.code = self.get_next_bank_cash_default_code(
                    record.type,
                    record.company_id,
                    cache.get(record.company_id)
                )
                cache[record.company_id].append(record.code)

    def _get_journals_payment_method_information(self):
        method_information = self.env['account.payment.method']._get_payment_method_information()
        unique_electronic_ids = set()
        electronic_names = set()
        pay_methods = self.env['account.payment.method'].sudo().search([('code', 'in', list(method_information.keys()))])
        manage_providers = 'payment_provider_id' in self.env['account.payment.method.line']._fields

        # Split the payment method information per id.
        method_information_mapping = {}
        for pay_method in pay_methods:
            code = pay_method.code
            values = method_information_mapping[pay_method.id] = {
                **method_information[code],
                'payment_method': pay_method,
                'company_journals': {},
            }
            if values['mode'] == 'unique':
                unique_electronic_ids.add(pay_method.id)
            elif manage_providers and values['mode'] == 'electronic':
                unique_electronic_ids.add(pay_method.id)
                electronic_names.add(pay_method.code)

        # Load the provider to manage 'electronic' payment methods.
        providers_per_code = {}
        if manage_providers:
            providers = self.env['payment.provider'].sudo().search([
                *self.env['payment.provider']._check_company_domain(self.company_id),
                ('code', 'in', tuple(electronic_names)),
            ])
            for provider in providers:
                providers_per_code.setdefault(provider.company_id.id, {}).setdefault(provider._get_code(), set()).add(provider.id)

        # Collect the existing unique/electronic payment method lines.
        if unique_electronic_ids:
            fnames = ['payment_method_id', 'journal_id']
            if manage_providers:
                fnames.append('payment_provider_id')
            self.env['account.payment.method.line'].flush_model(fnames=fnames)

            self._cr.execute(
                f'''
                    SELECT
                        apm.id,
                        journal.company_id,
                        journal.id,
                        {'apml.payment_provider_id' if manage_providers else 'NULL'}
                    FROM account_payment_method_line apml
                    JOIN account_journal journal ON journal.id = apml.journal_id
                    JOIN account_payment_method apm ON apm.id = apml.payment_method_id
                    WHERE apm.id IN %s
                ''',
                [tuple(unique_electronic_ids)],
            )
            for pay_method_id, company_id, journal_id, provider_id in self._cr.fetchall():
                values = method_information_mapping[pay_method_id]
                is_electronic = manage_providers and values['mode'] == 'electronic'
                if is_electronic:
                    journal_ids = values['company_journals'].setdefault(company_id, {}).setdefault(provider_id, [])
                else:
                    journal_ids = values['company_journals'].setdefault(company_id, [])
                journal_ids.append(journal_id)
        return {
            'pay_methods': pay_methods,
            'manage_providers': manage_providers,
            'method_information_mapping': method_information_mapping,
            'providers_per_code': providers_per_code,
        }

    @api.depends('outbound_payment_method_line_ids', 'inbound_payment_method_line_ids')
    def _compute_available_payment_method_ids(self):
        """
        Compute the available payment methods id by respecting the following rules:
            Methods of mode 'unique' cannot be used twice on the same company.
            Methods of mode 'electronic' cannot be used twice on the same company for the same 'payment_provider_id'.
            Methods of mode 'multi' can be duplicated on the same journal.
        """
        results = self._get_journals_payment_method_information()
        pay_methods = results['pay_methods']
        manage_providers = results['manage_providers']
        method_information_mapping = results['method_information_mapping']
        providers_per_code = results['providers_per_code']

        # Compute the candidates for each journal.
        for journal in self:
            commands = [Command.clear()]
            company = journal.company_id

            # Exclude the 'unique' / 'electronic' values that are already set on the journal.
            protected_provider_ids = set()
            protected_payment_method_ids = set()
            for payment_type in ('inbound', 'outbound'):
                lines = journal[f'{payment_type}_payment_method_line_ids']
                for line in lines:
                    if line.payment_method_id:
                        protected_payment_method_ids.add(line.payment_method_id.id)
                        if manage_providers and method_information_mapping.get(line.payment_method_id.id, {}).get('mode') == 'electronic':
                            protected_provider_ids.add(line.payment_provider_id.id)

            for pay_method in pay_methods:
                values = method_information_mapping[pay_method.id]

                # Get the domain of the journals on which the current method is usable.
                method_domain = pay_method._get_payment_method_domain(pay_method.code)
                if not journal.filtered_domain(method_domain):
                    continue

                if values['mode'] == 'unique':
                    # 'unique' are linked to a single journal per company.
                    already_linked_journal_ids = set(values['company_journals'].get(company.id, [])) - {journal._origin.id}
                    if not already_linked_journal_ids and pay_method.id not in protected_payment_method_ids:
                        commands.append(Command.link(pay_method.id))
                elif manage_providers and values['mode'] == 'electronic':
                    # 'electronic' are linked to a single journal per company per provider.
                    for provider_id in providers_per_code.get(company.id, {}).get(pay_method.code, set()):
                        already_linked_journal_ids = set(values['company_journals'].get(company.id, {}).get(provider_id, [])) - {journal._origin.id}
                        if not already_linked_journal_ids and provider_id not in protected_provider_ids:
                            commands.append(Command.link(pay_method.id))
                elif values['mode'] == 'multi':
                    # 'multi' are unlimited.
                    commands.append(Command.link(pay_method.id))

            journal.available_payment_method_ids = commands

    @api.depends('type')
    def _compute_default_account_type(self):
        default_account_id_types = {
            'bank': 'asset_cash',
            'cash': 'asset_cash',
            'sale': 'income%',
            'purchase': 'expense%',
        }

        for journal in self:
            journal.default_account_type = default_account_id_types.get(journal.type, '%')

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
            codes = [line.code for line in journal.inbound_payment_method_line_ids + journal.outbound_payment_method_line_ids if line.code]
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

    @api.depends('company_id')
    @api.depends_context('move_date', 'has_tax')
    def _compute_accounting_date(self):
        move_date = self.env.context.get('move_date') or fields.Date.context_today(self)
        has_tax = self.env.context.get('has_tax') or False
        for journal in self:
            temp_move = self.env['account.move'].new({'journal_id': journal.id})
            journal.accounting_date = temp_move._get_accounting_date(move_date, has_tax)


    @api.onchange('type')
    def _onchange_type_for_alias(self):
        self.filtered(lambda journal: journal.type not in {'sale', 'purchase'}).alias_name = False
        for journal in self.filtered(lambda journal: (
            not journal.alias_name and journal.type in {'sale', 'purchase'})
        ):
            journal.alias_name = self._alias_prepare_alias_name(
                False, journal.name, journal.code, journal.type, journal.company_id)

    @api.constrains('account_control_ids')
    def _constrains_account_control_ids(self):
        self.env['account.move.line'].flush_model(['account_id', 'journal_id', 'display_type'])
        self.flush_recordset(['account_control_ids'])
        self._cr.execute("""
            SELECT aml.id
            FROM account_move_line aml
            WHERE aml.journal_id in (%s)
            AND EXISTS (SELECT 1 FROM journal_account_control_rel rel WHERE rel.journal_id = aml.journal_id)
            AND NOT EXISTS (SELECT 1 FROM journal_account_control_rel rel WHERE rel.account_id = aml.account_id AND rel.journal_id = aml.journal_id)
            AND aml.display_type NOT IN ('line_section', 'line_note')
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
        for company, journals in groupby(self, lambda journal: journal.company_id):
            if self.env['account.move'].search([
                ('journal_id', 'in', [journal.id for journal in journals]),
                '!', ('company_id', 'child_of', company.id)
            ], limit=1):
                raise UserError(_("You can't change the company of your journal since there are some journal entries linked to it."))

    @api.constrains('type', 'default_account_id')
    def _check_type_default_account_id_type(self):
        for journal in self:
            if journal.type in ('sale', 'purchase') and journal.default_account_id.account_type in ('asset_receivable', 'liability_payable'):
                raise ValidationError(_("The type of the journal's default credit/debit account shouldn't be 'receivable' or 'payable'."))

    @api.constrains('inbound_payment_method_line_ids', 'outbound_payment_method_line_ids')
    def _check_payment_method_line_ids_multiplicity(self):
        """
        Check and ensure that the payment method lines multiplicity is respected.
        """
        results = self._get_journals_payment_method_information()
        pay_methods = results['pay_methods']
        manage_providers = results['manage_providers']
        method_information_mapping = results['method_information_mapping']
        providers_per_code = results['providers_per_code']

        failing_unicity_payment_methods = self.env['account.payment.method']
        for journal in self:
            company = journal.company_id

            # Exclude the 'unique' / 'electronic' values that are already set on the journal.
            protected_provider_ids = set()
            protected_payment_method_ids = set()
            for payment_type in ('inbound', 'outbound'):
                lines = journal[f'{payment_type}_payment_method_line_ids']

                # Ensure you don't have the same payment_method/name combination twice on the same journal.
                counter = {}
                for line in lines:
                    if method_information_mapping.get(line.payment_method_id.id, {}).get('mode') not in ('electronic', 'unique'):
                        continue

                    key = line.payment_method_id.id, line.name
                    counter.setdefault(key, 0)
                    counter[key] += 1
                    if counter[key] > 1:
                        raise ValidationError(_(
                            "You can't have two payment method lines of the same payment type (%s) "
                            "and with the same name (%s) on a single journal.",
                            payment_type,
                            line.name,
                        ))

                for line in lines:
                    if line.payment_method_id.id in method_information_mapping:
                        protected_payment_method_ids.add(line.payment_method_id.id)
                        if manage_providers and method_information_mapping[line.payment_method_id.id]['mode'] == 'electronic':
                            protected_provider_ids.add(line.payment_provider_id.id)

            for pay_method in pay_methods:
                values = method_information_mapping[pay_method.id]

                if values['mode'] == 'unique':
                    # 'unique' are linked to a single journal per company.
                    already_linked_journal_ids = values['company_journals'].get(company.id, [])
                    if len(already_linked_journal_ids) > 1:
                        failing_unicity_payment_methods |= pay_method
                elif manage_providers and values['mode'] == 'electronic':
                    # 'electronic' are linked to a single journal per company per provider.
                    for provider_id in providers_per_code.get(company.id, {}).get(pay_method.code, set()):
                        already_linked_journal_ids = values['company_journals'].get(company.id, {}).get(provider_id, [])
                        if len(already_linked_journal_ids) > 1:
                            failing_unicity_payment_methods |= pay_method

        if failing_unicity_payment_methods:
            raise ValidationError(_(
                "Some payment methods supposed to be unique already exists somewhere else.\n(%s)",
                ', '.join(failing_unicity_payment_methods.mapped('display_name')),
            ))

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

    @api.depends('type')
    def _compute_payment_sequence(self):
        for journal in self:
            journal.payment_sequence = journal.type in ('bank', 'cash')

    def unlink(self):
        bank_accounts = self.env['res.partner.bank'].browse()
        for bank_account in self.mapped('bank_account_id'):
            accounts = self.search([('bank_account_id', '=', bank_account.id)])
            if accounts <= self:
                bank_accounts += bank_account
        ret = super(AccountJournal, self).unlink()
        bank_accounts.unlink()
        return ret

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})

        # Find a unique code for the copied journal
        read_codes = self.env['account.journal'].with_context(active_test=False).search_read(
            self.env['account.journal']._check_company_domain(self.company_id),
            ['code'],
        )
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
            name=_("%s (copy)", self.name or ''))

        return super(AccountJournal, self).copy(default)

    def write(self, vals):
        # for journals, force a readable name instead of a sanitized name e.g. non ascii in journal names
        if vals.get('alias_name') and 'type' not in vals:
            # will raise if writing name on more than 1 record, using self[0] is safe
            if (not self.env['mail.alias']._is_encodable(vals['alias_name']) or
                not self.env['mail.alias']._sanitize_alias_name(vals['alias_name'])):
                vals['alias_name'] = self._alias_prepare_alias_name(
                    False, vals.get('name', self.name), vals.get('code', self.code), self[0].type, self[0].company_id)

        for journal in self:
            company = journal.company_id
            if ('company_id' in vals and journal.company_id.id != vals['company_id']):
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
                if vals.get('bank_account_id'):
                    bank_account = self.env['res.partner.bank'].browse(vals['bank_account_id'])
                    if bank_account.partner_id != company.partner_id:
                        raise UserError(_("The partners of the journal's company and the related bank account mismatch."))
            if 'restrict_mode_hash_table' in vals and not vals.get('restrict_mode_hash_table'):
                journal_entry = self.env['account.move'].sudo().search([('journal_id', '=', journal.id), ('state', '=', 'posted'), ('secure_sequence_number', '!=', 0)], limit=1)
                if journal_entry:
                    field_string = self._fields['restrict_mode_hash_table'].get_description(self.env)['string']
                    raise UserError(_("You cannot modify the field %s of a journal that already has accounting entries.", field_string))
        result = super(AccountJournal, self).write(vals)

        # Ensure alias coherency when changing type
        if 'type' in vals and not self._context.get('account_journal_skip_alias_sync'):
            for journal in self:
                alias_vals = journal._alias_get_creation_values()
                alias_vals = {
                    'alias_defaults': alias_vals['alias_defaults'],
                    'alias_name': alias_vals['alias_name'],
                }
                journal.update(alias_vals)

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

    def _alias_get_creation_values(self):
        values = super()._alias_get_creation_values()
        values['alias_model_id'] = self.env['ir.model']._get_id('account.move')
        if self.id:
            values['alias_name'] = self._alias_prepare_alias_name(self.alias_name, self.name, self.code, self.type, self.company_id)
            values['alias_defaults'] = defaults = literal_eval(self.alias_defaults or "{}")
            defaults['company_id'] = self.company_id.id
            defaults['move_type'] = 'in_invoice' if self.type == 'purchase' else 'out_invoice'
            defaults['journal_id'] = self.id
        return values

    @api.model
    def _alias_prepare_alias_name(self, alias_name, name, code, jtype, company):
        """ Tool method generating standard journal alias, to ensure uniqueness
        and readability;  reset for other journals than purchase / sale """
        if jtype not in ('purchase', 'sale'):
            return False

        alias_name = next(
            (
                string for string in (alias_name, name, code, jtype)
                if (string and self.env['mail.alias']._is_encodable(string) and
                    self.env['mail.alias']._sanitize_alias_name(string))
            ), False
        )
        if company != self.env.ref('base.main_company'):
            company_identifier = company.name if self.env['mail.alias']._is_encodable(company.name) else company.id
            if f'-{company_identifier}' not in alias_name:
                alias_name = f"{alias_name}-{company_identifier}"
        return self.env['mail.alias']._sanitize_alias_name(alias_name)

    @api.model
    def get_next_bank_cash_default_code(self, journal_type, company, cache=None, protected_codes=False):
        prefix_map = {'cash': 'CSH', 'general': 'GEN', 'bank': 'BNK'}
        journal_code_base = prefix_map.get(journal_type)
        existing_codes = set(self.env['account.journal'].with_context(active_test=False).search([
            *self.env['account.journal']._check_company_domain(company),
            ('code', '=like', journal_code_base + '%'),
        ]).mapped('code') + (cache or []))

        for num in range(1, 100):
            # journal_code has a maximal size of 5, hence we can enforce the boundary num < 100
            journal_code = journal_code_base + str(num)
            if journal_code not in existing_codes and (protected_codes and journal_code not in protected_codes or not protected_codes):
                return journal_code

    @api.model
    def _prepare_liquidity_account_vals(self, company, code, vals):
        return {
            'name': vals.get('name'),
            'code': code,
            'account_type': 'asset_cash',
            'currency_id': vals.get('currency_id'),
            'company_id': company.id,
        }

    @api.model
    def _fill_missing_values(self, vals, protected_codes=False):
        journal_type = vals.get('type')
        is_import = 'import_file' in self.env.context
        if is_import and not journal_type:
            vals['type'] = journal_type = 'general'

        # 'type' field is required.
        if not journal_type:
            return

        # === Fill missing company ===
        company = self.env['res.company'].browse(vals['company_id']) if vals.get('company_id') else self.env.company
        vals['company_id'] = company.id

        # Don't get the digits on 'chart_template' since the chart template could be a custom one.
        random_account = self.env['account.account'].search(
            self.env['account.account']._check_company_domain(company),
            limit=1,
        )
        digits = len(random_account.code) if random_account else 6

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

            # === Fill missing accounts ===
            if not has_liquidity_accounts:
                default_account_code = self.env['account.account']._search_new_account_code(company, digits, liquidity_account_prefix)
                default_account_vals = self._prepare_liquidity_account_vals(company, default_account_code, vals)
                default_account = self.env['account.account'].create(default_account_vals)
                self.env['ir.model.data']._update_xmlids([
                    {
                        'xml_id': f"account.{str(company.id)}_{journal_type}_journal_default_account_{default_account.id}",
                        'record': default_account,
                        'noupdate': True,
                    }
                ])
                vals['default_account_id'] = default_account.id
            if journal_type in ('cash', 'bank') and not has_profit_account:
                vals['profit_account_id'] = company.default_cash_difference_income_account_id.id
            if journal_type in ('cash', 'bank') and not has_loss_account:
                vals['loss_account_id'] = company.default_cash_difference_expense_account_id.id

        if is_import and not vals.get('code'):
            code = vals['name'][:5]
            vals['code'] = code if not protected_codes or code not in protected_codes else self.get_next_bank_cash_default_code(journal_type, company, protected_codes)
            if not vals['code']:
                raise UserError(_("Cannot generate an unused journal code. Please change the name for journal %s.", vals['name']))

        # === Fill missing refund_sequence ===
        if 'refund_sequence' not in vals:
            vals['refund_sequence'] = vals['type'] in ('sale', 'purchase')

        # === Fill missing alias name for sale / purchase, to force alias creation ===
        if journal_type in {'sale', 'purchase'} and 'alias_name' not in vals:
            vals['alias_name'] = self._alias_prepare_alias_name(
                False, vals.get('name'), vals.get('code'), journal_type, company
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # have to keep track of new journal codes when importing
            codes = [vals['code'] for vals in vals_list if 'code' in vals] if 'import_file' in self.env.context else False
            self._fill_missing_values(vals, protected_codes=codes)

        journals = super(AccountJournal, self.with_context(mail_create_nolog=True)).create(vals_list)

        for journal, vals in zip(journals, vals_list):
            # Create the bank_account_id if necessary
            if journal.type == 'bank' and not journal.bank_account_id and vals.get('bank_acc_number'):
                journal.set_bank_account(vals.get('bank_acc_number'), vals.get('bank_id'))

            # Create the secure_sequence_id if necessary
            if journal.restrict_mode_hash_table and not journal.secure_sequence_id:
                journal._create_secure_sequence(['secure_sequence_id'])

        return journals

    def set_bank_account(self, acc_number, bank_id=None):
        """ Create a res.partner.bank (if not exists) and set it as value of the field bank_account_id """
        self.ensure_one()
        res_partner_bank = self.env['res.partner.bank'].search([
            ('sanitized_acc_number', '=', sanitize_account_number(acc_number)),
            ('partner_id', '=', self.company_id.partner_id.id),
        ], limit=1)
        if res_partner_bank:
            self.bank_account_id = res_partner_bank.id
        else:
            self.bank_account_id = self.env['res.partner.bank'].create({
                'acc_number': acc_number,
                'bank_id': bank_id,
                'currency_id': self.currency_id.id,
                'partner_id': self.company_id.partner_id.id,
                'journal_id': self,
            }).id

    @api.depends('currency_id')
    def _compute_display_name(self):
        for journal in self:
            name = journal.name
            if journal.currency_id and journal.currency_id != journal.company_id.currency_id:
                name = f"{name} ({journal.currency_id.name})"
            journal.display_name = name

    def action_configure_bank_journal(self):
        """ This function is called by the "configure" button of bank journals,
        visible on dashboard if no bank statement source has been defined yet
        """
        # We simply call the setup bar function.
        return self.env['res.company'].setting_init_bank_account_action()

    def action_new_transaction(self):
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_bank_statement_tree')
        action['context'] = {'default_journal_id': self.id}
        return action

    def _create_document_from_attachment(self, attachment_ids):
        """ Create the invoices from files."""
        if not self:
            self = self.env['account.journal'].browse(self._context.get("default_journal_id"))
        move_type = self._context.get("default_move_type", "entry")
        if not self:
            if move_type in self.env['account.move'].get_sale_types(include_receipts=True):
                journal_type = "sale"
            elif move_type in self.env['account.move'].get_purchase_types(include_receipts=True):
                journal_type = "purchase"
            else:
                raise UserError(_("The journal in which to upload the invoice is not specified. "))
            self = self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(self.env.company),
                ('type', '=', journal_type),
            ], limit=1)

        attachments = self.env['ir.attachment'].browse(attachment_ids)
        if not attachments:
            raise UserError(_("No attachment was provided"))

        if not self:
            raise UserError(_("No journal found"))

        # As we are coming from the journal, we assume that each attachments
        # will create an invoice with a tentative to enhance with EDI / OCR..
        all_invoices = self.env['account.move']
        for attachment in attachments:
            invoice = self.env['account.move'].create({
                'journal_id': self.id,
                'move_type': move_type,
            })

            invoice._extend_with_attachments(attachment, new=True)

            all_invoices |= invoice

            invoice.with_context(
                account_predictive_bills_disable_prediction=True,
                no_new_invoice=True,
            ).message_post(attachment_ids=attachment.ids)

            attachment.write({'res_model': 'account.move', 'res_id': invoice.id})

        return all_invoices

    def create_document_from_attachment(self, attachment_ids):
        """ Create the invoices from files.
         :return: A action redirecting to account.move tree/form view.
        """
        invoices = self._create_document_from_attachment(attachment_ids)
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
                'views': [[False, "list"], [False, "kanban"], [False, "form"]],
                'view_mode': 'list, kanban, form',
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
                        'name': _('Securisation of %s - %s', seq_field, journal.name),
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

    # TODO move to `account_reports` in master (simple read_group)
    def _get_journal_bank_account_balance(self, domain=None):
        r''' Get the bank balance of the current journal by filtering the journal items using the journal's accounts.

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

    def _get_available_payment_method_lines(self, payment_type):
        """
        This getter is here to allow filtering the payment method lines if needed in other modules.
        It does NOT serve as a general getter to get the lines.

        For example, it'll be extended to filter out lines from inactive payment providers in the payment module.
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
        return self.filtered_domain(self.env['account.payment.method']._get_payment_method_domain(payment_method_code))

    def _process_reference_for_sale_order(self, order_reference):
        '''
        returns the order reference to be used for the payment.
        Hook to be overriden: see l10n_ch for an example.
        '''
        self.ensure_one()
        return order_reference
