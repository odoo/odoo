import logging
from datetime import datetime, timedelta
from typing import Any, Self

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import SQL
from odoo.orm._typing import ValuesType

_logger = logging.getLogger(__name__)


def _create_sequence(
    cr: Any, seq_name: str, number_increment: int, number_next: int
) -> None:
    """Create a PostgreSQL sequence."""
    if number_increment == 0:
        raise UserError(_("Step must not be zero."))
    cr.execute(
        SQL(
            "CREATE SEQUENCE %s INCREMENT BY %s START WITH %s",
            SQL.identifier(seq_name),
            number_increment,
            number_next,
        )
    )


def _drop_sequences(cr: Any, seq_names: list[str]) -> None:
    """Drop the PostgreSQL sequences if they exist."""
    if not seq_names:
        return
    names = SQL(",").join(map(SQL.identifier, seq_names))
    # RESTRICT is the default; it prevents dropping the sequence if an
    # object depends on it.
    cr.execute(SQL("DROP SEQUENCE IF EXISTS %s RESTRICT", names))


def _alter_sequence(
    cr: Any,
    seq_name: str,
    number_increment: int | None = None,
    number_next: int | None = None,
) -> None:
    """Alter a PostgreSQL sequence."""
    if number_increment is None and number_next is None:
        return  # nothing to alter
    if number_increment == 0:
        raise UserError(_("Step must not be zero."))
    cr.execute(
        "SELECT relname FROM pg_class"
        " WHERE relkind = %s AND relname = %s"
        "   AND relnamespace = current_schema::regnamespace",
        ("S", seq_name),
    )
    if not cr.fetchone():
        # sequence is not created yet, we're inside create() so ignore it, will be set later
        return
    statement = SQL(
        "ALTER SEQUENCE %s%s%s",
        SQL.identifier(seq_name),
        (
            SQL(" INCREMENT BY %s", number_increment)
            if number_increment is not None
            else SQL()
        ),
        (SQL(" RESTART WITH %s", number_next) if number_next is not None else SQL()),
    )
    cr.execute(statement)


def _select_nextval(cr: Any, seq_name: str) -> int:
    """Return the next value from a PostgreSQL sequence as an integer."""
    cr.execute("SELECT nextval(%s)", [seq_name])
    return cr.fetchone()[0]


def _update_nogap(self: Any, number_increment: int) -> int:
    self.flush_recordset(["number_next"])
    table = SQL.identifier(self._table)
    self.env.cr.execute(
        SQL(
            "SELECT number_next FROM %s WHERE id=%s FOR UPDATE NOWAIT",
            table,
            self.id,
        )
    )
    # Read the locked row's actual value instead of using the ORM cache,
    # which may be stale under concurrent access (READ COMMITTED isolation).
    [number_next] = self.env.cr.fetchone()
    self.env.cr.execute(
        SQL(
            "UPDATE %s SET number_next=number_next+%s WHERE id=%s",
            table,
            number_increment,
            self.id,
        )
    )
    self.invalidate_recordset(["number_next"])
    return number_next


def _predict_nextval(self: Any, seq_id: str) -> int:
    """Predict next value for PostgreSQL sequence without consuming it"""
    # Cannot use currval() as it requires prior call to nextval()
    seqname = f"ir_sequence_{seq_id}"
    seqtable = SQL.identifier(seqname)
    query = SQL(
        """
        SELECT last_value,
            (SELECT increment_by FROM pg_sequences WHERE sequencename = %s),
            is_called
        FROM %s""",
        seqname,
        seqtable,
    )
    rows = self.env.execute_query(query)
    if not rows:
        return 1  # sequence object missing; fall back to safe default
    [(last_value, increment_by, is_called)] = rows
    if is_called:
        return last_value + increment_by
    # sequence has just been RESTARTed to return last_value next time
    return last_value


