import re
from collections import defaultdict
from functools import cache
from typing import NamedTuple
from urllib.parse import urlencode

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.libs.web import urls
from odoo.tools import email_normalize, email_normalize_all, groupby, is_encodable
from odoo.tools.misc import hash_sign
from odoo.tools.translate import LazyTranslate

from odoo.addons.account.tools.display_types import NON_ACCOUNTABLE_DISPLAY_TYPES
from odoo.addons.base.models.mixin_catalog import name_uniq_index

_debug = DebugLog(__name__)

_lt = LazyTranslate(__name__)

ANY_ACCOUNT_TYPES = (
    "asset_receivable",
    "asset_cash",
    "asset_current",
    "asset_non_current",
    "asset_prepayments",
    "asset_fixed",
    "liability_payable",
    "liability_credit_card",
    "liability_current",
    "liability_non_current",
    "equity",
    "equity_unaffected",
    "income",
    "income_other",
    "expense",
    "expense_depreciation",
    "expense_direct_cost",
    "off_balance",
)

JOURNAL_TYPES = {
    "sale": {
        "code_prefix": "INV",
        "account_types": ("income", "income_other"),
        "alias_move_type": "out_invoice",
        "family": "document",
        "label": _lt("Customer Invoices"),
    },
    "purchase": {
        "code_prefix": "BILL",
        "account_types": ("expense", "expense_depreciation", "expense_direct_cost"),
        "alias_move_type": "in_invoice",
        "family": "document",
        "label": _lt("Vendor Bills"),
    },
    "cash": {
        "code_prefix": "CSH",
        "account_types": ("asset_cash",),
        "family": "liquidity",
        "cash_difference": True,
        "label": _lt("Cash"),
    },
    "bank": {
        "code_prefix": "BNK",
        "account_types": ("asset_cash", "liability_credit_card"),
        "family": "liquidity",
        "cash_difference": True,
        "label": _lt("Bank"),
    },
    "credit": {
        "code_prefix": "CCD",
        "account_types": ("liability_credit_card",),
        "family": "liquidity",
        "label": _lt("Credit Card"),
    },
    "general": {
        "code_prefix": "MISC",
        "account_types": ANY_ACCOUNT_TYPES,
        "family": "general",
        "label": _lt("Miscellaneous Operations"),
    },
}


@cache
def _generated_code_pattern(prefixes):
    return re.compile(rf"({'|'.join(re.escape(prefix) for prefix in prefixes)})\d*")


def _types_where(**criteria):
    return tuple(
        journal_type
        for journal_type, spec in JOURNAL_TYPES.items()
        if all(spec.get(key) == value for key, value in criteria.items())
    )


class JournalBatchReservations(NamedTuple):
    codes: dict
    alias_names: dict
    companies_read: set


class JournalPaymentMethods(NamedTuple):
    pay_methods: models.BaseModel
    manage_providers: bool
    method_information_mapping: dict
    providers_per_code: dict


LIQUIDITY_TYPES = _types_where(family="liquidity")
DOCUMENT_TYPES = _types_where(family="document")
CASH_DIFFERENCE_TYPES = _types_where(cash_difference=True)


class AccountJournalGroup(models.Model):
    _name = "account.journal.group"
    _description = "Account Journal Group"
    _order = "sequence"
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of

    name = fields.Char(
        string="Ledger group",
        translate=True,
        required=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        help="Define which company can select the multi-ledger in report filters. If none is provided, available for all companies",
    )
    excluded_journal_ids = fields.Many2many(
        comodel_name="account.journal",
        string="Excluded Journals",
        domain='company_id and [("company_id", "parent_of", company_id)] or []',
        context={"active_test": False},
    )
    sequence = fields.Integer(default=10)

    _name_src_uniq = name_uniq_index(
        "company_id",
        nulls_distinct=True,
        message="A Ledger group name must be unique per company.",
    )


