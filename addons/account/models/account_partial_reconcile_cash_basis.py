import json
from datetime import timedelta

from odoo import Command, _, api, models
from odoo.exceptions import UserError, ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.tools import frozendict

_debug = DebugLog(__name__)


class AccountPartialReconcile(models.Model):
    _inherit = "account.partial.reconcile"

    def _get_cash_basis_line_pairs(self):
        self.check_singleton()
        for source_line, counterpart_line in (
            (self.debit_move_id, self.credit_move_id),
            (self.credit_move_id, self.debit_move_id),
        ):
            if source_line.move_id != counterpart_line.move_id:
                yield source_line, counterpart_line

    def _get_cash_basis_journal(self):
        self.check_singleton()
        journal = self.company_id.account_config_id.tax_cash_basis_journal_id
        if not journal:
            raise UserError(
                _(
                    "There is no tax cash basis journal defined for the '%s' company.\n"
                    "Configure it in Accounting/Configuration/Settings",
                    self.company_id.display_name,
                )
            )
        return journal

    def _get_cash_basis_percentage(self, move, move_values, amounts):
        if move_values["currency"] == move.company_id.currency_id:
            currency = move.company_currency_id
            paid, total = amounts["amount"], move_values["total_balance"]
            reason = _(
                "Cash-basis taxes cannot be allocated for %(move)s because its company-currency payment total is zero.",
                move=move.display_name,
            )
        else:
            currency = move.currency_id
            paid, total = (
                amounts["amount_currency"],
                move_values["total_amount_currency"],
            )
            reason = _(
                "Cash-basis taxes cannot be allocated for %(move)s because its foreign-currency payment total is zero.",
                move=move.display_name,
            )
        if currency.is_zero(paid):
            _debug.logic("cash_basis_zero_payment_no", partial=self)
            return None
        if currency.is_zero(total):
            raise ValidationError(reason)
        _debug.logic(
            "cash_basis_percentage",
            partial=self,
            move=move,
            paid=paid,
            total=total,
            currency=currency,
        )
        return paid / total

    def _get_cash_basis_payment_rate(
        self, source_line, counterpart_line, amounts, payment_date
    ):
        self.check_singleton()
        if source_line.currency_id != counterpart_line.currency_id:
            _debug.logic(
                "cash_basis_rate_cross_currency",
                partial=self,
                forced="forced_rate_from_register_payment" in self.env.context,
                payment_date=payment_date,
            )
            if "forced_rate_from_register_payment" in self.env.context:
                return self.env.context["forced_rate_from_register_payment"]
            return self.env["res.currency"]._get_conversion_rate(
                counterpart_line.company_currency_id,
                source_line.currency_id,
                counterpart_line.company_id,
                payment_date,
            )
        if source_line.move_id.company_currency_id.is_zero(amounts["rate_amount"]):
            _debug.logic("cash_basis_rate_zero_amount", partial=self)
            return 0.0
        return amounts["rate_amount_currency"] / amounts["rate_amount"]

    def _get_cash_basis_amounts(self, source_line, counterpart_line):
        self.check_singleton()
        is_debit_source = source_line == self.debit_move_id
        sign = -1 if is_debit_source else 1
        return {
            "amount": self.amount,
            "amount_currency": (
                self.debit_amount_currency
                if is_debit_source
                else self.credit_amount_currency
            ),
            "rate_amount": sign * counterpart_line.balance,
            "rate_amount_currency": sign * counterpart_line.amount_currency,
        }

    @_debug.perf.timed
    def _prepare_cash_basis_partial_vals(
        self, source_line, counterpart_line, move_values
    ):
        self.check_singleton()
        move, counterpart_move = source_line.move_id, counterpart_line.move_id
        amounts = self._get_cash_basis_amounts(source_line, counterpart_line)
        if all(
            candidate.is_invoice(include_receipts=True)
            for candidate in move | counterpart_move
        ):
            amounts["rate_amount"] = source_line.balance
            amounts["rate_amount_currency"] = source_line.amount_currency
            payment_date = move.date
            _debug.logic("cash_basis_rate_from_invoices", partial=self, move=move)
        else:
            payment_date = counterpart_line.date
            _debug.logic(
                "cash_basis_rate_from_counterpart",
                partial=self,
                move=move,
                counterpart_move=counterpart_move,
            )

        percentage = self._get_cash_basis_percentage(move, move_values, amounts)
        if percentage is None:
            return None

        return {
            "partial": self,
            "percentage": percentage,
            "payment_rate": self._get_cash_basis_payment_rate(
                source_line, counterpart_line, amounts, payment_date
            ),
            "both_move_posted": self.debit_move_id.move_id.state == "posted"
            and self.credit_move_id.move_id.state == "posted",
            "payment_date": payment_date,
            "counterpart_move": counterpart_move,
        }

    def _collect_tax_cash_basis_values(self):
        values_per_move = {}
        collected_per_move = {}
        for partial in self:
            for source_line, counterpart_line in partial._get_cash_basis_line_pairs():
                move = source_line.move_id
                if move.id not in collected_per_move:
                    collected_per_move[move.id] = move._collect_tax_cash_basis_values()
                move_values = collected_per_move[move.id]
                if not move_values:
                    continue

                partial_vals = partial._prepare_cash_basis_partial_vals(
                    source_line, counterpart_line, move_values
                )
                if partial_vals is None:
                    continue

                values_per_move[move.id] = move_values
                move_values.setdefault("partials", []).append(partial_vals)
        _debug.pipeline(
            "cash_basis_values_collected",
            partial=self,
            moves_collected=len(collected_per_move),
            moves_with_values=len(values_per_move),
        )
        return values_per_move

    @api.model
    @_debug.perf.timed
    def _prepare_cash_basis_base_line_vals(self, base_line, balance, amount_currency):
        account = (
            base_line.company_id.account_config_id.account_cash_basis_base_account_id
            or base_line.account_id
        )
        tax_ids = base_line.tax_ids.flatten_taxes_hierarchy().filtered(
            lambda x: x.tax_exigibility == "on_payment"
        )
        is_refund = base_line.is_refund
        tax_tags = tax_ids._get_repartition_tags(is_refund, "base")
        product_tags = base_line.tax_tag_ids.filtered(
            lambda x: x.applicability == "products"
        )
        all_tags = tax_tags | product_tags

        return {
            "name": base_line.move_id.name,
            "debit": max(0.0, balance),
            "credit": -balance if balance < 0.0 else 0.0,
            "amount_currency": amount_currency,
            "currency_id": base_line.currency_id.id,
            "partner_id": base_line.partner_id.id,
            "account_id": account.id,
            "tax_ids": [Command.set(tax_ids.ids)],
            "tax_tag_ids": [Command.set(all_tags.ids)],
            "analytic_distribution": base_line.analytic_distribution,
            "display_type": base_line.display_type,
        }

    @api.model
    @_debug.perf.timed
    def _prepare_cash_basis_counterpart_base_line_vals(self, cb_base_line_vals):
        return {
            "name": cb_base_line_vals["name"],
            "debit": cb_base_line_vals["credit"],
            "credit": cb_base_line_vals["debit"],
            "account_id": cb_base_line_vals["account_id"],
            "amount_currency": -cb_base_line_vals["amount_currency"],
            "currency_id": cb_base_line_vals["currency_id"],
            "partner_id": cb_base_line_vals["partner_id"],
            "analytic_distribution": cb_base_line_vals["analytic_distribution"],
            "display_type": cb_base_line_vals["display_type"],
        }

    @api.model
    @_debug.perf.timed
    def _prepare_cash_basis_tax_line_vals(self, tax_line, balance, amount_currency):
        tax_ids = tax_line.tax_ids.filtered(lambda x: x.tax_exigibility == "on_payment")
        base_tags = tax_ids._get_repartition_tags(
            tax_line.tax_repartition_line_id.document_type == "refund",
            "base",
        )
        product_tags = tax_line.tax_tag_ids.filtered(
            lambda x: x.applicability == "products"
        )
        all_tags = base_tags | tax_line.tax_repartition_line_id.tag_ids | product_tags

        return {
            "name": tax_line.name,
            "debit": max(0.0, balance),
            "credit": -balance if balance < 0.0 else 0.0,
            "tax_base_amount": tax_line.tax_base_amount,
            "tax_repartition_line_id": tax_line.tax_repartition_line_id.id,
            "tax_ids": [Command.set(tax_ids.ids)],
            "tax_tag_ids": [Command.set(all_tags.ids)],
            "account_id": tax_line.tax_repartition_line_id.account_id.id
            or tax_line.company_id.account_config_id.account_cash_basis_base_account_id.id
            or tax_line.account_id.id,
            "amount_currency": amount_currency,
            "currency_id": tax_line.currency_id.id,
            "partner_id": tax_line.partner_id.id,
            "analytic_distribution": tax_line.analytic_distribution,
            "display_type": tax_line.display_type,
        }

    @api.model
    @_debug.perf.timed
    def _prepare_cash_basis_counterpart_tax_line_vals(self, tax_line, cb_tax_line_vals):
        return {
            "name": cb_tax_line_vals["name"],
            "debit": cb_tax_line_vals["credit"],
            "credit": cb_tax_line_vals["debit"],
            "account_id": tax_line.account_id.id,
            "amount_currency": -cb_tax_line_vals["amount_currency"],
            "currency_id": cb_tax_line_vals["currency_id"],
            "partner_id": cb_tax_line_vals["partner_id"],
            "analytic_distribution": cb_tax_line_vals["analytic_distribution"],
            "display_type": cb_tax_line_vals["display_type"],
        }

    @api.model
    def _get_cash_basis_base_line_grouping_key_from_vals(self, base_line_vals):
        tax_ids = base_line_vals["tax_ids"][0][2]
        base_taxes = self.env["account.tax"].browse(tax_ids)
        return (
            base_line_vals["currency_id"],
            base_line_vals["partner_id"],
            base_line_vals["account_id"],
            tuple(base_taxes.filtered(lambda x: x.tax_exigibility == "on_payment").ids),
            tuple(sorted(base_line_vals["tax_tag_ids"][0][2])),
            frozendict(base_line_vals["analytic_distribution"] or {}),
        )

    @api.model
    def _get_cash_basis_tax_line_grouping_key_from_vals(self, tax_line_vals):
        tax_ids = tax_line_vals["tax_ids"][0][2]
        base_taxes = self.env["account.tax"].browse(tax_ids)
        return (
            tax_line_vals["currency_id"],
            tax_line_vals["partner_id"],
            tax_line_vals["account_id"],
            tuple(base_taxes.filtered(lambda x: x.tax_exigibility == "on_payment").ids),
            tax_line_vals["tax_repartition_line_id"],
            tuple(sorted(tax_line_vals["tax_tag_ids"][0][2])),
            frozendict(tax_line_vals["analytic_distribution"] or {}),
        )

    @_debug.perf.timed
    def _prepare_cash_basis_move_vals(self, move, partial_values):
        partial = partial_values["partial"]
        journal = partial._get_cash_basis_journal()
        lock_date = move.company_id._get_user_fiscal_lock_date(journal)
        return {
            "move_type": "entry",
            "date": max(partial_values["payment_date"], lock_date + timedelta(days=1)),
            "ref": move.name,
            "journal_id": journal.id,
            "company_id": partial.company_id.id,
            "line_ids": [],
            "tax_cash_basis_rec_id": partial.id,
            "tax_cash_basis_origin_move_id": move.id,
            "fiscal_position_id": move.fiscal_position_id.id,
        }

    def _get_cash_basis_line_amount_currency(
        self, move_values, partial_values, caba_treatment, line, residual_per_tax_line
    ):
        amount_currency = line.currency_id.round(
            line.amount_currency * partial_values["percentage"]
        )
        if caba_treatment != "tax":
            return amount_currency
        if (
            move_values["is_fully_paid"]
            or line.currency_id.compare_amounts(
                abs(line.amount_residual_currency), abs(amount_currency)
            )
            < 0
        ) and partial_values is move_values["partials"][-1]:
            amount_currency = residual_per_tax_line[line.id]
        residual_per_tax_line[line.id] -= amount_currency
        return amount_currency

    @_debug.perf.timed
    def _prepare_cash_basis_line_vals(
        self, partial_values, caba_treatment, line, balance, amount_currency
    ):
        if caba_treatment == "tax":
            vals = self._prepare_cash_basis_tax_line_vals(
                line, balance, amount_currency
            )
            return self._get_cash_basis_tax_line_grouping_key_from_vals(vals), vals
        vals = self._prepare_cash_basis_base_line_vals(line, balance, amount_currency)
        vals["name"] = " - ".join(
            filter(None, (line.move_id.name, partial_values["counterpart_move"].name))
        )
        return self._get_cash_basis_base_line_grouping_key_from_vals(vals), vals

    @api.model
    def _add_cash_basis_line_vals(self, aggregated, caba_treatment, line, cb_line_vals):
        vals = aggregated["vals"]
        balance = (vals["debit"] + cb_line_vals["debit"]) - (
            vals["credit"] + cb_line_vals["credit"]
        )
        vals.update(
            {
                "debit": max(0, balance),
                "credit": -balance if balance < 0 else 0,
                "amount_currency": vals["amount_currency"]
                + cb_line_vals["amount_currency"],
            }
        )
        if caba_treatment == "tax":
            vals["tax_base_amount"] += cb_line_vals["tax_base_amount"]
            aggregated["tax_line"] |= line

    def _get_cash_basis_lines_to_create(
        self, move_values, partial_values, residual_per_tax_line
    ):
        lines_to_create = {}
        for caba_treatment, line in move_values["to_process_lines"]:
            amount_currency = self._get_cash_basis_line_amount_currency(
                move_values, partial_values, caba_treatment, line, residual_per_tax_line
            )
            payment_rate = partial_values["payment_rate"]
            balance = (payment_rate and amount_currency / payment_rate) or 0.0
            grouping_key, cb_line_vals = self._prepare_cash_basis_line_vals(
                partial_values, caba_treatment, line, balance, amount_currency
            )
            if grouping_key in lines_to_create:
                self._add_cash_basis_line_vals(
                    lines_to_create[grouping_key], caba_treatment, line, cb_line_vals
                )
            else:
                lines_to_create[grouping_key] = {"vals": cb_line_vals}
                if caba_treatment == "tax":
                    lines_to_create[grouping_key]["tax_line"] = line
        _debug.pipeline(
            "cash_basis_lines_grouped",
            partial=partial_values.get("partial"),
            lines=len(move_values["to_process_lines"]),
            groups=len(lines_to_create),
        )
        return lines_to_create

    @_debug.perf.timed
    def _get_cash_basis_move_line_commands(
        self, lines_to_create, move_index, to_reconcile_after
    ):
        commands = []
        sequence = 0
        for aggregated in lines_to_create.values():
            line_vals = aggregated["vals"]
            line_vals["sequence"] = sequence

            if "tax_repartition_line_id" in line_vals:
                tax_line = aggregated["tax_line"]
                counterpart_vals = self._prepare_cash_basis_counterpart_tax_line_vals(
                    tax_line, line_vals
                )
                counterpart_vals["sequence"] = sequence + 1
                if tax_line.account_id.reconcile:
                    to_reconcile_after.append(
                        (tax_line, move_index, counterpart_vals["sequence"])
                    )
            else:
                counterpart_vals = self._prepare_cash_basis_counterpart_base_line_vals(
                    line_vals
                )
                counterpart_vals["sequence"] = sequence + 1

            sequence += 2
            commands += [
                Command.create(counterpart_vals),
                Command.create(line_vals),
            ]
        _debug.pipeline(
            "cash_basis_line_commands",
            move_index=move_index,
            groups=len(lines_to_create),
            commands=len(commands),
            reconcile_after=len(to_reconcile_after),
        )
        return commands

    @api.model
    @_debug.perf.timed
    def _reconcile_cash_basis_transition_lines(self, moves, to_reconcile_after):
        reconciliation_plan = []
        for tax_lines, move_index, sequence in to_reconcile_after:
            lines = tax_lines.filtered(lambda x: not x.reconciled)
            if not lines:
                continue
            counterpart_line = moves[move_index].line_ids.filtered(
                lambda line, sequence=sequence: line.sequence == sequence
            )
            if counterpart_line.reconciled:
                continue
            reconciliation_plan.append(counterpart_line + lines)

        _debug.pipeline(
            "transition_lines_planned",
            moves=moves,
            candidates=len(to_reconcile_after),
            plan=len(reconciliation_plan),
        )
        self.env["account.move.line"].with_context(add_caba_vals=True)._reconcile_plan(
            reconciliation_plan
        )

    @_debug.perf.timed
    def _create_tax_cash_basis_moves(self):
        values_per_move = self._collect_tax_cash_basis_values()
        moves_to_create = []
        post_after_create = []
        to_reconcile_after = []

        for move_values in values_per_move.values():
            move = move_values["move"]
            residual_per_tax_line = {
                line.id: line.amount_residual_currency
                for line_type, line in move_values["to_process_lines"]
                if line_type == "tax"
            }
            for partial_values in move_values["partials"]:
                move_vals = self._prepare_cash_basis_move_vals(move, partial_values)
                move_vals["line_ids"] = self._get_cash_basis_move_line_commands(
                    self._get_cash_basis_lines_to_create(
                        move_values, partial_values, residual_per_tax_line
                    ),
                    len(moves_to_create),
                    to_reconcile_after,
                )
                moves_to_create.append(move_vals)
                post_after_create.append(partial_values["both_move_posted"])

        moves = (
            self.env["account.move"]
            .with_context(
                skip_invoice_sync=True,
                skip_invoice_line_sync=True,
                skip_account_move_synchronization=True,
            )
            .create(moves_to_create)
        )
        _debug.pipeline(
            "cash_basis",
            partial=self,
            moves=moves,
            posting=sum(post_after_create),
            moves_to_create_count=len(moves_to_create),
        )
        moves.browse(
            move.id for move, post in zip(moves, post_after_create, strict=True) if post
        )._post(soft=False)

        self._reconcile_cash_basis_transition_lines(moves, to_reconcile_after)
        return moves

    def _get_draft_caba_move_vals(self, collected_per_move=None):
        self.check_singleton()
        if collected_per_move is None:
            collected_per_move = {}

        def collect(move):
            if move.id not in collected_per_move:
                collected_per_move[move.id] = (
                    move._collect_tax_cash_basis_values() or {}
                )
            return collected_per_move[move.id]

        debit_vals = collect(self.debit_move_id.move_id)
        credit_vals = collect(self.credit_move_id.move_id)
        if not debit_vals and not credit_vals:
            _debug.logic("draft_caba_vals_empty", partial=self)
            return False
        _debug.logic(
            "draft_caba_vals_collected",
            partial=self,
            debit_lines=len(debit_vals.get("to_process_lines", [])),
            credit_lines=len(credit_vals.get("to_process_lines", [])),
        )
        return {
            "debit_caba_lines": [
                [aml_type, aml.id]
                for aml_type, aml in debit_vals.get("to_process_lines", [])
            ],
            "debit_total_balance": debit_vals.get("total_balance"),
            "debit_total_amount_currency": debit_vals.get("total_amount_currency"),
            "credit_caba_lines": [
                [aml_type, aml.id]
                for aml_type, aml in credit_vals.get("to_process_lines", [])
            ],
            "credit_total_balance": credit_vals.get("total_balance"),
            "credit_total_amount_currency": credit_vals.get("total_amount_currency"),
        }

    def _has_outdated_draft_caba_move_vals(self, collected_per_move=None):
        self.check_singleton()
        stored = self.draft_caba_move_vals
        if isinstance(stored, str):
            stored = json.loads(stored)
        return self._get_draft_caba_move_vals(collected_per_move) != stored

    def _set_draft_caba_move_vals(self):
        collected_per_move = {}
        for partial in self:
            partial.draft_caba_move_vals = partial._get_draft_caba_move_vals(
                collected_per_move
            )
