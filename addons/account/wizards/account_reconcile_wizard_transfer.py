from collections import defaultdict

from odoo import Command, _, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import groupby
from odoo.tools.misc import formatLang

_debug = DebugLog(__name__)


class AccountReconcileWizard(models.TransientModel):
    _inherit = "account.reconcile.wizard"

    @_debug.perf.timed
    def _prepare_transfer_data(self, amls):
        self.check_singleton()
        accounts = amls.account_id
        amounts_per_account = defaultdict(float)
        for line in amls:
            amounts_per_account[line.account_id] += line.amount_residual
        if abs(amounts_per_account[accounts[0]]) < abs(
            amounts_per_account[accounts[1]]
        ):
            transfer_from_account, transfer_to_account = accounts[0], accounts[1]
        else:
            transfer_from_account, transfer_to_account = accounts[1], accounts[0]

        amls_to_transfer = amls.filtered(
            lambda aml: aml.account_id == transfer_from_account
        )
        transfer_foreign_curr = amls.currency_id - amls.company_currency_id
        if len(transfer_foreign_curr) == 1:
            transfer_currency = transfer_foreign_curr
            transfer_amount_currency = sum(
                aml.amount_currency for aml in amls_to_transfer
            )
        else:
            transfer_currency = amls.company_currency_id
            transfer_amount_currency = sum(aml.balance for aml in amls_to_transfer)

        if (
            transfer_currency.is_zero(transfer_amount_currency)
            and transfer_currency != amls.company_currency_id
        ):
            transfer_currency = amls.company_currency_id
            transfer_amount_currency = sum(aml.balance for aml in amls_to_transfer)

        _debug.logic(
            "transfer_direction_chosen",
            recwizard=self,
            from_account=transfer_from_account,
            to_account=transfer_to_account,
            amls_to_transfer=len(amls_to_transfer),
            currency=transfer_currency,
            amount_currency=transfer_amount_currency,
        )
        amount_formatted = formatLang(
            self.env, abs(transfer_amount_currency), currency_obj=transfer_currency
        )
        transfer_warning_message = _(
            "An entry will transfer %(amount)s from %(from_account)s to %(to_account)s.",
            amount=amount_formatted,
            from_account=transfer_from_account.display_name
            if transfer_amount_currency < 0
            else transfer_to_account.display_name,
            to_account=transfer_to_account.display_name
            if transfer_amount_currency < 0
            else transfer_from_account.display_name,
        )
        return {
            "transfer_from_account_id": transfer_from_account,
            "reco_account_id": transfer_to_account,
            "transfer_warning_message": transfer_warning_message,
        }

    def _get_transfer_source_lines(self):
        self.check_singleton()
        lines_to_transfer = self.move_line_ids.filtered(
            lambda line: line.account_id == self.transfer_from_account_id
        )
        source_commands = []
        to_absorb = {}
        for (partner, currency), lines in groupby(
            lines_to_transfer, lambda line: (line.partner_id, line.currency_id)
        ):
            amount = sum(line.amount_residual for line in lines)
            amount_currency = sum(line.amount_residual_currency for line in lines)
            source_commands.append(
                Command.create(
                    {
                        "name": _("Transfer to %s", self.reco_account_id.display_name),
                        "account_id": self.transfer_from_account_id.id,
                        "partner_id": partner.id,
                        "currency_id": currency.id,
                        "amount_currency": -amount_currency,
                        "balance": -amount,
                    }
                )
            )
            sign = -1 if amount < 0 else 1
            to_absorb[partner, currency, sign] = {
                "balance": amount,
                "amount_currency": amount_currency,
            }
        return source_commands, to_absorb

    @_debug.perf.timed
    def _match_transfer_partners(self, to_absorb):
        self.check_singleton()
        other_lines = self.move_line_ids.filtered(
            lambda line: line.account_id == self.reco_account_id
        )
        destination_data = defaultdict(lambda: defaultdict(float))
        room_per_partner = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))

        for (partner, currency), lines in groupby(
            other_lines, lambda line: (line.partner_id, line.currency_id)
        ):
            amount = -sum(line.amount_residual for line in lines)
            amount_currency = -sum(line.amount_residual_currency for line in lines)
            sign = -1 if amount < 0 else 1
            if (partner, currency, sign) in to_absorb:
                default_amount = to_absorb[partner, currency, sign]["balance"]
                default_amount_currency = to_absorb[partner, currency, sign][
                    "amount_currency"
                ]
                amount_to_transfer = min(abs(amount), abs(default_amount)) * sign
                amount_currency_to_transfer = (
                    min(abs(amount_currency), abs(default_amount_currency)) * sign
                )
                destination_data[partner, currency, sign] = {
                    "balance": amount_to_transfer,
                    "amount_currency": amount_currency_to_transfer,
                }
                default_amount -= amount_to_transfer
                default_amount_currency -= amount_currency_to_transfer
                amount -= amount_to_transfer
                amount_currency -= amount_currency_to_transfer
                if not currency.is_zero(abs(default_amount)):
                    to_absorb[partner, currency, sign] = {
                        "balance": default_amount,
                        "amount_currency": default_amount_currency,
                    }
                else:
                    del to_absorb[partner, currency, sign]
            if not currency.is_zero(abs(amount)):
                room_per_partner[currency, sign][partner] = {
                    "balance": amount,
                    "amount_currency": amount_currency,
                }
        _debug.pipeline(
            "transfer_partners_matched",
            recwizard=self,
            other_lines=len(other_lines),
            matched=len(destination_data),
            unabsorbed=len(to_absorb),
            room_buckets=len(room_per_partner),
        )
        return destination_data, room_per_partner

    @_debug.perf.timed
    def _place_transfer_remainders(self, to_absorb, room_per_partner, destination_data):
        self.check_singleton()
        for partner, currency, sign in to_absorb:
            amount = to_absorb[partner, currency, sign]["balance"]
            amount_currency = to_absorb[partner, currency, sign]["amount_currency"]
            for other_partner in room_per_partner[currency, sign]:
                if self.company_currency_id.is_zero(amount) and currency.is_zero(
                    amount_currency
                ):
                    break
                room = room_per_partner[currency, sign][other_partner]
                amount_to_transfer = min(abs(amount), abs(room["balance"])) * sign
                amount_currency_to_transfer = (
                    min(abs(amount_currency), abs(room["amount_currency"])) * sign
                )
                amount -= amount_to_transfer
                amount_currency -= amount_currency_to_transfer

                destination_data[other_partner, currency, sign]["balance"] += (
                    amount_to_transfer
                )
                destination_data[other_partner, currency, sign]["amount_currency"] += (
                    amount_currency_to_transfer
                )
                room["balance"] -= amount_to_transfer
                room["amount_currency"] -= amount_currency_to_transfer

            if not self.company_currency_id.is_zero(amount) or not currency.is_zero(
                amount_currency
            ):
                destination_data[partner, currency, sign]["balance"] += amount
                destination_data[partner, currency, sign]["amount_currency"] += (
                    amount_currency
                )
        _debug.pipeline(
            "transfer_remainders_placed",
            recwizard=self,
            remainders=len(to_absorb),
            destinations=len(destination_data),
        )

    @_debug.perf.timed
    def create_transfer(self):
        self.check_singleton()
        source_commands, to_absorb = self._get_transfer_source_lines()
        destination_data, room_per_partner = self._match_transfer_partners(to_absorb)
        self._place_transfer_remainders(to_absorb, room_per_partner, destination_data)

        destination_commands = [
            Command.create(
                {
                    "name": _(
                        "Transfer from %s", self.transfer_from_account_id.display_name
                    ),
                    "account_id": self.reco_account_id.id,
                    "partner_id": partner.id,
                    "currency_id": currency.id,
                    "amount_currency": amounts["amount_currency"],
                    "balance": amounts["balance"],
                }
            )
            for (partner, currency, _sign), amounts in destination_data.items()
        ]
        transfer_move = self.env["account.move"].create(
            {
                "journal_id": self.journal_id.id,
                "company_id": self.company_id.id,
                "date": self._get_date_after_lock_date() or self.date,
                "line_ids": source_commands + destination_commands,
            }
        )
        _debug.pipeline(
            "transfer_move_created",
            recwizard=self,
            move=transfer_move,
            source_lines=len(source_commands),
            destination_lines=len(destination_commands),
        )
        transfer_move.action_post()
        return transfer_move
