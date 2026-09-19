from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AppointmentBookingLine(models.Model):
    _name = "appointment.booking.line"
    _rec_name = "calendar_event_id"
    _description = "Appointment Booking Line"
    _order = "event_start desc, id desc"

    active = fields.Boolean(related="calendar_event_id.active")
    resource_id = fields.Many2one(
        comodel_name="resource.resource",
        string="Resource",
        ondelete="cascade",
    )
    appointment_user_id = fields.Many2one(
        comodel_name="res.users",
        related="calendar_event_id.user_id",
        string="Appointment User",
        readonly=False,
    )
    appointment_type_id = fields.Many2one(
        comodel_name="appointment.type",
        related="calendar_event_id.appointment_type_id",
        readonly=True,
        ondelete="cascade",
    )
    capacity_reserved = fields.Integer(
        default=1,
        required=True,
        help="Capacity reserved by the user",
    )
    capacity_used = fields.Integer(
        compute="_compute_capacity_used",
        precompute=True,
        store=True,
        readonly=True,
        help="Capacity that will be used based on the capacity and user/resource selected",
    )
    calendar_event_id = fields.Many2one(
        comodel_name="calendar.event",
        string="Booking",
        index=True,
        required=True,
        ondelete="cascade",
    )
    event_start = fields.Datetime(
        related="calendar_event_id.start",
        string="Booking Start",
        readonly=True,
    )
    event_stop = fields.Datetime(
        related="calendar_event_id.stop",
        string="Booking End",
        readonly=True,
    )

    _check_capacity_reserved = models.Constraint(
        "CHECK(capacity_reserved >= 0)",
        "The capacity reserved should be positive.",
    )

    @api.constrains(
        "resource_id", "appointment_type_id", "appointment_user_id"
    )
    def _check_user_or_resource_set(self):
        for line in self:
            if (
                line.appointment_type_id.schedule_based_on == "users"
                and not line.appointment_user_id
            ) or (
                line.appointment_type_id.schedule_based_on == "resources"
                and not line.resource_id
            ):
                raise ValidationError(
                    _("Booking line must have a user or resource set.")
                )

    @api.constrains(
        "resource_id", "appointment_type_id", "appointment_user_id"
    )
    def _check_user_or_resource_match_appointment_type(self):
        """Check appointment user/resource linked to the lines is indeed usable through the appointment type."""
        for appointment_type, lines in self.grouped("appointment_type_id").items():
            if appointment_type.schedule_based_on == "users":
                non_compatible_users_and_resource = self.env["res.users"]
                for user in lines.appointment_user_id:
                    if not appointment_type.with_user(user).has_access("read"):
                        non_compatible_users_and_resource += user
            else:
                non_compatible_users_and_resource = (
                    lines.resource_id - appointment_type.resource_ids
                )

            if non_compatible_users_and_resource:
                raise ValidationError(
                    _(
                        '"%(name_list)s" cannot be used for "%(appointment_type_name)s"',
                        appointment_type_name=appointment_type.name,
                        name_list=", ".join(
                            non_compatible_users_and_resource.mapped("name")
                        ),
                    )
                )

    @api.depends(
        "resource_id.capacity",
        "resource_id.booking_exclusive",
        "appointment_type_id.manage_capacity",
        "capacity_reserved",
        "calendar_event_id.show_as",
        "calendar_event_id.attendee_ids.state",
        "calendar_event_id.attendee_ids.partner_id",
        "appointment_user_id",
    )
    def _compute_capacity_used(self):
        self.capacity_used = 0
        for line in self:
            declined = (
                line.appointment_type_id.schedule_based_on == "users"
                and line.calendar_event_id.attendee_ids.filtered(
                    lambda attendee, line=line: (
                        attendee.partner_id == line.appointment_user_id.partner_id
                        and attendee.state == "declined"
                    )
                )
            )
            if (
                line.capacity_reserved == 0
                or line.calendar_event_id.show_as == "free"
                or declined
            ):
                line.capacity_used = 0
            elif not line.appointment_type_id.manage_capacity:
                line.capacity_used = 1
            elif (
                line.appointment_type_id.schedule_based_on == "resources"
                and line.resource_id.booking_exclusive
            ):
                line.capacity_used = line.resource_id.capacity
            else:
                line.capacity_used = line.capacity_reserved

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines.calendar_event_id._sync_reservations()
        return lines

    def write(self, vals):
        events_before = self.calendar_event_id
        res = super().write(vals)
        (events_before | self.calendar_event_id)._sync_reservations()
        return res

    def unlink(self):
        events = self.calendar_event_id
        res = super().unlink()
        events.exists()._sync_reservations()
        return res