class IrSequence(models.Model):
    """Sequence model.

    The sequence model allows to define and use so-called sequence objects.
    Such objects are used to generate unique identifiers in a transaction-safe
    way.

    """

    _name = "ir.sequence"
    _description = "Sequence"
    _order = "name, id"
    _allow_sudo_commands = False

    def _get_number_next_actual(self) -> None:
        """Return number from ir_sequence row when no_gap implementation,
        and number from postgres sequence when standard implementation."""
        for seq in self:
            if not seq.id:
                seq.number_next_actual = 0
            elif seq.implementation != "standard":
                seq.number_next_actual = seq.number_next
            else:
                seq_id = "%03d" % seq.id
                seq.number_next_actual = _predict_nextval(seq, seq_id)

    def _set_number_next_actual(self) -> None:
        for seq in self:
            # Preserve 0 — valid starting value for a PostgreSQL sequence.
            # `or 1` would silently convert an explicit 0 to 1.
            val = seq.number_next_actual
            seq.write({"number_next": val if val is not None else 1})

    def _get_current_sequence(self, sequence_date: Any = None) -> Any:
        """Returns the object on which we can find the number_next to consider for the sequence.
        It could be an ir.sequence or an ir.sequence.date_range depending if use_date_range is checked
        or not. This function will also create the ir.sequence.date_range if none exists yet for today
        """
        if not self.use_date_range:
            return self
        sequence_date = sequence_date or fields.Date.today()
        seq_date = self.env["ir.sequence.date_range"].search(
            [
                ("sequence_id", "=", self.id),
                ("date_from", "<=", sequence_date),
                ("date_to", ">=", sequence_date),
            ],
            limit=1,
        )
        if seq_date:
            return seq_date[0]
        # no date_range sequence was found, we create a new one
        return self._create_date_range_seq(sequence_date)

    name = fields.Char(required=True)
    code = fields.Char(string="Sequence Code")
    implementation = fields.Selection(
        [("standard", "Standard"), ("no_gap", "No gap")],
        string="Implementation",
        required=True,
        default="standard",
        help="While assigning a sequence number to a record, the 'no gap' sequence implementation ensures that each previous sequence number has been assigned already. "
        "While this sequence implementation will not skip any sequence number upon assignment, there can still be gaps in the sequence if records are deleted. "
        "The 'no gap' implementation is slower than the standard one.",
    )
    active = fields.Boolean(default=True)
    prefix = fields.Char(help="Prefix value of the record for the sequence", trim=False)
    suffix = fields.Char(help="Suffix value of the record for the sequence", trim=False)
    number_next = fields.Integer(
        string="Next Number",
        required=True,
        default=1,
        help="Next number of this sequence",
    )
    number_next_actual = fields.Integer(
        compute="_get_number_next_actual",
        inverse="_set_number_next_actual",
        string="Actual Next Number",
        help="Next number that will be used. This number can be incremented "
        "frequently so the displayed value might already be obsolete",
    )
    number_increment = fields.Integer(
        string="Step",
        required=True,
        default=1,
        help="The next number of the sequence will be incremented by this number",
    )
    padding = fields.Integer(
        string="Sequence Size",
        required=True,
        default=0,
        help="Odoo will automatically adds some '0' on the left of the 'Next Number' to get the required padding size.",
    )
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda s: s.env.company
    )
    use_date_range = fields.Boolean(string="Use subsequences per date_range")
    date_range_ids = fields.One2many(
        "ir.sequence.date_range", "sequence_id", string="Subsequences"
    )

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        """Create a sequence, in implementation == standard a fast gaps-allowed PostgreSQL sequence is used."""
        seqs = super().create(vals_list)
        for seq in seqs:
            if seq.implementation == "standard":
                _create_sequence(
                    self.env.cr,
                    "ir_sequence_%03d" % seq.id,
                    seq.number_increment or 1,
                    seq.number_next if seq.number_next is not None else 1,
                )
        return seqs

    def unlink(self) -> bool:
        _drop_sequences(self.env.cr, ["ir_sequence_%03d" % x.id for x in self])
        return super().unlink()

    def write(self, vals: dict[str, Any]) -> bool:
        new_implementation = vals.get("implementation")
        for seq in self:
            # 4 cases: we test the previous impl. against the new one.
            i = vals.get("number_increment", seq.number_increment)
            n = vals.get("number_next", seq.number_next)
            if seq.implementation == "standard":
                if new_implementation in ("standard", None):
                    # Implementation has NOT changed.
                    # Only change sequence if really requested.
                    if "number_next" in vals:
                        _alter_sequence(
                            self.env.cr,
                            "ir_sequence_%03d" % seq.id,
                            number_next=n,
                        )
                    if seq.number_increment != i:
                        _alter_sequence(
                            self.env.cr,
                            "ir_sequence_%03d" % seq.id,
                            number_increment=i,
                        )
                        seq.date_range_ids._alter_sequence(number_increment=i)
                else:
                    _drop_sequences(self.env.cr, ["ir_sequence_%03d" % seq.id])
                    for sub_seq in seq.date_range_ids:
                        _drop_sequences(
                            self.env.cr,
                            ["ir_sequence_%03d_%03d" % (seq.id, sub_seq.id)],
                        )
            elif new_implementation in ("no_gap", None):
                pass
            else:
                _create_sequence(self.env.cr, "ir_sequence_%03d" % seq.id, i, n)
                for sub_seq in seq.date_range_ids:
                    _create_sequence(
                        self.env.cr,
                        "ir_sequence_%03d_%03d" % (seq.id, sub_seq.id),
                        i,
                        n,
                    )
        res = super().write(vals)
        # DLE P179
        self.flush_model(vals.keys())
        return res

    def _next_do(self) -> str:
        if self.implementation == "standard":
            number_next = _select_nextval(self.env.cr, "ir_sequence_%03d" % self.id)
        else:
            number_next = _update_nogap(self, self.number_increment)
        return self.get_next_char(number_next)

    def _get_prefix_suffix(
        self, date: Any = None, date_range: Any = None
    ) -> tuple[str, str]:
        def _interpolate(s, d):
            return (s % d) if s else ""

        def _interpolation_dict():
            now = range_date = effective_date = datetime.now(self.env.tz)
            if date or self.env.context.get("ir_sequence_date"):
                effective_date = fields.Datetime.from_string(
                    date or self.env.context.get("ir_sequence_date")
                )
            if date_range or self.env.context.get("ir_sequence_date_range"):
                range_date = fields.Datetime.from_string(
                    date_range or self.env.context.get("ir_sequence_date_range")
                )

            sequences = {
                "year": "%Y",
                "month": "%m",
                "day": "%d",
                "y": "%y",
                "doy": "%j",
                "woy": "%W",
                "weekday": "%w",
                "h24": "%H",
                "h12": "%I",
                "min": "%M",
                "sec": "%S",
                "isoyear": "%G",
                "isoy": "%g",
                "isoweek": "%V",
            }
            res = {}
            for key, format in sequences.items():
                res[key] = effective_date.strftime(format)
                res["range_" + key] = range_date.strftime(format)
                res["current_" + key] = now.strftime(format)

            return res

        self.ensure_one()
        d = _interpolation_dict()
        try:
            interpolated_prefix = _interpolate(self.prefix, d)
            interpolated_suffix = _interpolate(self.suffix, d)
        except ValueError, TypeError, KeyError:
            raise UserError(_("Invalid prefix or suffix for sequence “%s”", self.name))
        return interpolated_prefix, interpolated_suffix

    def get_next_char(self, number_next: int) -> str:
        interpolated_prefix, interpolated_suffix = self._get_prefix_suffix()
        return (
            interpolated_prefix
            + f"{number_next:0{max(0, self.padding)}d}"
            + interpolated_suffix
        )

    def _create_date_range_seq(self, date: Any) -> Any:
        year = fields.Date.from_string(date).strftime("%Y")
        date_from = f"{year}-01-01"
        date_to = f"{year}-12-31"
        date_range = self.env["ir.sequence.date_range"].search(
            [
                ("sequence_id", "=", self.id),
                ("date_from", ">=", date),
                ("date_from", "<=", date_to),
            ],
            order="date_from desc",
            limit=1,
        )
        if date_range:
            date_to = date_range.date_from + timedelta(days=-1)
        date_range = self.env["ir.sequence.date_range"].search(
            [
                ("sequence_id", "=", self.id),
                ("date_to", ">=", date_from),
                ("date_to", "<=", date),
            ],
            order="date_to desc",
            limit=1,
        )
        if date_range:
            date_from = date_range.date_to + timedelta(days=1)
        return (
            self.env["ir.sequence.date_range"]
            .sudo()
            .create(
                {
                    "date_from": date_from,
                    "date_to": date_to,
                    "sequence_id": self.id,
                }
            )
        )

    def _next(self, sequence_date: Any = None) -> str:
        """Returns the next number in the preferred sequence in all the ones given in self."""
        if not self.use_date_range:
            return self._next_do()
        # date mode
        dt = sequence_date or self.env.context.get(
            "ir_sequence_date", fields.Date.today()
        )
        seq_date = self.env["ir.sequence.date_range"].search(
            [
                ("sequence_id", "=", self.id),
                ("date_from", "<=", dt),
                ("date_to", ">=", dt),
            ],
            limit=1,
        )
        if not seq_date:
            seq_date = self._create_date_range_seq(dt)
        return seq_date.with_context(ir_sequence_date_range=seq_date.date_from)._next()

    def next_by_id(self, sequence_date: Any = None) -> str:
        """Draw an interpolated string using the specified sequence."""
        self.browse().check_access("read")
        return self._next(sequence_date=sequence_date)

    @api.model
    def next_by_code(self, sequence_code: str, sequence_date: Any = None) -> str | bool:
        """Draw an interpolated string using a sequence with the requested code.
        If several sequences with the correct code are available to the user
        (multi-company cases), the one from the user's current company will
        be used.
        """
        self.browse().check_access("read")
        company_id = self.env.company.id
        seq_ids = self.search(
            [
                ("code", "=", sequence_code),
                ("company_id", "in", [company_id, False]),
            ],
            order="company_id",
        )
        if not seq_ids:
            _logger.debug(
                "No ir.sequence has been found for code '%s'. Please make sure a sequence is set for current company.",
                sequence_code,
            )
            return False
        seq_id = seq_ids[0]
        return seq_id._next(sequence_date=sequence_date)


