# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AppointmentResource(models.Model):
    _inherit = "appointment.resource"

    def write(self, vals):
        result = super().write(vals)

        slots_altering_values = {
            'active',
            'capacity',
            'resource_calendar_id',
            'linked_resource_ids',
        }
        if slots_altering_values & vals.keys():
            google_appointments = self.appointment_type_ids.filtered('google_reserve_enable')
            google_appointments.google_reserve_pending_sync = True

        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_mark_pending_sync(self):
        self.appointment_type_ids.filtered(
            'google_reserve_enable'
        ).google_reserve_pending_sync = True
