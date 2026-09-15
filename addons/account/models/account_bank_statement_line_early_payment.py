from odoo import Command, api, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import float_is_zero

_debug = DebugLog(__name__)


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    def _convert_amount_to_transaction_currency(
        self, currency_id, amount_currency, balance
    ):
        (
            transaction_amount,
            transaction_currency,
            journal_amount,
            journal_currency,
            company_amount,
            _company_currency,
        ) = self._get_accounting_amounts_and_currencies()

        if currency_id == transaction_currency:
            return amount_currency
        if currency_id == journal_currency:
            journal_transaction_rate = (
                abs(transaction_amount / journal_amount) if journal_amount else 0.0
            )
            return transaction_currency.round(
                amount_currency * journal_transaction_rate
            )
        company_transaction_rate = (
            abs(transaction_amount / company_amount) if company_amount else 0.0
        )
        return transaction_currency.round(balance * company_transaction_rate)

    @_debug.perf.timed
    def _apply_early_payment_discount(
        self,
        move_line,
        open_amount_currency,
        transaction_currency,
        exchange_diff_balance,
    ):
        epd_lines_vals = []
        epd_amount_currency = (
            move_line.amount_currency - move_line.discount_amount_currency
        )
        total_amount = total_amount_currency = 0.0
        eligible = move_line.move_id._is_eligible_for_early_payment_discount(
            transaction_currency, self.date
        ) and self._qualifies_for_early_payment(
            transaction_currency, open_amount_currency, epd_amount_currency
        )
        _debug.logic(
            "early_payment_discount_line",
            stline=self,
            move_line=move_line,
            eligible=eligible,
            open=open_amount_currency,
            epd=epd_amount_currency,
        )
        if eligible:
            if not move_line.currency_id.is_zero(exchange_diff_balance):
                payment_with_move = self._create_payment_with_move_from_invoice(
                    move_line.move_id
                )
                payment_line_to_add = (
                    payment_with_move.move_id.line_ids.filtered_domain(
                        self._get_domain_default_amls_matching()
                    )
                )
                epd_lines_vals = [
                    payment_line_to_add._prepare_aml_values(
                        balance=-payment_line_to_add.balance,
                        amount_currency=-payment_line_to_add.amount_currency,
                        reconciled_lines_ids=[Command.set(payment_line_to_add.ids)],
                    )
                ]
                total_amount = payment_line_to_add.balance
                total_amount_currency = self._convert_amount_to_transaction_currency(
                    payment_line_to_add.currency_id,
                    payment_line_to_add.amount_currency,
                    payment_line_to_add.balance,
                )
            else:
                early_pay_aml_values_list = [
                    {
                        "aml": move_line,
                        "amount_currency": -move_line.amount_currency,
                        "balance": -move_line.amount_residual,
                    }
                ]
                epd_lines_vals = [
                    move_line._prepare_aml_values(
                        balance=-move_line.amount_residual,
                        amount_currency=-move_line.amount_residual_currency,
                        reconciled_lines_ids=[Command.set(move_line.ids)],
                    ),
                    *self._set_early_payment_discount_lines(
                        early_pay_aml_values_list, 0
                    ),
                ]
                for vals in epd_lines_vals:
                    total_amount -= vals["balance"]
                    total_amount_currency -= (
                        self._convert_amount_to_transaction_currency(
                            move_line.currency_id,
                            vals["amount_currency"],
                            vals["balance"],
                        )
                    )
        return epd_lines_vals, total_amount, total_amount_currency

    @_debug.perf.timed
    def _get_partial_amounts(
        self, current_balance, move_line, open_amount_currency, open_balance
    ):
        def has_enough(currency, open_amount, current_amount):
            return (
                currency.compare_amounts(open_amount, 0) > 0
                and currency.compare_amounts(current_amount, 0) > 0
                and currency.compare_amounts(current_amount, open_amount) > 0
            )

        (
            transaction_amount,
            transaction_currency,
            _journal_amount,
            _journal_currency,
            company_amount,
            company_currency,
        ) = self._get_accounting_amounts_and_currencies()
        has_enough_comp_debit = has_enough(
            company_currency, open_balance, current_balance
        )
        has_enough_comp_credit = has_enough(
            company_currency, -open_balance, -current_balance
        )
        current_amount_currency = -move_line.amount_residual_currency
        has_enough_curr_debit = has_enough(
            move_line.currency_id, open_amount_currency, current_amount_currency
        )
        has_enough_curr_credit = has_enough(
            move_line.currency_id, -open_amount_currency, -current_amount_currency
        )

        tolerance = self._get_payment_tolerance()
        if _debug.logic.enabled:
            _debug.logic(
                "partial_amount_mode_chosen",
                stline=self,
                line=move_line,
                same_currency=move_line.currency_id == transaction_currency,
                enough_currency=has_enough_curr_debit or has_enough_curr_credit,
                enough_company=has_enough_comp_debit or has_enough_comp_credit,
                tolerance=tolerance,
            )
        if move_line.currency_id == transaction_currency and (
            has_enough_curr_debit or has_enough_curr_credit
        ):
            new_amount_currency = (
                current_amount_currency
                if not float_is_zero(tolerance, 6)
                and move_line.currency_id.compare_amounts(
                    abs(open_amount_currency), tolerance * abs(current_amount_currency)
                )
                < 0
                else current_amount_currency - open_amount_currency
            )
            rate = (
                abs(company_amount / transaction_amount) if transaction_amount else 0.0
            )

            balance_after_partial = move_line.company_currency_id.round(
                new_amount_currency * rate
            )
            return {
                "partial_balance": balance_after_partial,
                "partial_amount_currency": new_amount_currency,
            }
        elif has_enough_comp_debit or has_enough_comp_credit:
            balance_after_partial = (
                current_balance
                if not float_is_zero(tolerance, 6)
                and move_line.currency_id.compare_amounts(
                    abs(open_balance), tolerance * abs(current_balance)
                )
                < 0
                else current_balance - open_balance
            )
            rate = move_line.currency_rate

            new_line_balance = move_line.company_currency_id.round(
                balance_after_partial
                * abs(move_line.amount_residual)
                / abs(current_balance)
            )
            new_amount_currency = move_line.currency_id.round(new_line_balance * rate)

            if (
                company_currency.compare_amounts(
                    new_line_balance, (-move_line.amount_residual_currency / rate)
                )
                == 0
            ):
                new_amount_currency = -move_line.amount_residual_currency

            return {
                "partial_balance": balance_after_partial,
                "partial_amount_currency": new_amount_currency,
            }
        return None

    def _get_payment_tolerance(self):
        if self.env.context.get("skip_payment_tolerance"):
            return 0.0
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param_float("account.bank_rec_payment_tolerance", 0.0)
        )

    def _lines_get_account_balance_exchange_diff(
        self, currency_id, amount, amount_currency
    ):
        amounts_in_st_curr = self._prepare_counterpart_amounts_using_st_line_rate(
            currency_id,
            amount,
            amount_currency,
        )
        transaction_currency_id = self.foreign_currency_id or self.currency_id
        origin_balance = amounts_in_st_curr["balance"]
        if (
            currency_id == self.company_currency_id
            and transaction_currency_id != self.company_currency_id
        ):
            origin_balance = amount
        elif (
            currency_id != self.company_currency_id
            and transaction_currency_id == self.company_currency_id
        ):
            origin_balance = currency_id._convert(
                amount_currency, transaction_currency_id, self.company_id, self.date
            )

        if currency_id.is_zero(origin_balance - amount):
            return 0.0

        return self.company_currency_id.round(origin_balance - amount)

    @api.model
    def _qualifies_for_early_payment(
        self, transaction_currency, open_amount_currency, total_early_payment_discount
    ):
        remaining = open_amount_currency + total_early_payment_discount
        if total_early_payment_discount < 0:
            return transaction_currency.compare_amounts(remaining, 0.0) <= 0
        return transaction_currency.compare_amounts(remaining, 0.0) >= 0

    @_debug.perf.timed
    def _set_early_payment_discount_lines(
        self, early_pay_aml_values_list, open_balance
    ):
        early_payment_values = self.env[
            "account.move"
        ]._get_invoice_counterpart_amls_for_early_payment_discount(
            early_pay_aml_values_list,
            -open_balance,
        )
        new_lines = []
        early_payment_values.pop("exchange_lines")

        for vals_list in early_payment_values.values():
            new_lines.extend(
                {
                    "account_id": vals["account_id"],
                    "date": self.date,
                    "name": vals["name"],
                    "partner_id": vals["partner_id"],
                    "currency_id": vals["currency_id"],
                    "amount_currency": vals["amount_currency"],
                    "balance": vals["balance"],
                    "analytic_distribution": vals.get("analytic_distribution"),
                    "tax_ids": vals.get("tax_ids", []),
                    "tax_tag_ids": vals.get("tax_tag_ids", []),
                    "tax_repartition_line_id": vals.get("tax_repartition_line_id"),
                    "group_tax_id": vals.get("group_tax_id"),
                }
                for vals in vals_list
            )
        if _debug.pipeline.enabled:
            _debug.pipeline(
                "early_payment_lines_built",
                stline=self,
                groups=sorted(early_payment_values),
                lines=len(new_lines),
                open_balance=open_balance,
            )
        return new_lines
