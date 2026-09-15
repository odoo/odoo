from odoo import Command, _, models
from odoo.exceptions import UserError, ValidationError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    def _get_counterpart_aml(
        self, open_balance, open_amount_currency, is_same_currency
    ):
        self.check_singleton()
        currency = (
            self.foreign_currency_id
            or self.currency_id
            or self.journal_id.currency_id
            or self.company_id.currency_id
        )
        return {
            "name": self.payment_ref,
            "account_id": self.journal_id.suspense_account_id.id,
            "balance": -open_balance,
            "currency_id": currency.id,
            "amount_currency": -open_amount_currency
            if is_same_currency
            else currency.round(
                -open_balance * currency.with_company(self.company_id).rate
            ),
        }

    @_debug.perf.timed
    def _set_move_line_to_statement_line_move(self, lines_to_set, lines_to_add):
        self.check_singleton()

        lines_to_add_balance = sum(line["balance"] for line in lines_to_add)
        lines_commands = [Command.set(lines_to_set.ids)] + [
            Command.create(line_to_add) for line_to_add in lines_to_add
        ]

        open_balance = sum(lines_to_set.mapped("balance")) + lines_to_add_balance
        _debug.pipeline(
            "set_lines_keep_add_open",
            stline=self,
            lines_to_set=lines_to_set,
            lines_to_add_count=len(lines_to_add),
            open_balance=open_balance,
        )
        if not self.company_currency_id.is_zero(open_balance):
            if not self.foreign_currency_id:
                lines_to_add_amount_currency = sum(
                    line["amount_currency"] for line in lines_to_add
                )
                open_amount_currency = (
                    sum(lines_to_set.mapped("amount_currency"))
                    + lines_to_add_amount_currency
                )
                is_same_currency = len(lines_to_set.currency_id) == 1 and all(
                    line["currency_id"] == lines_to_set.currency_id.id
                    for line in lines_to_add
                )
            else:
                liquidity_lines, _suspense_lines, _other_lines = self._seek_for_lines()
                lines_to_add_amount_currency = sum(
                    line["amount_currency"] for line in lines_to_add
                )
                open_amount_currency = (
                    self.amount_currency
                    + sum((lines_to_set - liquidity_lines).mapped("amount_currency"))
                    + lines_to_add_amount_currency
                )
                is_same_currency = len(lines_to_set.currency_id) == 1 and all(
                    line["currency_id"] == self.foreign_currency_id.id
                    for line in lines_to_add
                )
            lines_commands.append(
                Command.create(
                    self._get_counterpart_aml(
                        open_balance, open_amount_currency, is_same_currency
                    )
                )
            )
        move = self.move_id.with_context(force_delete=True, skip_readonly_check=True)
        with _debug.perf("rewrite_move_lines", cr=self.env.cr, stline=self):
            move.line_ids = lines_commands

        if self.env.context.get("recompute_partner"):
            partner_id = self._get_partner_id(
                {line["partner_id"] for line in lines_to_add if line.get("partner_id")}
            )
            partner = self.env["res.partner"].browse(partner_id)
            if partner:
                allowed_companies = partner.company_id.root_id
                if len(lines_to_set.company_id) == 1:
                    allowed_companies |= lines_to_set.company_id
                if not partner.company_id or partner.company_id in allowed_companies:
                    move.line_ids.filtered(
                        lambda line: not line.partner_id
                    ).partner_id = partner

        if self.account_number and self.partner_id:
            self.with_context(
                skip_account_move_synchronization=True,
                skip_readonly_check=True,
            ).partner_bank_id = self._get_or_create_bank_account()

        self._post_matching_done_confirmation()

    def _add_move_line_to_statement_line_move(self, lines_to_add):
        self.check_singleton()
        liquidity_lines, _suspense_lines, other_lines = self._seek_for_lines()
        self._set_move_line_to_statement_line_move(
            liquidity_lines + other_lines, lines_to_add
        )

    @_debug.perf.timed
    def set_account_bank_statement_line(self, aml_id, account_id):
        account = self.env["account.account"].browse(account_id)
        statement_lines = self

        base_lines = self.env["account.move.line"].browse(aml_id)
        if len(base_lines) != len(statement_lines):
            raise UserError(
                _(
                    "Expected one journal item per transaction, got %(lines)s for "
                    "%(transactions)s.",
                    lines=len(base_lines),
                    transactions=len(statement_lines),
                )
            )
        _debug.pipeline(
            "account_assignment_started",
            stline=statement_lines,
            account=account,
            lines=len(base_lines),
        )
        for statement_line, base_line in zip(statement_lines, base_lines, strict=True):
            reserved_accounts = (
                statement_line.journal_id.suspense_account_id
                | statement_line.journal_id.default_account_id
            )
            statement_line._create_account_model_fee(account_id)
            if account.tax_ids:
                original_base_lines, original_tax_lines = (
                    statement_line._prepare_for_tax_lines_recomputation()
                )

            base_line.account_id = account
            base_line.move_id._compute_checked()

            if account.tax_ids:
                statement_line._create_tax_lines(
                    original_base_lines, original_tax_lines, base_line
                )
                base_line = statement_line.line_ids.filtered(lambda line: line.tax_ids)[
                    -1:
                ]

            if _debug.logic.enabled:
                _debug.logic(
                    "account_assignment_outcome",
                    stline=statement_line,
                    account=account,
                    with_taxes=bool(account.tax_ids),
                    confirm_only=account.account_type
                    in {"asset_receivable", "liability_payable"}
                    or account in reserved_accounts,
                )
            if (
                account.account_type in {"asset_receivable", "liability_payable"}
                or account in reserved_accounts
            ):
                statement_line._post_matching_done_confirmation()
                continue

            statement_lines |= statement_line._create_automatic_reconciliation_model(
                base_line, account
            )
        return statement_lines

    @_debug.perf.timed
    def set_line_bank_statement_line(self, move_lines_ids):
        self.check_singleton()
        move_lines = self.env["account.move.line"].search(
            [
                ("id", "in", move_lines_ids),
                ("reconciled", "=", False),
            ],
            order="sequence DESC, id",
        )
        _debug.pipeline(
            "unreconciled_lines_found",
            stline=self,
            move_lines=move_lines,
            skipped=not move_lines,
        )
        if not move_lines:
            return

        _liquidity_line, _suspense_lines, other_lines = self._seek_for_lines()

        (
            transaction_amount,
            transaction_currency,
            _journal_amount,
            _journal_currency,
            company_amount,
            company_currency,
        ) = self._get_accounting_amounts_and_currencies()

        open_balance = company_amount
        open_amount_currency = transaction_amount

        for line in other_lines:
            open_balance += line.balance
            open_amount_currency += self._convert_amount_to_transaction_currency(
                line.currency_id, line.amount_currency, line.balance
            )

        new_lines = []
        has_exchange_diff = False
        stop_reco_at_first_partial = self.env.context.get("stop_reco_at_first_partial")
        partial_applied = False
        for move_line in move_lines:
            exchange_diff_balance = self._lines_get_account_balance_exchange_diff(
                move_line.currency_id,
                move_line.amount_residual,
                move_line.amount_residual_currency,
            )
            current_balance = -(move_line.amount_residual + exchange_diff_balance)
            current_amount_currency = self._convert_amount_to_transaction_currency(
                move_line.currency_id,
                move_line.amount_residual_currency,
                move_line.amount_residual,
            )

            has_exchange_diff = has_exchange_diff or not move_line.currency_id.is_zero(
                exchange_diff_balance
            )
            open_balance += current_balance
            open_amount_currency -= current_amount_currency

            new_line_balance = current_balance
            new_amount_currency = -move_line.amount_residual_currency

            if move_line == move_lines[-1] or stop_reco_at_first_partial:
                partial_amounts = (
                    self._get_partial_amounts(
                        current_balance, move_line, open_amount_currency, open_balance
                    )
                    if (
                        company_currency.compare_amounts(open_balance, 0) < 0
                        if company_currency.compare_amounts(company_amount, 0) > 0
                        else company_currency.compare_amounts(open_balance, 0) > 0
                    )
                    else None
                )
                if partial_amounts and not company_currency.is_zero(
                    partial_amounts["partial_balance"]
                ):
                    new_line_balance = partial_amounts["partial_balance"]
                    new_amount_currency = partial_amounts["partial_amount_currency"]
                    partial_applied = True

            new_lines_to_add = [
                move_line._prepare_aml_values(
                    balance=new_line_balance,
                    amount_currency=new_amount_currency,
                    currency_id=move_line.currency_id.id,
                    reconciled_lines_ids=[Command.set(move_line.ids)],
                )
            ]
            self.move_id._compute_checked()

            lines_with_epd, total_amount, total_amount_currency = (
                self._apply_early_payment_discount(
                    move_line,
                    open_amount_currency,
                    transaction_currency,
                    exchange_diff_balance,
                )
            )
            if lines_with_epd:
                open_balance -= total_amount + current_balance
                open_amount_currency += current_amount_currency - total_amount_currency

            new_lines.extend(lines_with_epd or new_lines_to_add)
            if stop_reco_at_first_partial and (
                partial_applied or company_currency.is_zero(open_balance)
            ):
                break

        _debug.logic(
            "matched_lines_balanced",
            stline=self,
            new_lines=len(new_lines),
            open_balance=open_balance,
            partial_applied=partial_applied,
            has_exchange_diff=has_exchange_diff,
            stop_at_first_partial=bool(stop_reco_at_first_partial),
        )
        self.with_context(
            no_exchange_difference_no_recursive=not has_exchange_diff,
            recompute_partner=True,
        )._add_move_line_to_statement_line_move(new_lines)

    @_debug.perf.timed
    def remove_reconciled_line(self, move_line_ids):
        self.check_singleton()
        if (
            self.checked
            and self.is_reconciled
            and not self.move_id._is_user_able_to_review()
        ):
            raise ValidationError(
                _("Validated entries can only be changed by your accountant.")
            )

        move_lines_to_remove = self.env["account.move.line"].browse(move_line_ids)
        if (
            _debug.logic.enabled
            and move_lines_to_remove.tax_line_id
            and not move_lines_to_remove.account_id.reconcile
        ):
            _debug.logic(
                "tax_line_removal_ignored",
                stline=self,
                move_lines=move_lines_to_remove,
            )
        if (
            move_lines_to_remove.tax_line_id
            and not move_lines_to_remove.account_id.reconcile
        ):
            return

        liquidity_line, _suspense_lines, other_lines = self._seek_for_lines()
        reco_model_id = move_lines_to_remove.reconcile_model_id[:1]
        if move_lines_to_remove_has_tax := move_lines_to_remove.tax_ids:
            original_base_lines, original_tax_lines = (
                self._prepare_for_tax_lines_recomputation()
            )

        _debug.pipeline(
            "reconciled_lines_removing",
            stline=self,
            move_lines=move_lines_to_remove,
            reco_model=reco_model_id,
            with_taxes=bool(move_lines_to_remove_has_tax),
            kept_other=len(other_lines),
        )
        move_lines_to_remove.remove_move_reconcile()
        self._set_move_line_to_statement_line_move(
            liquidity_line + other_lines - move_lines_to_remove,
            [],
        )
        self._post_matching_unreconciled()
        if reco_model_id:
            self._action_manual_reco_model(reco_model_id)

        if move_lines_to_remove_has_tax:
            self._remove_tax_lines(
                original_base_lines, original_tax_lines, move_lines_to_remove
            )

    @_debug.perf.timed
    def edit_reconcile_line(self, move_line_id, record_data):
        self.check_singleton()
        if (
            self.checked
            and self.is_reconciled
            and not self.move_id._is_user_able_to_review()
        ):
            raise ValidationError(
                _("Validated entries can only be changed by your accountant.")
            )

        move_line_to_edit = self.env["account.move.line"].browse(move_line_id)

        if record_data.get("account_id"):
            move_line_to_edit.analytic_line_ids.with_context(
                skip_analytic_sync=True
            ).unlink()

        if (
            _debug.logic.enabled
            and move_line_to_edit.tax_line_id
            and any(
                record_data.get(key) for key in ["tax_ids", "partner_id", "account_id"]
            )
        ):
            _debug.logic(
                "tax_line_edit_ignored",
                stline=self,
                line=move_line_to_edit,
            )
        if move_line_to_edit.tax_line_id and any(
            record_data.get(key) for key in ["tax_ids", "partner_id", "account_id"]
        ):
            return

        exchange_line = self.env["account.move.line"]
        if (
            exchange_move := move_line_to_edit._get_matched_move_ids().exchange_move_id
        ) and any(record_data.get(key) for key in ["balance", "amount_currency"]):
            exchange_line |= exchange_move.line_ids.filtered(
                lambda line: line in move_line_to_edit.reconciled_lines_ids
            )

        liquidity_lines, _suspense_lines, other_lines = self._seek_for_lines()

        original_base_lines = original_tax_lines = None
        if (
            not move_line_to_edit.reconciled_lines_ids
            and any(
                record_data.get(key)
                for key in ["tax_ids", "balance", "amount_currency"]
            )
            and not move_line_to_edit.tax_line_id
            and not exchange_move
        ):
            original_base_lines, original_tax_lines = (
                self._prepare_for_tax_lines_recomputation()
            )

        edited_move_reconciled_line_ids = (
            move_line_to_edit.reconciled_lines_ids - exchange_line
        ).ids
        if _debug.logic.enabled:
            _debug.logic(
                "edit_mode_resolved",
                stline=self,
                line=move_line_to_edit,
                edited_keys=sorted(record_data),
                exchange_move=exchange_move,
                exchange_lines=len(exchange_line),
                tax_recompute=original_base_lines is not None,
                reconciled_kept=len(edited_move_reconciled_line_ids),
            )
        move_line_to_edit.remove_move_reconcile()
        move_line_to_edit_vals = move_line_to_edit._prepare_aml_values(**record_data)
        if edited_move_reconciled_line_ids:
            move_line_to_edit_vals["reconciled_lines_ids"] = [
                Command.set(edited_move_reconciled_line_ids)
            ]

        self._set_move_line_to_statement_line_move(
            (liquidity_lines + other_lines) - move_line_to_edit,
            [move_line_to_edit_vals],
        )
        _new_liquidity_lines, new_suspense_lines, _new_other_lines = (
            self._seek_for_lines()
        )
        edited_line = self.line_ids - (
            liquidity_lines + other_lines + new_suspense_lines
        )

        if (
            not edited_line.reconciled_lines_ids
            and any(
                record_data.get(key)
                for key in ["tax_ids", "balance", "amount_currency"]
            )
            and not edited_line.tax_line_id
            and not exchange_move
        ):
            self._edit_tax_lines(
                original_base_lines, original_tax_lines, edited_line, move_line_to_edit
            )

        if "partner_id" in record_data and not record_data["partner_id"]:
            edited_line.partner_id = False