class AccountJournal(models.Model):
    _name = "account.journal"
    _description = "Journal"
    _order = "sequence, type, code"
    _inherit = [
        "mixin.portal",
        "mixin.mail.alias.optional",
        "mixin.mail.thread",
        "mixin.mail.activity",
    ]
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of
    _rec_names_search = ["name", "code"]

    def _default_display_invoice_template_pdf_report_id(self):
        reports = self.env[
            "account.move"
        ]._get_available_invoice_template_pdf_report_ids()
        return len(reports) > 1

    def _default_inbound_payment_methods(self):
        return self.env.ref("account.account_payment_method_manual_in")

    def _default_outbound_payment_methods(self):
        return self.env.ref("account.account_payment_method_manual_out")

    def _selection_bank_statements_source(self):
        return [("undefined", _("Undefined Yet"))]

    def _default_invoice_reference_model(self):
        country_code = self.env.company.country_id.code
        country_code = country_code and country_code.lower()
        if country_code:
            for model in self._fields["invoice_reference_model"].get_values(self.env):
                if model.startswith(country_code):
                    return model
        return "odoo"

    def _domain_default_account_id(self):
        branches = "".join(
            f"{spec['account_types']!r} if type == {journal_type!r} else "
            for journal_type, spec in JOURNAL_TYPES.items()
            if journal_type != "general"
        )
        return f"[('account_type', 'in', {branches}{ANY_ACCOUNT_TYPES!r})]"

    name = fields.Char(
        string="Journal Name",
        translate=True,
        required=True,
    )
    name_placeholder = fields.Char(compute="_compute_name_placeholder")
    code = fields.Char(
        string="Sequence Prefix",
        size=5,
        compute="_compute_code",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
        help="Shorter name used for display. "
        "The journal entries of this journal will also be named using this prefix by default.",
    )
    active = fields.Boolean(
        default=True,
        help="Set active to false to hide the Journal without removing it.",
    )
    type = fields.Selection(
        selection=[
            ("sale", "Sales"),
            ("purchase", "Purchase"),
            ("cash", "Cash"),
            ("bank", "Bank"),
            ("credit", "Credit Card"),
            ("general", "Miscellaneous"),
        ],
        required=True,
        help="""
        Select 'Sale' for customer invoices journals.
        Select 'Purchase' for vendor bills journals.
        Select 'Cash', 'Bank' or 'Credit Card' for journals that are used in customer or vendor payments.
        Select 'General' for miscellaneous operations journals.
        """,
    )
    is_self_billing = fields.Boolean(
        string="Self Billing",
        help="This journal is for self-billing invoices. "
        "Invoices will be created using a different sequence per partner.",
    )
    default_account_id = fields.Many2one(
        comodel_name="account.account",
        copy=False,
        domain=_domain_default_account_id,
        ondelete="restrict",
        check_company=True,
    )
    suspense_account_id = fields.Many2one(
        comodel_name="account.account",
        compute="_compute_suspense_account_id",
        store=True,
        readonly=False,
        domain="[('account_type', '=', 'asset_current')]",
        ondelete="restrict",
        check_company=True,
        help="Bank statements transactions will be posted on the suspense account until the final reconciliation "
        "allowing finding the right account.",
    )
    non_deductible_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Private Share Account",
        store=True,
        readonly=False,
        check_company=True,
        help="Account used to register the private part of mixed expenses.",
    )
    restrict_mode_hash_table = fields.Boolean(
        string="Secure Posted Entries with Hash",
        help="If ticked, when an entry is posted, we retroactively hash all moves in the sequence from the entry back to the last hashed entry. The hash can also be performed on demand by the Secure Entries wizard.",
    )
    sequence = fields.Integer(
        default=10,
        help="Used to order Journals in the dashboard view",
    )

    invoice_reference_type = fields.Selection(
        selection=[("partner", "Based on Customer"), ("invoice", "Based on Invoice")],
        string="Communication Type",
        default="invoice",
        required=True,
        help="You can set here the default communication that will appear on customer invoices, once validated, to help the customer to refer to that particular invoice when making the payment.",
    )
    invoice_reference_model = fields.Selection(
        selection=[
            ("odoo", "Full Reference (INV/2024/00001)"),
            ("euro", "European (RF83INV202400001)"),
            ("number", "Numbers only (202400001)"),
        ],
        string="Communication Standard",
        default=_default_invoice_reference_model,
        required=True,
        help="You can choose different models for each type of reference. The default one is the Odoo reference.",
    )

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        help="The currency used to enter statement",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        index=True,
        readonly=True,
        required=True,
        help="Company related to this journal",
    )
    country_code = fields.Char(
        related="company_id.account_config_id.account_fiscal_country_id.code",
        readonly=True,
    )
    account_fiscal_country_group_codes = fields.Json(
        related="company_id.account_config_id.account_fiscal_country_group_codes"
    )

    refund_sequence = fields.Boolean(
        string="Dedicated Credit Note Sequence",
        compute="_compute_refund_sequence",
        store=True,
        readonly=False,
        help="Check this box if you don't want to share the same sequence for invoices and credit notes made from this journal",
    )
    payment_sequence = fields.Boolean(
        string="Dedicated Payment Sequence",
        compute="_compute_payment_sequence",
        precompute=True,
        store=True,
        readonly=False,
        help="Check this box if you don't want to share the same sequence on payments and bank transactions posted on this journal",
    )
    invoice_template_pdf_report_id = fields.Many2one(
        comodel_name="ir.actions.report",
        string="Invoice report",
        readonly=False,
        domain="[('id', 'in', available_invoice_template_pdf_report_ids)]",
    )
    available_invoice_template_pdf_report_ids = fields.One2many(
        comodel_name="ir.actions.report",
        compute="_compute_available_invoice_template_pdf_report_ids",
    )
    display_invoice_template_pdf_report_id = fields.Boolean(
        default=_default_display_invoice_template_pdf_report_id,
        store=False,
    )
    sequence_override_regex = fields.Text(
        help="Technical field used to enforce complex sequence composition that the system would normally misunderstand.\n"
        "This is a regex that can include all the following capture groups: prefix1, year, prefix2, month, prefix3, seq, suffix.\n"
        "The prefix* groups are the separators between the year, month and the actual increasing sequence number (seq).\n"
        r"e.g: ^(?P<prefix1>.*?)(?P<year>\d{4})(?P<prefix2>\D*?)(?P<month>\d{2})(?P<prefix3>\D+?)(?P<seq>\d+)(?P<suffix>\D*?)$"
    )

    inbound_payment_channel_ids = fields.One2many(
        comodel_name="account.payment.channel",
        inverse_name="journal_id",
        string="Inbound Payment Methods",
        compute="_compute_inbound_payment_channel_ids",
        store=True,
        copy=False,
        readonly=False,
        domain=[("payment_type", "=", "inbound")],
        check_company=True,
        help="Manual: Get paid by any method outside of Odoo.\n"
        "Payment Providers: Each payment provider has its own Payment Method. Request a transaction on/to a card thanks to a payment token saved by the partner when buying or subscribing online.\n"
        "Batch Deposit: Collect several customer checks at once generating and submitting a batch deposit to your bank. Module account_batch_payment is necessary.\n"
        "SEPA Direct Debit: Get paid in the SEPA zone thanks to a mandate your partner will have granted to you. Module account_sepa is necessary.\n",
    )
    outbound_payment_channel_ids = fields.One2many(
        comodel_name="account.payment.channel",
        inverse_name="journal_id",
        string="Outbound Payment Methods",
        compute="_compute_outbound_payment_channel_ids",
        store=True,
        copy=False,
        readonly=False,
        domain=[("payment_type", "=", "outbound")],
        check_company=True,
        help="Manual: Pay by any method outside of Odoo.\n"
        "Check: Pay bills by check and print it from Odoo.\n"
        "SEPA Credit Transfer: Pay in the SEPA zone by submitting a SEPA Credit Transfer file to your bank. Module account_sepa is necessary.\n",
    )
    profit_account_id = fields.Many2one(
        comodel_name="account.account",
        domain="[('account_type', 'in', ('income', 'income_other'))]",
        check_company=True,
        help="Used to register a profit when the ending balance of a cash register differs from what the system computes",
    )
    loss_account_id = fields.Many2one(
        comodel_name="account.account",
        domain="[('account_type', '=', 'expense')]",
        check_company=True,
        help="Used to register a loss when the ending balance of a cash register differs from what the system computes",
    )

    company_partner_id = fields.Many2one(
        comodel_name="res.partner",
        related="company_id.partner_id",
        string="Account Holder",
        store=False,
        readonly=True,
    )
    bank_account_id = fields.Many2one(
        comodel_name="res.partner.bank",
        index="btree_not_null",
        copy=False,
        domain="[('partner_id','=', company_partner_id)]",
        ondelete="restrict",
        check_company=True,
    )
    bank_statements_source = fields.Selection(
        selection="_selection_bank_statements_source",
        string="Bank Feeds",
        default="undefined",
        help="Defines how the bank statements will be registered",
    )
    bank_acc_number = fields.Char(
        related="bank_account_id.acc_number",
        readonly=False,
    )
    bank_id = fields.Many2one(
        comodel_name="res.bank",
        related="bank_account_id.bank_id",
        readonly=False,
    )

    alias_name = fields.Char(
        help="Send one separate email for each invoice.\n"
        "Any file extension will be accepted.\n"
        "Only PDF and XML files will be interpreted by Odoo"
    )

    journal_group_ids = fields.Many2many(
        comodel_name="account.journal.group",
        string="Ledger Group",
        check_company=True,
    )

    available_payment_method_ids = fields.Many2many(
        comodel_name="account.payment.method",
        compute="_compute_available_payment_method_ids",
    )

    selected_payment_method_codes = fields.Char(
        compute="_compute_selected_payment_method_codes"
    )
    accounting_date = fields.Date(compute="_compute_accounting_date")
    display_alias_fields = fields.Boolean(compute="_compute_display_alias_fields")
    bank_statement_ids = fields.One2many(
        comodel_name="account.bank.statement",
        inverse_name="journal_id",
    )
    has_invalid_statements = fields.Boolean(compute="_compute_has_invalid_statements")

    show_fetch_in_einvoices_button = fields.Boolean(
        string="Show E-Invoice Buttons",
        compute="_compute_show_fetch_in_einvoices_button",
    )
    show_refresh_out_einvoices_status_button = fields.Boolean(
        string="Show E-Invoice Status Buttons",
        compute="_compute_show_refresh_out_einvoices_status_button",
    )

    incoming_einvoice_notification_email = fields.Char(
        string="Send Copy To",
        help="Email addresses that will receive copy for sent and received invoices. Separate entries with ';'.",
    )

    allowed_account_ids = fields.Many2many(
        comodel_name="account.account",
        relation="account_journal_allowed_account_rel",
        column1="journal_id",
        column2="account_id",
        string="Allowed Accounts",
        domain=[("account_type", "!=", "off_balance")],
        check_company=True,
        help="Accounts a journal item in this journal may use. Leave empty to allow "
        "any account. The journal's own accounts are always usable and need not be "
        "listed.",
    )
    structural_account_ids = fields.Many2many(
        comodel_name="account.account",
        string="Structural Accounts",
        compute="_compute_structural_account_ids",
        help="Accounts this journal designates itself. A list of allowed accounts that "
        "omits them would make the journal unusable rather than controlled, so they "
        "are always permitted.",
    )
    allowed_user_ids = fields.Many2many(
        comodel_name="res.users",
        relation="account_journal_allowed_user_rel",
        column1="journal_id",
        column2="user_id",
        string="Allowed Users",
        copy=False,
        help="Users allowed to use this journal on a journal entry. Leave empty to "
        "let everyone use it. This does not hide existing entries -- reading them is "
        "governed by record rules.",
    )

    _code_company_uniq = models.Constraint(
        "unique (company_id, code)",
        "Journal codes must be unique per company.",
    )

    @api.depends("bank_statement_ids.is_valid", "bank_statement_ids.is_complete")
    def _compute_has_invalid_statements(self):
        journals_with_invalid_statements = (
            self.env["account.bank.statement"]
            .search(
                [
                    ("journal_id", "in", self.ids),
                    "|",
                    ("is_valid", "=", False),
                    ("is_complete", "=", False),
                ]
            )
            .journal_id
        )
        journals_with_invalid_statements.has_invalid_statements = True
        (self - journals_with_invalid_statements).has_invalid_statements = False

    def _compute_display_alias_fields(self):
        self.display_alias_fields = bool(
            self.env["mail.alias.domain"].search_count([], limit=1)
        )

    @api.depends("type", "company_id")
    def _compute_code(self):
        used_by_company = {}
        for record in self:
            if record.code or not record.type:
                continue
            company = record.company_id
            used = used_by_company.get(company.id)
            if used is None:
                used = used_by_company[company.id] = self._get_company_journal_codes(
                    company
                )
            record.code = self._get_next_journal_default_code(
                record.type, company, used_codes=used
            )
            used.add(record.code)

    def _get_journals_payment_method_information(self):
        method_information = self.env[
            "account.payment.method"
        ]._get_payment_method_information()
        pay_methods = (
            self.env["account.payment.method"]
            .sudo()
            .search([("code", "in", list(method_information.keys()))])
        )
        manage_providers = (
            "payment_provider_id" in self.env["account.payment.channel"]._fields
        )

        mapping, unique_ids, electronic_names = self._map_payment_methods(
            pay_methods, method_information, manage_providers
        )
        self._update_company_journals(mapping, unique_ids, manage_providers)
        return JournalPaymentMethods(
            pay_methods=pay_methods,
            manage_providers=manage_providers,
            method_information_mapping=mapping,
            providers_per_code=self._get_providers_per_code(electronic_names)
            if manage_providers
            else {},
        )

    @api.model
    def _map_payment_methods(self, pay_methods, method_information, manage_providers):
        mapping = {}
        unique_ids = set()
        electronic_names = set()
        for pay_method in pay_methods:
            values = mapping[pay_method.id] = {
                **method_information[pay_method.code],
                "payment_method": pay_method,
                "company_journals": {},
            }
            if values["mode"] == "unique":
                unique_ids.add(pay_method.id)
            elif manage_providers and values["mode"] == "electronic":
                unique_ids.add(pay_method.id)
                electronic_names.add(pay_method.code)
        _debug.logic(
            "payment_methods_mapped",
            methods=len(mapping),
            unique=len(unique_ids),
            electronic=len(electronic_names),
            manage_providers=manage_providers,
        )
        return mapping, unique_ids, electronic_names

    def _get_providers_per_code(self, electronic_names):
        providers_per_code = {}
        providers = (
            self.env["payment.provider"]
            .sudo()
            .search(
                [
                    *self.env["payment.provider"]._check_company_domain(
                        self.company_id
                    ),
                    ("code", "in", tuple(electronic_names)),
                ]
            )
        )
        for provider in providers:
            providers_per_code.setdefault(provider.company_id.id, {}).setdefault(
                provider._get_code(), set()
            ).add(provider.id)
        return providers_per_code

    @_debug.perf.timed
    def _update_company_journals(self, mapping, unique_ids, manage_providers):
        if _debug.logic.enabled and (not unique_ids or not self.company_id):
            _debug.logic(
                "company_journals_skipped",
                methods=len(unique_ids or ()),
                companies=self.company_id,
            )
        if not unique_ids or not self.company_id:
            return
        _debug.pipeline(
            "company_journals_query",
            methods=len(unique_ids),
            manage_providers=manage_providers,
            journals=self,
        )
        fnames = ["payment_method_id", "journal_id"]
        if manage_providers:
            fnames.append("payment_provider_id")
        self.env["account.payment.channel"].flush_model(fnames=fnames)

        self.env.cr.execute(
            f"""
                SELECT
                    apm.id,
                    journal.company_id,
                    journal.id,
                    {"apml.payment_provider_id" if manage_providers else "NULL"}
                FROM account_payment_channel apml
                JOIN account_journal journal ON journal.id = apml.journal_id
                JOIN account_payment_method apm ON apm.id = apml.payment_method_id
                WHERE apm.id = ANY(%s)
                  AND journal.company_id = ANY(%s)
            """,
            [list(unique_ids), self.company_id.ids],
        )
        for (
            pay_method_id,
            company_id,
            journal_id,
            provider_id,
        ) in self.env.cr.fetchall():
            values = mapping[pay_method_id]
            company_journals = values["company_journals"]
            if manage_providers and values["mode"] == "electronic":
                journal_ids = company_journals.setdefault(company_id, {}).setdefault(
                    provider_id, []
                )
            else:
                journal_ids = company_journals.setdefault(company_id, [])
            journal_ids.append(journal_id)
        _debug.perf.count("payment_channels_fetched", rows=self.env.cr.rowcount)

    @api.depends("outbound_payment_channel_ids", "inbound_payment_channel_ids")
    @_debug.perf.timed
    def _compute_available_payment_method_ids(self):
        info = self._get_journals_payment_method_information()
        pay_methods = info.pay_methods
        manage_providers = info.manage_providers
        method_information_mapping = info.method_information_mapping
        providers_per_code = info.providers_per_code

        journal_bank_cash = self.filtered(lambda j: j.type in LIQUIDITY_TYPES)
        journal_other = self - journal_bank_cash
        _debug.pipeline(
            "available_methods_split",
            liquidity=journal_bank_cash,
            other=journal_other,
            methods=len(pay_methods),
            manage_providers=manage_providers,
        )
        journal_other.available_payment_method_ids = False

        for journal in journal_bank_cash:
            commands = [Command.clear()]
            company = journal.company_id

            protected_provider_ids = set()
            protected_payment_method_ids = set()
            for payment_type in ("inbound", "outbound"):
                lines = journal[f"{payment_type}_payment_channel_ids"]
                for line in lines:
                    values = method_information_mapping.get(line.payment_method_id.id)
                    if not values:
                        continue
                    protected_payment_method_ids.add(line.payment_method_id.id)
                    if manage_providers and values["mode"] == "electronic":
                        protected_provider_ids.add(line.payment_provider_id.id)

            for pay_method in pay_methods:
                if not journal._is_payment_method_available(
                    pay_method.code, complete_domain=False
                ):
                    continue

                values = method_information_mapping[pay_method.id]

                if values["mode"] == "unique":
                    already_linked_journal_ids = set(
                        values["company_journals"].get(company.id, [])
                    ) - {journal._origin.id}
                    if (
                        not already_linked_journal_ids
                        and pay_method.id not in protected_payment_method_ids
                    ):
                        commands.append(Command.link(pay_method.id))
                elif manage_providers and values["mode"] == "electronic":
                    for provider_id in providers_per_code.get(company.id, {}).get(
                        pay_method.code, set()
                    ):
                        already_linked_journal_ids = set(
                            values["company_journals"]
                            .get(company.id, {})
                            .get(provider_id, [])
                        ) - {journal._origin.id}
                        if (
                            not already_linked_journal_ids
                            and provider_id not in protected_provider_ids
                        ):
                            commands.append(Command.link(pay_method.id))
                elif values["mode"] == "multi":
                    commands.append(Command.link(pay_method.id))

            _debug.logic(
                "available_methods_resolved",
                journal=journal,
                company=company,
                linked=len(commands) - 1,
                protected_methods=len(protected_payment_method_ids),
                protected_providers=len(protected_provider_ids),
            )
            journal.available_payment_method_ids = commands

    @api.depends("type", "currency_id")
    def _compute_inbound_payment_channel_ids(self):
        self._compute_payment_channel_ids("inbound")

    @api.depends("type", "currency_id")
    def _compute_outbound_payment_channel_ids(self):
        self._compute_payment_channel_ids("outbound")

    @_debug.perf.timed
    def _compute_payment_channel_ids(self, payment_type):
        field_name = f"{payment_type}_payment_channel_ids"
        for journal in self:
            commands = [Command.clear()]
            if journal.type in LIQUIDITY_TYPES:
                existing_method_lines = journal[field_name]
                default_methods = getattr(
                    journal, f"_default_{payment_type}_payment_methods"
                )()
                for pay_method in default_methods:
                    payment_account = existing_method_lines.filtered(
                        lambda m, pay_method=pay_method: (
                            m.payment_method_id == pay_method
                        )
                    )[:1].payment_account_id
                    commands.append(
                        Command.create(
                            {
                                "name": pay_method.name,
                                "payment_method_id": pay_method.id,
                                "payment_account_id": (
                                    payment_account.id
                                    if not payment_account.currency_id
                                    or payment_account.currency_id
                                    == journal.currency_id
                                    else False
                                ),
                            }
                        )
                    )
            _debug.logic(
                "default_channels_built",
                journal=journal,
                payment_type=payment_type,
                created=len(commands) - 1,
            )
            journal[field_name] = commands

    @api.depends("outbound_payment_channel_ids", "inbound_payment_channel_ids")
    def _compute_selected_payment_method_codes(self):
        for journal in self:
            codes = [
                line.code
                for line in journal.inbound_payment_channel_ids
                + journal.outbound_payment_channel_ids
                if line.code
            ]
            journal.selected_payment_method_codes = "," + ",".join(codes) + ","

    @api.depends("company_id", "type")
    def _compute_suspense_account_id(self):
        for journal in self:
            if journal.type not in LIQUIDITY_TYPES:
                journal.suspense_account_id = False
            elif not journal.suspense_account_id:
                journal.suspense_account_id = (
                    journal.company_id.account_config_id.account_journal_suspense_account_id
                    or False
                )

    @api.depends(
        "type",
        "company_id.account_config_id.fiscalyear_lock_date",
        "company_id.account_config_id.tax_lock_date",
        "company_id.account_config_id.sale_lock_date",
        "company_id.account_config_id.purchase_lock_date",
        "company_id.account_config_id.hard_lock_date",
    )
    @api.depends_context("move_date", "has_tax")
    def _compute_accounting_date(self):
        move_date = self.env.context.get("move_date") or fields.Date.context_today(self)
        has_tax = self.env.context.get("has_tax") or False
        for journal in self:
            temp_move = self.env["account.move"].new({"journal_id": journal.id})
            journal.accounting_date = temp_move._get_accounting_date(move_date, has_tax)

    @api.depends("type")
    def _compute_show_fetch_in_einvoices_button(self):
        self.show_fetch_in_einvoices_button = False

    @api.depends("type")
    def _compute_show_refresh_out_einvoices_status_button(self):
        self.show_refresh_out_einvoices_status_button = False

    @api.model
    def _is_generated_code(self, code):
        if not code:
            return True
        prefixes = tuple(spec["code_prefix"] for spec in JOURNAL_TYPES.values())
        return bool(_generated_code_pattern(prefixes).fullmatch(code))

    @api.model
    def _prepare_type_defaults(self, journal_type, company):
        defaults = {
            "default_account_id": False,
            "profit_account_id": False,
            "loss_account_id": False,
        }
        if (
            journal_type == "sale"
            and company.account_config_id.income_account_id.active
        ):
            defaults["default_account_id"] = (
                company.account_config_id.income_account_id.id
            )
        elif (
            journal_type == "purchase"
            and company.account_config_id.expense_account_id.active
        ):
            defaults["default_account_id"] = (
                company.account_config_id.expense_account_id.id
            )
        elif journal_type in CASH_DIFFERENCE_TYPES:
            if company.account_config_id.default_cash_difference_income_account_id.active:
                defaults["profit_account_id"] = (
                    company.account_config_id.default_cash_difference_income_account_id.id
                )
            if company.account_config_id.default_cash_difference_expense_account_id.active:
                defaults["loss_account_id"] = (
                    company.account_config_id.default_cash_difference_expense_account_id.id
                )
        _debug.logic(
            "type_defaults_resolved",
            type=journal_type,
            company=company,
            default_account=defaults["default_account_id"],
            profit_account=defaults["profit_account_id"],
            loss_account=defaults["loss_account_id"],
        )
        return defaults

    @api.onchange("type")
    def _onchange_type(self):
        self.filtered(
            lambda journal: journal.type not in DOCUMENT_TYPES
        ).alias_name = False
        for journal in self.filtered(
            lambda journal: not journal.alias_name and journal.type in DOCUMENT_TYPES
        ):
            journal.alias_name = self._alias_prepare_alias_name(
                False, journal.name, journal.code, journal.type, journal.company_id
            )

        for journal in self:
            if self._is_generated_code(journal.code):
                journal.code = False
            journal.update(
                self._prepare_type_defaults(journal.type, journal.company_id)
            )

        self.env.add_to_compute(self._fields["code"], self)

    @api.depends("type")
    def _compute_name_placeholder(self):
        for journal in self:
            journal.name_placeholder = (
                self._get_default_name(journal.type, journal.code)
                if journal.type
                else _("Select a type")
            )

    @api.model
    def _get_type_label(self, journal_type):
        spec = JOURNAL_TYPES.get(journal_type)
        return str(spec["label"]) if spec else journal_type

    @api.model
    def _get_default_name(self, journal_type, code=None):
        match = re.search(r"[0-9]+$", code or "")
        suffix = match.group() if match else "1"
        return f"{self._get_type_label(journal_type)} ({suffix})"

    @api.constrains("type", "bank_account_id")
    @_debug.perf.timed
    def _check_bank_account(self):
        for journal in self:
            if journal.type == "bank" and journal.bank_account_id:
                if (
                    journal.bank_account_id.company_id
                    and journal.bank_account_id.company_id != journal.company_id
                ):
                    _debug.logic(
                        "bank_account_company_mismatch",
                        journal=journal,
                        bank_account=journal.bank_account_id,
                    )
                    raise ValidationError(
                        _(
                            "The bank account of a bank journal must belong to the same company (%s).",
                            journal.company_id.name,
                        )
                    )
                if journal.bank_account_id.partner_id != journal.company_id.partner_id:
                    _debug.logic(
                        "bank_account_holder_mismatch",
                        journal=journal,
                        bank_account=journal.bank_account_id,
                    )
                    raise ValidationError(
                        _(
                            "The holder of a journal's bank account must be the company (%s).",
                            journal.company_id.name,
                        )
                    )

    @api.constrains("company_id")
    @_debug.perf.timed
    def _check_company_consistency(self):
        move_companies_by_journal = defaultdict(set)
        for journal, move_company in self.env["account.move"]._read_group(
            [("journal_id", "in", self.ids)], ["journal_id", "company_id"]
        ):
            move_companies_by_journal[journal.id].add(move_company)
        for company, journals in groupby(self, lambda journal: journal.company_id):
            if any(
                company not in move_company.parent_ids
                for journal in journals
                for move_company in move_companies_by_journal[journal.id]
            ):
                raise ValidationError(
                    _(
                        "You can't change the company of your journal since there are some journal entries linked to it."
                    )
                )

    @api.depends(
        "default_account_id",
        "suspense_account_id",
        "non_deductible_account_id",
        "profit_account_id",
        "loss_account_id",
        "inbound_payment_channel_ids.payment_account_id",
        "outbound_payment_channel_ids.payment_account_id",
    )
    def _compute_structural_account_ids(self):
        for journal in self:
            journal.structural_account_ids = (
                journal.default_account_id
                | journal.suspense_account_id
                | journal.non_deductible_account_id
                | journal.profit_account_id
                | journal.loss_account_id
                | journal.inbound_payment_channel_ids.payment_account_id
                | journal.outbound_payment_channel_ids.payment_account_id
            )

    def _get_structural_account_ids(self):
        self.check_singleton()
        return self.structural_account_ids

    def _is_account_allowed(self, account):
        self.check_singleton()
        return (
            not self.allowed_account_ids
            or account in self.allowed_account_ids
            or account in self._get_structural_account_ids()
        )

    @api.constrains("allowed_account_ids")
    @_debug.perf.timed
    def _check_allowed_accounts_cover_existing_items(self):
        journals = self.filtered("allowed_account_ids")
        _debug.logic(
            "allowed_accounts_scope",
            journals=journals,
            skipped=not journals,
        )
        if not journals:
            return
        per_journal = Domain.OR(
            Domain(
                [
                    ("journal_id", "=", journal.id),
                    (
                        "account_id",
                        "not in",
                        (
                            journal.allowed_account_ids
                            | journal._get_structural_account_ids()
                        ).ids,
                    ),
                ]
            )
            for journal in journals
        )
        offending = self.env["account.move.line"].search(
            per_journal
            & Domain(
                [
                    ("parent_state", "!=", "cancel"),
                    ("display_type", "not in", NON_ACCOUNTABLE_DISPLAY_TYPES),
                ]
            ),
            limit=1,
        )
        _debug.logic(
            "allowed_accounts_checked",
            journals=journals,
            offending=offending,
        )
        if offending:
            raise ValidationError(
                _(
                    "Journal %(journal)s already has journal items on "
                    "%(account)s, which this list of allowed accounts excludes.",
                    journal=offending.journal_id.display_name,
                    account=offending.account_id.display_name,
                )
            )

    @api.constrains("type", "default_account_id")
    @_debug.perf.timed
    def _check_type_default_account_id_type(self):
        for journal in self:
            if journal.type in (
                "sale",
                "purchase",
            ) and journal.default_account_id.account_type in (
                "asset_receivable",
                "liability_payable",
            ):
                raise ValidationError(
                    _(
                        "The type of the journal's default credit/debit account shouldn't be 'receivable' or 'payable'."
                    )
                )

    @api.constrains("inbound_payment_channel_ids", "outbound_payment_channel_ids")
    @_debug.perf.timed
    def _check_payment_channel_ids_multiplicity(self):
        info = self._get_journals_payment_method_information()
        pay_methods = info.pay_methods
        manage_providers = info.manage_providers
        method_information_mapping = info.method_information_mapping
        providers_per_code = info.providers_per_code

        for journal in self:
            for payment_type in ("inbound", "outbound"):
                counter = {}
                for line in journal[f"{payment_type}_payment_channel_ids"]:
                    values = method_information_mapping.get(line.payment_method_id.id)
                    if not values or values["mode"] not in ("electronic", "unique"):
                        continue

                    key = line.payment_method_id.id, line.name
                    counter.setdefault(key, 0)
                    counter[key] += 1
                    if counter[key] > 1:
                        raise ValidationError(
                            _(
                                "You can't have two payment method lines of the same payment type (%(payment_type)s) "
                                "and with the same name (%(name)s) on a single journal.",
                                payment_type=payment_type,
                                name=line.name,
                            )
                        )

        _debug.pipeline(
            "channel_names_unique",
            journals=self,
            methods=len(pay_methods),
            manage_providers=manage_providers,
        )
        failing_unicity_payment_methods = self.env["account.payment.method"]
        for company in self.company_id:
            for pay_method in pay_methods:
                values = method_information_mapping[pay_method.id]
                company_journals = values["company_journals"]

                if values["mode"] == "unique":
                    if len(company_journals.get(company.id, [])) > 1:
                        failing_unicity_payment_methods |= pay_method
                elif manage_providers and values["mode"] == "electronic":
                    for provider_id in providers_per_code.get(company.id, {}).get(
                        pay_method.code, set()
                    ):
                        linked = company_journals.get(company.id, {}).get(
                            provider_id, []
                        )
                        if len(linked) > 1:
                            failing_unicity_payment_methods |= pay_method

        _debug.logic(
            "method_unicity_checked",
            journals=self,
            failing=failing_unicity_payment_methods,
        )
        if failing_unicity_payment_methods:
            raise ValidationError(
                _(
                    "Some payment methods supposed to be unique already exists somewhere else.\n(%s)",
                    ", ".join(failing_unicity_payment_methods.mapped("display_name")),
                )
            )

    @api.constrains("active")
    @_debug.perf.timed
    def _check_auto_post_draft_entries(self):
        archived = self.filtered(lambda j: not j.active)
        if archived:
            pending_moves = self.env["account.move"].search(
                [("journal_id", "in", archived.ids), ("state", "=", "draft")], limit=1
            )

            if pending_moves:
                _debug.logic(
                    "archive_blocked_draft_moves", journal=archived, move=pending_moves
                )
                raise ValidationError(
                    _(
                        "You can not archive a journal containing draft journal entries.\n\n"
                        "To proceed:\n"
                        "1/ click on the top-right button 'Journal Entries' from this journal form\n"
                        "2/ then filter on 'Draft' entries\n"
                        "3/ select them all and post or delete them through the action menu"
                    )
                )

    @api.onchange("incoming_einvoice_notification_email")
    def _onchange_incoming_einvoice_notification_email(self):
        for journal in self:
            journal.incoming_einvoice_notification_email = ", ".join(
                email_normalize_all(journal.incoming_einvoice_notification_email or "")
            )

    @api.depends("type")
    def _compute_refund_sequence(self):
        for journal in self:
            journal.refund_sequence = journal.type in DOCUMENT_TYPES

    @api.depends("type")
    def _compute_payment_sequence(self):
        for journal in self:
            journal.payment_sequence = journal.type in LIQUIDITY_TYPES

    def _compute_available_invoice_template_pdf_report_ids(self):
        reports = self.env[
            "account.move"
        ]._get_available_invoice_template_pdf_report_ids()
        for journal in self:
            journal.available_invoice_template_pdf_report_ids = reports

    @_debug.perf.timed
    def unlink(self):
        _debug.lifecycle("unlink", unlink=self)
        orphaned_bank_accounts = self.bank_account_id
        if orphaned_bank_accounts:
            orphaned_bank_accounts -= (
                self.with_context(active_test=False)
                .search(
                    [
                        ("bank_account_id", "in", orphaned_bank_accounts.ids),
                        ("id", "not in", self.ids),
                    ]
                )
                .bank_account_id
            )
        self.env["account.payment.channel"].search(
            [("journal_id", "in", self.ids)]
        ).unlink()
        ret = super().unlink()
        orphaned_bank_accounts.unlink()
        return ret

    @_debug.perf.timed
    def copy_data(self, default=None):
        _debug.lifecycle("copy_data", records=self)
        default = dict(default or {})
        vals_list = super().copy_data(default)
        used_by_company = {}
        for journal, vals in zip(self, vals_list, strict=True):
            company = self.env["res.company"].browse(vals["company_id"])
            used = used_by_company.get(company.id)
            if used is None:
                used = used_by_company[company.id] = self._get_company_journal_codes(
                    company
                )
            if "code" not in default:
                vals["code"] = self._get_next_available_code(
                    vals["code"], company, used_codes=used
                )
            used.add(vals["code"])
            if "name" not in default:
                vals["name"] = _("%s (copy)", journal.name or "")
        _debug.logic(
            "copy_codes_regenerated",
            journals=self,
            regenerated="code" not in default,
            renamed="name" not in default,
            companies=len(used_by_company),
        )
        return vals_list

    def copy_translations(self, new, excluded=()):
        super().copy_translations(new, excluded=(*excluded, "name"))
        self._copy_translations_of_renamed_field(
            new,
            "name",
            lambda record, term: record.env._("%s (copy)", term or ""),
        )

    @_debug.perf.timed
    def write(self, vals):
        _debug.lifecycle("write", records=self, fields=sorted(vals))
        journals_changing_type = (
            self.filtered(lambda journal: journal.type != vals["type"])
            if "type" in vals
            else self.browse()
        )

        unusable_alias = bool(vals.get("alias_name")) and (
            not is_encodable(vals["alias_name"])
            or not self.env["mail.alias"]._normalize_alias_name(vals["alias_name"])
        )
        alias_names = {}
        if _debug.logic.enabled and journals_changing_type:
            _debug.logic(
                "write_journal",
                change=set(journals_changing_type.mapped("type")),
                type=vals["type"],
                journals_changing_type=journals_changing_type,
            )
        if _debug.logic.enabled and unusable_alias:
            _debug.logic("write_unusable_deriving", alias_name=vals["alias_name"])
        if unusable_alias and "type" not in vals:
            taken = {}
            for journal in self:
                derived = self._alias_prepare_alias_name(
                    False,
                    vals.get("name", journal.name),
                    vals.get("code", journal.code),
                    journal.type,
                    journal.company_id,
                )
                claimed = taken.setdefault(journal.company_id.id, set())
                if derived and derived in claimed:
                    derived = self.env["mail.alias"]._normalize_alias_name(
                        f"{derived}-{journal.code}"
                    )
                claimed.add(derived)
                alias_names[journal.id] = derived
            vals = {key: value for key, value in vals.items() if key != "alias_name"}

        self._check_write_preconditions(vals)
        self._sync_bank_account_before_write(vals)
        result = super().write(vals)
        for journal in self:
            if journal.id in alias_names:
                journal.alias_name = alias_names[journal.id]
        self._sync_after_write(vals, journals_changing_type)
        return result

    @_debug.perf.timed
    def _check_write_preconditions(self, vals):
        _debug.logic(
            "write_preconditions",
            journals=self,
            bank_account=vals.get("bank_account_id"),
            company_in_vals="company_id" in vals,
            hash_disable=(
                "restrict_mode_hash_table" in vals
                and not vals.get("restrict_mode_hash_table")
            ),
        )
        if vals.get("bank_account_id"):
            bank_account = self.env["res.partner.bank"].browse(vals["bank_account_id"])
            for journal in self:
                company = (
                    self.env["res.company"].browse(vals["company_id"])
                    if "company_id" in vals
                    else journal.company_id
                )
                if bank_account.partner_id != company.partner_id:
                    raise UserError(
                        _(
                            "The partners of the journal's company and the related bank account mismatch."
                        )
                    )
        if "restrict_mode_hash_table" in vals and not vals.get(
            "restrict_mode_hash_table"
        ):
            domain = self.env["account.move"]._get_domain_move_hash(
                common_domain=[
                    ("journal_id", "in", self.ids),
                    ("inalterable_hash", "!=", False),
                ]
            )
            if self.env["account.move"].sudo().search_count(domain, limit=1):
                field_string = self._fields["restrict_mode_hash_table"].get_description(
                    self.env
                )["string"]
                raise UserError(
                    _(
                        "You cannot modify the field %s of a journal that already has accounting entries.",
                        field_string,
                    )
                )

    @_debug.perf.timed
    def _sync_bank_account_before_write(self, vals):
        for journal in self:
            if "company_id" in vals and journal.company_id.id != vals["company_id"]:
                company = self.env["res.company"].browse(vals["company_id"])
                if (
                    journal.bank_account_id.company_id
                    and journal.bank_account_id.company_id != company
                ):
                    _debug.logic(
                        "bank_account_company_moved", journal=journal, company=company
                    )
                    journal.bank_account_id.write(
                        {
                            "company_id": company.id,
                            "partner_id": company.partner_id.id,
                        }
                    )
            if "currency_id" in vals and journal.bank_account_id:
                journal.bank_account_id.currency_id = vals["currency_id"]
            if (
                vals.get("bank_acc_number")
                and journal.bank_account_id.allow_out_payment
                and journal.bank_account_id.acc_number != vals["bank_acc_number"]
            ):
                _debug.logic("bank_out_payment_revoked", journal=journal)
                journal.bank_account_id.allow_out_payment = False

    @_debug.perf.timed
    def _sync_after_write(self, vals, journals_changing_type):
        if "type" in vals and not self.env.context.get(
            "account_journal_skip_alias_sync"
        ):
            claimed = {}
            alias_names = {}
            alias_defaults = {}
            for journal in self:
                alias_vals = journal._alias_get_creation_values()
                derived = alias_vals["alias_name"]
                company_claimed = claimed.setdefault(journal.company_id.id, set())
                if derived and derived in company_claimed:
                    derived = self.env["mail.alias"]._normalize_alias_name(
                        f"{derived}-{journal.code}"
                    )
                company_claimed.add(derived)
                alias_names[journal.id] = derived
                alias_defaults[journal.id] = alias_vals["alias_defaults"]
            for journal in self:
                journal.update(
                    {
                        "alias_defaults": alias_defaults[journal.id],
                        "alias_name": alias_names[journal.id],
                    }
                )

        for journal in journals_changing_type:
            defaults = self._prepare_type_defaults(journal.type, journal.company_id)
            journal.update(
                {fname: value for fname, value in defaults.items() if fname not in vals}
            )
            if journal.type in LIQUIDITY_TYPES and not journal.default_account_id:
                _debug.logic("liquidity_type_without_default_account", journal=journal)
                journal.default_account_id = self._find_or_create_default_account(
                    journal.company_id,
                    journal.type,
                    {"name": journal.name, "type": journal.type},
                )

        if "currency_id" in vals:
            for journal in self.filtered(
                lambda journal: journal.type in LIQUIDITY_TYPES
            ):
                journal.default_account_id.currency_id = journal.currency_id

        if "bank_acc_number" in vals or "bank_account_id" in vals:
            acc_number = (
                vals.get("bank_acc_number") if "bank_acc_number" in vals else None
            )
            for journal in self:
                journal._link_bank_account(acc_number, vals.get("bank_id"))

    def _alias_get_creation_values(self):
        values = super()._alias_get_creation_values()
        values["alias_model_id"] = self.env["ir.model"]._get_id("account.move")
        if self.id:
            values["alias_name"] = self._alias_prepare_alias_name(
                self.alias_name, self.name, self.code, self.type, self.company_id
            )
            values["alias_defaults"] = defaults = self._prepare_alias_defaults()
            defaults["company_id"] = self.company_id.id
            defaults["move_type"] = JOURNAL_TYPES.get(self.type, {}).get(
                "alias_move_type", "entry"
            )
            defaults["journal_id"] = self.id
        return values

    @api.model
    def _get_domain_selectable(self):
        return [
            "|",
            ("allowed_user_ids", "=", False),
            ("allowed_user_ids", "in", [self.env.uid]),
        ]

    @api.model
    def _alias_prepare_alias_name(self, alias_name, name, code, jtype, company):
        if jtype not in ("purchase", "sale"):
            _debug.logic("alias_skipped", reason="journal_type", type=jtype)
            return False

        alias_name = next(
            (
                string
                for string in (alias_name, name, code, jtype)
                if (
                    string
                    and is_encodable(string)
                    and self.env["mail.alias"]._normalize_alias_name(string)
                )
            ),
            False,
        )
        if company != self.env.ref("base.main_company"):
            company_identifier = (
                self.env["mail.alias"]._normalize_alias_name(company.name)
                if is_encodable(company.name)
                else company.id
            )
            if f"-{company_identifier}" not in alias_name:
                alias_name = f"{alias_name}-{company_identifier}"
        _debug.logic(
            "alias_name_prepared", type=jtype, company=company, alias=alias_name
        )
        return self.env["mail.alias"]._normalize_alias_name(alias_name)

    @api.model
    def _get_unique_alias_name(self, vals, company, taken_alias_names=()):
        alias_name = self.env["mail.alias"]._normalize_alias_name(vals["alias_name"])
        if not alias_name:
            _debug.logic("alias_unsanitizable", company=company, code=vals.get("code"))
            return False
        alias_domain_name = company.alias_domain_id.name

        domain = [("alias_name", "=", alias_name)]
        if alias_domain_name:
            domain.extend(
                [
                    "|",
                    ("alias_domain", "=", alias_domain_name),
                    ("alias_domain_id", "=", False),
                ]
            )

        taken = alias_name in taken_alias_names or self.env["mail.alias"].search_count(
            domain, limit=1
        )
        if taken:
            _debug.logic(
                "alias_name_taken",
                alias=alias_name,
                company=company,
                code=vals.get("code"),
            )
            alias_name = self.env["mail.alias"]._normalize_alias_name(
                f"{alias_name}-{vals.get('code')}"
            )

        return alias_name

    @api.model
    def _get_company_journal_codes(self, company):
        groups = (
            self.env["account.journal"]
            .with_context(active_test=False)
            ._read_group(
                domain=self.env["account.journal"]._check_company_domain(company),
                aggregates=["code:array_agg"],
            )
        )
        return set(groups[0][0]) if groups and groups[0][0] else set()

    @api.model
    def _get_next_available_code(
        self, prefix, company, codes_to_avoid=(), used_codes=None
    ):
        size = self._fields["code"].size
        if used_codes is None:
            used_codes = self._get_company_journal_codes(company)
        used = used_codes | set(codes_to_avoid)
        prefix = re.sub(r"\d+", "", prefix or "").strip() or "J"
        for num in range(1, 10**size):
            suffix = str(num)
            candidate = f"{prefix[: size - len(suffix)]}{suffix}"
            if candidate not in used:
                _debug.logic(
                    "journal_code_generated",
                    prefix=prefix,
                    company=company,
                    code=candidate,
                    used=len(used),
                )
                return candidate
        _debug.logic("journal_code_range_exhausted", prefix=prefix, company=company)
        raise UserError(
            _(
                "Could not generate a unique journal code from prefix %(prefix)s: "
                "the whole numeric range is already in use.",
                prefix=prefix,
            )
        )

    @api.model
    def _get_next_journal_default_code(
        self, journal_type, company, codes_to_avoid=None, used_codes=None
    ):
        journal_code_base = JOURNAL_TYPES.get(journal_type, {}).get("code_prefix")
        if not journal_code_base:
            raise UserError(
                _(
                    "Unknown journal type '%s', cannot generate a default code.",
                    journal_type,
                )
            )
        return self._get_next_available_code(
            journal_code_base, company, codes_to_avoid or (), used_codes=used_codes
        )

    @api.model
    @_debug.perf.timed
    def _prepare_account_vals(self, company, code, vals, account_type):
        return {
            "name": vals.get("name"),
            "code": code,
            "account_type": account_type,
            "currency_id": vals.get("currency_id"),
            "company_ids": [Command.link(company.id)],
        }

    @api.model
    @_debug.perf.timed
    def _prepare_liquidity_account_vals(self, company, code, vals):
        return self._prepare_account_vals(company, code, vals, "asset_cash")

    @api.model
    @_debug.perf.timed
    def _prepare_credit_account_vals(self, company, code, vals):
        return self._prepare_account_vals(company, code, vals, "liability_credit_card")

    @api.model
    def _find_or_create_default_account(self, company, journal_type, vals):
        if journal_type == "credit":
            existing = (
                self.env["account.account"]
                .with_company(company)
                .search(
                    [
                        *self.env["account.account"]._check_company_domain(company),
                        (
                            "account_type",
                            "in",
                            JOURNAL_TYPES[journal_type]["account_types"],
                        ),
                    ],
                    limit=1,
                )
            )
            if existing:
                _debug.logic(
                    "default_account_reused",
                    company=company,
                    type=journal_type,
                    account=existing,
                )
                return existing.id
        return self._create_default_account(company, journal_type, vals)

    @api.model
    @_debug.perf.timed
    def _create_default_account(self, company, journal_type, vals):
        if journal_type not in LIQUIDITY_TYPES:
            raise UserError(
                _(
                    "No default account can be created for a journal of type %s.",
                    journal_type,
                )
            )
        random_account = (
            self.env["account.account"]
            .with_company(company)
            .search(
                self.env["account.account"]._check_company_domain(company),
                limit=1,
            )
        )
        digits = len(random_account.code) if random_account else 6
        _debug.logic(
            "default_account_digits",
            company=company,
            journal_type=journal_type,
            digits=digits,
            from_existing=bool(random_account),
        )

        if journal_type == "cash":
            account_prefix = (
                company.account_config_id.cash_account_code_prefix
                or company.account_config_id.bank_account_code_prefix
                or ""
            )
        else:
            account_prefix = company.account_config_id.bank_account_code_prefix or ""

        start_code = account_prefix.ljust(digits, "0")
        default_account_code = (
            self.env["account.account"]
            .with_company(company)
            ._search_new_account_code(start_code)
        )

        if journal_type == "credit":
            default_account_vals = self._prepare_credit_account_vals(
                company, default_account_code, vals
            )
        else:
            default_account_vals = self._prepare_liquidity_account_vals(
                company, default_account_code, vals
            )

        _debug.pipeline(
            "default_account_code_found",
            company=company,
            journal_type=journal_type,
            prefix=account_prefix,
            start_code=start_code,
            code=default_account_code,
        )
        default_account = self.env["account.account"].create(default_account_vals)
        _debug.logic(
            "default_account_created",
            company=company,
            account=default_account,
            xmlid_registered=bool(default_account),
        )
        if default_account:
            self.env["ir.model.data"]._update_xmlids(
                [
                    {
                        "xml_id": f"account.{company.id}_{journal_type}_journal_default_account_{default_account.id}",
                        "record": default_account,
                        "noupdate": True,
                    }
                ]
            )
        return default_account.id

    @api.model
    def _reserve_batch(self, vals_list):
        reservations = JournalBatchReservations({}, {}, set())
        for vals in vals_list:
            company_id = vals.get("company_id") or self.env.company.id
            reservations.codes.setdefault(company_id, set())
            reservations.alias_names.setdefault(company_id, set())
            if vals.get("code"):
                reservations.codes[company_id].add(vals["code"])
        return reservations

    @api.model
    def _reserved_codes(self, reservations, company):
        codes = reservations.codes.setdefault(company.id, set())
        reservations.alias_names.setdefault(company.id, set())
        if company.id not in reservations.companies_read:
            reservations.companies_read.add(company.id)
            codes |= self._get_company_journal_codes(company)
        return codes

    @api.model
    @_debug.perf.timed
    def _update_missing_values(self, vals, reservations=None):
        journal_type = vals.get("type")
        is_import = "import_file" in self.env.context
        if is_import and not journal_type:
            vals["type"] = journal_type = "general"

        if not journal_type:
            return

        company = (
            self.env["res.company"].browse(vals["company_id"])
            if vals.get("company_id")
            else self.env.company
        )
        vals["company_id"] = company.id
        if reservations is None:
            reservations = self._reserve_batch([vals])

        if not is_import:
            self._update_code(vals, journal_type, company, reservations)

        if journal_type in LIQUIDITY_TYPES:
            vals["name"] = (
                vals.get("name")
                or vals.get("bank_acc_number")
                or vals.get("name_placeholder")
                or self._get_default_name(journal_type, vals.get("code"))
            )

        for fname, value in self._prepare_type_defaults(journal_type, company).items():
            if value:
                vals.setdefault(fname, value)

        if journal_type in LIQUIDITY_TYPES and not vals.get("default_account_id"):
            vals["default_account_id"] = self._find_or_create_default_account(
                company, journal_type, vals
            )

        if is_import:
            self._update_code(vals, journal_type, company, reservations)

        if journal_type in DOCUMENT_TYPES:
            if "alias_name" not in vals:
                vals["alias_name"] = self._alias_prepare_alias_name(
                    False, vals.get("name"), vals.get("code"), journal_type, company
                )
            taken_alias_names = reservations.alias_names.setdefault(company.id, set())
            vals["alias_name"] = self._get_unique_alias_name(
                vals, company, taken_alias_names
            )
            if vals["alias_name"]:
                taken_alias_names.add(vals["alias_name"])

        if not vals.get("name"):
            vals["name"] = vals.get("name_placeholder") or self._get_default_name(
                journal_type, vals.get("code")
            )
        _debug.logic(
            "journal_defaults",
            type=journal_type,
            company=company,
            code=vals.get("code"),
            name=vals.get("name"),
            alias=vals.get("alias_name"),
            default_account=vals.get("default_account_id"),
            import_=is_import,
        )

    @api.model
    def _update_code(self, vals, journal_type, company, reservations):
        if vals.get("code"):
            reservations.codes.setdefault(company.id, set()).add(vals["code"])
            return
        candidate = (
            (vals.get("name") or "")[:5].strip()
            if "import_file" in self.env.context
            else ""
        )
        taken_codes = self._reserved_codes(reservations, company)
        _debug.logic(
            "journal_code_candidate",
            company=company,
            candidate=candidate,
            taken=bool(candidate) and candidate in taken_codes,
        )
        if not candidate or candidate in taken_codes:
            candidate = self._get_next_journal_default_code(
                journal_type, company, used_codes=taken_codes
            )
        vals["code"] = candidate
        taken_codes.add(candidate)
        _debug.logic(
            "journal_code_assigned", type=journal_type, company=company, code=candidate
        )

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
        reservations = self._reserve_batch(vals_list)
        for vals in vals_list:
            self._update_missing_values(vals, reservations=reservations)
        if _debug.logic.enabled:
            _debug.logic(
                "create", codes=[(v.get("type"), v.get("code")) for v in vals_list]
            )

        journals = super(
            AccountJournal, self.with_context(mail_create_nolog=True)
        ).create(vals_list)

        for journal, vals in zip(journals, vals_list, strict=True):
            journal._link_bank_account(vals.get("bank_acc_number"), vals.get("bank_id"))

        return journals

    def _link_bank_account(self, acc_number=None, bank_id=None):
        self.check_singleton()
        if self.type != "bank":
            return
        if acc_number and not self.bank_account_id:
            self.set_bank_account(acc_number, bank_id)
        if self.bank_account_id and self.bank_account_id._can_user_trust():
            self.bank_account_id.allow_out_payment = True

    def set_bank_account(self, acc_number, bank_id=None):
        self.check_singleton()
        self.bank_account_id = self.env["res.partner.bank"]._get_or_create_bank_account(
            account_number=acc_number,
            partner=self.company_id.partner_id,
            allow_company_account_creation=True,
            company=self.company_id,
            extra_create_vals={
                "bank_id": bank_id,
                "currency_id": self.currency_id.id,
                "journal_id": self,
            },
        )

    @api.depends("currency_id", "company_id.currency_id")
    def _compute_display_name(self):
        for journal in self:
            name = journal.name
            if (
                journal.currency_id
                and journal.currency_id != journal.company_id.sudo().currency_id
            ):
                name = f"{name} ({journal.currency_id.name})"
            journal.display_name = name

    @_debug.perf.timed
    def action_configure_bank_journal(self):
        _debug.lifecycle("action_configure_bank_journal", records=self)
        return (
            self.env["res.company"]
            .with_context(default_linked_journal_id=self.id)
            .setting_init_bank_account_action()
        )

    @api.model
    @_debug.perf.timed
    def _prepare_no_journal_error_msg(self, company_name, journal_types):
        return _(
            "No journal could be found in company %(company_name)s for any of those types: %(journal_types)s",
            company_name=company_name,
            journal_types=", ".join(journal_types),
        )

    @_debug.perf.timed
    def _create_document_from_attachment(self, attachment_ids):
        if not self:
            self = self.env["account.journal"].browse(
                self.env.context.get("default_journal_id")
            )
        move_type = self.env.context.get("default_move_type", "entry")
        if not self:
            if move_type in self.env["account.move"].get_sale_types(
                include_receipts=True
            ):
                journal_type = "sale"
            elif move_type in self.env["account.move"].get_purchase_types(
                include_receipts=True
            ):
                journal_type = "purchase"
            else:
                raise UserError(
                    _("The journal in which to upload the invoice is not specified. ")
                )
            self = self.env["account.journal"].search(
                [
                    *self.env["account.journal"]._check_company_domain(
                        self.env.company
                    ),
                    ("type", "=", journal_type),
                ],
                limit=1,
            )

        attachments = self.env["ir.attachment"].browse(attachment_ids)
        if not attachments:
            raise UserError(_("No attachment was provided"))

        if not self:
            raise UserError(
                self.env["account.journal"]._prepare_no_journal_error_msg(
                    self.env.company.display_name, [journal_type]
                )
            )

        _debug.pipeline(
            "_create_document_from_attachment",
            journal=self,
            attachments_count=len(attachments),
            move_type=move_type,
        )
        invoices = (
            self.env["account.move"]
            .with_context(
                default_journal_id=self.id,
                skip_is_manually_modified=True,
            )
            ._create_records_from_attachments(attachments)
        )
        _debug.pipeline("documents_created", journal=self, invoices=invoices)

        for invoice in invoices:
            invoice._autopost_bill()

        return invoices

    def create_document_from_attachment(self, attachment_ids):
        invoices = self._create_document_from_attachment(attachment_ids)
        action_vals = {
            "name": _("Generated Documents"),
            "domain": [("id", "in", invoices.ids)],
            "res_model": "account.move",
            "type": "ir.actions.act_window",
            "context": self.env.context,
        }
        if len(invoices) == 1:
            action_vals.update(
                {
                    "views": [[False, "form"]],
                    "view_mode": "form",
                    "res_id": invoices[0].id,
                }
            )
        else:
            action_vals.update(
                {
                    "views": [[False, "list"], [False, "kanban"], [False, "form"]],
                    "view_mode": "list,kanban,form",
                }
            )
        return action_vals

    def _get_journal_bank_account_balance(self, domain=None):
        self.check_singleton()
        nb_lines, balance, amount_currency = self.env["account.move.line"]._read_group(
            domain=(
                Domain("account_id", "in", tuple(self.default_account_id.ids))
                & Domain("display_type", "not in", NON_ACCOUNTABLE_DISPLAY_TYPES)
                & Domain("parent_state", "!=", "cancel")
                & Domain(domain or Domain.TRUE)
            ),
            aggregates=("__count", "balance:sum", "amount_currency:sum"),
        )[0]

        company_currency = self.company_id.currency_id
        journal_currency = (
            self.currency_id
            if self.currency_id and self.currency_id != company_currency
            else False
        )
        return amount_currency if journal_currency else balance, nb_lines

    def _get_journal_inbound_outstanding_payment_accounts(self):
        self.check_singleton()
        return self.inbound_payment_channel_ids.payment_account_id

    def _get_journal_outbound_outstanding_payment_accounts(self):
        self.check_singleton()
        return self.outbound_payment_channel_ids.payment_account_id

    def _get_available_payment_channels(self, payment_type):
        if not self:
            return self.env["account.payment.channel"]
        self.check_singleton()
        if not payment_type:
            return self.env["account.payment.channel"]
        if payment_type not in ("inbound", "outbound"):
            raise ValueError(f"Unknown payment type {payment_type!r}")
        return self[f"{payment_type}_payment_channel_ids"]

    def _is_payment_method_available(self, payment_method_code, complete_domain=True):
        self.check_singleton()
        method_domain = self.env["account.payment.method"]._get_domain_payment_method(
            code=payment_method_code,
            with_country=complete_domain,
            with_currency=complete_domain,
        )
        return self.filtered_domain(method_domain)

    @_debug.perf.timed
    def _process_reference_for_sale_order(self, order_reference):
        self.check_singleton()
        return order_reference

    def _get_journal_notification_unsubscribe_scope(self):
        return "account_journal_notification_unsubscribe"

    def _unsubscribe_invoice_notification_email(self, email_to_remove):
        self.check_singleton()
        normalized_to_remove = email_normalize(email_to_remove, strict=False)
        subscribed_emails = set(
            email_normalize_all(self.incoming_einvoice_notification_email or "")
        )
        if not normalized_to_remove or normalized_to_remove not in subscribed_emails:
            return False
        remaining = subscribed_emails - {normalized_to_remove}
        self.incoming_einvoice_notification_email = ", ".join(sorted(remaining))
        return True

    def _notify_einvoices_received(self, moves):
        self.check_singleton()
        for move in moves:
            self._notify_invoice_subscribers(move)

    @_debug.perf.timed
    def _notify_invoice_subscribers(self, invoice, mail_params=None):
        self.check_singleton()
        invoice.check_singleton()

        recipients = set(
            email_normalize_all(self.incoming_einvoice_notification_email or "")
        )
        _debug.logic(
            "subscribers_resolved",
            journal=self,
            move=invoice,
            recipients=len(recipients),
        )
        if not recipients:
            return

        if not (
            template := self.env.ref(
                "account.mail_template_invoice_subscriber", raise_if_not_found=False
            )
        ):
            return

        _debug.pipeline(
            "subscribers_notifying",
            journal=self,
            move=invoice,
            recipients=len(recipients),
            template=template,
        )
        base_url = self.get_base_url()
        for recipient in recipients:
            unsubscribe_token = hash_sign(
                self.sudo().env,
                scope=self._get_journal_notification_unsubscribe_scope(),
                message_values={
                    "email_to_unsubscribe": recipient,
                    "journal_id": self.id,
                },
            )
            unsubscribe_url = urls.urljoin(
                base_url,
                f"/my/journal/{self.id}/unsubscribe?{urlencode({'token': unsubscribe_token})}",
            )

            template.with_context(unsubscribe_url=unsubscribe_url).send_mail(
                invoice.id,
                email_values={
                    **(mail_params or {}),
                    "email_to": recipient,
                },
                force_send=True,
            )

    def button_fetch_in_einvoices(self):
        pass

    def button_refresh_out_einvoices_status(self):
        pass
