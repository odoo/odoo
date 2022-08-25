# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    has_accounting_entries = fields.Boolean(compute='_compute_has_chart_of_accounts')
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id", required=True, readonly=False,
        string='Currency', help="Main currency of the company.")
    currency_exchange_journal_id = fields.Many2one(
        comodel_name='account.journal',
        related='company_id.currency_exchange_journal_id', readonly=False,
        string="Currency Exchange Journal",
        domain="[('company_id', '=', company_id), ('type', '=', 'general')]",
        help='The accounting journal where automatic exchange differences will be registered')
    income_currency_exchange_account_id = fields.Many2one(
        comodel_name="account.account",
        related="company_id.income_currency_exchange_account_id",
        string="Gain Account",
        readonly=False,
        domain="[('account_type', 'not in', ('asset_receivable','liability_payable','asset_cash','liability_credit_card')), ('deprecated', '=', False), ('company_id', '=', company_id),\
                ('account_type', 'in', ('income', 'income_other'))]")
    expense_currency_exchange_account_id = fields.Many2one(
        comodel_name="account.account",
        related="company_id.expense_currency_exchange_account_id",
        string="Loss Account",
        readonly=False,
        domain="[('account_type', 'not in', ('asset_receivable','liability_payable','asset_cash','liability_credit_card')), ('deprecated', '=', False), ('company_id', '=', company_id),\
                ('account_type', '=', 'expense')]")
    has_chart_of_accounts = fields.Boolean(compute='_compute_has_chart_of_accounts', string='Company has a chart of accounts')
    chart_template_id = fields.Many2one('account.chart.template', string='Template', default=lambda self: self.env.company.chart_template_id,
        domain="[('visible','=', True)]")
    sale_tax_id = fields.Many2one('account.tax', string="Default Sale Tax", related='company_id.account_sale_tax_id', readonly=False)
    purchase_tax_id = fields.Many2one('account.tax', string="Default Purchase Tax", related='company_id.account_purchase_tax_id', readonly=False)
    tax_calculation_rounding_method = fields.Selection(
        related='company_id.tax_calculation_rounding_method', string='Tax calculation rounding method', readonly=False)
    account_journal_suspense_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Bank Suspense Account',
        readonly=False,
        related='company_id.account_journal_suspense_account_id',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id), ('account_type', 'not in', ('asset_receivable', 'liability_payable')), ('account_type', 'in', ('asset_current', 'liability_current'))]",
        help='Bank Transactions are posted immediately after import or synchronization. '
             'Their counterparty is the bank suspense account.\n'
             'Reconciliation replaces the latter by the definitive account(s).')
    account_journal_payment_debit_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Outstanding Receipts Account',
        readonly=False,
        related='company_id.account_journal_payment_debit_account_id',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id), ('account_type', 'not in', ('asset_receivable', 'liability_payable')), ('account_type', '=', 'asset_current')]",
        help='Incoming payments are posted on an Outstanding Receipts Account. '
             'In the bank reconciliation widget, they appear as blue lines.\n'
             'Bank transactions are then reconciled on the Outstanding Receipts Accounts rather than the Receivable '
             'Account.')
    account_journal_payment_credit_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Outstanding Payments Account',
        readonly=False,
        related='company_id.account_journal_payment_credit_account_id',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id), ('account_type', 'not in', ('asset_receivable', 'liability_payable')), ('account_type', '=', 'asset_current')]",
        help='Outgoing Payments are posted on an Outstanding Payments Account. '
             'In the bank reconciliation widget, they appear as blue lines.\n'
             'Bank transactions are then reconciled on the Outstanding Payments Account rather the Payable Account.')
    transfer_account_id = fields.Many2one('account.account', string="Internal Transfer Account",
        related='company_id.transfer_account_id', readonly=False,
        domain="[('reconcile', '=', True), ('account_type', '=', 'asset_current')]",
        help="Intermediary account used when moving from a liquidity account to another.")
    module_account_accountant = fields.Boolean(string='Accounting')
    group_analytic_tags = fields.Boolean(string='Analytic Tags', implied_group='analytic.group_analytic_tags')
    group_warning_account = fields.Boolean(string="Warnings in Invoices", implied_group='account.group_warning_account')
    group_cash_rounding = fields.Boolean(string="Cash Rounding", implied_group='account.group_cash_rounding')
    # group_show_line_subtotals_tax_excluded and group_show_line_subtotals_tax_included are opposite,
    # so we can assume exactly one of them will be set, and not the other.
    # We need both of them to coexist so we can take advantage of automatic group assignation.
    group_show_line_subtotals_tax_excluded = fields.Boolean(
        "Show line subtotals without taxes (B2B)",
        implied_group='account.group_show_line_subtotals_tax_excluded',
        group='base.group_portal,base.group_user,base.group_public',
        compute='_compute_group_show_line_subtotals', store=True, readonly=False)
    group_show_line_subtotals_tax_included = fields.Boolean(
        "Show line subtotals with taxes (B2C)",
        implied_group='account.group_show_line_subtotals_tax_included',
        group='base.group_portal,base.group_user,base.group_public',
        compute='_compute_group_show_line_subtotals', store=True, readonly=False)
    group_show_sale_receipts = fields.Boolean(string='Sale Receipt',
        implied_group='account.group_sale_receipts')
    group_show_purchase_receipts = fields.Boolean(string='Purchase Receipt',
        implied_group='account.group_purchase_receipts')
    show_line_subtotals_tax_selection = fields.Selection([
        ('tax_excluded', 'Tax Excluded'),
        ('tax_included', 'Tax Included')], string="Line Subtotals Tax Display",
        required=True, default='tax_excluded',
        config_parameter='account.show_line_subtotals_tax_selection')
    module_account_budget = fields.Boolean(string='Budget Management')
    module_account_payment = fields.Boolean(string='Invoice Online Payment')
    module_account_reports = fields.Boolean("Dynamic Reports")
    module_account_check_printing = fields.Boolean("Allow check printing and deposits")
    module_account_batch_payment = fields.Boolean(string='Use batch payments',
        help='This allows you grouping payments into a single batch and eases the reconciliation process.\n'
             '-This installs the account_batch_payment module.')
    module_account_sepa = fields.Boolean(string='SEPA Credit Transfer (SCT)')
    module_account_sepa_direct_debit = fields.Boolean(string='Use SEPA Direct Debit')
    module_account_bank_statement_import_qif = fields.Boolean("Import .qif files")
    module_account_bank_statement_import_ofx = fields.Boolean("Import in .ofx format")
    module_account_bank_statement_import_csv = fields.Boolean("Import in .csv format")
    module_account_bank_statement_import_camt = fields.Boolean("Import in CAMT.053 format")
    module_currency_rate_live = fields.Boolean(string="Automatic Currency Rates")
    module_account_intrastat = fields.Boolean(string='Intrastat')
    module_product_margin = fields.Boolean(string="Allow Product Margin")
    module_l10n_eu_oss = fields.Boolean(string="EU Intra-community Distance Selling")
    module_account_taxcloud = fields.Boolean(string="Account TaxCloud")
    module_account_invoice_extract = fields.Boolean(string="Document Digitization")
    module_snailmail_account = fields.Boolean(string="Snailmail")
    tax_exigibility = fields.Boolean(string='Cash Basis', related='company_id.tax_exigibility', readonly=False)
    tax_cash_basis_journal_id = fields.Many2one('account.journal', related='company_id.tax_cash_basis_journal_id', string="Tax Cash Basis Journal", readonly=False)
    account_cash_basis_base_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Base Tax Received Account",
        readonly=False,
        related='company_id.account_cash_basis_base_account_id',
        domain=[('deprecated', '=', False)])
    account_fiscal_country_id = fields.Many2one(string="Fiscal Country Code", related="company_id.account_fiscal_country_id", readonly=False, store=False)

    qr_code = fields.Boolean(string='Display SEPA QR-code', related='company_id.qr_code', readonly=False)
    invoice_is_print = fields.Boolean(string='Print', related='company_id.invoice_is_print', readonly=False)
    invoice_is_email = fields.Boolean(string='Send Email', related='company_id.invoice_is_email', readonly=False)
    incoterm_id = fields.Many2one('account.incoterms', string='Default incoterm', related='company_id.incoterm_id', help='International Commercial Terms are a series of predefined commercial terms used in international transactions.', readonly=False)
    invoice_terms = fields.Html(related='company_id.invoice_terms', string="Terms & Conditions", readonly=False)
    invoice_terms_html = fields.Html(related='company_id.invoice_terms_html', string="Terms & Conditions as a Web page",
                                     readonly=False)
    terms_type = fields.Selection(
        related='company_id.terms_type', readonly=False)
    preview_ready = fields.Boolean(string="Display preview button", compute='_compute_terms_preview')

    use_invoice_terms = fields.Boolean(
        string='Default Terms & Conditions',
        config_parameter='account.use_invoice_terms')
    account_use_credit_limit = fields.Boolean(
        string="Sales Credit Limit", related="company_id.account_use_credit_limit", readonly=False,
        help="Enable the use of credit limit on partners.")
    account_default_credit_limit = fields.Monetary(
        string="Default Credit Limit", readonly=False,
        help='This is the default credit limit that will be used on partners that do not have a specific limit on them.',
        compute="_compute_account_default_credit_limit", inverse="_inverse_account_default_credit_limit")

    # Technical field to hide country specific fields from accounting configuration
    country_code = fields.Char(related='company_id.account_fiscal_country_id.code', readonly=True)

    # Storno Accounting
    account_storno = fields.Boolean(string="Storno accounting", readonly=False, related='company_id.account_storno')

    # Allows for the use of a different delivery address
    group_sale_delivery_address = fields.Boolean("Customer Addresses", implied_group='account.group_delivery_invoice_address')

    # Quick encoding (fiduciary mode)
    quick_edit_mode = fields.Selection(string="Quick encoding", readonly=False, related='company_id.quick_edit_mode')

    def set_values(self):
        super().set_values()
        # install a chart of accounts for the given company (if required)
        if self.env.company == self.company_id \
                and self.chart_template_id \
                and self.chart_template_id != self.company_id.chart_template_id:
            self.chart_template_id._load(self.env.company)

    @api.depends('company_id')
    def _compute_account_default_credit_limit(self):
        for setting in self:
            setting.account_default_credit_limit = self.env['ir.property']._get('credit_limit', 'res.partner')

    def _inverse_account_default_credit_limit(self):
        for setting in self:
            self.env['ir.property']._set_default(
                'credit_limit',
                'res.partner',
                setting.account_default_credit_limit,
                self.company_id.id
            )

    @api.depends('company_id')
    def _compute_has_chart_of_accounts(self):
        self.has_chart_of_accounts = bool(self.company_id.chart_template_id)
        self.has_accounting_entries = self.env['account.chart.template'].existing_accounting(self.company_id)

    @api.depends('show_line_subtotals_tax_selection')
    def _compute_group_show_line_subtotals(self):
        for wizard in self:
            wizard.group_show_line_subtotals_tax_included = wizard.show_line_subtotals_tax_selection == "tax_included"
            wizard.group_show_line_subtotals_tax_excluded = wizard.show_line_subtotals_tax_selection == "tax_excluded"

    @api.onchange('group_analytic_accounting')
    def onchange_analytic_accounting(self):
        if self.group_analytic_accounting:
            self.module_account_accountant = True

    @api.onchange('module_account_budget')
    def onchange_module_account_budget(self):
        if self.module_account_budget:
            self.group_analytic_accounting = True

    @api.onchange('tax_exigibility')
    def _onchange_tax_exigibility(self):
        res = {}
        tax = self.env['account.tax'].search([
            ('company_id', '=', self.env.company.id), ('tax_exigibility', '=', 'on_payment')
        ], limit=1)
        if not self.tax_exigibility and tax:
            self.tax_exigibility = True
            res['warning'] = {
                'title': _('Error!'),
                'message': _('You cannot disable this setting because some of your taxes are cash basis. '
                             'Modify your taxes first before disabling this setting.')
            }
        return res

    @api.depends('terms_type')
    def _compute_terms_preview(self):
        for setting in self:
            # We display the preview button only if the terms_type is html in the setting but also on the company
            # to avoid landing on an error page (see terms.py controller)
            setting.preview_ready = self.env.company.terms_type == 'html' and setting.terms_type == 'html'

    def action_update_terms(self):
        self.ensure_one()
        return {
            'name': _('Update Terms & Conditions'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'res.company',
            'view_id': self.env.ref("account.res_company_view_form_terms", False).id,
            'target': 'new',
            'res_id': self.company_id.id,
        }
