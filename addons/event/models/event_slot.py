from datetime import UTC, datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.libs.datetime import timezone
from odoo.tools import (
    format_date,
    format_datetime,
    format_time,
    formatLang,
)
from odoo.tools.date_utils import float_to_time


class EventSlot(models.Model):
    _name = "event.slot"
    _description = "Event Slot"
    _order = "event_id, date, start_hour, end_hour, id"

    event_id = fields.Many2one(
        comodel_name="event.event",
        index=True,
        required=True,
        ondelete="cascade",
    )
    color = fields.Integer(default=0)
    date = fields.Date(required=True)
    date_tz = fields.Selection(related="event_id.date_tz")
    start_hour = fields.Float(
        string="Starting Hour",
        required=True,
        help="Expressed in the event timezone.",
    )
    end_hour = fields.Float(
        string="Ending Hour",
        required=True,
        help="Expressed in the event timezone.",
    )
    start_datetime = fields.Datetime(
        compute="_compute_datetimes",
        store=True,
    )
    end_datetime = fields.Datetime(
        compute="_compute_datetimes",
        store=True,
    )

    # Registrations
    is_sold_out = fields.Boolean(
        string="Sold Out",
        compute="_compute_is_sold_out",
        help="Whether seats are sold out for this slot.",
    )
    registration_ids = fields.One2many(
        comodel_name="event.registration",
        inverse_name="event_slot_id",
        string="Attendees",
    )
    seats_available = fields.Integer(
        string="Available Seats",
        compute="_compute_seats",
        store=False,
        readonly=True,
    )
    seats_reserved = fields.Integer(
        string="Number of Registrations",
        compute="_compute_seats",
        store=False,
        readonly=True,
    )
    seats_taken = fields.Integer(
        string="Number of Taken Seats",
        compute="_compute_seats",
        store=False,
        readonly=True,
    )
    seats_used = fields.Integer(
        string="Number of Attendees",
        compute="_compute_seats",
        store=False,
        readonly=True,
    )

    @api.constrains("start_hour", "end_hour")
    def _check_hours(self):
        for slot in self:
            if not (0 <= slot.start_hour < 24 and 0 <= slot.end_hour < 24):
                raise ValidationError(_("A slot hour must be between 0:00 and 23:59."))
            if slot.end_hour <= slot.start_hour:
                raise ValidationError(
                    _(
                        "A slot end hour must be later than its start hour.\n%s",
                        slot.display_name,
                    )
                )

    def _is_within_event_range(self):
        """Whether this slot lies inside its event's own time range.

        Shared with ``event.event._check_slots_dates``: an ORM constraint only
        fires on the model whose fields changed, so moving a slot out of range
        and shrinking an event under a slot need two constraints -- but not two
        definitions of what "in range" means.
        """
        self.check_singleton()
        event_start = self.event_id.date_begin
        event_end = self.event_id.date_end
        if not (event_start and event_end):
            return True
        return (
            event_start <= self.start_datetime <= event_end
            and event_start <= self.end_datetime <= event_end
        )

    @api.constrains("date", "start_hour", "end_hour")
    def _check_time_range(self):
        for slot in self:
            if not slot._is_within_event_range():
                raise ValidationError(
                    _(
                        "A slot cannot be scheduled outside of its event time range.\n\n"
                        "Event:\t\t%(event_start)s - %(event_end)s\n"
                        "Slot:\t\t%(slot_name)s",
                        event_start=format_datetime(
                            self.env,
                            slot.event_id.date_begin,
                            tz=slot.date_tz,
                            dt_format="medium",
                        ),
                        event_end=format_datetime(
                            self.env,
                            slot.event_id.date_end,
                            tz=slot.date_tz,
                            dt_format="medium",
                        ),
                        slot_name=slot.display_name,
                    )
                )

    @api.depends("date", "date_tz", "start_hour", "end_hour")
    def _compute_datetimes(self):
        for slot in self:
            event_tz = timezone(slot.date_tz)
            start = datetime.combine(slot.date, float_to_time(slot.start_hour))
            end = datetime.combine(slot.date, float_to_time(slot.end_hour))
            slot.start_datetime = (
                start.replace(tzinfo=event_tz).astimezone(UTC).replace(tzinfo=None)
            )
            slot.end_datetime = (
                end.replace(tzinfo=event_tz).astimezone(UTC).replace(tzinfo=None)
            )

    @api.depends("seats_available")
    @api.depends_context("name_with_seats_availability")
    def _compute_display_name(self):
        """Adds slot seats availability if requested by context.
        Always display the name without availabilities if the event is multi slots
        because the availability displayed won't be relative to the possible ticket combinations
        but only relative to the event and this will confuse the user.
        """
        for slot in self:
            date = format_date(self.env, slot.date, date_format="medium")
            start = format_time(
                self.env, float_to_time(slot.start_hour), time_format="short"
            )
            end = format_time(
                self.env, float_to_time(slot.end_hour), time_format="short"
            )
            name = f"{date}, {start} - {end}"
            if (
                self.env.context.get("name_with_seats_availability")
                and slot.event_id.seats_limited
                and not slot.event_id.is_multi_slots
            ):
                name = (
                    _("%(slot_name)s (Sold out)", slot_name=name)
                    if not slot.seats_available
                    else _(
                        "%(slot_name)s (%(count)s seats remaining)",
                        slot_name=name,
                        count=formatLang(self.env, slot.seats_available, digits=0),
                    )
                )
            slot.display_name = name

    @api.depends("event_id.seats_limited", "seats_available")
    def _compute_is_sold_out(self):
        for slot in self:
            slot.is_sold_out = slot.event_id.seats_limited and not slot.seats_available

    @api.depends(
        "event_id",
        "event_id.seats_max",
        "registration_ids.state",
        "registration_ids.active",
    )
    def _compute_seats(self):
        base_vals = {"seats_reserved": 0, "seats_used": 0}
        results = self.env["event.registration"]._count_taken_seats_by(
            "event_slot_id", self.ids
        )
        for slot in self:
            slot.seats_available = 0
            slot.update(results.get(slot._origin.id or slot.id, base_vals))
            # seats_max is the per-slot cap on multi-slot events
            if slot.event_id.seats_max > 0:
                slot.seats_available = slot.event_id.seats_max - (
                    slot.seats_reserved + slot.seats_used
                )
            slot.seats_taken = slot.seats_reserved + slot.seats_used

    @api.ondelete(at_uninstall=False)
    def _unlink_except_if_registrations(self):
        blocking = self.filtered("registration_ids")
        if blocking:
            raise UserError(
                _(
                    "The following slots cannot be deleted while they have one or more registrations linked to them:\n- %s",
                    "\n- ".join(blocking.mapped("display_name")),
                )
            )
