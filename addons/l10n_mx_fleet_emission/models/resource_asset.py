from calendar import monthrange
from datetime import date

from odoo import api, fields, models

from .l10n_mx_fleet_emission_calendar import STICKER_COLORS


class ResourceAsset(models.Model):
    _inherit = "resource.asset.vehicle"

    l10n_mx_emission_plate_digit = fields.Char(
        string="Plate Digit",
        compute="_compute_l10n_mx_emission_plate_digit",
        store=True,
        help="Last digit of the license plate; decides the sticker color.",
    )
    l10n_mx_emission_calendar_id = fields.Many2one(
        comodel_name="l10n_mx.fleet.emission.calendar",
        string="Emissions Calendar",
        compute="_compute_l10n_mx_emission_calendar_id",
        store=True,
    )
    l10n_mx_emission_color = fields.Selection(
        selection=STICKER_COLORS,
        related="l10n_mx_emission_calendar_id.color",
        string="Sticker Color",
    )
    l10n_mx_emission_period = fields.Char(
        related="l10n_mx_emission_calendar_id.period_display",
        string="Inspection Windows",
    )
    l10n_mx_emission_inspection_ids = fields.One2many(
        comodel_name="l10n_mx.fleet.emission.inspection",
        inverse_name="asset_id",
        string="Emissions Inspections",
    )
    l10n_mx_emission_pending_count = fields.Integer(
        compute="_compute_l10n_mx_emission_pending_count"
    )
    l10n_mx_emission_last_date = fields.Date(
        string="Last Inspection",
        compute="_compute_l10n_mx_emission_last_date",
        help="Date of the last emissions inspection this vehicle passed.",
    )
    l10n_mx_emission_deadline = fields.Date(
        string="Inspection Deadline",
        compute="_compute_l10n_mx_emission_status",
        help="Last day of the current semester's inspection window.",
    )
    l10n_mx_emission_status = fields.Selection(
        selection=[
            ("passed", "Passed"),
            ("scheduled", "Scheduled"),
            ("due", "Due Now"),
            ("overdue", "Overdue"),
            ("upcoming", "Upcoming"),
        ],
        string="Inspection Status",
        compute="_compute_l10n_mx_emission_status",
        search="_search_l10n_mx_emission_status",
    )

    @api.depends("license_plate")
    def _compute_l10n_mx_emission_plate_digit(self) -> None:
        for asset in self:
            digits = [c for c in (asset.license_plate or "") if c.isdigit()]
            asset.l10n_mx_emission_plate_digit = digits[-1] if digits else False

    @api.depends("l10n_mx_emission_plate_digit")
    def _compute_l10n_mx_emission_calendar_id(self) -> None:
        calendars = self.env["l10n_mx.fleet.emission.calendar"].search([])
        by_digit = {
            digit: calendar
            for calendar in calendars
            for digit in calendar._get_digits()
        }
        for asset in self:
            asset.l10n_mx_emission_calendar_id = (
                by_digit.get(asset.l10n_mx_emission_plate_digit, False)
            )

    @api.depends("l10n_mx_emission_inspection_ids.state")
    def _compute_l10n_mx_emission_pending_count(self) -> None:
        for asset in self:
            asset.l10n_mx_emission_pending_count = len(
                asset.l10n_mx_emission_inspection_ids.filtered(
                    lambda i: i.state != "done"
                )
            )

    @api.depends(
        "l10n_mx_emission_inspection_ids.state",
        "l10n_mx_emission_inspection_ids.date_done",
    )
    def _compute_l10n_mx_emission_last_date(self) -> None:
        for asset in self:
            dates = asset.l10n_mx_emission_inspection_ids.filtered("date_done").mapped(
                "date_done"
            )
            asset.l10n_mx_emission_last_date = max(dates) if dates else False

    @api.depends(
        "l10n_mx_emission_calendar_id",
        "l10n_mx_emission_inspection_ids.state",
        "l10n_mx_emission_inspection_ids.year",
        "l10n_mx_emission_inspection_ids.period",
    )
    def _compute_l10n_mx_emission_status(self) -> None:
        today = fields.Date.context_today(self)
        for asset in self:
            asset.l10n_mx_emission_status = asset._get_l10n_mx_emission_status(today)
            asset.l10n_mx_emission_deadline = asset._get_l10n_mx_emission_deadline(
                today
            )

    @api.model_create_multi
    def create(self, vals_list):
        assets = super().create(vals_list)
        assets._generate_l10n_mx_emission_inspections()
        return assets

    def _write_concrete(self, vals):
        result = super()._write_concrete(vals)
        if "license_plate" in vals or "product_id" in vals:
            self._generate_l10n_mx_emission_inspections()
        return result

    def _generate_l10n_mx_emission_inspections(self) -> None:
        vehicles = self.filtered("l10n_mx_emission_calendar_id")
        if not vehicles:
            return
        # The checklist follows the plate, whoever registers the vehicle.
        year = fields.Date.context_today(self).year
        self.env["l10n_mx.fleet.emission.inspection"].sudo()._generate_inspections(
            year, vehicles.sudo()
        )

    def action_view_l10n_mx_emission_inspections(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "l10n_mx_fleet_emission.l10n_mx_fleet_emission_inspection_action"
        )
        action["domain"] = [("asset_id", "=", self.id)]
        action["context"] = {"default_asset_id": self.id}
        return action

    def _search_l10n_mx_emission_status(self, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented
        today = fields.Date.context_today(self)
        vehicles = self.with_context(active_test=False).search(
            [("l10n_mx_emission_calendar_id", "!=", False)]
        )
        matching = vehicles.filtered(
            lambda v: v._get_l10n_mx_emission_status(today) in value
        )
        return [("id", "in" if operator == "in" else "not in", matching.ids)]

    def _get_l10n_mx_emission_window(self, today) -> tuple[int, int] | None:
        self.check_singleton()
        calendar = self.l10n_mx_emission_calendar_id
        if not calendar:
            return None
        first, second = calendar._get_periods()
        return first if today.month <= 6 else second

    def _get_l10n_mx_emission_deadline(self, today) -> date | bool:
        window = self._get_l10n_mx_emission_window(today)
        if not window:
            return False
        end = window[1]
        return date(today.year, end, monthrange(today.year, end)[1])

    def _get_l10n_mx_emission_status(self, today) -> str | bool:
        # The year splits into two semesters, each with one window per color. The
        # inspection of the current semester decides passed or scheduled; otherwise
        # the status follows where today sits relative to the window.
        window = self._get_l10n_mx_emission_window(today)
        if not window:
            return False
        start, end = window
        period = "1" if today.month <= 6 else "2"
        inspection = self.l10n_mx_emission_inspection_ids.filtered(
            lambda i: i.year == today.year and i.period == period
        )[:1]
        if inspection.state == "done":
            return "passed"
        if inspection.state == "scheduled":
            return "scheduled"
        if today.month < start:
            return "upcoming"
        if today.month > end:
            return "overdue"
        return "due"
