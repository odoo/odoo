# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
from bisect import bisect_left
from collections import defaultdict
import re

ACCOUNT_REGEX = re.compile(r'(?:(\S*\d+\S*)\s)?(.*)')
ACCOUNT_CODE_REGEX = re.compile(r'^[A-Za-z0-9.]+$')

class AccountAccount(models.Model):
    _name = "account.account"
    _inherit = ['mail.thread']
    _description = "Account"
    _order = "is_off_balance, code, company_id"
    _check_company_auto = True

    @api.constrains('account_type', 'reconcile')
    def _check_reconcile(self):
        for account in self:
            if account.account_type in ('asset_receivable', 'liability_payable') and not account.reconcile:
                raise ValidationError(_('You cannot have a receivable/payable account that is not reconcilable. (account code: %s)', account.code))

    @api.constrains('account_type')
    def _check_account_type_unique_current_year_earning(self):
        result = self._read_group(
            domain=[('account_type', '=', 'equity_unaffected')],
            fields=['company_id', 'ids:array_agg(id)'],
            groupby=['company_id'],
        )
        for res in result:
            if res.get('company_id_count', 0) >= 2:
                account_unaffected_earnings = self.browse(res['ids'])
                raise ValidationError(_('You cannot have more than one account with "Current Year Earnings" as type. (accounts: %s)', [a.code for a in account_unaffected_earnings]))

    name = fields.Char(string="Account Name", required=True, index='trigram', tracking=True)
    currency_id = fields.Many2one('res.currency', string='Account Currency', tracking=True,
        help="Forces all journal items in this account to have a specific currency (i.e. bank journals). If no currency is set, entries can use any currency.")
    code = fields.Char(size=64, required=True, tracking=True)
    deprecated = fields.Boolean(default=False, tracking=True)
    used = fields.Boolean(compute='_compute_used', search='_search_used')
    account_type = fields.Selection(
        selection=[
            ("asset_receivable", "Receivable"),
            ("asset_cash", "Bank and Cash"),
            ("asset_current", "Current Assets"),
            ("asset_non_current", "Non-current Assets"),
            ("asset_prepayments", "Prepayments"),
            ("asset_fixed", "Fixed Assets"),
            ("liability_payable", "Payable"),
            ("liability_credit_card", "Credit Card"),
            ("liability_current", "Current Liabilities"),
            ("liability_non_current", "Non-current Liabilities"),
            ("equity", "Equity"),
            ("equity_unaffected", "Current Year Earnings"),
            ("income", "Income"),
            ("income_other", "Other Income"),
            ("expense", "Expenses"),
            ("expense_depreciation", "Depreciation"),
            ("expense_direct_cost", "Cost of Revenue"),
            ("off_balance", "Off-Balance Sheet"),
        ],
        string="Type", tracking=True,
        required=True,
        compute='_compute_account_type', store=True, readonly=False, precompute=True,
        help="Account Type is used for information purpose, to generate country-specific legal reports, and set the rules to close a fiscal year and generate opening entries."
    )
    include_initial_balance = fields.Boolean(string="Bring Accounts Balance Forward",
        help="Used in reports to know if we should consider journal items from the beginning of time instead of from the fiscal year only. Account types that should be reset to zero at each new fiscal year (like expenses, revenue..) should not have this option set.",
        compute="_compute_include_initial_balance",
        store=True)
    internal_group = fields.Selection(
        selection=[
            ('equity', 'Equity'),
            ('asset', 'Asset'),
            ('liability', 'Liability'),
            ('income', 'Income'),
            ('expense', 'Expense'),
            ('off_balance', 'Off Balance'),
        ],
        string="Internal Group", readonly=True, compute="_compute_internal_group", store=True
    )
    #has_unreconciled_entries = fields.Boolean(compute='_compute_has_unreconciled_entries',
    #    help="The account has at least one unreconciled debit and credit since last time the invoices & payments matching was performed.")
    reconcile = fields.Boolean(string='Allow Reconciliation', tracking=True,
        compute='_compute_reconcile', store=True, readonly=False,
        help="Check this box if this account allows invoices & payments matching of journal items.")
    tax_ids = fields.Many2many('account.tax', 'account_account_tax_default_rel',
        'account_id', 'tax_id', string='Default Taxes',
        check_company=True,
        context={'append_type_to_tax_name': True})
    note = fields.Text('Internal Notes', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
        default=lambda self: self.env.company)
    tag_ids = fields.Many2many('account.account.tag', 'account_account_account_tag', string='Tags', help="Optional tags you may want to assign for custom reporting")
    group_id = fields.Many2one('account.group', compute='_compute_account_group', store=True, readonly=True,
                               help="Account prefixes can determine account groups.")
    root_id = fields.Many2one('account.root', compute='_compute_account_root', store=True)
    allowed_journal_ids = fields.Many2many('account.journal', string="Allowed Journals", help="Define in which journals this account can be used. If empty, can be used in all journals.")
    opening_debit = fields.Monetary(string="Opening Debit", compute='_compute_opening_debit_credit', inverse='_set_opening_debit')
    opening_credit = fields.Monetary(string="Opening Credit", compute='_compute_opening_debit_credit', inverse='_set_opening_credit')
    opening_balance = fields.Monetary(string="Opening Balance", compute='_compute_opening_debit_credit', inverse='_set_opening_balance')

    is_off_balance = fields.Boolean(compute='_compute_is_off_balance', default=False, store=True, readonly=True)

    current_balance = fields.Float(compute='_compute_current_balance')
    related_taxes_amount = fields.Integer(compute='_compute_related_taxes_amount')

    _sql_constraints = [
        ('code_company_uniq', 'unique (code,company_id)', 'The code of the account must be unique per company !')
    ]

    non_trade = fields.Boolean(default=False,
                               help="If set, this account will belong to Non Trade Receivable/Payable in reports and filters.\n"
                                    "If not, this account will belong to Trade Receivable/Payable in reports and filters.")

    @api.constrains('reconcile', 'internal_group', 'tax_ids')
    def _constrains_reconcile(self):
        for record in self:
            if record.internal_group == 'off_balance':
                if record.reconcile:
                    raise UserError(_('An Off-Balance account can not be reconcilable'))
                if record.tax_ids:
                    raise UserError(_('An Off-Balance account can not have taxes'))

    @api.constrains('allowed_journal_ids')
    def _constrains_allowed_journal_ids(self):
        self.env['account.move.line'].flush_model(['account_id', 'journal_id'])
        self.flush_recordset(['allowed_journal_ids'])
        self._cr.execute("""
            SELECT aml.id
            FROM account_move_line aml
            WHERE aml.account_id in %s
            AND EXISTS (SELECT 1 FROM account_account_account_journal_rel WHERE account_account_id = aml.account_id)
            AND NOT EXISTS (SELECT 1 FROM account_account_account_journal_rel WHERE account_account_id = aml.account_id AND account_journal_id = aml.journal_id)
        """, [tuple(self.ids)])
        ids = self._cr.fetchall()
        if ids:
            raise ValidationError(_('Some journal items already exist with this account but in other journals than the allowed ones.'))

    @api.constrains('currency_id')
    def _check_journal_consistency(self):
        ''' Ensure the currency set on the journal is the same as the currency set on the
        linked accounts.
        '''
        if not self:
            return

        self.env['account.account'].flush_model(['currency_id'])
        self.env['account.journal'].flush_model([
            'currency_id',
            'default_account_id',
            'suspense_account_id',
        ])
        self.env['account.payment.method'].flush_model(['payment_type'])
        self.env['account.payment.method.line'].flush_model(['payment_method_id', 'payment_account_id'])

        self._cr.execute('''
            SELECT
                account.id,
                journal.id
            FROM account_journal journal
            JOIN res_company company ON company.id = journal.company_id
            JOIN account_account account ON account.id = journal.default_account_id
            WHERE journal.currency_id IS NOT NULL
            AND journal.currency_id != company.currency_id
            AND account.currency_id != journal.currency_id
            AND account.id IN %(accounts)s

            UNION ALL

            SELECT
                account.id,
                journal.id
            FROM account_journal journal
            JOIN res_company company ON company.id = journal.company_id
            JOIN account_payment_method_line apml ON apml.journal_id = journal.id
            JOIN account_payment_method apm on apm.id = apml.payment_method_id
            JOIN account_account account ON account.id = COALESCE(apml.payment_account_id, company.account_journal_payment_debit_account_id)
            WHERE journal.currency_id IS NOT NULL
            AND journal.currency_id != company.currency_id
            AND account.currency_id != journal.currency_id
            AND apm.payment_type = 'inbound'
            AND account.id IN %(accounts)s

            UNION ALL

            SELECT
                account.id,
                journal.id
            FROM account_journal journal
            JOIN res_company company ON company.id = journal.company_id
            JOIN account_payment_method_line apml ON apml.journal_id = journal.id
            JOIN account_payment_method apm on apm.id = apml.payment_method_id
            JOIN account_account account ON account.id = COALESCE(apml.payment_account_id, company.account_journal_payment_credit_account_id)
            WHERE journal.currency_id IS NOT NULL
            AND journal.currency_id != company.currency_id
            AND account.currency_id != journal.currency_id
            AND apm.payment_type = 'outbound'
            AND account.id IN %(accounts)s
        ''', {
            'accounts': tuple(self.ids)
        })
        res = self._cr.fetchone()
        if res:
            account = self.env['account.account'].browse(res[0])
            journal = self.env['account.journal'].browse(res[1])
            raise ValidationError(_(
                "The foreign currency set on the journal '%(journal)s' and the account '%(account)s' must be the same.",
                journal=journal.display_name,
                account=account.display_name
            ))

    @api.constrains('company_id')
    def _check_company_consistency(self):
        if not self:
            return

        self.env['account.move.line'].flush_model(['account_id', 'company_id'])
        self.flush_recordset(['company_id'])
        self._cr.execute('''
            SELECT line.id
            FROM account_move_line line
            JOIN account_account account ON account.id = line.account_id
            WHERE line.account_id IN %s
            AND line.company_id != account.company_id
        ''', [tuple(self.ids)])
        if self._cr.fetchone():
            raise UserError(_("You can't change the company of your account since there are some journal items linked to it."))

    @api.constrains('account_type')
    def _check_account_type_sales_purchase_journal(self):
        if not self:
            return

        self.env['account.account'].flush_model(['account_type'])
        self.env['account.journal'].flush_model(['type', 'default_account_id'])
        self._cr.execute('''
            SELECT account.id
            FROM account_account account
            JOIN account_journal journal ON journal.default_account_id = account.id
            WHERE account.id IN %s
            AND account.account_type IN ('asset_receivable', 'liability_payable')
            AND journal.type IN ('sale', 'purchase')
            LIMIT 1;
        ''', [tuple(self.ids)])

        if self._cr.fetchone():
            raise ValidationError(_("The account is already in use in a 'sale' or 'purchase' journal. This means that the account's type couldn't be 'receivable' or 'payable'."))

    @api.constrains('reconcile')
    def _check_used_as_journal_default_debit_credit_account(self):
        accounts = self.filtered(lambda a: not a.reconcile)
        if not accounts:
            return

        self.flush_recordset(['reconcile'])
        self.env['account.journal'].flush_model(['company_id', 'default_account_id'])
        self.env['res.company'].flush_model(['account_journal_payment_credit_account_id', 'account_journal_payment_debit_account_id'])
        self.env['account.payment.method.line'].flush_model(['journal_id', 'payment_account_id'])

        self._cr.execute('''
            SELECT journal.id
            FROM account_journal journal
            JOIN res_company company on journal.company_id = company.id
            LEFT JOIN account_payment_method_line apml ON journal.id = apml.journal_id
            WHERE (
                company.account_journal_payment_credit_account_id IN %(accounts)s
                AND company.account_journal_payment_credit_account_id != journal.default_account_id
                ) OR (
                company.account_journal_payment_debit_account_id in %(accounts)s
                AND company.account_journal_payment_debit_account_id != journal.default_account_id
                ) OR (
                apml.payment_account_id IN %(accounts)s
                AND apml.payment_account_id != journal.default_account_id
            )
        ''', {
            'accounts': tuple(accounts.ids),
        })

        rows = self._cr.fetchall()
        if rows:
            journals = self.env['account.journal'].browse([r[0] for r in rows])
            raise ValidationError(_(
                "This account is configured in %(journal_names)s journal(s) (ids %(journal_ids)s) as payment debit or credit account. This means that this account's type should be reconcilable.",
                journal_names=journals.mapped('display_name'),
                journal_ids=journals.ids
            ))

    @api.constrains('code')
    def _check_account_code(self):
        for account in self:
            if not re.match(ACCOUNT_CODE_REGEX, account.code):
                raise ValidationError(_(
                    "The account code can only contain alphanumeric characters and dots."
                ))

    @api.constrains('account_type')
    def _check_account_is_bank_journal_bank_account(self):
        self.env['account.account'].flush_model(['account_type'])
        self.env['account.journal'].flush_model(['type', 'default_account_id'])
        self._cr.execute('''
            SELECT journal.id
              FROM account_journal journal
              JOIN account_account account ON journal.default_account_id = account.id
             WHERE account.account_type IN ('asset_receivable', 'liability_payable')
             LIMIT 1;
        ''', [tuple(self.ids)])

        if self._cr.fetchone():
            raise ValidationError(_("You cannot change the type of an account set as Bank Account on a journal to Receivable or Payable."))

    @api.depends('code')
    def _compute_account_root(self):
        # this computes the first 2 digits of the account.
        # This field should have been a char, but the aim is to use it in a side panel view with hierarchy, and it's only supported by many2one fields so far.
        # So instead, we make it a many2one to a psql view with what we need as records.
        for record in self:
            record.root_id = (ord(record.code[0]) * 1000 + ord(record.code[1:2] or '\x00')) if record.code else False

    @api.depends('code')
    def _compute_account_group(self):
        if self.ids:
            self.env['account.group']._adapt_accounts_for_account_groups(self)
        else:
            self.group_id = False

    def _search_used(self, operator, value):
        if operator not in ['=', '!='] or not isinstance(value, bool):
            raise UserError(_('Operation not supported'))
        if operator != '=':
            value = not value
        self._cr.execute("""
            SELECT id FROM account_account account
            WHERE EXISTS (SELECT 1 FROM account_move_line aml WHERE aml.account_id = account.id LIMIT 1)
        """)
        return [('id', 'in' if value else 'not in', [r[0] for r in self._cr.fetchall()])]

    def _compute_used(self):
        ids = set(self._search_used('=', True)[0][2])
        for record in self:
            record.used = record.id in ids

    @api.model
    def _search_new_account_code(self, company, digits, prefix):
        for num in range(1, 10000):
            new_code = str(prefix.ljust(digits - 1, '0')) + str(num)
            rec = self.search([('code', '=', new_code), ('company_id', '=', company.id)], limit=1)
            if not rec:
                return new_code
        raise UserError(_('Cannot generate an unused account code.'))

    def _compute_current_balance(self):
        balances = {
            read['account_id'][0]: read['balance']
            for read in self.env['account.move.line']._read_group(
                domain=[('account_id', 'in', self.ids), ('parent_state', '=', 'posted')],
                fields=['balance', 'account_id'],
                groupby=['account_id'],
            )
        }
        for record in self:
            record.current_balance = balances.get(record.id, 0)

    def _compute_related_taxes_amount(self):
        for record in self:
            record.related_taxes_amount = self.env['account.tax'].search_count([
                '|',
                ('invoice_repartition_line_ids.account_id', '=', record.id),
                ('refund_repartition_line_ids.account_id', '=', record.id),
            ])

    def _compute_opening_debit_credit(self):
        self.opening_debit = 0
        self.opening_credit = 0
        self.opening_balance = 0
        if not self.ids:
            return
        self.env.cr.execute("""
            SELECT line.account_id,
                   SUM(line.balance) AS balance,
                   SUM(line.debit) AS debit,
                   SUM(line.credit) AS credit
              FROM account_move_line line
              JOIN res_company comp ON comp.id = line.company_id
             WHERE line.move_id = comp.account_opening_move_id
               AND line.account_id IN %s
             GROUP BY line.account_id
        """, [tuple(self.ids)])
        result = {r['account_id']: r for r in self.env.cr.dictfetchall()}
        for record in self:
            res = result.get(record.id) or {'debit': 0, 'credit': 0, 'balance': 0}
            record.opening_debit = res['debit']
            record.opening_credit = res['credit']
            record.opening_balance = res['balance']

    @api.depends('code')
    def _compute_account_type(self):
        """ Compute the account type based on the account code.
        Search for the closest parent account code and sets the account type according to the parent.
        If there is no parent (e.g. the account code is lower than any other existing account code),
        the account type will be set to 'asset_current'.
        """
        accounts_to_process = self.filtered(lambda r: r.code and not r.account_type)
        all_accounts = self.search_read(
            domain=[('company_id', 'in', accounts_to_process.company_id.ids)],
            fields=['code', 'account_type', 'company_id'],
            order='code',
        )
        accounts_with_codes = defaultdict(dict)
        # We want to group accounts by company to only search for account codes of the current company
        for account in all_accounts:
            accounts_with_codes[account['company_id'][0]][account['code']] = account['account_type']
        for account in accounts_to_process:
            codes_list = list(accounts_with_codes[account.company_id.id].keys())
            closest_index = bisect_left(codes_list, account.code) - 1
            account.account_type = accounts_with_codes[account.company_id.id][codes_list[closest_index]] if closest_index != -1 else 'asset_current'

    @api.depends('internal_group')
    def _compute_is_off_balance(self):
        for account in self:
            account.is_off_balance = account.internal_group == "off_balance"

    @api.depends('account_type')
    def _compute_include_initial_balance(self):
        for account in self:
            account.include_initial_balance = account.account_type not in ('income', 'income_other', 'expense', 'expense_depreciation', 'expense_direct_cost', 'off_balance')

    @api.depends('account_type')
    def _compute_internal_group(self):
        for account in self:
            if account.account_type:
                account.internal_group = 'off_balance' if account.account_type == 'off_balance' else account.account_type.split('_')[0]

    @api.depends('account_type')
    def _compute_reconcile(self):
        for account in self:
            account.reconcile = account.account_type in ('asset_receivable', 'liability_payable')

    def _set_opening_debit(self):
        for record in self:
            record._set_opening_debit_credit(record.opening_debit, 'debit')

    def _set_opening_credit(self):
        for record in self:
            record._set_opening_debit_credit(record.opening_credit, 'credit')

    def _set_opening_balance(self):
        for account in self:
            if account.opening_balance:
                side = 'debit' if account.opening_balance > 0 else 'credit'
                account._set_opening_debit_credit(abs(account.opening_balance), side)

    def _set_opening_debit_credit(self, amount, field):
        """ Generic function called by both opening_debit and opening_credit's
        inverse function. 'Amount' parameter is the value to be set, and field
        either 'debit' or 'credit', depending on which one of these two fields
        got assigned.
        """
        self.company_id.create_op_move_if_non_existant()
        opening_move = self.company_id.account_opening_move_id

        if opening_move.state == 'draft':
            # check whether we should create a new move line or modify an existing one
            account_op_lines = self.env['account.move.line'].search([('account_id', '=', self.id),
                                                                      ('move_id','=', opening_move.id),
                                                                      (field,'!=', False),
                                                                      (field,'!=', 0.0)]) # 0.0 condition important for import

            if account_op_lines:
                op_aml_debit = sum(account_op_lines.mapped('debit'))
                op_aml_credit = sum(account_op_lines.mapped('credit'))

                # There might be more than one line on this account if the opening entry was manually edited
                # If so, we need to merge all those lines into one before modifying its balance
                opening_move_line = account_op_lines[0]
                if len(account_op_lines) > 1:
                    merge_write_cmd = [(1, opening_move_line.id, {'debit': op_aml_debit, 'credit': op_aml_credit, 'partner_id': None ,'name': _("Opening balance")})]
                    unlink_write_cmd = [(2, line.id) for line in account_op_lines[1:]]
                    opening_move.write({'line_ids': merge_write_cmd + unlink_write_cmd})

                if amount:
                    # modify the line
                    opening_move_line.with_context(check_move_validity=False)[field] = amount
                else:
                    # delete the line (no need to keep a line with value = 0)
                    opening_move_line.with_context(check_move_validity=False).unlink()

            elif amount:
                # create a new line, as none existed before
                self.env['account.move.line'].with_context(check_move_validity=False).create({
                        'name': _('Opening balance'),
                        field: amount,
                        'move_id': opening_move.id,
                        'account_id': self.id,
                })

            # Then, we automatically balance the opening move, to make sure it stays valid
            if not 'import_file' in self.env.context:
                # When importing a file, avoid recomputing the opening move for each account and do it at the end, for better performances
                self.company_id._auto_balance_opening_move()

    @api.model
    def default_get(self, default_fields):
        """If we're creating a new account through a many2one, there are chances that we typed the account code
        instead of its name. In that case, switch both fields values.
        """
        if 'name' not in default_fields and 'code' not in default_fields:
            return super().default_get(default_fields)
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
    def _get_most_frequent_accounts_for_partner(self, company_id, partner_id, move_type, filter_never_user_accounts=False, limit=None):
        """
        Returns the accounts ordered from most frequent to least frequent for a given partner
        and filtered according to the move type
        :param company_id: the company id
        :param partner_id: the partner id for which we want to retrieve the most frequent accounts
        :param move_type: the type of the move to know which type of accounts to retrieve
        :param filter_never_user_accounts: True if we should filter out accounts never used for the partner
        :param limit: the maximum number of accounts to retrieve
        :returns: List of account ids, ordered by frequency (from most to least frequent)
        """
        join = "INNER JOIN" if filter_never_user_accounts else "LEFT JOIN"
        limit = f"LIMIT {limit:d}" if limit else ""
        where_internal_group = ""
        if move_type in self.env['account.move'].get_inbound_types(include_receipts=True):
            where_internal_group = "AND account.internal_group = 'income'"
        elif move_type in self.env['account.move'].get_outbound_types(include_receipts=True):
            where_internal_group = "AND account.internal_group = 'expense'"
        self._cr.execute(f"""
            SELECT account.id
              FROM account_account account
            {join} account_move_line aml
                ON aml.account_id  = account.id
                AND aml.partner_id = %s
                AND account.deprecated = FALSE
                AND account.company_id = aml.company_id
                AND aml.date >= now() - interval '2 years'
              WHERE account.company_id = %s
                   {where_internal_group}
            GROUP BY account.id
            ORDER BY COUNT(aml.id) DESC, account.code
                   {limit}
        """, [partner_id, company_id])
        return [r[0] for r in self._cr.fetchall()]

    @api.model
    def _get_most_frequent_account_for_partner(self, company_id, partner_id, move_type=None):
        most_frequent_account = self._get_most_frequent_accounts_for_partner(company_id, partner_id, move_type, filter_never_user_accounts=True, limit=1)
        return most_frequent_account[0] if most_frequent_account else False

    @api.model
    def _order_accounts_by_frequency_for_partner(self, company_id, partner_id, move_type=None):
        return self._get_most_frequent_accounts_for_partner(company_id, partner_id, move_type)

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if not name and self._context.get('partner_id') and self._context.get('move_type'):
            return self._order_accounts_by_frequency_for_partner(
                            self.env.company.id, self._context.get('partner_id'), self._context.get('move_type'))
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', '=ilike', name.split(' ')[0] + '%'), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

    @api.onchange('account_type')
    def _onchange_account_type(self):
        if self.internal_group == 'off_balance':
            self.tax_ids = False
        elif self.internal_group == 'income' and not self.tax_ids:
            self.tax_ids = self.company_id.account_sale_tax_id
        elif self.internal_group == 'expense' and not self.tax_ids:
            self.tax_ids = self.company_id.account_purchase_tax_id

    def _split_code_name(self, code_name):
        # We only want to split the name on the first word if there is a digit in it
        code, name = ACCOUNT_REGEX.match(code_name or '').groups()
        return code, name.strip()

    @api.onchange('name')
    def _onchange_name(self):
        code, name = self._split_code_name(self.name)
        if code:
            self.name = name
            self.code = code

    def name_get(self):
        result = []
        for account in self:
            name = account.code + ' ' + account.name
            result.append((account.id, name))
        return result

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        if default.get('code', False):
            return super(AccountAccount, self).copy(default)
        try:
            default['code'] = (str(int(self.code) + 10) or '').zfill(len(self.code))
            default.setdefault('name', _("%s (copy)") % (self.name or ''))
            while self.env['account.account'].search([('code', '=', default['code']),
                                                      ('company_id', '=', default.get('company_id', False) or self.company_id.id)], limit=1):
                default['code'] = (str(int(default['code']) + 10) or '')
                default['name'] = _("%s (copy)") % (self.name or '')
        except ValueError:
            default['code'] = _("%s.copy") % (self.code or '')
            default['name'] = self.name
        return super(AccountAccount, self).copy(default)

    @api.model
    def load(self, fields, data):
        """ Overridden for better performances when importing a list of account
        with opening debit/credit. In that case, the auto-balance is postpone
        until the whole file has been imported.
        """
        rslt = super(AccountAccount, self).load(fields, data)

        if 'import_file' in self.env.context:
            companies = self.search([('id', 'in', rslt['ids'])]).mapped('company_id')
            for company in companies:
                company._auto_balance_opening_move()
                # the current_balance of the account only includes posted moves and
                # would always amount to 0 after the import if we didn't post the opening move
                company.account_opening_move_id.action_post()
        return rslt

    def _toggle_reconcile_to_true(self):
        '''Toggle the `reconcile´ boolean from False -> True

        Note that: lines with debit = credit = amount_currency = 0 are set to `reconciled´ = True
        '''
        if not self.ids:
            return None
        query = """
            UPDATE account_move_line SET
                reconciled = CASE WHEN debit = 0 AND credit = 0 AND amount_currency = 0
                    THEN true ELSE false END,
                amount_residual = (debit-credit),
                amount_residual_currency = amount_currency
            WHERE full_reconcile_id IS NULL and account_id IN %s
        """
        self.env.cr.execute(query, [tuple(self.ids)])

    def _toggle_reconcile_to_false(self):
        '''Toggle the `reconcile´ boolean from True -> False

        Note that it is disallowed if some lines are partially reconciled.
        '''
        if not self.ids:
            return None
        partial_lines_count = self.env['account.move.line'].search_count([
            ('account_id', 'in', self.ids),
            ('full_reconcile_id', '=', False),
            ('|'),
            ('matched_debit_ids', '!=', False),
            ('matched_credit_ids', '!=', False),
        ])
        if partial_lines_count > 0:
            raise UserError(_('You cannot switch an account to prevent the reconciliation '
                              'if some partial reconciliations are still pending.'))
        query = """
            UPDATE account_move_line
                SET amount_residual = 0, amount_residual_currency = 0
            WHERE full_reconcile_id IS NULL AND account_id IN %s
        """
        self.env.cr.execute(query, [tuple(self.ids)])

    @api.model
    def name_create(self, name):
        """ Split the account name into account code and account name in import.
        When importing a file with accounts, the account code and name may be both entered in the name column.
        In this case, the name will be split into code and name.
        """
        if 'import_file' in self.env.context:
            code, name = self._split_code_name(name)
            return self.create({'code': code, 'name': name}).name_get()[0]
        raise ValueError(_("The values for the created account need to be verified."))

    def write(self, vals):
        # Do not allow changing the company_id when account_move_line already exist
        if vals.get('company_id', False):
            move_lines = self.env['account.move.line'].search([('account_id', 'in', self.ids)], limit=1)
            for account in self:
                if (account.company_id.id != vals['company_id']) and move_lines:
                    raise UserError(_('You cannot change the owner company of an account that already contains journal items.'))
        if 'reconcile' in vals:
            if vals['reconcile']:
                self.filtered(lambda r: not r.reconcile)._toggle_reconcile_to_true()
            else:
                self.filtered(lambda r: r.reconcile)._toggle_reconcile_to_false()

        if vals.get('currency_id'):
            for account in self:
                if self.env['account.move.line'].search_count([('account_id', '=', account.id), ('currency_id', 'not in', (False, vals['currency_id']))]):
                    raise UserError(_('You cannot set a currency on this account as it already has some journal entries having a different foreign currency.'))

        return super(AccountAccount, self).write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_contains_journal_items(self):
        if self.env['account.move.line'].search([('account_id', 'in', self.ids)], limit=1):
            raise UserError(_('You cannot perform this action on an account that contains journal items.'))

    @api.ondelete(at_uninstall=False)
    def _unlink_except_account_set_on_customer(self):
        #Checking whether the account is set as a property to any Partner or not
        values = ['account.account,%s' % (account_id,) for account_id in self.ids]
        partner_prop_acc = self.env['ir.property'].sudo().search([('value_reference', 'in', values)], limit=1)
        if partner_prop_acc:
            account_name = partner_prop_acc.get_by_record().display_name
            raise UserError(
                _('You cannot remove/deactivate the account %s which is set on a customer or vendor.', account_name)
            )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_linked_to_fiscal_position(self):
        if self.env['account.fiscal.position.account'].search(['|', ('account_src_id', 'in', self.ids), ('account_dest_id', 'in', self.ids)], limit=1):
            raise UserError(_('You cannot remove/deactivate the accounts "%s" which are set on the account mapping of a fiscal position.', ', '.join(f"{a.code} - {a.name}" for a in self)))

    @api.ondelete(at_uninstall=False)
    def _unlink_except_linked_to_tax_repartition_line(self):
        if self.env['account.tax.repartition.line'].search([('account_id', 'in', self.ids)], limit=1):
            raise UserError(_('You cannot remove/deactivate the accounts "%s" which are set on a tax repartition line.', ', '.join(f"{a.code} - {a.name}" for a in self)))

    def action_read_account(self):
        self.ensure_one()
        return {
            'name': self.display_name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.account',
            'res_id': self.id,
        }

    def action_duplicate_accounts(self):
        for account in self.browse(self.env.context['active_ids']):
            account.copy()

    def action_open_related_taxes(self):
        related_taxes_ids = self.env['account.tax'].search([
            '|',
            ('invoice_repartition_line_ids.account_id', '=', self.id),
            ('refund_repartition_line_ids.account_id', '=', self.id),
        ]).ids
        return {
            'type': 'ir.actions.act_window',
            'name': _('Taxes'),
            'res_model': 'account.tax',
            'view_type': 'list',
            'view_mode': 'list',
            'views': [[False, 'list'], [False, 'form']],
            'domain': [('id', 'in', related_taxes_ids)],
        }

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Chart of Accounts'),
            'template': '/account/static/xls/coa_import_template.xlsx'
        }]


