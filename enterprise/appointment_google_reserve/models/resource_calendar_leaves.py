# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

from ..tools.google_reserve_iap import GoogleReserveIAP


class ResourceCalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    def create(self, vals_list):
        calendar_leaves = super().create(vals_list)
        calendar_leaves._sync_google_reserve_availabilities()
        return calendar_leaves

    def write(self, vals):
        google_sync_modifying_fields = {
            'date_from',
            'date_to',
            'resource_id',
        }

        if not google_sync_modifying_fields & vals.keys():
            return super().write(vals)

        old_dates_by_leave = False
        if 'date_from' in vals or 'date_to' in vals:
            old_dates_by_leave = {
                calendar_leave: (calendar_leave.date_from, calendar_leave.date_to) for calendar_leave in self
            }

        result = super().write(vals)
        self._sync_google_reserve_availabilities(old_dates_by_leave)

        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_update_availabilities(self):
        dates_by_appointment_type = self._sync_google_reserve_get_appointments()

        google_reserve_iap = GoogleReserveIAP()
        for appointment_type, dates in dates_by_appointment_type.items():
            google_reserve_iap.update_availabilities(
                appointment_type,
                dates[0],
                dates[1],
            )

    def _sync_google_reserve_availabilities(self, old_dates_by_leave=False):
        if not self.resource_id:
            return

        google_reserve_iap = GoogleReserveIAP()
        dates_by_appointment_type = self._sync_google_reserve_get_appointments(old_dates_by_leave=old_dates_by_leave)
        for appointment_type, dates in dates_by_appointment_type.items():
            google_reserve_iap.update_availabilities(
                appointment_type,
                dates[0],
                dates[1],
            )

    def _sync_google_reserve_get_appointments(self, old_dates_by_leave=False):
        appointment_resources = self.env['appointment.resource'].search([
            ('appointment_type_ids.google_reserve_enable', '=', 'True'),
            ('resource_id', 'in', self.resource_id.ids),
        ])
        appointment_resource_by_resource = appointment_resources.grouped('resource_id')

        dates_by_appointment_type = {}
        for calendar_leave in self:
            if not appointment_resource_by_resource.get(calendar_leave.resource_id):
                continue

            appointment_resource = appointment_resource_by_resource[calendar_leave.resource_id]
            for appointment_type in appointment_resource.appointment_type_ids:
                calendar_leave_from = calendar_leave.date_from
                calendar_leave_to = calendar_leave.date_to
                if old_dates_by_leave and old_dates_by_leave.get(calendar_leave):
                    calendar_leave_from = min(calendar_leave_from, old_dates_by_leave[calendar_leave][0])
                    calendar_leave_to = max(calendar_leave_to, old_dates_by_leave[calendar_leave][1])

                if not dates_by_appointment_type.get(appointment_type):
                    dates_by_appointment_type[appointment_type] = (calendar_leave_from, calendar_leave_to)
                else:
                    dates_by_appointment_type[appointment_type] = (
                        min(calendar_leave_from, dates_by_appointment_type[appointment_type][0]),
                        max(calendar_leave_to, dates_by_appointment_type[appointment_type][1])
                    )

        return dates_by_appointment_type
