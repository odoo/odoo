from odoo import Command, _, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountReconcileWizard(models.TransientModel):
    _inherit = "account.reconcile.wizard"

    @_debug.perf.timed
    def _prepare_write_off_taxes_data(self, partner):
        AccountTax = self.env["account.tax"]
        amount_currency = self.edit_mode_amount_currency or self.amount_currency
        amount = self.edit_mode_amount or self.amount
        if self.company_currency_id.is_zero(amount):
            rate = self.env["res.currency"]._get_conversion_rate(
                self.reco_currency_id,
                self.company_currency_id,
                self.company_id,
                self.date,
            )
        else:
            rate = abs(amount_currency / amount)
        _debug.logic(
            "write_off_rate_resolved",
            recwizard=self,
            edit_mode=bool(self.edit_mode_amount_currency),
            amount=amount,
            amount_currency=amount_currency,
            rate=rate,
        )
        tax_type = self.tax_id.type_tax_use if self.tax_id else None
        is_refund = (tax_type == "sale" and amount_currency > 0.0) or (
            tax_type == "purchase" and amount_currency < 0.0
        )
        base_line = AccountTax._prepare_base_line_for_taxes_computation(
            self,
            partner_id=partner,
            currency_id=self.reco_currency_id,
            tax_ids=self.tax_id,
            price_unit=amount_currency,
            quantity=1.0,
            account_id=self.account_id,
            is_refund=is_refund,
            rate=rate,
            special_mode="total_included",
        )
        base_lines = [base_line]
        AccountTax._add_tax_details_in_base_lines(base_lines, self.company_id)
        AccountTax._round_base_lines_tax_details(base_lines, self.company_id)
        AccountTax._add_accounting_data_in_base_lines_tax_details(
            base_lines, self.company_id, include_caba_tags=True
        )
        tax_results = AccountTax._prepare_tax_lines(base_lines, self.company_id)
        _base_line, base_to_update = tax_results["base_lines_to_update"][0]
        tax_lines_data = []
        tax_lines_data.extend(
            {
                "tax_amount": tax_line_vals["balance"],
                "tax_amount_currency": tax_line_vals["amount_currency"],
                "tax_tag_ids": tax_line_vals["tax_tag_ids"],
                "tax_account_id": tax_line_vals["account_id"],
            }
            for tax_line_vals in tax_results["tax_lines_to_add"]
        )
        base_amount_currency = base_to_update["amount_currency"]
        base_amount = amount - sum(entry["tax_amount"] for entry in tax_lines_data)
        _debug.pipeline(
            "write_off_taxes_computed",
            recwizard=self,
            tax=self.tax_id,
            is_refund=is_refund,
            tax_lines=len(tax_lines_data),
            base_amount=base_amount,
        )

        return {
            "base_amount": base_amount,
            "base_amount_currency": base_amount_currency,
            "base_tax_tag_ids": base_to_update["tax_tag_ids"],
            "tax_lines_data": tax_lines_data,
        }

    @_debug.perf.timed
    def _create_write_off_lines(self, partner=None):
        if not partner:
            partner = self.env["res.partner"]
        to_partner = self.to_partner_id if self.is_rec_pay_account else partner
        tax_data = (
            self._prepare_write_off_taxes_data(to_partner) if self.tax_id else None
        )
        amount_currency = self.edit_mode_amount_currency or self.amount_currency
        amount = self.edit_mode_amount or self.amount
        line_ids_commands = [
            Command.create(
                {
                    "name": self.label or _("Write-Off"),
                    "account_id": self.reco_account_id.id,
                    "partner_id": partner.id,
                    "currency_id": self.reco_currency_id.id,
                    "amount_currency": -amount_currency,
                    "balance": -amount,
                }
            ),
            Command.create(
                {
                    "name": self.label,
                    "account_id": self.account_id.id,
                    "partner_id": to_partner.id,
                    "currency_id": self.reco_currency_id.id,
                    "tax_ids": self.tax_id.ids,
                    "tax_tag_ids": None
                    if not tax_data
                    else tax_data["base_tax_tag_ids"],
                    "amount_currency": amount_currency
                    if not tax_data
                    else tax_data["base_amount_currency"],
                    "balance": amount if not tax_data else tax_data["base_amount"],
                }
            ),
        ]
        if tax_data:
            line_ids_commands.extend(
                Command.create(
                    {
                        "name": self.tax_id.name,
                        "account_id": tax_datum["tax_account_id"],
                        "partner_id": to_partner.id,
                        "currency_id": self.reco_currency_id.id,
                        "tax_tag_ids": tax_datum["tax_tag_ids"],
                        "amount_currency": tax_datum["tax_amount_currency"],
                        "balance": tax_datum["tax_amount"],
                    }
                )
                for tax_datum in tax_data["tax_lines_data"]
            )
        _debug.pipeline(
            "write_off_lines_built",
            recwizard=self,
            to_partner=to_partner,
            with_taxes=bool(tax_data),
            commands=len(line_ids_commands),
        )
        return line_ids_commands

    def create_write_off(self):
        self.check_singleton()
        partners = self.move_line_ids.partner_id
        partner = partners if len(partners) == 1 else None
        write_off_vals = {
            "journal_id": self.journal_id.id,
            "company_id": self.company_id.id,
            "date": self._get_date_after_lock_date() or self.date,
            "move_type": "entry",
            "checked": not self.to_check,
            "line_ids": self._create_write_off_lines(partner=partner),
        }
        write_off_move = (
            self.env["account.move"]
            .with_context(
                skip_invoice_sync=True,
                skip_invoice_line_sync=True,
            )
            .create(write_off_vals)
        )
        write_off_move.action_post()
        return write_off_move
