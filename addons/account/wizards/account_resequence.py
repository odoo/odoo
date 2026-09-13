import json
from collections import defaultdict

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools.date_utils import get_fiscal_year
from odoo.tools.misc import format_date

_debug = DebugLog(__name__)


class AccountResequenceWizard(models.TransientModel):
    _name = "account.resequence.wizard"
    _description = "Remake the sequence of Journal Entries."

    sequence_number_reset = fields.Char(compute="_compute_sequence_number_reset")
    first_date = fields.Date(
        help="Date (inclusive) from which the numbers are resequenced."
    )
    end_date = fields.Date(
        help="Date (inclusive) to which the numbers are resequenced. If not set, all Journal Entries up to the end of the period are resequenced."
    )
    first_name = fields.Char(
        string="First New Sequence",
        compute="_compute_first_name",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
    )
    ordering = fields.Selection(
        selection=[
            ("keep", "Keep current order"),
            ("date", "Reorder by accounting date"),
        ],
        default="keep",
        required=True,
    )
    move_ids = fields.Many2many(comodel_name="account.move")
    new_values = fields.Text(compute="_compute_new_values")
    preview_moves = fields.Text(compute="_compute_preview_moves")

    @api.model
    @_debug.perf.timed
    def default_get(self, fields_list):
        _debug.lifecycle("default_get", records=self)
        values = super().default_get(fields_list)
        if "move_ids" not in fields_list:
            return values
        active_move_ids = self.env["account.move"]
        if (
            self.env.context.get("active_model") == "account.move"
            and "active_ids" in self.env.context
        ):
            active_move_ids = self.env["account.move"].browse(
                self.env.context["active_ids"]
            )
        if len(active_move_ids.journal_id) > 1:
            raise UserError(_("You can only resequence items from the same journal"))
        move_types = set(active_move_ids.mapped("move_type"))
        if (
            active_move_ids.journal_id.refund_sequence
            and ("in_refund" in move_types or "out_refund" in move_types)
            and len(move_types) > 1
        ):
            raise UserError(
                _(
                    "The sequences of this journal are different for Invoices and Refunds but you selected some of both types."
                )
            )
        is_payment = set(active_move_ids.mapped(lambda x: bool(x.origin_payment_id)))
        if active_move_ids.journal_id.payment_sequence and len(is_payment) > 1:
            raise UserError(
                _(
                    "The sequences of this journal are different for Payments and non-Payments but you selected some of both types."
                )
            )
        if _debug.logic.enabled:
            _debug.logic(
                "resequence_moves_selected",
                move=active_move_ids,
                journal=active_move_ids.journal_id,
                move_types=sorted(move_types),
                payment_kinds=len(is_payment),
            )
        values["move_ids"] = [Command.set(active_move_ids.ids)]
        return values

    @api.depends("first_name", "move_ids")
    def _compute_sequence_number_reset(self):
        for record in self:
            if record.move_ids:
                record.sequence_number_reset = record.move_ids[
                    0
                ]._deduce_sequence_number_reset(record.first_name)
            else:
                record.sequence_number_reset = False

    @api.depends("move_ids")
    def _compute_first_name(self):
        self.first_name = ""
        for record in self:
            if record.move_ids:
                record.first_name = min(
                    record.move_ids._origin.mapped(lambda move: move.name or "")
                )

    @api.depends("new_values", "ordering", "sequence_number_reset")
    @_debug.perf.timed
    def _compute_preview_moves(self):
        for record in self:
            new_values = sorted(
                json.loads(record.new_values).values(),
                key=lambda x: x["server-date"],
                reverse=True,
            )
            change_lines = []
            in_elipsis = 0
            previous_line = None
            for i, line in enumerate(new_values):
                if (
                    i < 3
                    or i == len(new_values) - 1
                    or line["new_by_name"] != line["new_by_date"]
                    or (
                        record.sequence_number_reset == "year"
                        and line["server-date"][0:4]
                        != previous_line["server-date"][0:4]
                    )
                    or (
                        record.sequence_number_reset == "year_range"
                        and line["server-year-start-date"][0:4]
                        != previous_line["server-year-start-date"][0:4]
                    )
                    or (
                        record.sequence_number_reset == "month"
                        and line["server-date"][0:7]
                        != previous_line["server-date"][0:7]
                    )
                ):
                    if in_elipsis:
                        change_lines.append(
                            {
                                "id": "other_" + str(line["id"]),
                                "current_name": _(
                                    "... (%(nb_of_values)s other)",
                                    nb_of_values=in_elipsis,
                                ),
                                "new_by_name": "...",
                                "new_by_date": "...",
                                "date": "...",
                            }
                        )
                        in_elipsis = 0
                    change_lines.append(line)
                else:
                    in_elipsis += 1
                previous_line = line

            if _debug.pipeline.enabled:
                _debug.pipeline(
                    "resequence_preview_built",
                    resequence=record,
                    moves=len(new_values),
                    shown_lines=len(change_lines),
                    reset=record.sequence_number_reset,
                    ordering=record.ordering,
                )
            record.preview_moves = json.dumps(
                {
                    "ordering": record.ordering,
                    "changeLines": change_lines,
                }
            )

    def _get_resequence_period_key(self, move, sequence_number_reset):
        company = move.company_id
        date_start, date_end = get_fiscal_year(
            move.date,
            day=company.fiscalyear_last_day,
            month=int(company.fiscalyear_last_month),
        )
        match sequence_number_reset:
            case "year":
                return move.date.year
            case "year_range":
                return "%s-%s" % (date_start.year, date_end.year)
            case "year_range_month":
                return "%s-%s/%s" % (date_start.year, date_end.year, move.date.month)
            case "month":
                return (move.date.year, move.date.month)
            case _:
                return "default"

    @_debug.perf.timed
    def _update_resequence_period_values(
        self,
        new_values,
        period_recs,
        sequence_number_reset,
        seq_format,
        format_values,
        is_last_period,
    ):
        date_start, date_end, forced_year_start, forced_year_end = period_recs[
            0
        ]._get_sequence_date_range(sequence_number_reset)
        for move in period_recs:
            new_values[move.id] = {
                "id": move.id,
                "current_name": move.name,
                "state": move.state,
                "date": format_date(self.env, move.date),
                "server-date": str(move.date),
                "server-year-start-date": str(date_start),
            }

        new_name_list = [
            seq_format.format(
                **{
                    **format_values,
                    "month": date_start.month,
                    "year_end": (forced_year_end or date_end.year)
                    % (10 ** format_values["year_end_length"]),
                    "year": (forced_year_start or date_start.year)
                    % (10 ** format_values["year_length"]),
                    "seq": i + (format_values["seq"] if is_last_period else 1),
                }
            )
            for i in range(len(period_recs))
        ]
        _debug.pipeline(
            "resequence_period_named",
            resequence=self,
            moves=len(period_recs),
            date_start=date_start,
            date_end=date_end,
            reset=sequence_number_reset,
            is_last_period=is_last_period,
        )

        for move, new_name in zip(
            period_recs.sorted(lambda m: (m.sequence_prefix, m.sequence_number)),
            new_name_list,
            strict=True,
        ):
            new_values[move.id]["new_by_name"] = new_name
        for move, new_name in zip(
            period_recs.sorted(lambda m: (m.date, m.name or "", m.id)),
            new_name_list,
            strict=True,
        ):
            new_values[move.id]["new_by_date"] = new_name

    @api.depends("first_name", "move_ids", "sequence_number_reset")
    @api.depends_context("lang")
    @_debug.perf.timed
    def _compute_new_values(self):
        self.new_values = "{}"
        for record in self.filtered("first_name"):
            sequence_number_reset = record.move_ids[0]._deduce_sequence_number_reset(
                record.first_name
            )
            moves_by_period = defaultdict(
                lambda record=record: record.env["account.move"]
            )
            for move in record.move_ids._origin:
                key = self._get_resequence_period_key(move, sequence_number_reset)
                moves_by_period[key] += move

            seq_format, format_values = record.move_ids[0]._get_sequence_format_param(
                record.first_name
            )

            new_values = {}
            for j, period_recs in enumerate(moves_by_period.values()):
                self._update_resequence_period_values(
                    new_values,
                    period_recs,
                    sequence_number_reset,
                    seq_format,
                    format_values,
                    j == (len(moves_by_period) - 1),
                )

            record.new_values = json.dumps(new_values)

    def resequence(self):
        self.check_singleton()
        new_values = json.loads(self.new_values)
        if (
            self.move_ids.journal_id
            and self.move_ids.journal_id.restrict_mode_hash_table
        ):
            if self.ordering == "date":
                raise UserError(
                    _(
                        "You can not reorder sequence by date when the journal is locked with a hash."
                    )
                )
        moves_to_rename = self.env["account.move"].browse(int(k) for k in new_values)
        if _debug.pipeline.enabled:
            _debug.pipeline(
                "renaming",
                resequence=self,
                ordering=self.ordering,
                first=self.first_name,
                moves_to_rename=moves_to_rename,
            )
        moves_to_rename.name = False
        moves_to_rename.flush_recordset(["name"])

        for move_id in self.move_ids:
            if str(move_id.id) in new_values:
                if self.ordering == "keep":
                    move_id.name = new_values[str(move_id.id)]["new_by_name"]
                else:
                    move_id.name = new_values[str(move_id.id)]["new_by_date"]
