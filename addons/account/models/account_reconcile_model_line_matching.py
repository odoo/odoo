import json
import re
from math import copysign

from odoo import Command, api, models
from odoo.exceptions import RedirectWarning, UserError
from odoo.libs.debug_log import DebugLog
from odoo.libs.numbers import split_amount_str

_debug = DebugLog(__name__)


class AccountReconcileModelLine(models.Model):
    _inherit = "account.reconcile.model.line"

    @_debug.perf.timed
    def _prepare_aml_vals(self, partner):
        self.check_singleton()

        taxes = self.tax_ids or self.account_id.tax_ids
        if taxes and partner:
            fiscal_position = self.env["account.fiscal.position"]._get_fiscal_position(
                partner
            )
            if fiscal_position:
                taxes = fiscal_position.map_tax(taxes)
            _debug.logic(
                "reco_line_taxes_mapped",
                reco_model_line=self,
                partner=partner,
                fiscal_position=fiscal_position,
                taxes=taxes,
            )

        values = {
            "name": self.label,
            "partner_id": partner.id,
            "analytic_distribution": self.analytic_distribution,
            "reconcile_model_id": self.model_id.id,
        }
        if taxes:
            values["tax_ids"] = [Command.set(taxes.ids)]
        if self.account_id:
            values["account_id"] = self.account_id.id
        return values

    @_debug.perf.timed
    def _apply_in_manual_widget(
        self, residual_amount_currency, residual_balance, partner, st_line
    ):
        self.check_singleton()

        currency = (
            st_line.foreign_currency_id
            or st_line.journal_id.currency_id
            or st_line.company_currency_id
        )
        if self.amount_type == "percentage":
            amount_currency = currency.round(
                residual_amount_currency * (self.amount / 100.0)
            )
            balance = st_line.company_currency_id.round(
                residual_balance * (self.amount / 100.0)
            )
        elif self.amount_type == "fixed":
            sign = 1 if residual_amount_currency > 0.0 else -1
            amount_currency = currency.round(self.amount * sign)
            balance = st_line.company_currency_id.round(self.amount * sign)
        else:
            raise UserError(
                self.env._(
                    "%(model)s: a %(kind)s line resolves its amount from the statement "
                    "line, so it cannot be applied without one.",
                    model=self.model_id.display_name,
                    kind=self.amount_type,
                )
            )

        _debug.logic(
            "manual_line_amount_computed",
            stline=st_line,
            reco_model_line=self,
            amount_type=self.amount_type,
            balance=balance,
            amount_currency=amount_currency,
        )
        return {
            **self._prepare_aml_vals(partner),
            "currency_id": currency.id,
            "balance": balance,
            "amount_currency": amount_currency,
        }

    @_debug.perf.timed
    def _apply_in_bank_widget(
        self, residual_amount_currency, residual_balance, partner, st_line
    ):
        self.check_singleton()
        currency = (
            st_line.foreign_currency_id
            or st_line.journal_id.currency_id
            or st_line.company_currency_id
        )

        aml_values = {"currency_id": currency.id}

        if self.amount_type == "percentage_st_line":
            (
                _transaction_amount,
                _transaction_currency,
                journal_amount,
                journal_currency,
                company_amount,
                company_currency,
            ) = st_line._get_accounting_amounts_and_currencies()
            aml_values["amount_currency"] = currency.round(
                -journal_amount * self.amount / 100.0
            )
            aml_values["balance"] = company_currency.round(
                -company_amount * self.amount / 100.0
            )
            aml_values["currency_id"] = journal_currency.id
        elif self.amount_type == "regex":
            aml_values["amount_currency"] = self._get_amount_currency_by_regex(
                st_line, residual_amount_currency, self.amount_string
            )
            aml_values["balance"] = self._get_amount_currency_by_regex(
                st_line, residual_balance, self.amount_string
            )

        if "amount_currency" not in aml_values or "balance" not in aml_values:
            aml_values.update(
                self._apply_in_manual_widget(
                    residual_amount_currency=residual_amount_currency,
                    residual_balance=residual_balance,
                    partner=partner,
                    st_line=st_line,
                )
            )
        else:
            aml_values.update(self._prepare_aml_vals(partner))

        if not aml_values.get("name"):
            aml_values["name"] = st_line.payment_ref
        _debug.logic(
            "reco_model",
            stline=st_line,
            line=self,
            amount_type=self.amount_type,
            balance=aml_values.get("balance"),
            amount_currency=aml_values.get("amount_currency"),
            account=aml_values.get("account_id"),
        )

        return aml_values

    @api.model
    @_debug.perf.timed
    def _get_amount_currency_by_regex(
        self, st_line, residual_amount_currency, amount_string
    ):
        sign = 1 if residual_amount_currency > 0.0 else -1
        transaction_details = (
            json.dumps(st_line.transaction_details)
            if st_line.transaction_details
            else False
        )
        for target_field in (
            st_line.payment_ref,
            transaction_details,
            st_line.narration,
        ):
            if not target_field:
                continue
            if match := re.search(amount_string, target_field):
                try:
                    groups = match.groups()
                    if len(groups) >= 2:
                        group_iter = iter(groups)
                        int_part = (
                            str(next(group_iter) or "0")
                            .replace(".", "")
                            .replace(",", "")
                        )
                        dec_part = next(group_iter, None)
                        dec_part = dec_part if dec_part and dec_part.isdigit() else "0"
                        extracted_balance = float(f"{int_part}.{dec_part}")
                    else:
                        extracted_match_group = re.search(
                            r"\d[\d\s.,'\xa0]*", match.group(1)
                        )
                        int_part, dec_part = split_amount_str(
                            extracted_match_group.group()
                        )
                        extracted_balance = float(f"{int_part}.{dec_part}")
                    _debug.logic(
                        "regex_amount_extracted",
                        stline=st_line,
                        groups=len(groups),
                        extracted=extracted_balance,
                    )
                    return copysign(extracted_balance * sign, residual_amount_currency)
                except IndexError:
                    raise RedirectWarning(
                        self.env._(
                            "The regular expression for capturing the counterpart amount appears to be incorrectly formatted.\n"
                            "Please make sure that the part of the regex capturing the amount is the first (or only) one in parentheses, for example: BRT: ([\\d,.]+)."
                        ),
                        self.model_id._get_records_action(),
                        self.env._("Open reconcile model"),
                    ) from None
                except AttributeError:
                    raise RedirectWarning(
                        self.env._(
                            "The regular expression for capturing the counterpart amount appears to be incorrectly formatted.\n"
                            "Please make sure that the part of the regex capturing the amount (in parentheses) cannot capture an empty value (usually by an incorrect use of ? or *) "
                            "or any value with no digit. For example: BRT: ([\\d,.]+)."
                        ),
                        self.model_id._get_records_action(),
                        self.env._("Open reconcile model"),
                    ) from None
        _debug.logic("regex_amount_not_found", stline=st_line)
        return 0.0
