from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, Query

_debug = DebugLog(__name__)


class AccountAccount(models.Model):
    _name = "account.account"
    _inherit = [
        "account.account",
        "mixin.company.split",
        "mixin.mail.thread",
        "mixin.mail.activity",
    ]

    name = fields.Char(tracking=True)
    currency_id = fields.Many2one(tracking=True)
    active = fields.Boolean(tracking=True)
    account_type = fields.Selection(tracking=True)
    reconcile = fields.Boolean(tracking=True)
    note = fields.Text(tracking=True)
    tag_ids = fields.Many2many(tracking=True)

    company_fiscal_country_code = fields.Char(
        compute="_compute_company_fiscal_country_code"
    )
    tax_ids = fields.Many2many(
        comodel_name="account.tax",
        relation="account_account_tax_default_rel",
        column1="account_id",
        column2="tax_id",
        string="Default Taxes",
        context={"append_fields": ["type_tax_use", "company_ids"]},
        check_company=True,
    )
    group_id = fields.Many2one(
        comodel_name="account.group",
        compute="_compute_group_id",
        help="Account prefixes can determine account groups.",
    )
    used = fields.Boolean(
        compute="_compute_used",
        search="_search_used",
    )
    opening_debit = fields.Monetary(
        currency_field="company_currency_id",
        compute="_compute_opening_debit_credit",
        inverse="_inverse_opening_debit",
    )
    opening_credit = fields.Monetary(
        currency_field="company_currency_id",
        compute="_compute_opening_debit_credit",
        inverse="_inverse_opening_credit",
    )
    opening_balance = fields.Monetary(
        currency_field="company_currency_id",
        compute="_compute_opening_debit_credit",
        inverse="_inverse_opening_balance",
    )
    current_balance = fields.Float(compute="_compute_current_balance")
    related_taxes_amount = fields.Integer(compute="_compute_related_taxes_amount")

    @api.constrains("reconcile", "account_type", "tax_ids")
    def _constrains_reconcile(self):
        for record in self:
            if record.account_type == "off_balance":
                if record.reconcile:
                    raise UserError(
                        _("An Off-Balance account can not be reconcilable"),
                    )
                if record.tax_ids:
                    raise UserError(
                        _("An Off-Balance account can not have taxes"),
                    )

    @api.constrains("currency_id")
    @_debug.perf.timed
    def _check_journal_consistency(self):
        if not self:
            return

        journals = (
            self.env["account.journal"]
            .sudo()
            .search(
                [("currency_id", "!=", False), ("default_account_id", "in", self.ids)]
            )
        )
        mismatched = [
            (journal.default_account_id, journal)
            for journal in journals
            if journal.currency_id != journal.company_id.currency_id
            # an account without a currency matched nothing in SQL: NULL != x is no row
            and journal.default_account_id.currency_id
            and journal.default_account_id.currency_id != journal.currency_id
        ]
        if not mismatched:
            channels = (
                self.env["account.payment.channel"]
                .sudo()
                .search(
                    [
                        ("payment_account_id", "in", self.ids),
                        ("journal_id.currency_id", "!=", False),
                        (
                            "payment_method_id.payment_type",
                            "in",
                            ("inbound", "outbound"),
                        ),
                    ]
                )
            )
            mismatched = [
                (channel.payment_account_id, channel.journal_id)
                for channel in channels
                if channel.journal_id.currency_id
                != channel.journal_id.company_id.currency_id
                and channel.payment_account_id.currency_id
                and channel.payment_account_id.currency_id
                != channel.journal_id.currency_id
            ]
        _debug.logic(
            "journal_currency_checked",
            accounts=self,
            mismatch=bool(mismatched),
        )
        if mismatched:
            account, journal = mismatched[0]
            raise ValidationError(
                _(
                    "The foreign currency set on the journal '%(journal)s' and "
                    "the account '%(account)s' must be the same.",
                    journal=journal.display_name,
                    account=account.display_name,
                )
            )

    @api.constrains("company_ids")
    @_debug.perf.timed
    def _check_company_move_line_consistency(self):
        self.invalidate_recordset(fnames=["company_ids"])
        companies_by_account = defaultdict(set)
        for account, company in (
            self.env["account.move.line"]
            .sudo()
            ._read_group([("account_id", "in", self.ids)], ["account_id", "company_id"])
        ):
            companies_by_account[account.id].add(company)
        for companies, accounts in self.grouped(
            lambda a: a.company_ids,
        ).items():
            if any(
                not (companies & company.parent_ids)
                for account in accounts
                for company in companies_by_account[account.id]
            ):
                raise UserError(
                    _(
                        "You can't unlink this company from this account since "
                        "there are some journal items linked to it.",
                    )
                )

    @api.constrains("account_type")
    @_debug.perf.timed
    def _check_account_type_sales_purchase_journal(self):
        if not self:
            return

        used = (
            self.env["account.journal"]
            .sudo()
            .search_count(
                [
                    ("type", "in", ("sale", "purchase")),
                    ("default_account_id", "in", self.ids),
                    (
                        "default_account_id.account_type",
                        "in",
                        ("asset_receivable", "liability_payable"),
                    ),
                ],
                limit=1,
            )
        )
        if used:
            _debug.logic(
                "account_type_rejected", accounts=self, reason="sale_purchase_journal"
            )
            raise ValidationError(
                _(
                    "The account is already in use in a 'sale' or 'purchase' "
                    "journal. This means that the account's type couldn't be "
                    "'receivable' or 'payable'.",
                )
            )

    @api.constrains("account_type")
    @_debug.perf.timed
    def _check_account_is_bank_journal_bank_account(self):
        used = (
            self.env["account.journal"]
            .sudo()
            .search_count(
                [
                    ("default_account_id", "in", self.ids),
                    (
                        "default_account_id.account_type",
                        "in",
                        ("asset_receivable", "liability_payable"),
                    ),
                ],
                limit=1,
            )
        )
        if used:
            _debug.logic(
                "account_type_rejected", accounts=self, reason="bank_journal_account"
            )
            raise ValidationError(
                _(
                    "You cannot change the type of an account set as Bank "
                    "Account on a journal to Receivable or Payable.",
                )
            )

    @api.model
    @api.readonly
    @_debug.perf.timed
    def name_search(self, name="", domain=None, operator="ilike", limit=100):
        move_type = self.env.context.get("move_type")
        if _debug.logic.enabled and not move_type:
            _debug.logic("name_search_fallback", reason="no_move_type")
        if not move_type:
            return super().name_search(name, domain, operator, limit)

        domain = domain or []
        partner = self.env.context.get("partner_id")
        suggested_accounts = (
            self._order_accounts_by_frequency_for_partner(
                self.env.company.id,
                partner,
                move_type,
            )
            if partner
            else []
        )
        _debug.logic(
            "suggested_accounts_resolved",
            partner=partner,
            move_type=move_type,
            suggested=len(suggested_accounts),
            shortcut=not name and bool(suggested_accounts),
        )

        if not name and suggested_accounts:
            display_by_id = {
                record.id: record.display_name
                for record in self.search_fetch(
                    Domain.AND([[("id", "in", suggested_accounts)], domain]),
                    ["display_name"],
                )
            }
            return [
                (account_id, display_by_id[account_id])
                for account_id in suggested_accounts
                if account_id in display_by_id
            ][:limit]

        digit_in_search_term = any(c.isdigit() for c in name)
        search_domain = Domain("display_name", "ilike", name) if name else []

        if digit_in_search_term:
            domain = Domain.AND([search_domain, domain])
        else:
            allowed_account_types = self._get_name_search_account_types(move_type)
            type_domain = (
                [("account_type", "in", allowed_account_types)]
                if allowed_account_types
                else []
            )
            domain = Domain.AND([search_domain, type_domain, domain])

        _debug.logic(
            "name_search_domain_chosen",
            move_type=move_type,
            by_digits=digit_in_search_term,
            limit=limit,
        )
        records = self.with_context(
            preferred_account_ids=suggested_accounts,
        ).search_fetch(domain, ["display_name"], limit=limit)
        return [(record.id, record.display_name) for record in records]

    @_debug.perf.timed
    def write(self, vals):
        _debug.lifecycle("write", records=self, fields=sorted(vals))
        _debug.logic(
            "write_guards",
            accounts=self,
            reconcile=vals.get("reconcile"),
            reconcile_toggled="reconcile" in vals,
            currency_check=bool(vals.get("currency_id")),
            deprecate_check=vals.get("active") is False,
        )
        if "reconcile" in vals:
            if vals["reconcile"]:
                self.filtered(
                    lambda r: not r.reconcile,
                )._toggle_reconcile_to_true()
            else:
                self.filtered(
                    lambda r: r.reconcile,
                )._toggle_reconcile_to_false()

        if vals.get("currency_id") and self.env["account.move.line"].search_count(
            [
                ("account_id", "in", self.ids),
                ("currency_id", "not in", (False, vals["currency_id"])),
            ],
            limit=1,
        ):
            raise UserError(
                _(
                    "You cannot set a currency on this account as it "
                    "already has some journal entries having a different "
                    "foreign currency.",
                )
            )

        if vals.get("active") is False and self.env[
            "account.tax.repartition.line"
        ].search_count(
            [("account_id", "in", self.ids)],
            limit=1,
        ):
            raise UserError(
                _(
                    "You cannot deprecate an account that is used in a "
                    "tax distribution.",
                )
            )

        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    @_debug.perf.timed
    def _unlink_except_contains_journal_items(self):
        _debug.lifecycle("_unlink_except_contains_journal_items", records=self)
        if (
            self.env["account.move.line"]
            .sudo()
            .search_count(
                [("account_id", "in", self.ids)],
                limit=1,
            )
        ):
            raise UserError(
                _(
                    "You cannot perform this action on an account that "
                    "contains journal items.",
                )
            )

    @api.ondelete(at_uninstall=False)
    @_debug.perf.timed
    def _unlink_except_linked_to_fiscal_position(self):
        _debug.lifecycle("_unlink_except_linked_to_fiscal_position", records=self)
        if self.env["account.fiscal.position.account"].search_count(
            [
                "|",
                ("account_src_id", "in", self.ids),
                ("account_dest_id", "in", self.ids),
            ],
            limit=1,
        ):
            raise UserError(
                _(
                    'You cannot remove/deactivate the accounts "%s" which '
                    "are set on the account mapping of a fiscal position.",
                    ", ".join(f"{a.code} - {a.name}" for a in self),
                )
            )

    @api.ondelete(at_uninstall=False)
    @_debug.perf.timed
    def _unlink_except_linked_to_tax_repartition_line(self):
        _debug.lifecycle("_unlink_except_linked_to_tax_repartition_line", records=self)
        if self.env["account.tax.repartition.line"].search_count(
            [("account_id", "in", self.ids)],
            limit=1,
        ):
            raise UserError(
                _(
                    'You cannot remove/deactivate the accounts "%s" which '
                    "are set on a tax repartition line.",
                    ", ".join(f"{a.code} - {a.name}" for a in self),
                )
            )

    @api.depends_context("company")
    def _compute_company_fiscal_country_code(self):
        self.company_fiscal_country_code = (
            self.env.company.account_fiscal_country_id.code
        )

    @api.depends_context("company")
    @api.depends("code")
    @_debug.perf.timed
    def _compute_group_id(self):
        accounts_with_code = self.filtered(lambda a: a.code)
        _debug.pipeline(
            "group_codes_scope",
            accounts=self,
            with_code=accounts_with_code,
        )

        (self - accounts_with_code).group_id = False

        if not accounts_with_code:
            return

        codes = accounts_with_code.mapped("code")
        account_code_values = SQL(
            ",".join(["(%s)"] * len(codes)),
            *codes,
        )
        results = self.env.execute_query(
            SQL(
                """
                 SELECT DISTINCT ON (account_code.code)
                        account_code.code,
                        agroup.id AS group_id
                   FROM (VALUES %(account_code_values)s)
                        AS account_code (code)
              LEFT JOIN account_group agroup
                     ON agroup.code_prefix_start
                        <= LEFT(account_code.code,
                                char_length(agroup.code_prefix_start))
                        AND agroup.code_prefix_end
                        >= LEFT(account_code.code,
                                char_length(agroup.code_prefix_end))
                        AND agroup.company_id = %(root_company_id)s
               ORDER BY account_code.code,
                    char_length(agroup.code_prefix_start) DESC, agroup.id
            """,
                account_code_values=account_code_values,
                root_company_id=self.env.company.root_id.id,
            )
        )
        group_by_code = dict(results)
        if _debug.pipeline.enabled:
            _debug.pipeline(
                "groups_resolved",
                codes=len(codes),
                grouped=sum(1 for group_id in group_by_code.values() if group_id),
                root_company=self.env.company.root_id,
            )

        for account in accounts_with_code:
            account.group_id = group_by_code[account.code]

    def _compute_used(self):
        used = set(self._get_used_account_ids(self.ids))
        for record in self:
            record.used = record.id in used

    @api.depends_context("company")
    def _compute_current_balance(self):
        balances = {
            account.id: balance
            for account, balance in self.env["account.move.line"]._read_group(
                domain=[
                    ("account_id", "in", self.ids),
                    ("parent_state", "=", "posted"),
                    ("company_id", "child_of", self.env.company.id),
                ],
                groupby=["account_id"],
                aggregates=["balance:sum"],
            )
        }
        for record in self:
            record.current_balance = balances.get(record.id, 0)

    @api.depends_context("company")
    def _compute_related_taxes_amount(self):
        counts = dict(
            self.env["account.tax.repartition.line"]._read_group(
                domain=[
                    ("account_id", "in", self.ids),
                    *self.env["account.tax"]._check_company_domain(
                        self.env.company,
                    ),
                ],
                groupby=["account_id"],
                aggregates=["tax_id:count_distinct"],
            )
        )
        for record in self:
            record.related_taxes_amount = counts.get(record, 0)

    @api.depends_context("company")
    @_debug.perf.timed
    def _compute_opening_debit_credit(self):
        self.opening_debit = 0
        self.opening_credit = 0
        self.opening_balance = 0
        opening_move = self.env.company.account_opening_move_id
        _debug.logic(
            "opening_move_source",
            accounts=self,
            move=opening_move,
            skipped=not self.ids or not opening_move,
        )
        if not self.ids or not opening_move:
            return
        self.env.cr.execute(
            SQL(
                """
            SELECT line.account_id,
                   SUM(line.balance) AS balance,
                   SUM(line.debit) AS debit,
                   SUM(line.credit) AS credit
              FROM account_move_line line
             WHERE line.move_id = %(opening_move_id)s
               AND line.account_id IN %(account_ids)s
             GROUP BY line.account_id
            """,
                account_ids=tuple(self.ids),
                opening_move_id=opening_move.id,
            )
        )
        result = {r["account_id"]: r for r in self.env.cr.dictfetchall()}
        _debug.perf.count("opening_balance_rows", rows=len(result))
        for record in self:
            res = result.get(record.id) or {
                "debit": 0,
                "credit": 0,
                "balance": 0,
            }
            record.opening_debit = res["debit"]
            record.opening_credit = res["credit"]
            record.opening_balance = res["balance"]

    @api.depends_context("company", "formatted_display_name", "uid")
    @api.depends("code")
    @_debug.perf.timed
    def _compute_display_name(self):
        formatted_display_name = self.env.context.get(
            "formatted_display_name",
        )
        new_line = "\n"
        preferred_account_ids = self.env.context.get(
            "preferred_account_ids",
            [],
        )
        _debug.logic(
            "display_name_mode",
            accounts=self,
            formatted=bool(formatted_display_name),
            preferred_in_context=bool(preferred_account_ids),
        )
        if (
            (move_type := self.env.context.get("move_type"))
            and (partner := self.env.context.get("partner_id"))
            and not preferred_account_ids
        ):
            preferred_account_ids = self._order_accounts_by_frequency_for_partner(
                self.env.company.id,
                partner,
                move_type,
            )
        _debug.logic(
            "display_name_preferred",
            preferred=len(preferred_account_ids or ()),
        )
        for account in self:
            if formatted_display_name and account.code:
                suggested = (
                    f" `{_('Suggested')}`"
                    if account.id in preferred_account_ids
                    else ""
                )
                desc = (
                    f"{new_line}--{account.description}--"
                    if account.description
                    else ""
                )
                code_part = (
                    account.code
                    if self.env.user.has_group("account.group_account_readonly")
                    else ""
                )
                account.display_name = f"{code_part} {account.name}{suggested}{desc}"
            else:
                account.display_name = (
                    f"{account.code} {account.name}"
                    if account.code
                    and self.env.user.has_group(
                        "account.group_account_readonly",
                    )
                    else account.name
                )

    @_debug.perf.timed
    def _search_used(self, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented
        return [("id", operator, self._get_used_account_ids())]

    def _inverse_opening_debit(self):
        for record in self:
            record._set_opening_debit_credit(record.opening_debit, "debit")

    def _inverse_opening_credit(self):
        for record in self:
            record._set_opening_debit_credit(record.opening_credit, "credit")

    def _inverse_opening_balance(self):
        for account in self:
            balance = account.opening_balance
            account._set_opening_debit_credit(
                abs(balance) if balance > 0.0 else 0.0,
                "debit",
            )
            account._set_opening_debit_credit(
                abs(balance) if balance < 0.0 else 0.0,
                "credit",
            )

    def _set_opening_debit_credit(self, amount, field):
        self.check_singleton()
        if "import_account_opening_balance" not in self.env.cr.precommit.data:
            data = self.env.cr.precommit.data["import_account_opening_balance"] = {}
            self.env.cr.precommit.add(
                self._load_precommit_update_opening_move,
            )
        else:
            data = self.env.cr.precommit.data["import_account_opening_balance"]
        data.setdefault(self.env.company.id, {}).setdefault(
            self.id,
            [None, None],
        )
        index = 0 if field == "debit" else 1
        data[self.env.company.id][self.id][index] = amount

    @api.onchange("account_type")
    def _onchange_account_type(self):
        if self.account_type == "off_balance":
            self.tax_ids = False

    @api.model
    @_debug.perf.timed
    def _load_precommit_update_opening_move(self):
        data = self.env.cr.precommit.data.pop(
            "import_account_opening_balance",
            {},
        )

        for company_id, account_values in data.items():
            self.env["res.company"].browse(company_id)._update_opening_move(
                {
                    self.env["account.account"].browse(account_id): values
                    for account_id, values in account_values.items()
                }
            )

        self.env.flush_all()

    def _toggle_reconcile_to_true(self):
        if not self.ids:
            return
        self.env["account.move.line"].invalidate_model(
            [
                "amount_residual",
                "amount_residual_currency",
                "reconciled",
            ]
        )
        query = """
            UPDATE account_move_line SET
                reconciled = CASE WHEN debit = 0 AND credit = 0
                    AND amount_currency = 0
                    THEN true ELSE false END,
                amount_residual = (debit-credit),
                amount_residual_currency = amount_currency
            WHERE full_reconcile_id IS NULL and account_id = ANY(%s)
        """
        self.env.cr.execute(query, [list(self.ids)])
        _debug.lifecycle(
            "reconcile_true_reset", account=self, rowcount=self.env.cr.rowcount
        )

    @_debug.perf.timed
    def _toggle_reconcile_to_false(self):
        if not self.ids:
            return
        partial_lines_count = self.env["account.move.line"].search_count(
            [
                ("account_id", "in", self.ids),
                ("full_reconcile_id", "=", False),
                ("|"),
                ("matched_debit_ids", "!=", False),
                ("matched_credit_ids", "!=", False),
            ],
            limit=1,
        )
        _debug.logic(
            "partial_reconciles_pending",
            accounts=self,
            pending=partial_lines_count,
        )
        if partial_lines_count > 0:
            raise UserError(
                _(
                    "You cannot switch an account to prevent the reconciliation "
                    "if some partial reconciliations are still pending.",
                )
            )

        self.env["account.move.line"].invalidate_model(
            [
                "amount_residual",
                "amount_residual_currency",
            ]
        )
        query = """
            UPDATE account_move_line
                SET amount_residual = 0, amount_residual_currency = 0
            WHERE full_reconcile_id IS NULL AND account_id = ANY(%s)
        """
        self.env.cr.execute(query, [list(self.ids)])
        _debug.lifecycle(
            "reconcile_false_zeroed", account=self, rowcount=self.env.cr.rowcount
        )

    def _get_used_account_ids(self, account_ids=None):
        rows = self.env.execute_query(
            SQL(
                """
                SELECT account.id
                  FROM account_account account
                 WHERE EXISTS (
                           SELECT 1 FROM account_move_line aml
                            WHERE aml.account_id = account.id
                       )
                       %s
                """,
                SQL("AND account.id = ANY(%s)", list(account_ids))
                if account_ids is not None
                else SQL(),
            )
        )
        _debug.perf.count("used_accounts_fetched", rows=len(rows))
        return [r[0] for r in rows]

    @api.model
    @_debug.perf.timed
    def _get_most_frequent_accounts_for_partner(
        self,
        company_id,
        partner_id,
        move_type,
        filter_never_used_accounts=False,
        limit=None,
    ):
        domain = [
            *self.env["account.move.line"]._check_company_domain(company_id),
            ("partner_id", "=", partner_id),
            ("account_id.active", "=", True),
            (
                "date",
                ">=",
                fields.Date.add(
                    fields.Date.today(),
                    days=-365 * 2,
                ),
            ),
        ]
        if move_type in self.env["account.move"].get_inbound_types(
            include_receipts=True,
        ):
            domain.append(("account_id.internal_group", "=", "income"))
        elif move_type in self.env["account.move"].get_outbound_types(
            include_receipts=True,
        ):
            domain.append(("account_id.internal_group", "=", "expense"))

        query = self.env["account.move.line"]._search(
            domain,
            bypass_access=True,
        )
        if not filter_never_used_accounts:
            _kind, rhs_table, condition = query._joins["account_move_line__account_id"]
            query._joins["account_move_line__account_id"] = (
                SQL("RIGHT JOIN"),
                rhs_table,
                condition,
            )
        if _debug.logic.enabled:
            _debug.logic(
                "frequency_query_shaped",
                company=company_id,
                partner=partner_id,
                move_type=move_type,
                internal_group=(
                    domain[-1][2]
                    if domain[-1][0] == "account_id.internal_group"
                    else None
                ),
                right_join=not filter_never_used_accounts,
                limit=limit,
            )

        company = self.env["res.company"].browse(company_id)
        code_sql = self.with_company(company)._field_to_sql(
            "account_move_line__account_id",
            "code",
            query,
        )

        return [
            r[0]
            for r in self.env.execute_query(
                SQL(
                    """
                SELECT account_move_line__account_id.id
                  FROM %(from_clause)s
                 WHERE %(where_clause)s
              GROUP BY account_move_line__account_id.id
              ORDER BY COUNT(account_move_line.id) DESC,
                       MAX(%(code_sql)s)
                %(limit_clause)s
            """,
                    from_clause=query.from_clause,
                    where_clause=query.where_clause or SQL("TRUE"),
                    code_sql=code_sql,
                    limit_clause=SQL("LIMIT %s", limit) if limit else SQL(),
                )
            )
        ]

    @api.model
    def _get_most_frequent_account_for_partner(
        self,
        company_id,
        partner_id,
        move_type=None,
    ):
        cache = self.env.cr.cache.setdefault("most_frequent_accounts_for_partner", {})
        key = (company_id, partner_id, move_type)

        if key not in cache:
            most_frequent_account = self._get_most_frequent_accounts_for_partner(
                company_id,
                partner_id,
                move_type,
                filter_never_used_accounts=True,
                limit=1,
            )
            cache[key] = most_frequent_account[0] if most_frequent_account else False

        return cache[key]

    @api.model
    def _order_accounts_by_frequency_for_partner(
        self,
        company_id,
        partner_id,
        move_type=None,
    ):
        return self._get_most_frequent_accounts_for_partner(
            company_id,
            partner_id,
            move_type,
        )

    @_debug.perf.timed
    def _order_to_sql(
        self,
        order: str,
        query: Query,
        alias: (str | None) = None,
        reverse: bool = False,
    ) -> SQL:
        sql_order = super()._order_to_sql(order, query, alias, reverse)

        if order == self._order and (
            preferred_account_type := self.env.context.get(
                "preferred_account_type",
            )
        ):
            sql_order = SQL(
                "%(field_sql)s = %(preferred_account_type)s "
                "%(direction)s, %(base_order)s",
                field_sql=self._field_to_sql(
                    alias or self._table,
                    "account_type",
                ),
                preferred_account_type=preferred_account_type,
                direction=SQL("ASC") if reverse else SQL("DESC"),
                base_order=sql_order,
            )
        if order == self._order and (
            preferred_account_ids := self.env.context.get(
                "preferred_account_ids",
            )
        ):
            sql_order = SQL(
                "%(alias)s.id in %(preferred_account_ids)s "
                "%(direction)s, %(base_order)s",
                alias=SQL.identifier(alias or self._table),
                preferred_account_ids=tuple(
                    map(int, preferred_account_ids),
                ),
                direction=SQL("ASC") if reverse else SQL("DESC"),
                base_order=sql_order,
            )
        if _debug.logic.enabled and order == self._order:
            _debug.logic(
                "account_order_preferred",
                preferred_type=self.env.context.get("preferred_account_type"),
                preferred_ids=bool(self.env.context.get("preferred_account_ids")),
                reverse=reverse,
            )
        return sql_order

    def _get_name_search_account_types(self, move_type):
        move_type_accounts = {
            "out": ["income"],
            "in": ["expense", "asset_fixed", "expense_direct_cost"],
        }
        return move_type_accounts.get(move_type.split("_")[0])

    @_debug.perf.timed
    def action_view_related_taxes(self):
        _debug.lifecycle("action_view_related_taxes", records=self)
        related_taxes_ids = (
            self.env["account.tax"]
            .search(
                [
                    ("repartition_line_ids.account_id", "=", self.id),
                ]
            )
            .ids
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Taxes"),
            "res_model": "account.tax",
            "views": [[False, "list"], [False, "form"]],
            "domain": [("id", "in", related_taxes_ids)],
        }

    @_debug.perf.timed
    def action_view_reconcile(self):
        _debug.lifecycle("action_view_reconcile", records=self)
        self.check_singleton()
        return self.env["account.move.line"]._action_view_unreconciled(
            extra_domain=[("account_id", "=", self.id)],
        )

    @api.model
    def get_import_templates(self):
        return [
            {
                "label": _("Import Template for Chart of Accounts"),
                "template": "/account/static/xls/coa_import_template.xlsx",
            }
        ]

    def _merge_method(self, destination, source):
        raise UserError(_("You cannot merge accounts."))

    def _unmerge_action_xmlid(self):
        return "account.action_unmerge_accounts"

    def _unmerge_copy_defaults(self):
        return {"name": self.name}
