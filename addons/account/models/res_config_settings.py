from odoo import _, api, fields, models
from odoo.libs.debug_log import DebugLog

from odoo.addons.account.models.res_company import PEPPOL_LIST

_debug = DebugLog(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    has_accounting_entries = fields.Boolean(compute="_compute_accounting_presence")
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
        string="Currency",
        readonly=False,
        required=True,
        help="Main currency of the company.",
    )
    currency_exchange_journal_id = fields.Many2one(
        comodel_name="account.journal",
        related="company_id.account_config_id.currency_exchange_journal_id",
        string="Currency Exchange Journal",
        readonly=False,
        domain="[('type', '=', 'general')]",
        check_company=True,
        help="The accounting journal where automatic exchange differences will be registered",
    )
    income_currency_exchange_account_id = fields.Many2one(
        comodel_name="account.account",
        related="company_id.account_config_id.income_currency_exchange_account_id",
        string="Gain Exchange Rate Account",
        readonly=False,
        domain="[('internal_group', '=', 'income')]",
        check_company=True,
    )
    expense_currency_exchange_account_id = fields.Many2one(
        comodel_name="account.account",
        related="company_id.account_config_id.expense_currency_exchange_account_id",
        string="Loss Exchange Rate Account",
        readonly=False,
        domain="[('account_type', 'in', ('expense', 'expense_other'))]",
        check_company=True,
    )
    has_chart_of_accounts = fields.Boolean(
        string="Company has a chart of accounts",
        compute="_compute_accounting_presence",
    )
    chart_template = fields.Selection(
        selection=lambda self: self.env.company._selection_chart_templates(),
        default=lambda self: self.env.company.account_config_id.chart_template,
    )
    sale_tax_id = fields.Many2one(
        comodel_name="account.tax",
        related="company_id.account_config_id.account_sale_tax_id",
        string="Default Sale Tax",
        readonly=False,
        check_company=True,
    )
    purchase_tax_id = fields.Many2one(
        comodel_name="account.tax",
        related="company_id.account_config_id.account_purchase_tax_id",
        string="Default Purchase Tax",
        readonly=False,
        check_company=True,
    )
    account_price_include = fields.Selection(
        related="company_id.account_config_id.account_price_include",
        string="Default Sales Price Include",
        readonly=False,
        required=True,
        help="Default on whether the sales price used on the product and invoices with this Company includes its taxes.",
    )

    tax_calculation_rounding_method = fields.Selection(
        related="company_id.account_config_id.tax_calculation_rounding_method",
        string="Tax calculation rounding method",
        readonly=False,
    )
    account_journal_suspense_account_id = fields.Many2one(
        comodel_name="account.account",
        related="company_id.account_config_id.account_journal_suspense_account_id",
        string="Bank Suspense",
        readonly=False,
        domain="[('account_type', 'in', ('asset_current', 'liability_current'))]",
        check_company=True,
        help="Bank Transactions are posted immediately after import or synchronization. "
        "Their counterparty is the bank suspense account.\n"
        "Reconciliation replaces the latter by the definitive account(s).",
    )
    transfer_account_id = fields.Many2one(
        comodel_name="account.account",
        related="company_id.account_config_id.transfer_account_id",
        string="Internal Transfer",
        readonly=False,
        domain=[
            ("reconcile", "=", True),
            ("account_type", "=", "asset_current"),
        ],
        check_company=True,
        help="Intermediary account used when moving from a liquidity account to another.",
    )
    group_cash_rounding = fields.Boolean(
        string="Cash Rounding",
        implied_group="account.group_cash_rounding",
    )
    show_sale_receipts = fields.Boolean(
        string="Sale Receipt",
        config_parameter="account.show_sale_receipts",
    )
    module_account_budget = fields.Boolean(string="Budget Management")
    module_account_payment_provider = fields.Boolean(string="Invoice Online Payment")
    module_account_reports = fields.Boolean(string="Dynamic Reports")
    module_account_check_printing = fields.Boolean(
        string="Allow check printing and deposits"
    )
    module_account_batch_payment = fields.Boolean(
        string="Use batch payments",
        help="This allows you grouping payments into a single batch and eases the reconciliation process.\n"
        "-This installs the account_batch_payment module.",
    )
    module_account_iso20022 = fields.Boolean(string="SEPA Credit Transfer / ISO20022")
    module_account_sepa_direct_debit = fields.Boolean(string="Use SEPA Direct Debit")
    module_account_bank_statement_import_qif = fields.Boolean(
        string="Import .qif files"
    )
    module_currency_rate_live = fields.Boolean(string="Automatic Currency Rates")
    module_account_intrastat = fields.Boolean(string="Intrastat")
    module_product_margin = fields.Boolean(string="Allow Product Margin")
    module_extract_account = fields.Boolean(string="Invoice Digitization")
    module_extract_account_bank_statement = fields.Boolean(
        string="Bank Statement Digitization"
    )
    module_snailmail_account = fields.Boolean(string="Snailmail")
    module_account_peppol = fields.Boolean(string="PEPPOL Invoicing")
    tax_exigibility = fields.Boolean(
        related="company_id.account_config_id.tax_exigibility",
        string="Cash Basis",
        readonly=False,
    )
    tax_cash_basis_journal_id = fields.Many2one(
        comodel_name="account.journal",
        related="company_id.account_config_id.tax_cash_basis_journal_id",
        string="Tax Cash Basis Journal",
        readonly=False,
        check_company=True,
    )
    account_cash_basis_base_account_id = fields.Many2one(
        comodel_name="account.account",
        related="company_id.account_config_id.account_cash_basis_base_account_id",
        string="Base Tax Received Account",
        readonly=False,
        check_company=True,
    )
    account_fiscal_country_id = fields.Many2one(
        related="company_id.account_config_id.account_fiscal_country_id",
        string="Fiscal Country Code",
        store=False,
        readonly=False,
    )

    qr_code = fields.Boolean(
        related="company_id.account_config_id.qr_code",
        string="Display SEPA QR-code",
        readonly=False,
    )
    link_qr_code = fields.Boolean(
        related="company_id.account_config_id.link_qr_code",
        string="Display Link QR-code",
        readonly=False,
    )
    incoterm_id = fields.Many2one(
        comodel_name="account.incoterms",
        related="company_id.account_config_id.incoterm_id",
        string="Default incoterm",
        readonly=False,
        help="International Commercial Terms are a series of predefined commercial terms used in international transactions.",
    )
    invoice_terms = fields.Html(
        related="company_id.account_config_id.invoice_terms",
        string="Terms & Conditions",
        readonly=False,
    )
    invoice_terms_html = fields.Html(
        related="company_id.account_config_id.invoice_terms_html",
        string="Terms & Conditions as a Web page",
        readonly=False,
    )
    terms_type = fields.Selection(
        related="company_id.account_config_id.terms_type",
        readonly=False,
    )
    display_invoice_amount_total_words = fields.Boolean(
        related="company_id.account_config_id.display_invoice_amount_total_words",
        string="Total amount of invoice in letters",
        readonly=False,
    )
    display_invoice_tax_company_currency = fields.Boolean(
        related="company_id.account_config_id.display_invoice_tax_company_currency",
        string="Taxes in company currency",
        readonly=False,
    )
    preview_ready = fields.Boolean(
        string="Display preview button",
        compute="_compute_preview_ready",
    )

    use_invoice_terms = fields.Boolean(
        string="Default Terms & Conditions",
        config_parameter="account.use_invoice_terms",
    )
    account_use_credit_limit = fields.Boolean(
        related="company_id.account_config_id.account_use_credit_limit",
        string="Sales Credit Limit",
        readonly=False,
        help="Enable the use of credit limit on partners.",
    )
    account_default_credit_limit = fields.Monetary(
        string="Default Credit Limit",
        compute="_compute_account_default_credit_limit",
        inverse="_inverse_account_default_credit_limit",
        readonly=False,
        help="This is the default credit limit that will be used on partners that do not have a specific limit on them.",
    )

    country_code = fields.Char(
        related="company_id.account_config_id.account_fiscal_country_id.code",
        readonly=True,
    )

    account_storno = fields.Boolean(
        related="company_id.account_config_id.account_storno",
        string="Storno accounting",
        readonly=False,
    )
    display_account_storno = fields.Boolean(
        related="company_id.account_config_id.display_account_storno"
    )

    group_sale_delivery_address = fields.Boolean(
        string="Customer Addresses",
        implied_group="account.group_delivery_invoice_address",
    )

    quick_edit_mode = fields.Selection(
        related="company_id.account_config_id.quick_edit_mode",
        string="Quick encoding",
        readonly=False,
    )

    account_journal_early_pay_discount_loss_account_id = fields.Many2one(
        comodel_name="account.account",
        related="company_id.account_config_id.account_journal_early_pay_discount_loss_account_id",
        string="Early Discount Loss",
        readonly=False,
        domain="[('account_type', 'in', ('expense', 'expense_other', 'income', 'income_other'))]",
        check_company=True,
        help="Account for the difference amount after the expense discount has been granted",
    )
    account_journal_early_pay_discount_gain_account_id = fields.Many2one(
        comodel_name="account.account",
        related="company_id.account_config_id.account_journal_early_pay_discount_gain_account_id",
        string="Early Discount Gain",
        readonly=False,
        domain="[('account_type', 'in', ('income', 'income_other', 'expense', 'expense_other'))]",
        check_company=True,
        help="Account for the difference amount after the income discount has been granted",
    )

    account_discount_income_allocation_id = fields.Many2one(
        comodel_name="account.account",
        related="company_id.account_config_id.account_discount_income_allocation_id",
        string="Vendor Bills Discounts Account",
        readonly=False,
        domain="[('account_type', 'in', ('income', 'income_other', 'expense', 'expense_other'))]",
    )
    account_discount_expense_allocation_id = fields.Many2one(
        comodel_name="account.account",
        related="company_id.account_config_id.account_discount_expense_allocation_id",
        string="Customer Invoices Discounts Account",
        readonly=False,
        domain="[('account_type', 'in', ('income', 'income_other', 'expense', 'expense_other'))]",
    )

    is_account_peppol_eligible = fields.Boolean(
        string="PEPPOL eligible",
        compute="_compute_is_account_peppol_eligible",
    )

    restrictive_audit_trail = fields.Boolean(
        related="company_id.account_config_id.restrictive_audit_trail",
        string="Restricted Audit Trail",
        readonly=False,
    )
    force_restrictive_audit_trail = fields.Boolean(
        related="company_id.account_config_id.force_restrictive_audit_trail",
        string="Forced Audit Trail",
        readonly=False,
    )

    autopost_bills = fields.Boolean(
        related="company_id.account_config_id.autopost_bills",
        readonly=False,
    )
    income_account_id = fields.Many2one(
        related="company_id.account_config_id.income_account_id",
        readonly=False,
        check_company=True,
    )
    expense_account_id = fields.Many2one(
        related="company_id.account_config_id.expense_account_id",
        readonly=False,
        check_company=True,
    )

    @api.depends("country_code")
    def _compute_is_account_peppol_eligible(self):
        for config in self:
            config.is_account_peppol_eligible = config.country_code in PEPPOL_LIST

    def set_values(self):
        super().set_values()
        if (
            self.env.company == self.company_id
            and self.chart_template
            and self.chart_template != self.company_id.account_config_id.chart_template
        ):
            self.env["account.chart.template"].try_loading(
                self.chart_template, company=self.company_id
            )
            self.company_id._initiate_account_onboardings()

    def reload_template(self):
        self.env["account.chart.template"].try_loading(
            self.company_id.account_config_id.chart_template, company=self.company_id
        )

    @api.depends("company_id")
    def _compute_account_default_credit_limit(self):
        ResPartner = self.env["res.partner"]
        company_limit = ResPartner._fields[
            "credit_limit"
        ].get_company_dependent_fallback(ResPartner)
        self.account_default_credit_limit = company_limit

    def _inverse_account_default_credit_limit(self):
        for setting in self:
            self.env["ir.default"].set(
                "res.partner",
                "credit_limit",
                setting.account_default_credit_limit,
                company_id=setting.company_id.id,
            )

    @api.depends("company_id")
    def _compute_accounting_presence(self):
        self.has_chart_of_accounts = bool(
            self.company_id.account_config_id.chart_template
        )
        self.has_accounting_entries = self.company_id.root_id._existing_accounting()

    @api.onchange("module_account_budget")
    def _onchange_module_account_budget(self):
        if self.module_account_budget:
            self.group_analytic_accounting = True

    @api.onchange("tax_exigibility")
    def _onchange_tax_exigibility(self):
        res = {}
        tax = self.env["account.tax"].search(
            [
                *self.env["account.tax"]._check_company_domain(self.env.company),
                ("tax_exigibility", "=", "on_payment"),
            ],
            limit=1,
        )
        if not self.tax_exigibility and tax:
            self.tax_exigibility = True
            res["warning"] = {
                "title": _("Error!"),
                "message": _(
                    "You cannot disable this setting because some of your taxes are cash basis. "
                    "Modify your taxes first before disabling this setting."
                ),
            }
        return res

    @api.depends("terms_type")
    def _compute_preview_ready(self):
        for setting in self:
            setting.preview_ready = (
                self.env.company.account_config_id.terms_type == "html"
                and setting.terms_type == "html"
            )

    @_debug.perf.timed
    def action_update_terms(self):
        _debug.lifecycle("action_update_terms", records=self)
        self.check_singleton()
        if hasattr(self, "website_id") and self.env.user.has_group(
            "website.group_website_designer"
        ):
            return self.env["website"].get_client_action("/terms", True)
        return {
            "name": _("Update Terms & Conditions"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "account.config",
            "view_id": self.env.ref("account.res_company_view_form_terms", False).id,
            "target": "new",
            "res_id": self.company_id.account_config_id.id,
        }

    @_debug.perf.timed
    def action_eu_oss_tax_mapping(self):
        _debug.lifecycle("action_eu_oss_tax_mapping", records=self)
        l10n_eu_oss_module = self.env["ir.module.module"].search(
            [("name", "=", "l10n_eu_oss")], limit=1
        )
        if l10n_eu_oss_module:
            if l10n_eu_oss_module.state != "installed":
                l10n_eu_oss_module.button_immediate_install()
            self.env.companies._map_eu_taxes()
