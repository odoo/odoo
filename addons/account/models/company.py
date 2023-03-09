# -*- coding: utf-8 -*-

from datetime import timedelta, datetime, date
import calendar
from dateutil.relativedelta import relativedelta

from odoo.addons.account.models.account_move import MAX_HASH_VERSION
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError, RedirectWarning
from odoo.tools.mail import is_html_empty
from odoo.tools.misc import format_date
from odoo.tools.float_utils import float_round, float_is_zero
from odoo.tests.common import Form


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

ONBOARDING_STEP_STATES = [
    ('not_done', "Not done"),
    ('just_done', "Just done"),
    ('done', "Done"),
]
DASHBOARD_ONBOARDING_STATES = ONBOARDING_STEP_STATES + [('closed', 'Closed')]


class ResCompany(models.Model):
    _inherit = "res.company"

    #TODO check all the options/fields are in the views (settings + company form view)
    fiscalyear_last_day = fields.Integer(default=31, required=True)
    fiscalyear_last_month = fields.Selection(MONTH_SELECTION, default='12', required=True)
    period_lock_date = fields.Date(string="Lock Date for Non-Advisers", help="Only users with the 'Adviser' role can edit accounts prior to and inclusive of this date. Use it for period locking inside an open fiscal year, for example.")
    fiscalyear_lock_date = fields.Date(string="Lock Date", help="No users, including Advisers, can edit accounts prior to and inclusive of this date. Use it for fiscal year locking for example.")
    tax_lock_date = fields.Date("Tax Lock Date", help="No users can edit journal entries related to a tax prior and inclusive of this date.")
    transfer_account_id = fields.Many2one('account.account',
        domain=lambda self: [('reconcile', '=', True), ('user_type_id.id', '=', self.env.ref('account.data_account_type_current_assets').id), ('deprecated', '=', False)], string="Inter-Banks Transfer Account", help="Intermediary account used when moving money from a liquidity account to another")
    expects_chart_of_accounts = fields.Boolean(string='Expects a Chart of Accounts', default=True)
    chart_template_id = fields.Many2one('account.chart.template', help='The chart template for the company (if any)')
    bank_account_code_prefix = fields.Char(string='Prefix of the bank accounts')
    cash_account_code_prefix = fields.Char(string='Prefix of the cash accounts')
    default_cash_difference_income_account_id = fields.Many2one('account.account', string="Cash Difference Income Account")
    default_cash_difference_expense_account_id = fields.Many2one('account.account', string="Cash Difference Expense Account")
    account_journal_suspense_account_id = fields.Many2one('account.account', string='Journal Suspense Account')
    account_journal_payment_debit_account_id = fields.Many2one('account.account', string='Journal Outstanding Receipts Account')
    account_journal_payment_credit_account_id = fields.Many2one('account.account', string='Journal Outstanding Payments Account')
    transfer_account_code_prefix = fields.Char(string='Prefix of the transfer accounts')
    account_sale_tax_id = fields.Many2one('account.tax', string="Default Sale Tax")
    account_purchase_tax_id = fields.Many2one('account.tax', string="Default Purchase Tax")
    tax_calculation_rounding_method = fields.Selection([
        ('round_per_line', 'Round per Line'),
        ('round_globally', 'Round Globally'),
        ], default='round_per_line', string='Tax Calculation Rounding Method')
    currency_exchange_journal_id = fields.Many2one('account.journal', string="Exchange Gain or Loss Journal", domain=[('type', '=', 'general')])
    income_currency_exchange_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Gain Exchange Rate Account",
        domain=lambda self: "[('internal_type', '=', 'other'), ('deprecated', '=', False), ('company_id', '=', id), \
                             ('user_type_id', 'in', %s)]" % [self.env.ref('account.data_account_type_revenue').id,
                                                             self.env.ref('account.data_account_type_other_income').id])
    expense_currency_exchange_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Loss Exchange Rate Account",
        domain=lambda self: "[('internal_type', '=', 'other'), ('deprecated', '=', False), ('company_id', '=', id), \
                             ('user_type_id', '=', %s)]" % self.env.ref('account.data_account_type_expenses').id)
    anglo_saxon_accounting = fields.Boolean(string="Use anglo-saxon accounting")
    property_stock_account_input_categ_id = fields.Many2one('account.account', string="Input Account for Stock Valuation")
    property_stock_account_output_categ_id = fields.Many2one('account.account', string="Output Account for Stock Valuation")
    property_stock_valuation_account_id = fields.Many2one('account.account', string="Account Template for Stock Valuation")
    bank_journal_ids = fields.One2many('account.journal', 'company_id', domain=[('type', '=', 'bank')], string='Bank Journals')
    incoterm_id = fields.Many2one('account.incoterms', string='Default incoterm',
        help='International Commercial Terms are a series of predefined commercial terms used in international transactions.')

    qr_code = fields.Boolean(string='Display QR-code on invoices')

    invoice_is_email = fields.Boolean('Email by default', default=True)
    invoice_is_print = fields.Boolean('Print by default', default=True)

    #Fields of the setup step for opening move
    account_opening_move_id = fields.Many2one(string='Opening Journal Entry', comodel_name='account.move', help="The journal entry containing the initial balance of all this company's accounts.")
    account_opening_journal_id = fields.Many2one(string='Opening Journal', comodel_name='account.journal', related='account_opening_move_id.journal_id', help="Journal where the opening entry of this company's accounting has been posted.", readonly=False)
    account_opening_date = fields.Date(string='Opening Entry', default=lambda self: fields.Date.context_today(self).replace(month=1, day=1), required=True, help="That is the date of the opening entry.")

    # Fields marking the completion of a setup step
    account_setup_bank_data_state = fields.Selection(ONBOARDING_STEP_STATES, string="State of the onboarding bank data step", default='not_done')
    account_setup_fy_data_state = fields.Selection(ONBOARDING_STEP_STATES, string="State of the onboarding fiscal year step", default='not_done')
    account_setup_coa_state = fields.Selection(ONBOARDING_STEP_STATES, string="State of the onboarding charts of account step", default='not_done')
    account_setup_taxes_state = fields.Selection(ONBOARDING_STEP_STATES, string="State of the onboarding Taxes step", default='not_done')
    account_onboarding_invoice_layout_state = fields.Selection(ONBOARDING_STEP_STATES, string="State of the onboarding invoice layout step", default='not_done')
    account_onboarding_create_invoice_state = fields.Selection(ONBOARDING_STEP_STATES, string="State of the onboarding create invoice step", default='not_done')
    account_onboarding_sale_tax_state = fields.Selection(ONBOARDING_STEP_STATES, string="State of the onboarding sale tax step", default='not_done')

    # account dashboard onboarding
    account_invoice_onboarding_state = fields.Selection(DASHBOARD_ONBOARDING_STATES, string="State of the account invoice onboarding panel", default='not_done')
    account_dashboard_onboarding_state = fields.Selection(DASHBOARD_ONBOARDING_STATES, string="State of the account dashboard onboarding panel", default='not_done')
    invoice_terms = fields.Html(string='Default Terms and Conditions', translate=True)
    terms_type = fields.Selection([('plain', 'Add a Note'), ('html', 'Add a link to a Web Page')],
                                  string='Terms & Conditions format', default='plain')
    invoice_terms_html = fields.Html(string='Default Terms and Conditions as a Web page', translate=True,
                                     compute='_compute_invoice_terms_html', store=True, readonly=False)

    account_setup_bill_state = fields.Selection(ONBOARDING_STEP_STATES, string="State of the onboarding bill step", default='not_done')

    # Needed in the Point of Sale
    account_default_pos_receivable_account_id = fields.Many2one('account.account', string="Default PoS Receivable Account")

    # Accrual Accounting
    expense_accrual_account_id = fields.Many2one('account.account',
        help="Account used to move the period of an expense",
        domain="[('internal_group', '=', 'liability'), ('internal_type', 'not in', ('receivable', 'payable')), ('company_id', '=', id)]")
    revenue_accrual_account_id = fields.Many2one('account.account',
        help="Account used to move the period of a revenue",
        domain="[('internal_group', '=', 'asset'), ('internal_type', 'not in', ('receivable', 'payable')), ('company_id', '=', id)]")
    automatic_entry_default_journal_id = fields.Many2one('account.journal', help="Journal used by default for moving the period of an entry", domain="[('type', '=', 'general')]")

    # Technical field to hide country specific fields in company form view
    country_code = fields.Char(related='country_id.code')

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
        string="Cash Basis Journal")
    account_cash_basis_base_account_id = fields.Many2one(
        comodel_name='account.account',
        domain=[('deprecated', '=', False)],
        string="Base Tax Received Account",
        help="Account that will be set on lines created in cash basis journal entry and used to keep track of the "
             "tax base amount.")

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

    @api.depends('country_id')
    def compute_account_tax_fiscal_country(self):
        for record in self:
            record.account_fiscal_country_id = record.country_id

    @api.depends('account_fiscal_country_id')
    def _compute_account_enabled_tax_country_ids(self):
        for record in self:
            foreign_vat_fpos = self.env['account.fiscal.position'].search([('company_id', '=', record.id), ('foreign_vat', '!=', False)])
            record.account_enabled_tax_country_ids = foreign_vat_fpos.country_id + record.account_fiscal_country_id

    @api.depends('terms_type')
    def _compute_invoice_terms_html(self):
        term_template = self.env.ref("account.account_default_terms_and_conditions", False)
        if not term_template:
            return

        for company in self.filtered(lambda company: is_html_empty(company.invoice_terms_html) and company.terms_type == 'html'):
            company.invoice_terms_html = term_template._render({'company_name': company.name, 'company_country': company.country_id.name}, engine='ir.qweb')

    def get_and_update_account_invoice_onboarding_state(self):
        """ This method is called on the controller rendering method and ensures that the animations
            are displayed only one time. """
        return self.get_and_update_onbarding_state(
            'account_invoice_onboarding_state',
            self.get_account_invoice_onboarding_steps_states_names()
        )

    # YTI FIXME: Define only one method that returns {'account': [], 'sale': [], ...}
    def get_account_invoice_onboarding_steps_states_names(self):
        """ Necessary to add/edit steps from other modules (payment acquirer in this case). """
        return [
            'base_onboarding_company_state',
            'account_onboarding_invoice_layout_state',
            'account_onboarding_create_invoice_state',
        ]

    def get_and_update_account_dashboard_onboarding_state(self):
        """ This method is called on the controller rendering method and ensures that the animations
            are displayed only one time. """
        return self.get_and_update_onbarding_state(
            'account_dashboard_onboarding_state',
            self.get_account_dashboard_onboarding_steps_states_names()
        )

    def get_account_dashboard_onboarding_steps_states_names(self):
        """ Necessary to add/edit steps from other modules (account_winbooks_import in this case). """
        return [
            'account_setup_bank_data_state',
            'account_setup_fy_data_state',
            'account_setup_coa_state',
            'account_setup_taxes_state',
        ]

    def get_new_account_code(self, current_code, old_prefix, new_prefix):
        digits = len(current_code)
        return new_prefix + current_code.replace(old_prefix, '', 1).lstrip('0').rjust(digits-len(new_prefix), '0')

    def reflect_code_prefix_change(self, old_code, new_code):
        accounts = self.env['account.account'].search([('code', 'like', old_code), ('internal_type', '=', 'liquidity'),
            ('company_id', '=', self.id)], order='code asc')
        for account in accounts:
            if account.code.startswith(old_code):
                account.write({'code': self.get_new_account_code(account.code, old_code, new_code)})

    def _validate_fiscalyear_lock(self, values):
        if values.get('fiscalyear_lock_date'):

            draft_entries = self.env['account.move'].search([
                ('company_id', 'in', self.ids),
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
                ('company_id', 'in', self.ids),
                ('is_reconciled', '=', False),
                ('date', '<=', values['fiscalyear_lock_date']),
                ('move_id.state', 'in', ('draft', 'posted')),
            ])
            if unreconciled_statement_lines:
                error_msg = _("There are still unreconciled bank statement lines in the period you want to lock."
                            "You should either reconcile or delete them.")
                action_error = {
                    'type': 'ir.actions.client',
                    'tag': 'bank_statement_reconciliation_view',
                    'context': {'statement_line_ids': unreconciled_statement_lines.ids, 'company_ids': self.ids},
                }
                raise RedirectWarning(error_msg, action_error, _('Show Unreconciled Bank Statement Line'))

    def _get_user_fiscal_lock_date(self):
        """Get the fiscal lock date for this company depending on the user"""
        self.ensure_one()
        lock_date = max(self.period_lock_date or date.min, self.fiscalyear_lock_date or date.min)
        if self.user_has_groups('account.group_account_manager'):
            lock_date = self.fiscalyear_lock_date or date.min
        return lock_date

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
                if self.env['account.move.line'].search([('company_id', '=', company.id)]):
                    raise UserError(_('You cannot change the currency of the company since some journal items already exist'))

        return super(ResCompany, self).write(values)

    @api.model
    def setting_init_bank_account_action(self):
        """ Called by the 'Bank Accounts' button of the setup bar."""
        view_id = self.env.ref('account.setup_bank_account_wizard').id
        return {'type': 'ir.actions.act_window',
                'name': _('Create a Bank Account'),
                'res_model': 'account.setup.bank.manual.config',
                'target': 'new',
                'view_mode': 'form',
                'views': [[view_id, 'form']],
        }

    @api.model
    def setting_init_fiscal_year_action(self):
        """ Called by the 'Fiscal Year Opening' button of the setup bar."""
        company = self.env.company
        company.create_op_move_if_non_existant()
        new_wizard = self.env['account.financial.year.op'].create({'company_id': company.id})
        view_id = self.env.ref('account.setup_financial_year_opening_form').id

        return {
            'type': 'ir.actions.act_window',
            'name': _('Accounting Periods'),
            'view_mode': 'form',
            'res_model': 'account.financial.year.op',
            'target': 'new',
            'res_id': new_wizard.id,
            'views': [[view_id, 'form']],
        }

    @api.model
    def setting_chart_of_accounts_action(self):
        """ Called by the 'Chart of Accounts' button of the setup bar."""
        company = self.env.company
        company.sudo().set_onboarding_step_done('account_setup_coa_state')

        # If an opening move has already been posted, we open the tree view showing all the accounts
        if company.opening_move_posted():
            return 'account.action_account_form'

        # Otherwise, we create the opening move
        company.create_op_move_if_non_existant()

        # Then, we open will open a custom tree view allowing to edit opening balances of the account
        view_id = self.env.ref('account.init_accounts_tree').id
        # Hide the current year earnings account as it is automatically computed
        domain = [('user_type_id', '!=', self.env.ref('account.data_unaffected_earnings').id), ('company_id','=', company.id)]
        return {
            'type': 'ir.actions.act_window',
            'name': _('Chart of Accounts'),
            'res_model': 'account.account',
            'view_mode': 'tree',
            'limit': 99999999,
            'search_view_id': [self.env.ref('account.view_account_search').id],
            'views': [[view_id, 'list']],
            'domain': domain,
        }

    @api.model
    def create_op_move_if_non_existant(self):
        """ Creates an empty opening move in 'draft' state for the current company
        if there wasn't already one defined. For this, the function needs at least
        one journal of type 'general' to exist (required by account.move).
        """
        self.ensure_one()
        if not self.account_opening_move_id:
            default_journal = self.env['account.journal'].search([('type', '=', 'general'), ('company_id', '=', self.id)], limit=1)

            if not default_journal:
                raise UserError(_("Please install a chart of accounts or create a miscellaneous journal before proceeding."))

            opening_date = self.account_opening_date - timedelta(days=1)

            self.account_opening_move_id = self.env['account.move'].create({
                'ref': _('Opening Journal Entry'),
                'company_id': self.id,
                'journal_id': default_journal.id,
                'date': opening_date,
            })

    def opening_move_posted(self):
        """ Returns true if this company has an opening account move and this move is posted."""
        return bool(self.account_opening_move_id) and self.account_opening_move_id.state == 'posted'

    def get_unaffected_earnings_account(self):
        """ Returns the unaffected earnings account for this company, creating one
        if none has yet been defined.
        """
        unaffected_earnings_type = self.env.ref("account.data_unaffected_earnings")
        account = self.env['account.account'].search([('company_id', '=', self.id),
                                                      ('user_type_id', '=', unaffected_earnings_type.id)])
        if account:
            return account[0]
        # Do not assume '999999' doesn't exist since the user might have created such an account
        # manually.
        code = 999999
        while self.env['account.account'].search([('code', '=', str(code)), ('company_id', '=', self.id)]):
            code -= 1
        return self.env['account.account'].create({
                'code': str(code),
                'name': _('Undistributed Profits/Losses'),
                'user_type_id': unaffected_earnings_type.id,
                'company_id': self.id,
            })

    def get_opening_move_differences(self, opening_move_lines):
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
        if self.account_opening_move_id and self.account_opening_move_id.state == 'draft':
            balancing_account = self.get_unaffected_earnings_account()
            currency = self.currency_id

            balancing_move_line = self.account_opening_move_id.line_ids.filtered(lambda x: x.account_id == balancing_account)
            # There could be multiple lines if we imported the balance from unaffected earnings account too
            if len(balancing_move_line) > 1:
                self.with_context(check_move_validity=False).account_opening_move_id.line_ids -= balancing_move_line[1:]
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

    @api.model
    def action_close_account_invoice_onboarding(self):
        """ Mark the invoice onboarding panel as closed. """
        self.env.company.account_invoice_onboarding_state = 'closed'

    @api.model
    def action_close_account_dashboard_onboarding(self):
        """ Mark the dashboard onboarding panel as closed. """
        self.env.company.account_dashboard_onboarding_state = 'closed'

    @api.model
    def action_open_account_onboarding_sale_tax(self):
        """ Onboarding step for the invoice layout. """
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_open_account_onboarding_sale_tax")
        action['res_id'] = self.env.company.id
        return action

    @api.model
    def action_open_account_onboarding_create_invoice(self):
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_open_account_onboarding_create_invoice")
        return action

    @api.model
    def action_open_taxes_onboarding(self):
        """ Called by the 'Taxes' button of the setup bar."""

        company = self.env.company
        company.sudo().set_onboarding_step_done('account_setup_taxes_state')
        view_id_list = self.env.ref('account.view_tax_tree').id
        view_id_form = self.env.ref('account.view_tax_form').id

        return {
            'type': 'ir.actions.act_window',
            'name': _('Taxes'),
            'res_model': 'account.tax',
            'target': 'current',
            'views': [[view_id_list, 'list'], [view_id_form, 'form']],
            'context': {'search_default_sale': True, 'search_default_purchase': True, 'active_test': False},
        }

    def action_save_onboarding_invoice_layout(self):
        """ Set the onboarding step as done """
        if bool(self.external_report_layout_id):
            self.set_onboarding_step_done('account_onboarding_invoice_layout_state')

    def action_save_onboarding_sale_tax(self):
        """ Set the onboarding step as done """
        self.set_onboarding_step_done('account_onboarding_sale_tax_state')

    def get_chart_of_accounts_or_fail(self):
        account = self.env['account.account'].search([('company_id', '=', self.id)], limit=1)
        if len(account) == 0:
            action = self.env.ref('account.action_account_config')
            msg = _(
                "We cannot find a chart of accounts for this company, you should configure it. \n"
                "Please go to Account Configuration and select or install a fiscal localization.")
            raise RedirectWarning(msg, action.id, _("Go to the configuration panel"))
        return account

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

        journals = self.env['account.journal'].search([('company_id', '=', self.id)])
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
                rslt.update({'msg_cover': _('All entries are hashed.')})
            else:
                rslt.update({'msg_cover': _('Entries are hashed from %s (%s)') % (start_move_info[0], format_date(self.env, start_move_info[2]))})
            results_by_journal['results'].append(rslt)

        return results_by_journal

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
