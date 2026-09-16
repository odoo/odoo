import calendar
from collections import defaultdict
from datetime import date, timedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import LockError, RedirectWarning, UserError, ValidationError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, date_utils, format_list
from odoo.tools.mail import is_html_empty
from odoo.tools.misc import format_date

from odoo.addons.account.models.account_move import MAX_HASH_VERSION
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

PEPPOL_DEFAULT_COUNTRIES = [
    "AT",
    "BE",
    "CH",
    "CY",
    "CZ",
    "DE",
    "DK",
    "EE",
    "ES",
    "FI",
    "FR",
    "GR",
    "IE",
    "IS",
    "IT",
    "LT",
    "LU",
    "LV",
    "MT",
    "NL",
    "NO",
    "PL",
    "PT",
    "RO",
    "SE",
    "SI",
]

PEPPOL_MAILING_COUNTRIES = [
    "BE",
    "LU",
    "NL",
    "SE",
    "NO",
]

PEPPOL_LIST = PEPPOL_DEFAULT_COUNTRIES + [
    "AD",
    "AL",
    "BA",
    "BG",
    "BL",
    "GB",
    "GF",
    "GP",
    "HR",
    "HU",
    "LI",
    "MC",
    "ME",
    "MF",
    "MK",
    "MQ",
    "NC",
    "PF",
    "PM",
    "RE",
    "RS",
    "SK",
    "SM",
    "TF",
    "TR",
    "VA",
    "WF",
    "YT",
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

INTEGRITY_HASH_BATCH_SIZE = 1000

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


class ResCompany(models.Model):
    _name = "res.company"
    _inherit = ["res.company", "mixin.mail.thread"]

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
        inverse_name="company_id",
        string="Bank Journals",
        domain=[("type", "=", "bank")],
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
        store=True,
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
        inverse_name="company_id",
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

    @api.constrains("restrictive_audit_trail")
    @_debug.perf.timed
    def _check_audit_trail_restriction(self):
        companies = self.filtered(
            lambda c: not c.restrictive_audit_trail and c.force_restrictive_audit_trail
        )
        if companies:
            raise ValidationError(
                _("Can't disable restricted audit trail: forced by localization.")
            )

    @api.constrains("account_price_include")
    @_debug.perf.timed
    def _check_set_account_price_include(self):
        if any(company.sudo()._existing_accounting() for company in self):
            raise ValidationError(
                _(
                    "Cannot change Price Tax computation method on a company that has already started invoicing."
                )
            )

    @api.constrains(
        "account_opening_move_id", "fiscalyear_last_day", "fiscalyear_last_month"
    )
    @_debug.perf.timed
    def _check_fiscalyear_last_day(self):
        for rec in self:
            if rec.fiscalyear_last_day == 29 and rec.fiscalyear_last_month == "2":
                continue

            if rec.account_opening_date:
                year = rec.account_opening_date.year
            else:
                year = fields.Date.context_today(rec).year

            max_day = calendar.monthrange(year, int(rec.fiscalyear_last_month))[1]
            if rec.fiscalyear_last_day <= 0 or rec.fiscalyear_last_day > max_day:
                raise ValidationError(_("Invalid fiscal year last day"))

    def _compute_force_restrictive_audit_trail(self):
        for company in self:
            company.force_restrictive_audit_trail = False

    @api.depends(
        "country_id",
        "fiscal_position_ids",
        "fiscal_position_ids.sequence",
        "fiscal_position_ids.country_id",
        "fiscal_position_ids.country_group_id",
    )
    @_debug.perf.timed
    def _compute_domestic_fiscal_position_id(self):
        for company in self:
            potential_domestic_fps = company.fiscal_position_ids.filtered_domain(
                Domain("country_id", "=", company.country_id.id)
                | Domain(
                    [
                        ("country_id", "=", False),
                        (
                            "country_group_id",
                            "in",
                            company.country_id.country_group_ids.ids,
                        ),
                    ]
                ),
            ).sorted(lambda fp: (fp.sequence, fp.country_id.id or float("inf")))
            company.domestic_fiscal_position_id = potential_domestic_fps[:1]

    @api.depends("account_fiscal_country_id")
    def _compute_account_fiscal_country_group_codes(self):
        for company in self:
            company.account_fiscal_country_group_codes = (
                company.account_fiscal_country_id.country_group_codes
                if company.account_fiscal_country_id
                else [""]
            )

    def get_next_batch_payment_communication(self):
        self.check_singleton()
        company_sudo = self.sudo()
        if not company_sudo.batch_payment_sequence_id:
            company_sudo.batch_payment_sequence_id = (
                self.env["ir.sequence"]
                .sudo()
                .create(
                    {
                        "name": _("Group Payments Number Sequence"),
                        "implementation": "no_gap",
                        "padding": 5,
                        "use_date_range": True,
                        "company_id": self.id,
                        "prefix": "GROUP/%(year)s/",
                    }
                )
            )
        return company_sudo.batch_payment_sequence_id.next_by_id()

    def _get_field_names_delegated_to_root(self):
        return super()._get_field_names_delegated_to_root() + [
            "fiscalyear_last_day",
            "fiscalyear_last_month",
            "account_storno",
            "tax_exigibility",
        ]

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

    @api.depends("fiscal_position_ids.foreign_vat", "fiscal_position_ids.country_id")
    def _compute_multi_vat_foreign_country_ids(self):
        countries_per_company = self._get_foreign_vat_countries_per_company(self)
        for company in self:
            company.multi_vat_foreign_country_ids = countries_per_company.get(
                company.id, self.env["res.country"]
            )

    @api.depends("country_id")
    def _compute_account_fiscal_country_id(self):
        for record in self:
            if not record.account_fiscal_country_id:
                record.account_fiscal_country_id = record.country_id

    @api.depends(
        "account_fiscal_country_id",
        "fiscal_position_ids.foreign_vat",
        "fiscal_position_ids.country_id",
    )
    @api.depends_context("uid")
    def _compute_account_enabled_tax_country_ids(self):
        allowed_companies = self.env.user.company_ids
        countries_per_company = self._get_foreign_vat_countries_per_company(
            self & allowed_companies
        )
        for record in self:
            if record not in allowed_companies:
                record.account_enabled_tax_country_ids = False
                continue
            foreign_vat_countries = countries_per_company.get(
                record.id, self.env["res.country"]
            )
            record.account_enabled_tax_country_ids = (
                foreign_vat_countries + record.account_fiscal_country_id
            )

    @api.depends("terms_type")
    @_debug.perf.timed
    def _compute_invoice_terms_html(self):
        for company in self.filtered(
            lambda company: (
                is_html_empty(company.invoice_terms_html)
                and company.terms_type == "html"
            )
        ):
            html = self.env["ir.qweb"]._render(
                "account.account_default_terms_and_conditions",
                {
                    "company_name": company.name,
                    "company_country": company.country_id.name,
                },
                raise_if_not_found=False,
            )
            if html:
                company.invoice_terms_html = html

    def _compute_user_soft_lock_date(self, soft_lock_date_field):
        ignore_exceptions = bool(self.env.context.get("ignore_exceptions", False))
        user_lock_date_field = f"user_{soft_lock_date_field}"
        for company in self:
            company[user_lock_date_field] = company._get_user_lock_date(
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
        for company in self:
            company.user_hard_lock_date = max(
                c.hard_lock_date or date.min
                for c in company.with_context(active_test=False).sudo().parent_ids
            )

    @api.depends("account_fiscal_country_id")
    def _compute_account_storno(self):
        for company in self:
            company.account_storno = (
                company.account_fiscal_country_id.code in STORNO_MANDATORY_COUNTRIES
            )

    @api.depends("account_fiscal_country_id")
    def _compute_display_account_storno(self):
        for company in self:
            company.display_account_storno = (
                company.account_fiscal_country_id.code
                in STORNO_MANDATORY_COUNTRIES | STORNO_OPTIONAL_COUNTRIES
            )

    def _initiate_account_onboardings(self):
        account_onboarding_routes = [
            "account_dashboard",
        ]
        onboardings = (
            self.env["onboarding.onboarding"]
            .sudo()
            .search([("route_name", "in", account_onboarding_routes)])
        )
        for company in self:
            onboardings.with_company(company)._search_or_create_progress()

    @api.model_create_multi
    @_debug.perf.timed
    def create(self, vals_list):
        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "create",
                model=self._name,
                count=len(vals_list),
                fields=sorted({key for vals in vals_list for key in vals}),
            )
        companies = super().create(vals_list)
        for company in companies:
            if root_template := company.root_id.chart_template:
                _debug.pipeline(
                    "created_under_root_template_chart",
                    company=company,
                    root_template=root_template,
                )

                def try_loading(company=company, root_template=root_template):
                    self.env["account.chart.template"]._load(
                        root_template,
                        company,
                        install_demo=False,
                    )

                self.env.cr.precommit.add(try_loading)
        companies._set_category_defaults()
        return companies

    @staticmethod
    def get_new_account_code(current_code, old_prefix, new_prefix):
        digits = len(current_code)
        tail = current_code.removeprefix(old_prefix).lstrip("0")
        return new_prefix + tail.rjust(digits - len(new_prefix), "0")

    def reflect_code_prefix_change(self, old_code, new_code):
        self.check_singleton()
        if not old_code or new_code == old_code:
            return
        accounts = (
            self.env["account.account"]
            .with_company(self)
            .search(
                [
                    *self.env["account.account"]._check_company_domain(self),
                    ("code", "=like", old_code + "%"),
                    ("account_type", "in", ("asset_cash", "liability_credit_card")),
                ],
                order="code asc",
            )
        )
        for account in accounts:
            account.write(
                {"code": self.get_new_account_code(account.code, old_code, new_code)}
            )

    def _get_unreconciled_statement_lines_redirect_action(
        self, unreconciled_statement_lines
    ):
        action = {
            "name": _("Unreconciled Transactions"),
            "type": "ir.actions.act_window",
            "res_model": "account.bank.statement.line",
            "context": {"create": False},
        }
        if len(unreconciled_statement_lines) == 1:
            action.update(
                {
                    "view_mode": "form",
                    "res_id": unreconciled_statement_lines.id,
                }
            )
        else:
            action.update(
                {
                    "view_mode": "list,form",
                    "domain": [("id", "in", unreconciled_statement_lines.ids)],
                }
            )
        return action

    def _get_domain_unreconciled_statement_lines(self, last_date):
        return [
            ("company_id", "child_of", self.ids),
            ("is_reconciled", "=", False),
            ("date", "<=", last_date),
            ("move_id.state", "in", ("draft", "posted")),
        ]

    @_debug.perf.timed
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
        if _debug.logic.enabled:
            _debug.logic(
                "locks_requested",
                company=self,
                fields=sorted(new_locks),
                hard_lock_date=hard_lock_date,
                fiscal_lock_date=fiscal_lock_date,
            )

        if "hard_lock_date" in new_locks:
            for company in self:
                if not company.hard_lock_date:
                    continue
                if not hard_lock_date:
                    _debug.logic(
                        "lock_date_violated",
                        company=company,
                        reason="hard_lock_removed",
                        previous=company.hard_lock_date,
                    )
                    raise UserError(_("The Hard Lock Date cannot be removed."))
                if hard_lock_date < company.hard_lock_date:
                    _debug.logic(
                        "lock_date_violated",
                        company=company,
                        reason="hard_lock_backdated",
                        previous=company.hard_lock_date,
                        requested=hard_lock_date,
                    )
                    raise UserError(
                        _(
                            "A new Hard Lock Date must be posterior (or equal) to the previous one."
                        )
                    )

        if hard_lock_date:
            draft_entries = self.env["account.move"].search(
                [
                    ("company_id", "child_of", self.ids),
                    ("state", "=", "draft"),
                    ("date", "<=", hard_lock_date),
                ]
            )
            _debug.logic(
                "hard_lock_draft_check",
                company=self,
                hard_lock_date=hard_lock_date,
                draft_entries=draft_entries,
                blocked=bool(draft_entries),
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
            ].search(self._get_domain_unreconciled_statement_lines(fiscal_lock_date))
            _debug.logic(
                "fiscal_lock_stline_check",
                company=self,
                fiscal_lock_date=fiscal_lock_date,
                unreconciled=len(unreconciled_statement_lines),
                blocked=bool(unreconciled_statement_lines),
            )
            if unreconciled_statement_lines:
                error_msg = _(
                    "There are still unreconciled bank statement lines in the period you want to lock."
                    "You should either reconcile or delete them."
                )
                action_error = self._get_unreconciled_statement_lines_redirect_action(
                    unreconciled_statement_lines
                )
                raise RedirectWarning(
                    error_msg, action_error, _("Show Unreconciled Bank Statement Line")
                )

    def _get_soft_lock_date_exception(self, company, soft_lock_date_field):
        return self.env["account.lock_exception"].search(
            [
                ("state", "=", "active"),
                "|",
                ("user_id", "=", False),
                ("user_id", "=", self.env.user.id),
                (soft_lock_date_field, "<", company[soft_lock_date_field]),
                ("company_id", "=", company.id),
            ],
            order="lock_date asc NULLS FIRST",
            limit=1,
        )

    def _get_user_lock_date(self, soft_lock_date_field, ignore_exceptions=False):
        self.check_singleton()
        soft_lock_date = date.min
        for company in self.with_context(active_test=False).sudo().parent_ids:
            if company[soft_lock_date_field]:
                if ignore_exceptions:
                    exception = None
                else:
                    exception = self._get_soft_lock_date_exception(
                        company, soft_lock_date_field
                    )
                if exception:
                    soft_lock_date = max(
                        soft_lock_date, exception[soft_lock_date_field] or date.min
                    )
                else:
                    soft_lock_date = max(soft_lock_date, company[soft_lock_date_field])
        _debug.logic(
            "user_lock_date_resolved",
            company=self,
            field=soft_lock_date_field,
            lock_date=soft_lock_date,
            ignore_exceptions=ignore_exceptions,
        )
        return soft_lock_date

    def _get_user_fiscal_lock_date(self, journal, ignore_exceptions=False):
        self.check_singleton()
        company = self.with_context(ignore_exceptions=ignore_exceptions)
        lock = max(company.user_fiscalyear_lock_date, company.user_hard_lock_date)
        if journal.type == "sale":
            lock = max(company.user_sale_lock_date, lock)
        elif journal.type == "purchase":
            lock = max(company.user_purchase_lock_date, lock)
        return lock

    def _get_violated_soft_lock_date(self, soft_lock_date_field, accounting_date):
        if not self:
            return None
        self.check_singleton()
        user_lock_date_field = f"user_{soft_lock_date_field}"
        regular_lock_date = self.with_context(ignore_exceptions=True)[
            user_lock_date_field
        ]
        if accounting_date > regular_lock_date:
            return None
        user_lock_date = self.with_context(ignore_exceptions=False)[
            user_lock_date_field
        ]
        return None if accounting_date > user_lock_date else user_lock_date

    @_debug.perf.timed
    def _get_lock_date_violations(
        self,
        accounting_date,
        fiscalyear=True,
        sale=True,
        purchase=True,
        tax=True,
        hard=True,
    ):
        self.check_singleton()
        locks = []

        if not accounting_date:
            return locks

        soft_lock_date_fields_to_check = [
            ("fiscalyear_lock_date", fiscalyear),
            ("sale_lock_date", sale),
            ("purchase_lock_date", purchase),
            ("tax_lock_date", tax),
        ]
        for field, to_check in soft_lock_date_fields_to_check:
            if not to_check:
                continue
            violated_date = self._get_violated_soft_lock_date(field, accounting_date)
            if violated_date:
                locks.append((violated_date, field))

        if hard:
            hard_lock_date = self.user_hard_lock_date
            if accounting_date <= hard_lock_date:
                locks.append((hard_lock_date, "hard_lock_date"))

        if _debug.logic.enabled and locks:
            _debug.logic(
                "lock_dates_violated",
                company=self,
                accounting_date=accounting_date,
                locks=locks,
            )
        return locks

    @api.model
    def _format_lock_dates(self, lock_dates):
        field_labels = self.fields_get(
            {field for _date, field in lock_dates}, ["string"]
        )
        return format_list(
            self.env,
            [
                f"{field_labels[field]['string']} ({format_date(self.env, lock_date)})"
                for lock_date, field in sorted(lock_dates)
            ],
        )

    def _get_violated_lock_dates(self, accounting_date, has_tax, journal):
        locks = self._get_lock_date_violations(
            accounting_date,
            fiscalyear=True,
            sale=(journal and journal.type == "sale"),
            purchase=(journal and journal.type == "purchase"),
            tax=has_tax,
            hard=True,
        )
        locks.sort()
        return locks

    @_debug.perf.timed
    def write(self, vals):
        _debug.lifecycle("write", records=self, fields=sorted(vals))
        self._check_locks(vals)
        if _debug.lifecycle.enabled and vals.keys() & set(LOCK_DATE_FIELDS):
            _debug.lifecycle(
                "lock_dates",
                company=self,
                lock_changes={k: v for k, v in vals.items() if k in LOCK_DATE_FIELDS},
            )

        self.env["res.company"].invalidate_model(
            fnames=[f"user_{field}" for field in LOCK_DATE_FIELDS if field in vals]
        )

        for company in self:
            if bank_prefix := vals.get("bank_account_code_prefix"):
                company.reflect_code_prefix_change(
                    company.bank_account_code_prefix, bank_prefix
                )

            if cash_prefix := vals.get("cash_account_code_prefix"):
                company.reflect_code_prefix_change(
                    company.cash_account_code_prefix, cash_prefix
                )

            if "currency_id" in vals and vals["currency_id"] != company.currency_id.id:
                if company.root_id._existing_accounting():
                    raise UserError(
                        _(
                            "You cannot change the currency of the company since some journal items already exist"
                        )
                    )

        res = super().write(vals)

        self._set_category_defaults(vals)
        changed_soft_lock_fields = [
            field for field in SOFT_LOCK_DATE_FIELDS if field in vals
        ]
        if changed_soft_lock_fields:
            LockException = self.env["account.lock_exception"]
            domain = Domain.OR(
                LockException._get_domain_active_exceptions(
                    company, changed_soft_lock_fields
                )
                for company in self
            )
            exceptions = LockException.search(domain)
            _debug.logic(
                "recreating_exception",
                company=self,
                exceptions_count=len(exceptions),
                changed_soft_lock_fields=changed_soft_lock_fields,
            )
            exceptions._recreate()

        return res

    @api.model
    def setting_init_bank_account_action(self):
        view_id = self.env.ref("account.setup_bank_account_wizard").id
        context = {"dialog_size": "medium", **self.env.context}
        return {
            "type": "ir.actions.act_window",
            "name": _("Setup Bank Account"),
            "res_model": "account.setup.bank.manual.config",
            "target": "new",
            "view_mode": "form",
            "views": [[view_id, "form"]],
            "context": context,
        }

    @api.model
    def setting_init_credit_card_account_action(self):
        view_id = self.env.ref("account.setup_credit_card_account_wizard").id
        context = {"dialog_size": "medium", **self.env.context}
        return {
            "type": "ir.actions.act_window",
            "name": _("Setup Credit Card Account"),
            "res_model": "account.setup.bank.manual.config",
            "target": "new",
            "view_mode": "form",
            "views": [[view_id, "form"]],
            "context": context,
        }

    def _prepare_default_opening_move_values(self):
        self.check_singleton()
        default_journal = self.env["account.journal"].search(
            domain=[
                *self.env["account.journal"]._check_company_domain(self),
                ("type", "=", "general"),
            ],
            limit=1,
        )

        if not default_journal:
            raise UserError(
                _(
                    "Please install a chart of accounts or create a miscellaneous journal before proceeding."
                )
            )

        return {
            "ref": _("Opening Journal Entry"),
            "company_id": self.id,
            "journal_id": default_journal.id,
            "date": (
                self.account_opening_date
                or fields.Date.start_of(fields.Date.today(), "year")
            )
            - timedelta(days=1),
        }

    def opening_move_posted(self):
        return (
            bool(self.account_opening_move_id)
            and self.account_opening_move_id.state == "posted"
        )

    @_debug.perf.timed
    def get_unaffected_earnings_account(self):
        unaffected_earnings_type = "equity_unaffected"
        account = (
            self.env["account.account"]
            .with_company(self)
            .search(
                [
                    *self.env["account.account"]._check_company_domain(self),
                    ("account_type", "=", unaffected_earnings_type),
                ],
                limit=1,
            )
        )
        _debug.logic(
            "unaffected_earnings_resolved",
            company=self,
            account=account,
            found=bool(account),
        )
        if account:
            return account
        used_codes = set(
            self.env["account.account"]
            .with_company(self)
            .with_context(active_test=False)
            .search(
                [
                    *self.env["account.account"]._check_company_domain(self),
                    ("code", "=like", "9%"),
                ]
            )
            .mapped("code")
        )
        code = 999999
        while str(code) in used_codes:
            code -= 1
        _debug.logic(
            "unaffected_earnings_created",
            company=self,
            code=code,
            used_codes=len(used_codes),
        )
        return (
            self.env["account.account"]
            .with_company(self)
            ._load_records(
                [
                    {
                        "xml_id": f"account.{self.id!s}_unaffected_earnings_account",
                        "values": {
                            "code": str(code),
                            "name": _("Profit or Loss Appropriation"),
                            "account_type": unaffected_earnings_type,
                            "company_ids": [Command.link(self.id)],
                        },
                        "noupdate": True,
                    }
                ]
            )
        )

    @staticmethod
    def _plan_opening_move_lines(
        to_update,
        balancing_account,
        existing_lines,
        initial_balance,
        is_zero,
        amount_currency_of,
        currency_id_of,
        opening_name,
        balancing_name,
    ):
        commands = []
        open_balance = initial_balance

        def emit(account, side, balance, balancing):
            nonlocal open_balance
            lines = existing_lines.get((account, side)) or []
            amount_currency = (
                balance if balancing else amount_currency_of(account, balance)
            )
            open_balance += balance
            if is_zero(balance):
                for line in lines:
                    open_balance -= line.balance
                    commands.append(Command.delete(line.id))
            elif lines:
                line_to_update = lines[0]
                open_balance -= line_to_update.balance
                commands.append(
                    Command.update(
                        line_to_update.id,
                        {"balance": balance, "amount_currency": amount_currency},
                    )
                )
                for line in lines[1:]:
                    open_balance -= line.balance
                    commands.append(Command.delete(line.id))
            else:
                commands.append(
                    Command.create(
                        {
                            "name": balancing_name if balancing else opening_name,
                            "account_id": account.id,
                            "balance": balance,
                            "amount_currency": amount_currency,
                            "currency_id": currency_id_of(account),
                        }
                    )
                )

        for account, (debit, credit) in to_update.items():
            if debit is not None:
                emit(account, "debit", debit, False)
            if credit is not None:
                emit(account, "credit", -credit, False)
        _debug.pipeline(
            "opening_lines_planned",
            accounts=len(to_update),
            open_balance=open_balance,
            commands=len(commands),
        )
        emit(balancing_account, "debit", max(-open_balance, 0), True)
        emit(balancing_account, "credit", -max(open_balance, 0), True)
        _debug.pipeline(
            "opening_balancing_planned",
            balancing_account=balancing_account,
            open_balance=open_balance,
            commands=len(commands),
        )
        return commands

    @_debug.perf.timed
    def _update_opening_move(self, to_update):
        self.check_singleton()

        opening_move = self.account_opening_move_id
        if opening_move and opening_move.state != "draft":
            raise UserError(
                _(
                    'You cannot import the "opening_balance" if the opening move (%s) is already posted. '
                    "If you are absolutely sure you want to modify the opening balance of your accounts, "
                    "reset the move to draft.",
                    self.account_opening_move_id.name,
                )
            )

        AccountMoveLine = self.env["account.move.line"]
        existing_lines = opening_move.line_ids.grouped(
            lambda line: (
                line.account_id,
                "debit"
                if line.balance > 0.0 or line.amount_currency > 0.0
                else "credit",
            )
        )

        balancing_account = self.get_unaffected_earnings_account()
        initial_balance = sum(
            existing_lines.get((balancing_account, "credit"), AccountMoveLine).mapped(
                "credit"
            )
        ) - sum(
            existing_lines.get((balancing_account, "debit"), AccountMoveLine).mapped(
                "debit"
            )
        )

        _debug.pipeline(
            "opening_move_state",
            company=self,
            move=opening_move,
            existing_groups=len(existing_lines),
            balancing_account=balancing_account,
            initial_balance=initial_balance,
            to_update=len(to_update),
        )
        move_values = {}
        if opening_move:
            conversion_date = opening_move.date
        else:
            move_values.update(self._prepare_default_opening_move_values())
            conversion_date = move_values["date"]

        company_currency = self.currency_id
        commands = self._plan_opening_move_lines(
            to_update=to_update,
            balancing_account=balancing_account,
            existing_lines=existing_lines,
            initial_balance=initial_balance,
            is_zero=company_currency.is_zero,
            amount_currency_of=lambda account, balance: company_currency._convert(
                balance, account.currency_id or company_currency, date=conversion_date
            ),
            currency_id_of=lambda account: (account.currency_id or company_currency).id,
            opening_name=_("Opening balance"),
            balancing_name=_("Automatic Balancing Line"),
        )

        _debug.logic(
            "opening_move_decided",
            company=self,
            move=opening_move,
            commands=len(commands),
            action="noop" if not commands else ("write" if opening_move else "create"),
        )
        if not commands:
            return

        move_values["line_ids"] = commands
        if opening_move:
            opening_move.write(move_values)
        else:
            self.account_opening_move_id = self.env["account.move"].create(move_values)

    @_debug.perf.timed
    def action_save_onboarding_sale_tax(self):
        _debug.lifecycle("action_save_onboarding_sale_tax", records=self)
        self.env["onboarding.onboarding.step"].action_validate_step(
            "account.onboarding_onboarding_step_sales_tax"
        )

    @_debug.perf.timed
    def action_save_onboarding_company_data(self):
        _debug.lifecycle("action_save_onboarding_company_data", records=self)
        self.check_singleton()
        if self.street:
            ref = "account.onboarding_onboarding_step_company_data"
            self.env["onboarding.onboarding.step"].with_company(
                self
            ).action_validate_step(ref)
        return {"type": "ir.actions.client", "tag": "soft_reload"}

    def install_l10n_modules(self):
        if self.env.context.get("chart_template_load"):
            return False
        if res := super().install_l10n_modules():
            env = self.env
            env.flush_all()
            env.transaction.reset()
            for company in self.filtered(
                lambda c: c.country_id and not c.chart_template
            ):
                template_code = company.parent_id.chart_template or self.env[
                    "account.chart.template"
                ]._guess_chart_template(company.country_id)
                _debug.logic(
                    "install_l10n_modules_guessed_template_country",
                    company=company,
                    template_code=template_code,
                    code=company.country_id.code,
                )
                if template_code != "generic_coa":

                    @self.env.cr.precommit.add
                    def try_loading(template_code=template_code, company=company):
                        env["account.chart.template"].try_loading(
                            template_code,
                            env["res.company"].browse(company.id),
                        )

        return res

    def _existing_accounting(self) -> bool:
        self.check_singleton()
        return bool(
            self.env["account.move.line"]
            .sudo()
            .search_count([("company_id", "child_of", self.id)], limit=1)
        )

    def _selection_chart_templates(self):
        return self.env["account.chart.template"]._select_chart_template(
            self.country_id
        )

    @api.model
    @_debug.perf.timed
    def _action_check_hash_integrity(self):
        _debug.lifecycle("_action_check_hash_integrity", records=self)
        return self.env.ref(
            "account.action_report_account_hash_integrity"
        ).report_action(self.id)

    @_debug.perf.timed
    def _check_hash_integrity(self):
        if not self.env.user.has_group("account.group_account_user"):
            raise UserError(
                _("Please contact your accountant to print the Hash integrity result.")
            )

        journals = self.env["account.journal"].search(
            self.env["account.journal"]._check_company_domain(self)
        )
        results = []
        for journal in journals:
            results.extend(self._check_journal_hash_integrity(journal))
        return {
            "results": results,
            "printing_date": format_date(self.env, fields.Date.context_today(self)),
        }

    @_debug.perf.timed
    def _check_journal_hash_integrity(self, journal):
        restricted_flag = "V" if journal.restrict_mode_hash_table else "X"
        query = (
            self.env["account.move"]
            .sudo()
            ._search(
                domain=[
                    ("journal_id", "=", journal.id),
                    ("inalterable_hash", "!=", False),
                ],
                order="secure_sequence_number ASC NULLS LAST, sequence_prefix, sequence_number ASC",
            )
        )
        prefix2result = defaultdict(
            lambda: {
                "first_move": self.env["account.move"],
                "last_move": self.env["account.move"],
                "corrupted_move": self.env["account.move"],
            }
        )
        last_move = self.env["account.move"]
        any_hashed_move = False
        hashed_rows = 0  # debuglog
        hashed_batches = 0  # debuglog
        self.env.execute_query(
            SQL("DECLARE hashed_moves CURSOR FOR %s", query.select())
        )
        try:
            while move_ids := self.env.execute_query(
                SQL("FETCH %s FROM hashed_moves", SQL(str(INTEGRITY_HASH_BATCH_SIZE)))
            ):
                hashed_rows += len(move_ids)  # debuglog
                hashed_batches += 1  # debuglog
                self.env.invalidate_all()
                moves = self.env["account.move"].browse(
                    move_id[0] for move_id in move_ids
                )
                any_hashed_move = True

                hash_version = 1
                for move in moves:
                    prefix_result = prefix2result[move.sequence_prefix]
                    if prefix_result["corrupted_move"]:
                        continue
                    previous_move = (
                        prefix_result["last_move"]
                        if not move.secure_sequence_number
                        else last_move
                    )
                    computed_hash, hash_version = self._recompute_move_hash(
                        move, previous_move.inalterable_hash or "", hash_version
                    )
                    if move.inalterable_hash != computed_hash:
                        _debug.logic(
                            "hash_integrity_corrupted_prefix_version",
                            journal=journal,
                            move=move,
                            sequence_prefix=move.sequence_prefix,
                            hash_version=hash_version,
                        )
                        prefix_result["corrupted_move"] = move
                        continue
                    if not prefix_result["first_move"]:
                        prefix_result["first_move"] = move
                    prefix_result["last_move"] = move
                    last_move = move
        finally:
            self.env.execute_query(SQL("CLOSE hashed_moves"))
        _debug.perf.count(
            "hashed_moves_fetched",
            journal=journal,
            rows=hashed_rows,
            batches=hashed_batches,
        )

        if _debug.pipeline.enabled:
            _debug.pipeline(
                "hash_integrity",
                journal=journal,
                hashed=any_hashed_move,
                prefixes={
                    p: (r["first_move"].id, r["last_move"].id, r["corrupted_move"].id)
                    for p, r in prefix2result.items()
                },
            )
        if not any_hashed_move:
            return [self._hash_integrity_no_data_result(journal, restricted_flag)]
        return [
            self._hash_integrity_prefix_result(
                journal, restricted_flag, prefix, prefix_result
            )
            for prefix, prefix_result in prefix2result.items()
        ]

    @staticmethod
    def _recompute_move_hash(move, previous_hash, start_version):
        version = start_version
        computed_hash = move.with_context(hash_version=version)._get_hashes(
            previous_hash
        )[move]
        while move.inalterable_hash != computed_hash and version < MAX_HASH_VERSION:
            version += 1
            computed_hash = move.with_context(hash_version=version)._get_hashes(
                previous_hash
            )[move]
        return computed_hash, version

    def _hash_integrity_no_data_result(self, journal, restricted_flag):
        return {
            "journal_name": journal.name,
            "restricted_by_hash_table": restricted_flag,
            "status": "no_data",
            "msg_cover": _(
                "There is no journal entry flagged for accounting data inalterability yet."
            ),
        }

    def _hash_integrity_prefix_result(
        self, journal, restricted_flag, prefix, prefix_result
    ):
        journal_name = f"{journal.name} ({prefix}...)"
        if corrupted_move := prefix_result["corrupted_move"]:
            return {
                "restricted_by_hash_table": restricted_flag,
                "journal_name": journal_name,
                "status": "corrupted",
                "msg_cover": _(
                    "Corrupted data on journal entry with id %(id)s (%(name)s).",
                    id=corrupted_move.id,
                    name=corrupted_move.name,
                ),
            }
        first_move = prefix_result["first_move"]
        last_move = prefix_result["last_move"]
        return {
            "restricted_by_hash_table": restricted_flag,
            "journal_name": journal_name,
            "status": "verified",
            "msg_cover": _("Entries are correctly hashed"),
            "first_move_name": first_move.name,
            "first_hash": first_move.inalterable_hash,
            "first_move_date": format_date(self.env, first_move.date),
            "last_move_name": last_move.name,
            "last_hash": last_move.inalterable_hash,
            "last_move_date": format_date(self.env, last_move.date),
        }

    @api.model
    def _with_locked_records(self, records, allow_raising=True):
        try:
            records.lock_for_update()
        except LockError as err:
            if not allow_raising:
                return False
            raise UserError(
                _("Some documents are being sent by another process already.")
            ) from err
        return True

    def compute_fiscalyear_dates(self, current_date):
        self.check_singleton()
        date_from, date_to = date_utils.get_fiscal_year(
            current_date,
            day=self.fiscalyear_last_day,
            month=int(self.fiscalyear_last_month),
        )
        return {"date_from": date_from, "date_to": date_to}

    @api.depends("country_id", "account_fiscal_country_id")
    def _compute_company_vat_placeholder(self):
        Partner = self.env["res.partner"]
        for company in self:
            country = company.country_id or company.account_fiscal_country_id
            expected_vat = Partner._get_expected_vat_format(country.code)
            company.company_vat_placeholder = (
                _("%s, or / if not applicable", expected_vat)
                if expected_vat
                else _("/ if not applicable")
            )

    def _set_category_defaults(self, changed_fields=None):
        IrDefault = self.env["ir.default"].sudo()
        if _debug.logic.enabled:
            _debug.logic(
                "category_defaults_scope",
                companies=self,
                all_fields=changed_fields is None,
                expense="expense_account_id" in (changed_fields or ()),
                income="income_account_id" in (changed_fields or ()),
            )
        for company in self:
            if changed_fields is None or "expense_account_id" in changed_fields:
                IrDefault.set(
                    "product.category",
                    "property_account_expense_categ_id",
                    company.expense_account_id.id,
                    company_id=company.id,
                )
            if changed_fields is None or "income_account_id" in changed_fields:
                IrDefault.set(
                    "product.category",
                    "property_account_income_categ_id",
                    company.income_account_id.id,
                    company_id=company.id,
                )

    def _check_tax_return_configuration(self):
        return
