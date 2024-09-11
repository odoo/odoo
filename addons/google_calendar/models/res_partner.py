# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models
from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendarService, InvalidSyncToken

_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _inherit = 'res.partner'

    google_calendar_sync_token = fields.Char(related='calendar_settings.google_calendar_sync_token',
                                             groups="base.group_system")
    google_calendar_cal_id = fields.Char(related='calendar_settings.google_calendar_cal_id',
                                         groups="base.group_system")
    google_synchronization_stopped = fields.Boolean(related='user_id.google_synchronization_stopped', readonly=False, groups="base.group_system")

    def _sync_google_calendar(self, calendar_service: GoogleCalendarService):
        self.ensure_one()
        results = self._sync_request(calendar_service)
        if not results or not results.get('events'):
            return False
        events, default_reminders, full_sync = results.values()
        # Google -> Odoo
        send_updates = not full_sync
        events.clear_type_ambiguity(self.env)
        recurrences = events.filter(lambda e: e.is_recurrence())

        # We apply Google updates only if their write date is later than the write date in Odoo.
        # It's possible that multiple updates affect the same record, maybe not directly.
        # To handle this, we preserve the write dates in Odoo before applying any updates,
        # and use these dates instead of the current live dates.
        odoo_events = self.env['calendar.event'].browse((events - recurrences).odoo_ids(self.env))
        odoo_recurrences = self.env['calendar.recurrence'].browse(recurrences.odoo_ids(self.env))
        recurrences_write_dates = {r.id: r.write_date for r in odoo_recurrences}
        events_write_dates = {e.id: e.write_date for e in odoo_events}
        synced_recurrences = self.env['calendar.recurrence']._sync_google2odoo(recurrences, recurrences_write_dates)
        synced_events = self.env['calendar.event']._sync_google2odoo(events - recurrences, events_write_dates, default_reminders=default_reminders)

        # Odoo -> Google
        recurrences = self.env['calendar.recurrence']._get_records_to_sync(full_sync=full_sync)
        recurrences -= synced_recurrences
        recurrences.with_context(send_updates=send_updates)._sync_odoo2google(calendar_service)
        synced_events |= recurrences.calendar_event_ids - recurrences._get_outliers()
        synced_events |= synced_recurrences.calendar_event_ids - synced_recurrences._get_outliers()
        events = self.env['calendar.event']._get_records_to_sync(full_sync=full_sync)
        (events - synced_events).with_context(send_updates=send_updates)._sync_odoo2google(calendar_service)

        return bool(events | synced_events) or bool(recurrences | synced_recurrences)

    def _sync_single_event(self, calendar_service: GoogleCalendarService, odoo_event, event_id):
        self.ensure_one()
        results = self._sync_request(calendar_service, event_id)
        if not results or not results.get('events'):
            return False
        event, default_reminders, full_sync = results.values()
        # Google -> Odoo
        send_updates = not full_sync
        event.clear_type_ambiguity(self.env)
        synced_events = self.env['calendar.event']._sync_google2odoo(event, default_reminders=default_reminders)
        # Odoo -> Google
        odoo_event.with_context(send_updates=send_updates)._sync_odoo2google(calendar_service)
        return bool(odoo_event | synced_events)

    def _sync_request(self, calendar_service, event_id=None):
        if self.user_id._get_google_sync_status() != "sync_active":
            return False
        # don't attempt to sync when another sync is already in progress, as we wouldn't be
        # able to commit the transaction anyway (row is locked)
        self.env.cr.execute("""SELECT id FROM res_partner WHERE id = %s FOR NO KEY UPDATE SKIP LOCKED""", [self.id])
        if not self.env.cr.rowcount:
            _logger.info("skipping calendar sync, locked partner %s", self.name)
            return False

        primary = not self.parent_id
        token = self.user_id._get_google_calendar_token()
        try:
            events, next_sync_token, default_reminders, full_sync = calendar_service.get_events(self, token=token, primary=primary, event_id=event_id)
            if not event_id:
                self.google_calendar_sync_token = next_sync_token
        except InvalidSyncToken:
            events, next_sync_token, default_reminders, full_sync = calendar_service.get_events(self, token=token, primary=primary, full_sync=True)
            self.google_calendar_sync_token = next_sync_token
        return {
            'events': events,
            'default_reminders': default_reminders,
            'full_sync': full_sync,
        }

    @api.model
    def _sync_all_google_calendar(self):
        """ Cron job """
        partners = self.env['res.partner'].sudo().search([('google_calendar_sync_token', '!=', False), ('google_synchronization_stopped', '=', False)])
        google = GoogleCalendarService(self.env['google.service'])
        for partner in partners:
            _logger.info("Calendar Synchro - Starting synchronization for %s", partner)
            try:
                partner.with_user(partner.user_id).sudo()._sync_google_calendar(google)
                self.env.cr.commit()
            except Exception:
                _logger.exception("[%s] Calendar Synchro Error!", partner)
                self.env.cr.rollback()
