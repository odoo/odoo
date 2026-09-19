from xmlrpc.client import MAXINT

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL
from odoo.tools.misc import str2bool

from odoo.addons.account.tools.display_types import NON_ACCOUNTABLE_DISPLAY_TYPES

_debug = DebugLog(__name__)

_RUNNING_BALANCE_INPUTS = {
    "account.bank.statement.line": [
        "amount",
        "move_id",
        "statement_id",
        "journal_id",
        "internal_index",
    ],
    "account.bank.statement": ["first_line_index", "journal_id", "balance_start"],
    "account.move": ["state"],
}

_RUNNING_BALANCE_TRIGGERS = frozenset(
    {"amount", "date", "sequence", "journal_id", "statement_id", "state"}
)

_AMOUNT_SYNCED_FIELDS = frozenset(
    {"amount", "amount_currency", "foreign_currency_id", "currency_id"}
)
_LABEL_SYNCED_FIELDS = frozenset({"payment_ref", "partner_id"})

_ANCHOR_AGGREGATE = "internal_index:max"


class AccountBankStatementLine(models.Model):
    _name = "account.bank.statement.line"
    _inherit = ["mixin.mail.thread.main.attachment"]
    _inherits = {"account.move": "move_id"}
    _description = "Bank Statement Line"
    _order = "internal_index desc"
    _check_company_auto = True

    move_id = fields.Many2one(
        comodel_name="account.move",
        string="Journal Entry",
        index=True,
        readonly=True,
        required=True,
        ondelete="cascade",
        check_company=True,
        bypass_search_access=True,
    )
    journal_id = fields.Many2one(  # noqa: E8529  three indexes over (journal_id, company_id, internal_index)
        comodel_name="account.journal",
        related="move_id.journal_id",
        precompute=True,
        inherited=True,
        store=True,
        index=False,
        readonly=False,
        required=True,
    )
    company_id = fields.Many2one(  # noqa: E8529  three indexes over (journal_id, company_id, internal_index)
        comodel_name="res.company",
        related="move_id.company_id",
        precompute=True,
        inherited=True,
        store=True,
        index=False,
        readonly=False,
        required=True,
    )
    statement_id = fields.Many2one(
        comodel_name="account.bank.statement",
        index=True,
    )

    payment_ids = fields.Many2many(
        comodel_name="account.payment",
        relation="account_payment_account_bank_statement_line_rel",
        string="Auto-generated Payments",
    )

    sequence = fields.Integer(default=1)
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        domain="['|', ('parent_id','=', False), ('is_company','=',True)]",
        ondelete="restrict",
        check_company=True,
    )

    account_number = fields.Char(string="Bank Account Number")

    partner_name = fields.Char(index="btree_not_null")

    transaction_type = fields.Char()
    payment_ref = fields.Char(
        string="Label",
        index="trigram",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Journal Currency",
        compute="_compute_currency_id",
        store=True,
    )
    amount = fields.Monetary()

    running_balance = fields.Monetary(compute="_compute_running_balance")
    foreign_currency_id = fields.Many2one(
        comodel_name="res.currency",
        help="The optional other currency if it is a multi-currency entry.",
    )
    amount_currency = fields.Monetary(
        string="Amount in Currency",
        currency_field="foreign_currency_id",
        compute="_compute_amount_currency",
        store=True,
        readonly=False,
        help="The amount expressed in an optional other currency if it is a multi-currency entry.",
    )

    amount_residual = fields.Float(
        string="Residual Amount",
        compute="_compute_reconciliation",
        store=True,
    )
    country_code = fields.Char(related="company_id.account_fiscal_country_id.code")

    internal_index = fields.Char(
        string="Internal Reference",
        compute="_compute_internal_index",
        store=True,
    )

    is_reconciled = fields.Boolean(
        compute="_compute_reconciliation",
        store=True,
    )
    statement_complete = fields.Boolean(related="statement_id.is_complete")
    statement_valid = fields.Boolean(related="statement_id.is_valid")
    statement_balance_end_real = fields.Monetary(
        related="statement_id.balance_end_real"
    )
    statement_name = fields.Char(
        related="statement_id.name",
        string="Statement Name",
    )

    transaction_details = fields.Json(readonly=True)

    _unreconciled_idx = models.Index(
        "(journal_id, company_id, internal_index) WHERE is_reconciled IS NOT TRUE"
    )
    _orphan_idx = models.Index(
        "(journal_id, company_id, internal_index) WHERE statement_id IS NULL"
    )
    _main_idx = models.Index("(journal_id, company_id, internal_index)")
    _internal_index_idx = models.Index("(internal_index)")

    @api.depends("foreign_currency_id", "date", "amount", "company_id", "currency_id")
    def _compute_amount_currency(self):
        for st_line in self:
            if not st_line.foreign_currency_id:
                st_line.amount_currency = False
            elif st_line.date and st_line._is_amount_currency_unset():
                st_line.amount_currency = st_line.currency_id._convert(
                    from_amount=st_line.amount,
                    to_currency=st_line.foreign_currency_id,
                    company=st_line.company_id,
                    date=st_line.date,
                )

    def _is_amount_currency_unset(self):
        return not self.amount_currency

    @api.depends("journal_id.currency_id", "company_id.currency_id")
    def _compute_currency_id(self):
        for st_line in self:
            st_line.currency_id = (
                st_line.journal_id.currency_id or st_line.company_id.currency_id
            )

    @api.depends("journal_id")
    def _compute_running_balance(self):
        for model_name, fnames in _RUNNING_BALANCE_INPUTS.items():
            self.env[model_name].flush_model(fnames)
        record_by_id = {line.id: line for line in self}
        reached = self.browse()
        for journal in self.journal_id:
            reached |= self._update_running_balance(journal, record_by_id)
        for line in self - reached:
            line.running_balance = 0.0

    def _update_running_balance(self, journal, record_by_id):
        journal_lines = self.filtered(lambda line: line.journal_id == journal)
        indexes = journal_lines.sorted("internal_index").mapped("internal_index")
        min_index, max_index = indexes[0] or "", indexes[-1] or ""
        companies = self.env["res.company"].search(
            [("id", "child_of", journal.company_id.id)]
        )

        balance = self._get_running_balance_before(journal, companies, min_index)
        reached = self.browse()
        window = self._get_running_balance_window(
            journal, companies, min_index, max_index
        )
        for line_id, amount, is_anchor, balance_start, state in window:
            if is_anchor:
                balance = balance_start
            if state == "posted":
                balance += amount
            line = record_by_id.get(line_id)
            if line is not None:
                line.running_balance = balance
                reached |= line
        _debug.perf.count("running_balance_window_fetched", rows=len(window))
        _debug.pipeline(
            "running_balance_updated",
            journal=journal,
            lines=journal_lines,
            companies=companies,
            reached=reached,
        )
        return reached

    @_debug.perf.timed
    def _get_running_balance_before(self, journal, companies, min_index):
        self.env.cr.execute(
            """
                SELECT first_line_index, COALESCE(balance_start, 0.0)
                FROM account_bank_statement
                WHERE
                    first_line_index < %s
                    AND journal_id = %s
                ORDER BY first_line_index DESC
                LIMIT 1
            """,
            [min_index, journal.id],
        )
        anchor_index, balance = self.env.cr.fetchone() or (None, 0.0)
        _debug.pipeline(
            "running_balance_anchor_found",
            journal=journal,
            min_index=min_index,
            anchor_index=anchor_index,
            anchor_balance=balance,
        )

        self.env.cr.execute(
            SQL(
                """
                SELECT COALESCE(SUM(st_line.amount), 0.0)
                FROM account_bank_statement_line st_line
                JOIN account_move move ON move.id = st_line.move_id
                WHERE
                    st_line.internal_index < %s
                    AND st_line.journal_id = %s
                    AND st_line.company_id = ANY(%s)
                    AND move.state = 'posted'
                    %s
                """,
                min_index,
                journal.id,
                companies.ids,
                SQL("AND st_line.internal_index >= %s", anchor_index)
                if anchor_index
                else SQL(),
            )
        )
        return balance + self.env.cr.fetchone()[0]

    def _get_running_balance_window(self, journal, companies, min_index, max_index):
        self.env.cr.execute(
            SQL(
                """
                SELECT
                    st_line.id,
                    st_line.amount,
                    st.first_line_index = st_line.internal_index AS is_anchor,
                    COALESCE(st.balance_start, 0.0),
                    move.state
                FROM account_bank_statement_line st_line
                JOIN account_move move ON move.id = st_line.move_id
                LEFT JOIN account_bank_statement st ON st.id = st_line.statement_id
                WHERE
                    st_line.internal_index >= %s
                    AND st_line.internal_index <= %s
                    AND st_line.journal_id = %s
                    AND st_line.company_id = ANY(%s)
                ORDER BY st_line.internal_index
                """,
                min_index,
                max_index,
                journal.id,
                companies.ids,
            )
        )
        return self.env.cr.fetchall()

    @api.depends("date", "sequence")
    def _compute_internal_index(self):
        for st_line in self.filtered(lambda line: line._origin.id):
            st_line.internal_index = (
                f"{st_line.date.strftime('%Y%m%d')}"
                f"{MAXINT - st_line.sequence:0>10}"
                f"{st_line._origin.id:0>10}"
            )

    @api.depends(
        "journal_id",
        "currency_id",
        "amount",
        "foreign_currency_id",
        "amount_currency",
        "move_id.checked",
        "move_id.line_ids.account_id",
        "move_id.line_ids.amount_currency",
        "move_id.line_ids.amount_residual_currency",
        "move_id.line_ids.currency_id",
        "move_id.line_ids.matched_debit_ids",
        "move_id.line_ids.matched_credit_ids",
    )
    @_debug.perf.timed
    def _compute_reconciliation(self):
        for st_line in self:
            _liquidity_lines, suspense_lines, _other_lines = st_line._seek_for_lines()

            if not st_line.checked:
                st_line.amount_residual = (
                    -st_line.amount_currency
                    if st_line.foreign_currency_id
                    else -st_line.amount
                )
            elif suspense_lines.account_id.reconcile:
                st_line.amount_residual = sum(
                    suspense_lines.mapped("amount_residual_currency")
                )
            else:
                st_line.amount_residual = sum(suspense_lines.mapped("amount_currency"))

            if not st_line.id:
                st_line.is_reconciled = False
            elif suspense_lines:
                st_line.is_reconciled = suspense_lines.currency_id.is_zero(
                    st_line.amount_residual
                )
            else:
                st_line.is_reconciled = True

    @api.constrains(
        "amount", "amount_currency", "currency_id", "foreign_currency_id", "journal_id"
    )
    @_debug.perf.timed
    def _check_amounts_currencies(self):
        for st_line in self:
            if st_line.foreign_currency_id == st_line.currency_id:
                _debug.logic(
                    "amounts_currencies_rejected",
                    stline=st_line,
                    reason="foreign_currency_is_journal_currency",
                )
                raise ValidationError(
                    _(
                        "The foreign currency must be different than the journal one: %s",
                        st_line.currency_id.name,
                    )
                )
            if not st_line.foreign_currency_id and st_line.amount_currency:
                _debug.logic(
                    "amounts_currencies_rejected",
                    stline=st_line,
                    reason="amount_currency_without_foreign_currency",
                )
                raise ValidationError(
                    _(
                        "You can't provide an amount in foreign currency without "
                        "specifying a foreign currency."
                    )
                )
            if (
                st_line.foreign_currency_id
                and not st_line.amount_currency
                and not st_line.currency_id.is_zero(st_line.amount)
            ):
                _debug.logic(
                    "amounts_currencies_rejected",
                    stline=st_line,
                    reason="foreign_currency_without_amount_currency",
                )
                raise ValidationError(
                    _(
                        "You can't provide a foreign currency without specifying an amount in "
                        "'Amount in Currency' field."
                    )
                )

    @api.model
    @_debug.perf.timed
    def default_get(self, fields):
        _debug.lifecycle("default_get", records=self)
        self_ctx = self.with_context(is_statement_line=True)
        defaults = super(AccountBankStatementLine, self_ctx).default_get(fields)
        if "journal_id" in fields and not defaults.get("journal_id"):
            defaults["journal_id"] = (
                self_ctx.env["account.move"]._search_default_journal().id
            )

        if "date" in fields and not defaults.get("date") and "journal_id" in defaults:
            last_line = self.search(
                [
                    ("journal_id", "=", defaults["journal_id"]),
                    ("state", "=", "posted"),
                ],
                limit=1,
            )
            if last_line.statement_id:
                defaults["date"] = last_line.statement_id.date
            elif last_line:
                defaults["date"] = last_line.date
            _debug.logic(
                "default_date_from_last_line",
                last_line=last_line,
                from_statement=bool(last_line.statement_id),
                date=defaults.get("date"),
            )
        return defaults

    @api.model
    def new(self, values=None, origin=None, ref=None):
        return super(
            AccountBankStatementLine, self.with_context(is_statement_line=True)
        ).new(values, origin, ref)

    @_debug.perf.timed
    def _prepare_create_vals(self, vals):
        line_vals = {"name": False, **vals, "move_type": "entry"}
        counterpart_account_id = line_vals.pop("counterpart_account_id", None)
        line_vals.setdefault("amount", 0)

        if "statement_id" in line_vals and "journal_id" not in line_vals:
            statement = self.env["account.bank.statement"].browse(
                line_vals["statement_id"]
            )
            if statement.journal_id:
                line_vals["journal_id"] = statement.journal_id.id

        if line_vals.get("journal_id") and line_vals.get("foreign_currency_id"):
            journal = self.env["account.journal"].browse(line_vals["journal_id"])
            journal_currency = journal.currency_id or journal.company_id.currency_id
            if line_vals["foreign_currency_id"] == journal_currency.id:
                _debug.logic(
                    "foreign_currency_dropped",
                    journal=journal,
                    reason="same_as_journal_currency",
                )
                line_vals["foreign_currency_id"] = False
                line_vals["amount_currency"] = 0.0

        return line_vals, counterpart_account_id

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
        prepared = [self._prepare_create_vals(vals) for vals in vals_list]
        st_lines = super(
            AccountBankStatementLine, self.with_context(is_statement_line=True)
        ).create([line_vals for line_vals, _account_id in prepared])

        to_create_lines_vals = []
        for st_line, (line_vals, counterpart_account_id) in zip(
            st_lines, prepared, strict=True
        ):
            if "line_ids" not in line_vals:
                to_create_lines_vals.extend(
                    st_line._prepare_move_line_default_vals(counterpart_account_id)
                )
            to_write = {
                "statement_line_id": st_line.id,
                "narration": st_line.narration,
                "name": False,
            }
            with self.env.protecting(
                self.env["account.move"]._get_field_protections(line_vals, st_line)
            ):
                st_line.move_id.with_context(clear_sequence_mixin_cache=False).write(
                    to_write
                )
        _debug.pipeline(
            "created_moves_line",
            stline=st_lines,
            move_id=st_lines.move_id,
            to_create_lines_vals_count=len(to_create_lines_vals),
        )
        self.env["account.move.line"].create(to_create_lines_vals)
        self.env.add_to_compute(
            self.env["account.move"]._fields["name"], st_lines.move_id
        )

        self.env.remove_to_compute(
            self.env["account.move"]._fields["narration"], st_lines.move_id
        )

        st_lines.move_id.action_post()
        self._invalidate_running_balance()
        return st_lines.with_env(self.env)

    @_debug.perf.timed
    def write(self, vals):
        _debug.lifecycle("write", records=self, fields=sorted(vals))
        res = super(
            AccountBankStatementLine, self.with_context(skip_readonly_check=True)
        ).write(vals)
        self._sync_to_moves(set(vals.keys()))
        if not _RUNNING_BALANCE_TRIGGERS.isdisjoint(vals):
            self._invalidate_running_balance()
        return res

    @_debug.perf.timed
    def unlink(self):
        _debug.lifecycle("unlink", unlink=self)
        tracked_lines = self.filtered(
            lambda stl: stl.company_id.restrictive_audit_trail
        )
        _debug.logic(
            "unlink_statement_lines_cancel_audit",
            tracked_lines=tracked_lines,
            delete=self - tracked_lines,
        )
        tracked_lines.move_id.action_cancel()
        moves_to_delete = (self - tracked_lines).move_id
        res = super().unlink()
        moves_to_delete.with_context(force_delete=True).unlink()
        self._invalidate_running_balance()
        return res

    @api.model
    def _invalidate_running_balance(self):
        self.env["account.bank.statement.line"].invalidate_model(["running_balance"])

    @api.model
    def formatted_read_group(
        self,
        domain,
        groupby=(),
        aggregates=(),
        having=(),
        offset=0,
        limit=None,
        order=None,
    ) -> list[dict]:
        borrow_anchor = self._shows_running_balance(groupby) and (
            _ANCHOR_AGGREGATE not in aggregates
        )
        result = super().formatted_read_group(
            domain,
            groupby,
            (*aggregates, _ANCHOR_AGGREGATE) if borrow_anchor else aggregates,
            having=having,
            offset=offset,
            limit=limit,
            order=order,
        )
        if self._shows_running_balance(groupby):
            self._add_group_running_balance(result, pop_anchor=borrow_anchor)
        return result

    def _shows_running_balance(self, groupby):
        if not self.env.context.get("show_running_balance_latest"):
            return False
        return any(
            spec in {"statement_id", "journal_id"} or spec.startswith("date")
            for spec in groupby
        )

    def _add_group_running_balance(self, result, pop_anchor):
        anchor_indexes = [
            group_line.pop(_ANCHOR_AGGREGATE)
            if pop_anchor
            else group_line[_ANCHOR_AGGREGATE]
            for group_line in result
        ]
        anchors = self.search(
            [("internal_index", "in", [index for index in anchor_indexes if index])]
        )
        anchors.mapped("running_balance")
        balance_by_index = {
            anchor.internal_index: anchor.running_balance for anchor in anchors
        }
        for group_line, index in zip(result, anchor_indexes, strict=True):
            group_line["running_balance"] = balance_by_index.get(index) or 0.0

    @_debug.perf.timed
    def action_undo_reconciliation(self):
        _debug.lifecycle("action_undo_reconciliation", records=self)
        _debug.pipeline(
            "undo_payments",
            stline=self,
            line_ids_count=len(self.line_ids),
            payment_ids=self.payment_ids,
        )
        self.line_ids.remove_move_reconcile()
        self.payment_ids.unlink()

        for st_line in self:
            st_line.with_context(force_delete=True, skip_readonly_check=True).write(
                {
                    "checked": True,
                    "line_ids": [Command.clear()]
                    + [
                        Command.create(line_vals)
                        for line_vals in st_line._prepare_move_line_default_vals()
                    ],
                }
            )

    @api.ondelete(at_uninstall=False)
    @_debug.perf.timed
    def _check_allow_unlink(self):
        _debug.lifecycle("_check_allow_unlink", records=self)
        if self.statement_id.filtered(lambda stmt: stmt.is_valid and stmt.is_complete):
            raise UserError(
                _(
                    "You can not delete a transaction from a valid statement.\n"
                    "If you want to delete it, please remove the statement first."
                )
            )

    def _get_or_create_bank_account(self):
        self.check_singleton()
        if not self.partner_id:
            _debug.logic("bank_account_skipped", stline=self, reason="no_partner")
            return self.env["res.partner.bank"]
        if str2bool(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("account.skip_create_bank_account_on_reconcile")
        ):
            _debug.logic(
                "bank_account_create_skipped", stline=self, reason="config_param"
            )
            return self.env["res.partner.bank"].search(
                [
                    ("acc_number", "=", self.account_number),
                    ("partner_id", "=", self.partner_id.id),
                    ("company_id", "in", [False, self.company_id.id]),
                ],
                limit=1,
            )
        return self.env["res.partner.bank"]._get_or_create_bank_account(
            account_number=self.account_number,
            partner=self.partner_id,
            company=self.company_id,
        )

    @_debug.perf.timed
    def _get_domain_default_amls_matching(self):
        self.check_singleton()
        all_reconcilable_account_ids = (
            self.env["account.account"]
            .sudo()
            .search(
                [
                    ("company_ids", "child_of", self.company_id.root_id.id),
                    ("reconcile", "=", True),
                ]
            )
            .ids
        )
        _debug.pipeline(
            "default_matching_domain_built",
            stline=self,
            reconcilable_accounts=len(all_reconcilable_account_ids),
        )
        return [
            ("parent_state", "=", "posted"),
            (
                "display_type",
                "not in",
                NON_ACCOUNTABLE_DISPLAY_TYPES,
            ),
            (
                "company_id",
                "in",
                self.env["res.company"]
                .search([("id", "child_of", self.company_id.id)])
                .ids,
            ),
            ("reconciled", "=", False),
            ("account_id", "in", all_reconcilable_account_ids),
            "|",
            (
                "account_id.account_type",
                "not in",
                ("asset_receivable", "liability_payable"),
            ),
            ("payment_id", "=", False),
            ("statement_line_id", "!=", self.id),
        ]

    def _get_accounting_amounts_and_currencies(self):
        self.check_singleton()
        liquidity_line, suspense_line, other_lines = self._seek_for_lines()
        if suspense_line and not other_lines:
            transaction_amount = -suspense_line.amount_currency
            transaction_currency = suspense_line.currency_id
        else:
            transaction_amount = (
                self.amount_currency if self.foreign_currency_id else self.amount
            )
            transaction_currency = (
                self.foreign_currency_id or liquidity_line.currency_id
            )
        return (
            transaction_amount,
            transaction_currency,
            sum(liquidity_line.mapped("amount_currency")),
            liquidity_line.currency_id,
            sum(liquidity_line.mapped("balance")),
            liquidity_line.company_currency_id,
        )

    @_debug.perf.timed
    def _prepare_counterpart_amounts_using_st_line_rate(
        self, currency, balance, amount_currency
    ):
        self.check_singleton()

        (
            transaction_amount,
            transaction_currency,
            journal_amount,
            journal_currency,
            company_amount,
            company_currency,
        ) = self._get_accounting_amounts_and_currencies()

        rate_journal2foreign_curr = (
            abs(transaction_amount) / abs(journal_amount) if journal_amount else 0.0
        )
        rate_comp2journal_curr = (
            abs(journal_amount) / abs(company_amount) if company_amount else 0.0
        )

        if currency == transaction_currency:
            trans_amount_currency = amount_currency
            journ_amount_currency = self._rounded_quotient(
                journal_currency, trans_amount_currency, rate_journal2foreign_curr
            )
            new_balance = self._rounded_quotient(
                company_currency, journ_amount_currency, rate_comp2journal_curr
            )
        elif currency == journal_currency:
            trans_amount_currency = transaction_currency.round(
                amount_currency * rate_journal2foreign_curr
            )
            new_balance = self._rounded_quotient(
                company_currency, amount_currency, rate_comp2journal_curr
            )
        else:
            journ_amount_currency = journal_currency.round(
                balance * rate_comp2journal_curr
            )
            trans_amount_currency = transaction_currency.round(
                journ_amount_currency * rate_journal2foreign_curr
            )
            new_balance = balance

        if _debug.logic.enabled:
            _debug.logic(
                "counterpart_rate_applied",
                stline=self,
                currency=currency,
                is_transaction_currency=currency == transaction_currency,
                is_journal_currency=currency == journal_currency,
                balance=new_balance,
                amount_currency=trans_amount_currency,
            )
        return {
            "amount_currency": trans_amount_currency,
            "balance": new_balance,
        }

    def _rounded_quotient(self, currency, amount, rate):
        return currency.round(amount / rate) if rate else 0.0

    @_debug.perf.timed
    def _prepare_move_line_default_vals(self, counterpart_account_id=None):
        self.check_singleton()

        _debug.logic(
            "counterpart_account_chosen",
            stline=self,
            suspense_fallback=not counterpart_account_id,
        )
        if not counterpart_account_id:
            counterpart_account_id = self.journal_id.suspense_account_id.id

        if not counterpart_account_id:
            raise UserError(
                _(
                    "You can't create a new statement line without a suspense account set on the %s journal.",
                    self.journal_id.display_name,
                )
            )

        company_currency = self.journal_id.company_id.sudo().currency_id
        journal_currency = self.journal_id.currency_id or company_currency
        foreign_currency = (
            self.foreign_currency_id or journal_currency or company_currency
        )

        journal_amount = self.amount
        if foreign_currency == journal_currency:
            transaction_amount = journal_amount
        else:
            transaction_amount = self.amount_currency
        if journal_currency == company_currency:
            company_amount = journal_amount
        elif foreign_currency == company_currency:
            company_amount = transaction_amount
        else:
            company_amount = journal_currency._convert(
                journal_amount, company_currency, self.journal_id.company_id, self.date
            )

        if _debug.logic.enabled:
            _debug.logic(
                "statement_amounts_resolved",
                stline=self,
                foreign_is_journal=foreign_currency == journal_currency,
                journal_is_company=journal_currency == company_currency,
                foreign_is_company=foreign_currency == company_currency,
                company_amount=company_amount,
            )
        liquidity_line_vals = {
            **self._prepare_move_line_common_vals(),
            "account_id": self.journal_id.default_account_id.id,
            "currency_id": journal_currency.id,
            "amount_currency": journal_amount,
            "debit": max(0.0, company_amount),
            "credit": max(0.0, -company_amount),
        }

        counterpart_line_vals = {
            **self._prepare_move_line_common_vals(),
            "account_id": counterpart_account_id,
            "currency_id": foreign_currency.id,
            "amount_currency": -transaction_amount,
            "debit": max(0.0, -company_amount),
            "credit": max(0.0, company_amount),
        }
        return [liquidity_line_vals, counterpart_line_vals]

    @_debug.perf.timed
    def _prepare_move_line_common_vals(self):
        self.check_singleton()
        return {
            "name": self.payment_ref,
            "move_id": self.move_id.id,
            "partner_id": self.partner_id.id,
        }

    def _seek_for_lines(self):
        self.check_singleton()
        liquidity_lines = self.env["account.move.line"]
        suspense_lines = self.env["account.move.line"]
        other_lines = self.env["account.move.line"]

        for line in self.move_id.line_ids:
            if line.account_id == self.journal_id.default_account_id:
                liquidity_lines += line
            elif line.account_id == self.journal_id.suspense_account_id:
                suspense_lines += line
            else:
                other_lines += line
        if not liquidity_lines:
            liquidity_lines = self.move_id.line_ids.filtered(
                lambda l: (
                    l.account_id.account_type in ("asset_cash", "liability_credit_card")
                )
            )
            other_lines -= liquidity_lines
        return liquidity_lines, suspense_lines, other_lines

    @_debug.perf.timed
    def _sync_from_moves(self, changed_fields):
        if self.env.context.get("skip_account_move_synchronization"):
            return
        if "line_ids" not in changed_fields:
            return

        for st_line in self.with_context(skip_account_move_synchronization=True):
            move = st_line.move_id
            move_vals, st_line_vals = st_line._prepare_synchronized_vals_from_move()
            _debug.pipeline(
                "_sync_from_moves_move_st_line",
                stline=st_line,
                fields=sorted(move_vals),
                fields_to=sorted(st_line_vals),
            )
            move.with_context(skip_readonly_check=True).write(
                move._cleanup_write_orm_values(move, move_vals)
            )
            st_line.write(move._cleanup_write_orm_values(st_line, st_line_vals))

    @_debug.perf.timed
    def _prepare_synchronized_vals_from_move(self):
        self.check_singleton()
        liquidity_lines, suspense_lines, other_lines = self._seek_for_lines()
        company_currency = self.journal_id.company_id.currency_id
        journal_currency = (
            self.journal_id.currency_id
            if self.journal_id.currency_id != company_currency
            else False
        )

        if len(liquidity_lines) != 1:
            raise UserError(
                _(
                    "The journal entry %s reached an invalid state regarding its related statement line.\n"
                    "To be consistent, the journal entry must always have exactly one journal item involving the "
                    "bank/cash account.",
                    self.move_id.display_name,
                )
            )
        if len(suspense_lines) > 1:
            raise UserError(
                _(
                    "%(move)s reached an invalid state regarding its related statement line.\n"
                    "To be consistent, the journal entry must always have exactly one suspense line.",
                    move=self.move_id.display_name,
                )
            )

        _debug.pipeline(
            "move_lines_classified",
            stline=self,
            liquidity=len(liquidity_lines),
            suspense=len(suspense_lines),
            other=len(other_lines),
        )
        st_line_vals = {
            "payment_ref": liquidity_lines.name,
            "partner_id": liquidity_lines.partner_id.id,
            "amount": (
                liquidity_lines.amount_currency
                if journal_currency
                else liquidity_lines.balance
            ),
        }
        if suspense_lines:
            if suspense_lines.currency_id == (journal_currency or company_currency):
                st_line_vals["amount_currency"] = 0.0
                st_line_vals["foreign_currency_id"] = False
            elif not other_lines:
                st_line_vals["amount_currency"] = -suspense_lines.amount_currency
                st_line_vals["foreign_currency_id"] = suspense_lines.currency_id.id

        _debug.logic(
            "foreign_currency_synced",
            stline=self,
            amount_currency=st_line_vals.get("amount_currency"),
            foreign_currency_id=st_line_vals.get("foreign_currency_id"),
        )
        move_vals = {
            "partner_id": liquidity_lines.partner_id.id,
            "currency_id": (
                self.foreign_currency_id or journal_currency or company_currency
            ).id,
        }
        return move_vals, st_line_vals

    @_debug.perf.timed
    def _sync_to_moves(self, changed_fields):
        if self.env.context.get("skip_account_move_synchronization"):
            return

        rebuild = not _AMOUNT_SYNCED_FIELDS.isdisjoint(changed_fields)
        if not rebuild and _LABEL_SYNCED_FIELDS.isdisjoint(changed_fields):
            return
        if _debug.pipeline.enabled:
            _debug.pipeline(
                "_sync_to_moves",
                stline=self,
                rebuild=rebuild,
                fields=sorted(changed_fields),
            )

        for st_line in self.with_context(skip_account_move_synchronization=True):
            st_line.move_id.with_context(skip_readonly_check=True).write(
                st_line._prepare_synchronized_move_vals(rebuild=rebuild)
            )

    @_debug.perf.timed
    def _prepare_synchronized_move_vals(self, rebuild):
        self.check_singleton()
        liquidity_lines, suspense_lines, other_lines = self._seek_for_lines()

        move_vals = {}
        if self.move_id.journal_id != self.journal_id:
            move_vals["journal_id"] = self.journal_id.id
        if self.move_id.partner_id != self.partner_id:
            move_vals["partner_id"] = self.partner_id.id

        if _debug.logic.enabled:
            _debug.logic(
                "sync_mode_chosen",
                stline=self,
                rebuild=rebuild,
                header_keys=sorted(move_vals),
            )
        if not rebuild:
            common_vals = self._prepare_move_line_common_vals()
            move_vals["line_ids"] = [
                Command.update(
                    line.id,
                    {
                        "name": common_vals["name"],
                        "partner_id": common_vals["partner_id"],
                    },
                )
                for line in liquidity_lines + suspense_lines
            ]
            return move_vals

        if self.move_id.state == "posted" and other_lines.filtered(
            lambda line: line.balance or line.amount_currency
        ):
            raise UserError(
                _(
                    "%(transaction)s is already matched with journal items, so its "
                    "amount can no longer change: rebuilding it would delete posted "
                    "entries.\n"
                    "Undo the reconciliation first, then change the amount.",
                    transaction=self.display_name,
                )
            )

        company_currency = self.journal_id.company_id.sudo().currency_id
        journal_currency = (
            self.journal_id.currency_id
            if self.journal_id.currency_id != company_currency
            else False
        )
        liquidity_vals, counterpart_vals = self._prepare_move_line_default_vals()
        line_ids_commands = [Command.update(liquidity_lines.id, liquidity_vals)]
        if suspense_lines:
            line_ids_commands.append(
                Command.update(suspense_lines.id, counterpart_vals)
            )
        else:
            line_ids_commands.append(Command.create(counterpart_vals))
        line_ids_commands.extend(Command.delete(line.id) for line in other_lines)

        move_vals["currency_id"] = (
            self.foreign_currency_id or journal_currency or company_currency
        ).id
        move_vals["line_ids"] = line_ids_commands
        _debug.pipeline(
            "rebuild_commands_built",
            stline=self,
            commands=len(line_ids_commands),
            suspense_updated=bool(suspense_lines),
            deleted=len(other_lines),
        )
        return move_vals


class AccountMove(models.Model):
    _inherit = "account.move"

    statement_line_ids = fields.One2many(
        comodel_name="account.bank.statement.line",
        inverse_name="move_id",
        string="Statements",
    )
