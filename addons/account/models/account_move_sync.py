from collections import Counter, defaultdict
from contextlib import ExitStack, contextmanager

from odoo import _, api, models
from odoo.fields import Command
from odoo.libs.debug_log import DebugLog
from odoo.tools import float_compare, frozendict
from odoo.tools.misc import clean_context

from odoo.addons.account.tools.dynamic_lines import plan_dynamic_line_sync

_debug = DebugLog(__name__)

TAX_BASE_DISPLAY_TYPES = (
    "product",
    "epd",
    "rounding",
    "non_deductible_product",
    "non_deductible_product_total",
)
NON_DEDUCTIBLE_BASE_DISPLAY_TYPES = (
    "non_deductible_product",
    "non_deductible_product_total",
)
MOVE_TRACKED_FIELDS = ("currency_id", "move_type", "invoice_currency_rate")
TAX_LINE_TRACKED_FIELDS = ("amount_currency", "balance", "analytic_distribution")
INVOICE_BASE_LINE_TRACKED_FIELDS = (
    "price_unit",
    "quantity",
    "discount",
    "deductible_amount",
)
ENTRY_BASE_LINE_TRACKED_FIELDS = ("amount_currency",)

SKIP = None
FROM_BASE = (False, False)
FROM_TAX = (True, False)
FROM_TAX_REAPPLY_RATE = (True, True)


@contextmanager
def sync_boundary(prepare, commit):
    state = prepare()
    yield  # noqa: RUF075 - deliberate, and the reason every sync step in this module relies on it: an exception inside the `with` aborts the transaction, so a reconciliation skipped here changes nothing that would otherwise have been persisted
    commit(state)


def written_value(record, fname):
    return record._fields[fname].convert_to_write(record[fname], record)


def values_differ(record, values):
    return any(written_value(record, fname) != values[fname] for fname in values)


