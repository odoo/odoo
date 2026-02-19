# Copyright 2016-2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, models
from odoo.exceptions import ValidationError


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _default_outbound_payment_methods(self):
        all_out = self.env["account.payment.method"].search(
            [("payment_type", "=", "outbound")]
        )
        return all_out

    def _default_inbound_payment_methods(self):
        method_info = self.env[
            "account.payment.method"
        ]._get_payment_method_information()
        allowed_modes = ["unique"]
        if "payment_provider_id" in self.env["account.payment.method.line"]._fields:
            allowed_modes.append("electronic")
        unique_codes = tuple(
            code
            for code, info in method_info.items()
            if info.get("mode") in allowed_modes
        )
        all_in = self.env["account.payment.method"].search(
            [
                ("payment_type", "=", "inbound"),
                ("code", "not in", unique_codes),  # filter out unique codes
            ]
        )
        return all_in

    @api.constrains("company_id")
    def company_id_account_payment_mode_constrains(self):
        for journal in self:
            mode = self.env["account.payment.mode"].search(
                [
                    ("fixed_journal_id", "=", journal.id),
                    ("company_id", "!=", journal.company_id.id),
                ],
                limit=1,
            )
            if mode:
                raise ValidationError(
                    _(
                        "The company of the journal %(journal)s does not match "
                        "with the company of the payment mode %(paymode)s where it is "
                        "being used as Fixed Bank Journal.",
                        journal=journal.name,
                        paymode=mode.name,
                    )
                )
            mode = self.env["account.payment.mode"].search(
                [
                    ("variable_journal_ids", "in", [journal.id]),
                    ("company_id", "!=", journal.company_id.id),
                ],
                limit=1,
            )
            if mode:
                raise ValidationError(
                    _(
                        "The company of the journal  %(journal)s does not match "
                        "with the company of the payment mode  %(paymode)s where it is "
                        "being used in the Allowed Bank Journals.",
                        journal=journal.name,
                        paymode=mode.name,
                    )
                )
