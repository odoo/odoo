from odoo import api, fields, models
from odoo.exceptions import ValidationError

STICKER_COLORS = [
    ("yellow", "Yellow"),
    ("pink", "Pink"),
    ("red", "Red"),
    ("green", "Green"),
    ("blue", "Blue"),
]

MONTH_ABBR = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]  # fmt: skip


class L10nMxFleetEmissionCalendar(models.Model):
    _name = "l10n_mx.fleet.emission.calendar"
    _description = "Emissions Inspection Calendar"
    _order = "sequence, id"

    name = fields.Char(
        translate=True,
        required=True,
    )
    sequence = fields.Integer(default=10)
    color = fields.Selection(
        selection=STICKER_COLORS,
        required=True,
    )
    plate_digits = fields.Char(
        required=True,
        help="Last digits of the license plate covered by this color, e.g. '5,6'.",
    )
    first_period_start = fields.Integer(
        required=True,
        help="Month number, 1-12.",
    )
    first_period_end = fields.Integer(
        required=True,
        help="Month number, 1-12.",
    )
    second_period_start = fields.Integer(
        required=True,
        help="Month number, 1-12.",
    )
    second_period_end = fields.Integer(
        required=True,
        help="Month number, 1-12.",
    )
    period_display = fields.Char(compute="_compute_period_display")

    _color_uniq = models.Constraint("unique(color)", "Each color can appear only once.")

    @api.depends(
        "first_period_start",
        "first_period_end",
        "second_period_start",
        "second_period_end",
    )
    def _compute_period_display(self) -> None:
        for calendar in self:
            calendar.period_display = " / ".join(
                f"{MONTH_ABBR[start - 1]}-{MONTH_ABBR[end - 1]}"
                for start, end in calendar._get_periods()
            )

    @api.constrains(
        "first_period_start",
        "first_period_end",
        "second_period_start",
        "second_period_end",
        "plate_digits",
    )
    def _check_values(self) -> None:
        for calendar in self:
            for start, end in calendar._get_periods():
                if not (1 <= start <= end <= 12):
                    raise ValidationError(
                        self.env._(
                            "Inspection periods must be month ranges within 1-12."
                        )
                    )
            if not calendar._get_digits():
                raise ValidationError(
                    self.env._("Plate digits must be a comma-separated list of digits.")
                )

    @api.model_create_multi
    def create(self, vals_list):
        calendars = super().create(vals_list)
        self._recompute_vehicles()
        return calendars

    def write(self, vals):
        result = super().write(vals)
        self._recompute_vehicles()
        return result

    def unlink(self):
        result = super().unlink()
        self._recompute_vehicles()
        return result

    def _get_periods(self) -> list[tuple[int, int]]:
        self.check_singleton()
        return [
            (self.first_period_start, self.first_period_end),
            (self.second_period_start, self.second_period_end),
        ]

    def _get_digits(self) -> set[str]:
        self.check_singleton()
        digits = {d.strip() for d in (self.plate_digits or "").split(",")}
        return {d for d in digits if len(d) == 1 and d.isdigit()}

    def _recompute_vehicles(self) -> None:
        # A vehicle's calendar depends on every row of this table, so a change here
        # is pushed to all vehicles by hand; a recompute queued this way does not
        # cascade, so what reads through the calendar is dropped from the cache.
        vehicles = (
            self.env["resource.asset"]
            .with_context(active_test=False)
            .search([("is_vehicle", "=", True)])
        )
        self.env.add_to_compute(
            vehicles._fields["l10n_mx_emission_calendar_id"], vehicles
        )
        vehicles.flush_recordset(["l10n_mx_emission_calendar_id"])
        vehicles.invalidate_recordset(
            ["l10n_mx_emission_color", "l10n_mx_emission_period"]
        )
        inspections = self.env["l10n_mx.fleet.emission.inspection"].search(
            [("asset_id", "in", vehicles.ids)]
        )
        inspections.invalidate_recordset(
            ["calendar_id", "sticker_color", "color_sequence"]
        )
        self.env.add_to_compute(inspections._fields["deadline"], inspections)
