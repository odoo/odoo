from odoo import api, fields, models
from ..tools.google_reserve_iap import GoogleReserveIAP


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    is_google_reserve = fields.Boolean("From Google Reserve", readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        """ Update the availability based on the new events created if needed. """

        events = super().create(vals_list)
        events._sync_google_reserve_availabilities()

        return events

    def write(self, vals):
        """ Update the google booking and availabilities. """

        google_sync_modifying_fields = {
            'active',
            'duration',
            'start',
            'stop',
            'resource_total_capacity_reserved',
        }

        old_dates_by_event = False
        if 'start' in vals or 'stop' in vals:
            old_dates_by_event = {
                event: (event.start, event.stop) for event in self
            }

        result = super().write(vals)
        if not vals.keys() & google_sync_modifying_fields:
            return result

        self._sync_google_reserve_availabilities(old_dates_by_event)

        if not self.env.context.get('google_reserve_service_rpc'):
            # if the modification does not come from a Google Reserve call -> update the booking
            google_reserve = GoogleReserveIAP()
            events_by_appointment = self.filtered(
                lambda event: event.appointment_type_id.google_reserve_enable
            ).grouped('appointment_type_id')
            for appointment_type, appointment_events in events_by_appointment.items():
                if google_reserve_events := appointment_events.filtered('is_google_reserve'):
                    if 'stop' in vals and 'start' not in vals:
                        # special case: Google will only accept "start" and "duration"
                        # -> manually add start for each event
                        for google_reserve_event in google_reserve_events:
                            google_reserve.update_booking(
                                appointment_type,
                                google_reserve_events.ids,
                                {'start': google_reserve_event.start, **vals}
                            )
                    else:
                        google_reserve.update_booking(appointment_type, google_reserve_events.ids, vals)

        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_update_availabilities(self):
        """ Cancel the google booking and update availabilities."""

        google_reserve = GoogleReserveIAP()
        dates_by_appointment = {}
        deleted_bookings_by_appointment = {}
        events_by_appointment = self.grouped('appointment_type_id')
        for appointment_type, appointment_events in events_by_appointment.items():
            if not appointment_type or not appointment_type.google_reserve_enable:
                continue

            dates_by_appointment[appointment_type] = (
                min(appointment_events.mapped('start')),
                max(appointment_events.mapped('stop')),
            )

            if google_reserve_events := appointment_events.filtered('is_google_reserve'):
                deleted_bookings_by_appointment[appointment_type] = google_reserve_events.ids

        for appointment_type, (start, end) in dates_by_appointment.items():
            google_reserve.update_availabilities(appointment_type, start, end)

        for appointment_type, google_reserve_events_ids in deleted_bookings_by_appointment.items():
            google_reserve.update_booking(appointment_type, google_reserve_events_ids, {'active': False})

    def _sync_google_reserve_availabilities(self, old_dates_by_event=False):
        google_reserve = GoogleReserveIAP()
        events_by_appointment = self.grouped('appointment_type_id')
        for appointment_type, appointment_events in events_by_appointment.items():
            if not appointment_type or not appointment_type.google_reserve_enable:
                continue

            min_start = min(appointment_events.mapped('start'))
            max_stop = max(appointment_events.mapped('stop'))
            if old_dates_by_event:
                old_starts = [old_date[0] for event, old_date in old_dates_by_event.items() if event in appointment_events]
                old_stops = [old_date[1] for event, old_date in old_dates_by_event.items() if event in appointment_events]
                min_start = min([min_start] + old_starts)
                max_stop = max([max_stop] + old_stops)

            google_reserve.update_availabilities(appointment_type, min_start, max_stop)
