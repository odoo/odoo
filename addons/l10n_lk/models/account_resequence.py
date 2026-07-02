# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from datetime import date

from odoo import models

from .account_move import LK_MONTH_ABBR, LK_TAX_INVOICE_REGEX


class AccountResequenceWizard(models.TransientModel):
    _inherit = "account.resequence.wizard"

    def _compute_new_values(self):
        super()._compute_new_values()

        for wizard in self.filtered("move_ids"):
            seq_format, format_values = wizard.move_ids[0]._get_sequence_format_param(
                wizard.first_name,
            )
            if "month_abbr" not in format_values:
                continue

            new_values = json.loads(wizard.new_values)
            base_seq = format_values["seq"]

            def _format_entry(entry, seq):
                move_date = date.fromisoformat(entry["server-date"])
                return seq_format.format(
                    **{
                        **format_values,
                        "year": wizard.move_ids[0]._truncate_year_to_length(
                            move_date.year, format_values["year_length"],
                        ),
                        "month": move_date.month,
                        "month_abbr": LK_MONTH_ABBR[move_date.month],
                        "seq": seq,
                    },
                )

            def _current_seq(entry):
                match = LK_TAX_INVOICE_REGEX.match(entry.get("current_name", ""))
                return int(match["seq"]) if match else 0

            by_name_entries = sorted(
                new_values.values(),
                key=lambda e: (
                    _current_seq(e),
                    e["server-date"],
                    e["current_name"],
                    e["id"],
                ),
            )
            for offset, entry in enumerate(by_name_entries):
                entry["new_by_name"] = _format_entry(entry, base_seq + offset)

            by_date_entries = sorted(
                new_values.values(),
                key=lambda e: (e["server-date"], e["current_name"], e["id"]),
            )
            for offset, entry in enumerate(by_date_entries):
                entry["new_by_date"] = _format_entry(entry, base_seq + offset)

            wizard.new_values = json.dumps(new_values)
