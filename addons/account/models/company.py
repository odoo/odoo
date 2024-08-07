# -*- coding: utf-8 -*-

from collections import defaultdict
from datetime import timedelta, datetime, date
import calendar

from odoo import fields, models, api, _, Command
from odoo.exceptions import ValidationError, UserError, RedirectWarning
from odoo.tools.mail import is_html_empty
from odoo.tools.misc import format_date
from odoo.tools.float_utils import float_round, float_is_zero
from odoo.addons.account.models.account_move import MAX_HASH_VERSION


MONTH_SELECTION = [
    ('1', 'January'),
    ('2', 'February'),
    ('3', 'March'),
    ('4', 'April'),
    ('5', 'May'),
    ('6', 'June'),
    ('7', 'July'),
    ('8', 'August'),
    ('9', 'September'),
    ('10', 'October'),
    ('11', 'November'),
    ('12', 'December'),
]

PEPPOL_LIST = [
    'AD', 'AL', 'AT', 'BA', 'BE', 'BG', 'CH', 'CY', 'CZ', 'DE', 'DK', 'EE', 'ES', 'FI',
    'FR', 'GB', 'GR', 'HR', 'HU', 'IE', 'IS', 'IT', 'LI', 'LT', 'LU', 'LV', 'MC', 'ME',
    'MK', 'MT', 'NL', 'NO', 'PL', 'PT', 'RO', 'RS', 'SE', 'SI', 'SK', 'SM', 'TR', 'VA',
]

