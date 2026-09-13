from datetime import UTC

from odoo import fields, models
from odoo.libs.datetime import timezone


class AppointmentManageLeaves(models.TransientModel):
    _name = "appointment.manage.leaves"
    _description = "Add or remove leaves from appointments"

    def _default_time(self, hour, minute):
        user_timezone = timezone(
            self.env.user.tz or self.env.context.get("tz") or "UTC"
        )
        user_time = (
            fields.Datetime.today()
            .replace(hour=hour, minute=minute)
            .replace(tzinfo=user_timezone)
        )
        return user_time.astimezone(UTC).replace(tzinfo=None)

    appointment_resource_ids = fields.Many2many(
        "appointment.resource", string="Resources", required=True
    )
    leave_start_dt = fields.Datetime(
        "Start Date", required=True, default=lambda self: self._default_time(0, 0)
    )
    leave_end_dt = fields.Datetime(
        "End Date", required=True, default=lambda self: self._default_time(23, 59)
    )
    reason = fields.Char()

    def action_create_leave(self):
        self.env["resource.calendar.leaves"].create(
            [
                {
                    "calendar_id": resource.resource_calendar_id.id,
                    "date_from": wizard.leave_start_dt,
                    "date_to": wizard.leave_end_dt,
                    "name": wizard.reason,
                    "resource_id": resource.resource_id.id,
                }
                for wizard in self
                for resource in wizard.appointment_resource_ids
            ]
        )
        return {"type": "ir.actions.act_window_close"}
