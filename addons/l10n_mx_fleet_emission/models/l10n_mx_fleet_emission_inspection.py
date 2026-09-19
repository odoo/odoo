from calendar import monthrange
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models

from .l10n_mx_fleet_emission_calendar import MONTH_ABBR, STICKER_COLORS

COLOR_INDEX = {"yellow": 3, "pink": 6, "red": 1, "green": 10, "blue": 7}


class L10nMxFleetEmissionInspection(models.Model):
    _name = "l10n_mx.fleet.emission.inspection"
    _description = "Emissions Inspection"
    _order = "year desc, period, color_sequence, asset_id"
    _rec_name = "display_name"

    asset_id = fields.Many2one(
        comodel_name="resource.asset.vehicle",
        string="Vehicle",
        index=True,
        required=True,
        ondelete="cascade",
    )
    license_plate = fields.Char(related="asset_id.license_plate")
    driver_id = fields.Many2one(
        related="asset_id.operator_id",
        string="Driver",
    )
    company_id = fields.Many2one(
        related="asset_id.company_id",
    )
    calendar_id = fields.Many2one(
        related="asset_id.l10n_mx_emission_calendar_id",
    )
    sticker_color = fields.Selection(
        selection=STICKER_COLORS,
        related="calendar_id.color",
    )
    color_sequence = fields.Integer(
        related="calendar_id.sequence",
    )
    color = fields.Integer(compute="_compute_color")
    year = fields.Integer(
        default=lambda self: fields.Date.today().year,
        required=True,
        aggregator=None,
    )
    period = fields.Selection(
        selection=[("1", "First Period"), ("2", "Second Period")],
        default="1",
        required=True,
    )
    window_display = fields.Char(
        string="Window",
        compute="_compute_window",
        store=True,
    )
    window_start = fields.Date(
        compute="_compute_window",
        store=True,
    )
    deadline = fields.Date(
        compute="_compute_window",
        store=True,
    )
    state = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("scheduled", "Scheduled"),
            ("done", "Passed"),
        ],
        default="pending",
        required=True,
    )
    is_done = fields.Boolean(
        string="Passed",
        compute="_compute_is_done",
        inverse="_inverse_is_done",
        help="Tick when the vehicle passed its inspection for this period.",
    )
    date_scheduled = fields.Date(
        string="Appointment",
        help="Appointment date at the inspection center.",
    )
    date_done = fields.Date(string="Passed On")
    certificate_number = fields.Char(help="Certificate or hologram folio.")
    notes = fields.Char()
    is_overdue = fields.Boolean(
        compute="_compute_is_overdue",
        search="_search_is_overdue",
    )

    _vehicle_period_uniq = models.Constraint(
        "unique(asset_id, year, period)",
        "A vehicle has one inspection per year and period.",
    )

    @api.depends("asset_id.license_plate", "asset_id.name", "year", "period")
    def _compute_display_name(self) -> None:
        for inspection in self:
            inspection.display_name = (
                f"{inspection.asset_id.license_plate or inspection.asset_id.name} "
                f"{inspection.year}/{inspection.period}"
            )

    @api.depends("sticker_color")
    def _compute_color(self) -> None:
        for inspection in self:
            inspection.color = COLOR_INDEX.get(inspection.sticker_color, 0)

    @api.depends(
        "calendar_id.first_period_start",
        "calendar_id.first_period_end",
        "calendar_id.second_period_start",
        "calendar_id.second_period_end",
        "year",
        "period",
    )
    def _compute_window(self) -> None:
        for inspection in self:
            if not inspection.calendar_id or not inspection.year:
                inspection.window_display = False
                inspection.window_start = False
                inspection.deadline = False
                continue
            year = inspection.year
            start, end = inspection.calendar_id._get_periods()[
                int(inspection.period) - 1
            ]
            inspection.window_display = f"{MONTH_ABBR[start - 1]}-{MONTH_ABBR[end - 1]}"
            inspection.window_start = date(year, start, 1)
            inspection.deadline = date(year, end, monthrange(year, end)[1])

    @api.depends("state")
    def _compute_is_done(self) -> None:
        for inspection in self:
            inspection.is_done = inspection.state == "done"

    def _inverse_is_done(self) -> None:
        today = fields.Date.context_today(self)
        for inspection in self:
            if inspection.is_done:
                inspection.state = "done"
                inspection.date_done = inspection.date_done or today
                inspection._file_certificate()
            else:
                inspection.state = (
                    "scheduled" if inspection.date_scheduled else "pending"
                )
                inspection.date_done = False

    @api.depends("state", "deadline")
    def _compute_is_overdue(self) -> None:
        today = fields.Date.context_today(self)
        for inspection in self:
            inspection.is_overdue = bool(
                inspection.state != "done"
                and inspection.deadline
                and inspection.deadline < today
            )

    def _search_is_overdue(self, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented
        today = fields.Date.context_today(self)
        domain = [("state", "!=", "done"), ("deadline", "<", today)]
        wants_overdue = (True in value) == (operator == "in")
        return domain if wants_overdue else ["!", *domain]

    @api.onchange("date_scheduled")
    def _onchange_date_scheduled(self) -> None:
        for inspection in self:
            if inspection.state != "done":
                inspection.state = (
                    "scheduled" if inspection.date_scheduled else "pending"
                )

    def write(self, vals):
        result = super().write(vals)
        if "date_scheduled" in vals and "state" not in vals:
            for inspection in self.filtered(lambda i: i.state != "done"):
                inspection.state = (
                    "scheduled" if inspection.date_scheduled else "pending"
                )
        return result

    def _get_certificate_type(self):
        return self.env.ref(
            "l10n_mx_fleet_emission.document_type_emission_certificate",
            raise_if_not_found=False,
        )

    def _get_certificate_expiration(self):
        """The hologram carries to the next deadline that falls after it was
        issued -- not after this inspection's own window, which may already have
        closed when a late inspection is finally passed. With no generated
        inspection beyond that date, the periods are semestral, so six months.
        """
        self.check_singleton()
        issued = self.date_done or fields.Date.context_today(self)
        following = self.search(
            [
                ("asset_id", "=", self.asset_id.id),
                ("deadline", ">", issued),
            ],
            order="deadline asc",
            limit=1,
        )
        return following.deadline or issued + relativedelta(months=6)

    def _file_certificate(self):
        """File the hologram against the vehicle, so the compliance report reads
        the same fact the inspection does."""
        self.check_singleton()
        document_type = self._get_certificate_type()
        if not document_type or not self.asset_id:
            return self.env["document.document"]
        filed = self.env["document.document"].search(
            [
                ("res_model", "=", "resource.asset"),
                ("res_id", "=", self.asset_id.id),
                ("document_type_id", "=", document_type.id),
                ("date_issued", "=", self.date_done),
            ],
            limit=1,
        )
        if filed:
            return filed
        name = self.certificate_number or self.display_name
        return self.asset_id._file_document(
            name,
            document_type_id=document_type.id,
            date_issued=self.date_done,
            date_expiration=self._get_certificate_expiration(),
        )

    def action_mark_done(self) -> None:
        self.write({"is_done": True})

    @api.model
    def action_generate_current_year(self) -> None:
        today = fields.Date.context_today(self)
        self._generate_inspections(year=today.year)
        if today.month == 12:
            self._generate_inspections(year=today.year + 1)

    @api.model
    def _cron_generate_inspections(self) -> None:
        self.action_generate_current_year()

    @api.model
    def _generate_inspections(
        self, year: int, vehicles=None
    ) -> L10nMxFleetEmissionInspection:
        if vehicles is None:
            vehicles = self.env["resource.asset.vehicle"].search(
                [("l10n_mx_emission_calendar_id", "!=", False)]
            )
        else:
            vehicles = vehicles.filtered("l10n_mx_emission_calendar_id")
        existing = {
            (inspection.asset_id.id, inspection.period)
            for inspection in self.search(
                [("asset_id", "in", vehicles.ids), ("year", "=", year)]
            )
        }
        return self.create(
            [
                {"asset_id": vehicle.id, "year": year, "period": period}
                for vehicle in vehicles
                for period in ("1", "2")
                if (vehicle.id, period) not in existing
            ]
        )