def detach_container(value):
    if isinstance(value, list):
        return list(value)
    if isinstance(value, dict):
        return dict(value)
    return value


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_cash_rounding_difference(self, total_amount_currency):
        self.check_singleton()
        difference = self.invoice_cash_rounding_id.compute_difference(
            self.currency_id, total_amount_currency
        )
        rate = self.invoice_currency_rate or 1.0
        return self.company_id.currency_id.round(difference / rate), difference

    def _get_cash_rounding_profit_loss_account(self, diff_balance):
        self.check_singleton()
        cash_rounding = self.invoice_cash_rounding_id
        if diff_balance > 0.0 and cash_rounding.loss_account_id:
            return cash_rounding.loss_account_id
        return cash_rounding.profit_account_id

    def _get_biggest_tax_line(self):
        self.check_singleton()
        candidates = self.line_ids.filtered(
            lambda line: line.tax_repartition_line_id and line.display_type == "tax"
        )
        return max(
            candidates,
            key=lambda line: abs(line.balance),
            default=self.env["account.move.line"],
        )

    def _get_single_dynamic_line(self, lines):
        return lines[:1]

    @_debug.perf.timed
    def _prepare_cash_rounding_line_vals(self, diff_balance, diff_amount_currency):
        self.check_singleton()
        vals = {
            "balance": diff_balance,
            "amount_currency": diff_amount_currency,
            "partner_id": self.commercial_partner_id.id,
            "move_id": self.id,
            "currency_id": self.currency_id.id,
            "company_id": self.company_id.id,
            "company_currency_id": self.company_id.currency_id.id,
            "display_type": "rounding",
        }

        biggest_tax_line = (
            self._get_biggest_tax_line()
            if self.invoice_cash_rounding_id.strategy == "biggest_tax"
            else self.env["account.move.line"]
        )
        _debug.logic(
            "cash_rounding_target_chosen",
            move=self,
            biggest_tax_line=bool(biggest_tax_line),
        )
        if biggest_tax_line:
            vals.update(
                {
                    "name": _(
                        "%(tax_name)s (rounding)", tax_name=biggest_tax_line.name
                    ),
                    "account_id": biggest_tax_line.account_id.id,
                    "tax_repartition_line_id": biggest_tax_line.tax_repartition_line_id.id,
                    "tax_tag_ids": [Command.set(biggest_tax_line.tax_tag_ids.ids)],
                    "tax_ids": [Command.set(biggest_tax_line.tax_ids.ids)],
                }
            )
            return vals

        account = self._get_cash_rounding_profit_loss_account(diff_balance)
        _debug.logic("cash_rounding_account_resolved", move=self, found=bool(account))
        if not account:
            return None
        vals.update(
            {
                "name": self.invoice_cash_rounding_id.name,
                "account_id": account.id,
                "tax_ids": [Command.clear()],
            }
        )
        return vals

    @_debug.perf.timed
    def _recompute_cash_rounding_lines(self):
        self.check_singleton()
        existing_cash_rounding_line = self._get_single_dynamic_line(
            self.line_ids.filtered(lambda line: line.display_type == "rounding")
        )

        if not self.invoice_cash_rounding_id:
            _debug.logic(
                "cash_rounding_unset",
                move=self,
                existing=bool(existing_cash_rounding_line),
            )
            if existing_cash_rounding_line:
                existing_cash_rounding_line.unlink()
            return

        if existing_cash_rounding_line:
            old_strategy = (
                "biggest_tax"
                if existing_cash_rounding_line.tax_line_id
                else "add_invoice_line"
            )
            if self.invoice_cash_rounding_id.strategy != old_strategy:
                _debug.logic(
                    "cash_rounding_strategy_changed",
                    move=self,
                    old_strategy=old_strategy,
                )
                existing_cash_rounding_line.unlink()
                existing_cash_rounding_line = self.env["account.move.line"]

        others_lines = self.line_ids.filtered(
            lambda line: (
                line.account_id.account_type
                not in ("asset_receivable", "liability_payable")
            )
        )
        others_lines -= existing_cash_rounding_line
        diff_balance, diff_amount_currency = self._get_cash_rounding_difference(
            sum(others_lines.mapped("amount_currency"))
        )

        if self.company_currency_id.is_zero(diff_balance) and self.currency_id.is_zero(
            diff_amount_currency
        ):
            _debug.logic(
                "cash_rounding_zero_difference",
                move=self,
                existing=bool(existing_cash_rounding_line),
            )
            if existing_cash_rounding_line:
                existing_cash_rounding_line.unlink()
            return

        if (
            existing_cash_rounding_line
            and float_compare(
                existing_cash_rounding_line.balance,
                diff_balance,
                precision_rounding=self.company_currency_id.rounding,
            )
            == 0
            and float_compare(
                existing_cash_rounding_line.amount_currency,
                diff_amount_currency,
                precision_rounding=self.currency_id.rounding,
            )
            == 0
        ):
            _debug.logic("cash_rounding_line_unchanged", move=self)
            return

        vals = self._prepare_cash_rounding_line_vals(diff_balance, diff_amount_currency)
        _debug.pipeline(
            "cash_rounding_line_vals_ready",
            move=self,
            diff_balance=diff_balance,
            diff_amount_currency=diff_amount_currency,
            dropped=vals is None,
            existing=bool(existing_cash_rounding_line),
        )
        if vals is None:
            if existing_cash_rounding_line:
                existing_cash_rounding_line.unlink()
            return
        if existing_cash_rounding_line:
            existing_cash_rounding_line.write(vals)
        else:
            self.env["account.move.line"].create(vals)

    def _get_automatic_balancing_account(self):
        self.check_singleton()
        return (
            self.journal_id.default_account_id
            or self.company_id.account_config_id.account_journal_suspense_account_id
        )

    @_debug.perf.timed
    def _sync_unbalanced_lines(self, container):
        def has_tax(move):
            return bool(move.line_ids.tax_ids)

        def prepare():
            return {move: has_tax(move) for move in container["records"]}

        def commit(move_had_tax):
            balancing_line_by_move = {}
            detaxed_moves = self.env["account.move"]
            existing_balancing_lines = self.env["account.move.line"]
            for move in container["records"]:
                if move.state != "draft":
                    continue
                had_tax = move_had_tax.get(move, False)
                if not has_tax(move) and not had_tax:
                    continue
                if had_tax and not has_tax(move):
                    detaxed_moves |= move

                existing_balancing_line = self._get_single_dynamic_line(
                    move.line_ids.filtered(
                        lambda line: line.display_type == "balancing"
                    )
                )
                existing_balancing_lines |= existing_balancing_line
                balancing_line_by_move[move] = existing_balancing_line

            if detaxed_moves:
                _debug.logic(
                    "_sync_unbalanced_lines_taxes_removed_dropping_tax",
                    detaxed_moves=detaxed_moves,
                )
                detaxed_moves.line_ids.filtered("tax_line_id").unlink()
                detaxed_moves.line_ids.tax_tag_ids = [Command.set([])]
            if existing_balancing_lines:
                existing_balancing_lines.write({"balance": 0.0, "amount_currency": 0.0})

            if not balancing_line_by_move:
                return
            _debug.pipeline(
                "_sync_unbalanced_lines_balancing",
                balancing_line_by_move_count=len(balancing_line_by_move),
            )
            self._apply_balancing_lines(balancing_line_by_move)

        return sync_boundary(prepare, commit)

    @_debug.perf.timed
    def _apply_balancing_lines(self, balancing_line_by_move):
        moves = self.env["account.move"].union(*balancing_line_by_move)
        unbalanced_by_move_id = {
            move_id: (debit, credit)
            for move_id, debit, credit in (
                self._get_unbalanced_moves({"records": moves}) or []
            )
        }

        to_unlink = self.env["account.move.line"]
        to_create = []
        for move, existing_balancing_line in balancing_line_by_move.items():
            unbalanced = unbalanced_by_move_id.get(move.id)
            if not unbalanced:
                to_unlink |= existing_balancing_line
                continue
            debit, credit = unbalanced
            balance = credit - debit
            if existing_balancing_line:
                existing_balancing_line.write(
                    {
                        "balance": balance,
                        "amount_currency": existing_balancing_line.currency_id.round(
                            balance * existing_balancing_line.currency_rate
                        ),
                    }
                )
            else:
                to_create.append(
                    {
                        "balance": balance,
                        "name": _("Automatic Balancing Line"),
                        "display_type": "balancing",
                        "move_id": move.id,
                        "account_id": move._get_automatic_balancing_account().id,
                        "currency_id": move.currency_id.id,
                        "tax_ids": False,
                    }
                )

        _debug.pipeline(
            "balancing_lines_planned",
            moves=moves,
            unbalanced=len(unbalanced_by_move_id),
            unlink=len(to_unlink),
            create=len(to_create),
        )
        if to_unlink:
            to_unlink.unlink()
        if to_create:
            self.env["account.move.line"].create(to_create)

    @_debug.perf.timed
    def _sync_rounding_lines(self, container):
        def commit(_state):
            for invoice in container["records"]:
                if invoice.state == "draft":
                    invoice._recompute_cash_rounding_lines()

        return sync_boundary(lambda: None, commit)

    @api.model
    @_debug.perf.timed
    def _sync_dynamic_line_needed_values(self, values_list):
        line_fields = self.env["account.move.line"]._fields
        res = {}
        merged_keys = set()
        for computed_needed in values_list:
            if computed_needed is False:
                continue
            for key, values in computed_needed.items():
                if key not in res:
                    res[key] = {
                        fname: detach_container(value)
                        for fname, value in values.items()
                    }
                    continue
                merged_keys.add(key)
                for fname, value in values.items():
                    if fname not in res[key]:
                        res[key][fname] = detach_container(value)
                    elif line_fields[fname].type == "monetary":
                        res[key][fname] += value

        for key, values in res.items():
            move_id = key.get("move_id")
            if not move_id:
                continue
            record = self.env["account.move"].browse(move_id)
            for fname, current_value in values.items():
                field = line_fields[fname]
                if isinstance(current_value, float):
                    values[fname] = field.convert_to_cache(current_value, record)

        for key in merged_keys:
            values = res[key]
            if not any(
                values[fname]
                for fname in values
                if line_fields[fname].type == "monetary"
            ):
                del res[key]

        _debug.pipeline(
            "needed_values_merged",
            sources=len(values_list),
            merged=len(merged_keys),
            keys=len(res),
        )
        return res

    def _get_tax_base_amls(self):
        self.check_singleton()
        return self.line_ids.filtered(
            lambda line: (
                line.display_type in TAX_BASE_DISPLAY_TYPES
                and not (
                    line.display_type == "rounding" and line.tax_repartition_line_id
                )
            )
        )

    def _get_tax_amls(self):
        self.check_singleton()
        return self.line_ids.filtered("tax_repartition_line_id")

    def _get_base_line_tracked_fields(self, grouping_key_fields):
        self.check_singleton()
        extra_fields = (
            INVOICE_BASE_LINE_TRACKED_FIELDS
            if self.is_invoice(include_receipts=True)
            else ENTRY_BASE_LINE_TRACKED_FIELDS
        )
        return (*grouping_key_fields, *extra_fields)

    @_debug.perf.timed
    def _get_tax_rounding_mode(self, move, before):

        def field_has_changed(values, record, field):
            return written_value(record, field) != values.get(record, {}).get(field)

        def changed_lines_of(values, records):
            return [
                record
                for record in records
                if record not in values
                or any(
                    field_has_changed(values, record, field) for field in values[record]
                )
            ]

        tax_lines = move._get_tax_amls()
        base_lines = move._get_tax_base_amls()
        tax_before = before["tax_lines"].get(move, {})
        base_before = before["base_lines"].get(move, {})

        if move.is_invoice(include_receipts=True) and (
            field_has_changed(before["moves"], move, "currency_id")
            or field_has_changed(before["moves"], move, "move_type")
        ):
            _debug.logic("tax_rounding_currency_or_type_changed", move=move)
            return FROM_BASE

        if any(
            line not in base_lines
            for line, values in base_before.items()
            if values["tax_ids"]
        ):
            if changed_lines_of(tax_before, tax_lines):
                _debug.logic("tax_rounding_base_removed_tax_edited", move=move)
                return FROM_TAX
            _debug.logic("tax_rounding_base_line_removed", move=move)
            return FROM_BASE

        if changed_lines := changed_lines_of(base_before, base_lines):
            round_from_tax_lines = all(
                not line.tax_ids and not base_before.get(line, {}).get("tax_ids")
                for line in changed_lines
            ) or (
                list(tax_before) != list(tax_lines)
                or any(
                    self.env.is_protected(line._fields[fname], line)
                    for line in tax_lines
                    for fname in tax_before[line]
                )
            )
            if round_from_tax_lines and any(
                line[field]
                for line in changed_lines
                for field in ("amount_currency", "balance")
            ):
                _debug.logic(
                    "tax_rounding_amounts_edited_skipped",
                    move=move,
                    changed=len(changed_lines),
                )
                return SKIP
            _debug.logic(
                "tax_rounding_base_lines_changed",
                move=move,
                changed=len(changed_lines),
                from_tax=round_from_tax_lines,
            )
            return FROM_TAX if round_from_tax_lines else FROM_BASE

        if field_has_changed(before["moves"], move, "invoice_currency_rate"):
            _debug.logic("tax_rounding_rate_changed", move=move)
            return FROM_TAX_REAPPLY_RATE

        return SKIP

    @_debug.perf.timed
    def _prepare_non_deductible_tax_line_vals(self, move, base_lines_values):
        non_deductible_lines_values = [
            line_values
            for line_values in base_lines_values
            if line_values["special_type"] == "non_deductible"
            and line_values["tax_ids"]
        ]
        _debug.logic(
            "non_deductible_tax_sources",
            move=move,
            count=len(non_deductible_lines_values),
        )
        if not non_deductible_lines_values:
            return None

        tax_amount = 0.0
        tax_amount_currency = 0.0
        for line_values in non_deductible_lines_values:
            details = line_values["tax_details"]
            tax_amount += -line_values["sign"] * (
                details["total_included"] - details["total_excluded"]
            )
            tax_amount_currency += -line_values["sign"] * (
                details["total_included_currency"] - details["total_excluded_currency"]
            )

        return {
            "move_id": move.id,
            "account_id": (
                move.journal_id.non_deductible_account_id
                or move.journal_id.default_account_id
            ).id,
            "display_type": "non_deductible_tax",
            "name": _("private part (taxes)"),
            "balance": tax_amount,
            "amount_currency": tax_amount_currency,
            "sequence": max(
                move.line_ids.filtered(
                    lambda line: (
                        line.display_type
                        in ("product", *NON_DEDUCTIBLE_BASE_DISPLAY_TYPES)
                    )
                ).mapped("sequence"),
                default=0,
            )
            + 1,
        }

    @_debug.perf.timed
    def _sync_tax_lines(self, container):
        AccountTax = self.env["account.tax"]
        grouping_key_fields = tuple(
            AccountTax._prepare_base_line_grouping_key(
                AccountTax._prepare_base_line_for_taxes_computation(None)
            )
        )

        def snapshot(record, fnames):
            return {fname: written_value(record, fname) for fname in fnames}

        def prepare():
            return {
                "moves": {
                    move: snapshot(move, MOVE_TRACKED_FIELDS)
                    for move in container["records"]
                },
                "base_lines": {
                    move: {
                        line: snapshot(
                            line,
                            move._get_base_line_tracked_fields(grouping_key_fields),
                        )
                        for line in move._get_tax_base_amls()
                    }
                    for move in container["records"]
                },
                "tax_lines": {
                    move: {
                        line: snapshot(line, TAX_LINE_TRACKED_FIELDS)
                        for line in move._get_tax_amls()
                    }
                    for move in container["records"]
                },
            }

        def commit(before):
            to_delete = []
            to_create = []
            grouped_update = defaultdict(set)
            for move in container["records"]:
                if move.state != "draft":
                    continue
                mode = self._get_tax_rounding_mode(move, before)
                if mode is SKIP:
                    _debug.logic("_sync_tax_lines_unchanged_skipped", move=move)
                    continue
                move_delete, move_create, move_update = self._get_tax_line_changes(
                    move, *mode
                )
                _debug.pipeline(
                    "_sync_tax_lines",
                    move=move,
                    mode=mode,
                    delete=len(move_delete),
                    create=len(move_create),
                    update=len(move_update),
                )
                to_delete += move_delete
                to_create += move_create
                for key, line_id in move_update:
                    grouped_update[key].add(line_id)

            for (_currency_id, values), lines in grouped_update.items():
                self.env["account.move.line"].browse(lines).write(dict(values))
            if to_delete:
                self.env["account.move.line"].browse(to_delete).with_context(
                    dynamic_unlink=True
                ).unlink()
            if to_create:
                self.env["account.move.line"].create(to_create)

        return sync_boundary(prepare, commit)

    @_debug.perf.timed
    def _get_tax_line_changes(self, move, round_from_tax_lines, reapply_currency_rate):
        AccountTax = self.env["account.tax"]
        to_delete = []
        to_create = []
        to_update = []
        base_lines_values, tax_lines_values = move._get_rounded_base_and_tax_lines(
            round_from_tax_lines=round_from_tax_lines,
            reapply_currency_rate=reapply_currency_rate,
        )
        AccountTax._add_accounting_data_in_base_lines_tax_details(
            base_lines_values,
            move.company_id,
            include_caba_tags=move.always_tax_exigible,
        )
        tax_results = AccountTax._prepare_tax_lines(
            base_lines_values, move.company_id, tax_lines=tax_lines_values
        )
        _debug.pipeline(
            "tax_lines_prepared",
            move=move,
            from_tax=round_from_tax_lines,
            reapply_rate=reapply_currency_rate,
            base_lines=len(base_lines_values),
            tax_lines=len(tax_lines_values),
            base_updates=len(tax_results["base_lines_to_update"]),
            tax_adds=len(tax_results["tax_lines_to_add"]),
            tax_deletes=len(tax_results["tax_lines_to_delete"]),
            tax_updates=len(tax_results["tax_lines_to_update"]),
        )

        non_deductible_tax_line = move._get_single_dynamic_line(
            move.line_ids.filtered(
                lambda line: line.display_type == "non_deductible_tax"
            )
        )
        non_deductible_vals = self._prepare_non_deductible_tax_line_vals(
            move, base_lines_values
        )
        _debug.logic(
            "non_deductible_tax_line_action",
            move=move,
            action=(
                "delete"
                if non_deductible_vals is None
                else "update"
                if non_deductible_tax_line
                else "create"
            ),
        )
        if non_deductible_vals is None:
            to_delete.extend(non_deductible_tax_line.ids)
        elif non_deductible_tax_line:
            tax_results["tax_lines_to_update"].append(
                (
                    {"record": non_deductible_tax_line},
                    "unused_grouping_key",
                    {
                        "amount_currency": non_deductible_vals["amount_currency"],
                        "balance": non_deductible_vals["balance"],
                        "account_id": non_deductible_vals["account_id"],
                    },
                )
            )
        else:
            to_create.append(non_deductible_vals)

        def stage_update(line, values):
            if values_differ(line, values):
                to_update.append(((line.currency_id.id, frozendict(values)), line.id))

        for base_line, values in tax_results["base_lines_to_update"]:
            stage_update(base_line["record"], values)

        to_delete.extend(
            tax_line_vals["record"].id
            for tax_line_vals in tax_results["tax_lines_to_delete"]
            if tax_line_vals["record"].display_type != "rounding"
        )
        to_create.extend(
            {**tax_line_vals, "display_type": "tax", "move_id": move.id}
            for tax_line_vals in tax_results["tax_lines_to_add"]
        )
        for tax_line_vals, _grouping_key, values in tax_results["tax_lines_to_update"]:
            stage_update(tax_line_vals["record"], values)

        return to_delete, to_create, to_update

    @_debug.perf.timed
    def _prepare_non_deductible_line_vals(self, move):
        product_lines = move.line_ids.filtered(
            lambda line: line.display_type == "product"
        )
        sign = move.direction_sign
        rate = move.invoice_currency_rate or 1.0
        amount_currency_total = 0.0
        balance_total = 0.0
        vals_list = []

        for line in product_lines:
            if not line._is_partially_deductible():
                continue
            percentage = 1 - line.deductible_amount / 100
            non_deductible_subtotal = line.currency_id.round(
                line.price_subtotal * percentage
            )
            amount_currency = line.currency_id.round(sign * non_deductible_subtotal)
            balance = line.company_currency_id.round(
                sign * non_deductible_subtotal / rate
            )
            amount_currency_total += amount_currency
            balance_total += balance
            vals_list.append(
                {
                    "move_id": move.id,
                    "partner_id": move.commercial_partner_id.id,
                    "account_id": line.account_id.id,
                    "display_type": "non_deductible_product",
                    "name": line.name,
                    "balance": -balance,
                    "amount_currency": -amount_currency,
                    "tax_ids": [
                        Command.set(
                            line.tax_ids.filtered(
                                lambda tax: tax.amount_type != "fixed"
                            ).ids
                        )
                    ],
                    "sequence": line.sequence + 1,
                }
            )

        _debug.pipeline(
            "non_deductible_lines_built",
            move=move,
            products=len(product_lines),
            partial=len(vals_list),
            balance_total=balance_total,
        )
        vals_list.append(
            {
                "move_id": move.id,
                "partner_id": move.commercial_partner_id.id,
                "account_id": (
                    move.journal_id.non_deductible_account_id
                    or move.journal_id.default_account_id
                ).id,
                "display_type": "non_deductible_product_total",
                "name": _("private part"),
                "balance": balance_total,
                "amount_currency": amount_currency_total,
                "tax_ids": [Command.clear()],
                "sequence": max(product_lines.mapped("sequence")) + 1,
            }
        )
        return vals_list

    @_debug.perf.timed
    def _sync_non_deductible_base_lines(self, container):
        def product_line_fingerprint(move):
            return move.journal_id, Counter(
                (
                    line.name,
                    line.price_subtotal,
                    line.tax_ids,
                    line.deductible_amount,
                    line.account_id,
                )
                for line in move.line_ids
                if line.display_type == "product"
            )

        def has_non_deductible_lines(move):
            return (
                move.state == "draft"
                and move.is_purchase_document(include_receipts=True)
                and any(
                    line._is_partially_deductible()
                    for line in move.line_ids
                    if line.display_type == "product"
                )
            )

        def prepare():
            return {
                move: product_line_fingerprint(move) for move in container["records"]
            }

        def commit(before):
            to_delete = []
            to_create = []
            for move in container["records"]:
                if product_line_fingerprint(move) == before.get(move):
                    continue

                to_delete += move.line_ids.filtered(
                    lambda line: line.display_type in NON_DEDUCTIBLE_BASE_DISPLAY_TYPES
                ).ids
                if has_non_deductible_lines(move):
                    to_create += self._prepare_non_deductible_line_vals(move)

            _debug.pipeline(
                "non_deductible_base_lines_planned",
                moves=container["records"],
                delete=len(to_delete),
                create=len(to_create),
            )
            if to_delete:
                self.env["account.move.line"].browse(to_delete).with_context(
                    dynamic_unlink=True
                ).unlink()
            if to_create:
                self.env["account.move.line"].create(to_create)

        return sync_boundary(prepare, commit)

    @_debug.perf.timed
    def _sync_dynamic_line(
        self,
        existing_key_fname,
        needed_vals_fname,
        needed_dirty_fname,
        line_type,
        container,
    ):
        def existing():
            if line_type == "epd":
                return {
                    line: (
                        line[existing_key_fname] or frozendict({"epd_line_id": line.id})
                    )
                    for line in container["records"].line_ids
                    if line.display_type == "epd"
                    if line[existing_key_fname] or line.id
                }
            return {
                line: line[existing_key_fname]
                for line in container["records"].line_ids
                if line[existing_key_fname]
            }

        def needed():
            return self._sync_dynamic_line_needed_values(
                container["records"].mapped(needed_vals_fname)
            )

        *path, dirty_fname = needed_dirty_fname.split(".")

        def dirty_records():
            eligible_recs = container["records"].mapped(".".join(path))
            if eligible_recs._name == "account.move.line":
                eligible_recs = eligible_recs.filtered(
                    lambda rec: rec.display_type != "cogs"
                )
            return eligible_recs.filtered(dirty_fname)

        def prepare():
            state = (existing(), needed())
            dirty_records()[dirty_fname] = False
            return state

        def commit(state):
            dirty = dirty_records()
            if not dirty:
                _debug.logic(
                    "_sync_dynamic_line_nothing_dirty_skipped", line_type=line_type
                )
                return
            _debug.pipeline(
                "_sync_dynamic_line",
                line_type=line_type,
                dirty=dirty,
                records=container["records"],
            )
            inv_existing_before, needed_before = state
            self._apply_dynamic_line_plan(
                inv_existing_before, existing(), needed_before, needed(), line_type
            )

        return sync_boundary(prepare, commit)

    @_debug.perf.timed
    def _apply_dynamic_line_plan(
        self, existing_before, existing_after, needed_before, needed_after, line_type
    ):
        AccountMoveLine = self.env["account.move.line"]
        live_ids = set(
            AccountMoveLine.browse(k["id"] for k in needed_before if "id" in k)
            .exists()
            .ids
        )
        needed_before = {
            k: v
            for k, v in needed_before.items()
            if "id" not in k or k["id"] in live_ids
        }

        plan = plan_dynamic_line_sync(
            existing_before,
            existing_after,
            needed_before,
            needed_after,
            values_differ,
        )
        if plan is None:
            _debug.logic(
                "_apply_dynamic_line_plan_no_plan_unchanged", line_type=line_type
            )
            return
        to_delete, to_create, to_write = plan
        _debug.pipeline(
            "_apply_dynamic_line_plan",
            line_type=line_type,
            delete=len(to_delete),
            create=len(to_create),
            write=len(to_write),
        )

        recyclable = defaultdict(list)
        for line in AccountMoveLine.browse([line.id for line in to_delete]).exists():
            recyclable[line.move_id.id].append(line)
        for key in list(to_create):
            candidates = recyclable.get(key.get("move_id"))
            if not candidates:
                continue
            candidates.pop().write(
                {**key, **to_create.pop(key), "display_type": line_type}
            )
        if leftover := [line for lines in recyclable.values() for line in lines]:
            AccountMoveLine.union(*leftover).with_context(dynamic_unlink=True).unlink()
        if to_create:
            AccountMoveLine.with_context(clean_context(self.env.context)).create(
                [
                    {**key, **values, "display_type": line_type}
                    for key, values in to_create.items()
                ]
            )
        for line, values in to_write.items():
            line.write(values)

    @_debug.perf.timed
    def _sync_invoice(self, container):
        def commercial_partner_by_move():
            return {
                move: move.commercial_partner_id
                for move in container["records"].filtered(lambda m: m.is_invoice(True))
            }

        def commit(before):
            after = commercial_partner_by_move()
            line_ids_by_partner = defaultdict(set)
            for move, partner in after.items():
                if move not in before or before[move] != partner:
                    line_ids_by_partner[partner].update(move.line_ids.ids)

            for partner, line_ids in line_ids_by_partner.items():
                _debug.logic(
                    "_sync_invoice_commercial_changed",
                    line_ids_count=len(line_ids),
                    partner=partner,
                )
                self.env["account.move.line"].browse(line_ids).partner_id = partner

        return sync_boundary(commercial_partner_by_move, commit)

    @_debug.perf.timed
    def _get_sync_stack(self, container):
        tax_container, invoice_container, misc_container = ({} for _ in range(3))

        def update_containers():
            tax_container["records"] = container["records"].filtered(
                lambda m: (
                    m.is_invoice(True)
                    or m.line_ids.tax_ids
                    or m.line_ids.tax_repartition_line_id
                )
            )
            invoice_container["records"] = container["records"].filtered(
                lambda m: m.is_invoice(True)
            )
            misc_container["records"] = container["records"].filtered(
                lambda m: m.is_entry() and not m.tax_cash_basis_origin_move_id
            )
            _debug.pipeline(
                "sync_containers_updated",
                moves=container["records"],
                tax=tax_container["records"],
                invoice=invoice_container["records"],
                misc=misc_container["records"],
            )

            return tax_container, invoice_container, misc_container

        stack = [
            self._sync_invoice(invoice_container),
            self._sync_dynamic_line(
                existing_key_fname="epd_key",
                needed_vals_fname="line_ids.epd_needed",
                needed_dirty_fname="line_ids.epd_dirty",
                line_type="epd",
                container=invoice_container,
            ),
            self._sync_non_deductible_base_lines(invoice_container),
            self._sync_tax_lines(tax_container),
            self._sync_dynamic_line(
                existing_key_fname="discount_allocation_key",
                needed_vals_fname="line_ids.discount_allocation_needed",
                needed_dirty_fname="line_ids.discount_allocation_dirty",
                line_type="discount",
                container=invoice_container,
            ),
            self._sync_rounding_lines(invoice_container),
            self._sync_unbalanced_lines(misc_container),
            self._sync_dynamic_line(
                existing_key_fname="term_key",
                needed_vals_fname="needed_terms",
                needed_dirty_fname="needed_terms_dirty",
                line_type="payment_term",
                container=invoice_container,
            ),
        ]

        return stack, update_containers

    @contextmanager
    def _sync_dynamic_lines(self, container):
        with self._disable_recursion("skip_invoice_sync") as disabled:
            if disabled:
                _debug.logic(
                    "_sync_dynamic_lines_skipped_recursion_guard",
                    records=container["records"],
                )
                yield
                return

            _debug.pipeline("_sync_dynamic_lines_enter", records=container["records"])
            stack_list, update_containers = self._get_sync_stack(container)
            update_containers()
            with ExitStack() as stack:
                for contextmgr in reversed(stack_list):
                    stack.enter_context(contextmgr)

                line_container = {"records": container["records"].line_ids}
                with container["records"].line_ids._sync_invoice(line_container):
                    yield  # noqa: RUF075 - deliberate, same reason as sync_boundary: an exception here aborts the transaction, so the skipped refresh changes nothing that would otherwise persist
                    line_container["records"] = container["records"].line_ids
                update_containers()
