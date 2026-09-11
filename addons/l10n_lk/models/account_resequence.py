# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from datetime import date

from odoo import models

from odoo.addons.l10n_lk.models.account_move import (
    LK_MONTH_ABBR,
    LK_TAX_INVOICE_FORMAT,
    LK_TAX_INVOICE_REGEX,
)


class AccountResequenceWizard(models.TransientModel):
    _inherit = "account.resequence.wizard"

    def _compute_new_values(self):
        """Resequence LK invoices with per-record month/year from their
        invoice date, since the standard implementation reuses the month
        abbreviation of the previous name."""

        def _format_entry(entry, seq):
            move_date = date.fromisoformat(entry["server-date"])
            return seq_format.format(
                **{
                    **format_values,
                    "year": wizard.move_ids[0]._truncate_year_to_length(
                        move_date.year,
                        format_values["year_length"],
                    ),
                    "month": move_date.month,
                    "month_abbr": LK_MONTH_ABBR[move_date.month],
                    "seq": seq,
                },
            )

        def _current_seq(entry):
            match = LK_TAX_INVOICE_REGEX.match(entry.get("current_name") or "")
            return int(match["seq"]) if match else 0

        super()._compute_new_values()

        for wizard in self.filtered("first_name"):
            seq_format, format_values = wizard.move_ids[0]._get_sequence_format_param(
                wizard.first_name,
            )
            if seq_format != LK_TAX_INVOICE_FORMAT:
                continue

            new_values = json.loads(wizard.new_values)
            base_seq = format_values["seq"]

            by_name_entries = sorted(
                new_values.values(),
                key=lambda e: (
                    _current_seq(e),
                    e["server-date"],
                    e["current_name"] or "",
                    e["id"],
                ),
            )
            formatted_names = [_format_entry(e, base_seq + i) for i, e in enumerate(by_name_entries)]

            for entry, new_name in zip(by_name_entries, formatted_names):
                entry["new_by_name"] = new_name

            by_date_entries = sorted(
                new_values.values(),
                key=lambda e: (e["server-date"], e["current_name"] or "", e["id"]),
            )
            formatted_names_by_date = [_format_entry(e, base_seq + i) for i, e in enumerate(by_date_entries)]
            for entry, new_name in zip(by_date_entries, formatted_names_by_date):
                entry["new_by_date"] = new_name

            wizard.new_values = json.dumps(new_values)
