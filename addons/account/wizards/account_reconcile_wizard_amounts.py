from odoo import api, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountReconcileWizard(models.TransientModel):
    _inherit = "account.reconcile.wizard"

    def _get_reco_currency(self, amls, aml_values_map):
        company_currency = amls.company_currency_id
        foreign_currencies = amls.currency_id - company_currency
        _debug.logic(
            "reco_currency_inputs",
            amls=amls,
            company_currency=company_currency,
            foreign_currencies=foreign_currencies,
        )
        if len(foreign_currencies) == 0:
            return company_currency
        if len(foreign_currencies) == 1:
            return foreign_currencies

        lines_with_residuals = self.env["account.move.line"]
        for residual, residual_values in aml_values_map.items():
            if (
                residual_values["amount_residual"]
                or residual_values["amount_residual_currency"]
            ):
                lines_with_residuals += residual
                if (
                    lines_with_residuals
                    and len(lines_with_residuals.currency_id - company_currency) > 1
                ):
                    _debug.logic(
                        "reco_currency_ambiguous",
                        amls=amls,
                        residual_lines=lines_with_residuals,
                    )
                    return False
        return (lines_with_residuals.currency_id - company_currency) or company_currency

    def _get_simulated_residuals(self, amls, shadowed_aml_values):
        plan_list, all_amls = amls._optimize_reconciliation_plan(
            [amls], shadowed_aml_values=shadowed_aml_values
        )

        all_amls.fetch(["move_id", "matched_debit_ids", "matched_credit_ids"])

        aml_values_map = {
            aml: {
                "aml": aml,
                "amount_residual": aml.amount_residual,
                "amount_residual_currency": aml.amount_residual_currency,
            }
            for aml in all_amls
        }
        amls._prepare_reconciliation_plan(
            plan_list[0], aml_values_map, shadowed_aml_values=shadowed_aml_values
        )
        return aml_values_map

    def _get_reco_rate_bounds(self, amls, reco_currency):
        most_recent_line = max(amls, key=lambda aml: aml.date)
        if not most_recent_line.amount_currency:
            _debug.logic(
                "reco_rate_bounds_chosen", line=most_recent_line, source="no_amount"
            )
            return 0.0, 0.0, 0.0
        if most_recent_line.currency_id == reco_currency:
            _debug.logic(
                "reco_rate_bounds_chosen", line=most_recent_line, source="line_rate"
            )
            rate = abs(most_recent_line.balance / most_recent_line.amount_currency)
            rate_tolerance = (
                amls.company_currency_id.rounding
                / 2
                / abs(most_recent_line.amount_currency)
            )
            return rate, rate - rate_tolerance, rate + rate_tolerance
        rate = self.env["res.currency"]._get_conversion_rate(
            reco_currency,
            amls.company_currency_id,
            amls.company_id,
            most_recent_line.date,
        )
        _debug.logic(
            "reco_rate_bounds_chosen",
            line=most_recent_line,
            source="conversion_rate",
            currency=reco_currency,
            rate=rate,
        )
        return rate, rate, rate

    @api.depends("move_line_ids")
    @_debug.perf.timed
    def _compute_reco_wizard_data(self):
        for wizard in self:
            amls = wizard.move_line_ids._origin
            accounts = amls.account_id

            wizard.reco_currency_id = False
            wizard.amount_currency = wizard.amount = 0.0
            wizard.force_partials = True
            wizard.transfer_from_account_id = wizard.transfer_warning_message = False
            wizard.is_transfer_required = len(accounts) == 2
            if wizard.is_transfer_required:
                wizard.update(wizard._prepare_transfer_data(amls))
            else:
                wizard.reco_account_id = accounts

            _debug.logic(
                "transfer_requirement_decided",
                recwizard=wizard,
                amls=len(amls),
                accounts=len(accounts),
                transfer_required=wizard.is_transfer_required,
            )
            shadowed_aml_values = {
                aml: {"account_id": wizard.reco_account_id} for aml in amls
            }
            aml_values_map = wizard._get_simulated_residuals(amls, shadowed_aml_values)

            reco_currency = wizard._get_reco_currency(amls, aml_values_map)
            _debug.logic(
                "reco_currency_candidate",
                recwizard=wizard,
                currency=reco_currency,
                skipped=not reco_currency,
            )
            if not reco_currency:
                continue

            residual_amounts = {
                aml: aml._prepare_move_line_residual_amounts(
                    aml_values, reco_currency, shadowed_aml_values=shadowed_aml_values
                )
                for aml, aml_values in aml_values_map.items()
            }

            if all(
                reco_currency in residual_values
                for residual_values in residual_amounts.values()
                if residual_values
            ):
                wizard.reco_currency_id = reco_currency
            elif all(
                amls.company_currency_id in residual_values
                for residual_values in residual_amounts.values()
                if residual_values
            ):
                wizard.reco_currency_id = amls.company_currency_id
                reco_currency = wizard.reco_currency_id
            else:
                continue

            _debug.logic(
                "reco_currency_chosen",
                recwizard=wizard,
                currency=reco_currency,
            )
            rate, rate_lower_bound, rate_upper_bound = wizard._get_reco_rate_bounds(
                amls, reco_currency
            )
            amls_at_the_reconciliation_rate = {
                aml
                for aml in residual_amounts
                if (
                    aml.currency_id == reco_currency
                    and abs(aml.balance)
                    >= aml.company_currency_id.round(
                        abs(aml.amount_currency) * rate_lower_bound
                    )
                    and abs(aml.balance)
                    <= aml.company_currency_id.round(
                        abs(aml.amount_currency) * rate_upper_bound
                    )
                )
            }

            wizard.amount_currency = sum(
                residual_values[wizard.reco_currency_id]["residual"]
                for residual_values in residual_amounts.values()
                if residual_values
            )
            amount_raw = sum(
                (
                    residual_values[amls.company_currency_id]["residual"]
                    if aml in amls_at_the_reconciliation_rate
                    and amls.company_currency_id in residual_values
                    else residual_values[wizard.reco_currency_id]["residual"] * rate
                )
                for aml, residual_values in residual_amounts.items()
                if residual_values
            )
            wizard.amount = amls.company_currency_id.round(amount_raw)
            wizard.force_partials = False
            _debug.pipeline(
                "reco_amounts_computed",
                recwizard=wizard,
                rate=rate,
                amls_at_rate=len(amls_at_the_reconciliation_rate),
                amount_currency=wizard.amount_currency,
                amount=wizard.amount,
            )

    @api.depends("move_line_ids")
    def _compute_edit_mode_amount_currency(self):
        for wizard in self:
            if wizard.edit_mode:
                wizard.edit_mode_amount_currency = wizard.amount_currency
            else:
                wizard.edit_mode_amount_currency = 0.0

    @api.depends("edit_mode_amount_currency")
    @_debug.perf.timed
    def _compute_edit_mode_amount(self):
        for wizard in self:
            if wizard.edit_mode:
                single_line = wizard.move_line_ids
                rate = (
                    abs(single_line.amount_currency / single_line.balance)
                    if single_line.balance
                    else 0.0
                )
                wizard.edit_mode_amount = (
                    single_line.company_currency_id.round(
                        wizard.edit_mode_amount_currency / rate
                    )
                    if rate
                    else 0.0
                )
            else:
                wizard.edit_mode_amount = 0.0

    @api.depends("move_line_ids")
    def _compute_edit_mode_reco_currency_id(self):
        for wizard in self:
            if wizard.edit_mode:
                wizard.edit_mode_reco_currency_id = wizard.move_line_ids.currency_id
            else:
                wizard.edit_mode_reco_currency_id = False

    @api.depends("move_line_ids")
    def _compute_edit_mode(self):
        for wizard in self:
            wizard.edit_mode = len(wizard.move_line_ids) == 1
