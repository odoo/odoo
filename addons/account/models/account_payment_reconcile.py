from collections import defaultdict

from odoo import Command, models
from odoo.libs.debug_log import DebugLog
from odoo.libs.numbers import float_compare

_debug = DebugLog(__name__)


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @_debug.perf.timed
    def action_view_manual_reconciliation_widget(self):
        _debug.lifecycle("action_view_manual_reconciliation_widget", records=self)
        self.check_singleton()
        if not self.partner_id:
            return self.env["account.move.line"]._action_view_unreconciled()
        extra_context = {"search_default_partner_id": self.partner_id.id}
        if self.partner_type == "customer":
            extra_context["search_default_trade_receivable"] = 1
        elif self.partner_type == "supplier":
            extra_context["search_default_trade_payable"] = 1
        return self.env["account.move.line"]._action_view_unreconciled(
            extra_context=extra_context,
        )

    @_debug.perf.timed
    def button_open_statement_lines(self):
        _debug.lifecycle("button_open_statement_lines", records=self)
        self.check_singleton()

        default_statement_line = self.reconciled_statement_line_ids[-1]
        return self.env[
            "account.bank.statement.line"
        ]._action_view_bank_reconciliation_widget(
            extra_domain=[("id", "in", self.reconciled_statement_line_ids.ids)],
            default_context={
                "create": False,
                "default_st_line_id": default_statement_line.id,
                "default_journal_id": default_statement_line.journal_id.id,
            },
            name=self.env._("Matched Transactions"),
        )

    def _get_open_payment_term_lines(self):
        self.check_singleton()
        return self.invoice_ids.line_ids.filtered(
            lambda line: (
                line.display_type == "payment_term"
                and not line.reconciled
                and not line.currency_id.is_zero(line.amount_residual_currency)
            )
        ).sorted("date")

    @_debug.perf.timed
    def _get_amls_for_payment_without_move(self, date=None):
        valid_payment_states = ["draft", *self._valid_payment_states()]
        lines_to_create = []
        for payment in self:
            if payment.state not in valid_payment_states:
                continue

            company_currency = payment.company_id.currency_id
            rate_date = date or payment.date
            line2amount = defaultdict(float)

            payment_term_lines = payment._get_open_payment_term_lines()
            remaining = payment.amount_signed
            for line in payment_term_lines:
                if payment.currency_id.is_zero(remaining):
                    break

                line_amount = line.currency_id._convert(
                    from_amount=line.amount_residual_currency,
                    to_currency=payment.currency_id,
                    company=payment.company_id,
                    date=rate_date,
                )
                if (
                    float_compare(
                        payment.amount_signed, 0, payment.currency_id.decimal_places
                    )
                    >= 0
                ):
                    current = min(remaining, line_amount)
                else:
                    current = max(remaining, line_amount)
                remaining -= current
                line2amount[line] -= current

            if not payment.currency_id.is_zero(remaining):
                line2amount[False] -= remaining
            _debug.logic(
                "amls_without_move_line",
                payment=payment,
                payment_term_lines_count=len(payment_term_lines),
                unallocated=remaining,
            )

            for line, amount in line2amount.items():
                balance = payment.currency_id._convert(
                    from_amount=amount,
                    to_currency=company_currency,
                    company=payment.company_id,
                    date=rate_date,
                )
                if line:
                    line_to_create = line._prepare_aml_values(
                        name=payment.name,
                        balance=balance,
                        amount_currency=amount,
                        reconciled_lines_ids=[Command.set(line.ids)],
                        payment_lines_ids=[Command.set(payment.ids)],
                    )
                else:
                    partner_account = (
                        payment.partner_id.property_account_payable_id
                        if payment.payment_type == "outbound"
                        else payment.partner_id.property_account_receivable_id
                    )
                    line_to_create = {
                        "name": payment.name,
                        "partner_id": payment.partner_id.id,
                        "account_id": partner_account.id,
                        "currency_id": payment.currency_id.id,
                        "amount_currency": amount,
                        "balance": balance,
                        "payment_lines_ids": [Command.set(payment.ids)],
                    }
                lines_to_create.append(line_to_create)
        return lines_to_create

    def _get_aml_amount_in_payment_currency(self, aml):
        self.check_singleton()
        comp_curr = aml.company_id.currency_id
        if self.currency_id == aml.currency_id:
            amount = aml.amount_residual_currency
        elif self.currency_id == comp_curr:
            amount = aml.currency_id._convert(
                from_amount=aml.amount_residual_currency,
                to_currency=self.currency_id,
                company=aml.company_id,
                date=self.date,
            )
        else:
            amount = comp_curr._convert(
                from_amount=aml.amount_residual,
                to_currency=self.currency_id,
                company=aml.company_id,
                date=self.date,
            )
        return amount

    def _supersede_with_payment_move(self, line, current_amount):
        self.check_singleton()
        valid_payment_states = ["draft", *self._valid_payment_states()]
        payment_with_move = line.move_id.matched_payment_ids.filtered(
            lambda pay: pay.move_id and pay.state in valid_payment_states
        )
        _debug.logic(
            "superseded_move",
            payment=self,
            payment_with_move=payment_with_move,
            line=line,
            amount=self.amount_signed,
            current=current_amount,
        )
        if self.currency_id.compare_amounts(self.amount_signed, current_amount) == 0:
            self.action_cancel()
            self.message_post(
                subject=self.env._("Canceled payment during reconciliation"),
                body=self.env._(
                    "A payment with entry was created for the related invoice during its "
                    "reconciliation, replacing this one: %(link)s.",
                    link=payment_with_move._get_html_link(),
                ),
            )
        else:
            self.invoice_ids -= line.move_id
            self.amount -= current_amount
            self.message_post(
                subject=self.env._("Modified amount during reconciliation"),
                body=self.env._(
                    "A payment with entry was created for an invoice previously linked to "
                    "this payment: %(link)s.\nIts amount was deducted from this payment.",
                    link=payment_with_move._get_html_link(),
                ),
            )

    @_debug.perf.timed
    def _get_amls_for_reconciliation(self, st_line):
        def get_current_amount(payment, line_amount, remaining):
            return (
                min(remaining, line_amount)
                if payment.currency_id.compare_amounts(payment.amount_signed, 0) >= 0
                else max(remaining, line_amount)
            )

        amls_to_create = []
        has_exchange_diff = False
        payments_with_move = self.filtered(lambda payment: payment.move_id)
        (
            _transaction_amount,
            transaction_currency,
            _journal_amount,
            _journal_currency,
            _company_amount,
            company_currency,
        ) = st_line._get_accounting_amounts_and_currencies()
        domain = st_line._get_domain_default_amls_matching()

        for payment in payments_with_move:
            liquidity_lines, _counterpart_lines, _writeoff_lines = (
                payment._seek_for_lines()
            )
            filtered_liquidity_lines = liquidity_lines.filtered_domain(domain)
            for payment_move_line in filtered_liquidity_lines:
                exchange_diff_balance = (
                    st_line._lines_get_account_balance_exchange_diff(
                        payment_move_line.currency_id,
                        payment_move_line.amount_residual,
                        payment_move_line.amount_residual_currency,
                    )
                )
                has_exchange_diff = (
                    has_exchange_diff
                    or not payment_move_line.currency_id.is_zero(exchange_diff_balance)
                )
                amls_to_create.append(
                    payment_move_line._prepare_aml_values(
                        balance=-(
                            payment_move_line.amount_residual + exchange_diff_balance
                        ),
                        amount_currency=-payment_move_line.amount_currency,
                        reconciled_lines_ids=[Command.set(payment_move_line.ids)],
                        payment_lines_ids=[Command.set(payment.ids)],
                    ),
                )

        valid_payment_states = ["draft", *self._valid_payment_states()]
        _debug.pipeline(
            "payment_liquidity_lines_collected",
            stline=st_line,
            payment=self,
            with_move=len(payments_with_move),
            amls=len(amls_to_create),
            has_exchange_diff=has_exchange_diff,
        )
        for payment in self - payments_with_move:
            if _debug.logic.enabled and payment.state not in valid_payment_states:
                _debug.logic(
                    "moveless_payment_state_skipped",
                    stline=st_line,
                    payment=payment,
                    state=payment.state,
                )
            if payment.state not in valid_payment_states:
                continue

            payment_term_lines = payment._get_open_payment_term_lines()
            remaining = payment.amount_signed
            for line in payment_term_lines:
                if payment.currency_id.is_zero(remaining):
                    break

                line_amount = payment._get_aml_amount_in_payment_currency(line)
                current_amount = get_current_amount(payment, line_amount, remaining)
                exchange_diff_balance = (
                    st_line._lines_get_account_balance_exchange_diff(
                        line.currency_id,
                        line.amount_residual,
                        line.amount_residual_currency,
                    )
                )
                amls_to_add = [
                    line._prepare_aml_values(
                        name=line.name,
                        balance=payment.currency_id._convert(
                            from_amount=-current_amount,
                            to_currency=company_currency,
                            company=st_line.company_id,
                            date=st_line.date,
                        ),
                        currency_id=payment.currency_id.id,
                        amount_currency=-current_amount,
                        reconciled_lines_ids=[Command.set(line.ids)],
                        payment_lines_ids=[Command.set(payment.ids)],
                    )
                ]

                if line.currency_id == payment.currency_id:
                    lines_with_epd, _total_amount, total_amount_currency = (
                        st_line._apply_early_payment_discount(
                            line,
                            current_amount - line_amount,
                            transaction_currency,
                            exchange_diff_balance,
                        )
                    )
                    amls_to_add = lines_with_epd or amls_to_add
                    current_amount = total_amount_currency or current_amount
                    if len(lines_with_epd) == 1:
                        payment._supersede_with_payment_move(line, current_amount)
                    elif lines_with_epd:
                        lines_with_epd[0]["payment_lines_ids"] = [
                            Command.set(payment.ids)
                        ]

                remaining -= current_amount
                amls_to_create.extend(amls_to_add)

            if _debug.logic.enabled:
                _debug.logic(
                    "moveless_payment_remainder",
                    stline=st_line,
                    payment=payment,
                    term_lines=len(payment_term_lines),
                    remaining=remaining,
                    to_partner_account=not payment.currency_id.is_zero(remaining),
                )
            if not payment.currency_id.is_zero(remaining):
                partner_account = (
                    payment.partner_id.property_account_payable_id
                    if payment.payment_type == "outbound"
                    else payment.partner_id.property_account_receivable_id
                )
                amls_to_create.append(
                    {
                        "name": payment.name,
                        "partner_id": payment.partner_id.id,
                        "account_id": partner_account.id,
                        "currency_id": payment.currency_id.id,
                        "amount_currency": -remaining,
                        "balance": payment.currency_id._convert(
                            from_amount=-remaining,
                            to_currency=company_currency,
                            company=st_line.company_id,
                            date=st_line.date,
                        ),
                        "payment_lines_ids": [Command.set(payment.ids)],
                    }
                )
        _debug.pipeline(
            "payment_reconciliation_amls_built",
            stline=st_line,
            payment=self,
            amls=len(amls_to_create),
            has_exchange_diff=has_exchange_diff,
        )
        return amls_to_create, has_exchange_diff
