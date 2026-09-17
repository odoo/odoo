from odoo import api, models


class AppointmentBookingLine(models.Model):
    _inherit = "appointment.booking.line"

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._notify_room_kiosks("create")
        return lines

    def write(self, vals):
        if "resource_id" not in vals:
            return super().write(vals)
        self._notify_room_kiosks("delete")
        res = super().write(vals)
        self._notify_room_kiosks("create")
        return res

    def unlink(self):
        self._notify_room_kiosks("delete")
        return super().unlink()

    def _notify_room_kiosks(self, method):
        for line in self.sudo().filtered("resource_id.access_token"):
            line.resource_id._notify_booking_view(method, line.calendar_event_id)
