# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import _, fields, models
from odoo.exceptions import UserError

# Sri Lanka Tax Invoice format: YYMMM_QQQQ_XXXXX
# YY = 2-digit year, MMM = month abbreviation, QQQQ = journal code (1-15 chars), XXXXX = serial
LK_MONTH_ABBR = {
    1: "JAN",
    2: "FEB",
    3: "MAR",
    4: "APR",
    5: "MAY",
    6: "JUN",
    7: "JUL",
    8: "AUG",
    9: "SEP",
    10: "OCT",
    11: "NOV",
    12: "DEC",
}
LK_MONTH_BY_ABBR = {v: k for k, v in LK_MONTH_ABBR.items()}
LK_TAX_INVOICE_REGEX = re.compile(
    r"^(?P<year>\d{2})(?P<month_abbr>[A-Z]{3})_(?P<qqqq>[A-Za-z0-9]{1,15})_(?P<seq>\d+)(?P<suffix>\D*?)$",
)
LK_TAX_INVOICE_FORMAT = (
    "{year:0{year_length}d}{month_abbr}_{qqqq}_{seq:0{seq_length}d}{suffix}"
)
LK_TAX_INVOICE_MAX_LENGTH = 40


class AccountMove(models.Model):
    _inherit = "account.move"

    def _l10n_lk_is_tax_invoice_company(self):
        """Check if this invoice qualifies as a Sri Lankan tax invoice.

        Both the company and the partner must be VAT-registered.
        """
        self.ensure_one()
        return (
            self.country_code == "LK"
            and self.company_id.l10n_lk_vat_registered
            and self.partner_id.l10n_lk_vat_registered
        )

    def _l10n_lk_use_tax_invoice_sequence(self):
        """Whether this move uses the LK tax invoice sequence format."""
        return (
            self.country_code == "LK"
            and self.is_sale_document(include_receipts=True)
            and not self.is_refund()
            and not self.journal_id.payment_sequence
            and not self.journal_id.is_self_billing
        )

    def _get_last_sequence_domain(self, relaxed=False):
        where_string, param = super()._get_last_sequence_domain(relaxed)
        if (
            not relaxed
            and self._l10n_lk_use_tax_invoice_sequence()
            and "anti_regex" in param
        ):
            where_string = where_string.replace(
                " AND sequence_prefix !~ %(anti_regex)s ", " ",
            )
            del param["anti_regex"]
        return where_string, param

    def _sequence_matches_date(self):
        self.ensure_one()
        if not self._l10n_lk_use_tax_invoice_sequence():
            return super()._sequence_matches_date()

        match = LK_TAX_INVOICE_REGEX.match(self.name or "")
        if not match:
            return super()._sequence_matches_date()

        move_date = fields.Date.to_date(self[self._sequence_date_field])
        if not move_date:
            return True
        return (
            int(match["year"])
            == self._truncate_year_to_length(move_date.year, len(match["year"]))
            and LK_MONTH_BY_ABBR.get(match["month_abbr"]) == move_date.month
        )

    def _get_starting_sequence(self):
        self.ensure_one()
        if not self._l10n_lk_use_tax_invoice_sequence():
            return super()._get_starting_sequence()
        move_date = self.date or self.invoice_date or fields.Date.context_today(self)
        qqqq = (self.journal_id.code or "SEQ").upper()
        return (
            f"{move_date.strftime('%y')}{LK_MONTH_ABBR[move_date.month]}_{qqqq}_00000"
        )

    def _deduce_sequence_number_reset(self, name):
        if (
            self
            and self._l10n_lk_use_tax_invoice_sequence()
            and LK_TAX_INVOICE_REGEX.match(name or "")
        ):
            return "never"
        return super()._deduce_sequence_number_reset(name)

    def _get_sequence_format_param(self, previous):
        if not (self and self._l10n_lk_use_tax_invoice_sequence()):
            return super()._get_sequence_format_param(previous)

        match = LK_TAX_INVOICE_REGEX.match(previous or "")
        if not match:
            return super()._get_sequence_format_param(previous)

        month_abbr = match["month_abbr"]
        if month_abbr not in LK_MONTH_BY_ABBR:
            return super()._get_sequence_format_param(previous)

        return LK_TAX_INVOICE_FORMAT, {
            "year": int(match["year"]),
            "year_length": len(match["year"]),
            "year_end": 0,
            "year_end_length": 0,
            "month": LK_MONTH_BY_ABBR[month_abbr],
            "month_abbr": month_abbr,
            "qqqq": match["qqqq"],
            "seq": int(match["seq"]),
            "seq_length": len(match["seq"]),
            "suffix": match["suffix"] or "",
        }

    def _get_next_sequence_format(self):
        format_string, format_values = super()._get_next_sequence_format()
        if (
            self
            and self._l10n_lk_use_tax_invoice_sequence()
            and format_string == LK_TAX_INVOICE_FORMAT
        ):
            move_date = (
                self.date or self.invoice_date or fields.Date.context_today(self)
            )
            format_values["year"] = self._truncate_year_to_length(
                move_date.year, format_values["year_length"],
            )
            format_values["month"] = move_date.month
            format_values["month_abbr"] = LK_MONTH_ABBR[move_date.month]
            formatted = format_string.format(**format_values)
            if len(formatted) > LK_TAX_INVOICE_MAX_LENGTH:
                raise UserError(
                    _(
                        "Invoice number exceeds %(max)d characters: %(name)s",
                        max=LK_TAX_INVOICE_MAX_LENGTH,
                        name=formatted,
                    ),
                )
        return format_string, format_values
