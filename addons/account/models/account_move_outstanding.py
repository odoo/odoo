from collections import defaultdict
from contextlib import contextmanager

import markupsafe

from odoo import _, api, fields, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL
from odoo.tools.misc import formatLang
from odoo.tools.safe_eval import safe_eval

_debug = DebugLog(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    payment_state_before_switch = fields.Char(copy=False)

    @_debug.perf.timed
    def action_view_bank_reconciliation_widget(self):
        _debug.lifecycle("action_view_bank_reconciliation_widget", records=self)
        return self.statement_line_id._action_view_bank_reconciliation_widget(
            default_context={
                "search_default_journal_id": self.statement_line_id.journal_id.id,
                "search_default_statement_line_id": self.statement_line_id.id,
                "default_st_line_id": self.statement_line_id.id,
            }
        )

    @_debug.perf.timed
    def action_view_bank_reconciliation_widget_statement(self):
        _debug.lifecycle(
            "action_view_bank_reconciliation_widget_statement", records=self
        )
        return self.statement_line_id._action_view_bank_reconciliation_widget(
            extra_domain=[("statement_id", "in", self.statement_id.ids)],
        )

    @_debug.perf.timed
    def action_view_business_doc(self):
        _debug.lifecycle("action_view_business_doc", records=self)
        if self.statement_line_id:
            return self.action_view_bank_reconciliation_widget()
        else:
            action = super().action_view_business_doc()
            action["context"] = action.get("context", {}) | {
                "preferred_aml_value": None,
                "preferred_aml_currency_id": None,
            }
            return action

    def _get_mail_thread_data_attachments(self):
        res = super()._get_mail_thread_data_attachments()
        from_bank_reco = self.env.context.get("from_bank_reco")
        for move in self:
            res[move.id] += move.statement_line_id.statement_id.attachment_ids
            if from_bank_reco:
                res[move.id] += move.line_ids.reconciled_lines_ids.move_attachment_ids
        return res

    @contextmanager
    def _get_edi_creation(self):
        with super()._get_edi_creation() as move:
            previous_lines = move.invoice_line_ids
            try:
                yield move.with_context(disable_onchange_name_predictive=True)
            finally:
                for line in move.invoice_line_ids - previous_lines:
                    line._onchange_name_predictive()

    @_debug.perf.timed
    def _get_domain_outstanding_bank_statement_lines(self):
        self.check_singleton()
        if _debug.logic.enabled:
            _debug.logic(
                "outstanding_stline_scope",
                move=self,
                partner=self.commercial_partner_id,
                company=self.company_id,
                inbound=self.is_inbound(),
            )
        return [
            ("parent_state", "=", "posted"),
            ("partner_id", "=", self.commercial_partner_id.id),
            ("partner_id", "!=", False),
            ("account_id.account_type", "=", "asset_cash"),
            (
                "journal_id",
                "in",
                self.env["account.journal"]._search(
                    [
                        *self.env["account.journal"]._check_company_domain(
                            self.company_id.id
                        ),
                        ("type", "=", "bank"),
                    ]
                ),
            ),
            ("balance", ">" if self.is_inbound() else "<", 0.0),
            ("statement_line_id", "!=", False),
            (
                "move_id.line_ids",
                "any",
                [
                    (
                        "account_id",
                        "=",
                        self.company_id.account_journal_suspense_account_id.id,
                    ),
                    ("reconciled", "=", False),
                ],
            ),
        ]

    def _get_outstanding_bank_statement_lines(self):
        moves_by_scope = defaultdict(self.browse)
        for move in self:
            moves_by_scope[
                move.commercial_partner_id, move.company_id, move.is_inbound()
            ] |= move

        lines_by_move = {}
        for moves in moves_by_scope.values():
            lines = self.env["account.move.line"].search(  # noqa: E8507 - one query per (partner, company, direction) scope; moves sharing one were merged above
                moves[0]._get_domain_outstanding_bank_statement_lines()
            )
            for move in moves:
                lines_by_move[move.id] = lines
        return lines_by_move

    @_debug.perf.timed
    def _compute_invoice_outstanding_credits_debits_widget(self):
        super()._compute_invoice_outstanding_credits_debits_widget()
        candidates = self.filtered(
            lambda move: (
                move.state in {"draft", "posted"}
                and move.payment_state in ("not_paid", "partial")
                and move.is_invoice(include_receipts=True)
                and move.partner_id
            )
        )
        if not candidates:
            return

        lines_by_move = candidates._get_outstanding_bank_statement_lines()
        if _debug.logic.enabled:
            _debug.logic(
                "outstanding_statement_lines",
                lines_per_move={m: len(l) for m, l in lines_by_move.items()},
            )

        for move in candidates:
            payments_widget_vals = {
                "outstanding": True,
                "content": [],
                "move_id": move.id,
                "title": _("Outstanding credits")
                if move.is_inbound()
                else _("Outstanding debits"),
            }

            for line in lines_by_move[move.id]:
                amount = line._get_statement_line_residual_in(
                    move.currency_id, move.company_id
                )
                if move.currency_id.is_zero(amount):
                    continue

                payments_widget_vals["content"].append(
                    {
                        "bank_label": line.name
                        if line.journal_id.type == "bank"
                        else False,
                        "journal_name": line.ref or line.move_id.name,
                        "amount": amount,
                        "currency_id": move.currency_id.id,
                        "id": line.id,
                        "move_id": line.move_id.id,
                        "date": fields.Date.to_string(line.date),
                        "account_payment_id": line.payment_id.id,
                    }
                )

            if payments_widget_vals["content"]:
                if move.invoice_outstanding_credits_debits_widget:
                    move.invoice_outstanding_credits_debits_widget["content"].extend(
                        payments_widget_vals["content"]
                    )
                else:
                    move.invoice_outstanding_credits_debits_widget = (
                        payments_widget_vals
                    )

    def _get_partner_credit_warning_exclude_amount(self):
        exclude_amount = super()._get_partner_credit_warning_exclude_amount()
        for line in self._get_outstanding_bank_statement_lines()[self.id]:
            exclude_amount += line._get_statement_line_residual_in(
                self.company_id.currency_id, self.company_id
            )

        matched_credits = self.line_ids.filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
        ).matched_credit_ids
        if matched_credits:
            bank_line_amount = sum(matched_credits.mapped("amount"))
            payment_date = max(matched_credits.mapped("max_date"))
            amount_company = matched_credits[0].credit_currency_id._convert(
                from_amount=bank_line_amount,
                to_currency=self.company_id.currency_id,
                company=self.company_id,
                date=payment_date,
            )
            exclude_amount += amount_company

        return exclude_amount

    @_debug.perf.timed
    def js_add_outstanding_line(self, line_id):
        _debug.lifecycle("js_add_outstanding_line", records=self)
        super().js_add_outstanding_line(line_id)
        line = self.env["account.move.line"].browse(line_id)
        if line.account_id.account_type == "asset_cash" and line.statement_line_id:
            return line.statement_line_id.with_context(
                skip_payment_tolerance=True,
                stop_reco_at_first_partial=True,
            ).set_line_bank_statement_line(
                self.line_ids.filtered(
                    lambda line: (
                        line.account_id.account_type
                        in {"asset_receivable", "liability_payable"}
                    )
                ).ids
            )
        return None

    @_debug.perf.timed
    def js_remove_outstanding_partial(self, partial_id):
        _debug.lifecycle("js_remove_outstanding_partial", records=self)
        if st_line := self.statement_line_id:
            partial = self.env["account.partial.reconcile"].browse(partial_id)
            st_line.remove_reconciled_line(
                (partial.credit_move_id + partial.debit_move_id).ids
            )
        else:
            super().js_remove_outstanding_partial(partial_id)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    move_attachment_ids = fields.One2many(
        comodel_name="ir.attachment",
        compute="_compute_move_attachment_ids",
        exportable=False,
    )
    full_amount_switch_html = fields.Html(
        compute="_compute_full_amount_switch_html",
        exportable=False,
    )

    def _get_statement_line_residual_in(self, currency, company):
        self.check_singleton()
        st_line = self.statement_line_id
        from_currency = st_line.foreign_currency_id or st_line.currency_id
        return from_currency._convert(
            from_amount=abs(st_line.amount_residual),
            to_currency=currency,
            company=company,
            date=self.date,
        )

    def _order_to_sql(self, order, query, alias=None, reverse=False):
        sql_order = super()._order_to_sql(order, query, alias, reverse)
        preferred_aml_residual_value = self.env.context.get("preferred_aml_value")
        preferred_aml_currency_id = self.env.context.get("preferred_aml_currency_id")
        if (
            preferred_aml_residual_value
            and preferred_aml_currency_id
            and order == self._order
        ):
            currency = self.env["res.currency"].browse(preferred_aml_currency_id)
            preferred_aml_residual_value = round(
                preferred_aml_residual_value, currency.decimal_places
            )
            sql_residual_currency = self._field_to_sql(
                alias or self._table, "amount_residual_currency", query
            )
            sql_currency = self._field_to_sql(
                alias or self._table, "currency_id", query
            )
            return SQL(
                "ROUND(%(residual_currency)s, %(decimal_places)s) = %(value)s "
                "AND %(currency)s = %(currency_id)s DESC, %(order)s",
                residual_currency=sql_residual_currency,
                decimal_places=currency.decimal_places,
                value=preferred_aml_residual_value,
                currency=sql_currency,
                currency_id=currency.id,
                order=sql_order,
            )
        return sql_order

    @api.depends("balance")
    @_debug.perf.timed
    def _compute_full_amount_switch_html(self):
        for line in self:
            if (
                not (
                    reconciled_lines
                    := line.reconciled_lines_excluding_exchange_diff_ids
                )
                or len(reconciled_lines) > 1
                or not line.statement_line_id
            ):
                line.full_amount_switch_html = False
                continue

            is_invoice = reconciled_lines.move_id.is_invoice(include_receipts=True)
            btn_start = markupsafe.Markup(
                "<a name='apply_full_amount' type='object' class='btn btn-link p-0 align-baseline'>"
            )

            if reconciled_lines.currency_id.is_zero(
                reconciled_lines.amount_currency + line.amount_currency
            ):
                lines = [
                    _("%(display_name_html)s will be entirely paid by the transaction.")
                    if is_invoice
                    else _(
                        "%(display_name_html)s will be fully reconciled by the transaction."
                    )
                ]
                liquidity_lines = line.move_id.line_ids.filtered(
                    lambda other: (
                        other.account_id == other.move_id.journal_id.default_account_id
                    )
                )
                if (
                    reconciled_lines.currency_id.compare_amounts(
                        sum(liquidity_lines.mapped("amount_currency")),
                        reconciled_lines.amount_currency,
                    )
                    < 0
                ):
                    btn_start = markupsafe.Markup(
                        "<a name='apply_partial_amount' type='object' class='btn btn-link p-0 align-baseline'>"
                    )
                    lines.append(
                        _(
                            "You might want to record a %(btn_start)spartial payment%(btn_end)s."
                        )
                        if is_invoice
                        else _(
                            "You might want to make a %(btn_start)spartial reconciliation%(btn_end)s instead."
                        )
                    )
            elif is_invoice:
                lines = [
                    _("%(display_name_html)s will be reduced by %(amount)s."),
                    _(
                        "You might want to set the invoice as %(btn_start)sfully paid%(btn_end)s."
                    ),
                ]
            else:
                lines = [
                    _("%(display_name_html)s will be reduced by %(amount)s."),
                    _(
                        "You might want to %(btn_start)sfully reconcile%(btn_end)s the document."
                    ),
                ]

            _debug.logic(
                "full_amount_switch_mode",
                line=line,
                reconciled=reconciled_lines,
                invoice=is_invoice,
                messages=len(lines),
            )
            display_name_html = markupsafe.Markup("""
                    <a name='action_redirect_to_move' type='object' class="btn btn-link p-0 align-baseline fst-italic">%(display_name)s</a>
                """) % {
                "display_name": reconciled_lines.move_id._get_move_display_name(
                    show_ref=False
                ),
            }

            extra_text = markupsafe.Markup("<br/>").join(lines) % {
                "amount": formatLang(
                    self.env, line.amount_currency, currency_obj=line.currency_id
                ),
                "display_name_html": display_name_html,
                "btn_start": btn_start,
                "btn_end": markupsafe.Markup("</a>"),
            }
            line.full_amount_switch_html = (
                markupsafe.Markup("<div class='text-muted'>%s</div>") % extra_text
            )

    def _compute_move_attachment_ids(self):
        id_model2attachments = {
            (res_model, res_id): attachments
            for res_model, res_id, attachments in self.env["ir.attachment"]._read_group(
                domain=Domain.OR(self._get_attachment_domains()),
                groupby=["res_model", "res_id"],
                aggregates=["id:recordset"],
            )
        }

        for record in self:
            record.move_attachment_ids = self._get_attachment_by_record(
                id_model2attachments, record
            )

    @api.model
    @_debug.perf.timed
    def _action_view_unreconciled(self, extra_domain=None, extra_context=None):
        _debug.lifecycle("_action_view_unreconciled", records=self)
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "account.action_move_line_posted_unreconciled"
        )
        _debug.logic(
            "unreconciled_action_scoped",
            extra_domain=bool(extra_domain),
            extra_context=bool(extra_context),
        )
        if extra_domain:
            stored = safe_eval(action.get("domain") or "[]", dict(self.env.context))
            action["domain"] = list(Domain.AND([Domain(stored), Domain(extra_domain)]))
        if extra_context:
            action["context"] = {
                **self.env["ir.actions.actions"]._eval_action_context(
                    action.get("context")
                ),
                **extra_context,
            }
        return action

    @_debug.perf.timed
    def action_reconcile(self):
        _debug.lifecycle("action_reconcile", records=self)
        self = self.filtered(lambda x: x.balance or x.amount_currency)
        if not self:
            return None

        wizard = (
            self.env["account.reconcile.wizard"]
            .with_context(
                active_model="account.move.line",
                active_ids=self.ids,
            )
            .new({})
        )
        return (
            wizard._action_view_wizard()
            if (wizard.is_write_off_required or wizard.force_partials)
            else wizard.reconcile()
        )

    @_debug.perf.timed
    def _read_group_select(self, aggregate_spec, query):
        fname, __, func = models.parse_read_group_spec(aggregate_spec)
        if func != "sum_rounded":
            return super()._read_group_select(aggregate_spec, query)
        currency_alias = query.get_table_alias(self._table, "currency_id")
        query.add_join(
            "LEFT JOIN",
            currency_alias,
            "res_currency",
            SQL(
                "%s = %s",
                self._field_to_sql(self._table, "currency_id", query),
                SQL.identifier(currency_alias, "id"),
            ),
        )

        return SQL(
            "SUM(ROUND(%s, %s))",
            self._field_to_sql(self._table, fname, query),
            self.env["res.currency"]._field_to_sql(
                currency_alias, "decimal_places", query
            ),
        )

    @_debug.perf.timed
    def _read_group_groupby(self, alias, groupby_spec, query):
        if ":" in groupby_spec:
            fname, method = groupby_spec.split(":")
            if method == "abs_rounded":
                _debug.logic("groupby_rerouted", field=fname, method=method)
                currency_alias = query.get_table_alias(self._table, "currency_id")
                query.add_join(
                    "LEFT JOIN",
                    currency_alias,
                    "res_currency",
                    SQL(
                        "%s = %s",
                        self._field_to_sql(self._table, "currency_id", query),
                        SQL.identifier(currency_alias, "id"),
                    ),
                )

                return SQL(
                    "ROUND(ABS(%s), %s)",
                    self._field_to_sql(self._table, fname, query),
                    self.env["res.currency"]._field_to_sql(
                        currency_alias, "decimal_places", query
                    ),
                )

        return super()._read_group_groupby(alias, groupby_spec, query)
