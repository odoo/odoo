import calendar
import datetime
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools.mail import is_html_empty

from odoo.addons.account.models.account_return_type import PERIODS
from odoo.addons.account.models.product import ACCOUNT_DOMAIN

_debug = DebugLog(__name__)

MONTH_SELECTION = [
    ("1", "January"),
    ("2", "February"),
    ("3", "March"),
    ("4", "April"),
    ("5", "May"),
    ("6", "June"),
    ("7", "July"),
    ("8", "August"),
    ("9", "September"),
    ("10", "October"),
    ("11", "November"),
    ("12", "December"),
]
STORNO_MANDATORY_COUNTRIES = {
    "BA",
    "CN",
    "CZ",
    "HR",
    "PL",
    "RO",
    "RS",
    "RU",
    "SI",
    "SK",
    "UA",
}
STORNO_OPTIONAL_COUNTRIES = {"AT", "CH", "DE", "IT"}
SOFT_LOCK_DATE_FIELDS = [
    "fiscalyear_lock_date",
    "tax_lock_date",
    "sale_lock_date",
    "purchase_lock_date",
]
LOCK_DATE_FIELDS = [
    *SOFT_LOCK_DATE_FIELDS,
    "hard_lock_date",
]


class AccountConfig(models.Model):
    _name = "account.config"
    _description = "A company's accounting configuration"
    _inherit = ["mixin.company.config", "mixin.mail.thread"]

    fiscalyear_last_day = fields.Integer(
        default=31,
        required=True,
    )
    fiscalyear_last_month = fields.Selection(
        selection=MONTH_SELECTION,
        default="12",
        required=True,
    )
    fiscalyear_lock_date = fields.Date(
        string="Global Lock Date",
        tracking=True,
        help="Any entry up to and including that date will be postponed to a later time, in accordance with its journal's sequence.",
    )
    tax_lock_date = fields.Date(
        string="Tax Return Lock Date",
        tracking=True,
        help="Any entry with taxes up to and including that date will be postponed to a later time, in accordance with its journal's sequence. "
        "The tax lock date is automatically set when the tax closing entry is posted.",
    )
    sale_lock_date = fields.Date(
        string="Sales Lock Date",
        tracking=True,
        help="Any sales entry prior to and including this date will be postponed to a later date, in accordance with its journal's sequence.",
    )
    purchase_lock_date = fields.Date(
        string="Purchase Lock date",
        tracking=True,
        help="Any purchase entry prior to and including this date will be postponed to a later date, in accordance with its journal's sequence.",
    )
    hard_lock_date = fields.Date(
        tracking=True,
        help="Any entry up to and including that date will be postponed to a later time, in accordance with its journal sequence. "
        "This lock date is irreversible and does not allow any exception.",
    )
    user_fiscalyear_lock_date = fields.Date(
        compute="_compute_user_fiscalyear_lock_date"
    )
    user_tax_lock_date = fields.Date(compute="_compute_user_tax_lock_date")
    user_sale_lock_date = fields.Date(compute="_compute_user_sale_lock_date")
    user_purchase_lock_date = fields.Date(compute="_compute_user_purchase_lock_date")
    user_hard_lock_date = fields.Date(compute="_compute_user_hard_lock_date")
    transfer_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Inter-Banks Transfer Account",
        domain="[('reconcile', '=', True), ('account_type', '=', 'asset_current')]",
        check_company=True,
        help="Intermediary account used when moving money from a liquidity account to another",
    )
    expects_chart_of_accounts = fields.Boolean(
        string="Expects a Chart of Accounts",
        default=True,
    )
    chart_template = fields.Selection(selection="_selection_chart_templates")
    bank_account_code_prefix = fields.Char(string="Prefix of the bank accounts")
    cash_account_code_prefix = fields.Char(string="Prefix of the cash accounts")
    default_cash_difference_income_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Cash Difference Income",
        check_company=True,
    )
    default_cash_difference_expense_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Cash Difference Expense",
        check_company=True,
    )
    account_journal_suspense_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Journal Suspense Account",
        check_company=True,
    )
    account_journal_early_pay_discount_gain_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Cash Discount Write-Off Gain Account",
        check_company=True,
    )
    account_journal_early_pay_discount_loss_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Cash Discount Write-Off Loss Account",
        check_company=True,
    )
    transfer_account_code_prefix = fields.Char(string="Prefix of the transfer accounts")
    account_sale_tax_id = fields.Many2one(
        comodel_name="account.tax",
        string="Default Sale Tax",
        check_company=True,
    )
    account_purchase_tax_id = fields.Many2one(
        comodel_name="account.tax",
        string="Default Purchase Tax",
        check_company=True,
    )
    account_purchase_receipt_fiscal_position_id = fields.Many2one(
        comodel_name="account.fiscal.position",
        string="Default Purchase Receipt Fiscal Position",
        check_company=True,
    )
    tax_calculation_rounding_method = fields.Selection(
        selection=[
            ("round_globally", "Round per Tax"),
            ("round_per_line", "Round per Line"),
        ],
        default="round_globally",
    )
    currency_exchange_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Exchange Gain or Loss Journal",
        domain=[("type", "=", "general")],
    )
    income_currency_exchange_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Gain Exchange Rate Account",
        domain="[('internal_group', '=', 'income')]",
        check_company=True,
    )
    expense_currency_exchange_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Loss Exchange Rate Account",
        domain="[('account_type', 'in', ('expense', 'expense_other'))]",
        check_company=True,
    )
    anglo_saxon_accounting = fields.Boolean(string="Use anglo-saxon accounting")
    bank_journal_ids = fields.One2many(
        comodel_name="account.journal",
        string="Bank Journals",
        compute="_compute_bank_journal_ids",
    )
    incoterm_id = fields.Many2one(
        comodel_name="account.incoterms",
        string="Default incoterm",
        help="International Commercial Terms are a series of predefined commercial terms used in international transactions.",
    )

    qr_code = fields.Boolean(string="Display QR-code on invoices")
    link_qr_code = fields.Boolean(string="Display Link QR-code")

    display_invoice_amount_total_words = fields.Boolean(
        string="Total amount of invoice in letters"
    )
    display_invoice_tax_company_currency = fields.Boolean(
        string="Taxes in company currency",
        default=True,
    )
    account_use_credit_limit = fields.Boolean(
        string="Sales Credit Limit",
        help="Enable the use of credit limit on partners.",
    )

    batch_payment_sequence_id = fields.Many2one(
        comodel_name="ir.sequence",
        copy=False,
        readonly=True,
    )

    account_opening_move_id = fields.Many2one(
        comodel_name="account.move",
        string="Opening Journal Entry",
        help="The journal entry containing the initial balance of all this company's accounts.",
    )
    account_opening_journal_id = fields.Many2one(
        comodel_name="account.journal",
        related="account_opening_move_id.journal_id",
        string="Opening Journal",
        readonly=False,
        help="Journal where the opening entry of this company's accounting has been posted.",
    )
    account_opening_date = fields.Date(
        string="Opening Entry",
        help="That is the date of the opening entry.",
    )

    invoice_terms = fields.Html(
        string="Default Terms and Conditions",
        translate=True,
    )
    terms_type = fields.Selection(
        selection=[("plain", "Add a Note"), ("html", "Add a link to a Web Page")],
        string="Terms & Conditions format",
        default="plain",
    )
    invoice_terms_html = fields.Html(
        string="Default Terms and Conditions as a Web page",
        translate=True,
        sanitize_attributes=False,
        compute="_compute_invoice_terms_html",
        store=True,
        readonly=False,
    )

    account_default_pos_receivable_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Default PoS Receivable Account",
        check_company=True,
    )

    expense_accrual_account_id = fields.Many2one(
        comodel_name="account.account",
        domain="[('internal_group', '=', 'liability'), ('account_type', 'not in', ('asset_receivable', 'liability_payable'))]",
        check_company=True,
        help="Account used to move the period of an expense",
    )
    revenue_accrual_account_id = fields.Many2one(
        comodel_name="account.account",
        domain="[('internal_group', '=', 'asset'), ('account_type', 'not in', ('asset_receivable', 'liability_payable'))]",
        check_company=True,
        help="Account used to move the period of a revenue",
    )
    automatic_entry_default_journal_id = fields.Many2one(
        comodel_name="account.journal",
        domain="[('type', '=', 'general')]",
        check_company=True,
        help="Journal used by default for moving the period of an entry",
    )

    domestic_fiscal_position_id = fields.Many2one(
        comodel_name="account.fiscal.position",
        compute="_compute_domestic_fiscal_position_id",
    )
    account_fiscal_country_id = fields.Many2one(
        comodel_name="res.country",
        string="Fiscal Country",
        compute="_compute_account_fiscal_country_id",
        store=True,
        readonly=False,
        help="The country to use the tax reports from for this company",
    )
    account_fiscal_country_group_codes = fields.Json(
        compute="_compute_account_fiscal_country_group_codes"
    )

    account_enabled_tax_country_ids = fields.Many2many(
        comodel_name="res.country",
        string="l10n-used countries",
        compute="_compute_account_enabled_tax_country_ids",
        help="Technical field containing the countries for which this company is using tax-related features"
        "(hence the ones for which l10n modules need to show tax-related fields).",
    )

    tax_exigibility = fields.Boolean(string="Use Cash Basis")
    tax_cash_basis_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Cash Basis Journal",
        check_company=True,
    )
    account_cash_basis_base_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Base Tax Received Account",
        check_company=True,
        help="Account that will be set on lines created in cash basis journal entry and used to keep track of the "
        "tax base amount.",
    )

    account_storno = fields.Boolean(
        string="Storno accounting",
        compute="_compute_account_storno",
        store=True,
        readonly=False,
    )
    display_account_storno = fields.Boolean(compute="_compute_display_account_storno")

    fiscal_position_ids = fields.One2many(
        comodel_name="account.fiscal.position",
        compute="_compute_fiscal_position_ids",
    )
    multi_vat_foreign_country_ids = fields.Many2many(
        comodel_name="res.country",
        string="Foreign VAT countries",
        compute="_compute_multi_vat_foreign_country_ids",
        help="Countries for which the company has a VAT number",
    )

    quick_edit_mode = fields.Selection(
        selection=[
            ("out_invoices", "Customer Invoices"),
            ("in_invoices", "Vendor Bills"),
            ("out_and_in_invoices", "Customer Invoices and Vendor Bills"),
        ],
        string="Quick encoding",
    )

    account_discount_income_allocation_id = fields.Many2one(
        comodel_name="account.account",
        string="Separate account for income discount",
    )
    account_discount_expense_allocation_id = fields.Many2one(
        comodel_name="account.account",
        string="Separate account for expense discount",
    )

    restrictive_audit_trail = fields.Boolean(
        tracking=True,
        help="Enable this option to prevent deletion of journal item related logs",
    )
    force_restrictive_audit_trail = fields.Boolean(
        string="Force Audit Trail",
        compute="_compute_force_restrictive_audit_trail",
    )

    autopost_bills = fields.Boolean(
        string="Auto-validate bills",
        default=True,
    )

    account_price_include = fields.Selection(
        selection=[("tax_included", "Tax Included"), ("tax_excluded", "Tax Excluded")],
        string="Default Sales Price Include",
        default="tax_excluded",
        required=True,
        help="Default on whether the sales price used on the product and invoices with this Company includes its taxes.",
    )
    company_vat_placeholder = fields.Char(compute="_compute_company_vat_placeholder")

    income_account_id = fields.Many2one(
        comodel_name="account.account",
        domain=ACCOUNT_DOMAIN,
        help="This account will be used when validating a customer invoice.",
    )
    expense_account_id = fields.Many2one(
        comodel_name="account.account",
        domain=ACCOUNT_DOMAIN,
        help="The expense is accounted for when a vendor bill is validated, except in anglo-saxon"
        " accounting with perpetual inventory valuation in which case the expense (Cost of"
        " Goods Sold account) is recognized at the customer invoice validation.",
    )
    price_difference_account_id = fields.Many2one(
        comodel_name="account.account",
        domain=ACCOUNT_DOMAIN,
        help="During perpetual valuation, this account will hold the price difference between the standard price and the bill price.",
    )

    totals_below_sections = fields.Boolean(
        string="Add totals below sections",
        compute="_compute_totals_below_sections",
        store=True,
        readonly=False,
        help="When ticked, totals and subtotals appear below the sections of the report.",
    )

    account_return_periodicity = fields.Selection(
        selection=PERIODS,
        string="Delay units",
        default="monthly",
        required=True,
        help="Periodicity",
    )
    account_return_reminder_day = fields.Integer(
        string="Start from",
        default=7,
        required=True,
    )
    account_tax_return_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Journal",
        domain=[("type", "=", "general")],
        check_company=True,
    )
    account_revaluation_journal_id = fields.Many2one(
        comodel_name="account.journal",
        domain=[("type", "=", "general")],
        check_company=True,
    )
    account_revaluation_expense_provision_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Expense Provision Account",
        check_company=True,
    )
    account_revaluation_income_provision_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Income Provision Account",
        check_company=True,
    )
    account_tax_unit_ids = fields.Many2many(
        comodel_name="account.tax.unit",
        string="Tax Units",
        compute="_compute_account_tax_unit_ids",
        search="_search_account_tax_unit_ids",
        help="The tax units this company belongs to.",
    )
    account_representative_id = fields.Many2one(
        comodel_name="res.partner",
        string="Accounting Firm",
        index="btree_not_null",
        help="Specify an Accounting Firm that will act as a representative when exporting reports.",
    )
    account_display_representative_field = fields.Boolean(
        compute="_compute_account_display_representative_field"
    )
    account_last_return_cron_refresh = fields.Datetime()

    invoicing_switch_threshold = fields.Date(
        help="Every payment and invoice before this date will receive the 'From Invoicing' status, hiding all the accounting entries related to it. Use this option after installing Accounting if you were using only Invoicing before, before importing all your actual accounting data in to Odoo."
    )
    predict_bill_product = fields.Boolean()

    sign_invoice = fields.Boolean(string="Display signing field on invoices")
    signing_user = fields.Many2one(comodel_name="res.users")

    deferred_expense_journal_id = fields.Many2one(comodel_name="account.journal")
    deferred_expense_account_id = fields.Many2one(comodel_name="account.account")
    generate_deferred_expense_entries_method = fields.Selection(
        selection=[
            ("on_validation", "On bill validation"),
            ("manual", "Manually & Grouped"),
        ],
        string="Generate Deferred Expense Entries",
        default="on_validation",
        required=True,
    )
    deferred_expense_amount_computation_method = fields.Selection(
        selection=[
            ("day", "Days"),
            ("month", "Months"),
            ("full_months", "Full Months"),
        ],
        string="Deferred Expense Based on",
        default="month",
        required=True,
    )

    deferred_revenue_journal_id = fields.Many2one(comodel_name="account.journal")
    deferred_revenue_account_id = fields.Many2one(comodel_name="account.account")
    generate_deferred_revenue_entries_method = fields.Selection(
        selection=[
            ("on_validation", "On bill validation"),
            ("manual", "Manually & Grouped"),
        ],
        string="Generate Deferred Revenue Entries",
        default="on_validation",
        required=True,
    )
    deferred_revenue_amount_computation_method = fields.Selection(
        selection=[
            ("day", "Days"),
            ("month", "Months"),
            ("full_months", "Full Months"),
        ],
        string="Deferred Revenue Based on",
        default="month",
        required=True,
    )

    @api.model
    def _get_field_names_delegated_to_root(self):
        return super()._get_field_names_delegated_to_root() + [
            "fiscalyear_last_day",
            "fiscalyear_last_month",
            "account_storno",
            "tax_exigibility",
        ]

    @api.model
    def _selection_chart_templates(self):
        return self.env["res.company"]._selection_chart_templates()

    @api.constrains("restrictive_audit_trail")
    def _check_audit_trail_restriction(self):
        if any(
            not config.restrictive_audit_trail and config.force_restrictive_audit_trail
            for config in self
        ):
            raise ValidationError(
                _("Can't disable restricted audit trail: forced by localization.")
            )

    @api.constrains("account_price_include")
    def _check_set_account_price_include(self):
        if any(config.company_id.sudo()._existing_accounting() for config in self):
            raise ValidationError(
                _(
                    "Cannot change Price Tax computation method on a company that has already started invoicing."
                )
            )

    @api.constrains(
        "account_opening_move_id", "fiscalyear_last_day", "fiscalyear_last_month"
    )
    def _check_fiscalyear_last_day(self):
        for config in self:
            if config.fiscalyear_last_day == 29 and config.fiscalyear_last_month == "2":
                continue
            if config.account_opening_date:
                year = config.account_opening_date.year
            else:
                year = fields.Date.context_today(config).year
            max_day = calendar.monthrange(year, int(config.fiscalyear_last_month))[1]
            if config.fiscalyear_last_day <= 0 or config.fiscalyear_last_day > max_day:
                raise ValidationError(_("Invalid fiscal year last day"))

    def _compute_force_restrictive_audit_trail(self):
        for config in self:
            config.force_restrictive_audit_trail = False

    @api.depends("company_id")
    def _compute_bank_journal_ids(self):
        journals = self.env["account.journal"].search(
            [("company_id", "in", self.company_id.ids), ("type", "=", "bank")]
        )
        by_company = journals.grouped("company_id")
        for config in self:
            config.bank_journal_ids = by_company.get(
                config.company_id, self.env["account.journal"]
            )

    @api.depends("company_id")
    def _compute_fiscal_position_ids(self):
        positions = self.env["account.fiscal.position"].search(
            [("company_id", "in", self.company_id.ids)]
        )
        by_company = positions.grouped("company_id")
        for config in self:
            config.fiscal_position_ids = by_company.get(
                config.company_id, self.env["account.fiscal.position"]
            )

    @api.depends("company_id.country_id")
    def _compute_domestic_fiscal_position_id(self):
        for config in self:
            country = config.company_id.country_id
            potential_domestic_fps = config.fiscal_position_ids.filtered_domain(
                Domain("country_id", "=", country.id)
                | Domain(
                    [
                        ("country_id", "=", False),
                        ("country_group_id", "in", country.country_group_ids.ids),
                    ]
                ),
            ).sorted(lambda fp: (fp.sequence, fp.country_id.id or float("inf")))
            config.domestic_fiscal_position_id = potential_domestic_fps[:1]

    @api.depends("account_fiscal_country_id")
    def _compute_account_fiscal_country_group_codes(self):
        for config in self:
            config.account_fiscal_country_group_codes = (
                config.account_fiscal_country_id.country_group_codes
                if config.account_fiscal_country_id
                else [""]
            )

    def _get_foreign_vat_countries_per_company(self, companies):
        FiscalPosition = self.env["account.fiscal.position"]
        return {
            company.id: self.env["res.country"].browse(filter(None, country_ids))
            for company, country_ids in FiscalPosition._read_group(
                domain=[
                    *FiscalPosition._check_company_domain(companies),
                    ("foreign_vat", "!=", False),
                ],
                groupby=["company_id"],
                aggregates=["country_id:array_agg"],
            )
        }

    def _compute_multi_vat_foreign_country_ids(self):
        countries_per_company = self._get_foreign_vat_countries_per_company(
            self.company_id
        )
        for config in self:
            config.multi_vat_foreign_country_ids = countries_per_company.get(
                config.company_id.id, self.env["res.country"]
            )

    @api.depends("company_id.country_id")
    def _compute_account_fiscal_country_id(self):
        for config in self:
            if not config.account_fiscal_country_id:
                config.account_fiscal_country_id = config.company_id.country_id

    @api.depends("account_fiscal_country_id")
    @api.depends_context("uid")
    def _compute_account_enabled_tax_country_ids(self):
        allowed_companies = self.env.user.company_ids
        countries_per_company = self._get_foreign_vat_countries_per_company(
            self.company_id & allowed_companies
        )
        for config in self:
            if config.company_id not in allowed_companies:
                config.account_enabled_tax_country_ids = False
                continue
            foreign_vat_countries = countries_per_company.get(
                config.company_id.id, self.env["res.country"]
            )
            config.account_enabled_tax_country_ids = (
                foreign_vat_countries + config.account_fiscal_country_id
            )

    @api.depends("terms_type")
    def _compute_invoice_terms_html(self):
        for config in self.filtered(
            lambda config: (
                is_html_empty(config.invoice_terms_html) and config.terms_type == "html"
            )
        ):
            html = self.env["ir.qweb"]._render(
                "account.account_default_terms_and_conditions",
                {
                    "company_name": config.company_id.name,
                    "company_country": config.company_id.country_id.name,
                },
                raise_if_not_found=False,
            )
            if html:
                config.invoice_terms_html = html

    def _compute_user_soft_lock_date(self, soft_lock_date_field):
        ignore_exceptions = bool(self.env.context.get("ignore_exceptions", False))
        user_lock_date_field = f"user_{soft_lock_date_field}"
        for config in self:
            config[user_lock_date_field] = config.company_id._get_user_lock_date(
                soft_lock_date_field, ignore_exceptions
            )

    @api.depends("fiscalyear_lock_date")
    @api.depends_context("uid", "ignore_exceptions")
    def _compute_user_fiscalyear_lock_date(self):
        self._compute_user_soft_lock_date("fiscalyear_lock_date")

    @api.depends("tax_lock_date")
    @api.depends_context("uid", "ignore_exceptions")
    def _compute_user_tax_lock_date(self):
        self._compute_user_soft_lock_date("tax_lock_date")

    @api.depends("sale_lock_date")
    @api.depends_context("uid", "ignore_exceptions")
    def _compute_user_sale_lock_date(self):
        self._compute_user_soft_lock_date("sale_lock_date")

    @api.depends("purchase_lock_date")
    @api.depends_context("uid", "ignore_exceptions")
    def _compute_user_purchase_lock_date(self):
        self._compute_user_soft_lock_date("purchase_lock_date")

    @api.depends("hard_lock_date")
    def _compute_user_hard_lock_date(self):
        for config in self:
            parents = (
                config.company_id.with_context(active_test=False).sudo().parent_ids
            )
            config.user_hard_lock_date = max(
                parent.account_config_id.hard_lock_date or date.min
                for parent in parents
            )

    @api.depends("account_fiscal_country_id")
    def _compute_account_storno(self):
        for config in self:
            config.account_storno = (
                config.account_fiscal_country_id.code in STORNO_MANDATORY_COUNTRIES
            )

    @api.depends("account_fiscal_country_id")
    def _compute_display_account_storno(self):
        for config in self:
            config.display_account_storno = (
                config.account_fiscal_country_id.code
                in STORNO_MANDATORY_COUNTRIES | STORNO_OPTIONAL_COUNTRIES
            )

    @api.depends("account_fiscal_country_id", "company_id.country_id")
    def _compute_company_vat_placeholder(self):
        Partner = self.env["res.partner"]
        for config in self:
            country = config.company_id.country_id or config.account_fiscal_country_id
            expected_vat = Partner._get_expected_vat_format(country.code)
            config.company_vat_placeholder = (
                _("%s, or / if not applicable", expected_vat)
                if expected_vat
                else _("/ if not applicable")
            )

    def action_save_onboarding_sale_tax(self):
        self.env["onboarding.onboarding.step"].action_validate_step(
            "account.onboarding_onboarding_step_sales_tax"
        )

    @api.depends("account_fiscal_country_id.code")
    def _compute_account_display_representative_field(self):
        for config in self:
            country_set = config.company_id._get_countries_allowing_tax_representative()
            config.account_display_representative_field = (
                config.account_fiscal_country_id.code in country_set
            )

    @api.depends("anglo_saxon_accounting")
    def _compute_totals_below_sections(self):
        for config in self:
            config.totals_below_sections = config.anglo_saxon_accounting

    def _search_account_tax_unit_ids(self, operator, value):
        units = self.env["account.tax.unit"].search([("id", operator, value)])
        if operator in ("=", "!=") and not value:
            companies = self.env["account.tax.unit"].search([]).company_ids
            return [
                ("company_id", "not in" if operator == "=" else "in", companies.ids)
            ]
        return [("company_id", "in", units.company_ids.ids)]

    @api.depends("company_id")
    def _compute_account_tax_unit_ids(self):
        units = self.env["account.tax.unit"].search(
            [("company_ids", "in", self.company_id.ids)]
        )
        for config in self:
            company = config.company_id
            config.account_tax_unit_ids = units.filtered(
                lambda unit, company=company: company in unit.company_ids
            )

    def _apply_invoicing_switch(self, vals, old_threshold_vals):
        for record in self.exists():
            if (
                "invoicing_switch_threshold" in vals
                and old_threshold_vals[record] != record.invoicing_switch_threshold
            ):
                _debug.logic(
                    "invoicing_switch_moved",
                    company=record,
                    previous=old_threshold_vals[record],
                    threshold=record.invoicing_switch_threshold,
                    mode="apply" if record.invoicing_switch_threshold else "clear",
                )
                self.env["account.move.line"].flush_model(["move_id", "parent_state"])
                self.env["account.move"].flush_model(
                    [
                        "company_id",
                        "date",
                        "state",
                        "payment_state",
                        "payment_state_before_switch",
                    ]
                )
                if record.invoicing_switch_threshold:
                    params = {
                        "company_id": record.company_id.id,
                        "switch_threshold": record.invoicing_switch_threshold,
                    }
                    self.env.cr.execute(
                        """
                        update account_move_line aml
                        set parent_state = 'posted'
                        from account_move move
                        where aml.move_id = move.id
                        and move.payment_state = 'invoicing_legacy'
                        and move.date >= %(switch_threshold)s
                        and move.company_id = %(company_id)s
                    """,
                        params,
                    )
                    _debug.perf.count(
                        "legacy_lines_reposted",
                        company=record,
                        rows=self.env.cr.rowcount,
                    )
                    self.env.cr.execute(
                        """
                        update account_move
                        set state = 'posted',
                            payment_state = payment_state_before_switch,
                            payment_state_before_switch = null
                        where payment_state = 'invoicing_legacy'
                        and date >= %(switch_threshold)s
                        and company_id = %(company_id)s
                    """,
                        params,
                    )
                    _debug.perf.count(
                        "legacy_moves_reposted",
                        company=record,
                        rows=self.env.cr.rowcount,
                    )
                    self.env.cr.execute(
                        """
                        update account_move_line aml
                        set parent_state = 'cancel'
                        from account_move move
                        where aml.move_id = move.id
                        and move.state = 'posted'
                        and move.date < %(switch_threshold)s
                        and move.company_id = %(company_id)s
                    """,
                        params,
                    )
                    _debug.perf.count(
                        "pre_threshold_lines_cancelled",
                        company=record,
                        rows=self.env.cr.rowcount,
                    )
                    self.env.cr.execute(
                        """
                        update account_move
                        set state = 'cancel',
                            payment_state_before_switch = payment_state,
                            payment_state = 'invoicing_legacy'
                        where state = 'posted'
                        and date < %(switch_threshold)s
                        and company_id = %(company_id)s
                    """,
                        params,
                    )
                    _debug.perf.count(
                        "pre_threshold_moves_cancelled",
                        company=record,
                        rows=self.env.cr.rowcount,
                    )
                else:
                    params = {"company_id": record.company_id.id}
                    self.env.cr.execute(
                        """
                        update account_move_line aml
                        set parent_state = 'posted'
                        from account_move move
                        where aml.move_id = move.id
                        and move.payment_state = 'invoicing_legacy'
                        and move.company_id = %(company_id)s
                    """,
                        params,
                    )
                    _debug.perf.count(
                        "legacy_lines_restored",
                        company=record,
                        rows=self.env.cr.rowcount,
                    )
                    self.env.cr.execute(
                        """
                        update account_move
                        set state = 'posted',
                            payment_state = payment_state_before_switch,
                            payment_state_before_switch = null
                        where payment_state = 'invoicing_legacy'
                        and company_id = %(company_id)s
                    """,
                        params,
                    )
                    _debug.perf.count(
                        "legacy_moves_restored",
                        company=record,
                        rows=self.env.cr.rowcount,
                    )

                self.env["account.move.line"].invalidate_model(["parent_state"])
                self.env["account.move"].invalidate_model(
                    ["state", "payment_state", "payment_state_before_switch"]
                )

    def _sync_returns_after_write(self, vals):
        companies = self.company_id
        if "account_opening_date" in vals:
            self.env["account.return.type"].with_context(
                # 2 years to make sure we cover all cases, such as yearly returns with a deadline of more than 1 year.
                forced_date_from=self.account_opening_date - relativedelta(years=2),
                forced_date_to=datetime.date.today() + relativedelta(years=1),
            )._sync_all_returns(companies.root_id)
        elif (
            set(vals) & {"account_return_periodicity", "account_return_reminder_day"}
            and self.account_opening_date
        ):
            self.env["account.return.type"]._sync_all_returns(companies.root_id)

    def _check_locks(self, values):
        new_locks = {
            field: fields.Date.to_date(values[field])
            for field in LOCK_DATE_FIELDS
            if field in values
        }
        fiscalyear_lock_date = new_locks.get("fiscalyear_lock_date")
        hard_lock_date = new_locks.get("hard_lock_date")
        fiscal_lock_date = None
        if fiscalyear_lock_date or hard_lock_date:
            fiscal_lock_date = max(
                fiscalyear_lock_date or date.min, hard_lock_date or date.min
            )
        if "hard_lock_date" in new_locks:
            for config in self:
                if not config.hard_lock_date:
                    continue
                if not hard_lock_date:
                    raise UserError(_("The Hard Lock Date cannot be removed."))
                if hard_lock_date < config.hard_lock_date:
                    raise UserError(
                        _(
                            "A new Hard Lock Date must be posterior (or equal) to the previous one."
                        )
                    )
        companies = self.company_id
        if hard_lock_date:
            draft_entries = self.env["account.move"].search(
                [
                    ("company_id", "child_of", companies.ids),
                    ("state", "=", "draft"),
                    ("date", "<=", hard_lock_date),
                ]
            )
            if draft_entries:
                error_msg = _(
                    "There are still draft entries in the period you want to hard lock. You should either post or delete them."
                )
                action_error = {
                    "view_mode": "list",
                    "name": _("Draft Entries"),
                    "res_model": "account.move",
                    "type": "ir.actions.act_window",
                    "domain": [("id", "in", draft_entries.ids)],
                    "search_view_id": [
                        self.env.ref("account.view_account_move_filter").id,
                        "search",
                    ],
                    "views": [
                        [self.env.ref("account.view_move_tree_multi_edit").id, "list"],
                        [self.env.ref("account.view_move_form").id, "form"],
                    ],
                }
                raise RedirectWarning(error_msg, action_error, _("Show draft entries"))
        if fiscal_lock_date:
            unreconciled_statement_lines = self.env[
                "account.bank.statement.line"
            ].search(
                companies._get_domain_unreconciled_statement_lines(fiscal_lock_date)
            )
            if unreconciled_statement_lines:
                error_msg = _(
                    "There are still unreconciled bank statement lines in the period you want to lock."
                    "You should either reconcile or delete them."
                )
                action_error = (
                    companies._get_unreconciled_statement_lines_redirect_action(
                        unreconciled_statement_lines
                    )
                )
                raise RedirectWarning(
                    error_msg, action_error, _("Show Unreconciled Bank Statement Line")
                )

    def write(self, vals):
        self._check_locks(vals)
        old_threshold_vals = {
            config: config.invoicing_switch_threshold for config in self.exists()
        }
        self.invalidate_model(
            fnames=[f"user_{field}" for field in LOCK_DATE_FIELDS if field in vals]
        )
        for config in self:
            if bank_prefix := vals.get("bank_account_code_prefix"):
                config.company_id.reflect_code_prefix_change(
                    config.bank_account_code_prefix, bank_prefix
                )
            if cash_prefix := vals.get("cash_account_code_prefix"):
                config.company_id.reflect_code_prefix_change(
                    config.cash_account_code_prefix, cash_prefix
                )
        res = super().write(vals)
        self.company_id._set_category_defaults(vals)
        self._apply_invoicing_switch(vals, old_threshold_vals)
        self._sync_returns_after_write(vals)
        changed_soft_lock_fields = [
            field for field in SOFT_LOCK_DATE_FIELDS if field in vals
        ]
        if changed_soft_lock_fields:
            LockException = self.env["account.lock_exception"]
            domain = Domain.OR(
                LockException._get_domain_active_exceptions(
                    config.company_id, changed_soft_lock_fields
                )
                for config in self
            )
            LockException.search(domain)._recreate()
        return res
