import logging
import uuid
from datetime import datetime, timedelta

from markupsafe import Markup

from odoo import SUPERUSER_ID, _, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.libs.intervals import intervals_overlap
from odoo.tools.date_utils import localized
from odoo.tools.mail import (
    email_normalize,
    email_split_and_format_normalize,
    html_sanitize,
)

from odoo.addons.calendar.models.utils import interval_from_events

_logger = logging.getLogger(__name__)


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    booking_capacity_enforced = fields.Boolean(
        string="Enforce Booking Ceiling",
        default=False,
        copy=False,
        readonly=True,
        help="Public bookings retain their resource capacity constraint when edited or rescheduled.",
    )

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        # If the event has an apt type, set the event stop datetime to match the apt type duration
        if (
            res.get("appointment_type_id")
            and res.get("duration")
            and res.get("start")
            and "stop" in fields
        ):
            res["stop"] = res["start"] + timedelta(hours=res["duration"])
        if not self.env.context.get("booking_gantt_create_record", False):
            return res
        # Round the stop datetime to the nearest minute when coming from the gantt view
        if (
            res.get("stop")
            and isinstance(res["stop"], datetime)
            and res["stop"].second != 0
        ):
            res["stop"] = datetime.min + round(  # noqa: DTZ901  naive epoch, fields are naive UTC
                (res["stop"] - datetime.min) / timedelta(minutes=1)  # noqa: DTZ901  same
            ) * timedelta(minutes=1)
        user_id = res.get("user_id")
        resource_ids = (
            self.env["calendar.event"]
            ._fields["resource_ids"]
            .convert_to_cache(res.get("resource_ids", []), self.env["calendar.event"])
        )
        resources = self.env["resource.resource"].browse(resource_ids)
        # get a relevant appointment type for ease of use when coming from a view that groups by resource
        if not res.get("appointment_type_id") and "appointment_type_id" in fields:
            appointment_types = False
            if resources:
                appointment_types = resources.appointment_type_ids
            elif user_id:
                appointment_types = self.env["appointment.type"].search(
                    [("staff_user_ids", "in", user_id)]
                )
            if appointment_types:
                res["appointment_type_id"] = appointment_types[0].id

        if appointment_type_id := res.get("appointment_type_id"):
            appointment_type = self.env["appointment.type"].browse(appointment_type_id)
            if "name" in fields:
                res.setdefault("name", appointment_type.name)
            # set the maximum capacity if managing capacities
            if "total_capacity_reserved" in fields:
                if appointment_type.schedule_based_on == "resources" and resources:
                    res.setdefault(
                        "total_capacity_reserved",
                        sum(resource.capacity for resource in resources)
                        if appointment_type.manage_capacity
                        else len(resources),
                    )
                elif appointment_type.schedule_based_on == "users":
                    res.setdefault(
                        "total_capacity_reserved",
                        (
                            appointment_type.manage_capacity
                            and appointment_type.user_capacity
                        )
                        or 1,
                    )

        if self.env.context.get("appointment_default_assign_user_attendees"):
            default_partner_ids = self.env.context.get("default_partner_ids", [])
            # If there is only one attendee -> set him as organizer of the calendar event
            # Mostly used when you click on a specific slot in the appointment kanban
            if len(default_partner_ids) == 1 and "user_id" in fields:
                attendee_user = (
                    self.env["res.partner"].browse(default_partner_ids).user_ids
                )
                if attendee_user:
                    res["user_id"] = attendee_user[0].id
            # Special gantt case: we want to assign the current user to the attendees if he's set as organizer
            elif (
                res.get("user_id")
                and res.get("partner_ids", Command.set([])) == [Command.set([])]
                and res["user_id"] == self.env.uid
                and "partner_ids" in fields
            ):
                res["partner_ids"] = [Command.set(self.env.user.partner_id.ids)]
        return res

    name = fields.Char(
        compute="_compute_name",
        store=True,
        readonly=False,
    )
    booking_access_token = fields.Char(
        string="Booking Management Token",
        default=lambda self: str(uuid.uuid4()),
        index=True,
        copy=False,
        readonly=True,
        groups="base.group_system",
        help="Authorize managing a booking. Conference URLs never contain this token.",
    )
    _booking_access_token_unique = models.Constraint(
        "UNIQUE(booking_access_token)", "Booking management credentials must be unique."
    )
    alarm_ids = fields.Many2many(
        compute="_compute_alarm_ids",
        store=True,
        readonly=False,
    )

    appointment_response_ids = fields.One2many(
        comodel_name="survey.user_input",
        inverse_name="calendar_event_id",
        copy=False,
    )
    appointment_answer_input_ids = fields.One2many(
        comodel_name="survey.user_input.line",
        inverse_name="calendar_event_id",
        string="Appointment Answers",
    )
    appointment_status = fields.Selection(
        selection=[
            ("request", "Request"),
            ("booked", "Booked"),
            ("attended", "Checked-In"),
            ("no_show", "No Show"),
            ("cancelled", "Cancelled"),
        ],
        compute="_compute_appointment_status",
        store=True,
        readonly=False,
        tracking=True,
    )
    appointment_type_id = fields.Many2one(
        comodel_name="appointment.type",
        string="Appointment",
        index="btree_not_null",
        tracking=True,
    )
    appointment_type_schedule_based_on = fields.Selection(
        related="appointment_type_id.schedule_based_on"
    )
    appointment_type_manage_capacity = fields.Boolean(
        related="appointment_type_id.manage_capacity"
    )
    appointment_invite_id = fields.Many2one(
        comodel_name="appointment.invite",
        string="Appointment Invitation",
        index="btree_not_null",
        readonly=True,
        ondelete="set null",
    )
    # The booking-line table is the truth, and `booked_resource_ids` reads it so a
    # search or a group-by can reach it. `resource_ids` is what a writer uses: writing
    # the relation table directly would insert a line with no capacity_reserved.
    booked_resource_ids = fields.Many2many(
        comodel_name="resource.resource",
        relation="appointment_booking_line",
        column1="calendar_event_id",
        column2="resource_id",
        string="Booked Resources",
        depends=["booking_line_ids"],
        copy=False,
        readonly=True,
        group_expand="_read_group_resource_ids",
    )
    resource_ids = fields.Many2many(
        comodel_name="resource.resource",
        string="Resources",
        compute="_compute_resource_ids",
        inverse="_inverse_resource_ids_or_capacity",
        search="_search_resource_ids",
        copy=False,
        group_expand="_read_group_resource_ids",
        group_by_field="booked_resource_ids",
    )
    booking_line_ids = fields.One2many(
        comodel_name="appointment.booking.line",
        inverse_name="calendar_event_id",
        string="Booking Lines",
        copy=True,
    )
    partner_ids = fields.Many2many(
        comodel_name="res.partner",
        group_expand="_read_group_partner_ids",
    )
    total_capacity_reserved = fields.Integer(
        compute="_compute_total_capacity",
        inverse="_inverse_resource_ids_or_capacity",
    )
    total_capacity_used = fields.Integer(compute="_compute_total_capacity")
    user_id = fields.Many2one(
        comodel_name="res.users",
        group_expand="_read_group_user_id",
    )
    videocall_redirection = fields.Char(
        string="Meeting redirection URL",
        compute="_compute_videocall_redirection",
    )
    appointment_booker_id = fields.Many2one(
        comodel_name="res.partner",
        string="Person who is booking the appointment",
        index="btree_not_null",
    )
    unavailable_resource_ids = fields.Many2many(
        comodel_name="resource.resource",
        string="Resources intersecting with leave time",
        compute="_compute_unavailable_resource_ids",
    )

    @api.constrains("booked_resource_ids", "appointment_type_id")
    def _check_resource_and_appointment_type(self):
        for event in self:
            if event.booked_resource_ids and not event.appointment_type_id:
                raise ValidationError(
                    _(
                        "The event %s cannot book resources without an appointment type.",
                        event.name,
                    )
                )

    @api.constrains("appointment_type_id", "appointment_status")
    def _check_status_and_appointment_type(self):
        for event in self:
            if event.appointment_status and not event.appointment_type_id:
                raise ValidationError(
                    _(
                        "The event %s cannot have an appointment status without being linked to an appointment type.",
                        event.name,
                    )
                )

    def _get_organizer_validation_conditions(self, vals_list):
        res = super()._get_organizer_validation_conditions(vals_list)
        appointment_type_ids = list(
            {
                vals["appointment_type_id"]
                for vals in vals_list
                if vals.get("appointment_type_id")
            }
        )

        if appointment_type_ids:
            appointment_type_ids = self.env["appointment.type"].browse(
                appointment_type_ids
            )
            resource_appointment_type_ids = set(
                appointment_type_ids.filtered(
                    lambda apt: apt.schedule_based_on == "resources"
                ).ids
            )

            # Combine with super() instead of replacing it: another override in the
            # MRO may contribute a False, and returning a freshly built list would
            # silently drop it. Harmless with today's base implementation
            # (`[True] * len(vals_list)`), but only by accident.
            return [
                previous
                and vals.get("appointment_type_id") not in resource_appointment_type_ids
                for previous, vals in zip(res, vals_list, strict=True)
            ]

        return res

    @api.depends("appointment_type_id")
    def _compute_alarm_ids(self):
        for event in self.filtered("appointment_type_id"):
            if not event.alarm_ids:
                event.alarm_ids = event.appointment_type_id.reminder_ids

    @api.depends("appointment_type_id")
    def _compute_appointment_status(self):
        for event in self:
            if not event.appointment_type_id:
                event.appointment_status = False
            elif not event.appointment_status:
                event.appointment_status = "booked"

    @api.depends("partner_ids")
    def _compute_name(self):
        for event in self.filtered(lambda e: e.appointment_type_id and not e.name):
            non_staff_attendees = event.partner_ids.filtered(
                lambda p: (
                    p._origin.id
                    not in event.appointment_type_id.staff_user_ids.partner_id.ids  # noqa: B023  (consumed by filtered() in the same iteration)
                )
            )
            if len(non_staff_attendees) == 1:
                event.name = (
                    non_staff_attendees.name + " - " + event.appointment_type_id.name
                )

    @api.depends("booking_line_ids", "booking_line_ids.resource_id")
    def _compute_resource_ids(self):
        for event in self:
            event.resource_ids = event.booking_line_ids.resource_id

    @api.depends("start", "stop", "resource_ids")
    def _compute_unavailable_resource_ids(self):
        self.unavailable_resource_ids = False
        resource_events = self.filtered(lambda event: event.resource_ids)
        if not resource_events:
            return

        for start, stop, events in interval_from_events(resource_events):
            group_resources = events.resource_ids
            availabilities_values = self.env[
                "appointment.type"
            ]._slot_availability_prepare_resources_values(group_resources, start, stop)
            resource_unavailabilities = availabilities_values[
                "resource_unavailabilities"
            ]
            resource_to_bookings = availabilities_values["resource_to_bookings"]

            events_to_check = self.env["calendar.event"]
            for resource, bookings in resource_to_bookings.items():
                booking_events = bookings.calendar_event_id
                events_manage_capacity = booking_events.mapped(
                    "appointment_type_manage_capacity"
                )
                isAllCapacityTrue = all(events_manage_capacity)
                isAllCapacityFalse = not any(events_manage_capacity)
                # Add events of the bookings to check if:
                # - There are event appointments with manage capacity True and False
                # - Manage capacity is all True and the resource is exclusive or capacity used >= resource capacity
                # - Manage capacity is all False and more than one appointment type or number of bookings > max_bookings
                if (
                    (not isAllCapacityTrue and not isAllCapacityFalse)
                    or (
                        isAllCapacityTrue
                        and (
                            sum(bookings.mapped("capacity_used")) >= resource.capacity
                            or resource.booking_exclusive
                        )
                    )
                    or (
                        isAllCapacityFalse
                        and (
                            len(bookings.appointment_type_id) > 1
                            or len(bookings) > bookings.appointment_type_id.max_bookings
                        )
                    )
                ):
                    events_to_check |= booking_events
            for event in events:
                event_resources = event.resource_ids
                event_interval = (localized(event.start), localized(event.stop))
                event.unavailable_resource_ids = event_resources.filtered(
                    lambda resource: any(
                        intervals_overlap(
                            tuple(map(localized, interval)),
                            event_interval,  # noqa: B023  (consumed by filtered() in the same iteration)
                        )
                        for interval in resource_unavailabilities.get(resource, [])  # noqa: B023  same
                    )
                )
                for conflicting_event in events_to_check - event._origin:
                    if (
                        resources := event_resources._origin
                        & conflicting_event.resource_ids
                    ) and intervals_overlap(
                        event_interval,
                        (
                            localized(conflicting_event.start),
                            localized(conflicting_event.stop),
                        ),
                    ):
                        event.unavailable_resource_ids += resources

    @api.depends("booking_line_ids")
    def _compute_total_capacity(self):
        booking_data = self.env["appointment.booking.line"]._read_group(
            [("calendar_event_id", "in", self.ids)],
            ["calendar_event_id"],
            ["capacity_reserved:sum", "capacity_used:sum"],
        )
        mapped_data = {
            meeting.id: {
                "total_capacity_reserved": total_capacity_reserved,
                "total_capacity_used": total_capacity_used,
            }
            for meeting, total_capacity_reserved, total_capacity_used in booking_data
        }

        for event in self:
            data = mapped_data.get(event.id)
            event.total_capacity_reserved = (
                data.get("total_capacity_reserved", 0) if data else 0
            )
            event.total_capacity_used = (
                data.get("total_capacity_used", 0) if data else 0
            )

    @api.depends("videocall_location", "access_token")
    def _compute_videocall_redirection(self):
        for event in self:
            if not event.videocall_location:
                event.videocall_redirection = False
                continue
            if not event.access_token:
                # Mint the token through the model's own helper rather than
                # assigning here. This compute is non-stored and depends on
                # `access_token`, so a write made inside it is discarded: the
                # column stayed NULL and the URL below pointed at a token that
                # did not exist, giving a permanently dead videocall link.
                event._update_access_token()
            event.videocall_redirection = (
                f"{event.get_base_url()}/calendar/videocall/{event.access_token}"
            )

    @api.depends("appointment_type_id.event_videocall_source")
    def _compute_videocall_source(self):
        events_no_appointment = self.env["calendar.event"]
        for event in self:
            if not event.appointment_type_id or (
                event.videocall_location
                and self.DISCUSS_ROUTE not in event.videocall_location
            ):
                events_no_appointment |= event
                continue
            event.videocall_source = (
                event.sudo().appointment_type_id.event_videocall_source
            )
        super(CalendarEvent, events_no_appointment)._compute_videocall_source()

    def _compute_is_highlighted(self):
        super()._compute_is_highlighted()
        if self.env.context.get("active_model") == "appointment.type":
            appointment_type_id = self.env.context.get("active_id")
            for event in self:
                if event.appointment_type_id.id == appointment_type_id:
                    event.is_highlighted = True

    def get_base_url(self):
        if self.appointment_type_id:
            return self.appointment_type_id.sudo().get_base_url()
        return super().get_base_url()

    def _get_scheduled_partners(self):
        # Equipment customers receive invitations as booking stakeholders. They
        # may reserve several resources concurrently, including on others' behalf.
        # Only staff appointments and ordinary meetings reserve personal time.
        if self.appointment_type_id.schedule_based_on == "resources":
            return self.env["res.partner"]
        return super()._get_scheduled_partners()

    def _prepare_reservation_vals_list(self):
        vals_list = super()._prepare_reservation_vals_list()
        if not self.start or not self.stop or self.show_as != "busy":
            return vals_list
        by_resource = {vals["resource_id"]: vals for vals in vals_list}
        if self.appointment_type_id.schedule_based_on == "users":
            resource = self.user_id._get_calendar_event_resource()
            declined = self.attendee_ids.filtered(
                lambda attendee: (
                    attendee.partner_id == self.user_id.partner_id
                    and attendee.state == "declined"
                )
            )
            if (
                resource
                and not declined
                and resource.id not in by_resource
                and self.booking_line_ids
            ):
                start, stop = self._get_reservation_interval(
                    self.user_id.tz or resource.tz
                )
                values = {
                    "name": self.display_name,
                    "date_start": start,
                    "date_end": stop,
                    "resource_id": resource.id,
                    "enforcement_mode": "soft",
                }
                vals_list.append(values)
                by_resource[resource.id] = values
            if resource.id in by_resource:
                capacity = (
                    self.appointment_type_id.user_capacity
                    if self.appointment_type_id.manage_capacity
                    else self.appointment_type_id.max_bookings
                )
                by_resource[resource.id]["allocated_percentage"] = (
                    sum(self.booking_line_ids.mapped("capacity_used"))
                    / max(capacity, 1)
                    * 100.0
                )
        shares = {}
        for line in self.booking_line_ids:
            resource = line.resource_id
            if not resource or line.capacity_used <= 0:
                continue
            capacity = (
                resource.capacity
                if line.appointment_type_id.manage_capacity
                else line.appointment_type_id.max_bookings
            )
            shares[resource] = (
                shares.get(resource, 0.0)
                + line.capacity_used / max(capacity, 1) * 100.0
            )
        for resource, share in shares.items():
            start, stop = self._get_reservation_interval(resource.tz)
            if resource.id in by_resource:
                by_resource[resource.id]["allocated_percentage"] = max(
                    share, by_resource[resource.id]["allocated_percentage"]
                )
                continue
            vals_list.append(
                {
                    "name": self.display_name,
                    "date_start": start,
                    "date_end": stop,
                    "resource_id": resource.id,
                    "allocated_percentage": share,
                    "enforcement_mode": "soft",
                }
            )
        if self.booking_capacity_enforced:
            for values in vals_list:
                values["enforcement_mode"] = "hard"
        return vals_list

    def _get_fields_sync_trigger(self):
        return super()._get_fields_sync_trigger() | {
            "booking_line_ids",
            "booking_capacity_enforced",
            "appointment_type_id",
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("appointment_type_id"):
                if (
                    "active" not in vals
                    and vals.get("appointment_status") == "cancelled"
                ):
                    vals["active"] = False
                elif "appointment_status" not in vals and vals.get("active") is False:
                    vals["appointment_status"] = "cancelled"
        return super().create(vals_list)

    def write(self, vals):
        unconfirmed_bookings = self.filtered(
            lambda event: (
                event.appointment_type_id and event.appointment_status != "booked"
            )
        )
        if any(event.appointment_type_id for event in self) or vals.get(
            "appointment_type_id"
        ):
            if "active" in vals and "appointment_status" not in vals:
                vals["appointment_status"] = "booked" if vals["active"] else "cancelled"
            if "active" not in vals and "appointment_status" in vals:
                vals["active"] = vals["appointment_status"] != "cancelled"

        res = super().write(vals)

        confirmed_bookings = unconfirmed_bookings.filtered(
            lambda event: event.appointment_status == "booked"
        )
        if confirmed_bookings:
            confirmed_bookings.attendee_ids._send_invitation_emails()

        return res

    def _is_partner_unavailable(self, partner, partner_events):
        self.check_singleton()
        appointment = self.appointment_type_id
        if (
            partner in appointment.staff_user_ids.partner_id
            and not partner_events.filtered(
                lambda event: event.appointment_type_id != appointment
            )
        ):
            max_capacity = (
                appointment.user_capacity
                if appointment.manage_capacity
                else appointment.max_bookings
            )
            return sum(partner_events.mapped("total_capacity_used")) > max_capacity

        return super()._is_partner_unavailable(partner, partner_events)

    def _init_column(self, column_name, *, new_column=False):
        """Initialize the value of the given column for existing rows."""
        # access_token is skipped: generating unique tokens for potentially tons of existing
        # events is wasteful, they are generated on the fly when needed.
        if column_name != "access_token":
            super()._init_column(column_name, new_column=new_column)

    def _inverse_resource_ids_or_capacity(self):
        """Update booking lines as inverse of both resource capacity and resource_ids."""
        # Both values are stored on the booking line and the resource capacity depends on the
        # resources existing in the first place, so they share a single inverse to avoid any
        # ordering conflict.
        booking_lines = []
        booking_lines_to_delete = self.env["appointment.booking.line"]
        for event in self:
            if event.appointment_type_schedule_based_on == "resources":
                resources = event.resource_ids
                if (
                    event.appointment_type_manage_capacity
                    and event.total_capacity_reserved
                ):
                    capacity_to_reserve = event.total_capacity_reserved
                elif event.appointment_type_manage_capacity:
                    capacity_to_reserve = sum(
                        event.booking_line_ids.mapped("capacity_reserved")
                    ) or sum(resources.mapped("capacity"))
                else:
                    capacity_to_reserve = len(event.resource_ids)
                booking_lines_to_delete |= event.booking_line_ids
                for resource in resources.sorted("booking_exclusive", reverse=True):
                    if (
                        event.appointment_type_manage_capacity
                        and capacity_to_reserve <= 0
                    ):
                        break
                    resource_capacity_used = (
                        min(resource.capacity, capacity_to_reserve)
                        if event.appointment_type_manage_capacity
                        else 1
                    )
                    booking_lines.append(
                        {
                            "resource_id": resource.id,
                            "calendar_event_id": event.id,
                            "capacity_reserved": resource_capacity_used,
                        }
                    )
                    capacity_to_reserve -= resource_capacity_used
                    capacity_to_reserve = max(0, capacity_to_reserve)
                if event.appointment_type_manage_capacity and capacity_to_reserve:
                    raise UserError(
                        _(
                            "%(capacity)d seats are missing to be able to book the %(appointment_name)s: %(event_name)s (%(event_id)s)",
                            capacity=capacity_to_reserve,
                            appointment_name=event.appointment_type_id.name,
                            event_name=event.name,
                            event_id=repr(event.id),
                        )
                    )
            elif event.appointment_type_schedule_based_on == "users":
                max_user_capacity = (
                    event.appointment_type_manage_capacity
                    and event.appointment_type_id.user_capacity
                ) or 1
                if (
                    event.appointment_type_manage_capacity
                    and event.total_capacity_reserved
                ):
                    capacity_to_reserve = event.total_capacity_reserved
                else:
                    capacity_to_reserve = max_user_capacity
                if (
                    event.appointment_type_manage_capacity
                    and max_user_capacity < capacity_to_reserve
                ):
                    raise UserError(
                        _(
                            "%(capacity)d seats are missing to be able to book the %(appointment_name)s: %(event_name)s (%(event_id)s)",
                            capacity=capacity_to_reserve
                            - event.appointment_type_id.user_capacity,
                            appointment_name=event.appointment_type_id.name,
                            event_name=event.display_name,
                            event_id=repr(event.id),
                        )
                    )
                booking_lines_to_delete += event.booking_line_ids
                booking_lines.append(
                    {
                        "calendar_event_id": event.id,
                        "capacity_reserved": capacity_to_reserve,
                    }
                )
        booking_lines_to_delete.unlink()
        self.env["appointment.booking.line"].sudo().create(booking_lines)

    def _search_resource_ids(self, operator, value):
        return [("booked_resource_ids", operator, value)]

    def _read_group_resource_ids(self, resources, domain):
        if not self.env.context.get("appointment_booking_gantt_show_all_resources"):
            return resources
        resources_domain = [
            ("appointment_type_ids", "!=", False),
            "|",
            ("company_id", "=", False),
            ("company_id", "in", self.env.context.get("allowed_company_ids", [])),
        ]
        # If we have a default appointment type, we only want to show those resources
        default_appointment_type = self.env.context.get("default_appointment_type_id")
        if default_appointment_type:
            return (
                self.env["appointment.type"]
                .browse(default_appointment_type)
                .resource_ids.filtered_domain(resources_domain)
            )
        return self.env["resource.resource"].search(resources_domain)

    def _read_group_partner_ids(self, partners, domain):
        """Show the partners associated with relevant staff users in appointment gantt context."""
        if not self.env.context.get("appointment_booking_gantt_show_all_resources"):
            return partners
        appointment_type_id = self.env.context.get("default_appointment_type_id", False)
        appointment_types = self.env["appointment.type"].browse(appointment_type_id)
        if appointment_types:
            return appointment_types.staff_user_ids.partner_id
        return (
            self.env["appointment.type"]
            .search([("schedule_based_on", "=", "users")])
            .staff_user_ids.partner_id
        )

    def _read_group_user_id(self, users, domain):
        if not self.env.context.get("appointment_booking_gantt_show_all_resources"):
            return users
        appointment_types = self.env["appointment.type"].browse(
            self.env.context.get("default_appointment_type_id", [])
        )
        if appointment_types:
            return appointment_types.staff_user_ids
        return (
            self.env["appointment.type"]
            .search([("schedule_based_on", "=", "users")])
            .staff_user_ids
        )

    def _track_filtered_for_display(self, tracking_values):
        if self.appointment_type_id:
            return tracking_values.filtered(lambda t: t.field_id.name != "active")
        return super()._track_filtered_for_display(tracking_values)

    def _track_get_default_log_message(self, tracked_fields):
        if self.appointment_type_id and "active" in tracked_fields:
            if self.active:
                return _("Appointment re-booked")
            else:
                return _("Appointment cancelled")
        return super()._track_get_default_log_message(tracked_fields)

    def action_cancel_meeting(self, partner_ids):
        """Archive the meeting, logging which attendees requested the cancellation.

        :param list partner_ids: ids of the partners who requested the cancellation
        """
        self.check_singleton()
        message_body = _("Appointment cancelled")
        if partner_ids:
            attendees = self.env["calendar.attendee"].search(
                [("event_id", "=", self.id), ("partner_id", "in", partner_ids)]
            )
            if attendees:
                cancelling_attendees = ", ".join(
                    [attendee.display_name for attendee in attendees]
                )
                message_body = _(
                    "Appointment cancelled by: %(partners)s",
                    partners=cancelling_attendees,
                )
        self._track_set_log_message(message_body)
        # Use the organizer if set or fallback on SUPERUSER to notify attendees that the event is archived
        self.with_user(self.user_id or SUPERUSER_ID).sudo().action_archive()

    def action_set_appointment_attended(self):
        self.check_singleton()
        self.appointment_status = "attended"

    def action_set_appointment_booked(self):
        self.check_singleton()
        self.appointment_status = "booked"

    def action_set_appointment_cancelled(self):
        self.check_singleton()
        self.appointment_status = "cancelled"

    def action_set_appointment_no_show(self):
        self.check_singleton()
        self.appointment_status = "no_show"

    def _get_or_create_partners(self, guest_emails_str, limit=None):
        """Used to find the partners from the emails strings and creates partners if not found.

        :param str guest_emails_str: line-separated guest emails. It will
          fetch or create partners to add them as event attendees;
        :return: the fetched or created partners
        :rtype: <res.partner>
        """
        # Split and normalize guest emails
        formatted_emails = email_split_and_format_normalize(guest_emails_str)
        valid_normalized = list(
            tools.misc.unique(
                email_normalize(email_input, strict=False)
                for email_input in formatted_emails
            )
        )
        if not valid_normalized:
            return self.env["res.partner"]
        # Cap the guest count when the caller asks for it. This used to key on
        # `self.env.su` as a proxy for "came from the public web form", which bound
        # every sudo caller - crons, server actions, bridge modules - and bound no
        # ordinary internal user. The two public controllers pass the limit
        # explicitly instead.
        if limit and len(valid_normalized) > limit:
            raise UserError(
                _(
                    "Guest usage is limited to %(limit)s customers for performance reason.",
                    limit=limit,
                )
            )

        # Find or create existing partners
        return self.env["mixin.mail.thread"]._partner_get_or_create_from_emails_single(
            formatted_emails
        )

    def _get_mail_tz(self):
        self.check_singleton()
        if not self.event_tz and self.appointment_type_id.appointment_tz:
            return self.appointment_type_id.appointment_tz
        return super()._get_mail_tz()

    def _get_fields_public(self):
        return super()._get_fields_public() | {
            "appointment_type_id",
            "booked_resource_ids",
            "resource_ids",
            "total_capacity_reserved",
            "total_capacity_used",
        }

    def _track_template(self, changes):
        res = super()._track_template(changes)
        if not self.appointment_type_id or self._skip_send_mail_status_update():
            return res

        appointment_type_sudo = self.appointment_type_id.sudo()
        # set 'author_id' and 'email_from' based on the organizer
        vals = (
            {
                "author_id": self.user_id.partner_id.id,
                "email_from": self.user_id.email_formatted,
            }
            if self.user_id
            else {}
        )

        if "appointment_type_id" in changes and (
            self.appointment_status in {"booked", "request"}
        ):
            try:
                booked_template = self.env.ref(
                    "calendar.appointment_booked_mail_template"
                )
            except ValueError as e:
                _logger.warning(
                    "Mail could not be sent, as mail template is not found : %s", e
                )
            else:
                res["appointment_type_id"] = (
                    booked_template.sudo(),
                    {
                        **vals,
                        "auto_delete_keep_log": False,
                        "subtype_id": self.env["ir.model.data"]._xmlid_to_res_id(
                            "calendar.mt_calendar_event_booked"
                        ),
                        "email_layout_xmlid": "mail.mail_notification_light",
                        "partner_ids": [],  # notify followers of the subtype only, not default recipients
                    },
                )
        if (
            "active" in changes
            and not self.active
            and self.start > fields.Datetime.now()
            and appointment_type_sudo.canceled_mail_template_id
        ):
            res["active"] = (
                appointment_type_sudo.canceled_mail_template_id,
                {
                    **vals,
                    "auto_delete_keep_log": False,
                    "subtype_id": self.env["ir.model.data"]._xmlid_to_res_id(
                        "calendar.mt_calendar_event_canceled"
                    ),
                    "email_layout_xmlid": "mail.mail_notification_light",
                    "notify_author": True,
                },
            )
        return res

    @api.model
    def _get_activity_excluded_models(self):
        return super()._get_activity_excluded_models() + ["appointment.type"]

    def _get_customer_summary(self):
        # Summary should make sense for the person who booked the meeting
        if (
            self.appointment_type_id
            and self.appointment_type_id.schedule_based_on == "users"
            and self.partner_id
        ):
            return _(
                "%(appointment_name)s with %(partner_name)s",
                appointment_name=self.appointment_type_id.name,
                partner_name=self.partner_id.name or _("somebody"),
            )
        return super()._get_customer_summary()

    def _get_domain_default_privacy(self):
        """Extend the privacy domain to include every event related to a resource appointment type.

        :rtype: Domain
        """
        # Resource related events must stay visible and accessible from the gantt view whatever
        # their privacy: privacy derives from the user settings, and resource events aren't
        # typically linked to any user, so their visibility shouldn't depend on it.
        #
        # `any!`, not a dotted path: this domain is visibility policy that
        # `_search` injects into every search touching a non-public field, so it
        # must not be evaluated under the caller's rights on `appointment.type`.
        # Through `any` the subselect checked them, and a portal user -- who may
        # read their own appointments but not appointment types -- could not
        # count or list calendar events at all.
        return super()._get_domain_default_privacy() | Domain(
            "appointment_type_id",
            "any!",
            Domain("schedule_based_on", "=", "resources"),
        )

    def _get_customer_description(self):
        """Return shareable event details without embedding management credentials."""
        if not self.appointment_type_id:
            return super()._get_customer_description()
        confirmation = html_sanitize(
            self.appointment_type_id.sudo().message_confirmation or ""
        )
        return Markup("<br>").join([self.description or "", confirmation])