class IrSequenceDate_Range(models.Model):
    _name = "ir.sequence.date_range"
    _description = "Sequence Date Range"
    _rec_name = "sequence_id"
    _allow_sudo_commands = False

    _unique_range_per_sequence = models.Constraint(
        "UNIQUE(sequence_id, date_from, date_to)",
        "You cannot create two date ranges for the same sequence with the same date range.",
    )

    def _get_number_next_actual(self) -> None:
        """Return number from ir_sequence row when no_gap implementation,
        and number from postgres sequence when standard implementation."""
        for seq in self:
            if seq.sequence_id.implementation != "standard":
                seq.number_next_actual = seq.number_next
            else:
                seq_id = "%03d_%03d" % (seq.sequence_id.id, seq.id)
                seq.number_next_actual = _predict_nextval(seq, seq_id)

    def _set_number_next_actual(self) -> None:
        for seq in self:
            val = seq.number_next_actual
            seq.write({"number_next": val if val is not None else 1})

    @api.model
    def default_get(self, fields: list[str]) -> dict[str, Any]:
        result = super().default_get(fields)
        if "number_next_actual" in fields:
            result["number_next_actual"] = 1
        return result

    date_from = fields.Date(string="From", required=True)
    date_to = fields.Date(string="To", required=True)
    sequence_id = fields.Many2one(
        "ir.sequence", string="Main Sequence", required=True, ondelete="cascade"
    )
    number_next = fields.Integer(
        string="Next Number",
        required=True,
        default=1,
        help="Next number of this sequence",
    )
    number_next_actual = fields.Integer(
        compute="_get_number_next_actual",
        inverse="_set_number_next_actual",
        string="Actual Next Number",
        help="Next number that will be used. This number can be incremented "
        "frequently so the displayed value might already be obsolete",
    )

    def _next(self) -> str:
        if self.sequence_id.implementation == "standard":
            number_next = _select_nextval(
                self.env.cr,
                "ir_sequence_%03d_%03d" % (self.sequence_id.id, self.id),
            )
        else:
            number_next = _update_nogap(self, self.sequence_id.number_increment)
        return self.sequence_id.get_next_char(number_next)

    def _alter_sequence(
        self,
        number_increment: int | None = None,
        number_next: int | None = None,
    ) -> None:
        for seq in self:
            _alter_sequence(
                self.env.cr,
                "ir_sequence_%03d_%03d" % (seq.sequence_id.id, seq.id),
                number_increment=number_increment,
                number_next=number_next,
            )

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        """Create a sequence, in implementation == standard a fast gaps-allowed PostgreSQL sequence is used."""
        seqs = super().create(vals_list)
        for seq in seqs:
            main_seq = seq.sequence_id
            if main_seq.implementation == "standard":
                val = seq.number_next_actual
                _create_sequence(
                    self.env.cr,
                    "ir_sequence_%03d_%03d" % (main_seq.id, seq.id),
                    main_seq.number_increment or 1,
                    val if val is not None else 1,
                )
        return seqs

    def unlink(self) -> bool:
        _drop_sequences(
            self.env.cr,
            ["ir_sequence_%03d_%03d" % (x.sequence_id.id, x.id) for x in self],
        )
        return super().unlink()

    def write(self, vals: dict[str, Any]) -> bool:
        if "number_next" in vals:
            seq_to_alter = self.filtered(
                lambda seq: seq.sequence_id.implementation == "standard"
            )
            seq_to_alter._alter_sequence(number_next=vals["number_next"])
        # DLE P179: `test_in_invoice_line_onchange_sequence_number_1`
        # _update_nogap do a select to get the next sequence number_next
        # When changing (writing) the number next of a sequence, the number next must be flushed before doing the select.
        # Normally in such a case, we flush just above the execute, but for the sake of performance
        # I believe this is better to flush directly in the write:
        #  - Changing the number next of a sequence is really really rare,
        #  - But selecting the number next happens a lot,
        # Therefore, if I chose to put the flush just above the select, it would check the flush most of the time for no reason.
        res = super().write(vals)
        self.flush_model(vals.keys())
        return res
