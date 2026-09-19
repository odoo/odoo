from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL
from odoo.tools.misc import formatLang

_debug = DebugLog(__name__)

_RUNNING_BALANCE_TRIGGERS = frozenset(
    {"balance_start", "first_line_index", "journal_id", "line_ids"}
)


class AccountBankStatement(models.Model):
    _name = "account.bank.statement"
    _inherit = ["mixin.mail.thread.main.attachment"]
    _description = "Bank Statement"
    _order = "first_line_index desc"
    _check_company_auto = True

    name = fields.Char(
        string="Reference",
        compute="_compute_name",
        store=True,
        copy=False,
        readonly=False,
    )

    reference = fields.Char(
        string="External Reference",
        copy=False,
    )

    date = fields.Date(
        compute="_compute_date",
        store=True,
        index=True,
        readonly=False,
    )

    first_line_index = fields.Char(
        compute="_compute_first_line_index",
        store=True,
    )

    balance_start = fields.Monetary(
        string="Starting Balance",
        compute="_compute_balance_start",
        store=True,
        readonly=False,
    )

    balance_end = fields.Monetary(
        string="Computed Balance",
        compute="_compute_balance_end",
        store=True,
    )

    balance_end_real = fields.Monetary(
        string="Ending Balance",
        compute="_compute_balance_end_real",
        store=True,
        readonly=False,
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        related="journal_id.company_id",
    )

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_currency_id",
        store=True,
    )

    journal_id = fields.Many2one(
        comodel_name="account.journal",
        compute="_compute_journal_id",
        store=True,
        check_company=True,
    )

    line_ids = fields.One2many(
        comodel_name="account.bank.statement.line",
        inverse_name="statement_id",
        string="Statement lines",
    )

    is_complete = fields.Boolean(
        compute="_compute_is_complete",
        store=True,
    )

    is_valid = fields.Boolean(
        compute="_compute_is_valid",
        search="_search_is_valid",
    )

    journal_has_invalid_statements = fields.Boolean(
        related="journal_id.has_invalid_statements"
    )

    problem_description = fields.Text(compute="_compute_problem_description")

    attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        string="Attachments",
        bypass_search_access=True,
    )

    _journal_id_date_desc_id_desc_idx = models.Index("(journal_id, date DESC, id DESC)")
    _first_line_index_idx = models.Index("(journal_id, first_line_index)")

    @api.depends("create_date")
    def _compute_name(self):
        for stmt in self:
            name = ""
            if stmt.journal_id:
                name = stmt.journal_id.code + " "
            stmt.name = name + _(
                "Statement %(date)s",
                date=stmt.date or fields.Date.to_date(stmt.create_date),
            )

    @api.depends("line_ids.internal_index", "line_ids.state")
    def _compute_first_line_index(self):
        for stmt in self:
            stmt.first_line_index = stmt._get_indexed_lines()[:1].internal_index

    @api.depends("line_ids.internal_index", "line_ids.state")
    def _compute_date(self):
        for stmt in self:
            posted = stmt._get_indexed_lines().filtered(
                lambda line: line.state == "posted"
            )
            stmt.date = posted[-1:].date

    def _get_indexed_lines(self):
        self.check_singleton()
        return self.line_ids.filtered("internal_index").sorted("internal_index")

    @_debug.perf.timed
    def _get_balance_start(self, stmt):
        journal_id = stmt.journal_id.id or stmt.line_ids.journal_id.id
        previous_line_with_statement = self.env["account.bank.statement.line"].search(
            [
                ("internal_index", "<", stmt.first_line_index),
                ("journal_id", "=", journal_id),
                ("state", "=", "posted"),
                ("statement_id", "!=", False),
            ],
            limit=1,
        )
        balance_start = previous_line_with_statement.statement_id.balance_end_real

        lines_in_between_domain = [
            ("internal_index", "<", stmt.first_line_index),
            ("journal_id", "=", journal_id),
            ("state", "=", "posted"),
        ]
        if previous_line_with_statement:
            lines_in_between_domain.append(
                ("internal_index", ">", previous_line_with_statement.internal_index)
            )
            previous_st_lines = previous_line_with_statement.statement_id.line_ids
            lines_in_common = previous_st_lines.filtered(
                lambda line: line.id in stmt.line_ids._origin.ids
            )
            balance_start -= sum(lines_in_common.mapped("amount"))

        [(amount_in_between,)] = self.env["account.bank.statement.line"]._read_group(
            lines_in_between_domain, aggregates=["amount:sum"]
        )
        _debug.pipeline(
            "balance_start_computed",
            statement=stmt,
            journal=journal_id,
            previous_line=previous_line_with_statement,
            balance_start=balance_start,
            amount_in_between=amount_in_between,
        )
        return balance_start + (amount_in_between or 0.0)

    @api.depends("create_date")
    def _compute_balance_start(self):
        for stmt in self.sorted(lambda x: x.first_line_index or "0"):
            stmt.balance_start = self._get_balance_start(stmt)

    @api.depends("balance_start", "line_ids.amount", "line_ids.state")
    def _compute_balance_end(self):
        for stmt in self:
            lines = stmt.line_ids.filtered(lambda x: x.state == "posted")
            stmt.balance_end = stmt.balance_start + sum(lines.mapped("amount"))

    @api.depends("balance_start")
    def _compute_balance_end_real(self):
        for stmt in self:
            stmt.balance_end_real = stmt.balance_end

    @api.depends("journal_id.currency_id", "company_id.currency_id")
    def _compute_currency_id(self):
        for statement in self:
            statement.currency_id = (
                statement.journal_id.currency_id or statement.company_id.currency_id
            )

    @api.depends("line_ids.journal_id")
    def _compute_journal_id(self):
        for statement in self:
            statement.journal_id = statement.line_ids.journal_id

    @api.depends("balance_end", "balance_end_real", "line_ids.amount", "line_ids.state")
    def _compute_is_complete(self):
        for stmt in self:
            stmt.is_complete = bool(
                stmt.line_ids.filtered(lambda l: l.state == "posted")
                and stmt.currency_id.compare_amounts(
                    stmt.balance_end, stmt.balance_end_real
                )
                == 0
            )

    @api.depends("balance_end", "balance_end_real")
    def _compute_is_valid(self):
        if len(self) == 1:
            self.is_valid = self._is_statement_valid()
        else:
            invalids = self.filtered(
                lambda s: s.id in self._get_invalid_statement_ids()
            )
            invalids.is_valid = False
            (self - invalids).is_valid = True

    @api.depends("is_valid", "is_complete")
    def _compute_problem_description(self):
        for stmt in self:
            description = None
            if not stmt.is_valid:
                description = _(
                    "The starting balance doesn't match the ending balance of the previous statement, or an earlier statement is missing."
                )
            elif not stmt.is_complete:
                description = _(
                    "The running balance (%s) doesn't match the specified ending balance.",
                    formatLang(
                        self.env, stmt.balance_end, currency_obj=stmt.currency_id
                    ),
                )
            stmt.problem_description = description

    @_debug.perf.timed
    def _search_is_valid(self, operator, value):
        if operator != "in":
            return NotImplemented
        invalid_ids = self._get_invalid_statement_ids(all_statements=True)
        return [("id", "not in", invalid_ids)]

    def _is_statement_valid(self):
        self.check_singleton()
        previous = self.env["account.bank.statement"].search(
            [
                ("first_line_index", "<", self.first_line_index),
                ("first_line_index", "!=", False),
                ("journal_id", "=", self.journal_id.id),
            ],
            limit=1,
            order="first_line_index DESC",
        )
        return (
            not previous
            or self.currency_id.compare_amounts(
                self.balance_start, previous.balance_end_real
            )
            == 0
        )

    @_debug.perf.timed
    def _get_invalid_statement_ids(self, all_statements=None):
        self.env["account.bank.statement.line"].flush_model(
            ["statement_id", "internal_index"]
        )
        self.env["account.bank.statement"].flush_model(
            ["balance_start", "balance_end_real", "first_line_index", "journal_id"]
        )
        self.env["account.journal"].flush_model(["company_id", "currency_id"])

        self.env.cr.execute(
            SQL(
                """
                 WITH statements AS (
                         SELECT st.id,
                                st.balance_start,
                                st.journal_id,
                                LAG(st.balance_end_real) OVER (
                                    PARTITION BY st.journal_id
                                        ORDER BY st.first_line_index
                                ) AS prev_balance_end_real,
                                -- Fall back to 2 dp when no currency resolves:
                                -- ROUND(x, NULL) is NULL and `NULL != NULL` is NULL
                                -- (falsy), so a broken statement would otherwise be
                                -- silently reported as valid.
                                COALESCE(currency.decimal_places, 2) AS decimal_places
                           FROM account_bank_statement st
                      LEFT JOIN account_journal j ON st.journal_id = j.id
                      LEFT JOIN res_company co ON j.company_id = co.id
                      LEFT JOIN res_currency currency
                             ON COALESCE(j.currency_id, co.currency_id) = currency.id
                          WHERE st.first_line_index IS NOT NULL
                            %s
                      )
               SELECT id
                 FROM statements
                WHERE prev_balance_end_real IS NOT NULL
                  AND ROUND(prev_balance_end_real, decimal_places)
                   != ROUND(balance_start, decimal_places)
                  %s
                """,
                SQL()
                if all_statements
                else SQL("AND st.journal_id = ANY(%s)", self.journal_id.ids),
                SQL() if all_statements else SQL("AND id = ANY(%s)", self.ids),
            )
        )
        invalid_ids = [statement_id for (statement_id,) in self.env.cr.fetchall()]
        _debug.logic(
            "_get_invalid_statement_ids",
            all=bool(all_statements),
            records=self,
            invalid_ids=invalid_ids[:8],
        )
        return invalid_ids

    @api.model
    @_debug.perf.timed
    def default_get(self, fields):
        _debug.lifecycle("default_get", records=self)
        defaults = super().default_get(fields)

        if "line_ids" not in fields:
            return defaults

        active_ids = self.env.context.get("active_ids", [])
        context_split_line_id = self.env.context.get("split_line_id")
        context_st_line_id = self.env.context.get("st_line_id")
        lines = None
        if context_split_line_id:
            current_st_line = self.env["account.bank.statement.line"].browse(
                context_split_line_id
            )
            line_before = self.env["account.bank.statement.line"].search(
                domain=[
                    ("internal_index", "<", current_st_line.internal_index),
                    ("journal_id", "=", current_st_line.journal_id.id),
                    ("statement_id", "!=", current_st_line.statement_id.id),
                    ("statement_id", "!=", False),
                ],
                order="internal_index desc",
                limit=1,
            )
            lines = self.env["account.bank.statement.line"].search(
                domain=[
                    ("internal_index", "<=", current_st_line.internal_index),
                    ("internal_index", ">", line_before.internal_index or ""),
                    ("journal_id", "=", current_st_line.journal_id.id),
                ],
                order="internal_index desc",
            )
        elif context_st_line_id and len(active_ids) <= 1:
            lines = self.env["account.bank.statement.line"].browse(context_st_line_id)
        elif context_st_line_id and len(active_ids) > 1:
            lines = self.env["account.bank.statement.line"].browse(active_ids).sorted()
            if len(lines.journal_id) > 1:
                raise UserError(
                    _("A statement should only contain lines from the same journal.")
                )
            indexes = lines.mapped("internal_index")
            lines_between = self.env["account.bank.statement.line"].search(
                [
                    ("internal_index", ">=", min(indexes)),
                    ("internal_index", "<=", max(indexes)),
                    ("journal_id", "=", lines.journal_id.id),
                ]
            )
            canceled_lines = lines_between.filtered(lambda l: l.state == "cancel")
            if len(lines) != len(lines_between - canceled_lines):
                raise UserError(
                    _(
                        "Unable to create a statement due to missing transactions. You may want to reorder the transactions before proceeding."
                    )
                )
            lines |= canceled_lines

        _debug.logic(
            "statement_lines_source_chosen",
            split_line=context_split_line_id,
            stline=context_st_line_id,
            active_count=len(active_ids),
            lines=lines,
        )
        if lines:
            defaults["line_ids"] = [Command.set(lines.ids)]

        return defaults

    def _get_attachments(self, values_list):
        attachments_list = []
        for values in values_list:
            attachment_ids = set()
            for orm_command in values.get("attachment_ids", []):
                if orm_command[0] == Command.LINK:
                    attachment_ids.add(orm_command[1])
                elif orm_command[0] == Command.SET:
                    attachment_ids.update(orm_command[2])
            attachments_list.append(
                self.env["ir.attachment"].browse(sorted(attachment_ids))
            )
        return attachments_list

    def _reparent_attachments(self, statements, attachments_list):
        for stmt, attachments in zip(statements, attachments_list, strict=True):
            attachments.write({"res_id": stmt.id, "res_model": stmt._name})

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
        attachments_list = self._get_attachments(vals_list)
        stmts = super().create(vals_list)
        self._reparent_attachments(stmts, attachments_list)
        self.env["account.bank.statement.line"]._invalidate_running_balance()
        return stmts

    @_debug.perf.timed
    def write(self, vals):
        _debug.lifecycle("write", records=self, fields=sorted(vals))
        if len(self) != 1 and "attachment_ids" in vals:
            vals = {
                key: value for key, value in vals.items() if key != "attachment_ids"
            }

        attachments_list = self._get_attachments([vals] * len(self))
        res = super().write(vals)
        self._reparent_attachments(self, attachments_list)
        if not _RUNNING_BALANCE_TRIGGERS.isdisjoint(vals):
            self.env["account.bank.statement.line"]._invalidate_running_balance()
        return res

    @_debug.perf.timed
    def unlink(self):
        _debug.lifecycle("unlink", unlink=self)
        res = super().unlink()
        self.env["account.bank.statement.line"]._invalidate_running_balance()
        return res
