import logging
import re
from collections import defaultdict
from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, TransactionMemo, date_utils, frozendict
from odoo.tools.misc import format_date

_logger = logging.getLogger(__name__)

_debug = DebugLog(__name__)

_LAST_SEQUENCE_MEMOS: dict[str, TransactionMemo] = {}


def _last_sequence_memo(model_name):
    memo = _LAST_SEQUENCE_MEMOS.get(model_name)
    if memo is None:
        memo = _LAST_SEQUENCE_MEMOS[model_name] = TransactionMemo(
            f"mixin.sequence.last:{model_name}", invalidated_by=(model_name,)
        )
    return memo


class MixinSequence(models.AbstractModel):
    _name = "mixin.sequence"
    _description = "Automatic sequence"

    _sequence_field = "name"
    _sequence_date_field = "date"
    _sequence_index = False

    prefix = r"(?P<prefix1>.*?)"
    prefix2 = r"(?P<prefix2>\D)"
    prefix3 = r"(?P<prefix3>\D+?)"
    seq = r"(?P<seq>\d*)"
    month = r"(?P<month>(0[1-9]|1[0-2]))"
    year = r"(?P<year>((?<=\D)|(?<=^))((19|20|21)\d{2}|(\d{2}(?=\D))))"
    year_end = r"(?P<year_end>((?<=\D)|(?<=^))((19|20|21)\d{2}|(\d{2}(?=\D))))"
    suffix = r"(?P<suffix>\D*?)"

    _sequence_year_range_monthly_regex = rf"^{prefix}{year}{prefix2}{year_end}(?P<prefix3>\D){month}(?P<prefix4>\D+?){seq}{suffix}$"
    _sequence_year_range_regex = (
        rf"^(?:{prefix}{year}{prefix2}{year_end}{prefix3})?{seq}{suffix}$"
    )
    _sequence_monthly_regex = (
        rf"^{prefix}{year}(?P<prefix2>\D*?){month}{prefix3}{seq}{suffix}$"
    )
    _sequence_yearly_regex = rf"^{prefix}(?P<year>((?<=\D)|(?<=^))((19|20|21)?\d{{2}}))(?P<prefix2>\D+?){seq}{suffix}$"
    _sequence_fixed_regex = rf"^{prefix}(?P<seq>\d{{0,9}}){suffix}$"

    sequence_prefix = fields.Char(
        compute="_compute_split_sequence",
        store=True,
    )
    sequence_number = fields.Integer(
        compute="_compute_split_sequence",
        store=True,
    )

    @_debug.perf.timed
    def init(self):
        _debug.lifecycle("init", records=self)
        _debug.logic(
            "sequence_indexes_wanted",
            seq_model=self._name,
            abstract=self._abstract,
            sequence_index=self._sequence_index,
        )
        if not self._abstract and self._sequence_index:
            index_name = self._table + "_sequence_index"
            self.env.cr.execute(
                SQL(
                    """
                CREATE INDEX IF NOT EXISTS %(index_name)s ON %(table)s (%(sequence_index)s, sequence_prefix desc, sequence_number desc, %(field)s);
                CREATE INDEX IF NOT EXISTS %(index2_name)s ON %(table)s (%(sequence_index)s, id desc, sequence_prefix);
                """,
                    sequence_index=SQL.identifier(self._sequence_index),
                    index_name=SQL.identifier(index_name),
                    index2_name=SQL.identifier(index_name + "2"),
                    table=SQL.identifier(self._table),
                    field=SQL.identifier(self._sequence_field),
                )
            )
            unique_index = self.env.execute_query(
                SQL(
                    """
                SELECT 1
                  FROM pg_class t
                  JOIN pg_index ix ON t.oid = ix.indrelid
                  JOIN pg_attribute a ON a.attrelid = t.oid
                                     AND a.attnum = ANY(ix.indkey)
                 WHERE t.relkind = 'r'
                   AND t.relname = %(table)s
                   AND t.relnamespace = current_schema::regnamespace
                   AND a.attname = %(column)s
                   AND ix.indisunique
                """,
                    table=self._table,
                    column=self._sequence_field,
                )
            )
            _debug.logic(
                "sequence_unique_index_checked",
                seq_model=self._name,
                found=bool(unique_index),
            )
            if not unique_index:
                _logger.warning(
                    "A unique index for `mixin.sequence` is missing on %s. "
                    "This will cause duplicated sequences under heavy load.",
                    self._table,
                )

    def _get_sequence_cache(self):
        return self.env.cr.cache.setdefault("mixin.sequence", {})

    @_debug.perf.timed
    def write(self, vals):
        _debug.lifecycle("write", records=self, fields=sorted(vals))
        if self._sequence_field in vals and self.env.context.get(
            "clear_sequence_mixin_cache", True
        ):
            self._get_sequence_cache().clear()
        return super().write(vals)

    def _get_sequence_date_range(self, reset):
        ref_date = fields.Date.to_date(self[self._sequence_date_field])
        if reset in ("year", "year_range", "year_range_month"):
            return (date(ref_date.year, 1, 1), date(ref_date.year, 12, 31), None, None)
        if reset == "month":
            return date_utils.get_month(ref_date) + (None, None)
        if reset == "never":
            return (date(1, 1, 1), date(9999, 12, 31), None, None)
        raise NotImplementedError(reset)

    def _is_date_sequence_check_required(self):
        return True

    def _year_match(self, format_value, year):
        return format_value == self._truncate_year_to_length(
            year, len(str(format_value))
        )

    def _truncate_year_to_length(self, year, length):
        return year % (10**length)

    def _sequence_matches_date(self):
        self.check_singleton()
        record_date = fields.Date.to_date(self[self._sequence_date_field])
        sequence = self[self._sequence_field]

        if not sequence or not record_date:
            return True

        format_values = self._get_sequence_format_param(sequence)[1]
        sequence_number_reset = self._deduce_sequence_number_reset(sequence)
        date_start, date_end, forced_year_start, forced_year_end = (
            self._get_sequence_date_range(sequence_number_reset)
        )
        year_match = (
            not format_values["year"]
            or self._year_match(
                format_values["year"], forced_year_start or date_start.year
            )
        ) and (
            not format_values["year_end"]
            or self._year_match(
                format_values["year_end"], forced_year_end or date_end.year
            )
        )
        month_match = (
            not format_values["month"] or format_values["month"] == record_date.month
        )
        return year_match and month_match

    @api.constrains(lambda self: (self._sequence_field, self._sequence_date_field))
    def _constrains_date_sequence(self):
        constraint_date = fields.Date.to_date(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("sequence.mixin.constraint_start_date", "1970-01-01")
        )
        for record in self:
            if not record._is_date_sequence_check_required():
                continue
            record_date = fields.Date.to_date(record[record._sequence_date_field])
            sequence = record[record._sequence_field]
            if (
                sequence
                and record_date
                and record_date > constraint_date
                and not record._sequence_matches_date()
            ):
                _debug.logic(
                    "sequence_date_mismatch",
                    seq_model=record._name,
                    seq_id=record,
                    sequence=sequence,
                    date=record_date,
                )
                raise ValidationError(
                    _(
                        "The %(date_field)s (%(date)s) you've entered isn't aligned with the existing sequence number (%(sequence)s). Clear the sequence number to proceed.\n"
                        "To maintain date-based sequences, select entries and use the resequence option from the actions menu, available in developer mode.",
                        date_field=record._fields[
                            record._sequence_date_field
                        ]._description_string(self.env),
                        date=format_date(self.env, record_date),
                        sequence=sequence,
                    )
                )

    @api.depends(lambda self: [self._sequence_field])
    def _compute_split_sequence(self):
        self._update_split_sequence()

    def _update_split_sequence(self):
        compiled = {}
        for record in self:
            sequence = record[record._sequence_field] or ""
            pattern = record._sequence_fixed_regex
            matcher = compiled.get(pattern)
            if matcher is None:
                matcher = compiled[pattern] = re.compile(pattern)
            matching = matcher.match(sequence)
            if matching is None:
                _debug.logic(
                    "sequence_regex_mismatch",
                    seq_model=record._name,
                    seq_id=record,
                    sequence=sequence,
                )
                raise ValidationError(
                    self.env._(
                        "The sequence regex %(regex)s does not match the current "
                        "sequence %(sequence)s. Check the journal's advanced "
                        "settings.",
                        regex=pattern,
                        sequence=sequence or "''",
                    )
                )
            record.sequence_prefix = sequence[: matching.start("seq")]
            record.sequence_number = int(matching.group("seq") or 0)

    @api.model
    @_debug.perf.timed
    def _deduce_sequence_number_reset(self, name):
        for regex, ret_val, requirements in [
            (
                self._sequence_year_range_monthly_regex,
                "year_range_month",
                ["seq", "year", "year_end", "month"],
            ),
            (self._sequence_monthly_regex, "month", ["seq", "month", "year"]),
            (
                self._sequence_year_range_regex,
                "year_range",
                ["seq", "year", "year_end"],
            ),
            (self._sequence_yearly_regex, "year", ["seq", "year"]),
            (self._sequence_fixed_regex, "never", ["seq"]),
        ]:
            match = re.match(regex, name or "")
            if match:
                groupdict = match.groupdict()
                if (
                    groupdict.get("year_end")
                    and groupdict.get("year")
                    and (
                        len(groupdict["year"]) < len(groupdict["year_end"])
                        or self._truncate_year_to_length(
                            (int(groupdict["year"]) + 1), len(groupdict["year_end"])
                        )
                        != int(groupdict["year_end"])
                    )
                ):
                    _debug.logic(
                        "sequence_year_range_rejected",
                        seq_model=self._name,
                        name=name,
                        reset=ret_val,
                    )
                    continue
                if all(groupdict.get(req) is not None for req in requirements):
                    _debug.logic(
                        "sequence_reset_deduced",
                        seq_model=self._name,
                        name=name,
                        reset=ret_val,
                    )
                    return ret_val
        _debug.logic("sequence_reset_undeducible", seq_model=self._name, name=name)
        raise ValidationError(
            _(
                "The sequence regex should at least contain the seq grouping keys. For instance:\n"
                r"^(?P<prefix1>.*?)(?P<seq>\d*)(?P<suffix>\D*?)$"
            )
        )

    @_debug.perf.timed
    def _prepare_regex_non_capturing(self, regex):
        return re.sub(r"\?P<\w+>", "?:", regex)

    def _get_domain_last_sequence(self, relaxed=False):
        self.check_singleton()
        raise NotImplementedError(
            "Models inheriting 'mixin.sequence' must override "
            "'_get_domain_last_sequence' and return a Domain."
        )

    def _get_starting_sequence(self):
        self.check_singleton()
        return "00000000"

    def _get_last_sequence(self, relaxed=False, with_prefix=None):
        self.check_singleton()
        if (
            self._sequence_field not in self._fields
            or not self._fields[self._sequence_field].store
        ):
            _debug.logic(
                "sequence_field_not_stored",
                seq_model=self._name,
                field=self._sequence_field,
            )
            raise ValidationError(_("%s is not a stored field", self._sequence_field))
        domain = Domain(self._get_domain_last_sequence(relaxed))
        if self._origin.id:
            domain &= Domain("id", "!=", self._origin.id)
        if with_prefix is not None:
            domain &= Domain("sequence_prefix", "=", with_prefix or "")

        _debug.pipeline(
            "last_sequence_query_built",
            seq_model=self._name,
            seq_id=self,
            relaxed=relaxed,
            with_prefix=with_prefix,
        )
        memo = _last_sequence_memo(self._name)(self.env)
        key = (self._sequence_field, domain)
        if key in memo:
            return memo[key]
        self.flush_model([self._sequence_field, "sequence_number", "sequence_prefix"])
        candidates = self.sudo().with_context(active_test=False)
        latest = candidates.search(domain, order="id DESC", limit=1)
        result = None
        if latest:
            last = candidates.search(
                domain & Domain("sequence_prefix", "=", latest.sequence_prefix or ""),
                order="sequence_number DESC",
                limit=1,
            )
            result = last[self._sequence_field] or None
        memo[key] = result
        return result

    @_debug.perf.timed
    def _get_sequence_format_param(self, previous):
        sequence_number_reset = self._deduce_sequence_number_reset(previous)
        regex = self._sequence_fixed_regex
        if sequence_number_reset == "year":
            regex = self._sequence_yearly_regex
        elif sequence_number_reset == "year_range":
            regex = self._sequence_year_range_regex
        elif sequence_number_reset == "month":
            regex = self._sequence_monthly_regex
        elif sequence_number_reset == "year_range_month":
            regex = self._sequence_year_range_monthly_regex
        match = re.match(regex, previous)
        format_values = match.groupdict()
        format_values["seq_length"] = len(format_values["seq"])
        format_values["year_length"] = len(format_values.get("year") or "")
        format_values["year_end_length"] = len(format_values.get("year_end") or "")
        if (
            not format_values.get("seq")
            and "prefix1" in format_values
            and "suffix" in format_values
        ):
            _debug.logic(
                "sequence_suffix_moved_to_prefix",
                seq_model=self._name,
                previous=previous,
            )
            format_values["prefix1"] = format_values["suffix"]
            format_values["suffix"] = ""
        for field in ("seq", "year", "month", "year_end"):
            format_values[field] = int(format_values.get(field) or 0)

        placeholders = [
            name
            for name, _ in sorted(match.re.groupindex.items(), key=lambda kv: kv[1])
            if re.fullmatch(r"prefix\d|seq|suffix\d?|year|year_end|month", name)
        ]
        format = "".join(
            "{seq:0{seq_length}d}"
            if s == "seq"
            else "{month:02d}"
            if s == "month"
            else "{year:0{year_length}d}"
            if s == "year"
            else "{year_end:0{year_end_length}d}"
            if s == "year_end"
            else "{%s}" % s
            for s in placeholders
        )
        _debug.logic(
            "sequence_format_parsed",
            seq_model=self._name,
            previous=previous,
            reset=sequence_number_reset,
            format=format,
        )
        return format, format_values

    @_debug.perf.timed
    def _locked_increment(self, format_string, format_values):
        cache = self._get_sequence_cache()
        seq = format_values["seq"]
        format_values = {k: v for k, v in format_values.items() if k != "seq"}
        cache_key = (
            format_string.format(**format_values, seq=0),
            self._sequence_index and self[self._sequence_index],
        )
        if cache_key in cache:
            cache[cache_key] += 1
            _debug.logic(
                "sequence_cache_hit",
                seq_model=self._name,
                seq_id=self,
                cache_key=cache_key[0],
                sequence_number=cache[cache_key],
            )
            return format_string.format(**format_values, seq=cache[cache_key])

        self.flush_recordset()
        columns = self.env.backend.columns
        while True:
            seq += 1
            sequence = format_string.format(**format_values, seq=seq)
            if columns.try_write(self, self._sequence_field, self.id, sequence):
                cache[cache_key] = seq
                _last_sequence_memo(self._name).discard(self.env)
                _debug.lifecycle(
                    "sequence_assigned",
                    seq_model=self._name,
                    seq_id=self,
                    sequence=sequence,
                )
                return sequence
            _debug.logic(
                "sequence_taken_retrying",
                seq_model=self._name,
                seq_id=self,
                sequence=sequence,
            )

    def _set_next_sequence(self):
        self.check_singleton()
        format_string, format_values = self._get_next_sequence_format()

        sequence = self._locked_increment(format_string, format_values)
        self.with_context(clear_sequence_mixin_cache=False)[self._sequence_field] = (
            sequence
        )

        self.modified([self._sequence_field])

        self._update_split_sequence()

    @_debug.perf.timed
    def _get_next_sequence_format(self):
        last_sequence = self._get_last_sequence()
        new = not last_sequence
        if new:
            last_sequence = (
                self._get_last_sequence(relaxed=True) or self._get_starting_sequence()
            )

        format_string, format_values = self._get_sequence_format_param(last_sequence)
        _debug.logic(
            "sequence_format",
            seq_model=self._name,
            seq_id=self,
            new_chain=new,
            last=last_sequence,
            format=format_string,
        )
        if new:
            if not self[self._sequence_date_field]:
                raise ValidationError(
                    _(
                        "A %(date_field)s is required to start a new sequence.",
                        date_field=self._fields[
                            self._sequence_date_field
                        ]._description_string(self.env),
                    )
                )
            sequence_number_reset = self._deduce_sequence_number_reset(last_sequence)
            date_start, date_end, forced_year_start, forced_year_end = (
                self._get_sequence_date_range(sequence_number_reset)
            )
            format_values["seq"] = 0
            format_values["year"] = self._truncate_year_to_length(
                forced_year_start or date_start.year, format_values["year_length"]
            )
            format_values["year_end"] = self._truncate_year_to_length(
                forced_year_end or date_end.year, format_values["year_end_length"]
            )
            format_values["month"] = self[self._sequence_date_field].month
        return format_string, format_values

    def _is_last_from_seq_chain(self):
        last_sequence = self._get_last_sequence(with_prefix=self.sequence_prefix)
        if not last_sequence:
            return True
        seq_format, seq_format_values = self._get_sequence_format_param(last_sequence)
        seq_format_values["seq"] += 1
        return seq_format.format(**seq_format_values) == self[self._sequence_field]

    def _is_end_of_seq_chain(self):
        batched = defaultdict(lambda: {"last_rec": self.browse(), "seq_list": []})
        for record in self.filtered(lambda x: x[x._sequence_field]):
            seq_format, format_values = record._get_sequence_format_param(
                record[record._sequence_field]
            )
            seq = format_values.pop("seq")
            batch = batched[(seq_format, frozendict(format_values))]
            batch["seq_list"].append(seq)
            if batch["last_rec"].sequence_number <= record.sequence_number:
                batch["last_rec"] = record

        for values in batched.values():
            seq_list = values["seq_list"]
            if max(seq_list) - min(seq_list) != len(seq_list) - 1:
                _debug.logic(
                    "seq_chain_has_gap",
                    seq_model=self._name,
                    seq_id=values["last_rec"],
                    batches=len(batched),
                )
                return False

            record = values["last_rec"]
            if not record._is_last_from_seq_chain():
                _debug.logic("seq_chain_not_last", seq_model=self._name, seq_id=record)
                return False
        _debug.logic(
            "seq_chain_end_confirmed", seq_model=self._name, batches=len(batched)
        )
        return True
