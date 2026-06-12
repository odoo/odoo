# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import SQL, Query, frozendict

# Month abbreviations are hardcoded rather than relying on strftime('%b')
# because the latter is locale-dependent
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
    r"^(?P<year>\d{2})(?P<month_abbr>[A-Z]{3})_(?P<journal_code>[A-Za-z0-9]{1,15})_(?P<seq>\d+)(?P<suffix>\D*?)$",
)

LK_TAX_INVOICE_FORMAT = "{year:0{year_length}d}{month_abbr}_{journal_code}_{seq:0{seq_length}d}{suffix}"
LK_TAX_INVOICE_MAX_LENGTH = 40


class AccountMove(models.Model):
    _inherit = "account.move"

    def _lk_sql_seq_regex(self):
        r"""PSQL-safe pattern for LK names (no named groups, no lazy quantifiers).

        The Python `LK_TAX_INVOICE_REGEX` uses named groups (``(?P<name>...)``),
        which PostgreSQL's ``~`` operator does not support.
        `_make_regex_non_capturing` converts them to non-capturing groups, but
        it is not sufficient on its own: it leaves the lazy quantifier of the
        suffix group (``\D*?``) untouched. Since that group only matches
        non-digit characters at the end of the name, its greedy equivalent
        (``\D*``) matches exactly the same names, so it is used instead.
        """
        return self._make_regex_non_capturing(LK_TAX_INVOICE_REGEX.pattern).replace(r"\D*?", r"\D*")

    @api.constrains(lambda self: (self._sequence_field,))
    def _constrains_l10n_lk_sequence_length(self):
        for record in self:
            if record._l10n_lk_use_tax_invoice_sequence():
                sequence = record[record._sequence_field]
                if sequence and len(sequence) > LK_TAX_INVOICE_MAX_LENGTH:
                    raise UserError(
                        self.env._(
                            "Invoice number exceeds %(max)d characters: %(name)s",
                            max=LK_TAX_INVOICE_MAX_LENGTH,
                            name=sequence,
                        ),
                    )

    def _l10n_lk_is_tax_invoice_company(self):
        """
        Whether this invoice qualifies as a tax invoice under LK VAT law.

        Requires both parties to be VAT-registered (the customer's status is
        that of its commercial partner) and all lines to be 18%/zero-rated
        (gazette s.4.2).  Excludes debit notes.  Controls PDF-level display.
        """
        self.ensure_one()
        return bool(
            self.country_code == "LK"
            and self.company_id.l10n_lk_vat_registered
            and self.commercial_partner_id.l10n_lk_vat_registered
            # Debit notes are not tax invoices, even for registered suppliers.
            and not (self._fields.get("debit_origin_id") and self.debit_origin_id)
            and self._l10n_lk_has_taxable_taxes(),
        )

    def _get_name_invoice_report(self):
        self.ensure_one()
        if self.country_code == "LK":
            return "l10n_lk_invoice.report_invoice_document"
        return super()._get_name_invoice_report()

    def _l10n_lk_has_taxable_taxes(self):
        """All product lines must carry 18% or zero-rated taxes only (gazette
        s.4.2).

        WHT/AIT withholding taxes are ignored for this determination: they are
        deducted at payment time and do not qualify (nor disqualify) a line as
        a taxable supply.
        """
        self.ensure_one()
        product_lines = self.invoice_line_ids.filtered(
            lambda line: line.display_type == "product",
        )
        if not product_lines:
            return False
        ChartTemplate = self.env["account.chart.template"].with_company(self.company_id)
        group_18 = ChartTemplate.ref("l10n_lk_tax_group_18", raise_if_not_found=False)
        group_zero_rated = ChartTemplate.ref("l10n_lk_tax_group_zero_rated", raise_if_not_found=False)
        group_wht = ChartTemplate.ref("l10n_lk_tax_group_wht", raise_if_not_found=False)
        group_ait = ChartTemplate.ref("l10n_lk_tax_group_ait", raise_if_not_found=False)
        taxable_groups = (group_18, group_zero_rated)
        for line in product_lines:
            vat_taxes = line.tax_ids.filtered(lambda tax: tax.tax_group_id not in (group_wht, group_ait))
            all_taxable = all(tax.tax_group_id in taxable_groups for tax in vat_taxes)
            if not vat_taxes or not all_taxable:
                return False
        return True

    def _l10n_lk_use_tax_invoice_sequence(self):
        """
        Use YYMMM_QQQQ_XXXXX format for all LK sale documents from
        VAT-registered companies.  Unlike _l10n_lk_is_tax_invoice_company,
        does not check partner VAT or line taxability.
        """
        return (
            self.country_code == "LK"
            and self.company_id.l10n_lk_vat_registered
            and self.is_sale_document(include_receipts=False)
            and self.move_type != "out_refund"
        )

    def _get_last_sequence(self, relaxed=False, with_prefix=None):
        """
        Override to fetch the last LK sequence using a custom regex pattern.

        The standard method uses sequence_prefix for filtering, but LK sequences
        use YYMMM_JOURNAL_SEQ format where the journal code is part of the name,
        not the prefix. We use a PSQL regex via _lk_sql_seq_regex to match
        LK-specific pattern and fetch the correct last sequence.
        """
        if not self._l10n_lk_use_tax_invoice_sequence():
            return super()._get_last_sequence(relaxed=relaxed, with_prefix=with_prefix)
        self.ensure_one()
        sequence_field = self._fields.get(self._sequence_field)
        if not sequence_field or not sequence_field.store:
            raise ValidationError(self.env._("%(field_name)s is not a stored field", field_name=self._sequence_field))
        self.flush_model([self._sequence_field, "sequence_number", "sequence_prefix"])

        query = Query(self.env, alias="move", table=SQL.identifier(self._table))
        query.add_where(SQL("journal_id = %s", self.journal_id.id))
        query.add_where(SQL("name != '/'"))

        if self._origin.id:
            query.add_where(SQL("id != %s", self._origin.id))
        if with_prefix is not None:
            query.add_where(SQL("sequence_prefix = %s", with_prefix))
        query.add_where(SQL("name ~ %s", self._lk_sql_seq_regex()))

        query.order = SQL("sequence_number DESC")
        query.limit = 1

        result = self.env.execute_query(query.select(SQL.identifier(self._sequence_field)))
        return result and result[0][0]

    def _sequence_matches_date(self):
        """LK sequences never reset, so the standard date check (which
        depends on the reset frequency) does not apply."""
        self.ensure_one()
        if self._l10n_lk_use_tax_invoice_sequence():
            match = LK_TAX_INVOICE_REGEX.match(self.name or "")
            if match:
                move_date = fields.Date.to_date(self[self._sequence_date_field])
                if not move_date:
                    return True
                month = LK_MONTH_BY_ABBR.get(match["month_abbr"])
                if not month:
                    return super()._sequence_matches_date()
                year = int(match["year"])
                expected_year = self._truncate_year_to_length(move_date.year, len(match["year"]))
                return year == expected_year and month == move_date.month
        return super()._sequence_matches_date()

    def _get_starting_sequence(self):
        """Initial LK sequence: YYMMM_QQQQ_00000."""
        self.ensure_one()
        if not self._l10n_lk_use_tax_invoice_sequence():
            return super()._get_starting_sequence()
        move_date = self.date or self.invoice_date or fields.Date.context_today(self)
        return f"{move_date.strftime('%y')}{LK_MONTH_ABBR[move_date.month]}_{self.journal_id.code}_00000"

    def _deduce_sequence_number_reset(self, name):
        """LK sequences never reset."""
        if self._l10n_lk_use_tax_invoice_sequence() and LK_TAX_INVOICE_REGEX.match(name or ""):
            return "never"
        return super()._deduce_sequence_number_reset(name)

    def _get_sequence_format_param(self, previous):
        """Parse an LK name into format params, extracting year/month/journal_code/seq/suffix."""
        match = LK_TAX_INVOICE_REGEX.match(previous) if isinstance(previous, str) else None
        if not self._l10n_lk_use_tax_invoice_sequence() or not match:
            return super()._get_sequence_format_param(previous)
        month = LK_MONTH_BY_ABBR.get(match["month_abbr"])
        if not month:
            return super()._get_sequence_format_param(previous)
        return LK_TAX_INVOICE_FORMAT, {
            "year": int(match["year"]),
            "year_length": len(match["year"]),
            "year_end": 0,
            "year_end_length": 0,
            "month": month,
            "month_abbr": match["month_abbr"],
            "journal_code": match["journal_code"],
            "seq": int(match["seq"]),
            "seq_length": len(match["seq"]),
            "suffix": match["suffix"] or "",
        }

    def _get_next_sequence_format(self):
        """Update month/year from the invoice date even though the
        sequence never resets, so the date portion stays accurate."""
        format_string, format_values = super()._get_next_sequence_format()
        if self._l10n_lk_use_tax_invoice_sequence() and format_string == LK_TAX_INVOICE_FORMAT:
            move_date = self.date or self.invoice_date or fields.Date.context_today(self)
            format_values["year"] = self._truncate_year_to_length(move_date.year, format_values["year_length"])
            format_values["month"] = move_date.month
            format_values["month_abbr"] = LK_MONTH_ABBR[move_date.month]
        return format_string, format_values

    def _is_last_from_seq_chain(self):
        """LK sequences span months, so the standard prefix comparison
        cannot detect whether a newer entry exists in a different month."""
        if not self._l10n_lk_use_tax_invoice_sequence():
            return super()._is_last_from_seq_chain()
        query = Query(self.env, alias="move", table=SQL.identifier(self._table))
        query.add_where(SQL("journal_id = %s", self.journal_id.id))
        query.add_where(SQL("name != '/'"))

        if self._origin.id:
            query.add_where(SQL("id != %s", self._origin.id))
        query.add_where(SQL("sequence_number > %s", self.sequence_number or 0))
        query.add_where(SQL("name ~ %s", self._lk_sql_seq_regex()))

        query.order = SQL("sequence_number ASC")
        query.limit = 1

        result = self.env.execute_query(query.select(SQL.identifier("id")))
        return not (result and result[0])

    def _is_end_of_seq_chain(self):
        """Normalize LK batch keys to journal_code only, so invoices from
        different months but the same journal are grouped together."""
        lk_records = self.filtered(lambda m: m[m._sequence_field] and m._l10n_lk_use_tax_invoice_sequence())
        if not lk_records:
            return super()._is_end_of_seq_chain()

        standard_records = self - lk_records
        if standard_records and not super(AccountMove, standard_records)._is_end_of_seq_chain():
            return False

        batched = defaultdict(lambda: {"last_rec": self.browse(), "seq_list": []})
        for record in lk_records:
            seq_format, format_values = record._get_sequence_format_param(record[record._sequence_field])
            seq = format_values.pop("seq")
            batch = batched[seq_format, frozendict({"journal_code": format_values.get("journal_code")})]
            batch["seq_list"].append(seq)
            if batch["last_rec"].sequence_number <= record.sequence_number:
                batch["last_rec"] = record

        for values in batched.values():
            seq_list = values["seq_list"]
            if max(seq_list) - min(seq_list) != len(seq_list) - 1:
                return False
            record = values["last_rec"]
            if not record._is_last_from_seq_chain():
                return False
        return True