class AccountGroup(models.Model):
    _name = "account.group"
    _description = 'Account Group'
    _parent_store = True
    _order = 'code_prefix_start'

    parent_id = fields.Many2one('account.group', index=True, ondelete='cascade', readonly=True)
    parent_path = fields.Char(index=True, unaccent=False)
    name = fields.Char(required=True)
    code_prefix_start = fields.Char()
    code_prefix_end = fields.Char()
    company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company)

    _sql_constraints = [
        (
            'check_length_prefix',
            'CHECK(char_length(COALESCE(code_prefix_start, \'\')) = char_length(COALESCE(code_prefix_end, \'\')))',
            'The length of the starting and the ending code prefix must be the same'
        ),
    ]

    @api.onchange('code_prefix_start')
    def _onchange_code_prefix_start(self):
        if not self.code_prefix_end or self.code_prefix_end < self.code_prefix_start:
            self.code_prefix_end = self.code_prefix_start

    @api.onchange('code_prefix_end')
    def _onchange_code_prefix_end(self):
        if not self.code_prefix_start or self.code_prefix_start > self.code_prefix_end:
            self.code_prefix_start = self.code_prefix_end

    def name_get(self):
        result = []
        for group in self:
            prefix = group.code_prefix_start and str(group.code_prefix_start)
            if prefix and group.code_prefix_end != group.code_prefix_start:
                prefix += '-' + str(group.code_prefix_end)
            name = (prefix and (prefix + ' ') or '') + group.name
            result.append((group.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if operator == 'ilike' and not (name or '').strip():
            domain = []
        else:
            criteria_operator = ['|'] if operator not in expression.NEGATIVE_TERM_OPERATORS else ['&', '!']
            domain = criteria_operator + [('code_prefix_start', '=ilike', name + '%'), ('name', operator, name)]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

    @api.constrains('code_prefix_start', 'code_prefix_end')
    def _constraint_prefix_overlap(self):
        self.flush_model()
        query = """
            SELECT other.id FROM account_group this
            JOIN account_group other
              ON char_length(other.code_prefix_start) = char_length(this.code_prefix_start)
             AND other.id != this.id
             AND other.company_id = this.company_id
             AND (
                other.code_prefix_start <= this.code_prefix_start AND this.code_prefix_start <= other.code_prefix_end
                OR
                other.code_prefix_start >= this.code_prefix_start AND this.code_prefix_end >= other.code_prefix_start
            )
            WHERE this.id IN %(ids)s
        """
        self.env.cr.execute(query, {'ids': tuple(self.ids)})
        res = self.env.cr.fetchall()
        if res:
            raise ValidationError(_('Account Groups with the same granularity can\'t overlap'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'code_prefix_start' in vals and not vals.get('code_prefix_end'):
                vals['code_prefix_end'] = vals['code_prefix_start']
        res_ids = super(AccountGroup, self).create(vals_list)
        res_ids._adapt_accounts_for_account_groups()
        res_ids._adapt_parent_account_group()
        return res_ids

    def write(self, vals):
        res = super(AccountGroup, self).write(vals)
        if 'code_prefix_start' in vals or 'code_prefix_end' in vals:
            self._adapt_accounts_for_account_groups()
            self._adapt_parent_account_group()
        return res

    def unlink(self):
        for record in self:
            account_ids = self.env['account.account'].search([('group_id', '=', record.id)])
            account_ids.write({'group_id': record.parent_id.id})

            children_ids = self.env['account.group'].search([('parent_id', '=', record.id)])
            children_ids.write({'parent_id': record.parent_id.id})
        super(AccountGroup, self).unlink()

    def _adapt_accounts_for_account_groups(self, account_ids=None):
        """Ensure consistency between accounts and account groups.

        Find and set the most specific group matching the code of the account.
        The most specific is the one with the longest prefixes and with the starting
        prefix being smaller than the account code and the ending prefix being greater.
        """
        company_ids = account_ids.company_id.ids if account_ids else self.company_id.ids
        account_ids = account_ids.ids if account_ids else []
        if not company_ids and not account_ids:
            return
        self.flush_model()
        self.env['account.account'].flush_model()

        account_where_clause = ''
        where_params = [tuple(company_ids)]
        if account_ids:
            account_where_clause = 'AND account.id IN %s'
            where_params.append(tuple(account_ids))

        self._cr.execute(f'''
            WITH candidates_account_groups AS (
                SELECT
                    account.id AS account_id,
                    ARRAY_AGG(agroup.id ORDER BY char_length(agroup.code_prefix_start) DESC, agroup.id) AS group_ids
                FROM account_account account
                LEFT JOIN account_group agroup
                    ON agroup.code_prefix_start <= LEFT(account.code, char_length(agroup.code_prefix_start))
                    AND agroup.code_prefix_end >= LEFT(account.code, char_length(agroup.code_prefix_end))
                    AND agroup.company_id = account.company_id
                WHERE account.company_id IN %s {account_where_clause}
                GROUP BY account.id
            )
            UPDATE account_account
            SET group_id = rel.group_ids[1]
            FROM candidates_account_groups rel
            WHERE account_account.id = rel.account_id
        ''', where_params)
        self.env['account.account'].invalidate_model(['group_id'])

    def _adapt_parent_account_group(self):
        """Ensure consistency of the hierarchy of account groups.

        Find and set the most specific parent for each group.
        The most specific is the one with the longest prefixes and with the starting
        prefix being smaller than the child prefixes and the ending prefix being greater.
        """
        if not self:
            return
        self.flush_model()
        query = """
            WITH relation AS (
       SELECT DISTINCT FIRST_VALUE(parent.id) OVER (PARTITION BY child.id ORDER BY child.id, char_length(parent.code_prefix_start) DESC) AS parent_id,
                       child.id AS child_id
                  FROM account_group parent
                  JOIN account_group child
                    ON char_length(parent.code_prefix_start) < char_length(child.code_prefix_start)
                   AND parent.code_prefix_start <= LEFT(child.code_prefix_start, char_length(parent.code_prefix_start))
                   AND parent.code_prefix_end >= LEFT(child.code_prefix_end, char_length(parent.code_prefix_end))
                   AND parent.id != child.id
                   AND parent.company_id = child.company_id
                 WHERE child.company_id IN %(company_ids)s
            )
            UPDATE account_group child
               SET parent_id = relation.parent_id
              FROM relation
             WHERE child.id = relation.child_id;
        """
        self.env.cr.execute(query, {'company_ids': tuple(self.company_id.ids)})
        self.invalidate_model(['parent_id'])
        self.search([('company_id', 'in', self.company_id.ids)])._parent_store_update()


class AccountRoot(models.Model):
    _name = 'account.root'
    _description = 'Account codes first 2 digits'
    _auto = False

    name = fields.Char()
    parent_id = fields.Many2one('account.root')
    company_id = fields.Many2one('res.company')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute('''
            CREATE OR REPLACE VIEW %s AS (
            SELECT DISTINCT ASCII(code) * 1000 + ASCII(SUBSTRING(code,2,1)) AS id,
                   LEFT(code,2) AS name,
                   ASCII(code) AS parent_id,
                   company_id
            FROM account_account WHERE code IS NOT NULL
            UNION ALL
            SELECT DISTINCT ASCII(code) AS id,
                   LEFT(code,1) AS name,
                   NULL::int AS parent_id,
                   company_id
            FROM account_account WHERE code IS NOT NULL
            )''' % (self._table,)
        )