class ResCompany(models.Model):
    _name = "res.company"
    _inherit = ["res.company", "mail.thread"]

    #TODO check all the options/fields are in the views (settings + company form view)
    fiscalyear_last_day = fields.Integer(default=31, required=True)
    fiscalyear_last_month = fields.Selection(MONTH_SELECTION, default='12', required=True)
    period_lock_date = fields.Date(
        string="Journals Entries Lock Date",
        tracking=True,
        help="Only users with the 'Adviser' role can edit accounts prior to and inclusive of this"
             " date. Use it for period locking inside an open fiscal year, for example.")
    fiscalyear_lock_date = fields.Date(
        string="All Users Lock Date",
        tracking=True,
        help="No users, including Advisers, can edit accounts prior to and inclusive of this date."
             " Use it for fiscal year locking for example.")
    tax_lock_date = fields.Date(
        string="Tax Return Lock Date",
        tracking=True,
        help="No users can edit journal entries related to a tax prior and inclusive of this date.")
    max_tax_lock_date = fields.Date(compute='_compute_max_tax_lock_date', recursive=True)  # TODO maybe store
    transfer_account_id = fields.Many2one('account.account',
        check_company=True,
        domain="[('reconcile', '=', True), ('account_type', '=', 'asset_current'), ('deprecated', '=', False)]", string="Inter-Banks Transfer Account", help="Intermediary account used when moving money from a liqity account to another")
    expects_chart_of_accounts = fields.Boolean(string='Expects a Chart of Accounts', default=True)
    chart_template = fields.Selection(selection='_chart_template_selection')
    bank_account_code_prefix = fields.Char(string='Prefix of the bank accounts')
    cash_account_code_prefix = fields.Char(string='Prefix of the cash accounts')
    default_cash_difference_income_account_id = fields.Many2one('account.account', string="Cash Difference Income", check_company=True)
    default_cash_difference_expense_account_id = fields.Many2one('account.account', string="Cash Difference Expense", check_company=True)
    account_journal_suspense_account_id = fields.Many2one('account.account', string='Journal Suspense Account', check_company=True)
    account_journal_payment_debit_account_id = fields.Many2one('account.account', string='Journal Outstanding Receipts', check_company=True)
    account_journal_payment_credit_account_id = fields.Many2one('account.account', string='Journal Outstanding Payments', check_company=True)
    account_journal_early_pay_discount_gain_account_id = fields.Many2one(comodel_name='account.account', string='Cash Discount Write-Off Gain Account', check_company=True)
    account_journal_early_pay_discount_loss_account_id = fields.Many2one(comodel_name='account.account', string='Cash Discount Write-Off Loss Account', check_company=True)
    transfer_account_code_prefix = fields.Char(string='Prefix of the transfer accounts')
    account_sale_tax_id = fields.Many2one('account.tax', string="Default Sale Tax", check_company=True)
    account_purchase_tax_id = fields.Many2one('account.tax', string="Default Purchase Tax", check_company=True)
    tax_calculation_rounding_method = fields.Selection([
        ('round_per_line', 'Round per Line'),
        ('round_globally', 'Round Globally'),
        ], default='round_per_line', string='Tax Calculation Rounding Method')
    currency_exchange_journal_id = fields.Many2one('account.journal', string="Exchange Gain or Loss Journal", domain=[('type', '=', 'general')])
    income_currency_exchange_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Gain Exchange Rate Account",
        check_company=True,
        domain="[('deprecated', '=', False),\
                ('account_type', 'in', ('income', 'income_other'))]")
    expense_currency_exchange_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Loss Exchange Rate Account",
        check_company=True,
        domain="[('deprecated', '=', False), \
                ('account_type', '=', 'expense')]")
    anglo_saxon_accounting = fields.Boolean(string="Use anglo-saxon accounting")
    bank_journal_ids = fields.One2many('account.journal', 'company_id', domain=[('type', '=', 'bank')], string='Bank Journals')
    incoterm_id = fields.Many2one('account.incoterms', string='Default incoterm',
        help='International Commercial Terms are a series of predefined commercial terms used in international transactions.')

    qr_code = fields.Boolean(string='Display QR-code on invoices')

    invoice_is_email = fields.Boolean('Email by default', default=True)
    invoice_is_download = fields.Boolean('Download by default', default=True)
    display_invoice_amount_total_words = fields.Boolean(string='Total amount of invoice in letters')
    account_use_credit_limit = fields.Boolean(
        string='Sales Credit Limit', help='Enable the use of credit limit on partners.')

    #Fields of the setup step for opening move
    account_opening_move_id = fields.Many2one(string='Opening Journal Entry', comodel_name='account.move', help="The journal entry containing the initial balance of all this company's accounts.")
    account_opening_journal_id = fields.Many2one(string='Opening Journal', comodel_name='account.journal', related='account_opening_move_id.journal_id', help="Journal where the opening entry of this company's accounting has been posted.", readonly=False)
    account_opening_date = fields.Date(string='Opening Entry', default=lambda self: fields.Date.context_today(self).replace(month=1, day=1), required=True, help="That is the date of the opening entry.")

    invoice_terms = fields.Html(string='Default Terms and Conditions', translate=True)
    terms_type = fields.Selection([('plain', 'Add a Note'), ('html', 'Add a link to a Web Page')],
                                  string='Terms & Conditions format', default='plain')
    invoice_terms_html = fields.Html(string='Default Terms and Conditions as a Web page', translate=True,
                                     sanitize_attributes=False,
                                     compute='_compute_invoice_terms_html', store=True, readonly=False)

    # Needed in the Point of Sale
    account_default_pos_receivable_account_id = fields.Many2one('account.account', string="Default PoS Receivable Account", check_company=True)

    # Accrual Accounting
    expense_accrual_account_id = fields.Many2one('account.account',
        help="Account used to move the period of an expense",
        check_company=True,
        domain="[('internal_group', '=', 'liability'), ('account_type', 'not in', ('asset_receivable', 'liability_payable'))]")
    revenue_accrual_account_id = fields.Many2one('account.account',
        help="Account used to move the period of a revenue",
        check_company=True,
        domain="[('internal_group', '=', 'asset'), ('account_type', 'not in', ('asset_receivable', 'liability_payable'))]")
    automatic_entry_default_journal_id = fields.Many2one(
        'account.journal',
        domain="[('type', '=', 'general')]",
        check_company=True,
        help="Journal used by default for moving the period of an entry",
    )

    # Technical field to hide country specific fields in company form view
    country_code = fields.Char(related='country_id.code', depends=['country_id'])

    # Taxes
    account_fiscal_country_id = fields.Many2one(
        string="Fiscal Country",
        comodel_name='res.country',
        compute='compute_account_tax_fiscal_country',
        store=True,
        readonly=False,
        help="The country to use the tax reports from for this company")

    account_enabled_tax_country_ids = fields.Many2many(
        string="l10n-used countries",
        comodel_name='res.country',
        compute='_compute_account_enabled_tax_country_ids',
        help="Technical field containing the countries for which this company is using tax-related features"
             "(hence the ones for which l10n modules need to show tax-related fields).")

    # Cash basis taxes
    tax_exigibility = fields.Boolean(string='Use Cash Basis')
    tax_cash_basis_journal_id = fields.Many2one(
        comodel_name='account.journal',
        check_company=True,
        string="Cash Basis Journal")
    account_cash_basis_base_account_id = fields.Many2one(
        comodel_name='account.account',
        check_company=True,
        domain=[('deprecated', '=', False)],
        string="Base Tax Received Account",
        help="Account that will be set on lines created in cash basis journal entry and used to keep track of the "
             "tax base amount.")

    # Storno Accounting
    account_storno = fields.Boolean(string="Storno accounting", readonly=False)

    # Multivat
    fiscal_position_ids = fields.One2many(comodel_name="account.fiscal.position", inverse_name="company_id")
    multi_vat_foreign_country_ids = fields.Many2many(
        string="Foreign VAT countries",
        help="Countries for which the company has a VAT number",
        comodel_name='res.country',
        compute='_compute_multi_vat_foreign_country',
    )

    # Fiduciary mode
    quick_edit_mode = fields.Selection(
        selection=[
            ('out_invoices', 'Customer Invoices'),
            ('in_invoices', 'Vendor Bills'),
            ('out_and_in_invoices', 'Customer Invoices and Vendor Bills')],
        string="Quick encoding")

    # Separate account for allocation of discounts
    account_discount_income_allocation_id = fields.Many2one(comodel_name='account.account', string='Separate account for income discount')
    account_discount_expense_allocation_id = fields.Many2one(comodel_name='account.account', string='Separate account for expense discount')

    def _get_company_root_delegated_field_names(self):
        return super()._get_company_root_delegated_field_names() + [
            'fiscalyear_last_day',
            'fiscalyear_last_month',
            'account_storno',
            'tax_exigibility',
        ]

    @api.constrains('account_opening_move_id', 'fiscalyear_last_day', 'fiscalyear_last_month')
    def _check_fiscalyear_last_day(self):
        # if the user explicitly chooses the 29th of February we allow it:
        # there is no "fiscalyear_last_year" so we do not know his intentions.
        for rec in self:
            if rec.fiscalyear_last_day == 29 and rec.fiscalyear_last_month == '2':
                continue

            if rec.account_opening_date:
                year = rec.account_opening_date.year
            else:
                year = datetime.now().year

            max_day = calendar.monthrange(year, int(rec.fiscalyear_last_month))[1]
            if rec.fiscalyear_last_day > max_day:
                raise ValidationError(_("Invalid fiscal year last day"))

    @api.depends('fiscal_position_ids.foreign_vat')
    def _compute_multi_vat_foreign_country(self):
        company_to_foreign_vat_country = {
            company.id: country_ids
            for company, country_ids in self.env['account.fiscal.position']._read_group(
                domain=[
                    *self.env['account.fiscal.position']._check_company_domain(self),
                    ('foreign_vat', '!=', False),
                ],
                groupby=['company_id'],
                aggregates=['country_id:array_agg'],
            )
        }
        for company in self:
            company.multi_vat_foreign_country_ids = self.env['res.country'].browse(company_to_foreign_vat_country.get(company.id))

    @api.depends('country_id')
    def compute_account_tax_fiscal_country(self):
        for record in self:
            if not record.account_fiscal_country_id:
                record.account_fiscal_country_id = record.country_id

    @api.depends('account_fiscal_country_id')
    def _compute_account_enabled_tax_country_ids(self):
        for record in self:
            if record not in self.env.user.company_ids:
                # can have access to the company form without having access to its content (see base.res_company_rule_erp_manager)
                record.account_enabled_tax_country_ids = False
                continue
            foreign_vat_fpos = self.env['account.fiscal.position'].search([
                *self.env['account.fiscal.position']._check_company_domain(record),
                ('foreign_vat', '!=', False)
            ])
            record.account_enabled_tax_country_ids = foreign_vat_fpos.country_id + record.account_fiscal_country_id

    @api.depends('terms_type')
    def _compute_invoice_terms_html(self):
        for company in self.filtered(lambda company: is_html_empty(company.invoice_terms_html) and company.terms_type == 'html'):
            html = self.env['ir.qweb']._render('account.account_default_terms_and_conditions',
                        {'company_name': company.name, 'company_country': company.country_id.name},
                        raise_if_not_found=False)
            if html:
                company.invoice_terms_html = html

    @api.depends('tax_lock_date', 'parent_id.max_tax_lock_date')
    def _compute_max_tax_lock_date(self):
        for company in self:
            company.max_tax_lock_date = max(company.tax_lock_date or date.min, company.parent_id.sudo().max_tax_lock_date or date.min)

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        for company in companies:
            if root_template := company.parent_ids[0].chart_template:
                def try_loading(company=company):
                    self.env['account.chart.template']._load(
                        root_template,
                        company,
                        install_demo=False,
                    )
                self.env.cr.precommit.add(try_loading)
        return companies

    def get_new_account_code(self, current_code, old_prefix, new_prefix):
        digits = len(current_code)
        return new_prefix + current_code.replace(old_prefix, '', 1).lstrip('0').rjust(digits-len(new_prefix), '0')

    def reflect_code_prefix_change(self, old_code, new_code):
        if not old_code or new_code == old_code:
            return
        accounts = self.env['account.account'].search([
            *self.env['account.account']._check_company_domain(self),
            ('code', '=like', old_code + '%'),
            ('account_type', 'in', ('asset_cash', 'liability_credit_card')),
        ], order='code asc')
        for account in accounts:
            account.write({'code': self.get_new_account_code(account.code, old_code, new_code)})

    def _get_fiscalyear_lock_statement_lines_redirect_action(self, unreconciled_statement_lines):
        """ Get the action redirecting to the statement lines that are not already reconciled when setting a fiscal
        year lock date.

        :param unreconciled_statement_lines: The statement lines.
        :return: A dictionary representing a window action.
        """

        action = {
            'name': _("Unreconciled Transactions"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement.line',
            'context': {'create': False},
        }
        if len(unreconciled_statement_lines) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': unreconciled_statement_lines.id,
            })
        else:
            action.update({
                'view_mode': 'list,form',
                'domain': [('id', 'in', unreconciled_statement_lines.ids)],
            })
        return action

    def _validate_fiscalyear_lock(self, values):
        if values.get('fiscalyear_lock_date'):

            draft_entries = self.env['account.move'].search([
                ('company_id', 'child_of', self.ids),
                ('state', '=', 'draft'),
                ('date', '<=', values['fiscalyear_lock_date'])])
            if draft_entries:
                error_msg = _('There are still unposted entries in the period you want to lock. You should either post or delete them.')
                action_error = {
                    'view_mode': 'tree',
                    'name': _('Unposted Entries'),
                    'res_model': 'account.move',
                    'type': 'ir.actions.act_window',
                    'domain': [('id', 'in', draft_entries.ids)],
                    'search_view_id': [self.env.ref('account.view_account_move_filter').id, 'search'],
                    'views': [[self.env.ref('account.view_move_tree').id, 'list'], [self.env.ref('account.view_move_form').id, 'form']],
                }
                raise RedirectWarning(error_msg, action_error, _('Show unposted entries'))

            unreconciled_statement_lines = self.env['account.bank.statement.line'].search([
                ('company_id', 'child_of', self.ids),
                ('is_reconciled', '=', False),
                ('date', '<=', values['fiscalyear_lock_date']),
                ('move_id.state', 'in', ('draft', 'posted')),
            ])
            if unreconciled_statement_lines:
                error_msg = _("There are still unreconciled bank statement lines in the period you want to lock."
                            "You should either reconcile or delete them.")
                action_error = self._get_fiscalyear_lock_statement_lines_redirect_action(unreconciled_statement_lines)
                raise RedirectWarning(error_msg, action_error, _('Show Unreconciled Bank Statement Line'))

    def _get_user_fiscal_lock_date(self):
        """Get the fiscal lock date for this company depending on the user"""
        lock_date = max(self.period_lock_date or date.min, self.fiscalyear_lock_date or date.min)
        if self.user_has_groups('account.group_account_manager'):
            lock_date = self.fiscalyear_lock_date or date.min
        if self.parent_id:
            # We need to use sudo, since we might not have access to a parent company.
            lock_date = max(lock_date, self.sudo().parent_id._get_user_fiscal_lock_date())
        return lock_date

    def _get_violated_lock_dates(self, accounting_date, has_tax):
        """Get all the lock dates affecting the current accounting_date.
        :param accoutiaccounting_dateng_date: The accounting date
        :param has_tax: If any taxes are involved in the lines of the invoice
        :return: a list of tuples containing the lock dates ordered chronologically.
        """
        self.ensure_one()
        locks = []
        user_lock_date = self._get_user_fiscal_lock_date()
        if accounting_date and user_lock_date and accounting_date <= user_lock_date:
            locks.append((user_lock_date, _('user')))
        tax_lock_date = self.max_tax_lock_date
        if accounting_date and tax_lock_date and has_tax and accounting_date <= tax_lock_date:
            locks.append((tax_lock_date, _('tax')))
        locks.sort()
        return locks

    def write(self, values):
        #restrict the closing of FY if there are still unposted entries
        self._validate_fiscalyear_lock(values)

        # Reflect the change on accounts
        for company in self:
            if values.get('bank_account_code_prefix'):
                new_bank_code = values.get('bank_account_code_prefix') or company.bank_account_code_prefix
                company.reflect_code_prefix_change(company.bank_account_code_prefix, new_bank_code)

            if values.get('cash_account_code_prefix'):
                new_cash_code = values.get('cash_account_code_prefix') or company.cash_account_code_prefix
                company.reflect_code_prefix_change(company.cash_account_code_prefix, new_cash_code)

            #forbid the change of currency_id if there are already some accounting entries existing
            if 'currency_id' in values and values['currency_id'] != company.currency_id.id:
                if company.root_id._existing_accounting():
                    raise UserError(_('You cannot change the currency of the company since some journal items already exist'))

        return super(ResCompany, self).write(values)

    @api.model
    def setting_init_bank_account_action(self):
        """ Called by the 'Bank Accounts' button of the setup bar or from the Financial configuration menu."""
        view_id = self.env.ref('account.setup_bank_account_wizard').id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create a Bank Account'),
            'res_model': 'account.setup.bank.manual.config',
            'target': 'new',
            'view_mode': 'form',
            'views': [[view_id, 'form']],
        }

    @api.model
    def _get_default_opening_move_values(self):
        """ Get the default values to create the opening move.

        :return: A dictionary to be passed to account.move.create.
        """
        self.ensure_one()
        default_journal = self.env['account.journal'].search(
            domain=[
                *self.env['account.journal']._check_company_domain(self),
                ('type', '=', 'general'),
            ],
            limit=1,
        )

        if not default_journal:
            raise UserError(_("Please install a chart of accounts or create a miscellaneous journal before proceeding."))

        return {
            'ref': _('Opening Journal Entry'),
            'company_id': self.id,
            'journal_id': default_journal.id,
            'date': self.account_opening_date - timedelta(days=1),
        }

    def create_op_move_if_non_existant(self):
        """ Creates an empty opening move in 'draft' state for the current company
        if there wasn't already one defined. For this, the function needs at least
        one journal of type 'general' to exist (required by account.move).
        """
        # TO BE REMOVED IN MASTER
        self.ensure_one()
        if not self.account_opening_move_id:
            self.account_opening_move_id = self.env['account.move'].create(self._get_default_opening_move_values())

    def opening_move_posted(self):
        """ Returns true if this company has an opening account move and this move is posted."""
        return bool(self.account_opening_move_id) and self.account_opening_move_id.state == 'posted'

    def get_unaffected_earnings_account(self):
        """ Returns the unaffected earnings account for this company, creating one
        if none has yet been defined.
        """
        unaffected_earnings_type = "equity_unaffected"
        account = self.env['account.account'].search([
            *self.env['account.account']._check_company_domain(self),
            ('account_type', '=', unaffected_earnings_type),
        ])
        if account:
            return account[0]
        # Do not assume '999999' doesn't exist since the user might have created such an account
        # manually.
        code = 999999
        while self.env['account.account'].search([
            *self.env['account.account']._check_company_domain(self),
            ('code', '=', str(code)),
        ]):
            code -= 1
        return self.env['account.account']._load_records([
            {
                'xml_id': f"account.{str(self.id)}_unaffected_earnings_account",
                'values': {
                              'code': str(code),
                              'name': _('Undistributed Profits/Losses'),
                              'account_type': unaffected_earnings_type,
                              'company_id': self.id,
                          },
                'noupdate': True,
            }
        ])

    def get_opening_move_differences(self, opening_move_lines):
        # TO BE REMOVED IN MASTER
        currency = self.currency_id
        balancing_move_line = opening_move_lines.filtered(lambda x: x.account_id == self.get_unaffected_earnings_account())

        debits_sum = credits_sum = 0.0
        for line in opening_move_lines:
            if line != balancing_move_line:
                #skip the autobalancing move line
                debits_sum += line.debit
                credits_sum += line.credit

        difference = abs(debits_sum - credits_sum)
        debit_diff = (debits_sum > credits_sum) and float_round(difference, precision_rounding=currency.rounding) or 0.0
        credit_diff = (debits_sum < credits_sum) and float_round(difference, precision_rounding=currency.rounding) or 0.0
        return debit_diff, credit_diff

    def _auto_balance_opening_move(self):
        """ Checks the opening_move of this company. If it has not been posted yet
        and is unbalanced, balances it with a automatic account.move.line in the
        current year earnings account.
        """
        # TO BE REMOVED IN MASTER
        if self.account_opening_move_id and self.account_opening_move_id.state == 'draft':
            balancing_account = self.get_unaffected_earnings_account()
            currency = self.currency_id

            balancing_move_line = self.account_opening_move_id.line_ids.filtered(lambda x: x.account_id == balancing_account)
            # There could be multiple lines if we imported the balance from unaffected earnings account too
            if len(balancing_move_line) > 1:
                self.account_opening_move_id.line_ids -= balancing_move_line[1:]
                balancing_move_line = balancing_move_line[0]

            debit_diff, credit_diff = self.get_opening_move_differences(self.account_opening_move_id.line_ids)

            if float_is_zero(debit_diff + credit_diff, precision_rounding=currency.rounding):
                if balancing_move_line:
                    # zero difference and existing line : delete the line
                    self.account_opening_move_id.line_ids -= balancing_move_line
            else:
                if balancing_move_line:
                    # Non-zero difference and existing line : edit the line
                    balancing_move_line.write({'debit': credit_diff, 'credit': debit_diff})
                else:
                    # Non-zero difference and no existing line : create a new line
                    self.env['account.move.line'].create({
                        'name': _('Automatic Balancing Line'),
                        'move_id': self.account_opening_move_id.id,
                        'account_id': balancing_account.id,
                        'debit': credit_diff,
                        'credit': debit_diff,
                    })

    def _update_opening_move(self, to_update):
        """ Create or update the opening move for the accounts passed as parameter.

        :param to_update:   A dictionary mapping each account with a tuple (debit, credit).
                            A separated opening line is created for both fields. A None value on debit/credit means the corresponding
                            line will not be updated.
        """
        self.ensure_one()

        # Don't allow to modify the opening move if not in draft.
        opening_move = self.account_opening_move_id
        if opening_move and opening_move.state != 'draft':
            raise UserError(_(
                'You cannot import the "openning_balance" if the opening move (%s) is already posted. \
                If you are absolutely sure you want to modify the opening balance of your accounts, reset the move to draft.',
                self.account_opening_move_id.name,
            ))

        def del_lines(lines):
            nonlocal open_balance
            for line in lines:
                open_balance -= line.balance
                yield Command.delete(line.id)

        def update_vals(account, side, balance, balancing=False):
            nonlocal open_balance
            corresponding_lines = corresponding_lines_per_account[(account, side)]
            currency = account.currency_id or self.currency_id
            amount_currency = balance if balancing else self.currency_id._convert(balance, currency, date=conversion_date)
            open_balance += balance
            if self.currency_id.is_zero(balance):
                yield from del_lines(corresponding_lines)
            elif corresponding_lines:
                line_to_update = corresponding_lines[0]
                open_balance -= line_to_update.balance
                yield Command.update(line_to_update.id, {
                    'balance': balance,
                    'amount_currency': amount_currency,
                })
                yield from del_lines(corresponding_lines[1:])
            else:
                yield Command.create({
                    'name':_("Automatic Balancing Line") if balancing else _("Opening balance"),
                    'account_id': account.id,
                    'balance': balance,
                    'amount_currency': amount_currency,
                    'currency_id': currency.id,
                })

        # Decode the existing opening move.
        corresponding_lines_per_account = defaultdict(lambda: self.env['account.move.line'])
        corresponding_lines_per_account.update(opening_move.line_ids.grouped(lambda line: (
            line.account_id,
            'debit' if line.balance > 0.0 or line.amount_currency > 0.0 else 'credit',
        )))

        # Update the opening move's lines.
        balancing_account = self.get_unaffected_earnings_account()
        open_balance = (
            sum(corresponding_lines_per_account[(balancing_account, 'credit')].mapped('credit'))
            -sum(corresponding_lines_per_account[(balancing_account, 'debit')].mapped('debit'))
        )
        commands = []
        move_values = {'line_ids': commands}
        if opening_move:
            conversion_date = opening_move.date
        else:
            move_values.update(self._get_default_opening_move_values())
            conversion_date = move_values['date']
        for account, (debit, credit) in to_update.items():
            if debit is not None:
                commands.extend(update_vals(account, 'debit', debit))
            if credit is not None:
                commands.extend(update_vals(account, 'credit', -credit))

        commands.extend(update_vals(balancing_account, 'debit', max(-open_balance, 0), balancing=True))
        commands.extend(update_vals(balancing_account, 'credit', -max(open_balance, 0), balancing=True))

        # Nothing to do.
        if not commands:
            return

        if opening_move:
            opening_move.write(move_values)
        else:
            self.account_opening_move_id = self.env['account.move'].create(move_values)

    def action_save_onboarding_sale_tax(self):
        """ Set the onboarding step as done """
        self.env['onboarding.onboarding.step'].action_validate_step('account.onboarding_onboarding_step_sales_tax')

    def get_chart_of_accounts_or_fail(self):
        account = self.env['account.account'].search(self.env['account.account']._check_company_domain(self), limit=1)
        if len(account) == 0:
            action = self.env.ref('account.action_account_config')
            msg = _(
                "We cannot find a chart of accounts for this company, you should configure it. \n"
                "Please go to Account Configuration and select or install a fiscal localization.")
            raise RedirectWarning(msg, action.id, _("Go to the configuration panel"))
        return account

    def _existing_accounting(self) -> bool:
        """Return True iff some accounting entries have already been made for the current company."""
        self.ensure_one()
        return bool(self.env['account.move.line'].search([('company_id', 'child_of', self.id)], limit=1))

    def _chart_template_selection(self):
        return self.env['account.chart.template']._select_chart_template(self.country_id)

    @api.model
    def _action_check_hash_integrity(self):
        return self.env.ref('account.action_report_account_hash_integrity').report_action(self.id)

    def _check_hash_integrity(self):
        """Checks that all posted moves have still the same data as when they were posted
        and raises an error with the result.
        """
        if not self.env.user.has_group('account.group_account_user'):
            raise UserError(_('Please contact your accountant to print the Hash integrity result.'))

        def build_move_info(move):
            return(move.name, move.inalterable_hash, fields.Date.to_string(move.date))

        journals = self.env['account.journal'].search(self.env['account.journal']._check_company_domain(self))
        results_by_journal = {
            'results': [],
            'printing_date': format_date(self.env, fields.Date.to_string(fields.Date.context_today(self)))
        }

        for journal in journals:
            rslt = {
                'journal_name': journal.name,
                'journal_code': journal.code,
                'restricted_by_hash_table': journal.restrict_mode_hash_table and 'V' or 'X',
                'msg_cover': '',
                'first_hash': 'None',
                'first_move_name': 'None',
                'first_move_date': 'None',
                'last_hash': 'None',
                'last_move_name': 'None',
                'last_move_date': 'None',
            }
            if not journal.restrict_mode_hash_table:
                rslt.update({'msg_cover': _('This journal is not in strict mode.')})
                results_by_journal['results'].append(rslt)
                continue

            # We need the `sudo()` to ensure that all the moves are searched, no matter the user's access rights.
            # This is required in order to generate consistent hashs.
            # It is not an issue, since the data is only used to compute a hash and not to return the actual values.
            all_moves_count = self.env['account.move'].sudo().search_count([('state', '=', 'posted'), ('journal_id', '=', journal.id)])
            moves = self.env['account.move'].sudo().search([('state', '=', 'posted'), ('journal_id', '=', journal.id),
                                            ('secure_sequence_number', '!=', 0)], order="secure_sequence_number ASC")
            if not moves:
                rslt.update({
                    'msg_cover': _('There isn\'t any journal entry flagged for data inalterability yet for this journal.'),
                })
                results_by_journal['results'].append(rslt)
                continue

            previous_hash = u''
            start_move_info = []
            hash_corrupted = False
            current_hash_version = 1
            for move in moves:
                computed_hash = move.with_context(hash_version=current_hash_version)._compute_hash(previous_hash=previous_hash)
                while move.inalterable_hash != computed_hash and current_hash_version < MAX_HASH_VERSION:
                    current_hash_version += 1
                    computed_hash = move.with_context(hash_version=current_hash_version)._compute_hash(previous_hash=previous_hash)
                if move.inalterable_hash != computed_hash:
                    rslt.update({'msg_cover': _('Corrupted data on journal entry with id %s.', move.id)})
                    results_by_journal['results'].append(rslt)
                    hash_corrupted = True
                    break
                if not previous_hash:
                    #save the date and sequence number of the first move hashed
                    start_move_info = build_move_info(move)
                previous_hash = move.inalterable_hash
            end_move_info = build_move_info(move)

            if hash_corrupted:
                continue

            rslt.update({
                        'first_move_name': start_move_info[0],
                        'first_hash': start_move_info[1],
                        'first_move_date': format_date(self.env, start_move_info[2]),
                        'last_move_name': end_move_info[0],
                        'last_hash': end_move_info[1],
                        'last_move_date': format_date(self.env, end_move_info[2]),
                    })
            if len(moves) == all_moves_count:
                rslt['msg_cover'] = _('All entries are hashed.')
            else:
                rslt['msg_cover'] = _('Entries are hashed from %s (%s)', start_move_info[0], format_date(self.env, start_move_info[2]))
            results_by_journal['results'].append(rslt)

        return results_by_journal

    @api.model
    def _with_locked_records(self, records):
        """ To avoid sending the same records multiple times from different transactions,
        we use this generic method to lock the records passed as parameter.

        :param records: The records to lock.
        """
        self._cr.execute(f'SELECT * FROM {records._table} WHERE id IN %s FOR UPDATE SKIP LOCKED', [tuple(records.ids)])
        available_ids = {r[0] for r in self._cr.fetchall()}
        if available_ids != set(records.ids):
            raise UserError(_("Some documents are being sent by another process already."))

    def compute_fiscalyear_dates(self, current_date):
        """
        The role of this method is to provide a fallback when account_accounting is not installed.
        As the fiscal year is irrelevant when account_accounting is not installed, this method returns the calendar year.
        :param current_date: A datetime.date/datetime.datetime object.
        :return: A dictionary containing:
            * date_from
            * date_to
        """

        return {'date_from': datetime(year=current_date.year, month=1, day=1).date(),
                'date_to': datetime(year=current_date.year, month=12, day=31).date()}
