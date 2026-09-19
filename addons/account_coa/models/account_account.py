import contextlib
import itertools
import re
from bisect import bisect_left
from collections import defaultdict

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.tools import SQL, Query

ACCOUNT_REGEX = re.compile(r"(?:(\S*\d+\S*))?(.*)")
ACCOUNT_CODE_REGEX = re.compile(r"^[A-Za-z0-9.\-/]+$")
ACCOUNT_CODE_NUMBER_REGEX = re.compile(r"(.*?)(\d*)(\D*?)$")


class AccountAccount(models.Model):
    """Chart of Accounts foundation: code, type, tags, and multi-company support."""

    _name = "account.account"
    _description = "Account"
    _order = "code, placeholder_code"
    _check_company_auto = True
    _check_company_domain = models.check_companies_domain_parent_of

    name = fields.Char(
        string="Account Name",
        translate=True,
        index="trigram",
        required=True,
    )
    description = fields.Text(translate=True)
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Account Currency",
        help="Forces all journal items in this account to have a specific "
        "currency (i.e. bank journals). If no currency is set, entries "
        "can use any currency.",
    )
    company_currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_company_currency_id",
    )
    code = fields.Char(
        size=64,
        compute="_compute_code",
        inverse="_inverse_code",
        search="_search_code",
    )
    code_store = fields.Char(company_dependent=True)
    placeholder_code = fields.Char(
        string="Display code",
        compute="_compute_placeholder_code",
        search="_search_placeholder_code",
    )
    active = fields.Boolean(default=True)
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
            ("expense_other", "Other Expenses"),
            ("expense_depreciation", "Depreciation"),
            ("expense_direct_cost", "Cost of Revenue"),
            ("off_balance", "Off-Balance Sheet"),
        ],
        string="Type",
        compute="_compute_account_type_and_tags",
        precompute=True,
        store=True,
        index=True,
        readonly=False,
        required=True,
        help="Account Type is used for information purpose, to generate "
        "country-specific legal reports, and set the rules to close a "
        "fiscal year and generate opening entries.",
    )
    include_initial_balance = fields.Boolean(
        string="Bring Accounts Balance Forward",
        compute="_compute_include_initial_balance",
        search="_search_include_initial_balance",
        help="Used in reports to know if we should consider journal items "
        "from the beginning of time instead of from the fiscal year "
        "only. Account types that should be reset to zero at each new "
        "fiscal year (like expenses, revenue..) should not have this "
        "option set.",
    )
    internal_group = fields.Selection(
        selection=[
            ("equity", "Equity"),
            ("asset", "Asset"),
            ("liability", "Liability"),
            ("income", "Income"),
            ("expense", "Expense"),
            ("off", "Off Balance"),
        ],
        compute="_compute_internal_group",
        search="_search_internal_group",
    )
    reconcile = fields.Boolean(
        string="Allow Reconciliation",
        compute="_compute_reconcile",
        precompute=True,
        store=True,
        readonly=False,
        help="Check this box if this account allows invoices & payments "
        "matching of journal items.",
    )
    note = fields.Text(string="Internal Notes")
    company_ids = fields.Many2many(
        comodel_name="res.company",
        string="Companies",
        depends_context=("uid",),
        default=lambda self: self.env.company,
        readonly=False,
        required=True,
    )
    code_mapping_ids = fields.One2many(
        comodel_name="account.code.mapping",
        inverse_name="account_id",
    )
    # Write after company_ids so _check_code_is_unique does not fire before
    # both fields are set together.
    code_mapping_ids.write_sequence = 19
    tag_ids = fields.Many2many(
        comodel_name="account.account.tag",
        relation="account_account_account_tag",
        string="Tags",
        compute="_compute_account_type_and_tags",
        precompute=True,
        store=True,
        readonly=False,
        ondelete="restrict",
        help="Optional tags you may want to assign for custom reporting",
    )
    root_id = fields.Many2one(
        comodel_name="account.root",
        compute="_compute_account_root",
        search="_search_account_root",
    )
    non_trade = fields.Boolean(
        default=False,
        help="If set, this account will belong to Non Trade "
        "Receivable/Payable in reports and filters.\n"
        "If not, this account will belong to Trade "
        "Receivable/Payable in reports and filters.",
    )
    display_mapping_tab = fields.Boolean(
        default=lambda self: len(self.env.user.company_ids) > 1,
        store=False,
    )

    def _field_to_sql(
        self, alias: str, field_expr: str, query: Query | None = None
    ) -> SQL:
        if field_expr == "internal_group":
            return SQL(
                "split_part(%s, '_', 1)",
                self._field_to_sql(alias, "account_type", query),
            )
        if field_expr == "code":
            return SQL(
                "(COALESCE(%(code_store)s->%(root_company_id)s, to_jsonb(NULL::varchar))->>0)::varchar",
                code_store=SQL.identifier(
                    alias, "code_store", to_flush=self._fields["code_store"]
                ),
                # Inlined as a literal, not a bound parameter: two bound
                # parameters would be distinct nodes to Postgres, breaking
                # ORDER BY/GROUP BY matching against this expression elsewhere.
                root_company_id=SQL(f"'{int(self.env.company.root_id.id)}'"),
            )
        if field_expr == "placeholder_code":
            if "account_first_company" not in query._joins:
                query.add_join(
                    "LEFT JOIN",
                    "account_first_company",
                    SQL(
                        """(
                            SELECT DISTINCT ON (rel.account_account_id)
                                rel.account_account_id AS account_id,
                                rel.res_company_id AS company_id,
                                SPLIT_PART(res_company.parent_path, '/', 1)
                                    AS root_company_id,
                                res_partner.name AS company_name
                            FROM account_account_res_company_rel rel
                            JOIN res_company
                                ON res_company.id = rel.res_company_id
                            JOIN res_partner
                                ON res_partner.id = res_company.partner_id
                            WHERE rel.res_company_id
                                IN %(authorized_company_ids)s
                        ORDER BY rel.account_account_id, company_id
                        )""",
                        authorized_company_ids=self.env.user._get_company_ids(),
                        to_flush=self._fields["company_ids"],
                    ),
                    SQL(
                        "account_first_company.account_id = %(account_id)s",
                        account_id=SQL.identifier(alias, "id"),
                    ),
                )

            return SQL(
                """
                    COALESCE(
                        %(code_store)s->>%(active_company_root_id)s,
                        %(code_store)s->>%(account_first_company_root_id)s
                            || ' (' || %(account_first_company_name)s || ')'
                    )
                """,
                code_store=SQL.identifier(alias, "code_store"),
                # Same literal-vs-bound-parameter requirement as the "code"
                # branch above.
                active_company_root_id=SQL(f"'{int(self.env.company.root_id.id)}'"),
                account_first_company_name=SQL.identifier(
                    "account_first_company",
                    "company_name",
                ),
                account_first_company_root_id=SQL.identifier(
                    "account_first_company",
                    "root_company_id",
                ),
                to_flush=self._fields["code_store"],
            )
        if field_expr == "root_id":
            return SQL(
                "SUBSTRING(%(placeholder_code)s, 1, 2)",
                placeholder_code=self._field_to_sql(
                    alias,
                    "placeholder_code",
                    query,
                ),
            )

        return super()._field_to_sql(alias, field_expr, query)

    @api.constrains("account_type", "reconcile")
    def _check_reconcile(self):
        for account in self:
            if (
                account.account_type in ("asset_receivable", "liability_payable")
                and not account.reconcile
            ):
                raise ValidationError(
                    _(
                        "You cannot have a receivable/payable account that is "
                        "not reconcilable. (account code: %s)",
                        account.code,
                    )
                )

    @api.constrains("reconcile", "account_type")
    def _constrains_reconcile(self):
        for record in self:
            if record.account_type == "off_balance" and record.reconcile:
                raise UserError(
                    _("An Off-Balance account can not be reconcilable"),
                )

    @api.constrains("code")
    def _check_account_code(self):
        for account in self:
            if account.code and not ACCOUNT_CODE_REGEX.match(account.code):
                raise ValidationError(
                    _(
                        "The account code can only contain alphanumeric "
                        "characters, dots, hyphens, and slashes.",
                    )
                )

    @api.constrains("company_ids")
    def _check_company_consistency(self):
        self.invalidate_recordset(fnames=["company_ids"])
        if accounts_without_company := self.filtered(
            lambda a: not a.sudo().company_ids
        ):
            raise ValidationError(
                self.env._(
                    "The following accounts must be assigned to at least "
                    "one company:\n%(accounts)s",
                    accounts="\n".join(
                        f"- {account.display_name}"
                        for account in accounts_without_company
                    ),
                ),
            )
        if self.filtered(
            lambda a: a.account_type == "asset_cash" and len(a.company_ids) > 1
        ):
            raise ValidationError(
                _("Bank & Cash accounts cannot be shared between companies."),
            )

    @api.depends_context("company")
    @api.depends("code_store")
    def _compute_code(self):
        for record, record_root in zip(
            self,
            self.with_company(self.env.company.root_id).sudo(),
            strict=True,
        ):
            record.code = record_root.code_store

    def _search_code(self, operator, value):
        return [
            (
                "id",
                "in",
                self.with_company(self.env.company.root_id)
                .with_context(active_test=False)
                .sudo()
                ._search([("code_store", operator, value)]),
            ),
        ]

    def _inverse_code(self):
        for record, record_root in zip(
            self,
            self.with_company(self.env.company.root_id).sudo(),
            strict=True,
        ):
            record_root.code_store = record.code

        self.invalidate_recordset(fnames=["code"], flush=False)
        self._compute_code()

    @api.depends_context("company", "uid")
    @api.depends("code")
    def _compute_placeholder_code(self):
        self.placeholder_code = False
        for record in self:
            if record.code:
                record.placeholder_code = record.code
            elif authorized_companies := (
                record.company_ids
                & self.env["res.company"].browse(
                    self.env.user._get_company_ids(),
                )
            ).sorted("id"):
                company = authorized_companies[0]
                if code := record.with_company(company).code:
                    record.placeholder_code = f"{code} ({company.name})"

    def _search_placeholder_code(self, operator, value):
        if operator not in ("=ilike", "in"):
            return NotImplemented
        query = Query(self.env, "account_account")
        placeholder_code_sql = self.env["account.account"]._field_to_sql(
            "account_account",
            "placeholder_code",
            query,
        )
        if operator == "in":
            query.add_where(
                SQL("%s = ANY(%s)", placeholder_code_sql, list(value)),
            )
        else:
            query.add_where(
                SQL("%s ILIKE %s", placeholder_code_sql, value),
            )
        return [("id", "in", query)]

    @api.depends_context("company")
    @api.depends("code")
    def _compute_account_root(self):
        for record in self:
            record.root_id = self.env["account.root"]._from_account_code(
                record.placeholder_code,
            )

    def _search_account_root(self, operator, value):
        if operator not in ("in", "child_of", "any"):
            return NotImplemented
        if operator == "any":
            if (
                isinstance(value, Domain)
                and value.field_expr == "display_name"
                and value.operator == "in"
            ):
                roots = self.env["account.root"].browse(value.value)
            else:
                return NotImplemented
        else:
            roots = self.env["account.root"].browse(value)
        return Domain.OR(
            Domain(
                "placeholder_code",
                "=ilike",
                root.name
                + ("" if operator in ["in", "any"] and not root.parent_id else "%"),
            )
            for root in roots
        )

    def _search_panel_get_domain_image(
        self,
        field_name,
        domain,
        set_count=False,
        limit=False,
    ):
        if field_name != "root_id" or set_count:
            return super()._search_panel_get_domain_image(
                field_name,
                domain,
                set_count,
                limit,
            )

        domain = Domain(domain)
        if domain.is_false():
            return {}

        query_account = self.env["account.account"]._search(
            domain,
            limit=limit,
        )
        placeholder_code_alias = self.env["account.account"]._field_to_sql(
            "account_account",
            "code",
            query_account,
        )

        placeholder_codes = self.env.execute_query(
            query_account.select(placeholder_code_alias),
        )
        return {
            (root := self.env["account.root"]._from_account_code(code)).id: {
                "id": root.id,
                "display_name": root.display_name,
            }
            for (code,) in placeholder_codes
            if code
        }

    @api.depends("code")
    def _compute_account_type_and_tags(self):
        accounts_to_process = self.filtered(
            lambda account: (
                account.code and (not account.account_type or not account.tag_ids)
            ),
        )
        self._update_from_closest_parent_account(
            accounts_to_process,
            {"account_type": "asset_current", "tag_ids": []},
        )

    def _update_from_closest_parent_account(self, accounts_to_process, field_defaults):
        field_names = list(field_defaults)
        assert all(field_name in self._fields for field_name in field_names)

        all_accounts = self.search_read(
            domain=self._check_company_domain(self.env.company),
            fields=["code", *field_names],
            order="code",
        )
        accounts_with_values = {}
        for account in all_accounts:
            accounts_with_values[account["code"]] = {
                field_name: account[field_name] for field_name in field_names
            }
        codes_list = list(accounts_with_values.keys())
        for account in accounts_to_process:
            closest_index = bisect_left(codes_list, account.code) - 1
            parent_values = (
                accounts_with_values[codes_list[closest_index]]
                if closest_index != -1
                else None
            )
            for field_name, default_value in field_defaults.items():
                if account[field_name]:
                    continue
                account[field_name] = (
                    parent_values[field_name] if parent_values else default_value
                )

    @api.depends("account_type")
    def _compute_include_initial_balance(self):
        for account in self:
            account.include_initial_balance = (
                account.internal_group not in ["income", "expense"]
                and account.account_type != "equity_unaffected"
            )

    def _search_include_initial_balance(self, operator, value):
        if operator != "in":
            return NotImplemented
        return [
            ("internal_group", "not in", ["income", "expense"]),
            ("account_type", "!=", "equity_unaffected"),
        ]

    def _get_internal_group(self, account_type):
        return account_type.split("_", maxsplit=1)[0]

    @api.depends("account_type")
    def _compute_internal_group(self):
        for account in self:
            account.internal_group = (
                account.account_type
                and account._get_internal_group(account.account_type)
            )

    def _search_internal_group(self, operator, value):
        if operator != "in":
            return NotImplemented
        return Domain.OR(
            Domain("account_type", "=like", self._get_internal_group(v) + "%")
            for v in value
        )

    @api.depends("account_type")
    def _compute_reconcile(self):
        for account in self:
            if account.internal_group in ("income", "expense", "equity"):
                account.reconcile = False
            elif account.account_type in (
                "asset_receivable",
                "liability_payable",
            ):
                account.reconcile = True
            elif account.account_type in (
                "asset_cash",
                "liability_credit_card",
                "off_balance",
            ):
                account.reconcile = False

    @api.depends_context("company")
    def _compute_company_currency_id(self):
        self.company_currency_id = self.env.company.currency_id

    @api.depends_context("company")
    @api.depends("code")
    def _compute_display_name(self):
        for account in self:
            account.display_name = (
                f"{account.code} {account.name}" if account.code else account.name
            )

    @api.onchange("account_type")
    def _onchange_account_type(self):
        pass

    @api.onchange("name")
    def _onchange_name(self):
        code, name = self._split_code_name(self.name)
        if code and not self.code:
            self.name = name
            self.code = code

    def _split_code_name(self, code_name):
        code, name = ACCOUNT_REGEX.match(code_name or "").groups()
        return code, name.strip()

    @api.model
    def _search_display_name(self, operator, value):
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        if operator == "in":
            return [
                "|",
                ("code", "in", [(name or "").split(" ")[0] for name in value]),
                ("name", "in", value),
            ]
        if isinstance(value, str):
            name = value or ""
            return [
                "|",
                "|",
                ("code", "=like", name.split(" ")[0] + "%"),
                ("name", operator, name),
                ("description", "ilike", name),
            ]
        return NotImplemented

    @api.model
    def _search_new_account_code(self, start_code, cache=None):
        if cache is None:
            cache = {start_code}

        company_domain = [
            "|",
            ("company_ids", "parent_of", self.env.company.id),
            ("company_ids", "child_of", self.env.company.id),
        ]

        def code_is_available(new_code):
            return new_code not in cache and not self.with_context(
                active_test=False
            ).sudo().search_count(
                [("code", "=", new_code), *company_domain],
                limit=1,
            )

        if code_is_available(start_code):
            return start_code

        start_str, digits_str, end_str = ACCOUNT_CODE_NUMBER_REGEX.match(
            start_code
        ).groups()

        if digits_str != "":
            d, n = len(digits_str), int(digits_str)
            code_len = len(start_str) + d + len(end_str)
            existing_codes = (
                self.with_context(active_test=False)
                .sudo()
                .search_read(company_domain, fields=["code"])
            )
            occupied = set()
            for existing in existing_codes:
                code = existing["code"]
                if (
                    code
                    and len(code) == code_len
                    and code.startswith(start_str)
                    and code.endswith(end_str)
                ):
                    middle = code[len(start_str) : code_len - len(end_str)]
                    if middle.isdigit():
                        occupied.add(int(middle))
            for num in range(n + 1, 10**d):
                if num in occupied:
                    continue
                new_code = f"{start_str}{num:0{d}}{end_str}"
                if new_code not in cache:
                    return new_code

        for num in range(99):
            if code_is_available(
                new_code := f"{start_code}.copy{(num and num + 1) or ''}"
            ):
                return new_code

        raise UserError(_("Cannot generate an unused account code."))

    @api.model
    def default_get(self, fields):
        context = {}
        if "name" in fields or "code" in fields:
            default_name = self.env.context.get("default_name")
            default_code = self.env.context.get("default_code")
            if default_name and not default_code:
                is_numeric_code = False
                with contextlib.suppress(ValueError):
                    is_numeric_code = bool(int(default_name))
                if is_numeric_code:
                    context.update(
                        {
                            "default_name": False,
                            "default_code": default_name,
                        }
                    )

        defaults = super(
            AccountAccount,
            self.with_context(**context),
        ).default_get(fields)

        if "code_mapping_ids" in fields and "code_mapping_ids" not in defaults:
            defaults["code_mapping_ids"] = [
                Command.create({"company_id": c.id}) for c in self.env.user.company_ids
            ]

        return defaults

    @api.model
    def name_create(self, name):
        if "import_file" in self.env.context:
            code, name = self._split_code_name(name)
            record = self.create({"code": code, "name": name})
            return record.id, record.display_name
        raise ValidationError(
            _("Please create new accounts from the Chart of Accounts menu."),
        )

    def _sort_vals_for_company_grouping(self, vals_list):
        first_seen = {}
        for index, vals in enumerate(vals_list):
            first_seen.setdefault(repr(vals.get("company_ids", [])), index)
        return sorted(
            vals_list,
            key=lambda vals: first_seen[repr(vals.get("company_ids", []))],
        )

    def _update_vals_with_code(self, vals, companies, cache):
        if "prefix" in vals:
            prefix = vals.pop("prefix") or ""
            digits = vals.pop("code_digits")
            start_code = (
                prefix.ljust(digits - 1, "0") + "1" if len(prefix) < digits else prefix
            )
            vals["code"] = self.with_company(
                companies[0],
            )._search_new_account_code(start_code, cache)
            cache.add(vals["code"])

        if "code" not in vals:
            for mapping_command in vals.get("code_mapping_ids", []):
                match mapping_command:
                    case (
                        Command.CREATE,
                        _,
                        {
                            "company_id": company_id,
                            "code": code,
                        },
                    ) if company_id == companies[0].id:
                        vals["code"] = code
                        break

    @api.model_create_multi
    def create(self, vals_list):
        records_list = []
        vals_list = self._sort_vals_for_company_grouping(vals_list)

        for company_ids, vals_list_for_company in itertools.groupby(
            vals_list,
            lambda v: v.get("company_ids", []),
        ):
            cache = set()
            vals_list_for_company = list(vals_list_for_company)

            company_ids = self._fields["company_ids"].convert_to_cache(
                company_ids,
                self.browse(),
            )
            companies = self.env["res.company"].browse(company_ids)
            if self.env.company in companies or not companies:
                companies = self.env.company | companies

            for vals in vals_list_for_company:
                self._update_vals_with_code(vals, companies, cache)

            new_accounts = super(
                AccountAccount,
                self.with_context(
                    allowed_company_ids=companies.ids,
                    defer_account_code_checks=True,
                    default_code_mapping_ids=self.env.context.get(
                        "default_code_mapping_ids",
                        [],
                    ),
                ),
            ).create(vals_list_for_company)

            records_list.append(new_accounts)

        records = self.env["account.account"].union(*records_list)
        records.flush_recordset()
        records.invalidate_recordset(fnames=["code", "code_store"])
        records._check_code_is_unique()
        return records

    def write(self, vals):
        res = super(
            AccountAccount,
            self.with_context(
                defer_account_code_checks=True,
                prefetch_fields=not any(
                    field in vals for field in ["code", "account_type"]
                ),
            ),
        ).write(vals)

        if (
            not self.env.context.get("defer_account_code_checks")
            and {"company_ids", "code", "code_mapping_ids"} & vals.keys()
        ):
            if "company_ids" in vals:
                self.invalidate_recordset(fnames=["company_ids"])
            self._check_code_is_unique()

        return res

    def _check_code_is_unique(self):
        for account in self.sudo():
            for company in account.company_ids.root_id:
                acc_co = account.with_company(company)
                code = acc_co.code
                if not code:
                    raise ValidationError(
                        _(
                            "The code must be set for every company to which "
                            "this account belongs.",
                        )
                    )

        account_ids_to_check_by_company = defaultdict(list)
        for account in self.sudo():
            for company in account.company_ids:
                account_ids_to_check_by_company[company].append(account.id)

        for company, account_ids in account_ids_to_check_by_company.items():
            accounts = self.browse(account_ids).with_prefetch(self.ids).sudo()

            accounts_by_code = accounts.with_company(company).grouped("code")
            duplicate_codes = None
            if len(accounts_by_code) < len(accounts):
                duplicate_codes = [
                    code for code, accs in accounts_by_code.items() if len(accs) > 1
                ]

            # One query per company, not per record: `code` is company-dependent
            # and is searched under that company's context, which a single
            # query over every company cannot express.
            elif duplicates := (
                self.with_company(company)
                .sudo()
                .with_context(active_test=False)
                .search_fetch(  # pylint: disable=n-plus-one-query
                    [
                        ("code", "in", list(accounts_by_code)),
                        ("id", "not in", self.ids),
                        "|",
                        ("company_ids", "parent_of", company.ids),
                        ("company_ids", "child_of", company.ids),
                    ],
                    ["code_store"],
                )
            ):
                duplicate_codes = duplicates.mapped("code")
            if duplicate_codes:
                raise ValidationError(
                    _(
                        "Account codes must be unique. You can't create "
                        "accounts with these duplicate codes: %s",
                        ", ".join(duplicate_codes),
                    )
                )

    def _load_records_write(self, values):
        if "prefix" in values:
            del values["code_digits"]
            del values["prefix"]
        super()._load_records_write(values)

    def copy_data(self, default=None):
        vals_list = super().copy_data(default)
        default = default or {}
        cache = defaultdict(set)

        for account, vals in zip(self, vals_list, strict=True):
            company_ids = self._fields["company_ids"].convert_to_cache(
                vals["company_ids"],
                self.browse(),
            )
            companies = self.env["res.company"].browse(company_ids)

            if "code_mapping_ids" not in default and (
                "code" not in default or len(companies) > 1
            ):
                companies_to_get_new_codes = (
                    companies if "code" not in default else companies[1:]
                )
                vals["code_mapping_ids"] = []

                for company in companies_to_get_new_codes:
                    start_code = (
                        account.with_company(company).code
                        or account.with_company(
                            account.company_ids[0],
                        ).code
                    )
                    new_code = account.with_company(
                        company,
                    )._search_new_account_code(
                        start_code,
                        cache[company.id],
                    )
                    vals["code_mapping_ids"].append(
                        Command.create(
                            {
                                "company_id": company.id,
                                "code": new_code,
                            }
                        ),
                    )
                    cache[company.id].add(new_code)

            if "name" not in default:
                vals["name"] = self.env._(
                    "%s (copy)",
                    account.name or "",
                )

        return vals_list

    def copy_translations(self, new, excluded=()):
        super().copy_translations(new, excluded=(*excluded, "name"))
        self._copy_translations_of_renamed_field(
            new,
            "name",
            lambda record, term: record.env._("%s (copy)", term or ""),
        )
