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

    resource_ids = fields.Many2many(
        comodel_name="resource.resource",
        string="Resources",
        required=True,
    )
    leave_start_dt = fields.Datetime(
        string="Start Date",
        default=lambda self: self._default_time(0, 0),
        required=True,
    )
    leave_end_dt = fields.Datetime(
        string="End Date",
        default=lambda self: self._default_time(23, 59),
        required=True,
    )
    reason = fields.Char()

    def action_create_leave(self):
        self.env["resource.schedule.exception"].create(
            [
                {
                    "calendar_id": resource.calendar_id.id,
                    "date_from": wizard.leave_start_dt,
                    "date_to": wizard.leave_end_dt,
                    "name": wizard.reason,
                    "resource_id": resource.id,
                }
                for wizard in self
                for resource in wizard.resource_ids
            ]
        )
        return {"type": "ir.actions.act_window_close"}
